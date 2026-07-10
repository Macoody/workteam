"""
工作日志路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.timezone import day_bounds, to_business_time
from app.models.models import User, WorkLog, ROLE_ADMIN, normalize_role
from app.schemas.schemas import WorkLogCreate, WorkLogUpdate, WorkLogResponse
from app.routers.auth import build_user_response, get_current_user, _update_last_active_time

router = APIRouter()


def build_work_log_response(log: WorkLog):
    item = WorkLogResponse.model_validate(log)
    item.log_date = to_business_time(log.log_date)
    item.created_at = to_business_time(log.created_at)
    item.updated_at = to_business_time(log.updated_at)
    item.user = build_user_response(log.user) if log.user else None
    return item


@router.get("", response_model=list[WorkLogResponse])
def list_logs(
    date_str: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(WorkLog)
    if date_str:
        start, end = day_bounds(date_str)
        query = query.filter(
            WorkLog.log_date >= start,
            WorkLog.log_date <= end,
        )
    logs = query.order_by(WorkLog.log_date.desc()).all()
    return [build_work_log_response(log) for log in logs]


@router.post("", response_model=WorkLogResponse)
def create_log(data: WorkLogCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """创建或更新当日工作日志。同一用户同一天只保留一条，自动覆盖。"""
    log_date = to_business_time(data.log_date)
    start, end = day_bounds(log_date)
    existing = db.query(WorkLog).filter(
        WorkLog.user_id == current_user.id,
        WorkLog.log_date >= start,
        WorkLog.log_date <= end,
    ).first()

    if existing:
        existing.content = data.content
        existing.log_date = log_date
        db.commit()
        _update_last_active_time(db, current_user)
        db.refresh(existing)
        return build_work_log_response(existing)

    log = WorkLog(
        user_id=current_user.id,
        log_date=log_date,
        content=data.content,
    )
    db.add(log)
    db.commit()
    _update_last_active_time(db, current_user)
    db.refresh(log)
    return build_work_log_response(log)


@router.put("/{log_id}", response_model=WorkLogResponse)
def update_log(log_id: int, data: WorkLogUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """编辑自己的日志。"""
    log = db.query(WorkLog).filter(WorkLog.id == log_id).first()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="日志不存在")
    if log.user_id != current_user.id and normalize_role(current_user.role) != ROLE_ADMIN:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权限")
    if data.content is not None:
        log.content = data.content
    if data.log_date is not None:
        log.log_date = to_business_time(data.log_date)
    db.commit()
    db.refresh(log)
    return build_work_log_response(log)


@router.delete("/{log_id}")
def delete_log(log_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """删除自己的日志。"""
    log = db.query(WorkLog).filter(WorkLog.id == log_id).first()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="日志不存在")
    if log.user_id != current_user.id and normalize_role(current_user.role) != ROLE_ADMIN:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权限")
    db.delete(log)
    db.commit()
    return {"ok": True}
