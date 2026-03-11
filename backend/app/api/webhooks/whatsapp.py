"""WhatsApp webhook endpoints — verification + incoming messages."""
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import async_session
from app.models.customer import Customer
from app.models.channel_identity import ChannelIdentity
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage
from app.services.channels.whatsapp_adapter import WhatsAppAdapter
from app.api.ws import notify_chat_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
_adapter = WhatsAppAdapter()

# Debounce: track recently processed sender+conversation to prevent duplicate greetings
_recent_processed: dict[str, float] = {}  # key: "sender_id:conv_id" → timestamp
_DEBOUNCE_SECONDS = 1.0


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = hmac.HMAC(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[7:])


@router.get("/whatsapp")
async def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(403, "Verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    body = await request.body()
    if settings.META_APP_SECRET:
        sig = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_signature(body, sig, settings.META_APP_SECRET):
            raise HTTPException(403, "Invalid signature")
    else:
        logger.warning("META_APP_SECRET not set — webhook signature verification DISABLED")
    payload = await request.json()
    messages = await _adapter.process_webhook(payload)
    if messages:
        async with async_session() as db:
            for msg in messages:
                await _process_message(db, msg, "whatsapp")
            await db.commit()
    return {"status": "ok"}


async def _process_message(db: AsyncSession, msg: dict, channel: str):
    sender_id = msg["sender_id"]
    result = await db.execute(
        select(ChannelIdentity).where(ChannelIdentity.channel == channel, ChannelIdentity.channel_id == sender_id)
    )
    identity = result.scalar_one_or_none()
    if identity:
        customer_id = identity.customer_id
    else:
        customer = Customer(name=f"WhatsApp {sender_id}", phone=sender_id)
        db.add(customer)
        await db.flush()
        customer_id = customer.id
        db.add(ChannelIdentity(customer_id=customer_id, channel=channel, channel_id=sender_id))

    phone_number_id = msg.get("phone_number_id", "")

    result = await db.execute(
        select(Conversation).where(Conversation.customer_id == customer_id, Conversation.channel == channel, Conversation.status == "open")
        .order_by(Conversation.last_message_at.desc().nullslast())
    )
    conversation = result.scalars().first()
    if not conversation:
        conversation = Conversation(customer_id=customer_id, channel=channel, status="open",
                                     metadata_={"phone_number_id": phone_number_id} if phone_number_id else None)
        db.add(conversation)
        await db.flush()
    elif phone_number_id:
        meta = conversation.metadata_ or {}
        if meta.get("phone_number_id") != phone_number_id:
            meta["phone_number_id"] = phone_number_id
            conversation.metadata_ = meta
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
    chat_msg = ChatMessage(
        conversation_id=conversation.id, sender_type="contact", sender_id=customer_id,
        content_type=msg.get("content_type", "text"), content=msg.get("content", ""),
        channel_message_id=mid, created_at=now,
    )
    db.add(chat_msg)
    conversation.last_message_at = now

    await notify_chat_event({
        "event": "new_message", "channel": channel,
        "conversation_id": str(conversation.id),
        "sender_type": "contact", "sender_id": sender_id,
        "content": msg.get("content", ""),
    })

    wa_kwargs = {"phone_number_id": phone_number_id} if phone_number_id else {}

    # Debounce: skip pipeline if same sender processed within 1 second
    # (prevents duplicate greetings from burst messages)
    import time
    _debounce_key = f"{sender_id}:{conversation.id}"
    _now_ts = time.time()
    _last_ts = _recent_processed.get(_debounce_key, 0)
    if _now_ts - _last_ts < _DEBOUNCE_SECONDS:
        logger.debug("[DEBOUNCE] Skipping pipeline for %s (%.1fs since last)", _debounce_key, _now_ts - _last_ts)
        return
    _recent_processed[_debounce_key] = _now_ts
    # Cleanup old entries (keep last 100)
    if len(_recent_processed) > 200:
        _sorted = sorted(_recent_processed.items(), key=lambda x: x[1])
        _recent_processed.clear()
        _recent_processed.update(_sorted[-100:])

    content = msg.get("content", "")
    content_type = msg.get("content_type", "text")

    # Handle media messages (image, video, audio, sticker) — even without caption
    if not content and content_type in ("image", "video", "audio", "sticker", "document"):
        from app.services.message_pipeline import process_incoming_message
        cust_result = await db.execute(select(Customer).where(Customer.id == customer_id))
        customer = cust_result.scalar_one_or_none()
        if customer:
            pipeline_result = await process_incoming_message(
                db, conversation, customer, "", content_type=content_type,
            )
            if pipeline_result.get("bot_messages"):
                from app.services.channels.dispatcher import dispatcher
                for bot_msg in pipeline_result["bot_messages"]:
                    await dispatcher.send(channel, sender_id, bot_msg, **wa_kwargs)
            for im in pipeline_result.get("interactive_messages", []):
                if im.get("type") == "menu":
                    from app.services.channels.dispatcher import dispatcher
                    await dispatcher.send_interactive(
                        channel, sender_id, im["content"], im["options"], **wa_kwargs,
                    )

    elif content:
        from app.services.message_pipeline import process_incoming_message
        cust_result = await db.execute(select(Customer).where(Customer.id == customer_id))
        customer = cust_result.scalar_one_or_none()
        if customer:
            pipeline_result = await process_incoming_message(db, conversation, customer, content)
            if pipeline_result.get("bot_messages"):
                from app.services.channels.dispatcher import dispatcher
                for bot_msg in pipeline_result["bot_messages"]:
                    await dispatcher.send(channel, sender_id, bot_msg, **wa_kwargs)
            for im in pipeline_result.get("interactive_messages", []):
                if im.get("type") == "menu":
                    from app.services.channels.dispatcher import dispatcher
                    await dispatcher.send_interactive(
                        channel, sender_id, im["content"], im["options"], **wa_kwargs,
                    )
