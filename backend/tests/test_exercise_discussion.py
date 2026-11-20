import base64
import io
from datetime import timedelta

from PIL import Image

from app.core.clock import local_today
from app.core.config import settings
from tests.conftest import auth_headers, register_and_login

ROOT = "/api/v1/c/herlog/exercise"
POSTS = ROOT + "/discussion/posts"

POST_FIELDS = {"public_id", "title", "body", "category", "activity", "visibility", "author",
               "published_at", "mine", "reply_count", "like_count", "liked", "image_ids"}
REPLY_FIELDS = {"public_id", "published_at", "mine", "body", "visibility", "author", "like_count", "liked"}


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


def png_payload(size=12, color=(210, 140, 160)):
    buffer = io.BytesIO()
    Image.new("RGB", (size, size), color).save(buffer, "PNG")
    return {"mime": "image/png", "image_base64": base64.b64encode(buffer.getvalue()).decode()}


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
    assert set(feed[0]) == POST_FIELDS
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
    assert set(item) == REPLY_FIELDS
    assert item["visibility"] == "anonymous" and item["author"] is None
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


def test_visibility_images_and_likes(client):
    owner, _ = member(client, "social_author")
    reader, _ = member(client, "social_reader")

    public = publish(client, owner, visibility="public", title="公开的运动小结", client_key="social-public",
                     images=[png_payload(), png_payload(color=(120, 170, 200))])
    assert public.status_code == 200, public.text
    post = public.json()["data"]
    assert post["visibility"] == "public"
    assert post["author"] == "social_author"
    assert post["mine"] is True
    assert len(post["image_ids"]) == 2

    anonymous = publish(client, owner, title="匿名的运动小结", client_key="social-anon").json()["data"]
    assert anonymous["visibility"] == "anonymous" and anonymous["author"] is None

    # 图片：登录后可读，未登录 401，错误的图片 id 404
    post_path = f"{POSTS}/{post['public_id']}"
    image_path = f"{post_path}/images/{post['image_ids'][0]}"
    image = client.get(image_path, headers=reader)
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"
    assert image.content[:2] == b"\xff\xd8"
    assert client.get(image_path).status_code == 401
    assert client.get(f"{post_path}/images/999999", headers=reader).status_code == 404

    # 点赞：幂等、计数正确、按账号区分 liked
    assert client.post(post_path + "/like", headers=reader).json()["data"] == {"liked": True, "like_count": 1}
    assert client.post(post_path + "/like", headers=reader).json()["data"] == {"liked": True, "like_count": 1}
    author_view = next(item for item in client.get(POSTS, headers=owner).json()["data"]["items"]
                       if item["public_id"] == post["public_id"])
    reader_view = next(item for item in client.get(POSTS, headers=reader).json()["data"]["items"]
                       if item["public_id"] == post["public_id"])
    assert author_view["like_count"] == 1 and author_view["liked"] is False
    assert reader_view["liked"] is True
    assert client.delete(post_path + "/like", headers=reader).json()["data"] == {"liked": False, "like_count": 0}

    # 回复：公开回复展示昵称，回复点赞独立计数
    reply_path = post_path + "/replies"
    named = client.post(reply_path, headers=reader, json={
        "body": "我也喜欢这样的路线。", "client_key": "social-reply-1", "visibility": "public",
    }).json()["data"]
    assert named["author"] == "social_reader" and named["visibility"] == "public"
    reply_like = f"{reply_path}/{named['public_id']}/like"
    assert client.post(reply_like, headers=owner).json()["data"] == {"liked": True, "like_count": 1}
    listed = client.get(reply_path, headers=reader).json()["data"]["items"][0]
    assert listed["like_count"] == 1 and listed["liked"] is False
    assert client.delete(reply_like, headers=owner).json()["data"] == {"liked": False, "like_count": 0}


def test_popular_sort_and_my_posts_scope(client):
    first, _ = member(client, "sort_first")
    second, _ = member(client, "sort_second")
    reader, _ = member(client, "sort_reader")

    older = publish(client, first, title="最早的一条", client_key="sort-one").json()["data"]
    middle = publish(client, first, title="中间的一条", client_key="sort-two").json()["data"]
    newest = publish(client, second, title="最新的一条", client_key="sort-three").json()["data"]

    assert [item["public_id"] for item in client.get(POSTS, headers=reader).json()["data"]["items"]] == [
        newest["public_id"], middle["public_id"], older["public_id"],
    ]
    client.post(f"{POSTS}/{older['public_id']}/like", headers=reader)
    popular = client.get(POSTS, headers=reader, params={"sort": "popular"}).json()["data"]
    assert popular["items"][0]["public_id"] == older["public_id"]
    assert set(popular) == {"items", "next_cursor"}

    mine = client.get(POSTS, headers=first, params={"scope": "mine"}).json()["data"]["items"]
    assert {item["public_id"] for item in mine} == {older["public_id"], middle["public_id"]}
    assert all(item["mine"] for item in mine)
