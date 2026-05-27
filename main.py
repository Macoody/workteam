"""
工作团队系统 - FastAPI 后端
Phase 1 MVP: 用户注册登录 + 项目管理 + 看板 + 任务增删改查 + 文档中心
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.routers import auth, projects, tasks, documents, kanban

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="工作团队系统", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件和模板（文档预览用）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(projects.router, prefix="/api/projects", tags=["项目管理"])
app.include_router(kanban.router, prefix="/api/kanban", tags=["看板"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务"])
app.include_router(documents.router, prefix="/api/documents", tags=["文档中心"])


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}