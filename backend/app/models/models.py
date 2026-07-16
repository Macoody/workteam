"""
数据库模型

注意：
- 角色字段统一为小写字符串（'admin' / 'member' / 'guest'），不再使用 SQLAlchemy Enum，
  这是为了兼容 PG（避免强类型 ENUM 在做表结构迁移时的麻烦）以及兼容 MySQL 老数据
  （历史库中可能存在 'ADMIN' / 'MEMBER' 大写值，应用层在 UserRole 转换处做了大小写兜底）。
- 时间字段统一为带时区（TIMESTAMP WITH TIME ZONE）。
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    ForeignKey,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.timezone import business_now


# 角色常量
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
ROLE_GUEST = "guest"
VALID_ROLES = {ROLE_ADMIN, ROLE_MEMBER, ROLE_GUEST}


def normalize_role(value):
    """大小写兜底：把 'ADMIN' / 'admin' 都转成 'admin'。非法值返回 None。"""
    if value is None:
        return None
    v = str(value).strip().lower()
    return v if v in VALID_ROLES else None


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    phone = Column(String(20), unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default=ROLE_MEMBER)
    display_name = Column(String(100))
    color = Column(String(20), default="#93c5fd")
    avatar = Column(String(500))
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    last_visit_time = Column(DateTime(timezone=True), nullable=True)
    last_active_time = Column(DateTime(timezone=True), nullable=True)
    last_offline_time = Column(DateTime(timezone=True), nullable=True)
    current_section = Column(String(100), nullable=True)
    previous_section = Column(String(100), nullable=True)
    wechat_openid = Column(String(100), unique=True, index=True)
    wechat_unionid = Column(String(100), index=True)
    wechat_bound_at = Column(DateTime(timezone=True), nullable=True)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=business_now)

    owner = relationship("User")
    columns = relationship(
        "TaskColumn",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="TaskColumn.order",
    )
    tasks = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )


class TaskColumn(Base):
    __tablename__ = "task_columns"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100), nullable=False)
    order = Column(Integer, default=0)
    color = Column(String(20), default="#667eea")

    project = relationship("Project", back_populates="columns")
    tasks = relationship("Task", back_populates="column")


class RecurringTaskRule(Base):
    __tablename__ = "recurring_task_rules"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    column_id = Column(Integer, ForeignKey("task_columns.id", ondelete="SET NULL"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    node_output = Column(Text)
    linked_document_id = Column(Integer)
    assignee_id = Column(Integer, ForeignKey("users.id"))
    recurrence_type = Column(String(20), default="daily")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    due_time = Column(String(5))
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    last_generated_date = Column(Date)
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=business_now)

    project = relationship("Project")
    column = relationship("TaskColumn")
    assignee = relationship("User", foreign_keys=[assignee_id])
    creator = relationship("User", foreign_keys=[created_by])


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    column_id = Column(
        Integer,
        ForeignKey("task_columns.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(500), nullable=False)
    description = Column(Text)
    priority = Column(String(20), default="medium")
    node_output = Column(Text)
    linked_document_id = Column(Integer)
    assignee_id = Column(Integer, ForeignKey("users.id"))
    due_date = Column(DateTime(timezone=True))
    delivery_dates = Column(Text)
    completed_by = Column(Text)
    completed_at = Column(DateTime(timezone=True))
    tags = Column(Text)
    recurrence_rule_id = Column(Integer, ForeignKey("recurring_task_rules.id"))
    recurrence_occurrence_date = Column(Date)
    order = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=business_now)

    project = relationship("Project", back_populates="tasks")
    column = relationship("TaskColumn", back_populates="tasks")
    assignee = relationship("User")
    recurrence_rule = relationship("RecurringTaskRule")
    attachments = relationship(
        "Attachment", back_populates="task", cascade="all, delete-orphan"
    )
    comments = relationship(
        "Comment", back_populates="task", cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())

    task = relationship("Task", back_populates="attachments")
    uploader = relationship("User")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=business_now)

    task = relationship("Task", back_populates="comments")
    user = relationship("User")


class CommentMention(Base):
    __tablename__ = "comment_mentions"

    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    doc_type = Column(String(50))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    creator_id = Column(Integer, ForeignKey("users.id"))
    folder_id = Column(Integer, ForeignKey("folders.id"))
    is_public = Column(Boolean, default=False)
    share_token = Column(String(100))
    share_mode = Column(String(20))
    share_expire = Column(DateTime(timezone=True))
    view_count = Column(Integer, default=0)
    last_editor_id = Column(Integer, ForeignKey("users.id"))
    last_edited_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=business_now)

    creator = relationship("User", foreign_keys=[creator_id])
    last_editor = relationship("User", foreign_keys=[last_editor_id])


class DocumentActivityLog(Base):
    __tablename__ = "document_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=business_now, nullable=False)

    document = relationship("Document")
    user = relationship("User")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("folders.id"))
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())


class FileAsset(Base):
    __tablename__ = "file_assets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255))
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    uploader_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())


class WorkLog(Base):
    __tablename__ = "work_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    log_date = Column(DateTime(timezone=True), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=business_now)

    user = relationship("User")


class DigitalCustomer(Base):
    __tablename__ = "digital_customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    phone = Column(String(30))
    wechat = Column(String(100))
    device_number = Column(String(100))
    source = Column(String(100))
    payment_amount = Column(String(100))
    payment_method = Column(String(100))
    payment_status = Column(String(50), default="unpaid")
    payment_note = Column(Text)
    service_start_at = Column(DateTime(timezone=True))
    service_end_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=business_now)

    creator = relationship("User", foreign_keys=[created_by])
    phones = relationship("DigitalPhone", back_populates="customer")
    service_records = relationship(
        "DigitalServiceRecord",
        back_populates="customer",
        cascade="all, delete-orphan",
    )


class DigitalPhone(Base):
    __tablename__ = "digital_phones"

    id = Column(Integer, primary_key=True, index=True)
    model = Column(String(100), nullable=False)
    memory = Column(String(50), nullable=False)
    serial_number = Column(String(100), unique=True, index=True)
    activation_code = Column(String(100))
    condition = Column("phone_condition", String(20), default="new")
    color = Column(String(50))
    status = Column(String(30), default="in_stock", index=True)
    holder_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    customer_id = Column(Integer, ForeignKey("digital_customers.id", ondelete="SET NULL"))
    bound_phone = Column(String(30))
    douyin_account = Column(String(100))
    xiaohongshu_account = Column(String(100))
    wechat_account = Column(String(100))
    kuaishou_account = Column(String(100))
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=business_now)

    holder = relationship("User", foreign_keys=[holder_id])
    creator = relationship("User", foreign_keys=[created_by])
    customer = relationship("DigitalCustomer", back_populates="phones")


class DigitalServiceItem(Base):
    __tablename__ = "digital_service_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=business_now)


class DigitalServiceRecord(Base):
    __tablename__ = "digital_service_records"
    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "service_item_id",
            name="ux_digital_service_record_customer_item",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(
        Integer,
        ForeignKey("digital_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_item_id = Column(
        Integer,
        ForeignKey("digital_service_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_done = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    updated_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=business_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=business_now)

    customer = relationship("DigitalCustomer", back_populates="service_records")
    service_item = relationship("DigitalServiceItem")
    updated_user = relationship("User")
