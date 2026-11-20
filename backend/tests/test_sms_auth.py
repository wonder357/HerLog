import pytest

from app.core.config import settings
from app.services import sms_service
from tests.conftest import auth_headers, register_and_login

AUTH = "/api/v1/c/auth"
PHONE = "19900000001"
PASSWORD = "proof-pass-2026"


@pytest.fixture
def demo(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(settings, "HERLOG_SMS_MODE", "demo")
    monkeypatch.setattr(sms_service, "_demo_allowed", lambda request: True)
    monkeypatch.setattr(sms_service, "_demo_store", sms_service.DemoStore(lambda: clock[0]))
    return clock


def issue(client, purpose, phone=PHONE, *, headers=None):
    path = "/phone-binding/code" if purpose == "bind" else "/sms-code"
    body = {"phone": phone}
    if purpose != "bind":
        body["purpose"] = purpose
    response = client.post(AUTH + path, json=body, headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    data = response.json()["data"]
    return {"phone": phone, "challenge_id": data["challenge_id"], "code": data["demo_code"]}


def test_phone_registration_then_password_and_sms_login_keep_the_same_account(client, demo):
    registration = issue(client, "register", "+86 " + PHONE)
    assert client.post(AUTH + "/phone-login", json=registration).status_code == 422
    registered = client.post(AUTH + "/phone-register", json={
        **registration, "username": "phone_member", "password": PASSWORD,
    })
    assert registered.status_code == 200, registered.text
    member = registered.json()["data"]
    assert member["verified_phone_hint"] == "199****0001"
    assert member["phone"] is None
    headers = auth_headers(member)
    profile = client.get("/api/v1/c/herlog/profile", headers=headers).json()["data"]
    assert profile["contact_phone"] is None
    assert "verified_phone" not in profile
    assert client.post(AUTH + "/phone-register", json={
        **registration, "username": "second_member", "password": PASSWORD,
    }).status_code == 422
    assert client.post(AUTH + "/username-login", json={
        "username": "phone_member", "password": PASSWORD,
    }).json()["data"]["customer_id"] == member["customer_id"]
    demo[0] += 61
    challenge = issue(client, "login")
    login = client.post(AUTH + "/phone-login", json=challenge)
    assert login.status_code == 200, login.text
    assert login.json()["data"]["customer_id"] == member["customer_id"]
    assert client.post(AUTH + "/phone-login", json=challenge).status_code == 422
    demo[0] += 61
    duplicate = client.post(AUTH + "/phone-register", json={
        **issue(client, "register"), "username": "second_member", "password": PASSWORD,
    })
    assert duplicate.status_code == 409


def test_code_resend_attempts_and_expiry(client, demo):
    first = issue(client, "login")
    blocked = client.post(AUTH + "/sms-code", json={"phone": PHONE, "purpose": "register"})
    assert blocked.status_code == 429
    assert blocked.json()["data"]["retry_after"] == 60
    assert client.post(AUTH + "/sms-code", json={"phone": "13800000001", "purpose": "login"}).status_code == 422
    demo[0] += 61
    second = issue(client, "login")
    assert first["challenge_id"] != second["challenge_id"]
    assert client.post(AUTH + "/phone-login", json=first).status_code == 422
    wrong = "000000" if second["code"] != "000000" else "111111"
    for _ in range(sms_service.MAX_ATTEMPTS):
        assert client.post(AUTH + "/phone-login", json={**second, "code": wrong}).status_code == 422
    assert client.post(AUTH + "/phone-login", json=second).status_code == 422
    demo[0] += 61
    third = issue(client, "login")
    demo[0] += sms_service.CODE_TTL
    assert client.post(AUTH + "/phone-login", json=third).status_code == 422


def test_binding_is_owned_and_contact_phone_is_not_a_login_identity(client, demo):
    owner = register_and_login(client, username="sms_owner", password=PASSWORD)
    other = register_and_login(client, username="sms_other", password=PASSWORD)
    owner_auth, other_auth = auth_headers(owner), auth_headers(other)
    assert client.put("/api/v1/c/herlog/profile", json={"contact_phone": PHONE}, headers=other_auth).status_code == 200
    assert client.post(AUTH + "/phone-login", json=issue(client, "login")).status_code == 401
    demo[0] += 61
    assert client.post(AUTH + "/phone-binding/code", json={"phone": PHONE}).status_code == 401
    proof = issue(client, "bind", headers=owner_auth)
    payload = {**proof, "password": PASSWORD}
    assert client.post(AUTH + "/phone-binding", json=payload, headers=other_auth).status_code == 422
    assert client.post(AUTH + "/phone-binding", json={**payload, "password": "wrong-pass"}, headers=owner_auth).status_code == 422
    assert client.post(AUTH + "/phone-binding", json=payload, headers=owner_auth).status_code == 422
    demo[0] += 61
    bound = client.post(AUTH + "/phone-binding", json={
        **issue(client, "bind", headers=owner_auth), "password": PASSWORD,
    }, headers=owner_auth)
    assert bound.status_code == 200, bound.text
    assert bound.json()["data"]["verified_phone_hint"] == "199****0001"
    assert client.get(AUTH + "/me", headers=other_auth).json()["data"]["verified_phone_hint"] is None
    demo[0] += 61
    logged = client.post(AUTH + "/phone-login", json=issue(client, "login"))
    assert logged.json()["data"]["customer_id"] == owner["customer_id"]


def test_live_configuration_requires_phone_and_demo_is_not_visible_remotely(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_SMS_MODE", "demo")
    monkeypatch.setattr(settings, "ENV", "contest")
    assert client.get(AUTH + "/options").json()["data"]["sms_mode"] == "disabled"
    assert client.post(AUTH + "/sms-code", json={"phone": PHONE, "purpose": "login"}).status_code == 503
    monkeypatch.setattr(settings, "HERLOG_SMS_MODE", "aliyun")
    monkeypatch.setattr(settings, "REDIS_ENABLED", False)
    assert client.get(AUTH + "/options").json()["data"] == {"sms_mode": "disabled", "requires_phone": True}
    assert client.post(AUTH + "/username-register", json={"username": "without_phone", "password": PASSWORD}).status_code == 403
