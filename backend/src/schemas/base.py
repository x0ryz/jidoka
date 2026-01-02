from datetime import datetime
from typing import Any, Generic, List, TypeVar
from uuid import UUID

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    """Стандартна успішна відповідь"""

    status: str = "success"
    message: str
    data: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Стандартна помилка"""

    status: str = "error"
    code: int
    detail: str
    payload: dict[str, Any] | None = None


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Пагінована відповідь"""

    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool

    class Config:
        from_attributes = True


class TimestampMixin(BaseModel):
    """Міксін для полів created_at/updated_at"""

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UUIDMixin(BaseModel):
    """Міксін для UUID id"""

    id: UUID

    class Config:
        from_attributes = True
