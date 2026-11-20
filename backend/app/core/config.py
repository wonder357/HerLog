from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

# 环境文件固定在 backend/.env（已被 .gitignore 的 backend/.env* 覆盖），与启动目录无关。
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """运行期配置。字段名与比赛环境文件中的键一致；进程环境变量优先于环境文件。"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore", case_sensitive=True
    )

    ENV: str = "local"
    DEBUG: bool = False

    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 13306
    MYSQL_DATABASE: str = "herlog_contest"
    MYSQL_USER: str = "herlog"
    MYSQL_PASSWORD: str = ""
    DATABASE_URL: str | None = None

    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 16379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_ENABLED: bool = False

    SESSION_TTL_HOURS: int = 24 * 7
    PENDING_TTL_SECONDS: int = 600
    PENDING_MAX_PER_MEMBER: int = 3
    SKIN_MAX_UPLOAD_BYTES: int = 3 * 1024 * 1024
    SKIN_MAX_PIXELS: int = 40_000_000

    HERLOG_MODEL_MODE: Literal["fixture", "live"] = "fixture"
    HERLOG_MODEL_BASE_URL: str = "https://api.deepseek.com"
    HERLOG_MODEL_ID: str = "deepseek-flash"
    HERLOG_MODEL_API_KEY: str = ""
    HERLOG_ASSISTANT_MODEL_MODE: Literal["fixture", "live"] | None = None
    HERLOG_SKIN_MODEL_MODE: Literal["fixture", "live"] | None = None
    HERLOG_SKIN_MODEL_API_KEY: str = ""
    HERLOG_GROUP_INVITE_CODE: str = ""
    HERLOG_GROUP_MODERATOR_ID: str = ""
    HERLOG_MODEL_TIMEOUT_SECONDS: float = 60.0
    HERLOG_PROMPT_VERSION: str = "v1"

    @property
    def skin_model_mode(self) -> Literal["fixture", "live"]:
        return self.HERLOG_SKIN_MODEL_MODE or self.HERLOG_MODEL_MODE

    @property
    def assistant_model_mode(self) -> Literal["fixture", "live"]:
        return self.HERLOG_ASSISTANT_MODEL_MODE or self.HERLOG_MODEL_MODE

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        password = quote_plus(self.MYSQL_PASSWORD)
        user = quote_plus(self.MYSQL_USER)
        return (
            f"mysql+pymysql://{user}:{password}@{self.MYSQL_HOST}:{self.MYSQL_PORT}"
            f"/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo("Asia/Shanghai")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
