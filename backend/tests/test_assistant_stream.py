import json
from uuid import uuid4

from app.core.config import settings
from app.core.errors import ApiError
from app.services import assistant_stream
from app.services.deepseek_client import StreamChunk
from tests.conftest import auth_headers, register_and_login

ROOT = "/api/v1/c/herlog"
STREAM = ROOT + "/assistant/stream"
HISTORY = ROOT + "/assistant/conversations"
PREF = ROOT + "/assistant/history-preference"


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
    monkeypatch.setattr(settings, "HERLOG_MODEL_API_KEY", "test-provider-key")
    headers = auth_headers(register_and_login(client, username="stream_general"))
    assert client.post(ROOT + "/periods", headers=headers, json={"start_day": "2026-10-08"}).status_code == 200
    seen = []

    async def fake_stream(messages, **options):
        seen.extend(messages)
        assert options["thinking"] is False
        yield StreamChunk(reasoning="internal reasoning")
        yield StreamChunk(text="第一段。", model_id="deepseek-response-model")
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
    assert result[-1]["answer"]["model_id"] == "deepseek-response-model"
    assert result[-1]["answer"]["record_refs"] == []
    assert [item["content"] for item in seen[1:]] == ["怎样记录健康变化？", "从当天感受记起。", "那皮肤呢？"]
    assert "2026-10-08" not in str(seen)


def test_interrupted_stream_has_error_after_partial_text(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "live")
    monkeypatch.setattr(settings, "HERLOG_MODEL_API_KEY", "test-provider-key")

    async def incomplete(*_args, **_kwargs):
        yield StreamChunk(text="部分回答")

    monkeypatch.setattr(assistant_stream, "chat_stream", incomplete)
    headers = auth_headers(register_and_login(client, username="stream_incomplete"))
    result = events(client.post(STREAM, headers=headers, json={"question": "怎么开始？", "mode": "general"}))
    assert [event["type"] for event in result] == ["source", "delta", "error"]


def test_general_defaults_to_live_and_missing_key_does_not_return_a_fixture(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", None)
    monkeypatch.setattr(settings, "HERLOG_MODEL_MODE", "fixture")
    monkeypatch.setattr(settings, "HERLOG_MODEL_API_KEY", "")
    assert settings.assistant_model_mode == "live"
    headers = auth_headers(register_and_login(client, username="stream_setup"))
    payload = {"question": "怎么开始？", "mode": "general"}
    assert events(client.post(STREAM, headers=headers, json=payload)) == [
        {"type": "error", "message": "首页助手尚未配置 DeepSeek API 密钥。"}
    ]

    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "fixture")
    fixture = events(client.post(STREAM, headers=headers, json=payload))
    assert fixture[0] == {"type": "source", "source": "fixture"}
    assert fixture[-1]["type"] == "complete"


def test_upstream_rejection_shows_a_safe_error_without_a_success_label(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "live")
    monkeypatch.setattr(settings, "HERLOG_MODEL_API_KEY", "test-provider-key")

    async def rejected(*_args, **_kwargs):
        if False:
            yield StreamChunk()
        raise ApiError(502, "upstream failed", {"status": 402, "detail": "private provider payload"})

    monkeypatch.setattr(assistant_stream, "chat_stream", rejected)
    headers = auth_headers(register_and_login(client, username="stream_provider_reject"))
    result = events(client.post(STREAM, headers=headers, json={"question": "怎么开始？", "mode": "general"}))
    assert result == [{"type": "error", "message": "DeepSeek API 账户余额不足。"}]


def test_conversation_history_opt_in_restore_rename_and_isolation(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "fixture")
    owner = auth_headers(register_and_login(client, username="history_owner"))
    other = auth_headers(register_and_login(client, username="history_reader"))
    conversation_id = uuid4().hex
    path = HISTORY + "/" + conversation_id
    payload = {
        "mode": "general", "question": "想记录睡眠，号码是 13800000000",
        "conversation_id": conversation_id, "client_turn_id": uuid4().hex, "create_conversation": True,
    }
    assert client.get(PREF, headers=owner).json()["data"]["enabled"] is None
    assert client.post(STREAM, headers=owner, json=payload).status_code == 409
    assert client.put(PREF, headers=owner, json={"enabled": True}).status_code == 200
    assert client.get(HISTORY, headers=owner).json()["data"]["items"] == []
    first = events(client.post(STREAM, headers=owner, json=payload))
    assert first[0]["conversation"]["title"] == "关于睡眠记录"
    assert first[-1]["type"] == "complete"
    restored = client.get(path, headers=owner).json()["data"]
    assert len(restored["turns"]) == 1
    assert restored["turns"][0]["answer"] == first[-1]["answer"]
    again = events(client.post(STREAM, headers=owner, json=payload))
    assert [event["type"] for event in again] == ["accepted", "source", "complete"]
    assert client.post(STREAM, headers=owner, json={**payload, "question": "另一条问题"}).status_code == 409
    assert client.put(path, headers=owner, json={"title": "   "}).status_code == 422
    assert client.put(path, headers=owner, json={"title": " 睡眠日记 "}).json()["data"]["title"] == "睡眠日记"
    assert client.post(HISTORY + "/search", headers=owner, json={"q": "睡眠"}).json()["data"]["items"][0]["title"] == "睡眠日记"
    assert client.get(path, headers=other).status_code == 404
    assert client.put(path, headers=other, json={"title": "他人的对话"}).status_code == 404
    assert client.delete(path, headers=other).status_code == 404
    assert client.get(HISTORY, headers=other, params={"cursor": conversation_id}).status_code == 404
    assert client.post(STREAM, headers=other, json=payload).status_code == 404

    assert client.put(PREF, headers=owner, json={"enabled": False}).status_code == 200
    assert client.get(path, headers=owner).status_code == 200
    assert client.post(STREAM, headers=owner, json={**payload, "client_turn_id": uuid4().hex}).status_code == 409
    transient = events(client.post(STREAM, headers=owner, json={"mode": "general", "question": "临时记录"}))
    assert [event["type"] for event in transient] == ["source", "delta", "delta", "complete"]
    assert client.get(path, headers=owner).json()["data"]["turns"] == restored["turns"]
    assert client.delete(path, headers=owner).status_code == 200
    assert client.get(path, headers=owner).status_code == 404
    assert client.put(PREF, headers=owner, json={"enabled": True}).status_code == 200
    assert client.post(STREAM, headers=owner, json=payload).status_code == 404


def test_saved_context_stays_in_one_conversation_and_retry_reuses_turn(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "live")
    monkeypatch.setattr(settings, "HERLOG_MODEL_API_KEY", "test-provider-key")
    headers = auth_headers(register_and_login(client, username="history_context"))
    assert client.put(PREF, headers=headers, json={"enabled": True}).status_code == 200
    assert client.post(ROOT + "/periods", headers=headers, json={"start_day": "2026-10-08"}).status_code == 200
    context = []
    interrupted = [False]

    async def provider(messages, **options):
        context.append([message["content"] for message in messages][1:])
        yield StreamChunk(text="一段回复。")
        if not interrupted[0]:
            yield StreamChunk(done=True)

    monkeypatch.setattr(assistant_stream, "chat_stream", provider)
    conversation_id = uuid4().hex

    def send(question, mode="general", **values):
        return {
            "mode": mode, "question": question, "conversation_id": conversation_id,
            "client_turn_id": uuid4().hex, "create_conversation": True, **values,
        }

    events(client.post(STREAM, headers=headers, json=send("怎么记感受？")))
    records = events(client.post(STREAM, headers=headers, json=send("最近一次经期是哪天？", "records")))
    assert "2026-10-08" in records[-1]["answer"]["answer"]
    interrupted[0] = True
    interrupted_turn = send("那睡眠呢？", history=[{"question": "另一会话", "answer": "另一会话的回复"}])
    failed = events(client.post(STREAM, headers=headers, json=interrupted_turn))
    assert failed[-1]["type"] == "error"
    assert context[-1] == ["怎么记感受？", "一段回复。", "那睡眠呢？"]
    item = client.get(HISTORY + "/" + conversation_id, headers=headers).json()["data"]["turns"][-1]
    assert item["status"] == "failed" and item["partial"] == "一段回复。"
    interrupted[0] = False
    events(client.post(STREAM, headers=headers, json=interrupted_turn))
    saved = client.get(HISTORY + "/" + conversation_id, headers=headers).json()["data"]["turns"]
    assert len(saved) == 3 and saved[-1]["id"] == item["id"] and saved[-1]["status"] == "complete"
    events(client.post(STREAM, headers=headers, json=send("另一条新对话", conversation_id=uuid4().hex)))
    assert context[-1] == ["另一条新对话"]
