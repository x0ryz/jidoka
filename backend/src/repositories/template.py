from sqlalchemy import select
from src.models import Template
from src.repositories.base import BaseRepository


class TemplateRepository(BaseRepository[Template]):
    def __init__(self, session):
        super().__init__(session, Template)

    async def get_active_by_id(self, template_id: str) -> Template | None:
        stmt = select(Template).where(
            Template.id == template_id, Template.status == "APPROVED"
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_meta_id(self, meta_id: str) -> Template | None:
        stmt = select(Template).where(Template.meta_template_id == meta_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_sorted(self) -> list[Template]:
        stmt = select(Template).order_by(Template.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> list[Template]:
        stmt = select(Template).where(Template.status == status.upper())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
