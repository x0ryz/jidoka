from uuid import UUID

from sqlalchemy.exc import IntegrityError
from src.core.exceptions import BadRequestError, NotFoundError
from src.core.uow import UnitOfWork
from src.models.replies import QuickReply
from src.schemas.replies import QuickReplyCreate, QuickReplyUpdate


class QuickReplyService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_quick_reply(self, data: QuickReplyCreate) -> QuickReply:
        """Create a new quick reply"""
        async with self.uow:
            try:
                quick_reply = await self.uow.quick_replies.create(data.model_dump())
                await self.uow.commit()
                await self.uow.session.refresh(quick_reply)
                return quick_reply
            except IntegrityError:
                raise BadRequestError(
                    detail="Quick reply with this shortcut already exists"
                )

    async def get_all_quick_replies(self) -> list[QuickReply]:
        """Get all quick replies"""
        async with self.uow:
            return await self.uow.quick_replies.get_all()

    async def get_quick_reply(self, reply_id: UUID) -> QuickReply:
        """Get quick reply by ID"""
        async with self.uow:
            quick_reply = await self.uow.quick_replies.get_by_id(reply_id)
            if not quick_reply:
                raise NotFoundError(detail="Quick reply not found")
            return quick_reply

    async def get_by_shortcut(self, shortcut: str) -> QuickReply:
        """Get quick reply by shortcut"""
        async with self.uow:
            quick_reply = await self.uow.quick_replies.get_by_shortcut(shortcut)
            if not quick_reply:
                raise NotFoundError(
                    detail=f"Quick reply with shortcut '{shortcut}' not found"
                )
            return quick_reply

    async def update_quick_reply(
        self, reply_id: UUID, data: QuickReplyUpdate
    ) -> QuickReply:
        """Update quick reply"""
        async with self.uow:
            update_data = data.model_dump(exclude_unset=True)

            # Check if shortcut is being updated and if it conflicts
            if "shortcut" in update_data:
                existing = await self.uow.quick_replies.get_by_shortcut(
                    update_data["shortcut"]
                )
                if existing and existing.id != reply_id:
                    raise BadRequestError(
                        detail="Quick reply with this shortcut already exists"
                    )

            quick_reply = await self.uow.quick_replies.update(reply_id, update_data)
            if not quick_reply:
                raise NotFoundError(detail="Quick reply not found")

            await self.uow.commit()
            await self.uow.session.refresh(quick_reply)
            return quick_reply

    async def delete_quick_reply(self, reply_id: UUID) -> None:
        """Delete quick reply"""
        async with self.uow:
            success = await self.uow.quick_replies.delete(reply_id)
            if not success:
                raise NotFoundError(detail="Quick reply not found")
            await self.uow.commit()

    async def search_quick_replies(self, query: str) -> list[QuickReply]:
        """Search quick replies by title"""
        async with self.uow:
            return await self.uow.quick_replies.search_by_title(query)

    async def get_text(self, reply_id: UUID, language: str) -> tuple[str, str]:
        """Get text for quick reply in specified language"""
        async with self.uow:
            quick_reply = await self.uow.quick_replies.get_by_id(reply_id)
            if not quick_reply:
                raise NotFoundError(detail="Quick reply not found")

            text = quick_reply.get_text(language)
            actual_language = (
                language
                if language in quick_reply.content
                else quick_reply.default_language
            )

            return text, actual_language

    async def get_by_language(self, language: str) -> list[QuickReply]:
        """Get quick replies that have content for specified language"""
        async with self.uow:
            return await self.uow.quick_replies.get_by_language(language)

    async def get_stats(self) -> dict:
        """Get quick reply statistics"""
        async with self.uow:
            total_count = await self.uow.quick_replies.count_all()
            all_replies = await self.uow.quick_replies.get_all()

            # Count unique languages
            languages = set()
            for reply in all_replies:
                languages.update(reply.content.keys())

            return {
                "total_quick_replies": total_count,
                "unique_languages": len(languages),
                "available_languages": sorted(list(languages)),
            }

    async def add_language_content(
        self, reply_id: UUID, language: str, content: str
    ) -> QuickReply:
        """Add content for a new language to existing quick reply"""
        async with self.uow:
            quick_reply = await self.uow.quick_replies.get_by_id(reply_id)
            if not quick_reply:
                raise NotFoundError(detail="Quick reply not found")

            # Update content with new language
            new_content = quick_reply.content.copy()
            new_content[language] = content

            updated_reply = await self.uow.quick_replies.update(
                reply_id, {"content": new_content}
            )
            await self.uow.commit()
            await self.uow.session.refresh(updated_reply)

            return updated_reply

    async def remove_language_content(
        self, reply_id: UUID, language: str
    ) -> QuickReply:
        """Remove content for a specific language from quick reply"""
        async with self.uow:
            quick_reply = await self.uow.quick_replies.get_by_id(reply_id)
            if not quick_reply:
                raise NotFoundError(detail="Quick reply not found")

            if language == quick_reply.default_language:
                raise BadRequestError(detail="Cannot remove default language content")

            if language not in quick_reply.content:
                raise BadRequestError(
                    detail=f"Language '{language}' not found in quick reply content"
                )

            # Update content by removing the language
            new_content = quick_reply.content.copy()
            del new_content[language]

            updated_reply = await self.uow.quick_replies.update(
                reply_id, {"content": new_content}
            )
            await self.uow.commit()
            await self.uow.session.refresh(updated_reply)

            return updated_reply
