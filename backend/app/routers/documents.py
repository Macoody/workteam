"""
文档中心路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
import os
import uuid
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.database import get_db
from app.core.timezone import business_now, to_business_time
from app.models.models import (
    User, Document, DocumentActivityLog, Folder, FileAsset, ROLE_ADMIN, normalize_role
)
from app.schemas.schemas import (
    DocumentActivityResponse, DocumentCreate, DocumentUpdate, DocumentResponse,
    FolderCreate, FolderResponse, FileAssetResponse
)
from app.routers.auth import (
    build_user_response,
    get_current_user,
    require_admin,
    _update_last_active_time,
)

router = APIRouter()
UPLOAD_DIR = os.path.join(settings.UPLOAD_DIR, "documents")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_DOC_TYPES = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "png", "jpg", "jpeg", "gif", "zip", "rar"]
DOCUMENT_ACTION_CREATE = "create"
DOCUMENT_ACTION_VIEW = "view"
DOCUMENT_ACTION_EDIT = "edit"
DOCUMENT_VIEW_GROUP_WINDOW = timedelta(hours=12)


# === 文档 CRUD ===
def document_query(db: Session):
    return db.query(Document).options(
        joinedload(Document.creator),
        joinedload(Document.last_editor),
    )


def timestamp_close(left, right) -> bool:
    if not left or not right:
        return False
    left = to_business_time(left)
    right = to_business_time(right)
    return abs((left - right).total_seconds()) < 1


def build_document_response(doc: Document):
    item = DocumentResponse.model_validate(doc)
    item.creator = build_user_response(doc.creator) if doc.creator else None
    item.last_editor = build_user_response(doc.last_editor) if doc.last_editor else None
    item.created_at = to_business_time(doc.created_at)
    item.updated_at = to_business_time(doc.updated_at)
    item.last_edited_at = to_business_time(doc.last_edited_at)
    return item


def build_activity_response(activity: DocumentActivityLog):
    item = DocumentActivityResponse.model_validate(activity)
    item.user = build_user_response(activity.user) if activity.user else None
    item.created_at = to_business_time(activity.created_at)
    return item


def build_folder_response(folder: Folder):
    item = FolderResponse.model_validate(folder)
    item.created_at = to_business_time(folder.created_at)
    return item


def build_file_asset_response(asset: FileAsset):
    item = FileAssetResponse.model_validate(asset)
    item.created_at = to_business_time(asset.created_at)
    return item


def build_compact_activity_responses(activities: list[DocumentActivityLog]):
    compacted = []
    view_groups_by_user: dict[int, list[dict]] = {}

    for activity in activities:
        if activity.action != DOCUMENT_ACTION_VIEW:
            compacted.append(build_activity_response(activity))
            continue

        created_at = to_business_time(activity.created_at)
        user_groups = view_groups_by_user.setdefault(activity.user_id, [])
        current_group = user_groups[-1] if user_groups else None
        if (
            current_group
            and created_at
            and current_group["latest_at"]
            and current_group["latest_at"] - created_at <= DOCUMENT_VIEW_GROUP_WINDOW
        ):
            current_group["read_count"] += 1
            current_group["response"].read_count = current_group["read_count"]
            continue

        response = build_activity_response(activity)
        response.read_count = 1
        user_groups.append(
            {
                "latest_at": created_at,
                "read_count": 1,
                "response": response,
            }
        )
        compacted.append(response)

    return compacted


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
        created_at=created_at or business_now(),
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
            doc.created_at or doc.last_edited_at or business_now(),
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
    q: str | None = Query(None, max_length=100),
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
    keyword = q.strip() if q else ""
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                Document.title.ilike(pattern),
                func.coalesce(Document.content, "").ilike(pattern),
            )
        )
    docs = query.order_by(
        Document.last_edited_at.desc(),
        Document.updated_at.desc(),
        Document.created_at.desc(),
    ).limit(100).all()
    return [build_document_response(doc) for doc in docs]


@router.post("", response_model=DocumentResponse)
def create_document(data: DocumentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="文档标题不能为空")
    now = business_now()
    doc = Document(
        title=title,
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
    return build_compact_activity_responses(activities)


@router.put("/{doc_id}", response_model=DocumentResponse)
def update_document(doc_id: int, data: DocumentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = document_query(db).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 所有人可编辑任意文档（管理员可编辑全部）
    edited = False
    if data.title is not None:
        title = data.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="文档标题不能为空")
        if title != doc.title:
            doc.title = title
            edited = True
    if data.content is not None and data.content != doc.content:
        doc.content = data.content
        edited = True
    if edited:
        ensure_document_activity_seed(db, doc)
        now = business_now()
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
    
    doc.is_public = True
    doc.share_token = secrets.token_urlsafe(32)
    doc.share_mode = mode
    doc.share_expire = business_now() + timedelta(hours=expire_hours)
    db.commit()
    
    share_url = f"/api/documents/shared/{doc.share_token}"
    return {"share_url": share_url, "share_token": doc.share_token, "mode": mode, "expire_hours": expire_hours}


@router.get("/shared/{token}")
def view_shared_document(token: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.share_token == token).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或链接已失效")
    if doc.share_expire and to_business_time(doc.share_expire) < business_now():
        raise HTTPException(status_code=410, detail="分享链接已过期")
    return build_document_response(doc)


# === 文件夹 ===
@router.get("/folders/all", response_model=list[FolderResponse])
def list_folders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    folders = db.query(Folder).filter(Folder.owner_id == current_user.id).all()
    return [build_folder_response(folder) for folder in folders]


@router.post("/folders", response_model=FolderResponse)
def create_folder(data: FolderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    folder = Folder(name=data.name, parent_id=data.parent_id, owner_id=current_user.id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return build_folder_response(folder)


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
    return build_file_asset_response(asset)


@router.get("/assets", response_model=list[FileAssetResponse])
def list_assets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assets = db.query(FileAsset).order_by(FileAsset.created_at.desc()).limit(100).all()
    return [build_file_asset_response(asset) for asset in assets]
