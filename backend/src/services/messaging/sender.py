import uuid

from loguru import logger
from src.clients.meta import MetaClient
from src.core.uow import UnitOfWork
from src.models import Contact, Message, MessageDirection, MessageStatus
from src.schemas import WhatsAppMessage
from src.services.notifications.service import NotificationService


class MessageSenderService:
    """
    Message sending service.

    IMPORTANT: This service manages transactions.
    Each public method commits its changes.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        meta_client: MetaClient,
        notifier: NotificationService,
    ):
        self.uow = uow
        self.meta_client = meta_client
        self.notifier = notifier

    async def send_manual_message(self, message: WhatsAppMessage):
        """
        Send a manual message (from API).
        This method manages its own transaction.
        """
        async with self.uow:
            contact = await self.uow.contacts.get_or_create(message.phone_number)

            template_id = None
            template_name = None

            if message.type == "template":
                template = await self.uow.templates.get_active_by_id(message.body)
                if template:
                    template_id = template.id
                    template_name = template.name
                else:
                    logger.error(f"Template {message.body} not found")
                    return

            await self._send_and_commit(
                contact=contact,
                message_type=message.type,
                body=message.body,
                template_id=template_id,
                template_name=template_name,
                is_campaign=False,
                reply_to_message_id=message.reply_to_message_id,
            )

    async def send_reaction(
        self, contact: Contact, message_id: uuid.UUID, emoji: str = ""
    ):
        """
        Send (or remove) a reaction to a specific message.
        To remove a reaction, pass an empty string as emoji.
        """
        # 1. Знаходимо повідомлення, на яке реагуємо
        target_message = await self.uow.messages.get_by_id(message_id)
        if not target_message or not target_message.wamid:
            logger.error(
                f"Cannot react: Message {message_id} not found or has no WAMID"
            )
            return

        waba_phone = await self.uow.waba.get_default_phone()

        # 2. Формуємо payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": contact.phone_number,
            "type": "reaction",
            "reaction": {"message_id": target_message.wamid, "emoji": emoji},
        }

        try:
            # 3. Відправляємо в Meta
            await self.meta_client.send_message(waba_phone.phone_number_id, payload)

            # 4. Оновлюємо статус в нашій базі (опціонально, щоб бачити свої реакції)
            # Примітка: Meta не повертає новий ID для реакції, це просто оновлення.
            target_message.reaction = emoji
            self.uow.session.add(target_message)
            await self.uow.commit()

            logger.info(f"Sent reaction '{emoji}' to {contact.phone_number}")

            await self.notifier.notify_message_reaction(
                message_id=target_message.id, reaction=emoji, phone=contact.phone_number
            )

        except Exception as e:
            logger.error(f"Failed to send reaction: {e}")
            raise

    async def send_file_to_client(
        self, phone: str, file_content: bytes, mime_type: str, caption: str = None
    ):
        waba_phone = await self.uow.waba.get_default_phone()

        media_id = await self.meta_client.upload_media(
            phone_number_id=waba_phone.phone_number_id,
            file=file_content,
            mime_type=mime_type,
        )

        msg_type = "document"
        if mime_type.startswith("image/"):
            msg_type = "image"
        elif mime_type.startswith("video/"):
            msg_type = "video"

        payload = self._build_payload(
            to_phone=phone,
            message_type=msg_type,
            body=media_id,
            template_name=None,
            caption=caption,
        )

        await self.meta_client.send_message(waba_phone.phone_number_id, payload)

    async def send_to_contact(
        self,
        contact: Contact,
        message_type: str,
        body: str,
        template_id: uuid.UUID | None = None,
        template_name: str | None = None,
        is_campaign: bool = False,
        reply_to_message_id: uuid.UUID | None = None,
    ) -> Message:
        """
        Send message to a contact.
        IMPORTANT: This method does NOT commit.
        The caller must commit the transaction.
        """
        waba_phone = await self.uow.waba.get_default_phone()
        if not waba_phone:
            raise ValueError("No WABA Phone numbers found in DB.")

        context_wamid = None
        if reply_to_message_id:
            parent_msg = await self.uow.messages.get_by_id(reply_to_message_id)
            if parent_msg:
                context_wamid = parent_msg.wamid
            else:
                logger.warning(f"Reply target message {reply_to_message_id} not found")

        # Create message entity
        message = await self.uow.messages.create(
            waba_phone_id=waba_phone.id,
            contact_id=contact.id,
            direction=MessageDirection.OUTBOUND,
            status=MessageStatus.PENDING,
            message_type=message_type,
            body=body if message_type == "text" else template_name,
            template_id=template_id,
            reply_to_message_id=reply_to_message_id,
        )

        await self.uow.session.flush()
        await self.uow.session.refresh(message)

        contact.updated_at = message.created_at
        contact.last_message_at = message.created_at
        contact.last_message_id = message.id
        self.uow.session.add(contact)

        if not is_campaign:
            await self.notifier.notify_new_message(message, phone=contact.phone_number)

            preview_body = (
                body
                if message_type == "text"
                else (template_name or f"Sent {message_type}")
            )

            await self.notifier._publish(
                {
                    "event": "contact_updated",
                    "data": {
                        "id": str(contact.id),
                        "phone_number": contact.phone_number,
                        "unread_count": contact.unread_count,
                        "last_message_at": contact.last_message_at.isoformat(),
                        "last_message_body": preview_body,
                        "last_message_type": message_type,
                        "last_message_status": "pending",
                        "last_message_direction": "outbound",
                    },
                    "timestamp": message.created_at.isoformat(),
                }
            )

        try:
            # Send to Meta
            payload = self._build_payload(
                to_phone=contact.phone_number,
                message_type=message_type,
                body=body,
                template_name=template_name,
                context_wamid=context_wamid,
            )

            result = await self.meta_client.send_message(
                waba_phone.phone_number_id, payload
            )
            wamid = result.get("messages", [{}])[0].get("id")

            if not wamid:
                raise Exception("No WAMID in Meta response")

            # Update message with WAMID
            message.wamid = wamid
            message.status = MessageStatus.SENT
            self.uow.session.add(message)

            logger.info(f"Message sent to {contact.phone_number}. WAMID: {wamid}")

            if not is_campaign:
                await self.notifier.notify_message_status(
                    message_id=message.id,
                    wamid=wamid,
                    status="sent",
                    phone=contact.phone_number,
                )

            return message

        except Exception as e:
            logger.error(f"Failed to send to {contact.phone_number}: {e}")
            message.status = MessageStatus.FAILED
            self.uow.session.add(message)
            raise

    async def _send_and_commit(
        self,
        contact: Contact,
        message_type: str,
        body: str,
        template_id: uuid.UUID | None,
        template_name: str | None,
        is_campaign: bool,
        reply_to_message_id: uuid.UUID | None = None,
    ):
        try:
            await self.send_to_contact(
                contact=contact,
                message_type=message_type,
                body=body,
                template_id=template_id,
                template_name=template_name,
                is_campaign=is_campaign,
                reply_to_message_id=reply_to_message_id,
            )
            await self.uow.commit()
        except Exception:
            await self.uow.commit()
            raise

    def _build_payload(
        self,
        to_phone: str,
        message_type: str,
        body: str,
        template_name: str | None,
        context_wamid: str | None = None,
        caption: str | None = None,
    ) -> dict:
        """Build WhatsApp API payload."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": message_type,
        }
        if context_wamid:
            payload["context"] = {"message_id": context_wamid}
        if message_type == "text":
            payload["text"] = {"body": body}
        elif message_type == "template":
            if not template_name:
                raise ValueError("Template name required")
            payload["template"] = {
                "name": template_name,
                "language": {"code": "en_US"},
            }
        elif message_type in ["image", "document", "audio", "video", "sticker"]:
            media_object = {"id": body}
            if caption and message_type in ["image", "document", "video"]:
                media_object["caption"] = caption

            if message_type == "document" and caption:
                media_object["filename"] = caption

            payload[message_type] = media_object
        return payload

