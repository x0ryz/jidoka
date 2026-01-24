from typing import Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .base import TimestampMixin, UUIDMixin


class QuickReplyBase(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Display title for the quick reply",
    )
    content: Dict[str, str] = Field(
        default_factory=dict, description="Content in different languages"
    )


class QuickReplyCreate(QuickReplyBase):
    """Schema for creating a new quick reply"""

    pass


class QuickReplyUpdate(BaseModel):
    """Schema for updating a quick reply"""

    title: str | None = Field(None, min_length=1, max_length=100)
    content: Dict[str, str] | None = None


class QuickReplyResponse(QuickReplyBase, UUIDMixin, TimestampMixin):
    """Schema for quick reply response"""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Greeting Message",
                "content": {
                    "uk": "Привіт! Як справи?",
                    "en": "Hello! How are you?",
                    "ru": "Привет! Как дела?",
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    )


class QuickReplyListResponse(BaseModel):
    """Schema for quick reply list item"""

    id: UUID
    title: str

    model_config = ConfigDict(from_attributes=True)


class QuickReplyTextResponse(BaseModel):
    """Schema for getting text in specific language"""

    text: str
    language: str

    model_config = ConfigDict(
        json_schema_extra={"example": {
            "text": "Привіт! Як справи?", "language": "uk"}}
    )
