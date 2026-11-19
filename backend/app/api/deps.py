from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services.auth_service import CurrentUser, authenticate
from app.services.pending_store import PendingStore, get_pending_store


def get_token(
    token: str | None = Header(default=None, alias="token"),
    authorization: str | None = Header(default=None),
) -> str | None:
    """沿用请求头 `token`，同时接受 `Authorization: Bearer <token>`。"""

    if token:
        return token.strip() or None
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


def get_current_user(
    session: Session = Depends(get_session),
    token: str | None = Depends(get_token),
) -> CurrentUser:
    return authenticate(session, token)


def pending_store() -> PendingStore:
    return get_pending_store()
