"""
工作日志路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, date

from app.core.database import get_db
from app.models.models import User, WorkLog
from app.schemas.schemas import WorkLogCreate, WorkLogUpdate, WorkLogResponse
from app.routers.auth import get_current_user

router = APIRouter()


@router.get("", response_model=list[WorkLogResponse])
def list_logs(
    date_str: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(WorkLog)
    if date_str:
        target = datetime.fromisoformat(date_str)
        query = query.filter(
            WorkLog.log_date >= target.replace(hour=0, minute=0, second=0),
            WorkLog.log_date < target.replace(hour=23, minute=59, second=59)
        )
    return query.order_by(WorkLog.log_date.desc()).all()


@router.post("", response_model=WorkLogResponse)
def create_log(data: WorkLogCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """创建或更新当日工作日志。同一用户同一天只保留一条，自动覆盖。"""
    log_date = data.log_date.replace(hour=0, minute=0, second=0)
    existing = db.query(WorkLog).filter(
        WorkLog.user_id == current_user.id,
        WorkLog.log_date >= log_date,
        WorkLog.log_date < log_date.replace(hour=23, minute=59, second=59)
    ).first()

    if existing:
        existing.content = data.content
        existing.log_date = data.log_date
        db.commit()
        db.refresh(existing)
        return existing

    log = WorkLog(
        user_id=current_user.id,
        log_date=data.log_date,
        content=data.content,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.put("/{log_id}", response_model=WorkLogResponse)
def update_log(log_id: int, data: WorkLogUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """编辑自己的日志。"""
    log = db.query(WorkLog).filter(WorkLog.id == log_id).first()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="日志不存在")
    if log.user_id != current_user.id and current_user.role.value != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权限")
    if data.content is not None:
        log.content = data.content
    if data.log_date is not None:
        log.log_date = data.log_date
    db.commit()
    db.refresh(log)
    return log


@router.delete("/{log_id}")
def delete_log(log_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """删除自己的日志。"""
    log = db.query(WorkLog).filter(WorkLog.id == log_id).first()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="日志不存在")
    if log.user_id != current_user.id and current_user.role.value != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权限")
    db.delete(log)
    db.commit()
    return {"ok": True}