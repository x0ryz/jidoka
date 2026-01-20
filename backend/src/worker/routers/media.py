import mimetypes
import os
import uuid

import aiofiles
from faststream import Depends
from faststream.nats import NatsRouter

from src.clients.meta import MetaClient
from src.core.config import settings
from src.core.uow import UnitOfWork
from src.schemas.messages import MediaDownloadRequest, MediaSendRequest
from src.services.media.storage import AsyncIteratorFile, StorageService
from src.services.messaging.sender import MessageSenderService
from src.services.notifications.service import NotificationService
from src.worker.dependencies import get_uow, get_worker_meta_client, limiter, logger

router = NatsRouter()


@router.subscriber("media.download")
async def handle_media_download_task(
    task: MediaDownloadRequest,
    uow: UnitOfWork = Depends(get_uow),
    meta_client: MetaClient = Depends(get_worker_meta_client),
):
    storage_service = StorageService()

    with logger.contextualize(message_id=task.message_id, media_id=task.meta_media_id):
        try:
            logger.info(f"Processing media download for {task.message_id}")

            media_url = await meta_client.get_media_url(task.meta_media_id)
            ext = mimetypes.guess_extension(task.mime_type) or ".bin"
            filename = f"{uuid.uuid4()}{ext}"
            r2_key = f"whatsapp/{task.media_type}s/{filename}"

            logger.info(f"Starting stream download: {r2_key}")
            headers = {"Authorization": f"Bearer {meta_client.token}"}

            async with meta_client.client.stream(
                "GET", media_url, headers=headers
            ) as response:
                response.raise_for_status()
                file_size = int(response.headers.get("content-length", 0))
                file_stream = AsyncIteratorFile(response.aiter_bytes())

                await storage_service.upload_stream(
                    file_stream=file_stream,
                    object_name=r2_key,
                    content_type=task.mime_type,
                )

            async with uow:
                await uow.messages.add_media_file(
                    message_id=uuid.UUID(task.message_id),
                    meta_media_id=task.meta_media_id,
                    file_name=filename,
                    file_mime_type=task.mime_type,
                    file_size=file_size,
                    caption=task.caption,
                    r2_key=r2_key,
                    bucket_name=settings.R2_BUCKET_NAME,
                )
                await uow.commit()

            logger.info(f"Media saved successfully: {r2_key}")

        except Exception as e:
            logger.error(f"Failed to process media: {e}")
            raise e


@router.subscriber("messages.media_send")
async def handle_media_send_task(
    task: MediaSendRequest,
    uow: UnitOfWork = Depends(get_uow),
    meta_client: MetaClient = Depends(get_worker_meta_client),
):
    async with limiter:
        storage = StorageService()
        notifier = NotificationService()
        sender = MessageSenderService(uow, meta_client, notifier, storage)

        try:
            if not os.path.exists(task.file_path):
                logger.error(f"File not found: {task.file_path}")
                return

            async with aiofiles.open(task.file_path, "rb") as f:
                file_bytes = await f.read()

            await sender.send_media_message(
                phone_number=task.phone_number,
                file_bytes=file_bytes,
                filename=task.filename,
                mime_type=task.mime_type,
                caption=task.caption,
            )
            logger.info(f"Media sent to {task.phone_number}")
        finally:
            if os.path.exists(task.file_path):
                os.remove(task.file_path)
