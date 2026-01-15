from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload
from src.models import MediaFile, Message, MessageDirection, MessageStatus
from src.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session):
        super().__init__(session, Message)

    async def create(self, **kwargs) -> Message:
        message = Message(**kwargs)
        self.session.add(message)
        return message

    async def add_media_file(self, message_id: UUID | str, **kwargs) -> MediaFile:
        media_entry = MediaFile(message_id=message_id, **kwargs)
        self.session.add(media_entry)
        return media_entry

    async def get_by_wamid(self, wamid: str) -> Message | None:
        stmt = (
            select(Message)
            .where(Message.wamid == wamid)
            .options(selectinload(Message.contact))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, id: UUID) -> Message | None:
        return await self.session.get(Message, id)

    async def update_status(self, wamid: str, status: MessageStatus) -> Message | None:
        message = await self.get_by_wamid(wamid)
        if message:
            message.status = status
            self.session.add(message)
        return message

    async def get_chat_history(
        self, contact_id: UUID, limit: int, offset: int
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.contact_id == contact_id)
            .options(
                selectinload(Message.media_files),
                selectinload(Message.parent_message).options(
                    selectinload(Message.media_files)
                ),
            )
            .order_by(desc(Message.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        stmt = select(func.count()).select_from(Message)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_direction(self, direction: MessageDirection) -> int:
        stmt = select(func.count()).where(Message.direction == direction)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_recent(self, since: datetime) -> int:
        stmt = select(func.count()).where(Message.created_at >= since)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_delivered_outbound(self) -> int:
        stmt = select(func.count()).where(
            Message.direction == MessageDirection.OUTBOUND,
            Message.status == MessageStatus.DELIVERED,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_recent(self, limit: int) -> list[Message]:
        stmt = select(Message).order_by(desc(Message.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_after(self, timestamp: datetime) -> list[Message]:
        stmt = select(Message).where(Message.created_at >= timestamp)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
