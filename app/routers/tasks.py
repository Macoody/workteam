"""
任务路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import os
import uuid
import json
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User, Task, TaskColumn, Attachment, Comment, UserRole, Document
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


def parse_json_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []


def normalize_delivery_dates(values):
    result = []
    for value in values or []:
        if not value:
            continue
        if isinstance(value, datetime):
            result.append(value)
            continue
        try:
            result.append(datetime.fromisoformat(str(value)))
        except ValueError:
            continue
    return result


def validate_linked_document(db: Session, project_id: int, document_id: int | None):
    if not document_id:
        return
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="关联文档不存在")
    if document.project_id not in (None, project_id):
        raise HTTPException(status_code=400, detail="只能关联当前项目内的文档")


def build_task_response(task: Task):
    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        column_id=task.column_id,
        title=task.title,
        description=task.description,
        node_output=task.node_output,
        linked_document_id=task.linked_document_id,
        assignee_id=task.assignee_id,
        assignee=task.assignee,
        due_date=task.due_date,
        delivery_dates=normalize_delivery_dates(parse_json_list(task.delivery_dates)),
        completed_by=parse_json_list(task.completed_by),
        tags=parse_json_list(task.tags),
        order=task.order,
        created_at=task.created_at,
        attachments=task.attachments or [],
    )


def resolve_target_column(db: Session, project_id: int, column_name: str):
    return db.query(TaskColumn).filter(
        TaskColumn.project_id == project_id,
        TaskColumn.name == column_name
    ).first()


@router.get("", response_model=list[TaskResponse])
def list_tasks(project_id: int = None, my_tasks: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if my_tasks:
        query = query.filter(Task.assignee_id == current_user.id)
    tasks = query.order_by(Task.order.desc()).limit(100).all()
    return [build_task_response(task) for task in tasks]


@router.post("", response_model=TaskResponse)
def create_task(data: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    col = db.query(TaskColumn).filter(TaskColumn.id == data.column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="列不存在")
    if col.project_id != data.project_id:
        raise HTTPException(status_code=400, detail="任务项目和看板列不匹配")
    validate_linked_document(db, data.project_id, data.linked_document_id)

    delivery_dates = normalize_delivery_dates(data.delivery_dates)
    if data.due_date:
        if not delivery_dates:
            delivery_dates = [data.due_date]
        elif data.due_date.isoformat() != delivery_dates[0].isoformat():
            delivery_dates = [data.due_date, *delivery_dates[:4]]
    
    task = Task(
        project_id=data.project_id,
        column_id=data.column_id,
        title=data.title,
        description=data.description,
        node_output=data.node_output,
        linked_document_id=data.linked_document_id,
        assignee_id=data.assignee_id,
        due_date=data.due_date,
        delivery_dates=json.dumps([item.isoformat() for item in delivery_dates]) if delivery_dates else None,
        tags=json.dumps(data.tags) if data.tags else None,
        completed_by=json.dumps([]),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return build_task_response(task)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.view_count = (task.view_count or 0) + 1
    db.commit()
    db.refresh(task)
    return build_task_response(task)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    target_project_id = update_data.get("project_id", task.project_id)
    target_column_id = update_data.get("column_id", task.column_id)

    if target_column_id is not None:
        col = db.query(TaskColumn).filter(TaskColumn.id == target_column_id).first()
        if not col:
            raise HTTPException(status_code=404, detail="列不存在")
        if col.project_id != target_project_id:
            raise HTTPException(status_code=400, detail="任务项目和看板列不匹配")
    if "linked_document_id" in update_data:
        validate_linked_document(db, target_project_id, update_data.get("linked_document_id"))
    if "due_date" in update_data and update_data["due_date"] is not None:
        if task.due_date and update_data["due_date"] != task.due_date:
            raise HTTPException(status_code=400, detail="交付时间已锁定，请使用延期功能")
        if not task.due_date:
            delivery_dates = normalize_delivery_dates(parse_json_list(task.delivery_dates))
            if not delivery_dates:
                delivery_dates = [update_data["due_date"]]
            task.delivery_dates = json.dumps([item.isoformat() for item in delivery_dates[:5]])
    elif "delivery_dates" in update_data:
        update_data.pop("delivery_dates")

    if "tags" in update_data:
        update_data["tags"] = json.dumps(update_data["tags"]) if update_data["tags"] else None
    
    for key, value in update_data.items():
        setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    return build_task_response(task)


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.delete(task)
    db.commit()
    return {"ok": True}


@router.post("/{task_id}/extend-delivery", response_model=TaskResponse)
def extend_delivery(task_id: int, payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    value = payload.get("due_date")
    if not value:
        raise HTTPException(status_code=400, detail="请选择新的交付时间")
    try:
        new_date = datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="交付时间格式错误")

    delivery_dates = normalize_delivery_dates(parse_json_list(task.delivery_dates))
    if not task.due_date:
        task.due_date = new_date
        delivery_dates = [new_date]
    else:
        if len(delivery_dates) >= 5:
            raise HTTPException(status_code=400, detail="最多只能保留 5 个交付时间")
        delivery_dates.append(new_date)
    task.delivery_dates = json.dumps([item.isoformat() for item in delivery_dates])
    db.commit()
    db.refresh(task)
    return build_task_response(task)


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    completed_by = parse_json_list(task.completed_by)
    if current_user.username not in completed_by:
        completed_by.append(current_user.username)
    task.completed_by = json.dumps(completed_by)

    target_name = "已完成" if current_user.username == "mac" else "待验收"
    target_column = resolve_target_column(db, task.project_id, target_name)
    if not target_column:
        raise HTTPException(status_code=400, detail=f"项目中缺少“{target_name}”列")
    task.column_id = target_column.id

    db.commit()
    db.refresh(task)
    return build_task_response(task)


@router.post("/{task_id}/claim", response_model=TaskResponse)
def claim_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    target_column = resolve_target_column(db, task.project_id, "进行中")
    if not target_column:
        raise HTTPException(status_code=400, detail="项目中缺少“进行中”列")

    task.assignee_id = current_user.id
    task.column_id = target_column.id
    db.commit()
    db.refresh(task)
    return build_task_response(task)


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
