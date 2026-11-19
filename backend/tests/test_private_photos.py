import base64
from datetime import timedelta
from io import BytesIO

from PIL import Image

from app.core.clock import local_today
from tests.conftest import auth_headers, register_and_login

ROOT = "/api/v1/c/herlog"
WEIGHTS = ROOT + "/weights"
CHECKINS = ROOT + "/exercise/checkins"
PROFILE = ROOT + "/profile"
MALFORMED = {"mime": "image/jpeg", "image_base64": "!" * 32}


def photo(color="pink"):
    output = BytesIO()
    image = Image.new("RGB", (1200, 600), color)
    exif = Image.Exif()
    exif[270] = "private test metadata"
    image.save(output, "JPEG", exif=exif)
    return {"mime": "image/jpeg", "image_base64": base64.b64encode(output.getvalue()).decode()}


def members(client):
    a = register_and_login(client, username="photo_owner")
    b = register_and_login(client, username="photo_viewer")
    return auth_headers(a), auth_headers(b), a["customer_id"]


def measurement():
    return f"{local_today() - timedelta(days=1)}T08:00:00+08:00"


def get_photo(client, path, headers, *, size=(1024, 512)):
    response = client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers["Content-Type"] == "image/jpeg"
    assert response.headers["Cache-Control"] == "private, no-store"
    with Image.open(BytesIO(response.content)) as image:
        assert image.size == size
        assert not image.getexif()
        assert image.format == "JPEG"
    return response.content


def test_weight_photo_saves_and_updates_with_its_record(client):
    owner, viewer, _ = members(client)
    payload = {"client_key": "with-photo", "kg": "60.25", "measured_at": measurement(), "photo": photo()}
    invalid = client.post(WEIGHTS, headers=owner, json={**payload, "photo": MALFORMED})
    assert invalid.status_code == 422
    assert client.get(WEIGHTS, headers=owner).json()["data"]["total"] == 0
    created = client.post(WEIGHTS, headers=owner, json=payload).json()["data"]
    assert created["has_photo"]
    assert client.post(WEIGHTS, headers=owner, json=payload).json()["data"] == created
    assert client.post(WEIGHTS, headers=owner, json={**payload, "photo": photo("blue")}).status_code == 409
    assert client.get(WEIGHTS, headers=owner).json()["data"]["items"] == [created]
    record = f"{WEIGHTS}/{created['id']}"
    path = record + "/photo"
    original = get_photo(client, path, owner)
    assert client.get(path).status_code == 401
    assert client.get(path, headers=viewer).status_code == 404
    assert client.put(record, headers=viewer, json=payload).status_code == 404
    edit = {key: value for key, value in payload.items() if key != "photo"}
    assert client.put(record, headers=owner, json={**edit, "kg": "66", "photo": MALFORMED}).status_code == 422
    assert client.get(record, headers=owner).json()["data"]["kg"] == created["kg"]
    assert client.put(record, headers=owner, json=edit).json()["data"]["has_photo"]
    assert get_photo(client, path, owner) == original
    assert client.put(record, headers=owner, json={**edit, "photo": photo("blue")}).json()["data"]["has_photo"]
    assert get_photo(client, path, owner) != original
    assert not client.put(record, headers=owner, json={**edit, "photo": None}).json()["data"]["has_photo"]
    assert client.get(path, headers=owner).status_code == 404
    assert client.put(record, headers=owner, json=payload).json()["data"]["has_photo"]
    assert client.delete(record, headers=owner).status_code == 200
    assert client.get(path, headers=owner).status_code == 404


def test_exercise_photo_stays_private_even_on_public_discussion(client):
    owner, viewer, _ = members(client)
    payload = {"client_key": "with-photo", "activity_code": "walk", "started_at": measurement(),
               "duration_minutes": 15, "effort": "easy", "photo": photo()}
    assert client.post(CHECKINS, headers=owner, json={**payload, "photo": MALFORMED}).status_code == 422
    assert client.get(CHECKINS, headers=owner).json()["data"] == []
    created = client.post(CHECKINS, headers=owner, json=payload).json()["data"]
    assert created["has_photo"]
    assert client.post(CHECKINS, headers=owner, json=payload).json()["data"] == created
    assert client.get(CHECKINS, headers=owner).json()["data"] == [created]
    record = f"{CHECKINS}/{created['id']}"
    path = record + "/photo"
    original = get_photo(client, path, owner)
    assert client.get(path, headers=viewer).status_code == 404
    assert client.put(path, headers=viewer, json={"photo": photo("blue")}).status_code == 404
    assert client.put(path, headers=owner, json={"photo": MALFORMED}).status_code == 422
    assert get_photo(client, path, owner) == original
    posts = ROOT + "/exercise/discussion/posts"
    result = client.post(posts, headers=owner, json={
        "title": "散步记录", "body": "走了一段熟悉的小路。", "category": "checkin",
        "client_key": "with-photo-post", "checkin_id": created["id"],
    })
    assert result.status_code == 200, result.text
    public = client.get(posts, headers=viewer).json()["data"]["items"][0]
    assert set(public) == {"public_id", "title", "body", "category", "activity", "published_at", "mine", "reply_count"}
    assert public["activity"] == "散步"
    assert client.put(path, headers=owner, json={"photo": photo("blue")}).json()["data"]["has_photo"]
    assert get_photo(client, path, owner) != original
    assert not client.put(path, headers=owner, json={"photo": None}).json()["data"]["has_photo"]
    assert client.get(path, headers=owner).status_code == 404
    assert client.put(path, headers=owner, json={"photo": photo()}).json()["data"]["has_photo"]
    assert client.delete(record, headers=owner).status_code == 200
    assert client.get(path, headers=owner).status_code == 404


def test_avatar_updates_with_profile_and_can_be_cleared(client):
    owner, viewer, owner_id = members(client)
    path = PROFILE + "/avatar"
    assert client.get(path, headers=owner).status_code == 404
    assert client.put(PROFILE, headers=owner, json={"height_cm": 165, "avatar": photo()}).json()["data"]["has_avatar"]
    original = get_photo(client, path, owner, size=(512, 256))
    assert client.get(path, headers=viewer).status_code == 404
    assert client.get(path, headers=viewer, params={"customer_id": owner_id}).status_code == 404
    assert client.get(ROOT + "/health-summary", headers=owner).json()["data"]["has_avatar"]
    assert client.put(PROFILE, headers=owner, json={"height_cm": 170, "avatar": MALFORMED}).status_code == 422
    assert float(client.get(PROFILE, headers=owner).json()["data"]["height_cm"]) == 165
    assert client.put(PROFILE, headers=owner, json={"height_cm": 166}).json()["data"]["has_avatar"]
    assert get_photo(client, path, owner, size=(512, 256)) == original
    assert client.put(PROFILE, headers=owner, json={"avatar": photo("blue")}).json()["data"]["has_avatar"]
    assert get_photo(client, path, owner, size=(512, 256)) != original
    assert not client.put(PROFILE, headers=owner, json={"avatar": None}).json()["data"]["has_avatar"]
    assert client.get(path, headers=owner).status_code == 404
