"""Instagram Messaging adapter — sends/receives DMs via Meta Graph API."""

import logging
import httpx
from app.core.config import settings
from app.services.channels.base import ChannelAdapter

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class InstagramAdapter(ChannelAdapter):
    """Adapter for Instagram Direct Messages via Meta Graph API."""

    channel_name: str = "instagram"

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        media_url: str | None = None,
    ) -> dict | None:
        """Send a message to an Instagram user via Messenger Platform."""
        url = f"{GRAPH_API_BASE}/{settings.META_PAGE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_PAGE_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        payload: dict = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
        }

        if media_url:
            payload["message"] = {
                "attachment": {
                    "type": "image",
                    "payload": {"url": media_url},
                },
            }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("Instagram message sent to %s", recipient_id)
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send Instagram message to %s: %s", recipient_id, e)
            return None

    async def send_media(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str,
    ) -> dict | None:
        """Send a standalone media message to an Instagram user."""
        url = f"{GRAPH_API_BASE}/{settings.META_PAGE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_PAGE_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        # Instagram supports image, video, audio, file
        attachment_type = media_type if media_type in ("image", "video", "audio", "file") else "file"

        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": attachment_type,
                    "payload": {"url": media_url},
                },
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("Instagram media (%s) sent to %s", attachment_type, recipient_id)
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send Instagram media to %s: %s", recipient_id, e)
            return None

    async def process_webhook(self, payload: dict) -> list[dict]:
        """Parse Instagram messaging webhook payload into normalized messages.

        Expected payload shape (object == "instagram"):
        {
          "entry": [{
            "messaging": [{
              "sender": {"id": "..."},
              "recipient": {"id": "..."},
              "timestamp": 1234567890,
              "message": {
                "mid": "m_xxx",
                "text": "Hello"
              }
            }]
          }]
        }
        """
        messages: list[dict] = []

        for entry in payload.get("entry", []):
            for event in entry.get("messaging", []):
                msg_data = event.get("message", {})
                if not msg_data:
                    continue

                sender_id = event.get("sender", {}).get("id", "")
                timestamp = str(event.get("timestamp", ""))
                channel_message_id = msg_data.get("mid", "")

                # Check for attachments
                attachments = msg_data.get("attachments", [])
                if attachments:
                    att = attachments[0]
                    att_type = att.get("type", "image")
                    att_url = att.get("payload", {}).get("url", "")
                    messages.append({
                        "sender_id": sender_id,
                        "content": msg_data.get("text", ""),
                        "content_type": att_type,
                        "media_url": att_url,
                        "channel_message_id": channel_message_id,
                        "timestamp": timestamp,
                    })
                elif msg_data.get("text"):
                    messages.append({
                        "sender_id": sender_id,
                        "content": msg_data["text"],
                        "content_type": "text",
                        "channel_message_id": channel_message_id,
                        "timestamp": timestamp,
                    })

        return messages
