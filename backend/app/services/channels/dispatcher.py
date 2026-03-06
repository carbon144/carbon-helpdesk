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
    ) -> dict | None:
        adapter = self.adapters.get(channel)
        if adapter:
            return await adapter.send_message(recipient_id, text, media_url)
        logger.warning("No adapter registered for channel: %s", channel)
        return None

    async def send_media(
        self,
        channel: str,
        recipient_id: str,
        media_url: str,
        media_type: str,
    ) -> dict | None:
        adapter = self.adapters.get(channel)
        if adapter:
            return await adapter.send_media(recipient_id, media_url, media_type)
        logger.warning("No adapter registered for channel: %s", channel)
        return None

    async def send_interactive(
        self,
        channel: str,
        recipient_id: str,
        text: str,
        options: list[dict],
    ) -> dict | None:
        adapter = self.adapters.get(channel)
        if adapter:
            return await adapter.send_interactive(recipient_id, text, options)
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
