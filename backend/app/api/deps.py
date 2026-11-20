from __future__ import annotations

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.core.errors import not_found
from app.services.auth_service import CurrentUser, authenticate
from app.services.pending_store import PendingStore, get_pending_store


def own_account(request: Request) -> None:
    if "customer_id" in request.query_params or "customerId" in request.query_params:
        raise not_found()


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
