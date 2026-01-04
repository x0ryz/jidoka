import mimetypes
import uuid
from uuid import UUID

import httpx
from aiolimiter import AsyncLimiter
from src.clients.meta import MetaClient
from src.core.broker import broker
from src.core.config import settings
from src.core.database import async_session_maker
from src.core.logger import setup_logging
from src.core.uow import UnitOfWork
from src.models import WebhookLog, get_utc_now
from src.schemas import (
    MetaWebhookPayload,
    WabaSyncRequest,
    WebhookEvent,
    WhatsAppMessage,
)
from src.services.campaign.sender import CampaignSenderService
from src.services.media.service import MediaService

# Додайте імпорт AsyncIteratorFile, якщо ви додали його в storage.py
from src.services.media.storage import AsyncIteratorFile, StorageService
from src.services.messaging.processor import MessageProcessorService
from src.services.messaging.sender import MessageSenderService
from src.services.notifications.service import NotificationService
from src.services.sync import SyncService
from taskiq import Context, TaskiqDepends

logger = setup_logging()
limiter = AsyncLimiter(10, 1)


async def get_http_client(context: Context = TaskiqDepends()) -> httpx.AsyncClient:
    return context.state.http_client


@broker.task(
    task_name="handle_messages", retry_on_exception=True, max_retries=3, retry_delay=5
)
async def handle_messages_task(
    message: WhatsAppMessage, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
):
    """Handle individual WhatsApp message requests (API endpoint)"""
    async with limiter:
        with logger.contextualize(request_id=message.request_id):
            uow = UnitOfWork(async_session_maker)
            meta_client = MetaClient(client)

            notifier = NotificationService()
            sender_service = MessageSenderService(uow, meta_client, notifier)

            await sender_service.send_manual_message(message)


@broker.task(task_name="sync_account_data")
async def handle_account_sync_task(
    message: WabaSyncRequest, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
):
    """Handle WABA account sync requests"""
    with logger.contextualize(request_id=message.request_id):
        async with async_session_maker() as session:
            meta_client = MetaClient(client)
            sync_service = SyncService(session, meta_client)
            await sync_service.sync_account_data()


# === НОВА ЗАДАЧА ДЛЯ МЕДІА ===
@broker.task(
    task_name="download_media", retry_on_exception=True, max_retries=3, retry_delay=5
)
async def handle_media_download_task(
    message_id: UUID,
    meta_media_id: str,
    media_type: str,
    mime_type: str,
    caption: str | None = None,
    client: httpx.AsyncClient = TaskiqDepends(get_http_client),
):
    """
    Фонове завантаження медіа-файлів з Meta в R2.
    Використовує stream, щоб не забивати пам'ять.
    """
    with logger.contextualize(message_id=str(message_id), media_id=meta_media_id):
        uow = UnitOfWork(async_session_maker)
        meta_client = MetaClient(client)
        storage_service = StorageService()

        try:
            # 1. Отримуємо тимчасове посилання від Meta
            media_url = await meta_client.get_media_url(meta_media_id)

            # 2. Генеруємо шлях для збереження
            ext = mimetypes.guess_extension(mime_type) or ".bin"
            filename = f"{uuid.uuid4()}{ext}"
            r2_key = f"whatsapp/{media_type}s/{filename}"

            logger.info(f"Starting stream download for {media_type}: {r2_key}")

            # 3. Качаємо потік та передаємо його відразу в R2
            # Використовуємо raw client для стрімінгу, якщо в MetaClient немає методу stream
            async with client.stream("GET", media_url) as response:
                response.raise_for_status()

                # Отримуємо розмір файлу з заголовків (якщо є)
                file_size = int(response.headers.get("content-length", 0))

                # Обгортаємо ітератор в файлоподібний об'єкт
                file_stream = AsyncIteratorFile(response.aiter_bytes())

                # Заливаємо в R2
                await storage_service.upload_stream(
                    file_stream=file_stream,
                    object_name=r2_key,
                    content_type=mime_type,
                )

            # 4. Зберігаємо метадані в БД
            async with uow:
                await uow.messages.add_media_file(
                    message_id=message_id,
                    meta_media_id=meta_media_id,
                    file_name=filename,
                    file_mime_type=mime_type,
                    file_size=file_size,
                    caption=caption,
                    r2_key=r2_key,
                    bucket_name=settings.R2_BUCKET_NAME,
                )
                await uow.commit()

            logger.info(f"Media saved successfully: {r2_key}")

        except Exception as e:
            logger.error(f"Failed to process media: {e}")
            # Тут можна додати логіку оновлення статусу повідомлення на FAILED, якщо потрібно


@broker.task(
    task_name="raw_webhooks", retry_on_exception=True, max_retries=5, retry_delay=5
)
async def handle_raw_webhook_task(
    event: WebhookEvent, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
):
    """Handle incoming webhooks from Meta"""
    data = event.payload

    async with async_session_maker() as session:
        try:
            log_entry = WebhookLog(payload=data)
            session.add(log_entry)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to save webhook log: {e}")

    uow = UnitOfWork(async_session_maker)
    meta_client = MetaClient(client)

    storage_service = StorageService()
    notifier = NotificationService()
    media_service = MediaService(uow, storage_service, meta_client)

    processor_service = MessageProcessorService(uow, media_service, notifier)

    webhook_payload = MetaWebhookPayload(**event.payload)
    await processor_service.process_webhook(webhook_payload)


@broker.task(task_name="process_campaign_batch")
async def process_campaign_batch_task(
    campaign_id: str,
    batch_number: int = 1,
    client: httpx.AsyncClient = TaskiqDepends(get_http_client),
):
    """Process a batch of contacts."""
    BATCH_SIZE = 100
    PROGRESS_UPDATE_INTERVAL = 10

    uow = UnitOfWork(async_session_maker)
    meta_client = MetaClient(client)

    notifier = NotificationService()
    message_sender = MessageSenderService(uow, meta_client, notifier)

    sender = CampaignSenderService(uow, message_sender, notifier)

    async with uow:
        contacts = await uow.campaign_contacts.get_sendable_contacts(
            UUID(campaign_id), limit=BATCH_SIZE
        )

    if not contacts:
        await sender._check_campaign_completion(UUID(campaign_id))
        return

    batch_size = len(contacts)
    logger.info(f"Batch #{batch_number}: Processing {batch_size} contacts")

    await sender.notify_batch_progress(
        campaign_id=UUID(campaign_id),
        batch_number=batch_number,
        stats={"batch_size": batch_size, "processed": 0, "successful": 0, "failed": 0},
    )

    processed = 0
    successful = 0
    failed = 0

    for link in contacts:
        async with limiter:
            try:
                await sender.send_single_message(
                    campaign_id=UUID(campaign_id),
                    link_id=link.id,
                    contact_id=link.contact_id,
                )
                successful += 1
            except Exception as e:
                logger.error(f"Error sending in batch: {e}")
                failed += 1

            processed += 1

            if processed % PROGRESS_UPDATE_INTERVAL == 0 or processed == batch_size:
                await sender.notify_batch_progress(
                    campaign_id=UUID(campaign_id),
                    batch_number=batch_number,
                    stats={
                        "batch_size": batch_size,
                        "processed": processed,
                        "successful": successful,
                        "failed": failed,
                    },
                )

    logger.info(f"Batch #{batch_number} completed")
    await process_campaign_batch_task.kiq(campaign_id, batch_number + 1)


@broker.task(task_name="campaign_start")
async def handle_campaign_start_task(
    campaign_id: str, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
):
    with logger.contextualize(campaign_id=campaign_id):
        try:
            uow = UnitOfWork(async_session_maker)
            meta_client = MetaClient(client)

            notifier = NotificationService()
            message_sender = MessageSenderService(uow, meta_client, notifier)
            sender = CampaignSenderService(uow, message_sender, notifier)

            await sender.start_campaign(UUID(campaign_id))
            await process_campaign_batch_task.kiq(campaign_id, batch_number=1)

        except Exception as e:
            logger.exception(f"Campaign {campaign_id} failed to start")
            notifier = NotificationService()
            await notifier.notify_campaign_status(
                campaign_id=UUID(campaign_id), status="FAILED", error=str(e)
            )


@broker.task(task_name="campaign_resume")
async def handle_campaign_resume_task(
    campaign_id: str, client: httpx.AsyncClient = TaskiqDepends(get_http_client)
):
    with logger.contextualize(campaign_id=campaign_id):
        try:
            uow = UnitOfWork(async_session_maker)
            meta_client = MetaClient(client)

            # DI
            notifier = NotificationService()
            message_sender = MessageSenderService(uow, meta_client, notifier)
            sender = CampaignSenderService(uow, message_sender, notifier)

            await sender.resume_campaign(UUID(campaign_id))
            await process_campaign_batch_task.kiq(campaign_id)

        except Exception:
            logger.exception(f"Campaign {campaign_id} resume failed")


@broker.task(schedule=[{"cron": "* * * * *"}])
async def check_scheduled_campaigns_task():
    now = get_utc_now()
    uow = UnitOfWork(async_session_maker)

    async with uow:
        campaigns = await uow.campaigns.get_scheduled_campaigns(now)
        for campaign in campaigns:
            try:
                logger.info(f"Scheduler: Triggering campaign {campaign.id}")
                await handle_campaign_start_task.kiq(str(campaign.id))
            except Exception as e:
                logger.error(f"Failed to trigger campaign {campaign.id}: {e}")
