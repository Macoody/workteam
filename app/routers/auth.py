"""
认证路由
"""
import os
import hashlib
import base64
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import get_db
from app.core.timezone import business_now, to_business_time
from app.models.models import User, normalize_role, ROLE_ADMIN
from app.schemas.schemas import (
    PresenceHeartbeatRequest,
    UserCreate,
    UserManageCreate,
    UserManageUpdate,
    UserResponse,
    TokenResponse,
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
ONLINE_TIMEOUT_SECONDS = 90


def _naive(value: datetime | None):
    return to_business_time(value)


def _clean_section(value: str | None):
    value = (value or "").strip()
    return value[:100] or None


def _mark_online(db: Session, user: User, commit: bool = True, current_section: str | None = None):
    now = business_now()
    section = _clean_section(current_section)
    user.is_online = True
    user.last_visit_time = now
    user.last_active_time = now
    if section and section != user.current_section:
        user.previous_section = user.current_section
        user.current_section = section
    if commit:
        db.commit()
        db.refresh(user)
    return user


def _mark_offline(db: Session, user: User, commit: bool = True):
    now = business_now()
    user.is_online = False
    user.last_offline_time = now
    if commit:
        db.commit()
        db.refresh(user)
    return user


def _normalize_presence(user: User, now: datetime | None = None) -> bool:
    now = now or business_now()
    if not user.is_online:
        return False
    last_active = _naive(user.last_active_time)
    if last_active and (now - last_active).total_seconds() <= ONLINE_TIMEOUT_SECONDS:
        return False
    user.is_online = False
    user.last_offline_time = (
        last_active + timedelta(seconds=ONLINE_TIMEOUT_SECONDS)
        if user.last_active_time
        else now
    )
    return True


def _update_last_active_time(db: Session, user: User):
    """更新用户最后活跃时间（本地时区）"""
    _mark_online(db, user)


def build_user_response(user: User):
    item = UserResponse.model_validate(user)
    item.created_at = to_business_time(user.created_at)
    item.last_visit_time = to_business_time(user.last_visit_time)
    item.last_active_time = to_business_time(user.last_active_time)
    item.last_offline_time = to_business_time(user.last_offline_time)
    return item


def _clean_optional(value: str | None):
    if value is None:
        return None
    value = value.strip()
    return value or None


def _clean_username(value: str | None):
    value = (value or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    return value


def _clean_color(value: str | None):
    value = (value or "").strip()
    return value or "#93c5fd"


def _pbkdf2_hash(password: str, salt: bytes, rounds: int = 600000) -> str:
    """Generate pbkdf2_sha256 hash"""
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, rounds)
    hash_b64 = base64.b64encode(dk).decode('ascii')
    salt_b64 = base64.b64encode(salt).decode('ascii')
    return f"$pbkdf2-sha256${rounds}${salt_b64}${hash_b64}"


def _pbkdf2_verify(password: str, hashed: str) -> bool:
    """Verify pbkdf2_sha256 hash"""
    try:
        parts = hashed.split('$')
        # Format: $pbkdf2-sha256$rounds$salt_b64$hash_b64
        if len(parts) != 5:
            return False
        rounds = int(parts[2])
        salt_b64 = parts[3]
        hash_b64 = parts[4]
        salt = base64.b64decode(salt_b64)
        expected = _pbkdf2_hash(password, salt, rounds)
        return hashed == expected
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """New password hash - always pbkdf2_sha256"""
    salt = os.urandom(16)
    return _pbkdf2_hash(password, salt)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password"""
    if hashed.startswith("$pbkdf2"):
        return _pbkdf2_verify(plain, hashed)
    return False


def migrate_password_hash(user: User, plain_password: str, hashed: str, db: Session) -> bool:
    """Migrate old sha256_crypt hash to new pbkdf2_sha256"""
    if not hashed.startswith("$5$rounds="):
        return False
    import crypt
    if crypt.crypt(plain_password, hashed) != hashed:
        return False
    # Migration successful - update to new hash
    user.password_hash = get_password_hash(plain_password)
    db.commit()
    return True


def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="无效的认证信息")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    # 更新访问和在线状态（最多每 60 秒写一次，避免普通接口频繁写库）
    now = business_now()
    last_visit_time = _naive(user.last_visit_time)
    if not user.is_online or user.last_visit_time is None or (now - last_visit_time).total_seconds() > 60:
        user.is_online = True
        user.last_visit_time = now
        user.last_active_time = now
        db.commit()
    return user


def require_admin(current_user: User = Depends(get_current_user)):
    if normalize_role(current_user.role) != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


@router.post("/register", response_model=TokenResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
    username = _clean_username(data.username)
    phone = _clean_optional(data.phone)
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="用户名已存在")
        if phone and db.query(User).filter(User.phone == phone, User.id != existing.id).first():
            raise HTTPException(status_code=400, detail="手机号已存在")
        # 被删掉的账号：重置密码+重新激活
        existing.password_hash = get_password_hash(data.password)
        existing.is_active = True
        existing.phone = phone
        db.commit()
        db.refresh(existing)
        access_token = create_access_token(data={"sub": str(existing.id)})
        return TokenResponse(
            access_token=access_token,
            user=build_user_response(existing)
        )
    user = User(
        username=username,
        password_hash=get_password_hash(data.password),
        display_name=data.display_name or username,
        phone=phone,
        role="member",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        user=build_user_response(user)
    )


@router.post("/login", response_model=TokenResponse)
def login(data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    username = _clean_username(data.username)
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    password_ok = False
    if user.password_hash.startswith("$pbkdf2"):
        password_ok = verify_password(data.password, user.password_hash)
    elif user.password_hash.startswith("$5$rounds="):
        password_ok = migrate_password_hash(user, data.password, user.password_hash, db)
        if password_ok:
            db.refresh(user)
    
    if not password_ok:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    _mark_online(db, user, commit=True)

    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        user=build_user_response(user)
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return build_user_response(current_user)


@router.post("/presence/heartbeat", response_model=UserResponse)
def presence_heartbeat(
    data: PresenceHeartbeatRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return build_user_response(_mark_online(db, current_user, current_section=data.current_section if data else None))


@router.post("/presence/offline")
def presence_offline(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _mark_offline(db, current_user)
    return {"ok": True, "last_offline_time": to_business_time(current_user.last_offline_time)}


@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.created_at.desc()).all()
    now = business_now()
    changed = any(_normalize_presence(user, now) for user in users)
    if changed:
        db.commit()
        for user in users:
            db.refresh(user)
    return [build_user_response(user) for user in users]


@router.post("/users", response_model=UserResponse)
def create_user(data: UserManageCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    username = _clean_username(data.username)
    phone = _clean_optional(data.phone)
    color = _clean_color(data.color)

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if phone and db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="手机号已存在")

    try:
        role = normalize_role(data.role) or "member"
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的角色")

    user = User(
        username=username,
        password_hash=get_password_hash(data.password),
        display_name=data.display_name or username,
        phone=phone,
        role=role,
        color=color,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return build_user_response(user)


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserManageUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=404, detail="用户已停用")

    phone = _clean_optional(data.phone)
    color = _clean_color(data.color) if data.color is not None else None

    if phone:
        exists_phone = db.query(User).filter(User.phone == phone, User.id != user_id).first()
        if exists_phone:
            raise HTTPException(status_code=400, detail="手机号已存在")

    if data.role is not None:
        try:
            user.role = normalize_role(data.role) or "member"
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的角色")

    if data.display_name is not None:
        user.display_name = data.display_name
    if data.phone is not None:
        user.phone = phone
    if data.password:
        user.password_hash = get_password_hash(data.password)
    if data.color is not None:
        user.color = color

    db.commit()
    db.refresh(user)
    return build_user_response(user)


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=404, detail="用户已停用")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")

    user.is_active = False
    db.commit()
    return {"ok": True}


@router.put("/users/{user_id}/role")
def update_user_role(user_id: int, role: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    try:
        user.role = normalize_role(role) or "member"
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的角色")
    db.commit()
    return {"ok": True}
