import json

from app.core.config import settings
from app.services import assistant_stream
from app.services.deepseek_client import StreamChunk
from tests.conftest import auth_headers, register_and_login

ROOT = "/api/v1/c/herlog"
STREAM = ROOT + "/assistant/chats/stream"
CHATS = ROOT + "/assistant/chats"


def events(response):
    assert response.status_code == 200
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def ask(client, headers, question, chat_id=None, mode="general"):
    payload = {"mode": mode, "question": question}
    if chat_id is not None:
        payload["chat_id"] = chat_id
    return events(client.post(STREAM, headers=headers, json=payload))


def test_first_exchange_creates_chat_titled_by_question(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "fixture")
    headers = auth_headers(register_and_login(client, username="chat_title"))
    question = "晚上总是睡不好，白天没精神，要怎么记录？"

    chat_id = ask(client, headers, question)[-1]["chat_id"]
    assert isinstance(chat_id, int)

    listing = client.get(CHATS, headers=headers).json()["data"]
    assert len(listing) == 1
    assert listing[0]["id"] == chat_id
    assert listing[0]["message_count"] == 2
    assert question.startswith(listing[0]["title"].rstrip("…")[:10])
    assert len(listing[0]["title"]) <= 25


def test_second_exchange_appends_to_same_chat(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "fixture")
    headers = auth_headers(register_and_login(client, username="chat_append"))
    chat_id = ask(client, headers, "怎样记录睡眠？")[-1]["chat_id"]

    again = ask(client, headers, "那要记哪些内容？", chat_id=chat_id)
    assert again[-1]["chat_id"] == chat_id

    detail = client.get(f"{CHATS}/{chat_id}", headers=headers).json()["data"]
    assert [item["role"] for item in detail["messages"]] == ["user", "assistant", "user", "assistant"]
    assert detail["messages"][2]["content"] == "那要记哪些内容？"
    assert detail["messages"][1]["source"] == "fixture"
    assert len(client.get(CHATS, headers=headers).json()["data"]) == 1


def test_live_answer_is_saved_with_deepseek_source(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "live")
    monkeypatch.setattr(settings, "HERLOG_MODEL_API_KEY", "test-key")

    async def fake_stream(_messages, **_options):
        yield StreamChunk(text="先固定起床时间。")
        yield StreamChunk(text="连续记一周再看规律。")
        yield StreamChunk(done=True)

    monkeypatch.setattr(assistant_stream, "chat_stream", fake_stream)
    headers = auth_headers(register_and_login(client, username="chat_live"))
    chat_id = ask(client, headers, "作息怎么开始记？")[-1]["chat_id"]

    detail = client.get(f"{CHATS}/{chat_id}", headers=headers).json()["data"]
    assert detail["messages"][1]["content"] == "先固定起床时间。连续记一周再看规律。"
    assert detail["messages"][1]["source"] == "deepseek"


def test_chats_list_newest_first(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "fixture")
    headers = auth_headers(register_and_login(client, username="chat_order"))
    first = ask(client, headers, "第一个问题")[-1]["chat_id"]
    second = ask(client, headers, "第二个问题")[-1]["chat_id"]

    assert [item["id"] for item in client.get(CHATS, headers=headers).json()["data"]] == [second, first]


def test_rename_and_delete_chat(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "fixture")
    headers = auth_headers(register_and_login(client, username="chat_rename"))
    chat_id = ask(client, headers, "皮肤泛红怎么记？")[-1]["chat_id"]

    renamed = client.patch(f"{CHATS}/{chat_id}", headers=headers, json={"title": "皮肤记录计划"})
    assert renamed.status_code == 200
    assert renamed.json()["data"]["title"] == "皮肤记录计划"
    assert client.patch(f"{CHATS}/{chat_id}", headers=headers, json={"title": "   "}).status_code == 422

    removed = client.delete(f"{CHATS}/{chat_id}", headers=headers)
    assert removed.status_code == 200
    assert client.get(f"{CHATS}/{chat_id}", headers=headers).status_code == 404
    assert client.get(CHATS, headers=headers).json()["data"] == []


def test_other_member_cannot_read_or_change_chat(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_ASSISTANT_MODEL_MODE", "fixture")
    owner = auth_headers(register_and_login(client, username="chat_owner"))
    other = auth_headers(register_and_login(client, username="chat_other"))
    chat_id = ask(client, owner, "经期怎么记？")[-1]["chat_id"]

    assert client.get(f"{CHATS}/{chat_id}", headers=other).status_code == 404
    assert client.patch(f"{CHATS}/{chat_id}", headers=other, json={"title": "改标题"}).status_code == 404
    assert client.delete(f"{CHATS}/{chat_id}", headers=other).status_code == 404
    assert client.get(CHATS, headers=other).json()["data"] == []
    assert client.get(CHATS, headers=owner).json()["data"][0]["id"] == chat_id


def test_chat_endpoints_require_login(client):
    assert client.get(CHATS).status_code == 401
    assert client.get(f"{CHATS}/1").status_code == 401
