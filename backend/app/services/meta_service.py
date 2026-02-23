"""Meta Platform messaging service — WhatsApp, Instagram, Facebook Messenger."""
import hashlib
import hmac
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify X-Hub-Signature-256 from Meta webhook."""
    if not settings.META_APP_SECRET:
        return True  # Skip in dev if not configured
    expected = "sha256=" + hmac.new(
        settings.META_APP_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def send_message(platform: str, recipient_id: str, text: str) -> dict | None:
    """Send a text message via the appropriate Meta platform API."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if platform == "whatsapp":
                url = f"{GRAPH_API_BASE}/{settings.META_WHATSAPP_PHONE_ID}/messages"
                payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient_id,
                    "type": "text",
                    "text": {"body": text},
                }
                token = settings.META_WHATSAPP_TOKEN
            else:
                # Instagram and Facebook Messenger use the same Send API
                url = f"{GRAPH_API_BASE}/me/messages"
                payload = {
                    "recipient": {"id": recipient_id},
                    "message": {"text": text},
                }
                token = settings.META_PAGE_ACCESS_TOKEN

            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"Meta message sent via {platform} to {recipient_id}")
            return result
    except Exception as e:
        logger.error(f"Failed to send Meta message ({platform}): {e}")
        return None


async def get_user_profile(platform: str, user_id: str) -> dict | None:
    """Fetch basic profile (name) for a Meta user."""
    try:
        if platform == "whatsapp":
            return None  # WhatsApp profile comes in webhook payload

        token = settings.META_PAGE_ACCESS_TOKEN
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/{user_id}",
                params={"fields": "name", "access_token": token},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch Meta profile ({platform}, {user_id}): {e}")
        return None


def parse_webhook_entry(entry: dict, webhook_object: str = "") -> list[dict]:
    """Parse a single Meta webhook entry into normalized message dicts.

    Returns list of:
        {
            "platform": "whatsapp" | "instagram" | "facebook",
            "sender_id": str,
            "sender_name": str | None,
            "text": str,
            "message_id": str,
            "timestamp": str,
        }
    """
    messages = []

    # WhatsApp Cloud API format
    if "changes" in entry:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if value.get("messaging_product") == "whatsapp":
                contacts = {
                    c["wa_id"]: c.get("profile", {}).get("name", "")
                    for c in value.get("contacts", [])
                }
                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        continue  # Skip media/reactions for now
                    messages.append({
                        "platform": "whatsapp",
                        "sender_id": msg["from"],
                        "sender_name": contacts.get(msg["from"], ""),
                        "text": msg.get("text", {}).get("body", ""),
                        "message_id": msg["id"],
                        "timestamp": msg.get("timestamp", ""),
                    })

    # Instagram & Facebook Messenger format
    if "messaging" in entry:
        page_id = entry.get("id", "")
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id", "")
            if sender_id == page_id:
                continue
            msg = event.get("message", {})
            if not msg or msg.get("is_echo"):
                continue
            text = msg.get("text", "")
            if not text:
                continue
            platform = "instagram" if webhook_object == "instagram" else "facebook"
            messages.append({
                "platform": platform,
                "sender_id": sender_id,
                "sender_name": None,
                "text": text,
                "message_id": msg.get("mid", ""),
                "timestamp": str(event.get("timestamp", "")),
            })

    return messages
