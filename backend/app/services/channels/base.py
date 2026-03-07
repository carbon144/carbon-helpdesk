"""Abstract base class for channel adapters."""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ChannelAdapter(ABC):
    """Base class for all channel adapters (chat, WhatsApp, Instagram, etc.)."""

    channel_name: str

    @abstractmethod
    async def send_message(
        self,
        recipient_id: str,
        text: str,
        media_url: str | None = None,
        **kwargs,
    ) -> dict | None:
        pass

    @abstractmethod
    async def send_media(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str,
        **kwargs,
    ) -> dict | None:
        pass

    @abstractmethod
    async def process_webhook(self, payload: dict) -> list[dict]:
        pass

    async def send_interactive(
        self,
        recipient_id: str,
        text: str,
        options: list[dict],
        **kwargs,
    ) -> dict | None:
        """Send an interactive message with selectable options.

        Default implementation: falls back to a plain text message with numbered options.
        Subclasses can override for native interactive messages (buttons, lists, quick replies).
        """
        if not options:
            return await self.send_message(recipient_id, text, **kwargs)

        lines = [text, ""]
        for i, opt in enumerate(options, 1):
            title = opt.get("title") or opt.get("label") or f"Opcao {i}"
            desc = opt.get("description", "")
            line = f"{i}. {title}"
            if desc:
                line += f" - {desc}"
            lines.append(line)

        fallback_text = "\n".join(lines)
        logger.info(
            "%s: send_interactive fallback to text for %s (%d options)",
            self.channel_name, recipient_id, len(options),
        )
        return await self.send_message(recipient_id, fallback_text, **kwargs)
