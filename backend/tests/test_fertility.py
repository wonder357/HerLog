from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.clock import local_today
from tests.conftest import auth_headers, register_and_login

BASE = "/api/v1/c/herlog"
MODE = f"{BASE}/cycle-preference"
DAILY = f"{BASE}/fertility-daily"


def test_mode_preferences_are_private_and_do_not_change_existing_periods(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    other = auth_headers(register_and_login(client, username="other"))
    today = local_today()
    for offset in (75, 47, 19):
        start = today - timedelta(days=offset)
        saved = client.post(f"{BASE}/periods", headers=headers,
                            json={"start_day": str(start), "end_day": str(start + timedelta(days=4))})
        assert saved.status_code == 200
    day = str(today - timedelta(days=1))
    feelings_path = f"{BASE}/feelings"
    client.put(f"{feelings_path}/{day}", headers=headers, json={"note": "保留", "mood": "平静"})
    before = client.get(f"{BASE}/periods", headers=headers).json()["data"]
    context_before = client.get(f"{BASE}/weights/summary?days=30&include_cycle=true", headers=headers)
    assert context_before.status_code == 200
    feelings_query = {"from": day, "to": day}
    old_feelings = client.get(feelings_path, headers=headers, params=feelings_query).json()["data"]
    assert old_feelings[0]["mood"] == "平静"

    default = client.get(MODE, headers=headers)
    assert default.json()["data"]["active_mode"] == "period"
    assert not default.json()["data"]["configured"]
    assert default.headers["cache-control"] == "private, no-store"
    assert client.put(MODE, headers=headers, json={"active_mode": "pregnant"}).status_code == 422
    assert client.put(MODE + "/start-date", headers=headers,
                      json={"trying_started_on": str(today + timedelta(days=1))}).status_code == 422
    switched = client.put(MODE, headers=headers, json={"active_mode": "trying_to_conceive"})
    assert switched.json()["data"]["seen_fertility"]
    assert client.put(MODE + "/start-date", headers=headers,
                      json={"trying_started_on": day}).json()["data"]["trying_started_on"] == day
    path = f"{DAILY}/{day}"
    assert client.put(path, headers=headers, json={"bbt_c": "36.45", "expected_revision": None}).status_code == 200
    returned = client.put(MODE, headers=headers, json={"active_mode": "period"}).json()["data"]
    assert returned["active_mode"] == "period" and returned["seen_fertility"]
    assert client.get(MODE, headers=other).json()["data"]["trying_started_on"] is None
    cleared = client.put(MODE + "/start-date", headers=headers, json={"trying_started_on": None})
    assert cleared.json()["data"]["trying_started_on"] is None
    assert client.get(path, headers=headers).status_code == 200
    assert client.get(f"{BASE}/periods", headers=headers).json()["data"] == before
    assert client.get(feelings_path, headers=headers, params=feelings_query).json()["data"] == old_feelings
    context_after = client.get(f"{BASE}/weights/summary?days=30&include_cycle=true", headers=headers)
    assert context_after.json()["data"]["cycle_context"] == context_before.json()["data"]["cycle_context"]


def test_journal_precision_times_and_conflicts(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    day = str(local_today() - timedelta(days=2))
    path = f"{DAILY}/{day}"
    payload = {
        "expected_revision": None, "bbt_c": "36.50", "bbt_measured_at": f"{day}T06:08:00+08:00",
        "cervical_mucus": "stretchy", "intercourse_occurred": False, "lh_tests": [
            {"result": "strong_positive", "measured_at": f"{day}T18:30:00+08:00"},
            {"result": "negative", "measured_at": f"{day}T08:00:00+08:00"},
            {"result": "weak_positive"},
        ],
    }
    saved = client.put(path, headers=headers, json=payload)
    assert saved.status_code == 200, saved.text
    item = saved.json()["data"]
    assert item["bbt_c"] == "36.50"
    assert item["intercourse_occurred"] is False
    assert item["bbt_measured_at"].endswith("22:08:00Z")
    assert [test["result"] for test in item["lh_tests"]] == ["negative", "strong_positive", "weak_positive"]
    assert client.get(path, headers=headers).json()["data"] == item
    assert client.put(path, headers=headers, json=payload).status_code == 409
    changed = client.put(path, headers=headers, json={
        "expected_revision": item["revision"], "intercourse_occurred": False,
    }).json()["data"]
    assert changed["revision"] != item["revision"] and changed["lh_tests"] == [] and changed["bbt_c"] is None
    stale = client.delete(path, headers=headers, params={"expected_revision": item["revision"]})
    assert stale.status_code == 409
    assert client.delete(path, headers=headers, params={"expected_revision": changed["revision"]}).status_code == 200
    assert client.get(path, headers=headers).status_code == 404


def test_private_journal_404_and_invalid_input(client: TestClient) -> None:
    owner = auth_headers(register_and_login(client))
    other = auth_headers(register_and_login(client, username="other"))
    day = str(local_today() - timedelta(days=1))
    path = f"{DAILY}/{day}"
    for invalid in (
        {}, {"bbt_c": "36.452"}, {"bbt_c": 36.45}, {"bbt_c": "30.00", "bbt_measured_at": f"{day}T23:00:00Z"},
        {"lh_tests": [{"result": "negative"}, {"result": "strong_positive"}]},
        {"lh_tests": [{"result": "unknown"}]}, {"cervical_mucus": "other"}, {"intercourse_occurred": "false"},
    ):
        assert client.put(path, headers=owner, json={"expected_revision": None, **invalid}).status_code == 422
    item = client.put(path, headers=owner, json={"expected_revision": None, "bbt_c": "36.45"}).json()["data"]
    for method in ("get", "put", "delete"):
        kwargs = {"headers": other}
        if method == "put":
            kwargs["json"] = {"expected_revision": item["revision"], "bbt_c": "36.40"}
        if method == "delete":
            kwargs["params"] = {"expected_revision": item["revision"]}
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 404
        assert response.headers["cache-control"] == "private, no-store"
    assert client.get(DAILY, headers=other, params={"from": day, "to": day}).json()["data"] == []
    assert client.get(path).status_code == 401
    assert client.put(path, headers=other, json={"expected_revision": None, "cervical_mucus": "dry"}).status_code == 200
    assert client.get(path, headers=owner).json()["data"]["bbt_c"] == "36.45"
    assert client.get(DAILY, headers=owner, params={"from": "2025-01-01", "to": "2025-04-03"}).status_code == 422
    future = str(local_today() + timedelta(days=1))
    assert client.put(f"{DAILY}/{future}", headers=owner,
                      json={"expected_revision": None, "bbt_c": "36.60"}).status_code == 422
    assert client.delete(path, headers=owner, params={"expected_revision": str(uuid4())}).status_code == 409
