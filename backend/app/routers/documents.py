"""
文档中心路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
import os
import uuid

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User, Document, Folder, FileAsset, UserRole
from app.schemas.schemas import DocumentCreate, DocumentUpdate, DocumentResponse, FolderCreate, FolderResponse, FileAssetResponse
from app.routers.auth import get_current_user, require_admin

router = APIRouter()
UPLOAD_DIR = os.path.join(settings.UPLOAD_DIR, "documents")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_DOC_TYPES = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "png", "jpg", "jpeg", "gif", "zip", "rar"]


# === 文档 CRUD ===
@router.get("", response_model=list[DocumentResponse])
def list_documents(
    folder_id: int = None,
    project_id: int = None,
    my_docs: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Document)
    if folder_id is not None:
        query = query.filter(Document.folder_id == folder_id)
    if project_id:
        query = query.filter(Document.project_id == project_id)
    if my_docs:
        query = query.filter(Document.creator_id == current_user.id)
    return query.order_by(Document.updated_at.desc()).limit(100).all()


@router.post("", response_model=DocumentResponse)
def create_document(data: DocumentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = Document(
        title=data.title,
        content=data.content or "",
        doc_type=data.doc_type,
        project_id=data.project_id,
        folder_id=data.folder_id,
        creator_id=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    doc.view_count = (doc.view_count or 0) + 1
    db.commit()
    return doc


@router.put("/{doc_id}", response_model=DocumentResponse)
def update_document(doc_id: int, data: DocumentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 非创建者需检查权限
    if doc.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="无编辑权限")
    
    if data.title is not None:
        doc.title = data.title
    if data.content is not None:
        doc.content = data.content
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if doc.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="无删除权限")
    db.delete(doc)
    db.commit()
    return {"ok": True}


# === 外链分享 ===
@router.post("/{doc_id}/share")
def share_document(doc_id: int, mode: str = "readonly", expire_hours: int = 72, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if doc.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
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