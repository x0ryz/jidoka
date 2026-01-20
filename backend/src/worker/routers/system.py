from faststream import Depends
from faststream.nats import NatsRouter

from src.core.database import async_session_maker
from src.models import WebhookLog
from src.schemas import MetaWebhookPayload, WabaSyncRequest, WebhookEvent
from src.services.messaging.processor import MessageProcessorService
from src.services.sync import SyncService
from src.worker.dependencies import get_processor_service, get_sync_service, logger

router = NatsRouter()


@router.subscriber("webhooks.raw")
async def handle_raw_webhook_task(
    event: dict, processor: MessageProcessorService = Depends(get_processor_service)
):
    if isinstance(event, dict):
        event = WebhookEvent(**event)

    async with async_session_maker() as session:
        session.add(WebhookLog(payload=event.payload))
        await session.commit()

    webhook_payload = MetaWebhookPayload(**event.payload)
    await processor.process_webhook(webhook_payload)


@router.subscriber("sync.account_data")
async def handle_account_sync_task(
    message: WabaSyncRequest,
    sync_service: SyncService = Depends(get_sync_service),
):
    with logger.contextualize(request_id=message.request_id):
        await sync_service.sync_account_data()
