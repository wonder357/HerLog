from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.c import auth, herlog, skin, weights

router = APIRouter()
router.include_router(auth.router)
router.include_router(herlog.router)
router.include_router(weights.router)
router.include_router(skin.router)
