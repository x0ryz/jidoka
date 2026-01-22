from uuid import UUID

from sqlalchemy import select, update

from src.models import WabaAccount, WabaPhoneNumber, get_utc_now
from src.repositories.base import BaseRepository


class WabaRepository(BaseRepository[WabaAccount]):
    def __init__(self, session):
        super().__init__(session, WabaAccount)

    async def get_credentials(self) -> WabaAccount | None:
        stmt = select(WabaAccount).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_waba_id(self, waba_id: str) -> WabaAccount | None:
        stmt = select(WabaAccount).where(WabaAccount.waba_id == waba_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_accounts(self) -> list[WabaAccount]:
        return await self.get_all()


class WabaPhoneRepository(BaseRepository[WabaPhoneNumber]):
    def __init__(self, session):
        super().__init__(session, WabaPhoneNumber)

    async def get_by_phone_id(
        self, phone_number_id: str, include_deleted: bool = False
    ) -> WabaPhoneNumber | None:
        """Get phone by phone_number_id. By default excludes deleted phones."""
        stmt = select(WabaPhoneNumber).where(
            WabaPhoneNumber.phone_number_id == phone_number_id
        )
        if not include_deleted:
            stmt = stmt.where(WabaPhoneNumber.is_deleted == False)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_display_phone(self, phone: str) -> WabaPhoneNumber | None:
        stmt = select(WabaPhoneNumber).where(
            WabaPhoneNumber.display_phone_number == phone,
            WabaPhoneNumber.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_phones(self) -> list[WabaPhoneNumber]:
        stmt = select(WabaPhoneNumber).where(
            WabaPhoneNumber.is_deleted == False)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_by_waba_id(self, waba_id: UUID) -> list[WabaPhoneNumber]:
        """Get all phone numbers (including deleted) for a specific WABA account."""
        stmt = select(WabaPhoneNumber).where(
            WabaPhoneNumber.waba_id == waba_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete_by_phone_ids(self, phone_ids: list[str]) -> int:
        """Soft delete phone numbers by their phone_number_id. Returns count of deleted phones."""
        if not phone_ids:
            return 0
        stmt = (
            update(WabaPhoneNumber)
            .where(WabaPhoneNumber.phone_number_id.in_(phone_ids))
            .values(is_deleted=True, updated_at=get_utc_now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def restore_by_phone_ids(self, phone_ids: list[str]) -> int:
        """Restore soft-deleted phone numbers."""
        if not phone_ids:
            return 0
        stmt = (
            update(WabaPhoneNumber)
            .where(WabaPhoneNumber.phone_number_id.in_(phone_ids))
            .values(is_deleted=False, updated_at=get_utc_now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount
