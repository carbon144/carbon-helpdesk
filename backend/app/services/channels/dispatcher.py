"""Channel dispatcher — routes messages to the correct channel adapter."""

import logging
from app.services.channels.base import ChannelAdapter

logger = logging.getLogger(__name__)


class ChannelDispatcher:
    """Routes outbound messages to the appropriate channel adapter."""

    def __init__(self):
        self.adapters: dict[str, ChannelAdapter] = {}

    def register(self, adapter: ChannelAdapter):
        self.adapters[adapter.channel_name] = adapter
        logger.info("Registered channel adapter: %s", adapter.channel_name)

    async def send(
        self,
        channel: str,
        recipient_id: str,
        text: str,
        media_url: str | None = None,
        **kwargs,
    ) -> dict | None:
        adapter = self.adapters.get(channel)
        if adapter:
            return await adapter.send_message(recipient_id, text, media_url, **kwargs)
        logger.warning("No adapter registered for channel: %s", channel)
        return None

    async def send_media(
        self,
        channel: str,
        recipient_id: str,
        media_url: str,
        media_type: str,
        **kwargs,
    ) -> dict | None:
        adapter = self.adapters.get(channel)
        if adapter:
            return await adapter.send_media(recipient_id, media_url, media_type, **kwargs)
        logger.warning("No adapter registered for channel: %s", channel)
        return None

    async def send_document(
        self,
        channel: str,
        recipient_id: str,
        document_url: str,
        filename: str = "document.pdf",
        caption: str = "",
        **kwargs,
    ) -> dict | None:
        adapter = self.adapters.get(channel)
        if adapter and hasattr(adapter, "send_document"):
            return await adapter.send_document(recipient_id, document_url, filename, caption, **kwargs)
        # Fallback: send as regular media
        if adapter:
            return await adapter.send_media(recipient_id, document_url, "document", **kwargs)
        logger.warning("No adapter registered for channel: %s", channel)
        return None

    async def send_interactive(
        self,
        channel: str,
        recipient_id: str,
        text: str,
        options: list[dict],
        **kwargs,
    ) -> dict | None:
        adapter = self.adapters.get(channel)
        if adapter:
            return await adapter.send_interactive(recipient_id, text, options, **kwargs)
        logger.warning("No adapter registered for channel: %s", channel)
        return None

    async def process_webhook(self, channel: str, payload: dict) -> list[dict]:
        adapter = self.adapters.get(channel)
        if adapter:
            return await adapter.process_webhook(payload)
        logger.warning("No adapter registered for channel: %s", channel)
        return []


# Singleton instance — register adapters at startup
dispatcher = ChannelDispatcher()
