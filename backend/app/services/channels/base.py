"""Abstract base class for channel adapters."""

from abc import ABC, abstractmethod


class ChannelAdapter(ABC):
    """Base class for all channel adapters (chat, WhatsApp, Instagram, etc.)."""

    channel_name: str

    @abstractmethod
    async def send_message(
        self,
        recipient_id: str,
        text: str,
        media_url: str | None = None,
    ) -> dict | None:
        pass

    @abstractmethod
    async def send_media(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str,
    ) -> dict | None:
        pass

    @abstractmethod
    async def process_webhook(self, payload: dict) -> list[dict]:
        pass
