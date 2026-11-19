from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """带 HTTP 状态码与可展示文案的业务异常。"""

    def __init__(self, status_code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.data = data


def not_found(message: str = "记录不存在") -> ApiError:
    return ApiError(404, message)


def conflict(message: str) -> ApiError:
    return ApiError(409, message)


def invalid(message: str) -> ApiError:
    return ApiError(422, message)


def unauthorized(message: str = "登录状态已失效，请重新登录") -> ApiError:
    return ApiError(401, message)
