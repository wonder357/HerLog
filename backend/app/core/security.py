from __future__ import annotations

import hashlib
import secrets

import bcrypt

from app.core.errors import invalid, unauthorized


def hash_password(password: str) -> str:
    _check_password(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    if not hashed or len(password.encode("utf-8")) > 72:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("ascii"))
    except ValueError:
        return False


def _check_password(password: str) -> None:
    if len(password) < 8:
        raise invalid("密码至少 8 位")
    if len(password.encode("utf-8")) > 72:
        raise invalid("密码过长，UTF-8 编码后不能超过 72 字节")


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_password(password: str) -> str:
    """登录入口的密码长度检查不区分“格式不对”和“密码错误”，统一返回 401。"""

    if not password or len(password.encode("utf-8")) > 72:
        raise unauthorized("用户名或密码错误")
    return password
