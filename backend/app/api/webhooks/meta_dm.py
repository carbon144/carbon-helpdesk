"""Meta unified webhook — Instagram and Facebook Messenger."""
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
from app.services.channels.instagram_adapter import InstagramAdapter
from app.services.channels.facebook_adapter import FacebookAdapter
from app.api.ws import notify_chat_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
_instagram = InstagramAdapter()
_facebook = FacebookAdapter()


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[7:])


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
    if obj == "instagram":
        channel, messages = "instagram", await _instagram.process_webhook(payload)
    elif obj == "page":
        channel, messages = "facebook", await _facebook.process_webhook(payload)
    else:
        return {"status": "ok"}
    if messages:
        async with async_session() as db:
            for msg in messages:
                await _process_meta_message(db, msg, channel)
            await db.commit()
    return {"status": "ok"}


async def _process_meta_message(db: AsyncSession, msg: dict, channel: str):
    sender_id = msg["sender_id"]
    result = await db.execute(
        select(ChannelIdentity).where(ChannelIdentity.channel == channel, ChannelIdentity.channel_id == sender_id)
    )
    identity = result.scalar_one_or_none()
    if identity:
        customer_id = identity.customer_id
    else:
        label = "Instagram" if channel == "instagram" else "Facebook"
        customer = Customer(name=f"{label} {sender_id}")
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

    now = datetime.now(timezone.utc)
    db.add(ChatMessage(
        conversation_id=conversation.id, sender_type="contact", sender_id=customer_id,
        content_type=msg.get("content_type", "text"), content=msg.get("content", ""),
        channel_message_id=msg.get("channel_message_id"), created_at=now,
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
