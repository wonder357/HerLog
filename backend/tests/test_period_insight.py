import json
from datetime import date

from app.core.config import settings
from app.core.errors import ApiError
from app.services import period_ai, period_insight_service
from tests.conftest import auth_headers, register_and_login

ROOT = "/api/v1/c/herlog"
INSIGHT = ROOT + "/cycle-insight"


def _member(client, name: str) -> dict:
    return auth_headers(register_and_login(client, username=name))


def _period(client, headers: dict, start: str, end: str | None = None) -> None:
    response = client.post(ROOT + "/periods", headers=headers, json={"start_day": start, "end_day": end})
    assert response.status_code == 200, response.text


def _freeze(monkeypatch, day: date, mode: str = "fixture") -> None:
    """三个模块各自持有 local_today，必须一起固定到同一天；默认不联网。"""

    monkeypatch.setattr(settings, "HERLOG_MODEL_MODE", mode)
    monkeypatch.setattr("app.services.period_service.local_today", lambda: day)
    monkeypatch.setattr("app.services.cycle_context.local_today", lambda: day)
    monkeypatch.setattr("app.services.period_insight_service.local_today", lambda: day)


def test_insight_requires_login(client) -> None:
    assert client.get(INSIGHT).status_code == 401


def test_fixture_insight_matches_cycle_facts(client, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 12, 1))
    period_insight_service.clear_cache()
    headers = _member(client, "insight_fixture")
    _period(client, headers, "2026-09-17", "2026-09-21")
    _period(client, headers, "2026-10-15", "2026-10-19")
    _period(client, headers, "2026-11-12", "2026-11-16")

    response = client.get(INSIGHT, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["day"] == "2026-12-01"
    assert data["phase"] == "luteal" and data["basis"] == "estimated"
    assert data["headline"].startswith("距预计经期")
    assert data["summary"]
    assert [group["key"] for group in data["groups"]] == ["diet", "exercise", "wellbeing"]
    assert [group["title"] for group in data["groups"]] == ["饮食", "运动", "作息与健康"]
    for group in data["groups"]:
        assert 1 <= len(group["items"]) <= 3
        assert all(len(item) <= 60 for item in group["items"])
    assert any("不用于避孕" in item for item in data["cautions"])
    assert data["demo_sample"] is True and data["degraded"] is False
    assert data["model_id"].startswith("fixture:")
    assert data["generated_at"]


def test_insight_reads_the_same_ovulation_window_as_the_calendar(client, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 12, 1))
    period_insight_service.clear_cache()
    headers = _member(client, "insight_sync")
    _period(client, headers, "2026-09-17", "2026-09-21")
    _period(client, headers, "2026-10-15", "2026-10-19")
    _period(client, headers, "2026-11-12", "2026-11-16")

    prediction = client.get(ROOT + "/periods", headers=headers).json()["data"]["prediction"]
    fertile = prediction["fertile_window"]
    ovulation = prediction["ovulation_day"]
    assert prediction["expected_start"] == "2026-12-10"
    assert ovulation == "2026-11-26"
    assert fertile == {"start_day": "2026-11-21", "end_day": "2026-11-27"}

    # 易孕期首日、排卵日、末日都是 ovulatory，前一天卵泡期，后一天黄体期
    def phase(day: str) -> str:
        return client.get(ROOT + "/cycle-context", headers=headers, params={"day": day}).json()["data"]["phase"]

    assert phase(fertile["start_day"]) == "ovulatory"
    assert phase(ovulation) == "ovulatory"
    assert phase(fertile["end_day"]) == "ovulatory"
    assert phase("2026-11-20") == "follicular"
    assert phase("2026-11-28") == "luteal"

    # 建议卡片里的阶段与月历由同一套窗口得出
    insight = client.get(INSIGHT, headers=headers).json()["data"]
    assert insight["phase"] == "luteal"
    assert insight["phase_label"] == "黄体期"


def test_overdue_insight_explains_the_rolled_window(client, monkeypatch) -> None:
    _freeze(monkeypatch, date(2027, 1, 3))
    period_insight_service.clear_cache()
    headers = _member(client, "insight_overdue")
    _period(client, headers, "2026-10-03", "2026-10-07")
    _period(client, headers, "2026-11-01", "2026-11-05")
    _period(client, headers, "2026-11-30", "2026-12-04")

    data = client.get(INSIGHT, headers=headers).json()["data"]
    assert data["headline"] == "预计经期已推迟 5 天"
    assert "月历已按今天重新高亮" in data["summary"]
    assert data["phase"] == "luteal"
    assert any("就医" in item for item in data["cautions"])


def test_ovulatory_insight_counts_days_inside_the_fertile_window(client, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 11, 20))
    period_insight_service.clear_cache()
    headers = _member(client, "insight_fertile")
    _period(client, headers, "2026-09-10", "2026-09-14")
    _period(client, headers, "2026-10-08", "2026-10-12")
    _period(client, headers, "2026-11-05", "2026-11-09")

    data = client.get(INSIGHT, headers=headers).json()["data"]
    assert data["phase"] == "ovulatory" and data["phase_label"] == "易孕期"
    assert data["headline"] == "易孕期第 7 天"
    assert any("不用于避孕" in item for item in data["cautions"])


def test_live_insight_uses_model_text(client, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 12, 1), mode="live")
    period_insight_service.clear_cache()
    headers = _member(client, "insight_live")
    _period(client, headers, "2026-09-01", "2026-09-05")
    _period(client, headers, "2026-10-01", "2026-10-05")
    _period(client, headers, "2026-10-30", "2026-11-03")
    seen: list[str] = []

    class Result:
        model = "deepseek-test"
        content = json.dumps({
            "summary": "模型小结：黄体期注意休息。",
            "diet": ["多喝温水", "少盐"],
            "exercise": ["散步 20 分钟"],
            "wellbeing": ["早点睡"],
            "cautions": ["异常出血请就医"],
        }, ensure_ascii=False)

    def fake_chat(messages, **options):
        seen.extend(messages)
        assert options["json_object"] is True
        return Result()

    monkeypatch.setattr(period_ai, "chat_sync", fake_chat)
    data = client.get(INSIGHT, headers=headers).json()["data"]

    assert data["summary"] == "模型小结：黄体期注意休息。"
    assert data["groups"][0]["items"] == ["多喝温水", "少盐"]
    assert data["groups"][1]["items"] == ["散步 20 分钟"]
    assert data["cautions"] == ["异常出血请就医"]
    assert data["demo_sample"] is False and data["degraded"] is False
    assert data["model_id"] == "deepseek-test"
    # 只上传事实文本，不上传账号标识
    assert "insight_live" not in str(seen)


def test_model_failure_falls_back_to_rules(client, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 12, 1), mode="live")
    period_insight_service.clear_cache()
    headers = _member(client, "insight_degrade")
    _period(client, headers, "2026-09-01", "2026-09-05")
    _period(client, headers, "2026-10-01", "2026-10-05")
    _period(client, headers, "2026-10-30", "2026-11-03")

    def boom(*_args, **_kwargs):
        raise ApiError(503, "模型服务暂时不可用")

    monkeypatch.setattr(period_ai, "chat_sync", boom)
    data = client.get(INSIGHT, headers=headers).json()["data"]

    assert data["degraded"] is True and data["demo_sample"] is True
    assert data["model_id"] == "fixture:fallback"
    assert data["groups"][0]["items"]


def test_insight_is_cached_until_refreshed(client, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 12, 1))
    period_insight_service.clear_cache()
    headers = _member(client, "insight_cache")
    _period(client, headers, "2026-10-01", "2026-10-05")
    _period(client, headers, "2026-10-30", "2026-11-03")

    first = client.get(INSIGHT, headers=headers).json()["data"]["generated_at"]
    second = client.get(INSIGHT, headers=headers).json()["data"]["generated_at"]
    refreshed = client.get(INSIGHT, headers=headers, params={"refresh": "true"}).json()["data"]["generated_at"]
    assert first == second
    assert refreshed >= first
