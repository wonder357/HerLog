from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """沿用 ApiResponse：成功固定 200 + success，data 携带业务负载。"""

    code: int = 200
    message: str = "success"
    data: T | None = None


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def ok(data: Any = None) -> dict[str, Any]:
    return {"code": 200, "message": "success", "data": data}
