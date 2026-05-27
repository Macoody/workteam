"""
Pydantic Schemas（API请求/响应模型）
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# === 用户 ===
class UserCreate(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    role: str
    avatar: Optional[str]
    is_active: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# === 项目 ===
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: Optional[datetime]
    task_count: Optional[int] = 0

    class Config:
        from_attributes = True


# === 看板列 ===
class ColumnCreate(BaseModel):
    name: str
    order: int = 0
    color: str = "#667eea"


class ColumnUpdate(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None
    color: Optional[str] = None


class ColumnResponse(BaseModel):
    id: int
    project_id: int
    name: str
    order: int
    color: str
    tasks: List["TaskResponse"] = []

    class Config:
        from_attributes = True


# === 任务 ===
class TaskCreate(BaseModel):
    project_id: int
    column_id: int
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    column_id: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    order: Optional[int] = None


class TaskMove(BaseModel):
    task_id: int
    target_column_id: int
    order: int = 0


class TaskResponse(BaseModel):
    id: int
    project_id: int
    column_id: int
    title: str
    description: Optional[str]
    priority: str
    assignee_id: Optional[int]
    assignee: Optional["UserResponse"] = None
    due_date: Optional[datetime]
    tags: Optional[List[str]] = []
    order: int
    created_at: Optional[datetime]
    attachments: List["AttachmentResponse"] = []

    class Config:
        from_attributes = True


# === 附件 ===
class AttachmentResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    file_type: Optional[str]
    file_size: Optional[int]
    uploaded_by: int
    uploaded_at: Optional[datetime]

    class Config:
        from_attributes = True


# === 评论 ===
class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    user: Optional[UserResponse] = None
    content: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# === 文档 ===
class DocumentCreate(BaseModel):
    title: str
    doc_type: str = "doc"
    content: Optional[str] = ""
    project_id: Optional[int] = None
    folder_id: Optional[int] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class DocumentResponse(BaseModel):
    id: int
    title: str
    doc_type: str
    content: Optional[str]
    project_id: Optional[int]
    creator_id: int
    creator: Optional[UserResponse] = None
    is_public: bool
    share_mode: Optional[str]
    view_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# === 文件资产 ===
class FileAssetResponse(BaseModel):
    id: int
    filename: str
    original_name: Optional[str]
    file_path: str
    file_type: Optional[str]
    file_size: Optional[int]
    uploader_id: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# === 文件夹 ===
class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class FolderResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    owner_id: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# 前向引用
ColumnResponse.model_rebuild()
TaskResponse.model_rebuild()