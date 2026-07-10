"""
项目管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.timezone import to_business_time
from app.models.models import User, Project, TaskColumn, Task, ROLE_ADMIN, normalize_role
from app.schemas.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.routers.auth import get_current_user

router = APIRouter()

DEFAULT_KANBAN_COLUMNS = [
    {"name": "待处理", "order": 0, "color": "#94a3b8"},
    {"name": "进行中", "order": 1, "color": "#3b82f6"},
    {"name": "待验收", "order": 2, "color": "#f59e0b"},
    {"name": "已完成", "order": 3, "color": "#10b981"},
]


def build_project_response(project: Project):
    item = ProjectResponse.model_validate(project)
    item.created_at = to_business_time(project.created_at)
    return item


def default_columns(project_id: int):
    """新建项目时创建默认看板列"""
    cols = []
    for d in DEFAULT_KANBAN_COLUMNS:
        col = TaskColumn(project_id=project_id, **d)
        cols.append(col)
    return cols


def ensure_default_columns(db: Session, project_id: int):
    """补齐项目默认看板列，兼容老数据或误删列的情况。"""
    existing = {
        col.name
        for col in db.query(TaskColumn).filter(TaskColumn.project_id == project_id).all()
    }
    created = []
    for item in DEFAULT_KANBAN_COLUMNS:
        if item["name"] in existing:
            continue
        col = TaskColumn(project_id=project_id, **item)
        db.add(col)
        created.append(col)
    if created:
        db.commit()
    return created


@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = db.query(Project).all()
    result = []
    for p in projects:
        columns = db.query(TaskColumn).filter(TaskColumn.project_id == p.id).all()
        column_ids = [column.id for column in columns]
        column_name_by_id = {column.id: column.name for column in columns}
        status_counts = {
            "待处理": 0,
            "进行中": 0,
            "待验收": 0,
            "已完成": 0,
        }
        if column_ids:
            tasks = db.query(Task).filter(Task.column_id.in_(column_ids)).all()
            for task in tasks:
                column_name = column_name_by_id.get(task.column_id)
                if column_name in status_counts:
                    status_counts[column_name] += 1
        r = build_project_response(p)
        r.task_count = sum(status_counts.values())
        r.pending_count = status_counts["待处理"]
        r.in_progress_count = status_counts["进行中"]
        r.review_count = status_counts["待验收"]
        r.done_count = status_counts["已完成"]
        result.append(r)
    return result


@router.post("", response_model=ProjectResponse)
def create_project(data: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = Project(
        name=data.name,
        description=data.description,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # 创建默认看板列
    ensure_default_columns(db, project.id)
    
    return build_project_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return build_project_response(project)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    # 只有管理员或项目创建者可以编辑
    if normalize_role(current_user.role) != ROLE_ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")
    
    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    db.commit()
    db.refresh(project)
    return build_project_response(project)


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if normalize_role(current_user.role) != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="只有管理员可以删除项目")
    db.delete(project)
    db.commit()
    return {"ok": True}
