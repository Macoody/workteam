"""
徐东摆地摊 - FastAPI 后端
Phase 1 MVP: 用户注册登录 + 项目管理 + 看板 + 任务增删改查 + 文档中心
"""
import logging
import os
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal, ensure_runtime_schema
from app.routers import auth, projects, tasks, documents, kanban, worklogs, wechat, digital_employees
from app.services.recurring_tasks import generate_due_recurring_tasks

# 创建数据库表
ensure_runtime_schema()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="徐东摆地摊", version="1.0.0")
logger = logging.getLogger("workteam.recurring_tasks")
_recurring_scheduler_stop = threading.Event()
_recurring_scheduler_thread: threading.Thread | None = None


def run_recurring_task_generation():
    db = SessionLocal()
    try:
        count = generate_due_recurring_tasks(db)
        db.commit()
        if count:
            logger.info("generated %s recurring task(s)", count)
    except Exception:
        db.rollback()
        logger.exception("failed to generate recurring tasks")
    finally:
        db.close()


def recurring_scheduler_loop():
    run_recurring_task_generation()
    while not _recurring_scheduler_stop.wait(60 * 60):
        run_recurring_task_generation()


@app.on_event("startup")
def start_recurring_scheduler():
    global _recurring_scheduler_thread
    if _recurring_scheduler_thread and _recurring_scheduler_thread.is_alive():
        return
    _recurring_scheduler_stop.clear()
    _recurring_scheduler_thread = threading.Thread(
        target=recurring_scheduler_loop,
        name="recurring-task-generator",
        daemon=True,
    )
    _recurring_scheduler_thread.start()


@app.on_event("shutdown")
def stop_recurring_scheduler():
    _recurring_scheduler_stop.set()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上传文件（附件、文档素材）走运行时配置，方便本地和服务器挂载同一持久化目录。
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(projects.router, prefix="/api/projects", tags=["项目管理"])
app.include_router(kanban.router, prefix="/api/kanban", tags=["看板"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务"])
app.include_router(documents.router, prefix="/api/documents", tags=["文档中心"])
app.include_router(worklogs.router, prefix="/api/worklogs", tags=["工作日志"])
app.include_router(wechat.router, prefix="/api/wechat", tags=["微信小程序"])
app.include_router(digital_employees.router, prefix="/api/digital-employees", tags=["数字员工"])


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
