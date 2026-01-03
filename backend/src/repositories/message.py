from sqlalchemy.orm import selectinload
from sqlmodel import desc, select
from src.models import MediaFile, Message, MessageStatus
from src.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """
    Message repository.

    IMPORTANT: This repository does NOT commit changes.
    The caller (service) is responsible for transaction management.
    """

    def __init__(self, session):
        super().__init__(session, Message)

    async def create(self, **kwargs) -> Message:
        """
        Create a new message entity.

        Note: Entity is added to session but NOT flushed or committed.
        Caller must flush to get ID, and commit to persist.
        """
        message = Message(**kwargs)
        self.session.add(message)
        return message

    async def add_media_file(self, message_id: str, **kwargs) -> MediaFile:
        """
        Add media file to message.

        Note: Does NOT commit.
        """
        media_entry = MediaFile(message_id=message_id, **kwargs)
        self.session.add(media_entry)
        return media_entry

    async def get_by_wamid(self, wamid: str) -> Message | None:
        """Get message by WhatsApp message ID."""
        stmt = (
            select(Message)
            .where(Message.wamid == wamid)
            .options(selectinload(Message.contact))
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def update_status(self, wamid: str, status: MessageStatus) -> Message | None:
        """
        Update message status.

        Note: Does NOT commit.
        """
        message = await self.get_by_wamid(wamid)
        if message:
            message.status = status
            self.session.add(message)
        return message

    async def get_chat_history(
        self, contact_id: str, limit: int, offset: int
    ) -> list[Message]:
        """Get message history with contact, including media files."""
        stmt = (
            select(Message)
            .where(Message.contact_id == contact_id)
            .options(selectinload(Message.media_files))
            .order_by(desc(Message.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.exec(stmt)
        return list(result.all())
