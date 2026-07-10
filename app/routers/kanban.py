"""
看板路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import User, Project, TaskColumn, Task, ROLE_ADMIN, normalize_role
from app.schemas.schemas import ColumnCreate, ColumnUpdate, ColumnResponse, TaskMove
from app.routers.auth import get_current_user, require_admin
from app.routers.tasks import build_task_response
from app.routers.projects import ensure_default_columns

router = APIRouter()


@router.get("/project/{project_id}", response_model=List[ColumnResponse])
def get_kanban(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    ensure_default_columns(db, project_id)
    columns = db.query(TaskColumn).filter(TaskColumn.project_id == project_id).order_by(TaskColumn.order).all()
    result = []
    for col in columns:
        tasks = db.query(Task).filter(Task.column_id == col.id).order_by(Task.order).all()
        result.append(
            ColumnResponse(
                id=col.id,
                project_id=col.project_id,
                name=col.name,
                order=col.order,
                color=col.color,
                tasks=[build_task_response(task) for task in tasks],
            )
        )
    return result


@router.post("/project/{project_id}/column", response_model=ColumnResponse)
def create_column(project_id: int, data: ColumnCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if normalize_role(current_user.role) != ROLE_ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")
    
    col = TaskColumn(project_id=project_id, **data.model_dump())
    db.add(col)
    db.commit()
    db.refresh(col)
    return col


@router.put("/columns/{column_id}", response_model=ColumnResponse)
def update_column(column_id: int, data: ColumnUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    col = db.query(TaskColumn).filter(TaskColumn.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="列不存在")
    
    project = db.query(Project).filter(Project.id == col.project_id).first()
    if normalize_role(current_user.role) != ROLE_ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")
    
    if data.name is not None:
        col.name = data.name
    if data.order is not None:
        col.order = data.order
    if data.color is not None:
        col.color = data.color
    db.commit()
    db.refresh(col)
    return col


@router.delete("/columns/{column_id}")
def delete_column(column_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    col = db.query(TaskColumn).filter(TaskColumn.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="列不存在")
    db.delete(col)
    db.commit()
    return {"ok": True}


@router.post("/move")
def move_task(data: TaskMove, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == data.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    col = db.query(TaskColumn).filter(TaskColumn.id == data.target_column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="目标列不存在")
    
    task.column_id = data.target_column_id
    task.order = data.order
    db.commit()
    return {"ok": True}
