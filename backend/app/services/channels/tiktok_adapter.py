"""TikTok Business API adapter — sends/receives messages via TikTok API."""

import logging
import httpx
from app.core.config import settings
from app.services.channels.base import ChannelAdapter

logger = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://business-api.tiktok.com/open_api/v1.3"


class TikTokAdapter(ChannelAdapter):
    """Adapter for TikTok Business messaging API."""

    channel_name: str = "tiktok"

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        media_url: str | None = None,
    ) -> dict | None:
        """Send a text message to a TikTok user via Business API."""
        url = f"{TIKTOK_API_BASE}/im/send_message/"
        headers = {
            "Access-Token": settings.TIKTOK_ACCESS_TOKEN,
            "Content-Type": "application/json",
        }

        payload: dict = {
            "conversation_id": recipient_id,
            "message_type": "text",
            "text": {"text": text},
        }

        if media_url:
            payload["message_type"] = "image"
            payload["image"] = {"url": media_url}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("TikTok message sent to %s", recipient_id)
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send TikTok message to %s: %s", recipient_id, e)
            return None

    async def send_media(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str,
    ) -> dict | None:
        """Send a media message to a TikTok user."""
        url = f"{TIKTOK_API_BASE}/im/send_message/"
        headers = {
            "Access-Token": settings.TIKTOK_ACCESS_TOKEN,
            "Content-Type": "application/json",
        }

        # TikTok supports image and video
        tt_type = media_type if media_type in ("image", "video") else "image"

        payload = {
            "conversation_id": recipient_id,
            "message_type": tt_type,
            tt_type: {"url": media_url},
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("TikTok media (%s) sent to %s", tt_type, recipient_id)
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send TikTok media to %s: %s", recipient_id, e)
            return None

    async def process_webhook(self, payload: dict) -> list[dict]:
        """Parse TikTok webhook payload into normalized messages.

        Expected payload shape:
        {
          "event": "receive_message",
          "content": {
            "conversation_id": "...",
            "sender_id": "...",
            "message_id": "...",
            "message_type": "text",
            "text": {"text": "Hello"},
            "create_time": 1234567890
          }
        }
        """
        messages: list[dict] = []

        event = payload.get("event", "")
        if event != "receive_message":
            return messages

        content = payload.get("content", {})
        if not content:
            return messages

        sender_id = content.get("sender_id", "")
        channel_message_id = content.get("message_id", "")
        timestamp = str(content.get("create_time", ""))
        msg_type = content.get("message_type", "text")

        if msg_type == "text":
            text_content = content.get("text", {}).get("text", "")
            messages.append({
                "sender_id": sender_id,
                "content": text_content,
                "content_type": "text",
                "channel_message_id": channel_message_id,
                "timestamp": timestamp,
            })
        elif msg_type in ("image", "video"):
            media_data = content.get(msg_type, {})
            messages.append({
                "sender_id": sender_id,
                "content": "",
                "content_type": msg_type,
                "media_url": media_data.get("url", ""),
                "channel_message_id": channel_message_id,
                "timestamp": timestamp,
            })
        else:
            logger.warning("Unsupported TikTok message type: %s", msg_type)

        return messages
