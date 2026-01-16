from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.replies import QuickReply


class QuickReplyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> QuickReply:
        """Create a new quick reply"""
        quick_reply = QuickReply(**data)
        self.session.add(quick_reply)
        return quick_reply

    async def get_all(self) -> list[QuickReply]:
<<<<<<< HEAD
        """Get all quick replies ordered by shortcut"""
        query = select(QuickReply).order_by(QuickReply.shortcut)
=======
        """Get all quick replies ordered by title"""
        query = select(QuickReply).order_by(QuickReply.title)
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, reply_id: UUID) -> QuickReply | None:
        """Get quick reply by ID"""
        return await self.session.get(QuickReply, reply_id)

<<<<<<< HEAD
    async def get_by_shortcut(self, shortcut: str) -> QuickReply | None:
        """Get quick reply by shortcut"""
        query = select(QuickReply).where(QuickReply.shortcut == shortcut)
        result = await self.session.execute(query)
        return result.scalars().first()
=======

>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)

    async def update(self, reply_id: UUID, data: dict) -> QuickReply | None:
        """Update quick reply"""
        quick_reply = await self.get_by_id(reply_id)
        if not quick_reply:
            return None

        for key, value in data.items():
            if value is not None:
                setattr(quick_reply, key, value)

        self.session.add(quick_reply)
        await self.session.flush()
        return quick_reply

    async def delete(self, reply_id: UUID) -> bool:
        """Delete quick reply"""
        quick_reply = await self.get_by_id(reply_id)
        if not quick_reply:
            return False

        await self.session.delete(quick_reply)
        return True

    async def search_by_title(self, query: str) -> list[QuickReply]:
        """Search quick replies by title"""
        stmt = (
            select(QuickReply)
            .where(QuickReply.title.ilike(f"%{query}%"))
            .order_by(QuickReply.title)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_language(self, language: str) -> list[QuickReply]:
        """Get quick replies that have content for specified language"""
        stmt = (
            select(QuickReply)
            .where(QuickReply.content.op("?")(language))
<<<<<<< HEAD
            .order_by(QuickReply.shortcut)
=======
            .order_by(QuickReply.title)
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        """Count total number of quick replies"""
        from sqlalchemy import func

        query = select(func.count(QuickReply.id))
        result = await self.session.execute(query)
        return result.scalar() or 0
