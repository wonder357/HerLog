from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.core.clock import local_today, to_utc_naive
from app.logic import weight as weight_logic
from tests.conftest import auth_headers, register_and_login

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _measured(day: date, hour: int = 8) -> str:
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=SHANGHAI).isoformat()


def _post_weight(
    client: TestClient, headers: dict, kg: float, day: date, hour: int = 8, key: str | None = None
) -> dict:
    response = client.post(
        "/api/v1/c/herlog/weights",
        json={
            "client_key": key or f"key-{day.isoformat()}-{hour}-{kg}",
            "kg": kg,
            "measured_at": _measured(day, hour),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_kg_input_is_stored_as_positive_grams() -> None:
    assert weight_logic.parse_kg("56.8") == 56800
    assert weight_logic.parse_kg("56.800") == 56800
    assert weight_logic.parse_kg(0.001) == 1
    for bad in ("56.8001", "0", "-1", "abc"):
        try:
            weight_logic.parse_kg(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} 应被拒绝")


def test_same_day_takes_last_measurement_and_counts_every_record() -> None:
    """文档示例：同日 56.8、57.0，第三天 56.6 → 三笔、两个点、−0.4 kg。"""

    today = local_today()
    rows = [
        weight_logic.WeightRow(
            id=1, grams=56800, measured_at=to_utc_naive(datetime.combine(today, datetime.min.time()) + timedelta(hours=8))
        ),
        weight_logic.WeightRow(
            id=2, grams=57000, measured_at=to_utc_naive(datetime.combine(today, datetime.min.time()) + timedelta(hours=21))
        ),
        weight_logic.WeightRow(
            id=3,
            grams=56600,
            measured_at=to_utc_naive(
                datetime.combine(today + timedelta(days=2), datetime.min.time()) + timedelta(hours=8)
            ),
        ),
    ]
    summary = weight_logic.summarize(rows, 7, today + timedelta(days=2))
    assert summary.count == 3
    assert len(summary.points) == 2
    assert summary.points[0].grams == 57000
    assert summary.points[-1].grams == 56600
    assert summary.delta_grams == -400
    assert summary.delta_kg == -0.4


def test_weight_create_summary_and_details(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    today = local_today()
    first_day = today - timedelta(days=2)
    _post_weight(client, headers, 56.8, first_day, hour=8)
    _post_weight(client, headers, 57.0, first_day, hour=21)
    _post_weight(client, headers, 56.6, today, hour=8)

    summary = client.get(
        "/api/v1/c/herlog/weights/summary", params={"days": 7}, headers=headers
    ).json()["data"]
    assert summary["count"] == 3
    assert len(summary["points"]) == 2
    assert summary["delta_kg"] == -0.4
    assert summary["latest_kg"] == 56.6
    assert summary["suggestion"]

    details = client.get("/api/v1/c/herlog/weights", headers=headers).json()["data"]
    assert details["total"] == 3
    assert [item["kg"] for item in details["items"]] == [56.6, 57.0, 56.8]


def test_single_record_has_no_delta(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    _post_weight(client, headers, 56.8, local_today(), hour=8)
    summary = client.get(
        "/api/v1/c/herlog/weights/summary", params={"days": 30}, headers=headers
    ).json()["data"]
    assert summary["count"] == 1
    assert summary["delta_kg"] is None
    assert summary["delta_grams"] is None
    assert "继续记录" in summary["suggestion"]


def test_empty_state(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    summary = client.get(
        "/api/v1/c/herlog/weights/summary", params={"days": 30}, headers=headers
    ).json()["data"]
    assert summary["latest_kg"] is None
    assert summary["count"] == 0
    assert summary["points"] == []
    assert summary["suggestion"] is None


def test_client_key_is_idempotent_and_conflicts_on_changed_content(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    today = local_today()
    first = _post_weight(client, headers, 56.8, today, hour=8, key="retry-key-0001")

    again = client.post(
        "/api/v1/c/herlog/weights",
        json={"client_key": "retry-key-0001", "kg": 56.8, "measured_at": _measured(today, 8)},
        headers=headers,
    )
    assert again.status_code == 200
    assert again.json()["data"]["id"] == first["id"]

    changed = client.post(
        "/api/v1/c/herlog/weights",
        json={"client_key": "retry-key-0001", "kg": 60.1, "measured_at": _measured(today, 8)},
        headers=headers,
    )
    assert changed.status_code == 409

    assert client.get("/api/v1/c/herlog/weights", headers=headers).json()["data"]["total"] == 1


def test_update_and_delete_weight(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    today = local_today()
    record = _post_weight(client, headers, 56.8, today, hour=8)
    updated = client.put(
        f"/api/v1/c/herlog/weights/{record['id']}",
        json={
            "client_key": record["client_key"],
            "kg": 56.4,
            "measured_at": _measured(today, 9),
            "tag": "晨起",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["kg"] == 56.4
    assert updated.json()["data"]["tag"] == "晨起"

    assert (
        client.delete(f"/api/v1/c/herlog/weights/{record['id']}", headers=headers).status_code == 200
    )
    assert client.get("/api/v1/c/herlog/weights", headers=headers).json()["data"]["total"] == 0


def test_measured_at_requires_timezone(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    response = client.post(
        "/api/v1/c/herlog/weights",
        json={"client_key": "no-tz-key-0001", "kg": 56.8, "measured_at": "2026-11-18T08:00:00"},
        headers=headers,
    )
    assert response.status_code == 422
    assert "时区" in response.json()["message"]


def test_summary_days_validation(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    response = client.get(
        "/api/v1/c/herlog/weights/summary", params={"days": 14}, headers=headers
    )
    assert response.status_code == 422
