import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from src.core.websocket import manager
from src.schemas import MessageCreate, MessageSendResponse, WhatsAppMessage
from src.worker import handle_messages_task

router = APIRouter(tags=["Messages"])


@router.websocket("/ws/messages")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.post(
    "/messages",
    response_model=MessageSendResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_message(data: MessageCreate):
    """
    Send a WhatsApp message asynchronously.

    - **text**: Send regular text message
    - **template**: Send template message (template_id required)
    """
    request_id = str(uuid.uuid4())

    message_body = data.body
    if data.type == "template" and data.template_id:
        message_body = str(data.template_id)

    message_obj = WhatsAppMessage(
        phone_number=data.phone_number,
        type=data.type,
        body=message_body,
        request_id=request_id,
    )

    await handle_messages_task.kiq(message_obj)

    return MessageSendResponse(
        status="queued", message_id=uuid.uuid4(), request_id=request_id
    )
