"""WhatsApp Cloud API adapter — sends/receives messages via Meta WhatsApp Business API."""

import logging
import httpx
from app.core.config import settings
from app.services.channels.base import ChannelAdapter

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppAdapter(ChannelAdapter):
    """Adapter for WhatsApp Cloud API (Meta Business Platform)."""

    channel_name: str = "whatsapp"

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        media_url: str | None = None,
    ) -> dict | None:
        """Send a text message (optionally with media) to a WhatsApp number."""
        url = f"{GRAPH_API_BASE}/{settings.META_WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        if media_url:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "image",
                "image": {
                    "link": media_url,
                    "caption": text,
                },
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "text",
                "text": {"body": text},
            }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("WhatsApp message sent to %s", recipient_id)
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send WhatsApp message to %s: %s", recipient_id, e)
            return None

    async def send_media(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str,
    ) -> dict | None:
        """Send a standalone media message via WhatsApp Cloud API."""
        url = f"{GRAPH_API_BASE}/{settings.META_WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        wa_type = media_type if media_type in ("image", "document", "video", "audio") else "document"

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": wa_type,
            wa_type: {"link": media_url},
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("WhatsApp media (%s) sent to %s", wa_type, recipient_id)
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send WhatsApp media to %s: %s", recipient_id, e)
            return None

    async def send_document(
        self,
        recipient_id: str,
        document_url: str,
        filename: str = "document.pdf",
        caption: str = "",
    ) -> dict | None:
        """Send a document (PDF) via WhatsApp Cloud API with filename and caption."""
        url = f"{GRAPH_API_BASE}/{settings.META_WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        doc_payload = {"link": document_url, "filename": filename}
        if caption:
            doc_payload["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "document",
            "document": doc_payload,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                logger.info("WhatsApp document sent to %s: %s", recipient_id, filename)
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send WhatsApp document to %s: %s", recipient_id, e)
            return None

    async def send_interactive(
        self,
        recipient_id: str,
        text: str,
        options: list[dict],
    ) -> dict | None:
        """Send interactive message via WhatsApp Cloud API.

        - 3 or fewer options: reply buttons (type=button)
        - More than 3 options: list message (type=list)
        """
        if not options:
            return await self.send_message(recipient_id, text)

        url = f"{GRAPH_API_BASE}/{settings.META_WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        try:
            body_text = (text or "Selecione uma opção:")[:1024]

            if len(options) <= 3:
                # Reply buttons
                buttons = []
                for opt in options:
                    title = str(opt.get("title") or opt.get("label") or opt.get("id") or "")[:20]
                    buttons.append({
                        "type": "reply",
                        "reply": {
                            "id": str(opt.get("id") or opt.get("title") or opt.get("label") or "")[:256],
                            "title": title,
                        },
                    })
                payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient_id,
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": body_text},
                        "action": {"buttons": buttons},
                    },
                }
            else:
                # List message
                rows = []
                for opt in options[:10]:  # WA max 10 rows
                    title = str(opt.get("title") or opt.get("label") or opt.get("id") or "")[:24]
                    row = {
                        "id": str(opt.get("id") or opt.get("title") or opt.get("label") or "")[:200],
                        "title": title,
                    }
                    desc = opt.get("description", "")
                    if desc:
                        row["description"] = str(desc)[:72]
                    rows.append(row)
                payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient_id,
                    "type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {"text": text[:1024]},
                        "action": {
                            "button": "Selecionar",
                            "sections": [{"title": "Opções", "rows": rows}],
                        },
                    },
                }

            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("WhatsApp interactive sent to %s (%d options)", recipient_id, len(options))
                return data
        except httpx.HTTPError as e:
            logger.error("WhatsApp interactive failed for %s: %s — falling back to text", recipient_id, e)
            # Fallback to numbered text
            return await super().send_interactive(recipient_id, text, options)

    async def process_webhook(self, payload: dict) -> list[dict]:
        """Parse WhatsApp Cloud API webhook payload into normalized messages."""
        messages: list[dict] = []

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = value.get("contacts", [])
                contact_names = {c.get("wa_id", ""): c.get("profile", {}).get("name", "") for c in contacts}
                for msg in value.get("messages", []):
                    normalized = self._parse_message(msg)
                    if normalized:
                        sender = normalized.get("sender_id", "")
                        normalized["sender_name"] = contact_names.get(sender, "")
                        messages.append(normalized)

        return messages

    def _parse_message(self, msg: dict) -> dict | None:
        """Parse a single WhatsApp message into normalized format."""
        msg_type = msg.get("type", "")
        sender_id = msg.get("from", "")
        channel_message_id = msg.get("id", "")
        timestamp = msg.get("timestamp", "")

        if msg_type == "text":
            return {
                "sender_id": sender_id,
                "content": msg.get("text", {}).get("body", ""),
                "content_type": "text",
                "channel_message_id": channel_message_id,
                "timestamp": timestamp,
            }
        elif msg_type == "interactive":
            # Handle interactive replies (button_reply or list_reply)
            interactive = msg.get("interactive", {})
            interactive_type = interactive.get("type", "")
            if interactive_type == "button_reply":
                reply = interactive.get("button_reply", {})
                return {
                    "sender_id": sender_id,
                    "content": reply.get("title", ""),
                    "content_type": "text",
                    "channel_message_id": channel_message_id,
                    "timestamp": timestamp,
                    "interactive_reply_id": reply.get("id", ""),
                }
            elif interactive_type == "list_reply":
                reply = interactive.get("list_reply", {})
                return {
                    "sender_id": sender_id,
                    "content": reply.get("title", ""),
                    "content_type": "text",
                    "channel_message_id": channel_message_id,
                    "timestamp": timestamp,
                    "interactive_reply_id": reply.get("id", ""),
                }
            return None
        elif msg_type in ("image", "video", "audio", "document"):
            media_data = msg.get(msg_type, {})
            return {
                "sender_id": sender_id,
                "content": media_data.get("caption", ""),
                "content_type": msg_type,
                "media_url": media_data.get("id", ""),
                "media_type": media_data.get("mime_type", ""),
                "channel_message_id": channel_message_id,
                "timestamp": timestamp,
            }
        elif msg_type == "sticker":
            sticker_data = msg.get("sticker", {})
            return {
                "sender_id": sender_id,
                "content": "",
                "content_type": "sticker",
                "media_url": sticker_data.get("id", ""),
                "channel_message_id": channel_message_id,
                "timestamp": timestamp,
            }
        elif msg_type == "location":
            loc = msg.get("location", {})
            return {
                "sender_id": sender_id,
                "content": f"Location: {loc.get('latitude', '')},{loc.get('longitude', '')}",
                "content_type": "location",
                "channel_message_id": channel_message_id,
                "timestamp": timestamp,
            }
        else:
            logger.warning("Unsupported WhatsApp message type: %s", msg_type)
            return None
