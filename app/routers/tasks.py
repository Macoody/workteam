"""
任务路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session
import os
import uuid
import json
import re
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.core.timezone import business_now, parse_datetime, to_business_time
from app.models.models import (
    User, Task, TaskColumn, Attachment, Comment, CommentMention,
    Document, Project, RecurringTaskRule, ROLE_ADMIN, normalize_role
)
from app.routers.auth import _update_last_active_time, build_user_response
from app.schemas.schemas import (
    TaskCreate, TaskUpdate, TaskResponse,
    CommentCreate, CommentResponse, AttachmentResponse, MentionNotificationResponse,
    RecurringTaskRuleCreate, RecurringTaskRuleResponse
)
from app.routers.auth import get_current_user
from app.routers.projects import ensure_default_columns
from app.services.recurring_tasks import business_today, generate_due_recurring_tasks

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
            result.append(to_business_time(value))
            continue
        try:
            result.append(to_business_time(parse_datetime(value)))
        except (TypeError, ValueError):
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
    recent_comments = []
    comments = sorted(
        task.comments or [],
        key=lambda item: to_business_time(item.created_at) or datetime.min,
        reverse=True,
    )[:2]
    for comment in comments:
        item = CommentResponse.model_validate(comment)
        item.user = build_user_response(comment.user) if comment.user else None
        item.created_at = to_business_time(comment.created_at)
        recent_comments.append(item)
    attachments = []
    for attachment in task.attachments or []:
        item = AttachmentResponse.model_validate(attachment)
        item.uploaded_at = to_business_time(attachment.uploaded_at)
        attachments.append(item)
    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        column_id=task.column_id,
        column_name=task.column.name if task.column else None,
        column_color=task.column.color if task.column else None,
        title=task.title,
        description=task.description,
        node_output=task.node_output,
        linked_document_id=task.linked_document_id,
        assignee_id=task.assignee_id,
        assignee=build_user_response(task.assignee) if task.assignee else None,
        due_date=to_business_time(task.due_date),
        delivery_dates=normalize_delivery_dates(parse_json_list(task.delivery_dates)),
        completed_by=parse_json_list(task.completed_by),
        completed_at=to_business_time(task.completed_at),
        tags=parse_json_list(task.tags),
        recurrence_rule_id=task.recurrence_rule_id,
        recurrence_occurrence_date=task.recurrence_occurrence_date,
        order=task.order,
        created_at=to_business_time(task.created_at),
        updated_at=to_business_time(task.updated_at),
        attachments=attachments,
        recent_comments=recent_comments,
    )


def resolve_target_column(db: Session, project_id: int, column_name: str):
    return db.query(TaskColumn).filter(
        TaskColumn.project_id == project_id,
        TaskColumn.name == column_name
    ).first()


def extract_mentioned_users(db: Session, content: str, author_id: int):
    tokens = {token.strip() for token in re.findall(r'@([^\s@，,。；;：:\n]+)', content or '') if token.strip()}
    if not tokens:
        return []
    users = db.query(User).filter(User.is_active == True, User.id != author_id).all()
    matched = []
    for user in users:
        if user.username in tokens or (user.display_name and user.display_name in tokens):
            matched.append(user)
    return matched


def build_mention_notification(mention: CommentMention):
    task = mention.task
    project = task.project if task else None
    return MentionNotificationResponse(
        id=mention.id,
        comment_id=mention.comment_id,
        task_id=mention.task_id,
        project_id=task.project_id if task else 0,
        task_title=task.title if task else "任务",
        project_name=project.name if project else None,
        comment_content=mention.comment.content if mention.comment else "",
        mentioned_by=build_user_response(mention.comment.user) if mention.comment and mention.comment.user else None,
        created_at=to_business_time(mention.created_at),
        is_read=bool(mention.is_read),
    )


def validate_due_time(value: str | None):
    if not value:
        return None
    value = value.strip()
    if not re.match(r"^\d{2}:\d{2}$", value):
        raise HTTPException(status_code=400, detail="每日交付时间格式应为 HH:mm")
    hour, minute = [int(part) for part in value.split(":", 1)]
    if hour > 23 or minute > 59:
        raise HTTPException(status_code=400, detail="每日交付时间无效")
    return value


def build_recurring_rule_response(rule: RecurringTaskRule):
    return RecurringTaskRuleResponse.model_validate(rule)


@router.get("", response_model=list[TaskResponse])
def list_tasks(project_id: int = None, assignee_id: int = None, my_tasks: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    generate_due_recurring_tasks(db)
    db.commit()
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if assignee_id is not None:
        query = query.filter(Task.assignee_id == assignee_id)
    if my_tasks:
        query = query.filter(Task.assignee_id == current_user.id)
    tasks = query.order_by(
        func.coalesce(Task.updated_at, Task.created_at).desc(),
        Task.created_at.desc(),
        Task.id.desc(),
    ).limit(100).all()
    return [build_task_response(task) for task in tasks]


@router.post("", response_model=TaskResponse)
def create_task(data: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_default_columns(db, data.project_id)
    col = db.query(TaskColumn).filter(TaskColumn.id == data.column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="列不存在")
    if col.project_id != data.project_id:
        raise HTTPException(status_code=400, detail="任务项目和看板列不匹配")
    validate_linked_document(db, data.project_id, data.linked_document_id)

    due_date = to_business_time(data.due_date)
    delivery_dates = normalize_delivery_dates(data.delivery_dates)
    if due_date:
        if not delivery_dates:
            delivery_dates = [due_date]
        elif due_date.isoformat() != delivery_dates[0].isoformat():
            delivery_dates = [due_date, *delivery_dates[:4]]
    
    task = Task(
        project_id=data.project_id,
        column_id=data.column_id,
        title=data.title,
        description=data.description,
        node_output=data.node_output,
        linked_document_id=data.linked_document_id,
        assignee_id=data.assignee_id,
        due_date=due_date,
        delivery_dates=json.dumps([item.isoformat() for item in delivery_dates]) if delivery_dates else None,
        tags=json.dumps(data.tags) if data.tags else None,
        completed_by=json.dumps([]),
    )
    db.add(task)
    db.commit()
    _update_last_active_time(db, current_user)
    db.refresh(task)
    return build_task_response(task)


@router.get("/recurring-rules", response_model=list[RecurringTaskRuleResponse])
def list_recurring_rules(project_id: int = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(RecurringTaskRule)
    if project_id:
        query = query.filter(RecurringTaskRule.project_id == project_id)
    rules = query.order_by(RecurringTaskRule.created_at.desc()).limit(100).all()
    return [build_recurring_rule_response(rule) for rule in rules]


@router.post("/recurring-rules", response_model=RecurringTaskRuleResponse)
def create_recurring_rule(data: RecurringTaskRuleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.end_date and data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    if data.end_date and data.end_date < business_today():
        raise HTTPException(status_code=400, detail="结束日期不能早于今天")

    ensure_default_columns(db, data.project_id)
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    col = db.query(TaskColumn).filter(TaskColumn.id == data.column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="列不存在")
    if col.project_id != data.project_id:
        raise HTTPException(status_code=400, detail="任务项目和看板列不匹配")
    validate_linked_document(db, data.project_id, data.linked_document_id)

    rule = RecurringTaskRule(
        project_id=data.project_id,
        column_id=data.column_id,
        title=data.title,
        description=data.description,
        node_output=data.node_output,
        linked_document_id=data.linked_document_id,
        assignee_id=data.assignee_id,
        recurrence_type="daily",
        start_date=data.start_date,
        end_date=data.end_date,
        due_time=validate_due_time(data.due_time),
        is_active=True,
        created_by=current_user.id,
    )
    db.add(rule)
    db.flush()
    generate_due_recurring_tasks(db)
    db.commit()
    _update_last_active_time(db, current_user)
    db.refresh(rule)
    return build_recurring_rule_response(rule)


@router.delete("/recurring-rules/{rule_id}")
def stop_recurring_rule(rule_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rule = db.query(RecurringTaskRule).filter(RecurringTaskRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="周期任务规则不存在")
    if rule.created_by != current_user.id and current_user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="无权限停用该周期任务")
    rule.is_active = False
    db.commit()
    _update_last_active_time(db, current_user)
    return {"ok": True}


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
        update_data["due_date"] = to_business_time(update_data["due_date"])
        if task.due_date and update_data["due_date"] != to_business_time(task.due_date):
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
    _update_last_active_time(db, current_user)
    db.refresh(task)
    return build_task_response(task)


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.delete(task)
    db.commit()
    _update_last_active_time(db, current_user)
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
        new_date = to_business_time(parse_datetime(value))
    except (TypeError, ValueError):
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

    task.completed_at = business_now()

    target_name = "已完成" if normalize_role(current_user.role) == ROLE_ADMIN else "待验收"
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

    current_column = db.query(TaskColumn).filter(TaskColumn.id == task.column_id).first()
    if not current_column or current_column.name != "待处理":
        raise HTTPException(status_code=400, detail="只有待处理状态的任务可以领取")

    target_column = resolve_target_column(db, task.project_id, "进行中")
    if not target_column:
        raise HTTPException(status_code=400, detail="项目中缺少“进行中”列")
    pending_column = resolve_target_column(db, task.project_id, "待处理")
    if not pending_column or task.column_id != pending_column.id:
        raise HTTPException(status_code=400, detail="只有待处理状态的任务才能领取")

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
    item = AttachmentResponse.model_validate(attachment)
    item.uploaded_at = to_business_time(attachment.uploaded_at)
    return item


@router.get("/{task_id}/attachments", response_model=list[AttachmentResponse])
def list_attachments(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attachments = db.query(Attachment).filter(Attachment.task_id == task_id).all()
    result = []
    for attachment in attachments:
        item = AttachmentResponse.model_validate(attachment)
        item.uploaded_at = to_business_time(attachment.uploaded_at)
        result.append(item)
    return result


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
        r.user = build_user_response(c.user) if c.user else None
        r.created_at = to_business_time(c.created_at)
        result.append(r)
    return result


@router.get("/comment-mentions/me", response_model=list[MentionNotificationResponse])
def list_my_mentions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mentions = db.query(CommentMention).filter(
        CommentMention.user_id == current_user.id
    ).order_by(CommentMention.created_at.desc()).limit(30).all()
    return [build_mention_notification(mention) for mention in mentions]


@router.post("/comment-mentions/{mention_id}/read")
def mark_mention_read(mention_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mention = db.query(CommentMention).filter(
        CommentMention.id == mention_id,
        CommentMention.user_id == current_user.id
    ).first()
    if not mention:
        raise HTTPException(status_code=404, detail="提醒不存在")
    mention.is_read = True
    db.commit()
    return {"ok": True}


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

    mentioned_users = extract_mentioned_users(db, data.content, current_user.id)
    for user in mentioned_users:
        db.add(CommentMention(
            comment_id=comment.id,
            task_id=task_id,
            user_id=user.id,
            is_read=False,
        ))
    if mentioned_users:
        db.commit()
    
    r = CommentResponse.model_validate(comment)
    r.user = build_user_response(current_user)
    r.created_at = to_business_time(comment.created_at)
    return r
