from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models import (
    Campaign,
    CampaignDeliveryStatus,
    CampaignStatus,
    get_utc_now,
)
from src.repositories.campaign import CampaignRepository
from src.services.campaign.tracker import CampaignProgressTracker
from src.services.notifications.service import NotificationService


class CampaignLifecycleManager:
    """Manages campaign lifecycle states and transitions."""

    def __init__(
        self,
        session: AsyncSession,
        campaigns_repo: CampaignRepository,
        notifier: NotificationService,
        trackers: dict[str, CampaignProgressTracker],
    ):
        self.session = session
        self.campaigns = campaigns_repo
        self.notifier = notifier
        self.trackers = trackers

    async def start_campaign(self, campaign: Campaign):
        """Start a campaign and initialize tracking."""
        self._validate_can_start(campaign)

        now = get_utc_now()
        campaign.status = CampaignStatus.RUNNING
        campaign.started_at = now
        campaign.updated_at = now
        self.session.add(campaign)

        # Initialize progress tracker
        self.trackers[str(campaign.id)] = CampaignProgressTracker(
            campaign_id=campaign.id
        )

        await self.session.commit()
        logger.info(f"Campaign {campaign.id} started")

        # Notify
        await self.notifier.notify_campaign_status(
            campaign_id=campaign.id,
            status="running",
            name=campaign.name,
            total_contacts=campaign.total_contacts,
            message_type=campaign.message_type,
            started_at=now.isoformat(),
        )

    async def pause_campaign(self, campaign: Campaign):
        """Pause a running campaign."""
        campaign.status = CampaignStatus.PAUSED
        campaign.updated_at = get_utc_now()
        self.session.add(campaign)
        await self.session.commit()

        logger.info(f"Campaign {campaign.id} paused")

        await self.notifier.notify_campaign_status(
            campaign_id=campaign.id,
            status="paused",
            name=campaign.name,
        )

    async def resume_campaign(self, campaign: Campaign):
        """Resume a paused campaign."""
        logger.info(
            f"Resuming campaign {campaign.id} from status {campaign.status}")
        campaign.status = CampaignStatus.RUNNING
        campaign.updated_at = get_utc_now()
        self.session.add(campaign)
        await self.session.flush()  # Ensure changes are written to DB
        await self.session.commit()
        await self.session.refresh(campaign)

        logger.info(
            f"Campaign {campaign.id} resumed with status {campaign.status}")

        await self.notifier.notify_campaign_status(
            campaign_id=campaign.id,
            status="running",
            name=campaign.name,
        )

    async def complete_campaign(self, campaign: Campaign):
        """Mark campaign as completed and notify."""
        now = get_utc_now()

        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = now
        campaign.updated_at = now
        self.session.add(campaign)
        await self.session.commit()

        # Get tracker for duration
        tracker = self.trackers.get(str(campaign.id))
        duration = tracker.get_elapsed_time() if tracker else None

        logger.info(f"Campaign {campaign.id} completed")

        # Notify
        await self.notifier.notify_campaign_status(
            campaign_id=campaign.id,
            status="completed",
            name=campaign.name,
            total=campaign.total_contacts,
            sent=campaign.sent_count,
            delivered=campaign.delivered_count,
            failed=campaign.failed_count,
            duration_seconds=duration,
            completed_at=now.isoformat(),
        )

        # Clean up tracker
        if str(campaign.id) in self.trackers:
            del self.trackers[str(campaign.id)]

    async def check_and_complete_if_done(self, campaign_id: UUID):
        """Check if campaign is completed and update status if so."""
        campaign = await self.campaigns.get_by_id(campaign_id)

        if not campaign:
            logger.debug(f"Campaign {campaign_id} not found")
            return

        if campaign.status not in [CampaignStatus.RUNNING, CampaignStatus.PAUSED]:
            logger.debug(
                f"Campaign {campaign_id} is {campaign.status}, not checking completion")
            return

        # Determine remaining contacts that still could be processed
        # Note: We only count QUEUED contacts as remaining, not FAILED ones that
        # haven't been retried yet, because we don't have a retry mechanism
        # (failed contacts aren't republished to NATS queue)
        from sqlalchemy import select
        from src.models import CampaignContact

        remaining_stmt = select(CampaignContact).where(
            CampaignContact.campaign_id == campaign_id,
            (
                # Only queued contacts (not yet attempted)
                (CampaignContact.status == CampaignDeliveryStatus.QUEUED)
                # OR failed contacts that haven't been attempted yet (shouldn't happen but just in case)
                | (
                    (CampaignContact.status == CampaignDeliveryStatus.FAILED)
                    & (CampaignContact.retry_count == 0)
                )
            ),
        )
        remaining_result = await self.session.execute(remaining_stmt)
        remaining = len(list(remaining_result.scalars().all()))

        logger.info(
            f"Campaign {campaign_id} completion check: "
            f"remaining={remaining}, "
            f"total={campaign.total_contacts}, "
            f"sent={campaign.sent_count}, "
            f"delivered={campaign.delivered_count}, "
            f"failed={campaign.failed_count}, "
            f"read={campaign.read_count}, "
            f"replied={campaign.replied_count}"
        )

        if remaining > 0:
            logger.debug(
                f"Campaign {campaign_id}: still {remaining} contacts remaining (queued or retryable). "
                f"Not completing yet."
            )
            return

        # No remaining contacts; complete the campaign
        logger.info(
            f"Completing campaign {campaign_id}: all contacts processed. Sent: {campaign.sent_count}, "
            f"Failed exhausted: {campaign.failed_count}"
        )
        await self.complete_campaign(campaign)

    @staticmethod
    def _validate_can_start(campaign: Campaign):
        """Validate that campaign can be started."""
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            raise ValueError(
                f"Cannot start campaign in {campaign.status} status")

        if campaign.total_contacts == 0:
            raise ValueError("Cannot start campaign with no contacts")
