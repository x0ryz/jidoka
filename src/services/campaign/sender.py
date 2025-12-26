import asyncio
from datetime import timedelta
from typing import Awaitable, Callable, Optional
from uuid import UUID

from loguru import logger

from src.clients.meta import MetaClient
from src.core.uow import UnitOfWork
from src.models import (
    Campaign,
    CampaignContact,
    CampaignStatus,
    Contact,
    ContactStatus,
    MessageDirection,
    MessageStatus,
    get_utc_now,
)


class CampaignSenderService:
    """Service for sending campaign messages with rate limiting and 24h window check"""

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

    def _can_send_now(self, contact: Contact) -> bool:
        """
        Check if we can send to this contact now (24-hour window).
        """
        if not contact.last_message_at:
            return True

        now = get_utc_now()
        elapsed = now - contact.last_message_at
        return elapsed < timedelta(hours=24)

    async def start_campaign(self, campaign_id: UUID):
        """Start campaign execution."""
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

    async def process_campaign(self, campaign_id: UUID):
        """
        Main worker method to process campaign messages.
        """
        logger.info(f"Processing campaign {campaign_id}")

        async with self.uow:
            campaign = await self.uow.campaigns.get_by_id(campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return

            if campaign.status != CampaignStatus.RUNNING:
                logger.warning(
                    f"Campaign {campaign_id} is {campaign.status}, not RUNNING"
                )
                return

            mps = campaign.messages_per_second

        # Process in batches of 500
        batch_size = 500
        processed_total = 0

        while True:
            # Збираємо дані (ID) в рамках однієї транзакції
            contacts_data = []

            async with self.uow:
                # Check if still running
                campaign = await self.uow.campaigns.get_by_id(campaign_id)
                if not campaign or campaign.status != CampaignStatus.RUNNING:
                    logger.info(f"Campaign {campaign_id} stopped or paused")
                    break

                mps = campaign.messages_per_second

                # Get sendable contacts objects
                contacts_list = await self.uow.campaign_contacts.get_sendable_contacts(
                    campaign_id, limit=batch_size
                )

                if not contacts_list:
                    logger.info(f"No more contacts to send in campaign {campaign_id}")
                    break

                # Extract IDs to simple dicts/tuples to avoid DetachedInstanceError outside session
                contacts_data = [(c.id, c.contact_id) for c in contacts_list]

                logger.info(
                    f"Processing batch of {len(contacts_data)} contacts for campaign {campaign_id}"
                )

            if not contacts_data:
                break

            # Send to each contact with rate limiting
            delay_between_messages = 1.0 / mps

            for link_id, contact_id in contacts_data:
                # Pass IDs, not objects
                await self._send_to_contact(campaign_id, link_id, contact_id)

                await asyncio.sleep(delay_between_messages)

                processed_total += 1

                if processed_total % 10 == 0:
                    await self._notify_progress(campaign_id)

        # Final check and completion
        await self._check_campaign_completion(campaign_id)

    async def _send_to_contact(
        self, campaign_id: UUID, link_id: UUID, contact_id: UUID
    ):
        """Send message to a single contact by fetching fresh data"""
        try:
            async with self.uow:
                # 1. Load Campaign (with template)
                campaign = await self.uow.campaigns.get_by_id_with_template(campaign_id)
                if not campaign or campaign.status != CampaignStatus.RUNNING:
                    return

                # 2. Load CampaignContact (fresh)
                contact_link = await self.uow.campaign_contacts.get_by_id(link_id)
                if not contact_link:
                    logger.error(f"CampaignContact {link_id} not found")
                    return

                # 3. Load Contact (fresh)
                contact = await self.uow.contacts.get_by_id(contact_id)
                if not contact:
                    logger.error(f"Contact {contact_id} not found")
                    return

                # Check 24-hour window
                if not self._can_send_now(contact):
                    now = get_utc_now()
                    can_send_after = contact.last_message_at + timedelta(hours=24)

                    contact_link.status = ContactStatus.SCHEDULED
                    contact_link.can_send_after = can_send_after
                    contact_link.updated_at = now
                    self.uow.session.add(contact_link)
                    await self.uow.commit()

                    logger.info(
                        f"Contact {contact.phone_number} delayed until {can_send_after}"
                    )
                    return

                # Get WABA phone
                waba_phone = await self.uow.waba.get_default_phone()
                if not waba_phone:
                    logger.error("No WABA phone found")
                    contact_link.status = ContactStatus.FAILED
                    contact_link.error_message = "No WABA phone available"
                    self.uow.session.add(contact_link)
                    await self.uow.commit()
                    return

                # Prepare body
                body_text = campaign.message_body
                if campaign.message_type == "template" and campaign.template:
                    body_text = campaign.template.name

                # Create message in DB
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

                # Build WhatsApp payload
                payload = self._build_whatsapp_payload(campaign, contact)

                # Send via Meta API
                result = await self.meta_client.send_message(
                    waba_phone.phone_number_id, payload
                )

                wamid = result.get("messages", [{}])[0].get("id")

                if wamid:
                    now = get_utc_now()

                    # Update message
                    message.wamid = wamid
                    message.status = MessageStatus.SENT
                    self.uow.session.add(message)

                    # Update contact link
                    contact_link.status = ContactStatus.SENT
                    contact_link.message_id = message.id
                    contact_link.last_sent_at = now
                    contact_link.updated_at = now
                    self.uow.session.add(contact_link)

                    # Update contact
                    contact.last_message_at = now
                    contact.status = ContactStatus.SENT
                    contact.updated_at = now
                    self.uow.session.add(contact)

                    # Update campaign stats
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

        except Exception as e:
            logger.exception(f"Failed to send to contact {contact_id}")

            # Update with error (new transaction)
            try:
                async with self.uow:
                    contact_link = await self.uow.campaign_contacts.get_by_id(link_id)
                    campaign = await self.uow.campaigns.get_by_id(campaign_id)

                    if contact_link:
                        contact_link.status = ContactStatus.FAILED
                        contact_link.error_message = str(e)[:500]
                        contact_link.retry_count += 1
                        contact_link.updated_at = get_utc_now()
                        self.uow.session.add(contact_link)

                    if campaign:
                        campaign.failed_count += 1
                        campaign.updated_at = get_utc_now()
                        self.uow.session.add(campaign)

                    await self.uow.commit()
            except Exception as inner_e:
                logger.error(f"Failed to update error status: {inner_e}")

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

    async def _notify_progress(self, campaign_id: UUID):
        """Send progress notification"""
        async with self.uow:
            campaign = await self.uow.campaigns.get_by_id(campaign_id)

            if not campaign:
                return

            progress = 0.0
            if campaign.total_contacts > 0:
                progress = (campaign.sent_count / campaign.total_contacts) * 100

            await self._notify(
                "campaign_progress",
                {
                    "campaign_id": str(campaign_id),
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
                        "delivered": campaign.delivered_count,
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
