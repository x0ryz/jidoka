import httpx, asyncio

from faststream import FastStream
from faststream.redis import RedisBroker
from src.schemas import WhatsAppMessage
from src.config import settings

broker = RedisBroker(settings.REDIS_URL)
app = FastStream(broker)

async def send_whatsapp_message(phone: str):
    url = f"{settings.META_URL}/{settings.META_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.META_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {
                "code": "en_US"
            }
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

@broker.subscriber("whatsapp_messages")
async def handle_messages(message: WhatsAppMessage):
    try:
        result = await send_whatsapp_message(message.phone)
        print(f"Message sent to {message.phone}: {result}")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Failed to send message to {message.phone}: {e}")
        