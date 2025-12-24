import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from redis import asyncio as aioredis
from sqladmin import Admin
from sqlalchemy.orm import selectinload
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.routes import webhooks
from src.core.config import settings
from src.core.database import engine, get_session
from src.core.logger import setup_logging
from src.core.websocket import manager
from src.models import Contact, Message
from src.schemas import MediaFileResponse, MessageResponse
from src.services.storage import StorageService

background_tasks = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lifespan: Starting up...")

    redis = aioredis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )

    app.state.redis = redis
    logger.info("Redis pool initialized")

    task = asyncio.create_task(redis_listener())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    yield

    logger.info("Lifespan: Shutting down...")

    for task in background_tasks:
        task.cancel()

    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)

    await app.state.redis.close()
    logger.info("Redis client closed")

    await engine.dispose()
    logger.info("Database engine disposed")


logger = setup_logging()
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)

instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[
        ".*admin.*",
        "/metrics",
    ],
    env_var_name="ENABLE_METRICS",
    inprogress_name="inprogress",
    inprogress_labels=True,
)

instrumentator.instrument(app).expose(app)


async def redis_listener():
    logger.info("Starting Redis Listener...")
    try:
        redis = aioredis.from_url(settings.REDIS_URL)
        pubsub = redis.pubsub()
        await pubsub.subscribe("ws_updates")

        logger.info("Subscribed to 'ws_updates' channel.")

        async for message in pubsub.listen():
            # Логуємо все, що приходить (навіть службові повідомлення підписки)
            # logger.debug(f"Raw Redis event: {message}")

            if message["type"] == "message":
                logger.info(f"Received message data: {message['data']}")
                try:
                    data = json.loads(message["data"])
                    await manager.broadcast(data)
                except Exception as e:
                    logger.error(f"Error broadcasting message: {e}")
    except Exception as e:
        logger.error(f"Redis listener crashed: {e}")


@app.websocket("/ws/messages")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/send_message/{phone}")
async def send_message(
    request: Request,
    phone: str,
    type: str = "text",
    text: str = "This is a test message from the API.",
):
    request_id = str(uuid.uuid4())

    payload = {
        "phone_number": phone,
        "type": type,
        "body": text,
        "request_id": request_id,
    }

    try:
        await request.app.state.redis.publish("whatsapp_messages", json.dumps(payload))
    except Exception as e:
        logger.error(f"Failed to publish to Redis: {e}")
        return {"status": "error", "detail": "Internal Broker Error"}

    return {"status": "sent", "request_id": request_id}


@app.post("/waba/sync")
async def trigger_waba_sync(request: Request):
    """Sends a command to the worker to update data from Meta."""
    request_id = str(uuid.uuid4())
    payload = {"request_id": request_id}

    try:
        await request.app.state.redis.publish("sync_account_data", json.dumps(payload))
    except Exception as e:
        logger.error(f"Failed to publish to Redis: {e}")
        return {"status": "error", "detail": "Internal Broker Error"}

    return {"status": "sync_started", "request_id": request_id}


@app.get("/contacts", response_model=list[Contact])
async def get_contacts(session: AsyncSession = Depends(get_session)):
    statement = select(Contact).order_by(desc(Contact.updated_at))
    result = await session.exec(statement)
    contacts = result.all()
    return contacts


@app.get("/contacts/{contact_id}/messages", response_model=list[MessageResponse])
async def get_chat_history(
    contact_id: UUID,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    statement = (
        select(Message)
        .where(Message.contact_id == contact_id)
        .options(selectinload(Message.media_files))
        .order_by(desc(Message.created_at))
        .offset(offset)
        .limit(limit)
    )

    result = await session.exec(statement)
    messages = result.all()

    # Генеруємо URL для медіа-файлів
    storage = StorageService()
    response_data = []

    for msg in messages:
        media_dtos = []
        for mf in msg.media_files:
            url = await storage.get_presigned_url(mf.r2_key)
            media_dtos.append(
                MediaFileResponse(
                    id=mf.id,
                    file_name=mf.file_name,
                    file_mime_type=mf.file_mime_type,
                    url=url,
                    caption=mf.caption,
                )
            )

        response_data.append(
            MessageResponse(
                id=msg.id,
                wamid=msg.wamid,
                direction=msg.direction,
                status=msg.status,
                message_type=msg.message_type,
                body=msg.body,
                created_at=msg.created_at,
                media_files=media_dtos,
            )
        )

    return list(reversed(response_data))
