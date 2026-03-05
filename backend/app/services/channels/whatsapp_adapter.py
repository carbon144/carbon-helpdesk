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
            # Send as image with caption
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
        """Send a standalone media message via WhatsApp Cloud API.

        Supported media_type values: image, document, video, audio.
        """
        url = f"{GRAPH_API_BASE}/{settings.META_WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        # Map generic types to WhatsApp API types
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

    async def process_webhook(self, payload: dict) -> list[dict]:
        """Parse WhatsApp Cloud API webhook payload into normalized messages.

        Expected payload shape:
        {
          "entry": [{
            "changes": [{
              "value": {
                "messages": [{
                  "from": "5511999...",
                  "id": "wamid.xxx",
                  "timestamp": "1234567890",
                  "type": "text",
                  "text": {"body": "Hello"}
                }]
              }
            }]
          }]
        }
        """
        messages: list[dict] = []

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    normalized = self._parse_message(msg)
                    if normalized:
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
        elif msg_type in ("image", "video", "audio", "document"):
            media_data = msg.get(msg_type, {})
            return {
                "sender_id": sender_id,
                "content": media_data.get("caption", ""),
                "content_type": msg_type,
                "media_url": media_data.get("id", ""),  # WhatsApp uses media IDs
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
