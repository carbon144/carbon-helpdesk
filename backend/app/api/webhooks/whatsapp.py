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
from app.services.chat_ws_manager import chat_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
_adapter = WhatsAppAdapter()


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
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

    result = await db.execute(
        select(Conversation).where(Conversation.customer_id == customer_id, Conversation.channel == channel, Conversation.status == "open")
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(customer_id=customer_id, channel=channel, status="open")
        db.add(conversation)
        await db.flush()

    now = datetime.now(timezone.utc)
    chat_msg = ChatMessage(
        conversation_id=conversation.id, sender_type="contact", sender_id=customer_id,
        content_type=msg.get("content_type", "text"), content=msg.get("content", ""),
        channel_message_id=msg.get("channel_message_id"), created_at=now,
    )
    db.add(chat_msg)
    conversation.last_message_at = now

    await chat_manager.broadcast_to_agents({
        "event": "new_message", "channel": channel, "conversation_id": conversation.id,
        "sender_id": sender_id, "content": msg.get("content", ""),
    })

    content = msg.get("content", "")
    if content:
        from app.services.message_pipeline import process_incoming_message
        cust_result = await db.execute(select(Customer).where(Customer.id == customer_id))
        customer = cust_result.scalar_one_or_none()
        if customer:
            pipeline_result = await process_incoming_message(db, conversation, customer, content)
            if pipeline_result.get("bot_messages"):
                from app.services.channels.dispatcher import dispatcher
                for bot_msg in pipeline_result["bot_messages"]:
                    await dispatcher.send(channel, sender_id, bot_msg)
