import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from faststream.redis import RedisBroker
from sqladmin import Admin
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.database import engine, get_session

# from src.admin import WabaAccountAdmin
from src.logger import setup_logging
from src.models import WabaAccount
from src.schemas import WebhookEvent

logger = setup_logging()
app = FastAPI()
admin = Admin(app, engine, title="My Admin")

# admin.add_view(WabaAccountAdmin)


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.VERIFY_TOKEN:
        return int(hub_challenge or 0)

    raise HTTPException(status_code=403, detail="Invalid token")


@app.post("/webhook")
async def receive_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"status": "ignored"}

    async with RedisBroker(settings.REDIS_URL) as broker:
        await broker.publish(WebhookEvent(payload=data), channel="raw_webhooks")

    return {"status": "ok"}


@app.post("/send_message/{phone}")
async def send_message(
    phone: str, type: str = "text", text: str = "Це тестове повідомлення з API"
):
    request_id = str(uuid.uuid4())

    async with RedisBroker(settings.REDIS_URL) as broker:
        logger.info("New API request received", request_id=request_id)

        await broker.publish(
            {"phone": phone, "type": type, "body": text, "request_id": request_id},
            channel="whatsapp_messages",
        )

        return {"status": "sent", "request_id": request_id}


@app.post("/waba/sync")
async def trigger_waba_sync():
    """Відправляє команду воркеру на оновлення даних з Meta."""
    request_id = str(uuid.uuid4())

    async with RedisBroker(settings.REDIS_URL) as broker:
        await broker.publish({"request_id": request_id}, channel="sync_account_data")

    return {"status": "sync_started", "request_id": request_id}
