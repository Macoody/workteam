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
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import UserCreate, UserManageCreate, UserManageUpdate, UserResponse, TokenResponse

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _clean_optional(value: str | None):
    if value is None:
        return None
    value = value.strip()
    return value or None


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
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
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
    return user


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


@router.post("/register", response_model=TokenResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="用户名已存在")
        # 被删掉的账号：重置密码+重新激活
        existing.password_hash = get_password_hash(data.password)
        existing.is_active = True
        existing.phone = data.phone
        db.commit()
        db.refresh(existing)
        access_token = create_access_token(data={"sub": str(existing.id)})
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(existing)
        )
    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        display_name=data.display_name or data.username,
        phone=data.phone,
        role=UserRole.MEMBER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
def login(data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username, User.is_active == True).first()
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
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(User).filter(User.is_active == True).order_by(User.created_at.desc()).all()


@router.post("/users", response_model=UserResponse)
def create_user(data: UserManageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    phone = _clean_optional(data.phone)
    color = _clean_color(data.color)

    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if phone and db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="手机号已存在")

    try:
        role = UserRole(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的角色")

    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        display_name=data.display_name or data.username,
        phone=phone,
        role=role,
        color=color,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserManageUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    phone = _clean_optional(data.phone)
    color = _clean_color(data.color) if data.color is not None else None

    if phone:
        exists_phone = db.query(User).filter(User.phone == phone, User.id != user_id).first()
        if exists_phone:
            raise HTTPException(status_code=400, detail="手机号已存在")

    if data.role is not None:
        try:
            user.role = UserRole(data.role)
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
    return user


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
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
        user.role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的角色")
    db.commit()
    return {"ok": True}
