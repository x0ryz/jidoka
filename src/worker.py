import json

import httpx
from faststream import Context, ContextRepo, FastStream
from faststream.redis import RedisBroker
from pydantic import BaseModel
from redis import asyncio as aioredis

from src.clients.meta import MetaClient
from src.core.config import settings
from src.core.database import async_session_maker
from src.core.logger import setup_logging
from src.core.uow import UnitOfWork
from src.models import WebhookLog
from src.schemas import WabaSyncRequest, WebhookEvent, WhatsAppMessage
from src.services.campaign import CampaignSenderService
from src.services.sync import SyncService
from src.services.whatsapp import WhatsAppService

logger = setup_logging()

broker = RedisBroker(settings.REDIS_URL)
app = FastStream(broker)


@app.on_startup
async def setup_http_client(context: ContextRepo):
    client = httpx.AsyncClient(
        timeout=10.0,
        headers={
            "Authorization": f"Bearer {settings.META_TOKEN}",
            "Content-Type": "application/json",
        },
    )

    context.set_global("http_client", client)
    logger.info("HTTPX Client initialized")


@app.after_shutdown
async def close_http_client(context: ContextRepo):
    client = context.get("http_client")
    if client:
        await client.aclose()
        logger.info("HTTPX Client closed")


async def publish_ws_update(data: dict):
    """Publish WebSocket updates to Redis"""
    try:
        redis = aioredis.from_url(settings.REDIS_URL)
        message_json = json.dumps(data, default=str)
        await redis.publish("ws_updates", message_json)
        await redis.close()
        logger.info(f"WS EVENT PUBLISHED: {message_json}")
    except Exception as e:
        logger.error(f"Failed to publish WS update: {e}")


@broker.subscriber("whatsapp_messages")
async def handle_messages(
    message: WhatsAppMessage, client: httpx.AsyncClient = Context("http_client")
):
    """Handle individual WhatsApp message requests"""
    with logger.contextualize(request_id=message.request_id):
        logger.info(f"Received message request for phone: {message.phone_number}")

        uow = UnitOfWork(async_session_maker)
        meta_client = MetaClient(client)
        service = WhatsAppService(uow, meta_client, notifier=publish_ws_update)

        await service.send_outbound_message(message)


@broker.subscriber("sync_account_data")
async def handle_account_sync(
    message: WabaSyncRequest, client: httpx.AsyncClient = Context("http_client")
):
    """Handle WABA account sync requests"""
    request_id = message.request_id

    with logger.contextualize(request_id=request_id):
        logger.info("Starting sync task...")

        async with async_session_maker() as session:
            meta_client = MetaClient(client)
            sync_service = SyncService(session, meta_client)
            await sync_service.sync_account_data()


@broker.subscriber("raw_webhooks")
async def handle_raw_webhook(
    event: WebhookEvent, client: httpx.AsyncClient = Context("http_client")
):
    """Handle incoming webhooks from Meta"""
    data = event.payload

    # Log webhook
    async with async_session_maker() as session:
        try:
            log_entry = WebhookLog(payload=data)
            session.add(log_entry)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to save webhook log: {e}")

    # Process webhook
    try:
        uow = UnitOfWork(async_session_maker)
        meta_client = MetaClient(client)
        service = WhatsAppService(uow, meta_client, notifier=publish_ws_update)
        await service.process_webhook(data)
    except Exception as e:
        logger.exception("Error processing webhook in service")


# Campaign handlers


class CampaignStartMessage(BaseModel):
    """Message to start a campaign"""

    campaign_id: str


@broker.subscriber("campaign_start")
async def handle_campaign_start(
    message: CampaignStartMessage, client: httpx.AsyncClient = Context("http_client")
):
    """
    Handle campaign start requests.
    This is published when:
    1. User clicks "Start Now" button
    2. Scheduler starts a scheduled campaign
    """
    campaign_id = message.campaign_id

    with logger.contextualize(campaign_id=campaign_id):
        logger.info(f"Starting campaign: {campaign_id}")

        try:
            uow = UnitOfWork(async_session_maker)
            meta_client = MetaClient(client)
            sender = CampaignSenderService(uow, meta_client, notifier=publish_ws_update)

            # Start the campaign (update status to RUNNING)
            await sender.start_campaign(campaign_id)

            # Process all messages
            await sender.process_campaign(campaign_id)

            logger.success(f"Campaign {campaign_id} processing completed")

        except Exception as e:
            logger.exception(f"Campaign {campaign_id} failed")

            # Mark campaign as failed
            try:
                uow = UnitOfWork(async_session_maker)
                async with uow:
                    from src.models import CampaignStatus, get_utc_now

                    campaign = await uow.campaigns.get_by_id(campaign_id)
                    if campaign:
                        campaign.status = CampaignStatus.FAILED
                        campaign.updated_at = get_utc_now()
                        uow.session.add(campaign)
            except Exception as inner_e:
                logger.error(f"Failed to mark campaign as failed: {inner_e}")


class CampaignResumeMessage(BaseModel):
    """Message to resume a paused campaign"""

    campaign_id: str


@broker.subscriber("campaign_resume")
async def handle_campaign_resume(
    message: CampaignResumeMessage, client: httpx.AsyncClient = Context("http_client")
):
    """Handle campaign resume requests"""
    campaign_id = message.campaign_id

    with logger.contextualize(campaign_id=campaign_id):
        logger.info(f"Resuming campaign: {campaign_id}")

        try:
            uow = UnitOfWork(async_session_maker)
            meta_client = MetaClient(client)
            sender = CampaignSenderService(uow, meta_client, notifier=publish_ws_update)

            # Resume (update status to RUNNING)
            await sender.resume_campaign(campaign_id)

            # Continue processing
            await sender.process_campaign(campaign_id)

            logger.success(f"Campaign {campaign_id} resumed and completed")

        except Exception as e:
            logger.exception(f"Campaign {campaign_id} resume failed")
