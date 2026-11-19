from __future__ import annotations

import base64
import io
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from PIL import Image

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

    history = client.get("/api/v1/c/herlog/skin/observations", headers=headers).json()["data"]
    assert len(history) == 1
    assert history[0]["site"] == "面部"


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
