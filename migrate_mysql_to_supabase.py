"""
migrate_mysql_to_supabase.py
============================
把老 MySQL 的数据迁移到 Supabase Postgres。

⚠️  本脚本只做「全量覆盖」：写入端会 TRUNCATE 目标表再批量 INSERT。
    跑之前请确认：
      1. Supabase 端 schema 已经通过 ensure_runtime_schema() 建好
         （uvicorn 启动一次后端即可）
      2. Supabase 端当前没有需要保留的"线上数据"
         （你刚切过来，正常是空的；如果不是空，停下来自己手动清理）

用法：
    # 1) 在另一个终端里把后端启起来，让它把 Supabase 上的 schema 建好
    #    uvicorn main:app --host 127.0.0.1 --port 8001
    #
    # 2) 设环境变量
    export MYSQL_URL='mysql+pymysql://user:password@mysql.example.com:3306/machao_workteam?charset=utf8mb4'
    export DATABASE_URL='postgresql+psycopg://postgres:password@db.example.supabase.co:5432/postgres'
    #
    # 3) 跑脚本（默认 dry-run；会打印计划，不写数据）
    python migrate_mysql_to_supabase.py --dry-run
    #
    # 4) 真的跑（脚本会再问一次 y/n）
    python migrate_mysql_to_supabase.py
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# --- 迁移顺序：先父后子，按外键依赖排 ---
# 父子关系：
#   users -> projects -> task_columns -> tasks
#                                -> comments
#                                          -> comment_mentions
#                                -> attachments
#                  -> documents
#                  -> folders
#                  -> file_assets
#   work_logs（独立，但挂在 users 上）
MIGRATION_ORDER: list[str] = [
    "users",
    "projects",
    "task_columns",
    "folders",
    "documents",
    "tasks",
    "comments",
    "comment_mentions",
    "attachments",
    "file_assets",
    "work_logs",
]

# 时区处理：MySQL 里所有 datetime 都是无时区的"本地时间"
# PG 端是 TIMESTAMP WITH TIME ZONE，按 Asia/Shanghai (+08:00) 解释
BIZ_TZ_OFFSET = "+08:00"

# 已知 MySQL 时间字段（需要把无时区 datetime 转换成带时区的 timestamptz）
# 仅列出有数据的表对应的字段。结构来自前面 SHOW CREATE TABLE 的结果。
MYSQL_DT_COLUMNS: dict[str, list[str]] = {
    "users": ["created_at", "last_visit_time", "last_active_time"],
    "projects": ["created_at", "updated_at"],
    "task_columns": [],
    "folders": ["created_at"],
    "documents": ["created_at", "updated_at", "share_expire"],
    "tasks": ["due_date", "created_at", "updated_at"],
    "comments": ["created_at", "updated_at"],
    "comment_mentions": ["created_at"],
    "attachments": ["uploaded_at"],
    "file_assets": ["created_at"],
    "work_logs": ["log_date", "created_at", "updated_at"],
}


def _make_engine(url: str, label: str) -> Engine:
    print(f"  [engine] {label}: connecting ...")
    eng = create_engine(url, pool_pre_ping=True, future=True)
    # 立即触发一次连接，失败立刻报错
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    print(f"  [engine] {label}: ok")
    return eng


def _coerce_role(value: Any) -> Any:
    """大写转小写；非法值置为 NULL（让 PG 端默认 'member' 接管）"""
    if value is None:
        return None
    v = str(value).strip().lower()
    if v in {"admin", "member", "guest"}:
        return v
    return None


def _coerce_bool(value: Any) -> Any:
    """MySQL tinyint(1) -> PG boolean。SQLAlchemy 读出来是 int，强制转 bool"""
    if value is None:
        return None
    return bool(value)


def _row_to_pg(table: str, row: dict[str, Any]) -> dict[str, Any]:
    """逐行做类型/时区/枚举兜底转换"""
    out = dict(row)

    # 1) role 大小写兜底
    if table == "users" and "role" in out:
        out["role"] = _coerce_role(out["role"])

    # 2) tinyint(1) -> bool
    bool_cols_by_table = {
        "users": ["is_active"],
        "documents": ["is_public"],
        "comment_mentions": ["is_read"],
    }
    for col in bool_cols_by_table.get(table, []):
        if col in out:
            out[col] = _coerce_bool(out[col])

    # 3) 时区：把无时区 datetime 当成 +08:00 的本地时间
    for col in MYSQL_DT_COLUMNS.get(table, []):
        v = out.get(col)
        if v is None:
            continue
        # SQLAlchemy 读出来是 naive datetime；如果带 tzinfo 就不动
        if hasattr(v, "tzinfo") and v.tzinfo is not None:
            continue
        # naive：按 BIZ_TZ_OFFSET 解释
        from datetime import datetime, timezone, timedelta
        out[col] = v.replace(tzinfo=timezone(timedelta(hours=8)))

    return out


def _table_count(engine: Engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


def _fetch_all(engine: Engine, table: str) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"SELECT * FROM {table} ORDER BY id")).mappings().all()
    return [dict(r) for r in rows]


def _truncate(engine: Engine, table: str) -> None:
    with engine.begin() as conn:
        # RESTART IDENTITY 让 PG 端 SERIAL 从 1 重新开始
        # CASCADE 兜底万一有外键残留
        conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))


def _bulk_insert(engine: Engine, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    # 用 SQLAlchemy 的 insert().values(...) + 事务，更安全
    from sqlalchemy import Table, MetaData
    meta = MetaData()
    meta.reflect(bind=engine)
    tbl = meta.tables[table]
    with engine.begin() as conn:
        conn.execute(tbl.insert(), rows)


def migrate_table(mysql_engine: Engine, pg_engine: Engine, table: str) -> tuple[int, int]:
    """迁移单张表。返回 (mysql_count, pg_count_after)"""
    print(f"\n--- table: {table} ---")
    src_rows = _fetch_all(mysql_engine, table)
    src_count = len(src_rows)
    print(f"  mysql count: {src_count}")

    if src_count == 0:
        # 即便源表是空的，也保证目标表 schema 存在 + truncate 让序列对齐
        _truncate(pg_engine, table)
        print(f"  pg truncated (was empty), rows inserted: 0")
        return (src_count, 0)

    converted = [_row_to_pg(table, r) for r in src_rows]
    _truncate(pg_engine, table)
    _bulk_insert(pg_engine, table, converted)

    pg_count = _table_count(pg_engine, table)
    ok = "✓" if src_count == pg_count else "✗"
    print(f"  pg count after insert: {pg_count}  {ok}")
    if src_count != pg_count:
        raise RuntimeError(
            f"行数对不上: {table} mysql={src_count} pg={pg_count}，请人工核对"
        )
    return (src_count, pg_count)


def print_dry_run() -> None:
    pg_url = os.environ.get("DATABASE_URL", "")
    if not pg_url and os.environ.get("PG_HOST"):
        from urllib.parse import quote
        pg_url = (
            f"postgresql+psycopg://{quote(os.environ['PG_USER'], safe='')}:"
            f"{quote(os.environ['PG_PASSWORD'], safe='')}@"
            f"{os.environ['PG_HOST']}:{os.environ.get('PG_PORT', '5432')}/"
            f"{os.environ.get('PG_DB', 'postgres')}"
        )
    mysql_url = os.environ.get("MYSQL_URL", "")
    if not mysql_url and os.environ.get("MYSQL_HOST"):
        from urllib.parse import quote
        mysql_url = (
            f"mysql+pymysql://{quote(os.environ['MYSQL_USER'], safe='')}:"
            f"{quote(os.environ['MYSQL_PASSWORD'], safe='')}@"
            f"{os.environ['MYSQL_HOST']}:{os.environ.get('MYSQL_PORT', '3306')}/"
            f"{os.environ.get('MYSQL_DB', 'machao_workteam')}?charset=utf8mb4"
        )
    print("=" * 60)
    print("DRY RUN 模式：只读，不会写任何数据到 Supabase")
    print("=" * 60)
    print(f"  MYSQL_URL   = {'(set)' if mysql_url else '(MISSING)'}")
    print(f"  DATABASE_URL= {'(set)' if pg_url else '(MISSING)'}")
    print()
    print("如果上面两个都设了，准备迁移的表（按顺序）：")
    for i, t in enumerate(MIGRATION_ORDER, 1):
        print(f"  {i:2d}. {t}")
    print()
    print("转换规则：")
    print("  - users.role  大写->小写，非法值置 NULL（默认 'member'）")
    print("  - is_active/is_public/is_read  int(0/1) -> bool")
    print("  - 所有 datetime 字段 按 Asia/Shanghai (+08:00) 解释为带时区")
    print("  - 目标表先 TRUNCATE ... RESTART IDENTITY CASCADE 再批量 INSERT")
    print()
    print("去掉 --dry-run 参数会再次确认 y/n 后真正写入。")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只读模式：检查连通 + 打印计划")
    parser.add_argument("--yes", action="store_true", help="跳过 y/n 确认（CI 场景）")
    args = parser.parse_args()

    print_dry_run()

    pg_url = os.environ.get("DATABASE_URL", "")
    if not pg_url and os.environ.get("PG_HOST"):
        from urllib.parse import quote
        pg_url = (
            f"postgresql+psycopg://{quote(os.environ['PG_USER'], safe='')}:"
            f"{quote(os.environ['PG_PASSWORD'], safe='')}@"
            f"{os.environ['PG_HOST']}:{os.environ.get('PG_PORT', '5432')}/"
            f"{os.environ.get('PG_DB', 'postgres')}"
        )
    mysql_url = os.environ.get("MYSQL_URL", "")
    if not mysql_url and os.environ.get("MYSQL_HOST"):
        from urllib.parse import quote
        mysql_url = (
            f"mysql+pymysql://{quote(os.environ['MYSQL_USER'], safe='')}:"
            f"{quote(os.environ['MYSQL_PASSWORD'], safe='')}@"
            f"{os.environ['MYSQL_HOST']}:{os.environ.get('MYSQL_PORT', '3306')}/"
            f"{os.environ.get('MYSQL_DB', 'machao_workteam')}?charset=utf8mb4"
        )
    if not mysql_url or not pg_url:
        print("\n!! 请先 export MYSQL_URL 和 DATABASE_URL")
        return 2

    if args.dry_run:
        # 在 dry-run 模式下也连一下，验证两边都通
        print("\n[连通性体检] 尝试连接两个库 ...")
        _make_engine(mysql_url, "MySQL  (source)")
        _make_engine(pg_url,    "Supabase PG (target)")
        print("\n✓ dry-run 完成。两个库都通。去掉 --dry-run 真正迁移。")
        return 0

    print("\n即将：")
    print("  1) 读 MySQL machao_workteam 全表数据")
    print("  2) 逐表 TRUNCATE Supabase 目标表")
    print("  3) 逐表 bulk INSERT 到 Supabase")
    print("  4) 打印行数对账")
    print()
    if not args.yes:
        ans = input("确认执行？这一步会清空 Supabase 当前所有业务表 (yes/no): ").strip().lower()
        if ans not in {"y", "yes"}:
            print("取消。")
            return 0

    mysql_engine = _make_engine(mysql_url, "MySQL  (source)")
    pg_engine    = _make_engine(pg_url,    "Supabase PG (target)")

    print("\n开始迁移 ...")
    results: list[tuple[str, int, int]] = []
    try:
        for table in MIGRATION_ORDER:
            src, dst = migrate_table(mysql_engine, pg_engine, table)
            results.append((table, src, dst))
    except Exception as e:
        print(f"\n!! 迁移失败: {e}")
        print("!! 已迁移过的表：")
        for t, s, d in results:
            print(f"     {t}: mysql={s} pg={d}")
        return 1

    print("\n" + "=" * 60)
    print("迁移完成，行数对账：")
    print("=" * 60)
    print(f"  {'TABLE':<22} {'MYSQL':>8} {'PG':>8}  STATUS")
    total_src = total_dst = 0
    for t, s, d in results:
        status = "✓" if s == d else "✗"
        print(f"  {t:<22} {s:>8} {d:>8}    {status}")
        total_src += s
        total_dst += d
    print("-" * 60)
    print(f"  {'TOTAL':<22} {total_src:>8} {total_dst:>8}    {'✓' if total_src == total_dst else '✗'}")
    return 0 if total_src == total_dst else 1


if __name__ == "__main__":
    sys.exit(main())
