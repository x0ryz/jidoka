import uuid
from typing import Any, Dict, Literal

from pydantic import BaseModel


class WhatsAppMessage(BaseModel):
    phone_number: str
    type: Literal["text", "template"]
    body: str
    request_id: str = str(uuid.uuid4())


class WabaSyncRequest(BaseModel):
    request_id: str = str(uuid.uuid4())


class WebhookEvent(BaseModel):
    payload: Dict[str, Any]
