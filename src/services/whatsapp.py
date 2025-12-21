from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.clients.meta import MetaClient
from src.models import (
    Contact,
    Message,
    MessageDirection,
    MessageStatus,
    WabaPhoneNumber,
)
from src.schemas import WhatsAppMessage


class WhatsAppService:
    def __init__(self, session: AsyncSession, meta_client: MetaClient):
        self.session = session
        self.meta_client = meta_client

    async def send_outbound_message(self, message: WhatsAppMessage):
        # Find existing contact or create a new one if it doesn't exist
        stmt_contact = select(Contact).where(
            Contact.phone_number == message.phone_number
        )
        contact = (await self.session.exec(stmt_contact)).first()

        if not contact:
            contact = Contact(phone_number=message.phone_number)
            self.session.add(contact)
            await self.session.commit()
            await self.session.refresh(contact)

        stmt_phone = select(WabaPhoneNumber)
        waba_phone = (await self.session.exec(stmt_phone)).first()

        if not waba_phone:
            logger.error("No WABA Phone numbers found in DB.")
            return

        db_message = Message(
            waba_phone_id=waba_phone.id,
            contact_id=contact.id,
            direction=MessageDirection.OUTBOUND,
            status=MessageStatus.PENDING,
            body=message.body,
        )

        self.session.add(db_message)
        await self.session.commit()
        await self.session.refresh(db_message)

        try:
            # Construct specific payload structure depending on message type
            if message.type == "text":
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": message.phone_number,
                    "type": "text",
                    "text": {"body": message.body},
                }
            else:
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": message.phone_number,
                    "type": "template",
                    "template": {
                        "name": message.body,
                        "language": {"code": "en_US"},
                    },
                }

            result = await self.meta_client.send_message(
                waba_phone.phone_number_id, payload
            )

            # Safely extract WAMID using a defensive approach to handle potential API format changes
            wamid = result.get("messages", [{}])[0].get("id")

            if wamid:
                db_message.wamid = wamid
                db_message.status = MessageStatus.SENT
                self.session.add(db_message)
                await self.session.commit()
                logger.success(
                    f"Message sent to {message.phone_number}. WAMID: {wamid}"
                )

        except Exception as e:
            logger.exception(f"Failed to send message to {message.phone_number}")
            db_message.status = MessageStatus.FAILED
            self.session.add(db_message)
            await self.session.commit()

    async def process_webhook(self, payload: dict):
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                if "statuses" in value:
                    await self._handle_statuses(value["statuses"])

                if "messages" in value:
                    await self._handle_incoming_messages(value)

    def _get_status_weight(self, status: MessageStatus) -> int:
        weights = {
            MessageStatus.PENDING: 0,
            MessageStatus.SENT: 1,
            MessageStatus.DELIVERED: 2,
            MessageStatus.READ: 3,
            MessageStatus.FAILED: 4,
        }
        return weights.get(status, -1)

    async def _handle_statuses(self, statuses: list):
        status_map = {
            "sent": MessageStatus.SENT,
            "delivered": MessageStatus.DELIVERED,
            "read": MessageStatus.READ,
            "failed": MessageStatus.FAILED,
        }

        for status in statuses:
            wamid = status.get("id")
            new_status_str = status.get("status")
            new_status = status_map.get(new_status_str)

            if wamid and new_status:
                stmt = select(Message).where(Message.wamid == wamid)
                db_message = (await self.session.exec(stmt)).first()

                if db_message:
                    current_weight = self._get_status_weight(db_message.status)
                    new_weight = self._get_status_weight(new_status)

                    if new_weight > current_weight:
                        old_status = db_message.status
                        db_message.status = new_status
                        self.session.add(db_message)
                        logger.info(
                            f"Updated status for {wamid}: {old_status} -> {new_status}"
                        )
                    else:
                        logger.debug(
                            f"Ignored outdated status {new_status} for {wamid} "
                            f"(current: {db_message.status})"
                        )

        await self.session.commit()

    async def _handle_incoming_messages(self, value: dict):
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id")

        stmt_phone = select(WabaPhoneNumber).where(
            WabaPhoneNumber.phone_number_id == phone_number_id
        )
        waba_phone = (await self.session.exec(stmt_phone)).first()

        if not waba_phone:
            logger.warning(f"Webhook for unknown phone ID: {phone_number_id}")
            return

        for msg in value.get("messages", []):
            wamid = msg.get("id")
            from_phone = msg.get("from")

            stmt_dup = select(Message).where(Message.wamid == wamid)
            if (await self.session.exec(stmt_dup)).first():
                logger.info(f"Message {wamid} already processed")
                continue

            stmt_contact = select(Contact).where(Contact.phone_number == from_phone)
            contact = (await self.session.exec(stmt_contact)).first()
            if not contact:
                contact = Contact(
                    phone_number=from_phone,
                    name=msg.get("profile", {}).get("name"),
                )
                self.session.add(contact)
                await self.session.commit()
                await self.session.refresh(contact)

            parsed_data = self._parse_message_data(msg)

            new_msg = Message(
                waba_phone_id=waba_phone.id,
                contact_id=contact.id,
                direction=MessageDirection.INBOUND,
                status=MessageStatus.RECEIVED,
                wamid=wamid,
                message_type=parsed_data["type"],
                body=parsed_data["body"],
                media_id=parsed_data["media_id"],
                caption=parsed_data["caption"],
            )
            self.session.add(new_msg)
            logger.info(f"Saved {parsed_data['type']} message from {from_phone}")

        await self.session.commit()

    def _parse_message_data(self, msg: dict) -> dict:
        """Return structures: {type, body, media_id, caption}"""
        msg_type = msg.get("type")
        result = {"type": msg_type, "body": "", "media_id": None, "caption": None}

        if msg_type == "text":
            result["body"] = msg.get("text", {}).get("body", "")

        elif msg_type == "image":
            media = msg.get("image", {})
            result["media_id"] = media.get("id")
            result["caption"] = media.get("caption")
            result["body"] = "[Фото]"

        elif msg_type == "video":
            media = msg.get("video", {})
            result["media_id"] = media.get("id")
            result["caption"] = media.get("caption")
            result["body"] = "[Відео]"

        elif msg_type == "document":
            media = msg.get("document", {})
            result["media_id"] = media.get("id")
            result["caption"] = media.get("caption")
            filename = media.get("filename", "file")
            result["body"] = f"[Документ: {filename}]"

        elif msg_type == "audio":
            media = msg.get("audio", {})
            result["media_id"] = media.get("id")
            result["body"] = "[Аудіо]"

        elif msg_type == "voice":
            media = msg.get("voice", {})
            result["media_id"] = media.get("id")
            result["body"] = "[Голосове]"

        elif msg_type == "sticker":
            media = msg.get("sticker", {})
            result["media_id"] = media.get("id")
            result["body"] = "[Стікер]"

        else:
            result["body"] = f"[{msg_type} message]"

        if result["caption"]:
            result["body"] += f": {result['caption']}"

        return result
