# backend/src/schemas/contacts.py
"""
Pydantic схеми для контактів.
Використовуються в API endpoints.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from src.models.base import ContactStatus

from .base import TimestampMixin, UUIDMixin

# === Request Schemas ===


class ContactCreate(BaseModel):
    """Схема створення контакту"""

    phone_number: str = Field(..., min_length=10, max_length=15)
    name: Optional[str] = Field(None, max_length=255)
    tags: List[str] = Field(default_factory=list)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Видаляємо всі нецифрові символи
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone must be 10-15 digits")
        return digits

    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "380671234567",
                "name": "John Doe",
                "tags": ["vip", "active"],
            }
        }


class ContactUpdate(BaseModel):
    """Схема оновлення контакту"""

    name: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None

    class Config:
        json_schema_extra = {
            "example": {"name": "John Smith", "tags": ["vip", "premium"]}
        }


class ContactImport(BaseModel):
    """Схема імпорту контакту з файлу"""

    phone_number: str
    name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


# === Response Schemas ===


class ContactResponse(UUIDMixin, TimestampMixin):
    """Повна інформація про контакт для API"""

    phone_number: str
    name: Optional[str] = None
    unread_count: int
    status: ContactStatus
    last_message_at: Optional[datetime] = None
    source: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "phone_number": "380671234567",
                "name": "John Doe",
                "unread_count": 3,
                "status": "new",
                "last_message_at": "2024-01-15T10:30:00Z",
                "source": "import_csv",
                "tags": ["vip"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class ContactListResponse(BaseModel):
    """Скорочена інформація для списку"""

    id: UUID
    phone_number: str
    name: Optional[str] = None
    unread_count: int
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContactImportResult(BaseModel):
    """Результат імпорту контактів"""

    total: int = Field(..., description="Total contacts in file")
    imported: int = Field(..., description="Successfully imported")
    skipped: int = Field(..., description="Skipped (duplicates)")
    errors: List[str] = Field(default_factory=list, description="Error messages")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "imported": 95,
                "skipped": 3,
                "errors": [
                    "Row 5: Invalid phone number",
                    "Row 12: Missing phone number",
                ],
            }
        }
