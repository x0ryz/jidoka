"""Service for updating campaign statistics based on message status changes."""

import uuid

from loguru import logger

from src.core.uow import UnitOfWork
from src.models import CampaignDeliveryStatus, MessageStatus


class CampaignStatsService:
    """Manages campaign delivery statistics and status updates."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def update_on_status_change(
        self, message_id: uuid.UUID, new_status: MessageStatus
    ) -> None:
        """
        Update campaign statistics when a message status changes.

        Args:
            message_id: Database ID of the message (UUID)
            new_status: New message status (DELIVERED, READ, FAILED)
        """
        campaign_link = await self.uow.campaign_contacts.get_by_message_id(message_id)

        if not campaign_link:
            return  # Not a campaign message

        # Don't update if already marked as replied
        if campaign_link.status == CampaignDeliveryStatus.REPLIED:
            return

        campaign = await self.uow.campaigns.get_by_id(campaign_link.campaign_id)
        if not campaign:
            logger.warning(f"Campaign {campaign_link.campaign_id} not found")
            return

        # Update campaign counters based on status transition
        if new_status == MessageStatus.DELIVERED:
            await self._handle_delivered(campaign, campaign_link)
        elif new_status == MessageStatus.READ:
            await self._handle_read(campaign, campaign_link)
        elif new_status == MessageStatus.FAILED:
            await self._handle_failed(campaign, campaign_link)

        self.uow.campaigns.add(campaign)
        self.uow.campaign_contacts.add(campaign_link)

    async def _handle_delivered(self, campaign, campaign_link):
        """Handle transition to DELIVERED status."""
        if campaign_link.status in [
            CampaignDeliveryStatus.READ,
            CampaignDeliveryStatus.FAILED,
        ]:
            # Don't downgrade from READ or FAILED
            return

        campaign_link.status = CampaignDeliveryStatus.DELIVERED
        campaign.delivered_count += 1
        campaign.sent_count = max(0, campaign.sent_count - 1)

    async def _handle_read(self, campaign, campaign_link):
        """Handle transition to READ status."""
        campaign_link.status = CampaignDeliveryStatus.READ
        campaign.read_count += 1
        campaign.delivered_count = max(0, campaign.delivered_count - 1)

    async def _handle_failed(self, campaign, campaign_link):
        """Handle transition to FAILED status."""
        campaign_link.status = CampaignDeliveryStatus.FAILED
        campaign.failed_count += 1
        # Note: Don't decrement other counters since we don't know
        # what the previous status was in the campaign_link
