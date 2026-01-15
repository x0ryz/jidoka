from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, session: AsyncSession, model: type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: UUID) -> ModelType | None:
        return await self.session.get(self.model, id)

    async def get_all(self) -> list[ModelType]:
        stmt = select(self.model)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def add(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        return obj

    async def delete(self, id: UUID) -> None:
        obj = await self.get_by_id(id)
        if obj:
            await self.session.delete(obj)
