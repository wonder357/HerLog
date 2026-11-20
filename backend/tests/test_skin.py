from __future__ import annotations

import base64
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.models.herlog import SkinObservation
from app.schemas.herlog import SkinAnalyzeIn
from app.services import pending_store, skin_service, vision
from app.services.image_validation import DecodedImage

from tests.conftest import auth_headers, register_and_login

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _image_bytes(size: tuple[int, int] = (900, 900)) -> bytes:
    image = Image.new("RGB", size, (232, 210, 200))
    pixels = image.load()
    for x in range(0, size[0], 3):
        for y in range(0, size[1], 3):
            pixels[x, y] = (180 + (x % 40), 160 + (y % 40), 150)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def _payload(site: str = "面部", mime: str = "image/jpeg") -> dict:
    return {
        "site": site,
        "captured_at": datetime(2026, 11, 18, 9, 0, tzinfo=SHANGHAI).isoformat(),
        "mime": mime,
        "image_base64": base64.b64encode(_image_bytes()).decode("ascii"),
    }


def test_analyze_returns_three_sections_and_quality(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    response = client.post("/api/v1/c/herlog/skin/analyze", json=_payload(), headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["analysis_id"]
    assert data["site"] == "面部"
    assert data["visible"] and data["unclear"] and data["attention"]
    assert data["quality"]["level"] in {"good", "limited"}
    assert data["quality"]["message"]
    assert data["prompt_version"].startswith("herlog-skin")
    assert data["demo_sample"] is True
    assert data["model_id"].startswith("fixture:")


def test_discard_then_save_returns_410(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    analyzed = client.post("/api/v1/c/herlog/skin/analyze", json=_payload(), headers=headers).json()["data"]
    assert (
        client.delete(
            f"/api/v1/c/herlog/skin/pending/{analyzed['analysis_id']}", headers=headers
        ).status_code
        == 200
    )
    save = client.post(
        "/api/v1/c/herlog/skin/observations",
        json={"analysis_id": analyzed["analysis_id"]},
        headers=headers,
    )
    assert save.status_code == 410
    assert "过期" in save.json()["message"]
    assert client.get("/api/v1/c/herlog/skin/observations", headers=headers).json()["data"] == []


def test_save_is_idempotent_and_history_grows_once(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    analyzed = client.post("/api/v1/c/herlog/skin/analyze", json=_payload(), headers=headers).json()["data"]
    first = client.post(
        "/api/v1/c/herlog/skin/observations",
        json={"analysis_id": analyzed["analysis_id"]},
        headers=headers,
    )
    assert first.status_code == 200
    second = client.post(
        "/api/v1/c/herlog/skin/observations",
        json={"analysis_id": analyzed["analysis_id"]},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["data"]["id"] == first.json()["data"]["id"]
    assert first.json()["data"]["quality"] == analyzed["quality"]
    assert second.json()["data"]["quality"] == analyzed["quality"]
    assert first.json()["data"]["demo_sample"] is True

    history = client.get("/api/v1/c/herlog/skin/observations", headers=headers).json()["data"]
    assert len(history) == 1
    assert history[0]["site"] == "面部"
    assert history[0]["demo_sample"] is True


def test_history_filter_and_private_image(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    for site in ("面部", "颈部"):
        analyzed = client.post(
            "/api/v1/c/herlog/skin/analyze", json=_payload(site), headers=headers
        ).json()["data"]
        client.post(
            "/api/v1/c/herlog/skin/observations",
            json={"analysis_id": analyzed["analysis_id"]},
            headers=headers,
        )

    filtered = client.get(
        "/api/v1/c/herlog/skin/observations", params={"site": "颈部"}, headers=headers
    ).json()["data"]
    assert len(filtered) == 1 and filtered[0]["site"] == "颈部"

    record_id = filtered[0]["id"]
    detail = client.get(f"/api/v1/c/herlog/skin/observations/{record_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["mime"] == "image/jpeg"

    image = client.get(f"/api/v1/c/herlog/skin/observations/{record_id}/image", headers=headers)
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"
    assert image.headers["cache-control"] == "private, no-store"
    assert image.content[:2] == b"\xff\xd8"


def test_rejects_wrong_mime_and_broken_base64(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    wrong_mime = _payload(mime="image/png")
    response = client.post("/api/v1/c/herlog/skin/analyze", json=wrong_mime, headers=headers)
    assert response.status_code == 422
    assert "格式" in response.json()["message"]

    broken = _payload()
    broken["image_base64"] = "not-an-image!!!!"
    response = client.post("/api/v1/c/herlog/skin/analyze", json=broken, headers=headers)
    assert response.status_code == 422


def test_pending_is_capped_per_member(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    ids = [
        client.post("/api/v1/c/herlog/skin/analyze", json=_payload(), headers=headers).json()["data"][
            "analysis_id"
        ]
        for _ in range(4)
    ]
    oldest = client.post(
        "/api/v1/c/herlog/skin/observations", json={"analysis_id": ids[0]}, headers=headers
    )
    assert oldest.status_code == 410
    newest = client.post(
        "/api/v1/c/herlog/skin/observations", json={"analysis_id": ids[-1]}, headers=headers
    )
    assert newest.status_code == 200


def test_unknown_site_is_rejected(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client))
    response = client.post(
        "/api/v1/c/herlog/skin/analyze", json=_payload("脚底"), headers=headers
    )
    assert response.status_code == 422


def test_shanghai_month_filter_and_private_records(client: TestClient) -> None:
    owner = auth_headers(register_and_login(client, "skin_owner"))
    guest = auth_headers(register_and_login(client, "skin_guest"))
    path = "/api/v1/c/herlog/skin"
    saved = []
    for moment in ("2026-11-30T15:59:59Z", "2026-11-30T16:00:00Z", "2026-11-30T16:00:00Z"):
        payload = {**_payload("下巴"), "captured_at": moment}
        pending = client.post(f"{path}/analyze", json=payload, headers=owner).json()["data"]
        request = {"analysis_id": pending["analysis_id"]}
        assert client.post(f"{path}/observations", json=request, headers=guest).status_code == 410
        client.delete(f'{path}/pending/{request["analysis_id"]}', headers=guest)
        response = client.post(f"{path}/observations", json=request, headers=owner)
        assert response.status_code == 200
        saved.append(response.json()["data"]["id"])

    params = {"site": "下巴", "from": "2026-12-01", "to": "2026-12-01"}
    december = client.get(f"{path}/observations", params=params, headers=owner).json()["data"]
    assert [record["id"] for record in december] == [saved[2], saved[1]]
    latest = client.get(f"{path}/observations", params={**params, "limit": 1}, headers=owner).json()["data"]
    assert [record["id"] for record in latest] == [saved[2]]
    assert client.get(f"{path}/observations", headers=guest).json()["data"] == []
    assert client.get(f"{path}/observations/{saved[2]}", headers=guest).status_code == 404
    assert client.get(f"{path}/observations/{saved[2]}/image", headers=guest).status_code == 404
    assert client.get(f"{path}/observations/{saved[2]}/image").status_code == 401
    assert client.get(f"{path}/observations", params={"from": "2026-12-02", "to": "2026-12-01"}, headers=owner).status_code == 422


def test_pending_expires_after_ten_minutes(client: TestClient, monkeypatch) -> None:
    tick = [0]
    monkeypatch.setattr(pending_store, "time", SimpleNamespace(time=lambda: tick[0]))
    headers = auth_headers(register_and_login(client))
    path = "/api/v1/c/herlog/skin"
    pending = client.post(f"{path}/analyze", json=_payload(), headers=headers).json()["data"]
    assert client.get(f"{path}/observations", headers=headers).json()["data"] == []
    tick[0] = 600
    response = client.post(f"{path}/observations", json={"analysis_id": pending["analysis_id"]}, headers=headers)
    assert response.status_code == 410


def test_live_model_renders_only_approved_observations(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "HERLOG_SKIN_MODEL_MODE", "live")
    monkeypatch.setattr(settings, "HERLOG_SKIN_MODEL_API_KEY", "test-key")
    answer = {"visible": ["redness", "texture"], "unclear": "edges"}
    monkeypatch.setattr(vision, "_post_chat", lambda *_: answer)
    headers = auth_headers(register_and_login(client))
    path = "/api/v1/c/herlog/skin"

    response = client.post(f"{path}/analyze", json=_payload(), headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["visible"] == vision.VISIBLE["redness"] + vision.VISIBLE["texture"]
    assert data["unclear"] == vision.UNCLEAR["edges"]
    assert data["attention"] == vision.ATTENTION
    assert data["demo_sample"] is False
    assert data["inference_ms"] >= 0

    answer["visible"] = ["unexpected free text"]
    assert client.post(f"{path}/analyze", json=_payload(), headers=headers).status_code == 503
    assert client.get(f"{path}/observations", headers=headers).json()["data"] == []


def test_fixture_skips_deepseek_call(monkeypatch) -> None:
    monkeypatch.setattr(settings, "HERLOG_SKIN_MODEL_MODE", "fixture")

    def fail_if_called(*_):
        raise AssertionError("fixture must not call DeepSeek")

    monkeypatch.setattr(vision, "_post_chat", fail_if_called)
    image = DecodedImage(b"", "image/jpeg", 256, 256, 100, 21)
    observation = vision.observe_skin(image, "下巴")
    assert observation.demo_sample is True
    assert observation.quality == "limited"


def test_concurrent_save_returns_one_record_when_pending_cleanup_fails(tmp_path) -> None:
    database_path = (tmp_path / "skin-race.sqlite3").as_posix()
    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    Base.metadata.create_all(engine)
    customer_id = "a" * 32
    barrier = Barrier(2, timeout=5)

    class RacingPendingStore(pending_store.MemoryPendingStore):
        def get(self, owner, analysis_id):
            pending = super().get(owner, analysis_id)
            barrier.wait()
            return pending

        def delete(self, owner, analysis_id):
            raise RuntimeError("simulated cache cleanup failure")

    store = RacingPendingStore(3)
    with Session(engine) as session:
        pending = skin_service.analyze(session, customer_id, SkinAnalyzeIn(**_payload()), store)

    def save():
        with Session(engine) as session:
            return skin_service.save_observation(session, customer_id, pending.analysis_id, store)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            requests = [executor.submit(save) for _ in range(2)]
            (first, first_created), (second, second_created) = [request.result() for request in requests]
        assert first.id == second.id
        assert first_created != second_created
        with Session(engine) as session:
            assert session.scalars(select(SkinObservation.id)).all() == [first.id]
    finally:
        engine.dispose()
