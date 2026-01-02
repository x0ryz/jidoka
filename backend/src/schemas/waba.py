from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .base import TimestampMixin, UUIDMixin

# === Request Schemas ===


class WabaSyncRequest(BaseModel):
    """Запит на синхронізацію WABA"""

    request_id: str = Field(default_factory=lambda: str(uuid4()))

    class Config:
        json_schema_extra = {"example": {"request_id": "sync_123"}}


# === Response Schemas ===


class WabaAccountResponse(UUIDMixin):
    """Інформація про WABA акаунт"""

    waba_id: str
    name: str
    account_review_status: Optional[str] = None
    business_verification_status: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "waba_id": "1234567890",
                "name": "My Business",
                "account_review_status": "APPROVED",
                "business_verification_status": "VERIFIED",
            }
        }


class WabaPhoneResponse(UUIDMixin, TimestampMixin):
    """Інформація про WABA номер телефону"""

    waba_id: UUID
    phone_number_id: str
    display_phone_number: str
    status: Optional[str] = None
    quality_rating: str
    messaging_limit_tier: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "waba_id": "789e4567-e89b-12d3-a456-426614174000",
                "phone_number_id": "1234567890",
                "display_phone_number": "+380671234567",
                "status": "CONNECTED",
                "quality_rating": "GREEN",
                "messaging_limit_tier": "TIER_1K",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class WabaSyncResponse(BaseModel):
    """Відповідь на запит синхронізації"""

    status: str = "sync_started"
    request_id: str
    message: str = "WABA sync initiated"

    class Config:
        json_schema_extra = {
            "example": {
                "status": "sync_started",
                "request_id": "sync_123",
                "message": "WABA sync initiated",
            }
        }
