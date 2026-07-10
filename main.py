"""
徐东摆地摊 - FastAPI 后端
Phase 1 MVP: 用户注册登录 + 项目管理 + 看板 + 任务增删改查 + 文档中心
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base, ensure_runtime_schema
from app.routers import auth, projects, tasks, documents, kanban, worklogs

# 创建数据库表
ensure_runtime_schema()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="徐东摆地摊", version="1.0.0")

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


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
