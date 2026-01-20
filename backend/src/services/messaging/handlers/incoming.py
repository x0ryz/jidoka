import base64
import uuid
from typing import Optional

from loguru import logger

from src.core.broker import broker
from src.core.uow import UnitOfWork
from src.models import MessageDirection, MessageStatus, get_utc_now
from src.schemas import MetaMessage
from src.services.media.service import MediaService
from src.services.notifications.service import NotificationService


class IncomingMessageHandler:
    """Handles incoming messages and reactions from WhatsApp webhook."""

    def __init__(
        self,
        uow: UnitOfWork,
        media_service: MediaService,
        notifier: NotificationService,
    ):
        self.uow = uow
        self.media = media_service
        self.notifier = notifier

    async def handle(self, messages: list[MetaMessage], phone_number_id: str):
        """Process incoming messages and reactions."""
        waba_phone_db_id = await self._get_waba_phone_id(phone_number_id)
        if not waba_phone_db_id:
            logger.warning(f"Unknown phone ID: {phone_number_id}")
            return

        for msg in messages:
            if msg.type == "reaction" and msg.reaction:
                await self._handle_reaction(msg)
            else:
                await self._handle_message(msg, waba_phone_db_id)

    async def _get_waba_phone_id(self, phone_number_id: str) -> Optional[uuid.UUID]:
        """Retrieve WABA phone database ID."""
        async with self.uow:
            waba_phone = await self.uow.waba_phones.get_by_phone_id(phone_number_id)
            return waba_phone.id if waba_phone else None

    async def _handle_reaction(self, msg: MetaMessage):
        """Handle reaction updates to existing messages."""
        reaction_notification = None

        async with self.uow:
            target_msg = await self.uow.messages.get_by_wamid(msg.reaction.message_id)

            if not target_msg:
                target_msg = await self._fuzzy_find_message(
                    msg.from_, msg.reaction.message_id
                )

            if target_msg:
                target_msg.reaction = msg.reaction.emoji
                self.uow.messages.add(target_msg)
                logger.info(
                    f"Updated reaction for msg {target_msg.id}: {msg.reaction.emoji}"
                )
                reaction_notification = {
                    "message_id": target_msg.id,
                    "reaction": msg.reaction.emoji,
                    "phone": msg.from_,
                }
                await self.uow.commit()
            else:
                logger.warning(
                    f"Target message {msg.reaction.message_id} not found anywhere."
                )

        if reaction_notification:
            await self.notifier.notify_message_reaction(**reaction_notification)

    async def _handle_message(self, msg: MetaMessage, waba_phone_db_id: uuid.UUID):
        """Handle regular incoming messages."""
        media_download_task = None
        notification_data = None
        websocket_data = None

        async with self.uow:
            # Deduplication check
            if await self.uow.messages.get_by_wamid(msg.id):
                logger.info(f"Message {msg.id} deduplicated")
                return

            contact = await self.uow.contacts.get_or_create(msg.from_)
            contact.unread_count += 1
            contact.updated_at = get_utc_now()

            # Extract body
            body = self._extract_message_body(msg)

            # Resolve Context / Reply
            reply_to_uuid = await self._resolve_reply_context(msg)

            # Update Campaign Logic (mark as replied)
            await self._update_campaign_on_reply(contact.id)

            # Create Message
            new_msg = await self.uow.messages.create(
                waba_phone_id=waba_phone_db_id,
                contact_id=contact.id,
                direction=MessageDirection.INBOUND,
                status=MessageStatus.RECEIVED,
                wamid=msg.id,
                message_type=msg.type,
                body=body,
                reply_to_message_id=reply_to_uuid,
            )

            await self.uow.session.flush()

            # Update Contact Metadata
            contact.last_message_id = new_msg.id
            contact.last_message_at = get_utc_now()
            contact.last_incoming_message_at = get_utc_now()
            self.uow.contacts.add(contact)

            # Prepare Media Task
            if msg.type in [
                "image",
                "video",
                "document",
                "audio",
                "voice",
                "sticker",
            ]:
                media_meta = getattr(msg, msg.type, None)
                if media_meta:
                    media_download_task = {
                        "message_id": str(new_msg.id),
                        "meta_media_id": media_meta.id,
                        "media_type": msg.type,
                        "mime_type": media_meta.mime_type or "application/octet-stream",
                        "caption": media_meta.caption,
                    }

            # Prepare Notifications
            notification_data = new_msg

            preview_body = body if body else f"Sent {msg.type}"
            websocket_data = {
                "event": "contact_updated",
                "data": {
                    "id": str(contact.id),
                    "phone_number": contact.phone_number,
                    "unread_count": contact.unread_count,
                    "last_message_at": contact.last_message_at.isoformat(),
                    "last_message_body": preview_body,
                    "last_message_type": msg.type,
                    "last_message_status": "received",
                },
                "timestamp": get_utc_now().isoformat(),
            }

            # COMMIT TRANSACTION
            await self.uow.commit()

        # Execute Side Effects (After Commit)

        # 1. Publish Media Task to NATS
        if media_download_task:
            await broker.publish(media_download_task, subject="media.download")
            logger.info(
                f"Queued media download for msg {media_download_task['message_id']}"
            )

        # 2. Notify WebSocket (New Message)
        if notification_data:
            await self.notifier.notify_new_message(
                notification_data,
                phone=websocket_data["data"]["phone_number"],
                media_files=[],
            )

        # 3. Notify WebSocket (Contact Update)
        if websocket_data:
            await self.notifier._publish(websocket_data)

    async def _resolve_reply_context(self, msg: MetaMessage) -> Optional[uuid.UUID]:
        """Resolve the parent message UUID for replies."""
        if not msg.context or not msg.context.id:
            return None

        ctx_wamid = msg.context.id
        parent_msg = await self.uow.messages.get_by_wamid(ctx_wamid)
        if not parent_msg:
            parent_msg = await self._fuzzy_find_message(msg.from_, ctx_wamid)

        return parent_msg.id if parent_msg else None

    async def _update_campaign_on_reply(self, contact_id: uuid.UUID):
        """Mark campaign as replied when contact sends a message."""
        from src.models import CampaignDeliveryStatus

        latest_campaign_message = (
            await self.uow.messages.get_latest_campaign_message_for_contact(contact_id)
        )

        if not latest_campaign_message:
            return

        campaign_link = await self.uow.campaign_contacts.get_by_message_id(
            latest_campaign_message.id
        )

        if not campaign_link or campaign_link.status == CampaignDeliveryStatus.REPLIED:
            return

        campaign = await self.uow.campaigns.get_by_id(campaign_link.campaign_id)
        if not campaign:
            return

        # Update campaign counters
        campaign.replied_count += 1

        if campaign_link.status == CampaignDeliveryStatus.READ:
            campaign.read_count = max(0, campaign.read_count - 1)
        elif campaign_link.status == CampaignDeliveryStatus.DELIVERED:
            campaign.delivered_count = max(0, campaign.delivered_count - 1)
        elif campaign_link.status == CampaignDeliveryStatus.SENT:
            campaign.sent_count = max(0, campaign.sent_count - 1)

        self.uow.campaigns.add(campaign)
        campaign_link.status = CampaignDeliveryStatus.REPLIED
        self.uow.campaign_contacts.add(campaign_link)

    def _extract_message_body(self, msg: MetaMessage) -> Optional[str]:
        """Helper to extract text body from various message types."""
        if msg.type == "text":
            return msg.text.body
        elif msg.type == "interactive":
            interactive = msg.interactive
            if interactive.type == "button_reply":
                return interactive.button_reply.title
            elif interactive.type == "list_reply":
                return interactive.list_reply.title
        elif msg.type == "location":
            loc = msg.location
            return f"Location: {loc.name or ''} {loc.address or ''} ({loc.latitude}, {loc.longitude})".strip()
        elif msg.type == "contacts" and msg.contacts:
            c = msg.contacts[0]
            name = c.name.formatted_name if c.name else "Unknown"
            phone = c.phones[0].phone if c.phones else "No phone"
            return f"Contact: {name} ({phone})"
        elif hasattr(msg, msg.type):
            media_obj = getattr(msg, msg.type)
            if hasattr(media_obj, "caption"):
                return media_obj.caption
        return None

    async def _fuzzy_find_message(self, phone_number: str, target_wamid: str):
        """Attempt to find a message by fuzzy matching WAMID suffixes."""
        try:
            contact = await self.uow.contacts.get_or_create(phone_number)
            last_msgs = await self.uow.messages.get_chat_history(
                contact.id, limit=50, offset=0
            )

            target_clean = target_wamid.replace("wamid.", "")
            try:
                target_suffix = base64.b64decode(target_clean)[-8:]
            except Exception:
                return None

            for m in last_msgs:
                if not m.wamid:
                    continue
                try:
                    m_suffix = base64.b64decode(
                        m.wamid.replace("wamid.", ""))[-8:]
                    if m_suffix == target_suffix:
                        return m
                except Exception:
                    continue
            return None
        except Exception as e:
            logger.error(f"Fuzzy search error: {e}")
            return None
