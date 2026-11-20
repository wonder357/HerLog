from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.core.clock import local_today
from tests.conftest import auth_headers, register_and_login
from tests.test_skin import _payload

ROOT = "/api/v1/c/herlog"


def put(client, path, headers, payload):
    return client.put(ROOT + path, headers=headers, json=payload)


def weight(client, headers, amount, moment, key):
    response = client.post(ROOT + "/weights", headers=headers, json={
        "kg": amount, "measured_at": moment, "client_key": "home-test-" + key,
    })
    assert response.status_code == 200, response.text


def test_overview_projects_only_own_month_and_daily_last_weight(client: TestClient, monkeypatch) -> None:
    today = date(2026, 11, 20)
    monkeypatch.setattr("app.services.home_service.local_today", lambda: today)
    monkeypatch.setattr("app.services.cycle_context.local_today", lambda: today)
    monkeypatch.setattr("app.services.period_service.local_today", lambda: today)

    owner_session = register_and_login(client)
    owner = auth_headers(owner_session)
    other = auth_headers(register_and_login(client, username="another"))
    for start, end in (("2026-11-01", "2026-11-04"), ("2026-11-18", "2026-11-20")):
        assert client.post(ROOT + "/periods", headers=owner, json={"start_day": start, "end_day": end}).status_code == 200
    weight(client, owner, 58.2, "2026-11-17T15:59:00Z", "prev")
    weight(client, owner, 58.9, "2026-11-17T16:00:00Z", "early")
    weight(client, owner, 57.1, "2026-11-17T20:00:00Z", "last")
    weight(client, owner, 57.2, "2026-11-17T20:00:00Z", "tie")
    assert put(client, "/feelings/2026-11-18", owner, {"mood": "平静", "note": "不能进入月历"}).status_code == 200
    analyzed = client.post(ROOT + "/skin/analyze", headers=owner, json=_payload()).json()["data"]
    assert client.post(ROOT + "/skin/observations", headers=owner, json={"analysis_id": analyzed["analysis_id"]}).status_code == 200

    path = ROOT + "/overview"
    response = client.get(path, headers=owner, params={"month": "2026-11"})
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    data = response.json()["data"]
    days = {row["day"]: row for row in data["days"]}
    assert days["2026-11-17"]["weight_kg"] == "58.2"
    assert days["2026-11-18"] == {
        "day": "2026-11-18", "weight_kg": "57.2", "skin_observation_count": 1, "feeling_tags": ["平静"]
    }
    assert data["week"]["recorded_days"] == 3
    assert data["today_recorded"]["period"]
    assert data["focus"]["action"] == "review_today"
    assert data["cycle_context"] == client.get(ROOT + "/cycle-context", headers=owner, params={"day": str(today)}).json()["data"]
    assert client.get(path, headers=other, params={"month": "2026-11"}).json()["data"]["days"] == []
    for route in ("/profile", "/overview?month=2026-11"):
        response = client.get(ROOT + route, headers=other, params={"customer_id": owner_session["customer_id"], "month": "2026-11"})
        assert response.status_code == 404
    assert client.get(path, headers=owner, params={"month": "9999-12"}).status_code == 422

    question = client.post(ROOT + "/assistant/query", headers=owner, json={"question": "最近一次经期从哪天开始？"})
    assert "2026-11-18" in question.json()["data"]["answer"]
    assert client.get(path, headers=owner, params={"month": "2026-11"}).json()["data"]["days"] == data["days"]


def test_health_summary_distinguishes_missing_inputs_and_recalculates(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    path = ROOT + "/health-summary"
    def bmi():
        return client.get(path, headers=headers).json()["data"]["bmi"]

    assert bmi()["status"] == "missing_both"
    assert put(client, "/profile", headers, {"height_cm": "0"}).status_code == 422
    assert put(client, "/profile", headers, {"birthday": str(local_today() + timedelta(days=1))}).status_code == 422
    assert put(client, "/profile", headers, {"height_cm": "165", "contact_phone": "12345"}).status_code == 200
    assert bmi()["status"] == "missing_weight"
    moment = f"{local_today() - timedelta(days=1)}T08:00:00+08:00"
    weight(client, headers, 58.2, moment, "bmi-record")
    assert bmi()["value"] == "21.4"
    assert put(client, "/profile", headers, {"height_cm": "170"}).status_code == 200
    assert bmi()["value"] == "20.1"
    assert put(client, "/profile", headers, {"height_cm": None}).status_code == 200
    assert bmi()["status"] == "missing_height"
    assert client.get(ROOT + "/profile", headers=headers).json()["data"]["contact_phone"] == "12345"


def test_preference_and_password_changes_are_account_scoped(client: TestClient) -> None:
    first = register_and_login(client)
    owner = auth_headers(first)
    second = client.post("/api/v1/c/auth/username-login", json={"username": "lily", "password": "secret123"}).json()["data"]
    other = auth_headers(register_and_login(client, username="another"))

    reminder = put(client, "/reminder-settings", owner, {"period_reminder_enabled": True}).json()["data"]
    assert reminder == {"delivery_status": "preference_only", "period_reminder_enabled": True, "record_reminder_enabled": False}
    assert not client.get(ROOT + "/reminder-settings", headers=other).json()["data"]["period_reminder_enabled"]
    assert put(client, "/reminder-settings", owner, {"record_reminder_enabled": None}).status_code == 422
    assert put(client, "/recording-preferences", owner, {"weekly_record_days_target": 3, "show_focus": False}).status_code == 200
    assert put(client, "/recording-preferences", owner, {"target_kg": 56}).status_code == 422
    assert put(client, "/recording-preferences", owner, {"weekly_record_days_target": 8}).status_code == 422
    assert client.get(ROOT + "/recording-preferences", headers=owner).json()["data"]["weekly_record_days_target"] == 3
    assert put(client, "/account/password", owner, {"current_password": "wrong123", "new_password": "updated1234"}).status_code == 422
    assert put(client, "/account/password", owner, {"current_password": "secret123", "new_password": "updated1234"}).status_code == 200
    for session in (owner, auth_headers(second)):
        assert client.get(ROOT + "/profile", headers=session).status_code == 401
    assert client.get(ROOT + "/profile", headers=other).status_code == 200
    assert client.post("/api/v1/c/auth/username-login", json={"username": "lily", "password": "secret123"}).status_code == 401
    assert client.post("/api/v1/c/auth/username-login", json={"username": "lily", "password": "updated1234"}).status_code == 200
