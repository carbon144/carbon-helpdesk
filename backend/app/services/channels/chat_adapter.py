"""Chat adapter — sends messages via the chat WebSocket manager (no external API)."""

import logging
from app.services.channels.base import ChannelAdapter
from app.services.chat_ws_manager import chat_manager

logger = logging.getLogger(__name__)


class ChatAdapter(ChannelAdapter):
    """Adapter for the live chat widget channel.

    Sends messages directly via WebSocket instead of calling an external API.
    """

    channel_name: str = "chat"

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        media_url: str | None = None,
    ) -> dict | None:
        payload: dict = {
            "event": "new_message",
            "content": text,
            "content_type": "text",
            "sender_type": "system",
        }
        if media_url:
            payload["media_url"] = media_url
            payload["content_type"] = "media"

        await chat_manager.send_to_visitor(recipient_id, payload)
        return {"status": "sent", "recipient_id": recipient_id}

    async def send_media(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str,
    ) -> dict | None:
        payload = {
            "event": "new_message",
            "content": media_url,
            "content_type": media_type,
            "media_url": media_url,
            "sender_type": "system",
        }
        await chat_manager.send_to_visitor(recipient_id, payload)
        return {"status": "sent", "recipient_id": recipient_id, "media_type": media_type}

    async def process_webhook(self, payload: dict) -> list[dict]:
        """Chat channel does not use webhooks — messages arrive via WebSocket."""
        return []
