from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_and_login


def test_register_returns_username_and_has_no_phone(client: TestClient) -> None:
    response = client.post(
        "/api/v1/c/auth/username-register", json={"username": "  lily  ", "password": "secret123"}
    )
    assert response.status_code == 200
    assert response.json() == {"code": 200, "message": "success", "data": {"username": "lily"}}


def test_duplicate_username_is_rejected(client: TestClient) -> None:
    body = {"username": "lily", "password": "secret123"}
    assert client.post("/api/v1/c/auth/username-register", json=body).status_code == 200
    second = client.post("/api/v1/c/auth/username-register", json=body)
    assert second.status_code == 409
    assert second.json()["message"] == "该用户名已被注册"


def test_username_is_case_sensitive(client: TestClient) -> None:
    assert (
        client.post(
            "/api/v1/c/auth/username-register", json={"username": "Lily", "password": "secret123"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/c/auth/username-register", json={"username": "lily", "password": "secret123"}
        ).status_code
        == 200
    )


def test_login_returns_session_and_member_without_phone(client: TestClient) -> None:
    data = register_and_login(client)
    assert data["username"] == "lily"
    assert data["name"] == "lily"
    assert data["phone"] is None
    assert len(data["customer_id"]) == 32
    assert data["session_id"] == data["token"]


def test_wrong_password_and_unknown_user_share_one_message(client: TestClient) -> None:
    register_and_login(client)
    wrong = client.post(
        "/api/v1/c/auth/username-login", json={"username": "lily", "password": "wrongpass"}
    )
    unknown = client.post(
        "/api/v1/c/auth/username-login", json={"username": "nobody", "password": "secret123"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["message"] == unknown.json()["message"] == "用户名或密码错误"


def test_short_password_is_rejected_on_register(client: TestClient) -> None:
    response = client.post(
        "/api/v1/c/auth/username-register", json={"username": "lily", "password": "short"}
    )
    assert response.status_code == 422
    assert "密码至少 8 位" in response.json()["message"]


def test_me_refresh_and_logout(client: TestClient) -> None:
    data = register_and_login(client)
    headers = auth_headers(data)
    me = client.get("/api/v1/c/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "lily"

    assert client.post("/api/v1/c/auth/logout", headers=headers).status_code == 200
    after_logout = client.get("/api/v1/c/auth/me", headers=headers)
    assert after_logout.status_code == 401


def test_business_routes_require_token(client: TestClient) -> None:
    assert client.get("/api/v1/c/herlog/profile").status_code == 401
    assert client.get("/api/v1/c/herlog/weights").status_code == 401
    assert client.post("/api/v1/c/herlog/assistant/query", json={"question": "体重"}).status_code == 401


def test_health_endpoint_reports_dependencies(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["env"] in {"local", "contest"}
    assert "mysql" in body and "redis" in body
