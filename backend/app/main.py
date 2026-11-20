"""她记 · 女性健康记录助手 —— 比赛分支 API 入口。

启动前对齐的两条约束：
1. 后台调度器只在非 contest 环境启动（`settings.ENV != "contest"`），比赛五页不需要它。
2. 只有 `/api/v1/c/auth/username-register` 与 `/username-login` 允许匿名，其余业务路由都要会员会话。
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.v1.c import router as api_router
from app.core.config import settings
from app.core.errors import ApiError
from app.db.session import get_engine

logger = logging.getLogger("herlog")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _scheduler_enabled() -> bool:
    """原调度器用于既有业务同步；比赛环境不启动。"""

    return settings.ENV != "contest"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if _scheduler_enabled():
        logger.info("scheduler would start for ENV=%s", settings.ENV)
    else:
        logger.info("scheduler disabled for contest environment")
    if settings.REDIS_ENABLED:
        try:
            from app.services.pending_store import build_pending_store

            build_pending_store()
            logger.info("skin pending store: redis")
        except Exception as exc:  # pragma: no cover - 依赖外部服务
            logger.warning("redis unavailable, falling back to memory store: %s", exc)
    else:
        logger.info("skin pending store: memory")
    yield
    logger.info("shutdown complete")


app = FastAPI(title="她记 · 女性健康记录助手 API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "token"],
    expose_headers=["Content-Type"],
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    """请求日志只记耗时、状态和请求编号，不落图片与问题原文。"""

    request_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - started) * 1000
    response.headers["X-Request-Id"] = request_id
    path = request.url.path
    if path.startswith("/api/v1/c/herlog/"):
        response.headers["Cache-Control"] = "private, no-store"
    if path.startswith("/api/v1/c/herlog/fertility-daily/"):
        path = "/api/v1/c/herlog/fertility-daily/{day}"
    logger.info(
        "rid=%s %s %s -> %s %.1fms",
        request_id,
        request.method,
        path,
        response.status_code,
        elapsed,
    )
    return response


def _error(status_code: int, message: str, data=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "message": message, "data": data},
    )


@app.exception_handler(ApiError)
async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
    return _error(exc.status_code, exc.message, exc.data)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    if request.url.path == "/api/v1/c/herlog/account/password":
        return _error(422, "请输入当前密码和至少 8 位的新密码")
    first = exc.errors()[0] if exc.errors() else {}
    message = first.get("msg", "请求参数不正确")
    message = message.replace("Value error, ", "")
    location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    if location:
        message = f"{location}: {message}"
    return _error(422, message)


@app.exception_handler(IntegrityError)
async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("integrity error: %s", type(exc).__name__)
    return _error(409, "该记录已存在，请刷新后重试")


@app.get("/health", tags=["ops"])
def health() -> dict:
    mysql_state = "ok"
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - 依赖外部服务
        mysql_state = f"error: {type(exc).__name__}"
    redis_state = "disabled"
    if settings.REDIS_ENABLED:
        try:
            import redis

            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                socket_timeout=2,
            )
            client.ping()
            redis_state = "ok"
        except Exception as exc:  # pragma: no cover
            redis_state = f"error: {type(exc).__name__}"
    return {
        "status": "ok" if mysql_state == "ok" else "degraded",
        "env": settings.ENV,
        "mysql": mysql_state,
        "redis": redis_state,
        "model_mode": settings.HERLOG_MODEL_MODE,
        "skin_model_mode": settings.skin_model_mode,
    }


app.include_router(api_router, prefix="/api/v1/c")
