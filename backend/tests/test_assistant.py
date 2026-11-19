from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.core.clock import local_today
from tests.conftest import auth_headers, register_and_login

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _ask(client: TestClient, headers: dict, question: str) -> dict:
    response = client.post(
        "/api/v1/c/herlog/assistant/query", json={"question": question}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _post_weight(client: TestClient, headers: dict, kg: float, day, hour: int = 8) -> None:
    measured = datetime(day.year, day.month, day.day, hour, 0, tzinfo=SHANGHAI).isoformat()
    response = client.post(
        "/api/v1/c/herlog/weights",
        json={"client_key": f"k-{day.isoformat()}-{hour}-{kg}", "kg": kg, "measured_at": measured},
        headers=headers,
    )
    assert response.status_code == 200, response.text


def test_weight_question_without_records_returns_empty_state(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    data = _ask(client, headers, "过去七天体重如何")
    assert data["domain"] == "weight"
    assert data["range"]["days"] == 7
    assert "还没有体重记录" in data["answer"]
    assert data["record_refs"] == []


def test_weight_question_uses_saved_records_and_dates(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    today = local_today()
    _post_weight(client, headers, 57.0, today - timedelta(days=2))
    _post_weight(client, headers, 56.6, today)

    data = _ask(client, headers, "这周体重有变化吗")
    assert data["domain"] == "weight"
    assert data["range"]["days"] == 7
    assert data["range"]["date_to"] == today.isoformat()
    assert f"最近 {7} 天" in data["range"]["label"]
    assert "56.6" in data["answer"] and "-0.400" in data["answer"]
    assert len(data["record_refs"]) == 2
    assert data["record_refs"][0]["route"] == "/pages/weight/index"


def test_thirty_day_scope_is_understood(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    data = _ask(client, headers, "最近一个月体重怎么样")
    assert data["range"]["days"] == 30


def test_record_request_points_to_shortcuts_without_writing(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    data = _ask(client, headers, "帮我记 56.8 kg")
    assert data["domain"] == "record_help"
    assert "记体重" in data["answer"]
    assert client.get("/api/v1/c/herlog/weights", headers=headers).json()["data"]["total"] == 0


def test_cross_module_attribution_is_refused(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    data = _ask(client, headers, "是不是因为来了月经才长痘")
    assert data["domain"] == "unsupported"
    assert "归因" in data["answer"]


def test_period_question_reports_estimate(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    for start in ("2026-10-03", "2026-11-01", "2026-11-30"):
        response = client.post(
            "/api/v1/c/herlog/periods", json={"start_day": start}, headers=headers
        )
        assert response.status_code == 200, response.text
    data = _ask(client, headers, "下次经期大概什么时候")
    assert data["domain"] == "period"
    assert "2026-12-29" in data["answer"]
    assert "不作为避孕依据" in data["answer"]
    assert len(data["record_refs"]) == 3


def test_unsupported_question_lists_capabilities(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    data = _ask(client, headers, "今天天气怎么样")
    assert data["domain"] == "unsupported"
    assert "体重" in data["answer"]
