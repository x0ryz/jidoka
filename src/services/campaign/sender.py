from typing import Awaitable, Callable, Optional
from uuid import UUID

from loguru import logger

from src.clients.meta import MetaClient
from src.core.uow import UnitOfWork
from src.models import (
    Campaign,
    CampaignStatus,
    Contact,
    ContactStatus,
    MessageDirection,
    MessageStatus,
    get_utc_now,
)


class CampaignSenderService:
    """Service for sending single campaign messages without internal scheduling logic"""

    def __init__(
        self,
        uow: UnitOfWork,
        meta_client: MetaClient,
        notifier: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        self.uow = uow
        self.meta_client = meta_client
        self.notifier = notifier

    async def _notify(self, event_type: str, data: dict):
        """Send notification via Redis pub/sub for WebSocket"""
        if self.notifier:
            payload = {"event": event_type, "data": data}
            await self.notifier(payload)

    async def start_campaign(self, campaign_id: UUID):
        """Start campaign execution (just status update)"""
        async with self.uow:
            campaign = await self.uow.campaigns.get_by_id_with_template(campaign_id)

            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
                raise ValueError(f"Cannot start campaign in {campaign.status} status")

            if campaign.total_contacts == 0:
                raise ValueError("Cannot start campaign with no contacts")

            # Update status
            now = get_utc_now()
            campaign.status = CampaignStatus.RUNNING
            campaign.started_at = now
            campaign.updated_at = now
            self.uow.session.add(campaign)

            logger.info(f"Campaign {campaign_id} started")

            await self._notify(
                "campaign_started",
                {
                    "campaign_id": str(campaign_id),
                    "name": campaign.name,
                    "total_contacts": campaign.total_contacts,
                },
            )
            await self.uow.commit()

    async def send_single_message(
        self, campaign_id: UUID, link_id: UUID, contact_id: UUID
    ):
        """
        Main Method: Sends a message to a single contact.
        No loops, no sleeps. Logic is atomic.
        """
        try:
            async with self.uow:
                campaign = await self.uow.campaigns.get_by_id_with_template(campaign_id)
                contact_link = await self.uow.campaign_contacts.get_by_id(link_id)
                contact = await self.uow.contacts.get_by_id(contact_id)

                if not campaign or not contact_link or not contact:
                    logger.warning(f"Data missing for send task: link {link_id}")
                    return

                if campaign.status != CampaignStatus.RUNNING:
                    logger.info(
                        f"Skipping contact {contact_id}: Campaign is {campaign.status}"
                    )
                    return

                if contact_link.status == ContactStatus.SENT:
                    logger.warning(f"Contact {contact_id} already sent")
                    return

                waba_phone = await self.uow.waba.get_default_phone()
                if not waba_phone:
                    await self._mark_as_failed(
                        contact_link, campaign, "No WABA phone available"
                    )
                    return

                body_text = campaign.message_body
                if campaign.message_type == "template" and campaign.template:
                    body_text = campaign.template.name

                message = await self.uow.messages.create(
                    auto_flush=True,
                    waba_phone_id=waba_phone.id,
                    contact_id=contact.id,
                    direction=MessageDirection.OUTBOUND,
                    status=MessageStatus.PENDING,
                    message_type=campaign.message_type,
                    body=body_text,
                    template_id=campaign.template_id,
                )

                payload = self._build_whatsapp_payload(campaign, contact)

                result = await self.meta_client.send_message(
                    waba_phone.phone_number_id, payload
                )

                wamid = result.get("messages", [{}])[0].get("id")

                if wamid:
                    now = get_utc_now()

                    message.wamid = wamid
                    message.status = MessageStatus.SENT
                    self.uow.session.add(message)

                    contact_link.status = ContactStatus.SENT
                    contact_link.message_id = message.id
                    contact_link.updated_at = now
                    self.uow.session.add(contact_link)

                    contact.last_message_at = now
                    contact.status = ContactStatus.SENT
                    contact.updated_at = now
                    self.uow.session.add(contact)

                    campaign.sent_count += 1
                    campaign.updated_at = now
                    self.uow.session.add(campaign)

                    await self.uow.commit()

                    logger.info(
                        f"Message sent to {contact.phone_number}, WAMID: {wamid}"
                    )

                    await self._notify(
                        "message_sent",
                        {
                            "campaign_id": str(campaign.id),
                            "contact_id": str(contact.id),
                            "phone": contact.phone_number,
                            "wamid": wamid,
                        },
                    )

                    await self._notify_progress(campaign)

                else:
                    raise Exception("No WAMID in Meta response")

        except Exception as e:
            logger.exception(f"Failed to send to contact {contact_id}")
            async with self.uow:
                contact_link = await self.uow.campaign_contacts.get_by_id(link_id)
                campaign = await self.uow.campaigns.get_by_id(campaign_id)
                if contact_link and campaign:
                    await self._mark_as_failed(contact_link, campaign, str(e))

        await self._check_campaign_completion(campaign_id)

    async def _mark_as_failed(self, link, campaign, error_msg: str):
        """Helper to mark contact and campaign stats as failed"""
        link.status = ContactStatus.FAILED
        link.error_message = error_msg[:500]
        link.retry_count += 1
        link.updated_at = get_utc_now()
        self.uow.session.add(link)

        campaign.failed_count += 1
        campaign.updated_at = get_utc_now()
        self.uow.session.add(campaign)

        await self.uow.commit()

    def _build_whatsapp_payload(self, campaign: Campaign, contact: Contact) -> dict:
        """Build Meta API payload for message"""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": contact.phone_number,
            "type": campaign.message_type,
        }

        if campaign.message_type == "text":
            payload["text"] = {"body": campaign.message_body}

        elif campaign.message_type == "template":
            if not campaign.template:
                raise ValueError("Template not found for campaign")

            payload["template"] = {
                "name": campaign.template.name,
                "language": {"code": campaign.template.language},
            }

        return payload

    async def _notify_progress(self, campaign: Campaign):
        """Send progress notification based on campaign object"""
        progress = 0.0
        if campaign.total_contacts > 0:
            progress = (campaign.sent_count / campaign.total_contacts) * 100

        await self._notify(
            "campaign_progress",
            {
                "campaign_id": str(campaign.id),
                "total": campaign.total_contacts,
                "sent": campaign.sent_count,
                "delivered": campaign.delivered_count,
                "failed": campaign.failed_count,
                "progress": round(progress, 2),
            },
        )

    async def _check_campaign_completion(self, campaign_id: UUID):
        """Check if campaign is completed and update status"""
        async with self.uow:
            campaign = await self.uow.campaigns.get_by_id(campaign_id)

            if not campaign or campaign.status != CampaignStatus.RUNNING:
                return

            # Check if there are any remaining contacts
            remaining = await self.uow.campaign_contacts.get_sendable_contacts(
                campaign_id, limit=1
            )

            if not remaining:
                now = get_utc_now()
                campaign.status = CampaignStatus.COMPLETED
                campaign.completed_at = now
                campaign.updated_at = now
                self.uow.session.add(campaign)
                await self.uow.commit()

                logger.info(f"Campaign {campaign_id} completed")

                await self._notify(
                    "campaign_completed",
                    {
                        "campaign_id": str(campaign_id),
                        "name": campaign.name,
                        "total": campaign.total_contacts,
                        "sent": campaign.sent_count,
                        "failed": campaign.failed_count,
                    },
                )

    async def pause_campaign(self, campaign_id: UUID):
        async with self.uow:
            campaign = await self.uow.campaigns.get_by_id(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            campaign.status = CampaignStatus.PAUSED
            campaign.updated_at = get_utc_now()
            self.uow.session.add(campaign)
            await self.uow.commit()

            await self._notify(
                "campaign_paused",
                {"campaign_id": str(campaign_id), "name": campaign.name},
            )

    async def resume_campaign(self, campaign_id: UUID):
        async with self.uow:
            campaign = await self.uow.campaigns.get_by_id(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            campaign.status = CampaignStatus.RUNNING
            campaign.updated_at = get_utc_now()
            self.uow.session.add(campaign)
            await self.uow.commit()

            await self._notify(
                "campaign_resumed",
                {"campaign_id": str(campaign_id), "name": campaign.name},
            )
