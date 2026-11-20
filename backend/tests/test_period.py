from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core.clock import local_today
from app.logic import period as period_logic
from tests.conftest import auth_headers, register_and_login


def test_prediction_matches_appendix_cases() -> None:
    """附录六组边界用例。"""

    today = date(2026, 12, 1)
    prediction = period_logic.predict_next_start(
        [date(2026, 10, 3), date(2026, 11, 1), date(2026, 11, 30)], today
    )
    assert prediction.status == "upcoming"
    assert prediction.expected_start == date(2026, 12, 29)
    assert prediction.estimate_days == 29

    # 相差 7 天仍可预测
    spread7 = period_logic.predict_next_start(
        [date(2026, 10, 6), date(2026, 10, 31), date(2026, 12, 2)], date(2026, 12, 3)
    )
    assert spread7.status == "upcoming"
    assert spread7.estimate_days == 29

    # 相差 8 天则隐藏预测
    spread8 = period_logic.predict_next_start(
        [date(2026, 10, 5), date(2026, 10, 30), date(2026, 12, 2)], date(2026, 12, 3)
    )
    assert spread8.status == "irregular"
    assert spread8.expected_start is None
    assert spread8.message == "近期周期变化较大，暂不显示预计日期"

    # 少于三条开始记录不预测
    insufficient = period_logic.predict_next_start([date(2026, 10, 3), date(2026, 11, 1)], today)
    assert insufficient.status == "insufficient"
    assert insufficient.expected_start is None

    # 过了预计日期不顺延
    overdue = period_logic.predict_next_start(
        [date(2026, 10, 3), date(2026, 11, 1), date(2026, 11, 30)], date(2026, 12, 30)
    )
    assert overdue.status == "overdue"
    assert overdue.expected_start is None


def test_prediction_uses_median_of_three_cycles() -> None:
    starts = [date(2026, 8, 1), date(2026, 8, 31), date(2026, 9, 30), date(2026, 11, 1)]
    estimate, intervals = period_logic.estimate_cycle_days(starts)
    assert intervals == [32, 30, 30]
    assert estimate == 30
    prediction = period_logic.predict_next_start(starts, date(2026, 11, 2))
    assert prediction.expected_start == date(2026, 12, 1)


def test_duration_includes_both_endpoints() -> None:
    assert period_logic.duration_days(date(2026, 10, 3), date(2026, 10, 7)) == 5
    assert period_logic.duration_days(date(2026, 10, 3), None) is None


def _create_period(client: TestClient, headers: dict, start: str, end: str | None = None) -> dict:
    response = client.post(
        "/api/v1/c/herlog/periods", json={"start_day": start, "end_day": end}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_period_crud_updates_history_and_prediction(client: TestClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.period_service.local_today", lambda: date(2026, 12, 1))
    headers = auth_headers(register_and_login(client))
    first = _create_period(client, headers, "2026-10-03", "2026-10-07")
    assert first["duration_days"] == 5
    assert first["cycle_days"] is None

    second = _create_period(client, headers, "2026-11-01")
    assert second["cycle_days"] == 29
    assert second["duration_days"] is None

    listing = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]
    assert [item["start_day"] for item in listing["items"]] == ["2026-11-01", "2026-10-03"]
    assert listing["items"][0]["duration_days"] is None
    assert listing["prediction"]["status"] == "insufficient"
    assert listing["items"][1]["duration_days"] == 5

    _create_period(client, headers, "2026-11-30")
    listing = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]
    assert listing["prediction"]["status"] == "upcoming"
    assert listing["prediction"]["estimate_days"] == 29
    assert listing["prediction"]["ovulatory_window"] is None
    assert listing["prediction"]["expected_end"] == listing["prediction"]["expected_start"]

    latest = listing["items"][0]
    edited = client.put(
        f"/api/v1/c/herlog/periods/{latest['id']}",
        json={"start_day": "2026-11-30", "end_day": "2026-11-30"},
        headers=headers,
    )
    assert edited.status_code == 200
    listing = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]
    assert listing["prediction"]["ovulatory_window"] == {
        "start_day": "2026-12-10", "estimated_day": "2026-12-15", "end_day": "2026-12-16",
    }


def test_period_forecast_crosses_month_then_expires_until_new_start(client: TestClient, monkeypatch: MonkeyPatch) -> None:
    today = date(2026, 11, 30)
    monkeypatch.setattr("app.services.period_service.local_today", lambda: today)
    headers = auth_headers(register_and_login(client))
    for start, end in (("2026-09-07", "2026-09-10"), ("2026-10-05", "2026-10-09"), ("2026-11-02", "2026-11-07")):
        _create_period(client, headers, start, end)

    path = "/api/v1/c/herlog/periods"
    forecast = client.get(path, headers=headers).json()["data"]["prediction"]
    assert forecast["status"] == "upcoming"
    assert (forecast["expected_start"], forecast["expected_end"]) == ("2026-11-30", "2026-12-04")
    assert forecast["ovulatory_window"]["estimated_day"] == "2026-11-16"

    today += timedelta(days=1)
    forecast = client.get(path, headers=headers).json()["data"]["prediction"]
    assert forecast["status"] == "overdue"
    assert forecast["expected_start"] is forecast["expected_end"] is forecast["ovulatory_window"] is None
    _create_period(client, headers, "2026-11-30")
    forecast = client.get(path, headers=headers).json()["data"]["prediction"]
    assert (forecast["expected_start"], forecast["expected_end"]) == ("2026-12-28", "2027-01-01")


def test_overlapping_period_is_rejected_with_the_conflicting_date(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    _create_period(client, headers, "2026-11-01", "2026-11-05")
    response = client.post(
        "/api/v1/c/herlog/periods",
        json={"start_day": "2026-11-04", "end_day": "2026-11-08"},
        headers=headers,
    )
    assert response.status_code == 409
    assert "2026-11-01" in response.json()["message"]


def test_unknown_end_only_occupies_start_day(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    _create_period(client, headers, "2026-11-01")
    later = client.post(
        "/api/v1/c/herlog/periods", json={"start_day": "2026-11-05"}, headers=headers
    )
    assert later.status_code == 200


def test_end_before_start_is_rejected(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    response = client.post(
        "/api/v1/c/herlog/periods",
        json={"start_day": "2026-11-05", "end_day": "2026-11-01"},
        headers=headers,
    )
    assert response.status_code == 422


def test_update_and_delete_period(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    created = _create_period(client, headers, "2026-11-01", "2026-11-05")
    moved = client.put(
        f"/api/v1/c/herlog/periods/{created['id']}",
        json={"start_day": "2026-11-02", "end_day": "2026-11-06"},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["data"]["start_day"] == "2026-11-02"
    assert moved.json()["data"]["duration_days"] == 5

    assert (
        client.delete(f"/api/v1/c/herlog/periods/{created['id']}", headers=headers).status_code
        == 200
    )
    listing = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]
    assert listing["items"] == []
    assert listing["status"]["message"] == "还没有经期记录"


def test_feelings_are_independent_from_periods(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    _create_period(client, headers, "2026-11-01", "2026-11-05")
    saved = client.put(
        "/api/v1/c/herlog/feelings/2026-11-03",
        json={"flow": "中等", "symptoms": ["腹胀"], "impact": "轻微影响", "note": "下午更明显"},
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["data"]["symptoms"] == ["腹胀"]

    # 感受可脱离实际经期存在
    extra = client.put(
        "/api/v1/c/herlog/feelings/2026-11-20",
        json={"symptoms": ["腹胀"]},
        headers=headers,
    )
    assert extra.status_code == 200

    listing = client.get(
        "/api/v1/c/herlog/feelings",
        params={"from": "2026-11-01", "to": "2026-11-30"},
        headers=headers,
    ).json()["data"]
    assert [item["day"] for item in listing] == ["2026-11-03", "2026-11-20"]

    # 删除经期段不删除感受
    periods = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]["items"]
    client.delete(f"/api/v1/c/herlog/periods/{periods[0]['id']}", headers=headers)
    listing = client.get(
        "/api/v1/c/herlog/feelings",
        params={"from": "2026-11-01", "to": "2026-11-30"},
        headers=headers,
    ).json()["data"]
    assert len(listing) == 2

    # 清空全部字段等同于删除
    cleared = client.put(
        "/api/v1/c/herlog/feelings/2026-11-03",
        json={"flow": None, "symptoms": [], "impact": None, "note": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["data"] is None


def test_unknown_symptom_is_rejected(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    response = client.put(
        "/api/v1/c/herlog/feelings/2026-11-03",
        json={"symptoms": ["不存在的症状"]},
        headers=headers,
    )
    assert response.status_code == 422


def test_status_shows_current_day_index(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    today = local_today()
    start = today - timedelta(days=1)
    client.post(
        "/api/v1/c/herlog/periods",
        json={"start_day": start.isoformat(), "end_day": today.isoformat()},
        headers=headers,
    )
    status = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]["status"]
    assert status["in_period"] is True
    assert status["message"] == "经期第 2 天"


def test_old_open_period_does_not_override_newer_closed_record(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    today = local_today()
    _create_period(client, headers, (today - timedelta(days=40)).isoformat(), None)
    latest = (today - timedelta(days=10)).isoformat()
    _create_period(client, headers, latest, (today - timedelta(days=6)).isoformat())
    data = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]
    assert data["status"]["in_period"] is False
    assert data["status"]["start_day"] == latest


def test_overdue_prediction_does_not_extend_unfinished_period(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    today = local_today()
    for age in (85, 57, 29):
        _create_period(client, headers, (today - timedelta(days=age)).isoformat(), None)
    data = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]
    assert data["prediction"]["status"] == "overdue"
    assert data["status"]["in_period"] is False


def test_legacy_future_period_does_not_drive_current_prediction(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    today = local_today()
    for age in (57, 29, -1):
        _create_period(client, headers, (today - timedelta(days=age)).isoformat())
    data = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]
    assert len(data["items"]) == 3
    assert data["prediction"]["status"] == "insufficient"
    assert data["status"]["start_day"] == (today - timedelta(days=29)).isoformat()


def test_mood_only_entries_are_private_and_editable_by_new_and_legacy_forms(client: TestClient) -> None:
    owner = auth_headers(register_and_login(client))
    other = auth_headers(register_and_login(client, username="another"))
    day = "2026-11-11"
    path = f"/api/v1/c/herlog/feelings/{day}"
    response = client.put(path, json={"mood": "平静"}, headers=owner)
    assert response.status_code == 200
    assert response.json()["data"]["mood"] == "平静"
    params = {"from": day, "to": day}
    assert client.get("/api/v1/c/herlog/feelings", params=params, headers=other).json()["data"] == []
    assert client.put(path, json={"mood": "不允许的心情"}, headers=owner).status_code == 422
    edited = client.put(path, json={"note": "早上写的"}, headers=owner).json()["data"]
    assert edited["mood"] == "平静"
    assert edited["note"] == "早上写的"
    assert client.put(path, json={"mood": None}, headers=owner).json()["data"] is None
