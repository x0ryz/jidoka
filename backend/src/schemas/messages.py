# backend/src/schemas/messages.py
"""
Pydantic схеми для повідомлень.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from src.models.base import MessageDirection, MessageStatus

from .base import TimestampMixin, UUIDMixin

# === Request Schemas ===


class MessageCreate(BaseModel):
    """Схема створення повідомлення через API"""

    phone_number: str = Field(..., description="Recipient phone number")
    type: Literal["text", "template"] = "text"
    body: str = Field(..., description="Message text or template ID")
    template_id: Optional[UUID] = None


class WhatsAppMessage(BaseModel):
    """Схема для відправки через воркер (внутрішня)"""

    phone_number: str
    type: Literal["text", "template"]
    body: str
    request_id: str = Field(default_factory=lambda: str(uuid4()))

    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "380671234567",
                "type": "text",
                "body": "Hello from API",
                "request_id": "req_123",
            }
        }


# === Response Schemas ===


class MediaFileResponse(BaseModel):
    """Інформація про медіа файл"""

    id: UUID
    file_name: str
    file_mime_type: str
    caption: Optional[str] = None
    url: str = Field(..., description="Presigned URL for download")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "file_name": "image.jpg",
                "file_mime_type": "image/jpeg",
                "caption": "Photo caption",
                "url": "https://storage.example.com/...",
            }
        }


class MessageResponse(UUIDMixin):
    """Повна інформація про повідомлення"""

    wamid: Optional[str] = None
    direction: MessageDirection
    status: MessageStatus
    message_type: str
    body: Optional[str] = None
    created_at: datetime
    media_files: List[MediaFileResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "wamid": "wamid.ABC123",
                "direction": "outbound",
                "status": "delivered",
                "message_type": "text",
                "body": "Hello, World!",
                "created_at": "2024-01-15T10:30:00Z",
                "media_files": [],
            }
        }


class MessageSendResponse(BaseModel):
    """Відповідь на запит відправки"""

    status: str = "sent"
    message_id: UUID
    request_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "status": "sent",
                "message_id": "123e4567-e89b-12d3-a456-426614174000",
                "request_id": "req_123",
            }
        }
