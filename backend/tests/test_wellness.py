from __future__ import annotations

from datetime import timedelta

from app.core.clock import local_today
from app.core.config import settings
from tests.conftest import auth_headers, register_and_login

ROOT = "/api/v1/c/herlog"


def member(client, name: str) -> dict:
    return auth_headers(register_and_login(client, username=name))


def save_weight(client, headers, day, hour, value, key, feelings=None):
    return client.post(f"{ROOT}/weights", headers=headers, json={
        "client_key": key, "kg": value, "measured_at": f"{day.isoformat()}T{hour:02d}:00:00+08:00",
        "feeling_tags": feelings or [],
    })


def join(client, topic, headers):
    return client.post(f"{ROOT}/{topic}/groups/general/membership", headers=headers, json={
        "invite_code": "test-invite", "consent": True,
    })


def test_weight_keeps_all_records_and_nonoverlapping_compare(client):
    headers = member(client, "wellness_weight")
    today = local_today()
    boundary = today - timedelta(days=6)
    records = (
        (boundary - timedelta(days=1), 8, 58.1),
        (boundary, 8, 56.8),
        (boundary, 21, 57.0),
        (today, 8, 56.6),
    )
    for index, (day, hour, kg) in enumerate(records):
        assert save_weight(client, headers, day, hour, kg, f"wellness-weight-{index}").status_code == 200
    summary = client.get(f"{ROOT}/weights/summary?days=7", headers=headers).json()["data"]
    assert summary["count"] == 3 and summary["record_days"] == 2
    assert [point["kg"] for point in summary["points"]] == [57, 56.6]
    assert summary["delta_grams"] == -400
    assert summary["metrics"]["bmi"]["status"] == "missing_height"
    assert client.put(f"{ROOT}/profile", headers=headers, json={"height_cm": 165}).status_code == 200
    next_summary = client.get(f"{ROOT}/weights/summary?days=7", headers=headers).json()["data"]
    assert next_summary["metrics"]["bmi"]["value"] == 20.8
    compare = client.get(f"{ROOT}/weights/compare?days=7", headers=headers).json()["data"]
    assert compare["previous"]["end_day"] == (boundary - timedelta(days=1)).isoformat()
    assert compare["previous"]["count"] == 1 and compare["current"]["count"] == 3
    assert compare["avg_delta_kg"] is None


def test_luteal_note_needs_personal_feeling(client):
    headers = member(client, "wellness_cycle")
    today = local_today()
    for offset in (78, 50, 22):
        start = today - timedelta(days=offset)
        response = client.post(f"{ROOT}/periods", headers=headers, json={
            "start_day": start.isoformat(), "end_day": (start + timedelta(days=4)).isoformat(),
        })
        assert response.status_code == 200, response.text
    get_summary = lambda: client.get(f"{ROOT}/weights/summary?days=7&include_cycle=true", headers=headers).json()["data"]
    assert save_weight(client, headers, today, 8, 60.0, "cycle-weight-first").status_code == 200
    cycle = get_summary()["cycle_context"][-1]
    assert cycle["phase"] == "luteal" and cycle["basis"] == "estimated" and cycle["note"] is None
    assert save_weight(client, headers, today, 9, 60.1, "cycle-weight-other", ["bloating"]).status_code == 200
    assert get_summary()["cycle_context"][-1]["note"]


def test_exercise_share_is_opt_in_and_private(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_GROUP_INVITE_CODE", "test-invite")
    owner = member(client, "exercise_share_owner")
    viewer = member(client, "exercise_share_viewer")
    request = {
        "client_key": "exercise-persist-once",
        "activity_code": "walk",
        "started_at": f"{local_today()}T08:00:00+08:00",
        "duration_minutes": 23,
        "effort": "easy",
    }
    first = client.post(f"{ROOT}/exercise/checkins", headers=owner, json=request).json()["data"]
    repeated = client.post(f"{ROOT}/exercise/checkins", headers=owner, json=request).json()["data"]
    assert repeated["id"] == first["id"]
    assert client.delete(f"{ROOT}/exercise/checkins/{first['id']}", headers=viewer).status_code == 404
    assert client.get(f"{ROOT}/weights/summary", headers=owner).json()["data"]["count"] == 0
    assert join(client, "exercise", owner).status_code == 200
    payload = {
        "client_key": "exercise-share-once",
        "checkin_id": first["id"],
        "group_key": "general",
        "caption_code": "checked_in",
    }
    assert client.post(f"{ROOT}/exercise/shares", headers=owner, json={**payload, "weight_kg": 57}).status_code == 422
    published = client.post(f"{ROOT}/exercise/shares", headers=owner, json=payload).json()["data"]
    feed = f"{ROOT}/exercise/groups/general/shares"
    assert client.get(feed, headers=viewer).status_code == 404
    assert join(client, "exercise", viewer).status_code == 200
    card = client.get(feed, headers=viewer).json()["data"]["items"][0]
    assert not card["mine"] and set(card["snapshot"]) == {"caption", "activity"}
    assert not {"started_at", "customer_id", "checkin_id"} & card.keys()
    assert client.post(
        f"{ROOT}/exercise/shares/{published['public_id']}/reports",
        headers=viewer,
        json={"reason_code": "other"},
    ).status_code == 200
    assert client.get(feed, headers=viewer).json()["data"]["items"] == []
    reports = f"{ROOT}/exercise/moderation/reports"
    assert client.get(reports, headers=viewer).status_code == 404
    owner_id = client.get("/api/v1/c/auth/me", headers=owner).json()["data"]["customer_id"]
    monkeypatch.setattr(settings, "HERLOG_GROUP_MODERATOR_ID", owner_id)
    queue = client.get(reports, headers=owner).json()["data"]
    assert queue[0]["public_id"] == published["public_id"]
    assert "customer_id" not in queue[0]
    hide = f"{ROOT}/exercise/shares/{published['public_id']}/moderation"
    assert client.put(hide, headers=viewer, json={"action": "hide"}).status_code == 404
    assert client.put(hide, headers=owner, json={"action": "hide"}).status_code == 200
    assert client.get(feed, headers=owner).json()["data"]["items"] == []
    assert client.delete(f"{ROOT}/exercise/checkins/{first['id']}", headers=owner).status_code == 200
    assert client.get(feed, headers=owner).json()["data"]["items"] == []


def test_skin_journal_and_share_replies_survive_through_api(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_GROUP_INVITE_CODE", "test-invite")
    owner = member(client, "skin_journal_owner")
    viewer = member(client, "skin_journal_viewer")
    day = local_today().isoformat()
    path = f"{ROOT}/skin/journal/{day}"
    payload = {"skin_type": "combination", "comfort": 4, "sensations": ["tight"], "routine": ["shade"], "note": "private"}
    assert client.put(path, headers=owner, json=payload).json()["data"]["comfort"] == 4
    assert client.put(path, headers=owner, json={**payload, "comfort": 8}).status_code == 422
    assert client.get(f"{ROOT}/skin/journal/latest", headers=viewer).json()["data"] is None
    assert client.delete(path, headers=viewer).status_code == 404
    assert join(client, "skin", owner).status_code == 200
    assert join(client, "skin", viewer).status_code == 200
    published = client.post(f"{ROOT}/skin/shares", headers=owner, json={
        "client_key": "skin-share-once", "day": day, "group_key": "general", "caption_code": "sun_care",
    }).json()["data"]
    reply = f"{ROOT}/skin/shares/{published['public_id']}/replies"
    assert client.post(reply, headers=viewer, json={"reply_code": "thanks"}).status_code == 200
    assert client.post(reply, headers=viewer, json={"reply_code": "also_record"}).status_code == 200
    feed = client.get(f"{ROOT}/skin/groups/general/shares", headers=owner).json()["data"]["items"]
    assert set(feed[0]["snapshot"]) == {"caption"}
    assert feed[0]["replies"] == [{"text": "我也在记护理日记。", "count": 1}]
    assert client.delete(path, headers=owner).status_code == 200
    assert client.get(f"{ROOT}/skin/groups/general/shares", headers=viewer).json()["data"]["items"] == []
