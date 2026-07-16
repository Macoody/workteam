"""
Pydantic Schemas（API请求/响应模型）
"""
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List


# === 用户 ===
class UserCreate(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    phone: Optional[str] = None


class UserManageCreate(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "member"
    color: str = "#93c5fd"


class UserManageUpdate(BaseModel):
    display_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    color: Optional[str] = None


class PresenceHeartbeatRequest(BaseModel):
    current_section: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    phone: Optional[str]
    role: str
    color: Optional[str]
    avatar: Optional[str]
    is_active: bool
    is_online: bool = False
    created_at: Optional[datetime]
    last_visit_time: Optional[datetime]
    last_active_time: Optional[datetime]
    last_offline_time: Optional[datetime]
    current_section: Optional[str] = None
    previous_section: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class WechatLoginRequest(BaseModel):
    code: Optional[str] = None
    dev_openid: Optional[str] = None


class WechatBindRequest(WechatLoginRequest):
    username: str
    password: str


class WechatLoginResponse(BaseModel):
    bound: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[UserResponse] = None
    message: Optional[str] = None


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
    pending_count: Optional[int] = 0
    in_progress_count: Optional[int] = 0
    review_count: Optional[int] = 0
    done_count: Optional[int] = 0

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
    node_output: Optional[str] = None
    linked_document_id: Optional[int] = None
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None
    delivery_dates: Optional[List[datetime]] = None
    tags: Optional[List[str]] = None


class TaskUpdate(BaseModel):
    project_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    node_output: Optional[str] = None
    linked_document_id: Optional[int] = None
    assignee_id: Optional[int] = None
    column_id: Optional[int] = None
    due_date: Optional[datetime] = None
    delivery_dates: Optional[List[datetime]] = None
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
    column_name: Optional[str] = None
    column_color: Optional[str] = None
    title: str
    description: Optional[str]
    node_output: Optional[str]
    linked_document_id: Optional[int]
    assignee_id: Optional[int]
    assignee: Optional["UserResponse"] = None
    due_date: Optional[datetime]
    delivery_dates: Optional[List[datetime]] = []
    completed_by: Optional[List[str]] = []
    completed_at: Optional[datetime] = None
    tags: Optional[List[str]] = []
    recurrence_rule_id: Optional[int] = None
    recurrence_occurrence_date: Optional[date] = None
    order: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime] = None
    attachments: List["AttachmentResponse"] = []
    recent_comments: List["CommentResponse"] = []

    class Config:
        from_attributes = True


class RecurringTaskRuleCreate(BaseModel):
    project_id: int
    column_id: int
    title: str
    description: Optional[str] = None
    node_output: Optional[str] = None
    linked_document_id: Optional[int] = None
    assignee_id: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    due_time: Optional[str] = None


class RecurringTaskRuleResponse(BaseModel):
    id: int
    project_id: int
    column_id: Optional[int]
    title: str
    description: Optional[str]
    node_output: Optional[str]
    linked_document_id: Optional[int]
    assignee_id: Optional[int]
    assignee: Optional[UserResponse] = None
    recurrence_type: str
    start_date: date
    end_date: Optional[date]
    due_time: Optional[str]
    is_active: bool
    created_by: Optional[int]
    last_generated_date: Optional[date]
    created_at: Optional[datetime]

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


class MentionNotificationResponse(BaseModel):
    id: int
    comment_id: int
    task_id: int
    project_id: int
    task_title: str
    project_name: Optional[str] = None
    comment_content: str
    mentioned_by: Optional[UserResponse] = None
    created_at: Optional[datetime]
    is_read: bool


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
    last_editor_id: Optional[int] = None
    last_editor: Optional[UserResponse] = None
    last_edited_at: Optional[datetime] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentActivityResponse(BaseModel):
    id: int
    document_id: int
    user_id: int
    user: Optional[UserResponse] = None
    action: str
    created_at: Optional[datetime]
    read_count: int = 1

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


# === 工作日志 ===
class WorkLogCreate(BaseModel):
    log_date: datetime
    content: str


class WorkLogUpdate(BaseModel):
    log_date: Optional[datetime] = None
    content: Optional[str] = None


class WorkLogResponse(BaseModel):
    id: int
    user_id: int
    log_date: datetime
    content: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


# === 数字员工 ===
class DigitalCustomerSummary(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    device_number: Optional[str] = None

    class Config:
        from_attributes = True


class DigitalPhoneSummary(BaseModel):
    id: int
    model: str
    memory: str
    serial_number: Optional[str] = None
    activation_code: Optional[str] = None
    status: str
    bound_phone: Optional[str] = None

    class Config:
        from_attributes = True


class DigitalPhoneBase(BaseModel):
    model: str
    memory: str
    serial_number: Optional[str] = None
    activation_code: Optional[str] = None
    condition: str = "new"
    color: Optional[str] = None
    status: str = "in_stock"
    holder_id: Optional[int] = None
    customer_id: Optional[int] = None
    bound_phone: Optional[str] = None
    douyin_account: Optional[str] = None
    xiaohongshu_account: Optional[str] = None
    wechat_account: Optional[str] = None
    kuaishou_account: Optional[str] = None
    notes: Optional[str] = None


class DigitalPhoneCreate(DigitalPhoneBase):
    pass


class DigitalPhoneUpdate(BaseModel):
    model: Optional[str] = None
    memory: Optional[str] = None
    serial_number: Optional[str] = None
    activation_code: Optional[str] = None
    condition: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None
    holder_id: Optional[int] = None
    customer_id: Optional[int] = None
    bound_phone: Optional[str] = None
    douyin_account: Optional[str] = None
    xiaohongshu_account: Optional[str] = None
    wechat_account: Optional[str] = None
    kuaishou_account: Optional[str] = None
    notes: Optional[str] = None


class DigitalPhoneResponse(DigitalPhoneBase):
    id: int
    holder: Optional[UserResponse] = None
    customer: Optional[DigitalCustomerSummary] = None
    creator: Optional[UserResponse] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DigitalCustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    wechat: Optional[str] = None
    device_number: Optional[str] = None
    source: Optional[str] = None
    payment_amount: Optional[str] = None
    payment_method: Optional[str] = None
    payment_status: str = "unpaid"
    payment_note: Optional[str] = None
    service_start_at: Optional[datetime] = None
    service_end_at: Optional[datetime] = None
    notes: Optional[str] = None


class DigitalCustomerCreate(DigitalCustomerBase):
    phone_ids: Optional[List[int]] = []


class DigitalCustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    wechat: Optional[str] = None
    device_number: Optional[str] = None
    source: Optional[str] = None
    payment_amount: Optional[str] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None
    payment_note: Optional[str] = None
    service_start_at: Optional[datetime] = None
    service_end_at: Optional[datetime] = None
    notes: Optional[str] = None
    phone_ids: Optional[List[int]] = None


class DigitalServiceItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    sort_order: Optional[int] = None


class DigitalServiceItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class DigitalServiceItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    sort_order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DigitalServiceRecordUpdate(BaseModel):
    is_done: bool = False
    notes: Optional[str] = None


class DigitalServiceRecordResponse(BaseModel):
    id: int
    customer_id: int
    service_item_id: int
    service_item: Optional[DigitalServiceItemResponse] = None
    is_done: bool
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    updated_by: Optional[int] = None
    updated_user: Optional[UserResponse] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DigitalCustomerResponse(DigitalCustomerBase):
    id: int
    phones: List[DigitalPhoneSummary] = []
    service_records: List[DigitalServiceRecordResponse] = []
    creator: Optional[UserResponse] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DigitalOverviewResponse(BaseModel):
    total_phones: int = 0
    in_stock_phones: int = 0
    assigned_phones: int = 0
    sold_phones: int = 0
    customers: int = 0
    active_service_items: int = 0
    unfinished_service_records: int = 0
