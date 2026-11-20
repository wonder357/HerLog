from datetime import timedelta

from app.core.clock import local_today
from app.core.config import settings
from tests.conftest import auth_headers, register_and_login

ROOT = "/api/v1/c/herlog/exercise"
POSTS = ROOT + "/discussion/posts"


def member(client, username):
    session = register_and_login(client, username=username)
    return auth_headers(session), session["customer_id"]


def publish(client, headers, **values):
    return client.post(POSTS, headers=headers, json={
        "title": "散步路线", "body": "今天走了熟悉的小路。", "category": "experience",
        "client_key": "discussion-default", **values,
    })


def checkin(client, headers):
    yesterday = local_today() - timedelta(days=1)
    response = client.post(ROOT + "/checkins", headers=headers, json={
        "activity_code": "walk", "started_at": f"{yesterday}T19:00:00+08:00",
        "duration_minutes": 17, "effort": "easy", "client_key": "discussion-checkin",
    })
    assert response.status_code == 200
    return response.json()["data"]["id"]


def test_public_posts_are_opt_in_and_legacy_shares_stay_private(client, monkeypatch):
    monkeypatch.setattr(settings, "HERLOG_GROUP_INVITE_CODE", "private-test-invite")
    owner, _ = member(client, "exercise_poster")
    viewer, _ = member(client, "exercise_reader")
    own_checkin = checkin(client, owner)
    assert client.post(ROOT + "/groups/general/membership", headers=owner,
                       json={"consent": True, "invite_code": "private-test-invite"}).status_code == 200
    legacy = client.post(ROOT + "/shares", headers=owner, json={
        "group_key": "general", "checkin_id": own_checkin, "caption_code": "checked_in", "client_key": "legacy-exercise",
    }).json()["data"]
    assert client.get(POSTS, headers=viewer).json()["data"]["items"] == []
    assert client.get(f"{POSTS}/{legacy['public_id']}/replies", headers=viewer).status_code == 404
    assert client.get(POSTS).status_code == 401
    assert publish(client, viewer, checkin_id=own_checkin).status_code == 404

    response = publish(client, owner, category="checkin", checkin_id=own_checkin)
    assert response.status_code == 200, response.text
    post = response.json()["data"]
    assert publish(client, owner, category="checkin", checkin_id=own_checkin).json()["data"]["public_id"] == post["public_id"]
    assert publish(client, owner, category="checkin", checkin_id=own_checkin, body="另一条记录").status_code == 409
    feed = client.get(POSTS, headers=viewer, params={"category": "checkin"}).json()["data"]["items"]
    assert feed == [{**post, "mine": False}]
    assert set(feed[0]) == {
        "public_id", "title", "body", "category", "activity", "published_at", "mine", "reply_count",
        "like_count", "liked", "saved",
    }
    assert feed[0]["activity"] == "散步"
    assert client.get(POSTS, headers=viewer, params={"category": "question"}).json()["data"]["items"] == []
    assert client.delete(f"{POSTS}/{post['public_id']}", headers=viewer).status_code == 404
    assert client.delete(f"{ROOT}/checkins/{own_checkin}", headers=owner).status_code == 200
    assert client.get(POSTS, headers=viewer).json()["data"]["items"] == []


def test_discussion_text_limits_and_anonymous_reply_reporting(client, monkeypatch):
    owner, _ = member(client, "discussion_author")
    viewer, _ = member(client, "discussion_viewer")
    moderator, moderator_id = member(client, "discussion_mod")
    monkeypatch.setattr(settings, "HERLOG_GROUP_MODERATOR_ID", moderator_id)
    for body in ("我现在５５ｋｇ", "我建议每天只吃500大卡", "我的联系方式 https://example.com", "   "):
        assert publish(client, owner, body=body).status_code == 422
    assert publish(client, owner, weight_kg=55).status_code == 422

    post = publish(client, owner).json()["data"]
    post_path = f"{POSTS}/{post['public_id']}"
    replies = f"{post_path}/replies"
    payload = {"body": "我也喜欢下班后散步。", "client_key": "discussion-reply"}
    posted = client.post(replies, headers=viewer, json=payload)
    assert posted.status_code == 200
    item = posted.json()["data"]
    assert client.post(replies, headers=viewer, json=payload).json()["data"] == item
    assert set(item) == {"public_id", "published_at", "mine", "body"}
    assert client.get(replies, headers=owner).json()["data"]["items"] == [{**item, "mine": False}]
    assert client.get(POSTS, headers=owner).json()["data"]["items"][0]["reply_count"] == 1
    target = f"{replies}/{item['public_id']}"
    assert client.delete(target, headers=owner).status_code == 404
    assert client.post(target + "/reports", headers=owner, json={"reason_code": "other"}).status_code == 200
    assert client.get(replies, headers=owner).json()["data"]["items"] == []
    assert client.get(replies, headers=viewer).json()["data"]["items"]
    moderation = ROOT + "/discussion/moderation/reply-reports"
    assert client.get(moderation, headers=viewer).status_code == 404
    assert client.get(moderation, headers=moderator).json()["data"][0]["reply_id"] == item["public_id"]
    assert client.put(target + "/moderation", headers=moderator, json={"action": "hide"}).status_code == 200
    assert client.get(replies, headers=viewer).json()["data"]["items"] == []

    assert client.post(post_path + "/reports", headers=viewer, json={"reason_code": "other"}).status_code == 200
    assert client.get(POSTS, headers=viewer).json()["data"]["items"] == []
    assert client.get(replies, headers=viewer).status_code == 404
    assert client.get(POSTS, headers=owner).json()["data"]["items"]
    assert client.delete(post_path, headers=owner).status_code == 200
    assert client.get(POSTS, headers=owner).json()["data"]["items"] == []


def test_discussion_discovery_and_private_bookmarks(client, monkeypatch):
    monkeypatch.setattr("app.services.exercise_discussion.PAGE_SIZE", 2)
    owner, _ = member(client, "discovery_author")
    viewer, _ = member(client, "discovery_viewer")
    oldest = publish(client, owner, title="节奏与呼吸", body="周末溜达时聊到了呼吸节奏。").json()["data"]
    middle = publish(client, owner, title="户外散步路线", client_key="discussion-middle").json()["data"]
    newest = publish(client, viewer, title="力量练习提问", category="question").json()["data"]
    path = f"{POSTS}/{oldest['public_id']}"

    def feed(headers, **params):
        response = client.get(POSTS, headers=headers, params=params)
        assert response.status_code == 200, response.text
        return response.json()["data"]

    assert [row["public_id"] for row in feed(viewer, q="呼吸节奏")["items"]] == [oldest["public_id"]]
    assert feed(viewer, q="%")["items"] == []
    assert [row["public_id"] for row in feed(viewer, view="mine")["items"]] == [newest["public_id"]]
    assert feed(viewer, view="saved")["items"] == []
    for _ in range(2):
        assert client.put(path + "/reactions/like", headers=viewer).json()["data"] == {
            "like_count": 1, "liked": True, "saved": False,
        }
    assert client.put(path + "/reactions/save", headers=viewer).json()["data"]["saved"] is True
    assert feed(owner, view="saved")["items"] == []
    assert feed(viewer, view="saved")["items"][0]["public_id"] == oldest["public_id"]
    owner_item = feed(owner, q="呼吸节奏")["items"][0]
    assert (owner_item["like_count"], owner_item["liked"], owner_item["saved"]) == (1, False, False)

    first = feed(viewer, sort="popular")
    assert [row["public_id"] for row in first["items"]] == [oldest["public_id"], newest["public_id"]]
    second = feed(viewer, sort="popular", cursor=first["next_cursor"], cursor_likes=first["next_cursor_likes"])
    assert [row["public_id"] for row in second["items"]] == [middle["public_id"]]
    assert second["next_cursor"] is None
    for _ in range(2):
        assert client.delete(path + "/reactions/like", headers=viewer).json()["data"]["like_count"] == 0
    assert client.delete(path + "/reactions/save", headers=viewer).json()["data"]["saved"] is False
    assert feed(viewer, view="saved")["items"] == []

    client.put(path + "/reactions/save", headers=viewer)
    assert client.post(path + "/reports", headers=viewer, json={"reason_code": "other"}).status_code == 200
    assert feed(viewer, view="saved")["items"] == []
    assert feed(viewer, sort="popular", q="呼吸节奏")["items"] == []
    assert client.put(path + "/reactions/like", headers=viewer).status_code == 404


def test_discussion_edit_is_owned_and_preserves_private_attachment_boundary(client):
    owner, _ = member(client, "discussion_editor")
    viewer, _ = member(client, "discussion_visitor")
    post = publish(client, owner, category="checkin", checkin_id=checkin(client, owner)).json()["data"]
    path = f"{POSTS}/{post['public_id']}"
    payload = {"title": "夜间散步", "body": "想交流照明充足的路线。", "category": "question"}
    assert client.put(path, headers=viewer, json=payload).status_code == 404
    assert client.put(path, headers=owner, json={**payload, "body": "现在体重 50kg"}).status_code == 422
    assert client.put(path, headers=owner, json=payload).status_code == 200
    result = client.get(POSTS, headers=viewer, params={"q": "照明"}).json()["data"]["items"][0]
    assert {**post, **payload, "mine": False} == result
    assert client.delete(path, headers=owner).status_code == 200
    assert client.put(path, headers=owner, json=payload).status_code == 404
