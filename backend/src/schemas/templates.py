# backend/src/schemas/templates.py
"""
Pydantic схеми для шаблонів повідомлень.
"""

from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, Field

from .base import TimestampMixin, UUIDMixin

# === Response Schemas ===


class TemplateResponse(UUIDMixin, TimestampMixin):
    """Інформація про шаблон"""

    waba_id: UUID
    meta_template_id: str
    name: str
    language: str
    status: str
    category: str
    components: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "waba_id": "789e4567-e89b-12d3-a456-426614174000",
                "meta_template_id": "1234567890",
                "name": "hello_world",
                "language": "en_US",
                "status": "APPROVED",
                "category": "MARKETING",
                "components": [{"type": "BODY", "text": "Hello {{1}}!"}],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class TemplateListResponse(BaseModel):
    """Скорочена інформація для списку"""

    id: UUID
    name: str
    language: str
    status: str
    category: str

    class Config:
        from_attributes = True
