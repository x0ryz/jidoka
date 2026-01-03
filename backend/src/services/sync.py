from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.clients.meta import MetaClient
from src.models import Template, WabaAccount, WabaPhoneNumber, get_utc_now


class SyncService:
    """
    Service for syncing WABA data from Meta.

    Responsibilities:
    - Sync account information
    - Sync phone numbers
    - Sync message templates
    """

    def __init__(self, session: AsyncSession, meta_client: MetaClient):
        self.session = session
        self.meta_client = meta_client

    async def sync_account_data(self):
        """
        Sync all WABA data from Meta.

        Syncs:
        1. Account information
        2. Phone numbers
        3. Message templates
        """
        waba_account = await self._get_waba_account()
        if not waba_account:
            logger.warning("No WABA accounts found in the database.")
            return

        logger.info(f"Syncing WABA account ID: {waba_account.waba_id}")

        try:
            # Sync account info
            await self._sync_account_info(waba_account)

            # Sync phone numbers
            await self._sync_phone_numbers(waba_account)

            # Sync templates
            await self._sync_templates(waba_account)

            logger.success(f"Synced account '{waba_account.name}' successfully")

        except Exception as e:
            logger.exception(f"Failed to sync WABA ID {waba_account.waba_id}")
            raise

    async def _get_waba_account(self) -> WabaAccount | None:
        """Get the first WABA account from database."""
        stmt = select(WabaAccount)
        result = await self.session.exec(stmt)
        return result.first()

    async def _sync_account_info(self, waba_account: WabaAccount):
        """Sync account information from Meta."""
        account_info = await self.meta_client.fetch_account_info(waba_account.waba_id)

        waba_account.name = account_info.get("name")
        waba_account.account_review_status = account_info.get("account_review_status")
        waba_account.business_verification_status = account_info.get(
            "business_verification_status"
        )

        self.session.add(waba_account)
        await self.session.commit()
        await self.session.refresh(waba_account)

    async def _sync_phone_numbers(self, waba_account: WabaAccount):
        """Sync phone numbers from Meta."""
        phones_data = await self.meta_client.fetch_phone_numbers(waba_account.waba_id)

        for item in phones_data.get("data", []):
            await self._upsert_phone_number(waba_account.id, item)

        await self.session.commit()

    async def _upsert_phone_number(self, waba_db_id, item: dict):
        """Create or update a phone number."""
        phone_id = item.get("id")

        # Check if exists
        stmt = select(WabaPhoneNumber).where(
            WabaPhoneNumber.phone_number_id == phone_id
        )
        result = await self.session.exec(stmt)
        phone_obj = result.first()

        if not phone_obj:
            # Create new
            phone_obj = WabaPhoneNumber(
                waba_id=waba_db_id,
                phone_number_id=phone_id,
                display_phone_number=item.get("display_phone_number"),
                status=item.get("code_verification_status"),
                quality_rating=item.get("quality_rating", "UNKNOWN"),
                messaging_limit_tier=item.get("messaging_limit_tier"),
            )
        else:
            # Update existing
            phone_obj.status = item.get("code_verification_status")
            phone_obj.quality_rating = item.get("quality_rating", "UNKNOWN")
            phone_obj.messaging_limit_tier = item.get("messaging_limit_tier")
            phone_obj.updated_at = get_utc_now()

        self.session.add(phone_obj)

    async def _sync_templates(self, waba_account: WabaAccount):
        """Sync message templates from Meta."""
        logger.info(f"Syncing templates for WABA: {waba_account.name}")

        try:
            data = await self.meta_client.fetch_templates(waba_account.waba_id)

            for item in data.get("data", []):
                await self._upsert_template(waba_account.id, item)

            await self.session.commit()
            logger.success("Templates synced successfully")

        except Exception as e:
            logger.exception("Failed to sync templates")
            raise

    async def _upsert_template(self, waba_id, item: dict):
        """Create or update a template."""
        meta_id = item.get("id")

        # Check if exists
        stmt = select(Template).where(Template.meta_template_id == meta_id)
        result = await self.session.exec(stmt)
        existing = result.first()

        if not existing:
            # Create new
            existing = Template(
                waba_id=waba_id,
                meta_template_id=meta_id,
                name=item.get("name"),
                language=item.get("language"),
                status=item.get("status"),
                category=item.get("category"),
                components=item.get("components", []),
            )
        else:
            # Update existing
            existing.status = item.get("status")
            existing.components = item.get("components", [])
            existing.updated_at = get_utc_now()

        self.session.add(existing)
