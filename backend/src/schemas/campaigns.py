from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from src.models.base import CampaignStatus, ContactStatus

from .base import TimestampMixin, UUIDMixin

# === Request Schemas ===


class CampaignCreate(BaseModel):
    """Схема створення кампанії"""

    name: str = Field(..., min_length=1, max_length=255)
    message_type: Literal["text", "template"] = "template"
    template_id: Optional[UUID] = None
    message_body: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Black Friday Campaign",
                "message_type": "template",
                "template_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }


class CampaignUpdate(BaseModel):
    """Схема оновлення кампанії"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    message_type: Optional[Literal["text", "template"]] = None
    template_id: Optional[UUID] = None
    message_body: Optional[str] = None


class CampaignSchedule(BaseModel):
    """Схема планування кампанії"""

    scheduled_at: datetime = Field(
        ..., description="ISO 8601 datetime when to start the campaign"
    )

    class Config:
        json_schema_extra = {"example": {"scheduled_at": "2024-12-31T12:00:00Z"}}


# === Response Schemas ===


class CampaignResponse(UUIDMixin, TimestampMixin):
    """Повна інформація про кампанію"""

    name: str
    status: CampaignStatus
    message_type: str
    template_id: Optional[UUID] = None
    message_body: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_contacts: int
    sent_count: int
    delivered_count: int
    failed_count: int

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Black Friday",
                "status": "running",
                "message_type": "template",
                "total_contacts": 1000,
                "sent_count": 750,
                "delivered_count": 700,
                "failed_count": 50,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class CampaignStats(BaseModel):
    """Детальна статистика кампанії"""

    id: UUID
    name: str
    status: CampaignStatus
    total_contacts: int
    sent_count: int
    delivered_count: int
    failed_count: int
    progress_percent: float = Field(..., ge=0, le=100)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Black Friday",
                "status": "running",
                "total_contacts": 1000,
                "sent_count": 750,
                "delivered_count": 700,
                "failed_count": 50,
                "progress_percent": 75.0,
                "started_at": "2024-01-15T09:00:00Z",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class CampaignContactResponse(BaseModel):
    """Інформація про контакт в кампанії"""

    id: UUID
    contact_id: UUID
    phone_number: str
    name: Optional[str] = None
    status: ContactStatus
    error_message: Optional[str] = None
    retry_count: int

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "contact_id": "789e4567-e89b-12d3-a456-426614174000",
                "phone_number": "380671234567",
                "name": "John Doe",
                "status": "sent",
                "error_message": None,
                "retry_count": 0,
            }
        }


class CampaignStartResponse(BaseModel):
    """Відповідь на запит запуску кампанії"""

    status: str = "started"
    campaign_id: UUID
    message: str = "Campaign started successfully"

    class Config:
        json_schema_extra = {
            "example": {
                "status": "started",
                "campaign_id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "Campaign started successfully",
            }
        }
