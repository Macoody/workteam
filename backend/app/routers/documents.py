"""
文档中心路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.database import get_db
from app.models.models import (
    User, Document, DocumentActivityLog, Folder, FileAsset, ROLE_ADMIN, normalize_role
)
from app.schemas.schemas import (
    DocumentActivityResponse, DocumentCreate, DocumentUpdate, DocumentResponse,
    FolderCreate, FolderResponse, FileAssetResponse
)
from app.routers.auth import get_current_user, require_admin, _update_last_active_time

router = APIRouter()
UPLOAD_DIR = os.path.join(settings.UPLOAD_DIR, "documents")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_DOC_TYPES = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "png", "jpg", "jpeg", "gif", "zip", "rar"]
BUSINESS_TZ = ZoneInfo(settings.BUSINESS_TIMEZONE)
DOCUMENT_ACTION_CREATE = "create"
DOCUMENT_ACTION_VIEW = "view"
DOCUMENT_ACTION_EDIT = "edit"


# === 文档 CRUD ===
def document_query(db: Session):
    return db.query(Document).options(
        joinedload(Document.creator),
        joinedload(Document.last_editor),
    )


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_business_time(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BUSINESS_TZ)


def timestamp_close(left, right) -> bool:
    if not left or not right:
        return False
    if left.tzinfo is not None:
        left = left.replace(tzinfo=None)
    if right.tzinfo is not None:
        right = right.replace(tzinfo=None)
    return abs((left - right).total_seconds()) < 1


def build_document_response(doc: Document):
    item = DocumentResponse.model_validate(doc)
    item.created_at = to_business_time(doc.created_at)
    item.updated_at = to_business_time(doc.updated_at)
    item.last_edited_at = to_business_time(doc.last_edited_at)
    return item


def build_activity_response(activity: DocumentActivityLog):
    item = DocumentActivityResponse.model_validate(activity)
    item.created_at = to_business_time(activity.created_at)
    return item


def add_document_activity(
    db: Session,
    document_id: int,
    user_id: int | None,
    action: str,
    created_at: datetime | None = None,
):
    if not user_id:
        return None
    activity = DocumentActivityLog(
        document_id=document_id,
        user_id=user_id,
        action=action,
        created_at=created_at or utc_now_naive(),
    )
    db.add(activity)
    return activity


def ensure_document_activity_seed(db: Session, doc: Document):
    exists = db.query(DocumentActivityLog.id).filter(
        DocumentActivityLog.document_id == doc.id
    ).first()
    if exists:
        return
    if doc.creator_id:
        add_document_activity(
            db,
            doc.id,
            doc.creator_id,
            DOCUMENT_ACTION_CREATE,
            doc.created_at or doc.last_edited_at or utc_now_naive(),
        )
    if doc.last_editor_id and doc.last_edited_at:
        created_at = doc.created_at
        same_initial_editor = doc.last_editor_id == doc.creator_id
        same_initial_time = timestamp_close(doc.last_edited_at, created_at)
        if not (same_initial_editor and same_initial_time):
            add_document_activity(
                db,
                doc.id,
                doc.last_editor_id,
                DOCUMENT_ACTION_EDIT,
                doc.last_edited_at,
            )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    folder_id: int = None,
    project_id: int = None,
    my_docs: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = document_query(db)
    if folder_id is not None:
        query = query.filter(Document.folder_id == folder_id)
    if project_id:
        query = query.filter(Document.project_id == project_id)
    if my_docs:
        query = query.filter(Document.creator_id == current_user.id)
    docs = query.order_by(
        Document.last_edited_at.desc(),
        Document.updated_at.desc(),
        Document.created_at.desc(),
    ).limit(100).all()
    return [build_document_response(doc) for doc in docs]


@router.post("", response_model=DocumentResponse)
def create_document(data: DocumentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    now = utc_now_naive()
    doc = Document(
        title=data.title,
        content=data.content or "",
        doc_type=data.doc_type,
        project_id=data.project_id,
        folder_id=data.folder_id,
        creator_id=current_user.id,
        last_editor_id=current_user.id,
        last_edited_at=now,
    )
    db.add(doc)
    db.flush()
    add_document_activity(db, doc.id, current_user.id, DOCUMENT_ACTION_CREATE, now)
    db.commit()
    _update_last_active_time(db, current_user)
    db.refresh(doc)
    return build_document_response(doc)


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = document_query(db).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    ensure_document_activity_seed(db, doc)
    db.execute(
        text(
            "UPDATE documents "
            "SET view_count = COALESCE(view_count, 0) + 1 "
            "WHERE id = :doc_id"
        ),
        {"doc_id": doc_id},
    )
    doc.view_count = (doc.view_count or 0) + 1
    add_document_activity(db, doc.id, current_user.id, DOCUMENT_ACTION_VIEW)
    db.commit()
    return build_document_response(doc)


@router.get("/{doc_id}/activities", response_model=list[DocumentActivityResponse])
def list_document_activities(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    ensure_document_activity_seed(db, doc)
    db.commit()
    activities = db.query(DocumentActivityLog).options(
        joinedload(DocumentActivityLog.user)
    ).filter(
        DocumentActivityLog.document_id == doc_id
    ).order_by(
        DocumentActivityLog.created_at.desc(),
        DocumentActivityLog.id.desc(),
    ).all()
    return [build_activity_response(activity) for activity in activities]


@router.put("/{doc_id}", response_model=DocumentResponse)
def update_document(doc_id: int, data: DocumentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = document_query(db).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 所有人可编辑任意文档（管理员可编辑全部）
    edited = False
    if data.title is not None and data.title != doc.title:
        doc.title = data.title
        edited = True
    if data.content is not None and data.content != doc.content:
        doc.content = data.content
        edited = True
    if edited:
        ensure_document_activity_seed(db, doc)
        now = utc_now_naive()
        doc.last_editor_id = current_user.id
        doc.last_editor = current_user
        doc.last_edited_at = now
        add_document_activity(db, doc.id, current_user.id, DOCUMENT_ACTION_EDIT, now)
    db.commit()
    _update_last_active_time(db, current_user)
    db.refresh(doc)
    return build_document_response(doc)


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if doc.creator_id != current_user.id and normalize_role(current_user.role) != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="无删除权限")
    db.delete(doc)
    db.commit()
    _update_last_active_time(db, current_user)
    return {"ok": True}


# === 外链分享 ===
@router.post("/{doc_id}/share")
def share_document(doc_id: int, mode: str = "readonly", expire_hours: int = 72, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if doc.creator_id != current_user.id and normalize_role(current_user.role) != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="无分享权限")
    
    import secrets
    from datetime import datetime, timedelta
    
    doc.is_public = True
    doc.share_token = secrets.token_urlsafe(32)
    doc.share_mode = mode
    doc.share_expire = datetime.utcnow() + timedelta(hours=expire_hours)
    db.commit()
    
    share_url = f"/api/documents/shared/{doc.share_token}"
    return {"share_url": share_url, "share_token": doc.share_token, "mode": mode, "expire_hours": expire_hours}


@router.get("/shared/{token}")
def view_shared_document(token: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.share_token == token).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或链接已失效")
    from datetime import datetime
    if doc.share_expire and doc.share_expire < datetime.utcnow():
        raise HTTPException(status_code=410, detail="分享链接已过期")
    return doc


# === 文件夹 ===
@router.get("/folders/all", response_model=list[FolderResponse])
def list_folders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Folder).filter(Folder.owner_id == current_user.id).all()


@router.post("/folders", response_model=FolderResponse)
def create_folder(data: FolderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    folder = Folder(name=data.name, parent_id=data.parent_id, owner_id=current_user.id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


@router.delete("/folders/{folder_id}")
def delete_folder(folder_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder or folder.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    db.delete(folder)
    db.commit()
    return {"ok": True}


# === 文件资产上传（通用文件存储）===
@router.post("/assets", response_model=FileAssetResponse)
async def upload_asset(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ext = file.filename.lower().split(".")[-1]
    if ext not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)
    
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件超过100MB")
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    asset = FileAsset(
        filename=stored_name,
        original_name=file.filename,
        file_path=f"/uploads/documents/{stored_name}",
        file_type=ext,
        file_size=len(content),
        uploader_id=current_user.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/assets", response_model=list[FileAssetResponse])
def list_assets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(FileAsset).order_by(FileAsset.created_at.desc()).limit(100).all()
