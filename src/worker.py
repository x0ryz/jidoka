import httpx, asyncio

from faststream import FastStream, Context, ContextRepo
from faststream.redis import RedisBroker
from src.schemas import WhatsAppMessage

from src.logger import setup_logging
from src.config import settings

logger = setup_logging()

broker = RedisBroker(settings.REDIS_URL)
app = FastStream(broker)


@app.on_startup
async def setup_http_client(context: ContextRepo):
    client = httpx.AsyncClient(
        timeout=10.0,
        headers={
            "Authorization": f"Bearer {settings.META_TOKEN}",
            "Content-Type": "application/json"
        }
    )

    context.set_global("http_client", client)
    logger.info("HTTPX Client initialized")


@app.after_shutdown
async def close_http_client(context: ContextRepo):
    client = context.get("http_client")
    if client:
        await client.aclose()
        logger.info("HTTPX Client closed")

async def send_whatsapp_message(phone: str, client: httpx.AsyncClient):
    url = f"{settings.META_URL}/{settings.META_PHONE_ID}/messages"

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

    resp = await client.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()

@broker.subscriber("whatsapp_messages")
async def handle_messages(message: WhatsAppMessage, client: httpx.AsyncClient = Context("http_client")):
    with logger.contextualize(request_id=message.request_id):
        logger.info(f"Received message request for phone: {message.phone}")

        try:
            result = await send_whatsapp_message(message.phone, client)
            logger.success(
                f"Message sent successfully. Meta Response: {result}")
            await asyncio.sleep(1)
        except Exception as e:
            logger.exception(f"Failed to send message to {message.phone}")
            