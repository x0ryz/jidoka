# backend/src/schemas/webhooks.py
"""
Pydantic схеми для обробки вебхуків від Meta.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# === Internal Schemas ===


class WebhookEvent(BaseModel):
    """Wrapper для raw webhook payload"""

    payload: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {"payload": {"object": "whatsapp_business_account", "entry": []}}
        }


# === Meta API Webhook Schemas ===


class MetaProfile(BaseModel):
    """Профіль контакту в Meta"""

    name: str


class MetaContact(BaseModel):
    """Контакт в Meta webhook"""

    wa_id: str
    profile: MetaProfile


class MetaMedia(BaseModel):
    """Медіа файл в Meta webhook"""

    id: str
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    caption: Optional[str] = None


class MetaText(BaseModel):
    """Текстове повідомлення"""

    body: str


class MetaMessage(BaseModel):
    """Вхідне повідомлення від Meta"""

    from_: str = Field(alias="from")
    id: str
    timestamp: str
    type: str
    text: Optional[MetaText] = None
    image: Optional[MetaMedia] = None
    video: Optional[MetaMedia] = None
    audio: Optional[MetaMedia] = None
    voice: Optional[MetaMedia] = None
    document: Optional[MetaMedia] = None
    sticker: Optional[MetaMedia] = None

    class Config:
        populate_by_name = True


class MetaStatus(BaseModel):
    """Статус повідомлення від Meta"""

    id: str
    status: str
    timestamp: str
    recipient_id: str
    errors: Optional[List[Dict[str, Any]]] = None


class MetaValue(BaseModel):
    """Value об'єкт в webhook"""

    messaging_product: str
    metadata: Dict[str, Any]
    contacts: List[MetaContact] = Field(default_factory=list)
    messages: List[MetaMessage] = Field(default_factory=list)
    statuses: List[MetaStatus] = Field(default_factory=list)


class MetaChange(BaseModel):
    """Change об'єкт в webhook"""

    value: MetaValue
    field: str


class MetaEntry(BaseModel):
    """Entry об'єкт в webhook"""

    id: str
    changes: List[MetaChange] = Field(default_factory=list)


class MetaWebhookPayload(BaseModel):
    """Повний webhook payload від Meta"""

    object: str
    entry: List[MetaEntry] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": "PHONE_NUMBER_ID",
                        "changes": [
                            {
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "display_phone_number": "380671234567",
                                        "phone_number_id": "PHONE_NUMBER_ID",
                                    },
                                    "messages": [
                                        {
                                            "from": "380671234567",
                                            "id": "wamid.ABC123",
                                            "timestamp": "1234567890",
                                            "type": "text",
                                            "text": {"body": "Hello!"},
                                        }
                                    ],
                                },
                                "field": "messages",
                            }
                        ],
                    }
                ],
            }
        }
