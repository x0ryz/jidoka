from uuid import UUID

from src.core.exceptions import NotFoundError
from src.core.uow import UnitOfWork
from src.schemas.messages import MediaFileResponse, MessageResponse
from src.services.storage import StorageService


class ChatService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.storage = StorageService()

    async def get_chat_history(
        self, contact_id: UUID, limit: int, offset: int
    ) -> list[MessageResponse]:
        async with self.uow:
            contact = await self.uow.contacts.get_by_id(contact_id)
            if not contact:
                raise NotFoundError(detail="Contact not found")

            if contact.unread_count > 0:
                contact.unread_count = 0
                self.uow.session.add(contact)
                await self.uow.commit()

            messages = await self.uow.messages.get_chat_history(
                contact_id, limit, offset
            )

            response_data = []
            for msg in messages:
                media_dtos = []
                for mf in msg.media_files:
                    url = await self.storage.get_presigned_url(mf.r2_key)
                    media_dtos.append(
                        MediaFileResponse(
                            id=mf.id,
                            file_name=mf.file_name,
                            file_mime_type=mf.file_mime_type,
                            url=url,
                            caption=mf.caption,
                        )
                    )

                msg_dto = MessageResponse(
                    id=msg.id,
                    wamid=msg.wamid,
                    direction=msg.direction,
                    status=msg.status,
                    message_type=msg.message_type,
                    body=msg.body,
                    created_at=msg.created_at,
                    media_files=media_dtos,
                )

                response_data.append(msg_dto)

            return list(reversed(response_data))
