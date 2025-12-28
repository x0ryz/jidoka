import json
from datetime import timedelta
from uuid import UUID

import httpx
from redis import asyncio as aioredis
from taskiq import Context, TaskiqDepends
from taskiq.scheduler.scheduled_task import ScheduledTask

from src.clients.meta import MetaClient
from src.core.broker import broker, redis_source
from src.core.config import settings
from src.core.database import async_session_maker
from src.core.logger import setup_logging
from src.core.uow import UnitOfWork
from src.models import WebhookLog, get_utc_now
from src.schemas import WabaSyncRequest, WebhookEvent, WhatsAppMessage
from src.services.campaign import CampaignSenderService
from src.services.sync import SyncService
from src.services.whatsapp import WhatsAppService

logger = setup_logging()


async def get_http_client(context: Context = TaskiqDepends()) -> httpx.AsyncClient:
    return context.state.http_client


async def publish_ws_update(data: dict):
    """Publish WebSocket updates to Redis Pub/Sub (for frontend)"""
    try:
        redis = aioredis.from_url(settings.REDIS_URL)
        message_json = json.dumps(data, default=str)
        await redis.publish("ws_updates", message_json)
        await redis.close()
    except Exception as e:
        logger.error(f"Failed to publish WS update: {e}")


@broker.task(task_name="handle_messages")
async def handle_messages_task(
    message: WhatsAppMessage, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
):
    """Handle individual WhatsApp message requests (API endpoint)"""
    with logger.contextualize(request_id=message.request_id):
        logger.info(f"Task: Sending message to {message.phone_number}")

        uow = UnitOfWork(async_session_maker)
        meta_client = MetaClient(client)
        service = WhatsAppService(uow, meta_client, notifier=publish_ws_update)

        await service.send_outbound_message(message)


@broker.task(task_name="sync_account_data")
async def handle_account_sync_task(
    message: WabaSyncRequest, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
):
    """Handle WABA account sync requests"""
    request_id = message.request_id

    with logger.contextualize(request_id=request_id):
        logger.info("Task: Starting sync task...")

        async with async_session_maker() as session:
            meta_client = MetaClient(client)
            sync_service = SyncService(session, meta_client)
            await sync_service.sync_account_data()


@broker.task(task_name="raw_webhooks")
async def handle_raw_webhook_task(
    event: WebhookEvent, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
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


@broker.task(task_name="send_one_message")
async def send_one_message_task(
    campaign_id: str,
    link_id: str,
    contact_id: str,
    client: httpx.AsyncClient = TaskiqDepends(get_http_client),
):
    """
    Atomic task: Sends exactly ONE message.
    This task is executed by the worker at a precise time scheduled by the planner.
    """
    try:
        uow = UnitOfWork(async_session_maker)
        meta_client = MetaClient(client)
        sender = CampaignSenderService(uow, meta_client, notifier=publish_ws_update)

        await sender.send_single_message(
            UUID(campaign_id), UUID(link_id), UUID(contact_id)
        )
    except Exception as e:
        logger.exception(f"Failed atomic send for contact {contact_id}")


@broker.task(task_name="plan_campaign_batch")
async def plan_campaign_batch_task(
    campaign_id: str, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
):
    BATCH_SIZE = 500
    MESSAGES_PER_SECOND = 10

    uow = UnitOfWork(async_session_maker)
    meta_client = MetaClient(client)
    sender = CampaignSenderService(uow, meta_client, notifier=publish_ws_update)

    logger.info(f"Planning batch for campaign {campaign_id}...")

    async with uow:
        contacts = await uow.campaign_contacts.get_sendable_contacts(
            UUID(campaign_id), limit=BATCH_SIZE
        )

        if not contacts:
            logger.info(
                f"No more contacts to plan for {campaign_id}. Checking completion."
            )
            await sender._check_campaign_completion(UUID(campaign_id))
            return

        logger.info(f"Scheduling {len(contacts)} messages for campaign {campaign_id}")

        start_time = get_utc_now()

        for i, link in enumerate(contacts):
            delay_seconds = i / MESSAGES_PER_SECOND
            run_at = start_time + timedelta(seconds=delay_seconds)

            task_data = ScheduledTask(
                task_name="send_one_message",
                labels={},
                args=[
                    campaign_id,
                    str(link.id),
                    str(link.contact_id),
                ],
                kwargs={},
                time=run_at,
            )

            await redis_source.add_schedule(task_data)

    batch_duration = len(contacts) / MESSAGES_PER_SECOND
    next_plan_run_at = get_utc_now() + timedelta(seconds=batch_duration)

    logger.info(f"Next batch planning scheduled at {next_plan_run_at}")

    next_batch_task = ScheduledTask(
        task_name="plan_campaign_batch",
        labels={},
        args=[campaign_id],
        kwargs={},
        time=next_plan_run_at,
    )
    await redis_source.add_schedule(next_batch_task)


@broker.task(task_name="campaign_start")
async def handle_campaign_start_task(
    campaign_id: str, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
):
    """Start processing a campaign"""
    with logger.contextualize(campaign_id=campaign_id):
        logger.info(f"Task: Starting campaign {campaign_id}")

        try:
            uow = UnitOfWork(async_session_maker)
            meta_client = MetaClient(client)
            sender = CampaignSenderService(uow, meta_client, notifier=publish_ws_update)

            await sender.start_campaign(UUID(campaign_id))

            await plan_campaign_batch_task.kiq(campaign_id)

        except Exception as e:
            logger.exception(f"Campaign {campaign_id} failed to start")


@broker.task(task_name="campaign_resume")
async def handle_campaign_resume_task(
    campaign_id: str, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
):
    """Resume a paused campaign"""
    with logger.contextualize(campaign_id=campaign_id):
        logger.info(f"Task: Resuming campaign {campaign_id}")
        try:
            uow = UnitOfWork(async_session_maker)
            meta_client = MetaClient(client)
            sender = CampaignSenderService(uow, meta_client, notifier=publish_ws_update)

            await sender.resume_campaign(UUID(campaign_id))

            await plan_campaign_batch_task.kiq(campaign_id)

        except Exception as e:
            logger.exception(f"Campaign {campaign_id} resume failed")


@broker.task(schedule=[{"cron": "* * * * *"}])
async def check_scheduled_campaigns_task():
    """
    Background task that checks for scheduled campaigns and starts them.
    Runs every minute.
    """
    now = get_utc_now()
    logger.info("Scheduler: Checking for campaigns to start...")

    uow = UnitOfWork(async_session_maker)

    async with uow:
        campaigns = await uow.campaigns.get_scheduled_campaigns(now)

        if not campaigns:
            return

        logger.info(f"Scheduler: Found {len(campaigns)} campaigns to start")

        for campaign in campaigns:
            try:
                logger.info(f"Scheduler: Triggering campaign {campaign.id}")
                await handle_campaign_start_task.kiq(str(campaign.id))
            except Exception as e:
                logger.exception(f"Failed to trigger campaign {campaign.id}: {e}")
