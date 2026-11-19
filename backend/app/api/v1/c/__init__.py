from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.c import auth, herlog, skin, weight_plus, weights

router = APIRouter()
router.include_router(auth.router)
router.include_router(herlog.router)
# weight_plus 必须先于 weights 注册：`/weights/goal` 与 `/weights/{weight_id}` 同形。
router.include_router(weight_plus.router)
router.include_router(weights.router)
router.include_router(skin.router)
