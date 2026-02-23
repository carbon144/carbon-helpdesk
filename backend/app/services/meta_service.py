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


def parse_comment_events(entry: dict, webhook_object: str = "") -> list[dict]:
    """Parse comment events from a Meta webhook entry.

    Returns list of:
        {
            "platform": "instagram" | "facebook",
            "comment_id": str,
            "post_id": str,
            "author_id": str,
            "author_name": str,
            "text": str,
            "parent_comment_id": str | None,
            "timestamp": str,
        }
    """
    comments = []

    # Instagram comment webhooks
    if webhook_object == "instagram" and "changes" in entry:
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            value = change.get("value", {})
            # Instagram sends comment data in the value
            comment_id = value.get("id", "")
            text = value.get("text", "")
            if not comment_id or not text:
                continue
            comments.append({
                "platform": "instagram",
                "comment_id": comment_id,
                "post_id": value.get("media", {}).get("id", ""),
                "author_id": value.get("from", {}).get("id", ""),
                "author_name": value.get("from", {}).get("username", ""),
                "text": text,
                "parent_comment_id": value.get("parent_id"),
                "timestamp": str(value.get("timestamp", "")),
            })

    # Facebook page feed comments
    if webhook_object == "page" and "changes" in entry:
        for change in entry.get("changes", []):
            if change.get("field") != "feed":
                continue
            value = change.get("value", {})
            if value.get("item") != "comment":
                continue
            comment_id = value.get("comment_id", "")
            text = value.get("message", "")
            if not comment_id or not text:
                continue
            # Ignore own page comments
            page_id = entry.get("id", "")
            sender_id = value.get("from", {}).get("id", "")
            if sender_id == page_id:
                continue
            comments.append({
                "platform": "facebook",
                "comment_id": comment_id,
                "post_id": value.get("post_id", ""),
                "author_id": sender_id,
                "author_name": value.get("from", {}).get("name", ""),
                "text": text,
                "parent_comment_id": value.get("parent_id"),
                "timestamp": str(value.get("created_time", "")),
            })

    return comments


async def reply_to_comment(platform: str, comment_id: str, text: str) -> dict | None:
    """Reply to a comment on Instagram or Facebook."""
    try:
        if platform == "instagram":
            url = f"{GRAPH_API_BASE}/{comment_id}/replies"
            token = settings.META_PAGE_ACCESS_TOKEN
            payload = {"message": text}
        else:
            url = f"{GRAPH_API_BASE}/{comment_id}/comments"
            token = settings.META_PAGE_ACCESS_TOKEN
            payload = {"message": text}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"Replied to {platform} comment {comment_id}")
            return result
    except Exception as e:
        logger.error(f"Failed to reply to {platform} comment {comment_id}: {e}")
        return None


async def hide_comment(platform: str, comment_id: str) -> bool:
    """Hide/delete a comment on Instagram or Facebook.

    Instagram: uses hide=true (reversible)
    Facebook: deletes the comment (irreversible)
    """
    try:
        token = settings.META_PAGE_ACCESS_TOKEN
        async with httpx.AsyncClient(timeout=30) as client:
            if platform == "instagram":
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{comment_id}",
                    json={"hide": True},
                    headers={"Authorization": f"Bearer {token}"},
                )
            else:
                resp = await client.delete(
                    f"{GRAPH_API_BASE}/{comment_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
            resp.raise_for_status()
            logger.info(f"Hidden/deleted {platform} comment {comment_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to hide {platform} comment {comment_id}: {e}")
        return False
