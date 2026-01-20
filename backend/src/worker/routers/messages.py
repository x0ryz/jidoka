from faststream import Depends
from faststream.nats import NatsRouter

from src.schemas import WhatsAppMessage
from src.services.messaging.sender import MessageSenderService
from src.worker.dependencies import get_message_sender_service, limiter, logger

router = NatsRouter()


@router.subscriber("messages.manual_send")
async def handle_messages_task(
    message: WhatsAppMessage,
    sender_service: MessageSenderService = Depends(get_message_sender_service),
):
    async with limiter:
        with logger.contextualize(request_id=message.request_id):
            await sender_service.send_manual_message(message)
