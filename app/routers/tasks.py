"""
任务路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import os
import uuid
import json

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User, Task, TaskColumn, Attachment, Comment, UserRole
from app.schemas.schemas import (
    TaskCreate, TaskUpdate, TaskResponse,
    CommentCreate, CommentResponse, AttachmentResponse
)
from app.routers.auth import get_current_user

router = APIRouter()

UPLOAD_DIR = settings.UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)


def allowed_file(filename: str) -> bool:
    ext = filename.lower().split('.')[-1]
    return ext in ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "png", "jpg", "jpeg", "gif", "zip", "rar"]


@router.get("", response_model=list[TaskResponse])
def list_tasks(project_id: int = None, my_tasks: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if my_tasks:
        query = query.filter(Task.assignee_id == current_user.id)
    tasks = query.order_by(Task.order.desc()).limit(100).all()
    return tasks


@router.post("", response_model=TaskResponse)
def create_task(data: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    col = db.query(TaskColumn).filter(TaskColumn.id == data.column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="列不存在")
    
    task = Task(
        project_id=data.project_id,
        column_id=data.column_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        assignee_id=data.assignee_id,
        due_date=data.due_date,
        tags=json.dumps(data.tags) if data.tags else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.view_count = (task.view_count or 0) + 1
    db.commit()
    return task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    if "tags" in update_data and update_data["tags"]:
        update_data["tags"] = json.dumps(update_data["tags"])
    
    for key, value in update_data.items():
        setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.delete(task)
    db.commit()
    return {"ok": True}


# === 附件上传 ===
@router.post("/{task_id}/attachments", response_model=AttachmentResponse)
async def upload_attachment(task_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    
    ext = file.filename.split(".")[-1]
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)
    
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件超过100MB限制")
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    attachment = Attachment(
        task_id=task_id,
        filename=stored_name,
        file_path=f"/uploads/{stored_name}",
        file_type=ext,
        file_size=len(content),
        uploaded_by=current_user.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{task_id}/attachments", response_model=list[AttachmentResponse])
def list_attachments(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Attachment).filter(Attachment.task_id == task_id).all()


@router.delete("/{task_id}/attachments/{attachment_id}")
def delete_attachment(task_id: int, attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    att = db.query(Attachment).filter(Attachment.id == attachment_id, Attachment.task_id == task_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")
    
    # 删除物理文件
    file_path = os.path.join(UPLOAD_DIR, att.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.delete(att)
    db.commit()
    return {"ok": True}


# === 评论 ===
@router.get("/{task_id}/comments", response_model=list[CommentResponse])
def list_comments(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    comments = db.query(Comment).filter(Comment.task_id == task_id).order_by(Comment.created_at).all()
    result = []
    for c in comments:
        r = CommentResponse.model_validate(c)
        r.user = c.user
        result.append(r)
    return result


@router.post("/{task_id}/comments", response_model=CommentResponse)
def create_comment(task_id: int, data: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    comment = Comment(
        task_id=task_id,
        user_id=current_user.id,
        content=data.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    r = CommentResponse.model_validate(comment)
    r.user = current_user
    return r