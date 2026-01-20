from src.core.uow import UnitOfWork
from src.models import MessageStatus
from src.schemas import MetaStatus
from src.services.campaign.stats import CampaignStatsService
from src.services.notifications.service import NotificationService


class StatusHandler:
    """Handles message status updates from WhatsApp webhook."""

    def __init__(
        self,
        uow: UnitOfWork,
        notifier: NotificationService,
        campaign_stats: CampaignStatsService,
    ):
        self.uow = uow
        self.notifier = notifier
        self.campaign_stats = campaign_stats

    async def handle(self, statuses: list[MetaStatus]):
        """Process status updates for messages."""
        status_map = {
            "sent": MessageStatus.SENT,
            "delivered": MessageStatus.DELIVERED,
            "read": MessageStatus.READ,
            "failed": MessageStatus.FAILED,
        }

        notifications_to_send = []

        async with self.uow:
            for status in statuses:
                new_status = status_map.get(status.status)
                if not new_status:
                    continue

                db_message = await self.uow.messages.get_by_wamid(status.id)
                if not db_message:
                    continue

                if self._is_newer_status(db_message.status, new_status):
                    db_message.status = new_status
                    self.uow.messages.add(db_message)

                    # Update campaign statistics (decoupled via service)
                    await self.campaign_stats.update_on_status_change(
                        db_message.id, new_status
                    )

                    # Prepare notification data (don't send yet)
                    notifications_to_send.append(
                        {
                            "message_id": db_message.id,
                            "wamid": status.id,
                            "status": status.status,
                            "phone": db_message.contact.phone_number
                            if db_message.contact
                            else None,
                        }
                    )

            # Commit transaction first
            await self.uow.commit()

        # Send notifications after commit
        for note in notifications_to_send:
            await self.notifier.notify_message_status(**note)

    def _is_newer_status(self, old: MessageStatus, new: MessageStatus) -> bool:
        """Check if the new status is a progression from the old status."""
        weights = {
            MessageStatus.PENDING: 0,
            MessageStatus.SENT: 1,
            MessageStatus.DELIVERED: 2,
            MessageStatus.READ: 3,
            MessageStatus.FAILED: 4,
        }
        return weights.get(new, -1) > weights.get(old, -1)
