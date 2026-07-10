"""
微信小程序登录与账号绑定。
"""
import json
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.timezone import business_now
from app.models.models import User
from app.routers.auth import (
    _clean_username,
    _mark_online,
    build_user_response,
    create_access_token,
    migrate_password_hash,
    verify_password,
    get_current_user,
)
from app.schemas.schemas import WechatBindRequest, WechatLoginRequest, WechatLoginResponse

router = APIRouter()


def authenticate_user(db: Session, username: str, password: str) -> User:
    username = _clean_username(username)
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    password_ok = False
    if user.password_hash.startswith("$pbkdf2"):
        password_ok = verify_password(password, user.password_hash)
    elif user.password_hash.startswith("$5$rounds="):
        password_ok = migrate_password_hash(user, password, user.password_hash, db)
        if password_ok:
            db.refresh(user)

    if not password_ok:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return user


def create_login_response(user: User) -> WechatLoginResponse:
    return WechatLoginResponse(
        bound=True,
        access_token=create_access_token(data={"sub": str(user.id)}),
        user=build_user_response(user),
    )


def resolve_wechat_identity(data: WechatLoginRequest) -> tuple[str, str | None]:
    if settings.WECHAT_DEV_LOGIN_ENABLED and data.dev_openid:
        return data.dev_openid.strip(), None

    if not settings.WECHAT_MINI_APP_ID or not settings.WECHAT_MINI_APP_SECRET:
        raise HTTPException(status_code=503, detail="微信小程序 AppID/AppSecret 尚未配置")
    if not data.code:
        raise HTTPException(status_code=400, detail="缺少微信登录 code")

    query = urllib.parse.urlencode(
        {
            "appid": settings.WECHAT_MINI_APP_ID,
            "secret": settings.WECHAT_MINI_APP_SECRET,
            "js_code": data.code,
            "grant_type": "authorization_code",
        }
    )
    url = f"https://api.weixin.qq.com/sns/jscode2session?{query}"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="微信登录服务暂时不可用") from exc

    if payload.get("errcode"):
        raise HTTPException(status_code=400, detail=payload.get("errmsg") or "微信登录失败")
    openid = (payload.get("openid") or "").strip()
    if not openid:
        raise HTTPException(status_code=400, detail="微信登录未返回 openid")
    unionid = (payload.get("unionid") or "").strip() or None
    return openid, unionid


@router.post("/login", response_model=WechatLoginResponse)
def wechat_login(data: WechatLoginRequest, db: Session = Depends(get_db)):
    openid, _unionid = resolve_wechat_identity(data)
    user = db.query(User).filter(User.wechat_openid == openid, User.is_active == True).first()
    if not user:
        return WechatLoginResponse(bound=False, message="微信尚未绑定成员账号")
    _mark_online(db, user, commit=True)
    return create_login_response(user)


@router.post("/bind", response_model=WechatLoginResponse)
def bind_wechat_account(data: WechatBindRequest, db: Session = Depends(get_db)):
    openid, unionid = resolve_wechat_identity(data)
    user = authenticate_user(db, data.username, data.password)

    bound_user = db.query(User).filter(User.wechat_openid == openid).first()
    if bound_user and bound_user.id != user.id:
        raise HTTPException(status_code=400, detail="这个微信已经绑定了其他成员")

    user.wechat_openid = openid
    user.wechat_unionid = unionid
    user.wechat_bound_at = business_now()
    db.commit()
    db.refresh(user)
    _mark_online(db, user, commit=True)
    return create_login_response(user)


@router.post("/unbind")
def unbind_wechat_account(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.wechat_openid = None
    current_user.wechat_unionid = None
    current_user.wechat_bound_at = None
    db.commit()
    return {"ok": True}
