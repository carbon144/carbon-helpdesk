"""Facebook Messenger adapter — sends/receives messages via Meta Graph API."""

import logging
import httpx
from app.core.config import settings
from app.services.channels.base import ChannelAdapter

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class FacebookAdapter(ChannelAdapter):
    """Adapter for Facebook Messenger via Meta Graph API."""

    channel_name: str = "facebook"

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        media_url: str | None = None,
        **kwargs,
    ) -> dict | None:
        """Send a message to a Facebook user via Messenger."""
        url = f"{GRAPH_API_BASE}/me/messages"
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
                    "payload": {"url": media_url, "is_reusable": True},
                },
            }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                if resp.status_code != 200:
                    logger.error("Facebook send error %s: %s", resp.status_code, resp.text)
                resp.raise_for_status()
                data = resp.json()
                logger.info("Facebook message sent to %s", recipient_id)
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send Facebook message to %s: %s", recipient_id, e)
            return None

    async def send_media(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str,
        **kwargs,
    ) -> dict | None:
        """Send a standalone media message to a Facebook user."""
        url = f"{GRAPH_API_BASE}/me/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_PAGE_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        attachment_type = media_type if media_type in ("image", "video", "audio", "file") else "file"

        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": attachment_type,
                    "payload": {"url": media_url, "is_reusable": True},
                },
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("Facebook media (%s) sent to %s", attachment_type, recipient_id)
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send Facebook media to %s: %s", recipient_id, e)
            return None

    async def send_interactive(
        self,
        recipient_id: str,
        text: str,
        options: list[dict],
        **kwargs,
    ) -> dict | None:
        """Send interactive message with quick_replies via Facebook Messenger API.

        Facebook supports up to 13 quick replies, title max 20 chars.
        """
        if not options:
            return await self.send_message(recipient_id, text)

        url = f"{GRAPH_API_BASE}/me/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_PAGE_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        quick_replies = []
        for opt in options[:13]:  # FB max 13 quick replies
            title = str(opt.get("title") or opt.get("label") or opt.get("id") or "")[:20]
            quick_replies.append({
                "content_type": "text",
                "title": title,
                "payload": str(opt.get("id") or opt.get("title") or opt.get("label") or "")[:1000],
            })

        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "text": text,
                "quick_replies": quick_replies,
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("Facebook interactive sent to %s (%d options)", recipient_id, len(options))
                return data
        except httpx.HTTPError as e:
            logger.error("Facebook interactive failed for %s: %s — falling back to text", recipient_id, e)
            return await super().send_interactive(recipient_id, text, options)

    async def process_webhook(self, payload: dict) -> list[dict]:
        """Parse Facebook Messenger webhook payload into normalized messages."""
        messages: list[dict] = []

        for entry in payload.get("entry", []):
            # Debug: log entry keys to understand payload structure
            entry_keys = list(entry.keys())
            has_messaging = "messaging" in entry
            has_changes = "changes" in entry
            logger.info("[FB-WEBHOOK] entry keys=%s has_messaging=%s has_changes=%s", entry_keys, has_messaging, has_changes)
            if has_changes:
                for change in entry.get("changes", []):
                    logger.info("[FB-WEBHOOK] change field=%s value_keys=%s", change.get("field"), list(change.get("value", {}).keys())[:5])
            for event in entry.get("messaging", []):
                msg_data = event.get("message", {})
                if not msg_data:
                    continue

                # Skip echo messages (bot's own messages reflected back)
                if msg_data.get("is_echo"):
                    continue

                sender_id = event.get("sender", {}).get("id", "")
                timestamp = str(event.get("timestamp", ""))
                channel_message_id = msg_data.get("mid", "")

                # Check for quick_reply payload
                quick_reply = msg_data.get("quick_reply")

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
                    normalized = {
                        "sender_id": sender_id,
                        "content": msg_data["text"],
                        "content_type": "text",
                        "channel_message_id": channel_message_id,
                        "timestamp": timestamp,
                    }
                    if quick_reply:
                        normalized["interactive_reply_id"] = quick_reply.get("payload", "")
                    messages.append(normalized)

        return messages
