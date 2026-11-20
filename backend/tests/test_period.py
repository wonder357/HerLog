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
    assert overdue.expected_start == date(2026, 12, 29)


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
    assert "ovulatory_window" not in listing["prediction"]
    # 日历高亮：未记录结束的那段不参与持续天数估算，沿用唯一一段完整记录的 5 天
    assert listing["prediction"]["duration_days"] == 5
    assert listing["prediction"]["predicted_range"] == {"start_day": "2026-12-29", "end_day": "2027-01-02"}
    assert listing["prediction"]["ovulation_day"] == "2026-12-15"
    assert listing["prediction"]["fertile_window"] == {"start_day": "2026-12-10", "end_day": "2026-12-16"}

    latest = listing["items"][0]
    edited = client.put(
        f"/api/v1/c/herlog/periods/{latest['id']}",
        json={"start_day": "2026-11-30", "end_day": "2026-11-30"},
        headers=headers,
    )
    assert edited.status_code == 200
    listing = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]
    # 排卵日与易孕期只跟预计开始日有关，不随经期长度变化
    assert listing["prediction"]["ovulation_day"] == "2026-12-15"
    assert listing["prediction"]["fertile_window"] == {"start_day": "2026-12-10", "end_day": "2026-12-16"}
    # 两段完整记录（5 天、1 天）平均 3 天，预测经期随之收窄
    assert listing["prediction"]["duration_days"] == 3
    assert listing["prediction"]["predicted_range"] == {"start_day": "2026-12-29", "end_day": "2026-12-31"}


def test_derived_windows_for_calendar_highlight() -> None:
    next_start = date(2027, 1, 4)
    assert period_logic.ovulation_day(next_start) == date(2026, 12, 21)
    assert period_logic.fertile_window(next_start) == (date(2026, 12, 16), date(2026, 12, 22))
    assert period_logic.predicted_range(next_start, 5) == (date(2027, 1, 4), date(2027, 1, 8))
    # 持续天数夹在 2–10 天
    assert period_logic.predicted_range(next_start, 0) == (date(2027, 1, 4), date(2027, 1, 5))
    assert period_logic.predicted_range(next_start, 42) == (date(2027, 1, 4), date(2027, 1, 13))

    assert period_logic.estimate_duration_days([]) == 5
    assert period_logic.estimate_duration_days([4, 6]) == 5
    assert period_logic.estimate_duration_days([5, 5, 5, 5, 9]) == 5
    assert period_logic.estimate_duration_days([1, 1]) == 2
    assert period_logic.estimate_duration_days([30]) == 10

    rows = [
        (date(2026, 11, 1), date(2026, 11, 5)),
        (date(2026, 10, 3), None),
        (date(2026, 9, 5), date(2026, 9, 9)),
    ]
    assert period_logic.recent_durations(rows) == [5, 5]


def test_schedule_range_rolls_forward_until_recorded() -> None:
    expected = date(2026, 12, 29)
    # 未到期：区间就是预计那几天
    assert period_logic.schedule_range(expected, date(2026, 12, 20), 5) == (
        date(2026, 12, 29),
        date(2027, 1, 2),
        0,
    )
    # 到期当天：仍从今天开始，不算推迟
    assert period_logic.schedule_range(expected, date(2026, 12, 29), 5) == (
        date(2026, 12, 29),
        date(2027, 1, 2),
        0,
    )
    # 过期未记录：区间跟着今天走，逐日顺延
    assert period_logic.schedule_range(expected, date(2027, 1, 3), 5) == (
        date(2027, 1, 3),
        date(2027, 1, 7),
        5,
    )
    assert period_logic.schedule_range(expected, date(2027, 2, 10), 5) == (
        date(2027, 2, 10),
        date(2027, 2, 14),
        43,
    )


def test_overdue_prediction_never_highlights_the_past(
    client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.period_service.local_today", lambda: date(2027, 1, 3))
    headers = auth_headers(register_and_login(client))
    _create_period(client, headers, "2026-10-03", "2026-10-07")
    _create_period(client, headers, "2026-11-01", "2026-11-05")
    _create_period(client, headers, "2026-11-30", "2026-12-04")

    prediction = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]["prediction"]
    assert prediction["status"] == "overdue"
    assert prediction["expected_start"] == "2026-12-29"
    assert prediction["duration_days"] == 5
    assert prediction["overdue_days"] == 5
    assert prediction["predicted_range"] == {"start_day": "2027-01-03", "end_day": "2027-01-07"}

    # 再往后一天，高亮区间跟着往后挪
    monkeypatch.setattr("app.services.period_service.local_today", lambda: date(2027, 1, 6))
    prediction = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]["prediction"]
    assert prediction["overdue_days"] == 8
    assert prediction["predicted_range"] == {"start_day": "2027-01-06", "end_day": "2027-01-10"}

    # 补记实际开始日后回到 upcoming，区间重新按新周期算
    _create_period(client, headers, "2027-01-05", "2027-01-09")
    prediction = client.get("/api/v1/c/herlog/periods", headers=headers).json()["data"]["prediction"]
    assert prediction["overdue_days"] == 0
    assert prediction["status"] == "upcoming"
    assert prediction["predicted_range"] == {"start_day": "2027-02-03", "end_day": "2027-02-07"}


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
