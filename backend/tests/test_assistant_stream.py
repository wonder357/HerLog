import json
from datetime import date, timedelta

from app.core.config import settings
from app.services import assistant_stream
from app.services.deepseek_client import StreamChunk
from tests.conftest import auth_headers, register_and_login

ROOT = "/api/v1/c/herlog"
STREAM = ROOT + "/assistant/stream"


def events(response):
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/event-stream")
    assert response.headers["Cache-Control"] == "private, no-store"
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_stream_authentication_and_records_stay_local(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "live")

    async def unexpected_call(*_args, **_kwargs):
        raise AssertionError("private records must stay on the app server")

    monkeypatch.setattr(assistant_stream, "chat_stream", unexpected_call)
    payload = {"mode": "records", "question": "最近一次经期是哪天"}
    assert client.post(STREAM, json=payload).status_code == 401
    owner = auth_headers(register_and_login(client, username="stream_owner"))
    other = auth_headers(register_and_login(client, username="stream_other"))
    start = "2026-10-08"
    assert client.post(ROOT + "/periods", headers=owner, json={"start_day": start}).status_code == 200
    own = events(client.post(STREAM, headers=owner, json=payload))
    assert own[0] == {"type": "source", "source": "records"}
    assert start in own[-1]["answer"]["answer"]
    assert own[-1]["answer"]["record_refs"]
    assert not events(client.post(STREAM, headers=other, json=payload))[-1]["answer"]["record_refs"]


def test_model_stream_forwards_only_conversation_and_public_text(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "live")
    headers = auth_headers(register_and_login(client, username="stream_general"))
    assert client.post(ROOT + "/periods", headers=headers, json={"start_day": "2026-10-08"}).status_code == 200
    seen = []

    async def fake_stream(messages, **options):
        seen.extend(messages)
        assert options["thinking"] is False
        yield StreamChunk(reasoning="internal reasoning")
        yield StreamChunk(text="第一段。")
        yield StreamChunk(text="第二段。")
        yield StreamChunk(done=True)

    monkeypatch.setattr(assistant_stream, "chat_stream", fake_stream)
    result = events(client.post(STREAM, headers=headers, json={
        "mode": "general", "question": "那皮肤呢？",
        "history": [{"question": "怎样记录健康变化？", "answer": "从当天感受记起。"}],
    }))
    assert result[0] == {"type": "source", "source": "deepseek"}
    assert result[1:3] == [{"type": "delta", "text": "第一段。"}, {"type": "delta", "text": "第二段。"}]
    assert result[-1]["answer"]["answer"] == "第一段。第二段。"
    assert result[-1]["answer"]["record_refs"] == []
    assert [item["content"] for item in seen[1:]] == ["怎样记录健康变化？", "从当天感受记起。", "那皮肤呢？"]
    assert "2026-10-08" not in str(seen)


def test_interrupted_stream_has_error_after_partial_text(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "live")

    async def incomplete(*_args, **_kwargs):
        yield StreamChunk(text="部分回答")

    monkeypatch.setattr(assistant_stream, "chat_stream", incomplete)
    headers = auth_headers(register_and_login(client, username="stream_incomplete"))
    result = events(client.post(STREAM, headers=headers, json={"question": "怎么开始？", "mode": "general"}))
    assert [event["type"] for event in result] == ["source", "delta", "error"]
