import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from src.models import MessageDirection, MessageStatus


class WhatsAppMessage(BaseModel):
    phone_number: str
    type: Literal["text", "template"]
    body: str
    request_id: str = str(uuid.uuid4())


class WabaSyncRequest(BaseModel):
    request_id: str = str(uuid.uuid4())


class WebhookEvent(BaseModel):
    payload: dict[str, Any]


class MediaFileResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    file_mime_type: str
    caption: str | None = None
    url: str


class MessageResponse(BaseModel):
    id: uuid.UUID
    wamid: str | None = None
    direction: MessageDirection
    status: MessageStatus
    message_type: str
    body: str | None = None
    created_at: datetime | None = None
    media_files: list[MediaFileResponse] = []

    class Config:
        from_attributes = True
