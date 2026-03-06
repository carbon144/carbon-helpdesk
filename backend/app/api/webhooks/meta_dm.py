"""Meta unified webhook — Instagram and Facebook Messenger."""
import hashlib
import hmac
import logging
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Request, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import async_session
from app.models.customer import Customer
from app.models.channel_identity import ChannelIdentity
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage
from app.services.channels.instagram_adapter import InstagramAdapter
from app.services.channels.facebook_adapter import FacebookAdapter
from app.services.channels.whatsapp_adapter import WhatsAppAdapter
from app.api.ws import notify_chat_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
_instagram = InstagramAdapter()
_facebook = FacebookAdapter()
_whatsapp = WhatsAppAdapter()

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = hmac.HMAC(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[7:])


async def _fetch_ig_profile(ig_scoped_id: str) -> dict | None:
    """Fetch Instagram username and profile pic from a scoped user ID."""
    token = settings.META_PAGE_ACCESS_TOKEN
    if not token:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/{ig_scoped_id}",
                params={"fields": "name,username,profile_pic", "access_token": token},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "name": data.get("username") or data.get("name"),
                    "avatar_url": data.get("profile_pic"),
                }
    except Exception as e:
        logger.warning("Failed to fetch IG profile for %s: %s", ig_scoped_id, e)
    return None


async def _fetch_fb_profile(fb_scoped_id: str) -> dict | None:
    """Fetch Facebook user name and profile pic from a scoped user ID."""
    token = settings.META_PAGE_ACCESS_TOKEN
    if not token:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/{fb_scoped_id}",
                params={"fields": "name,profile_pic", "access_token": token},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "name": data.get("name"),
                    "avatar_url": data.get("profile_pic"),
                }
    except Exception as e:
        logger.warning("Failed to fetch FB profile for %s: %s", fb_scoped_id, e)
    return None


@router.get("/meta-dm")
async def meta_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(403, "Verification failed")


@router.post("/meta-dm")
async def meta_webhook(request: Request):
    body = await request.body()
    if settings.META_APP_SECRET:
        sig = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_signature(body, sig, settings.META_APP_SECRET):
            raise HTTPException(403, "Invalid signature")
    payload = await request.json()
    obj = payload.get("object", "")
    logger.info("Webhook received: object=%s", obj)
    if obj == "whatsapp_business_account":
        channel, messages = "whatsapp", await _whatsapp.process_webhook(payload)
    elif obj == "instagram":
        channel, messages = "instagram", await _instagram.process_webhook(payload)
    elif obj == "page":
        channel, messages = "facebook", await _facebook.process_webhook(payload)
    else:
        logger.info("Unknown webhook object: %s", obj)
        return {"status": "ok"}
    logger.info("Parsed %d messages for channel=%s", len(messages), channel)
    if messages:
        async with async_session() as db:
            for msg in messages:
                logger.info("Processing msg from sender=%s content=%s", msg.get("sender_id", "?"), msg.get("content", "")[:50])
                if channel == "whatsapp":
                    await _process_whatsapp_message(db, msg)
                else:
                    await _process_meta_message(db, msg, channel)
            await db.commit()
    return {"status": "ok"}


async def _process_whatsapp_message(db: AsyncSession, msg: dict):
    """Process a WhatsApp message — uses phone number as channel_id."""
    channel = "whatsapp"
    sender_id = msg["sender_id"]  # phone number e.g. "5511999999999"

    result = await db.execute(
        select(ChannelIdentity).where(ChannelIdentity.channel == channel, ChannelIdentity.channel_id == sender_id)
    )
    identity = result.scalars().first()
    if identity:
        customer_id = identity.customer_id
    else:
        name = msg.get("sender_name") or f"WhatsApp +{sender_id}"
        customer = Customer(name=name, phone=sender_id)
        db.add(customer)
        await db.flush()
        customer_id = customer.id
        db.add(ChannelIdentity(customer_id=customer_id, channel=channel, channel_id=sender_id))

    result = await db.execute(
        select(Conversation).where(Conversation.customer_id == customer_id, Conversation.channel == channel, Conversation.status == "open")
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(customer_id=customer_id, channel=channel, status="open")
        db.add(conversation)
        await db.flush()

    # Dedup by channel_message_id
    mid = msg.get("channel_message_id")
    if mid:
        existing_msg = await db.execute(
            select(ChatMessage).where(ChatMessage.channel_message_id == mid)
        )
        if existing_msg.scalars().first():
            return

    now = datetime.now(timezone.utc)
    db.add(ChatMessage(
        conversation_id=conversation.id, sender_type="contact", sender_id=customer_id,
        content_type=msg.get("content_type", "text"), content=msg.get("content", ""),
        channel_message_id=mid, created_at=now,
    ))
    conversation.last_message_at = now

    await notify_chat_event({
        "event": "new_message", "channel": channel,
        "conversation_id": str(conversation.id),
        "sender_type": "contact", "sender_id": sender_id,
        "content": msg.get("content", ""),
    })

    content = msg.get("content", "")
    if content:
        from app.services.message_pipeline import process_incoming_message
        cust = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
        if cust:
            pr = await process_incoming_message(db, conversation, cust, content)
            if pr.get("bot_messages"):
                from app.services.channels.dispatcher import dispatcher
                for bot_msg in pr["bot_messages"]:
                    await dispatcher.send(channel, sender_id, bot_msg)


async def _process_meta_message(db: AsyncSession, msg: dict, channel: str):
    sender_id = msg["sender_id"]
    # Ignore messages sent by our own page/IG account
    own_ids = {settings.META_PAGE_ID, settings.META_INSTAGRAM_ACCOUNT_ID}
    if sender_id in own_ids:
        return
    result = await db.execute(
        select(ChannelIdentity).where(ChannelIdentity.channel == channel, ChannelIdentity.channel_id == sender_id)
    )
    identity = result.scalars().first()
    if identity:
        customer_id = identity.customer_id
        # Update name/avatar if still generic
        cust_res = await db.execute(select(Customer).where(Customer.id == customer_id))
        existing = cust_res.scalars().first()
        if existing and existing.name and existing.name.startswith(("Instagram ", "Facebook ")):
            profile = await _fetch_ig_profile(sender_id) if channel == "instagram" else await _fetch_fb_profile(sender_id)
            if profile:
                if profile.get("name"):
                    existing.name = f"@{profile['name']}" if channel == "instagram" else profile["name"]
                if profile.get("avatar_url"):
                    existing.avatar_url = profile["avatar_url"]
        elif existing and not existing.avatar_url:
            profile = await _fetch_ig_profile(sender_id) if channel == "instagram" else await _fetch_fb_profile(sender_id)
            if profile and profile.get("avatar_url"):
                existing.avatar_url = profile["avatar_url"]
    else:
        profile = await _fetch_ig_profile(sender_id) if channel == "instagram" else await _fetch_fb_profile(sender_id)
        if profile and profile.get("name"):
            name = f"@{profile['name']}" if channel == "instagram" else profile["name"]
        else:
            name = f"Instagram {sender_id[:8]}" if channel == "instagram" else f"Facebook {sender_id[:8]}"
        avatar_url = profile.get("avatar_url") if profile else None
        customer = Customer(name=name, avatar_url=avatar_url)
        db.add(customer)
        await db.flush()
        customer_id = customer.id
        db.add(ChannelIdentity(customer_id=customer_id, channel=channel, channel_id=sender_id))

    result = await db.execute(
        select(Conversation).where(Conversation.customer_id == customer_id, Conversation.channel == channel, Conversation.status == "open")
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(customer_id=customer_id, channel=channel, status="open")
        db.add(conversation)
        await db.flush()

    # Dedup by channel_message_id
    mid = msg.get("channel_message_id")
    if mid:
        existing_msg = await db.execute(
            select(ChatMessage).where(ChatMessage.channel_message_id == mid)
        )
        if existing_msg.scalars().first():
            return  # already processed

    now = datetime.now(timezone.utc)
    db.add(ChatMessage(
        conversation_id=conversation.id, sender_type="contact", sender_id=customer_id,
        content_type=msg.get("content_type", "text"), content=msg.get("content", ""),
        channel_message_id=mid, created_at=now,
    ))
    conversation.last_message_at = now

    await notify_chat_event({
        "event": "new_message", "channel": channel,
        "conversation_id": str(conversation.id),
        "sender_type": "contact", "sender_id": sender_id,
        "content": msg.get("content", ""),
    })

    content = msg.get("content", "")
    if content:
        from app.services.message_pipeline import process_incoming_message
        cust = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
        if cust:
            pr = await process_incoming_message(db, conversation, cust, content)
            if pr.get("bot_messages"):
                from app.services.channels.dispatcher import dispatcher
                for bot_msg in pr["bot_messages"]:
                    await dispatcher.send(channel, sender_id, bot_msg)
