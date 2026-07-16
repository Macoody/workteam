"""
数据库连接与运行时 schema 兼容

- 使用 SQLAlchemy 2.0 + psycopg2（PostgreSQL）。
- `ensure_runtime_schema()` 在启动时检查并补齐老库迁移期间缺失的列/表，
  这样本地首次启动或灰度阶段都不会因为 schema 不齐导致崩溃。
  老库（MySQL 8.x）迁移完成后，这个函数仅在补列时是幂等的，可继续保留。
"""
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings
from .timezone import business_utc_offset

# 启动期配置校验（DB URL/密钥必须存在）
settings.validate()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    future=True,
)


@event.listens_for(engine, "connect")
def set_business_timezone(dbapi_connection, _connection_record) -> None:
    """让数据库连接里的 CURRENT_TIMESTAMP/now() 也使用业务时区。"""
    cursor = dbapi_connection.cursor()
    try:
        if engine.dialect.name == "postgresql":
            cursor.execute("SET TIME ZONE %s", (settings.BUSINESS_TIMEZONE,))
        elif engine.dialect.name in {"mysql", "mariadb"}:
            cursor.execute("SET time_zone = %s", (business_utc_offset(),))
    finally:
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 一些 PG 上没有但项目里仍然使用的老字段名/老兼容逻辑，仅在补列时使用
_LEGACY_COLUMN_DDL: dict[str, list[tuple[str, str]]] = {
    "users": [
        ("color", "VARCHAR(20) DEFAULT '#93c5fd'"),
        ("email", "VARCHAR(100)"),
        ("is_online", "BOOLEAN DEFAULT FALSE"),
        ("last_visit_time", "TIMESTAMP WITH TIME ZONE"),
        ("last_active_time", "TIMESTAMP WITH TIME ZONE"),
        ("last_offline_time", "TIMESTAMP WITH TIME ZONE"),
        ("current_section", "VARCHAR(100)"),
        ("previous_section", "VARCHAR(100)"),
        ("wechat_openid", "VARCHAR(100)"),
        ("wechat_unionid", "VARCHAR(100)"),
        ("wechat_bound_at", "TIMESTAMP WITH TIME ZONE"),
    ],
    "tasks": [
        ("node_output", "TEXT"),
        ("linked_document_id", "INTEGER"),
        ("delivery_dates", "TEXT"),
        ("completed_by", "TEXT"),
        ("completed_at", "TIMESTAMP WITH TIME ZONE"),
        ("recurrence_rule_id", "INTEGER"),
        ("recurrence_occurrence_date", "DATE"),
    ],
    "documents": [
        ("last_editor_id", "INTEGER"),
        ("last_edited_at", "TIMESTAMP WITH TIME ZONE"),
    ],
    "digital_phones": [
        ("activation_code", "VARCHAR(100)"),
    ],
    "digital_customers": [
        ("device_number", "VARCHAR(100)"),
    ],
}


def _dialect_name() -> str:
    return engine.dialect.name


def _compatible_column_type(ddl_type: str) -> str:
    if _dialect_name() in {"mysql", "mariadb"}:
        return ddl_type.replace("TIMESTAMP WITH TIME ZONE", "DATETIME")
    return ddl_type


def _add_column_sql(table: str, column_name: str, ddl_type: str) -> str:
    ddl_type = _compatible_column_type(ddl_type)
    if _dialect_name() == "postgresql":
        return f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column_name} {ddl_type}"
    return f"ALTER TABLE {table} ADD COLUMN {column_name} {ddl_type}"


def _column_exists(inspector, table: str, column: str) -> bool:
    if not inspector.has_table(table):
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def _index_exists(inspector, table: str, index_name: str) -> bool:
    if not inspector.has_table(table):
        return False
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


def _unique_exists(inspector, table: str, unique_name: str) -> bool:
    if not inspector.has_table(table):
        return False
    return any(u["name"] == unique_name for u in inspector.get_unique_constraints(table))


def ensure_runtime_schema() -> None:
    """
    启动时检查并补齐缺失的列/索引/表。
    - 补列：users.color / users.email / tasks.node_output / tasks.linked_document_id /
            tasks.delivery_dates / tasks.completed_by
    - 补表：comment_mentions
    - 补唯一约束：documents.share_token（允许空值）
    - 补外键：projects.owner_id → users.id
    """
    inspector = inspect(engine)

    # 1) 补列
    for table, columns in _LEGACY_COLUMN_DDL.items():
        if not inspector.has_table(table):
            continue
        for column_name, ddl_type in columns:
            if not _column_exists(inspector, table, column_name):
                with engine.begin() as conn:
                    conn.execute(text(_add_column_sql(table, column_name, ddl_type)))
    inspector = inspect(engine)

    if inspector.has_table("documents"):
        with engine.begin() as conn:
            if _column_exists(inspector, "documents", "last_editor_id"):
                conn.execute(
                    text(
                        "UPDATE documents "
                        "SET last_editor_id = creator_id "
                        "WHERE last_editor_id IS NULL AND creator_id IS NOT NULL"
                    )
                )
            if _column_exists(inspector, "documents", "last_edited_at"):
                conn.execute(
                    text(
                        "UPDATE documents "
                        "SET last_edited_at = COALESCE(updated_at, created_at) "
                        "WHERE last_edited_at IS NULL"
                    )
                )

    # 1.05) 微信小程序绑定索引
    if (
        inspector.has_table("users")
        and _column_exists(inspector, "users", "wechat_openid")
        and not _index_exists(inspector, "users", "ix_users_wechat_openid")
    ):
        with engine.begin() as conn:
            if _dialect_name() == "postgresql":
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_wechat_openid "
                        "ON users (wechat_openid)"
                    )
                )
            else:
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX ix_users_wechat_openid "
                        "ON users (wechat_openid)"
                    )
                )
    if (
        inspector.has_table("users")
        and _column_exists(inspector, "users", "wechat_unionid")
        and not _index_exists(inspector, "users", "ix_users_wechat_unionid")
    ):
        with engine.begin() as conn:
            if _dialect_name() == "postgresql":
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_users_wechat_unionid "
                        "ON users (wechat_unionid)"
                    )
                )
            else:
                conn.execute(text("CREATE INDEX ix_users_wechat_unionid ON users (wechat_unionid)"))

    # 1.1) 周期任务生成防重索引
    if (
        inspector.has_table("tasks")
        and _column_exists(inspector, "tasks", "recurrence_rule_id")
        and _column_exists(inspector, "tasks", "recurrence_occurrence_date")
        and not _index_exists(inspector, "tasks", "ux_tasks_recurring_occurrence")
    ):
        with engine.begin() as conn:
            if _dialect_name() == "postgresql":
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tasks_recurring_occurrence "
                        "ON tasks (recurrence_rule_id, recurrence_occurrence_date)"
                    )
                )
            else:
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX ux_tasks_recurring_occurrence "
                        "ON tasks (recurrence_rule_id, recurrence_occurrence_date)"
                    )
                )

    # 2) 补 comment_mentions 表（如果模型声明了 Base 之后还没建）
    if not inspector.has_table("comment_mentions"):
        id_type = "SERIAL" if _dialect_name() == "postgresql" else "INTEGER AUTO_INCREMENT"
        timestamp_type = "TIMESTAMP WITH TIME ZONE" if _dialect_name() == "postgresql" else "DATETIME"
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS comment_mentions (
                        id {id_type} PRIMARY KEY,
                        comment_id INTEGER NOT NULL
                            REFERENCES comments(id) ON DELETE CASCADE,
                        task_id INTEGER NOT NULL
                            REFERENCES tasks(id) ON DELETE CASCADE,
                        user_id INTEGER NOT NULL
                            REFERENCES users(id),
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at {timestamp_type} DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

    # 3) 补 documents.share_token 的唯一约束（如果还没有）
    if inspector.has_table("documents") and not (
        _unique_exists(inspector, "documents", "ix_documents_share_token")
        or _index_exists(inspector, "documents", "ix_documents_share_token")
    ):
        with engine.begin() as conn:
            if _dialect_name() == "postgresql":
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_share_token "
                        "ON documents (share_token) WHERE share_token IS NOT NULL"
                    )
                )
            else:
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX ix_documents_share_token "
                        "ON documents (share_token)"
                    )
                )

    # 4) 补 projects.owner_id 上的索引（如果还没有）
    if inspector.has_table("projects") and not _index_exists(
        inspector, "projects", "ix_projects_owner_id"
    ):
        with engine.begin() as conn:
            if _dialect_name() == "postgresql":
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_projects_owner_id "
                        "ON projects (owner_id)"
                    )
                )
            else:
                conn.execute(text("CREATE INDEX ix_projects_owner_id ON projects (owner_id)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
