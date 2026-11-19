from datetime import date, datetime, timedelta

from app.core.clock import local_today
from app.services import wellness
from tests.conftest import auth_headers, register_and_login
from tests.test_private_photos import photo

ROOT = "/api/v1/c/herlog/exercise"


def test_movement_week_and_journal_use_shanghai_dates(client, monkeypatch):
    monkeypatch.setattr(wellness, "local_today", lambda: date(2026, 11, 20))
    owner = auth_headers(register_and_login(client, username="exercise_journal_owner"))
    other = auth_headers(register_and_login(client, username="exercise_journal_other"))

    def create(key, started_at, code, duration=None, **detail):
        payload = {"client_key": key, "started_at": started_at, "activity_code": code,
                   "duration_minutes": duration, **detail}
        response = client.post(ROOT + "/checkins", headers=owner, json=payload)
        assert response.status_code == 200, response.text
        return response.json()["data"]

    recent = create("exercise-first", "2026-11-13T16:15:00.375Z", "yoga", 20,
                    feeling_code="comfortable", photo=photo())
    create("exercise-outside", "2026-11-13T15:59:00Z", "walk", 15)
    rest = create("exercise-rest", "2026-11-19T16:15:00Z", "rest", feeling_code="tired")
    for offset in range(1, 10):
        time = datetime(2026, 11, 19) - timedelta(days=offset)
        create(f"exercise-page-{offset}", time.isoformat() + "+08:00", "jog", 10)

    week = client.get(ROOT + "/week", headers=owner).json()["data"]
    assert week["days"][0] == {"day": "2026-11-14", "activities": 2, "rests": 0}
    assert week["days"][-1] == {"day": "2026-11-20", "activities": 0, "rests": 1}
    assert week["activity_count"] == 6
    assert week["recorded_minutes"] == 70
    assert week["rest_days"] == 1
    assert client.get(ROOT + "/week", headers=other).json()["data"]["activity_count"] == 0

    journal = client.get(ROOT + "/journal", headers=owner, params={"window": "all"}).json()["data"]
    assert journal["total"] == 12
    assert journal["items"][0]["id"] == rest["id"]
    assert len(journal["items"]) == 10
    assert journal["next_page"] == 2
    older = client.get(ROOT + "/journal", headers=owner, params={"window": "all", "page": 2}).json()["data"]
    assert len(older["items"]) == 2
    assert older["next_page"] is None
    filtered = client.get(ROOT + "/journal", headers=owner, params={"window": "7", "activity_code": "yoga"}).json()["data"]
    assert filtered["items"] == [recent]
    assert not client.get(ROOT + "/journal", headers=other).json()["data"]["items"]

    path = ROOT + f"/checkins/{recent['id']}"
    edit = {"activity_code": "swim", "started_at": recent["started_at"], "duration_minutes": 30, "feeling_code": "energetic"}
    assert client.put(path, headers=other, json=edit).status_code == 404
    saved = client.put(path, headers=owner, json=edit).json()["data"]
    assert saved["started_at"] == recent["started_at"]
    assert saved["has_photo"] and saved["feeling_code"] == "energetic"
    assert client.get(path + "/photo", headers=other).status_code == 404
    assert client.put(path, headers=owner, json={**edit, "activity_code": "rest"}).status_code == 422
    assert client.put(path, headers=owner, json={**edit, "photo": None}).json()["data"]["has_photo"] is False


def test_exercise_library_has_categories_and_respects_cycle_switch(client):
    owner = auth_headers(register_and_login(client, username="exercise_activity_library"))
    today = local_today()
    assert client.post("/api/v1/c/herlog/periods", headers=owner, json={"start_day": today.isoformat()}).status_code == 200
    tailored = client.get(ROOT + "/recommendations", headers=owner).json()["data"]
    basic = client.get(ROOT + "/recommendations", headers=owner, params={"include_cycle": False}).json()["data"]
    assert tailored["phase"]["phase"] == "menstrual"
    assert tailored["cards"][0]["activity_code"] == "mobility"
    assert basic["phase"] is None and basic["cards"][0]["activity_code"] == "walk"
    assert {item["category"] for item in basic["cards"]} == {"gentle", "cardio", "strength", "rest"}
    assert len(basic["cards"]) == 9
