from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  注册全部比赛表
from app.api.deps import pending_store
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.services.pending_store import MemoryPendingStore


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    store = MemoryPendingStore(3)

    def override_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[pending_store] = lambda: store
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def register_and_login(client: TestClient, username: str = "lily", password: str = "secret123") -> dict:
    registered = client.post(
        "/api/v1/c/auth/username-register", json={"username": username, "password": password}
    )
    assert registered.status_code == 200, registered.text
    logged_in = client.post(
        "/api/v1/c/auth/username-login", json={"username": username, "password": password}
    )
    assert logged_in.status_code == 200, logged_in.text
    return logged_in.json()["data"]


def auth_headers(session_data: dict) -> dict:
    return {"token": session_data["token"]}
