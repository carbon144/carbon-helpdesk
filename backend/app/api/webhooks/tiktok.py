"""TikTok webhook endpoint."""
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.core.database import async_session
from app.models.customer import Customer
from app.models.channel_identity import ChannelIdentity
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage
from app.services.channels.tiktok_adapter import TikTokAdapter
from app.api.ws import notify_chat_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
_adapter = TikTokAdapter()


@router.post("/tiktok")
async def tiktok_webhook(request: Request):
    body = await request.body()
    if settings.TIKTOK_CLIENT_SECRET:
        sig = request.headers.get("X-TikTok-Signature", "")
        expected = hmac.new(settings.TIKTOK_CLIENT_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(403, "Invalid signature")
    payload = await request.json()
    messages = await _adapter.process_webhook(payload)
    if messages:
        async with async_session() as db:
            for msg in messages:
                sender_id = msg["sender_id"]
                result = await db.execute(
                    select(ChannelIdentity).where(ChannelIdentity.channel == "tiktok", ChannelIdentity.channel_id == sender_id)
                )
                identity = result.scalar_one_or_none()
                if identity:
                    customer_id = identity.customer_id
                else:
                    customer = Customer(name=f"TikTok {sender_id}")
                    db.add(customer)
                    await db.flush()
                    customer_id = customer.id
                    db.add(ChannelIdentity(customer_id=customer_id, channel="tiktok", channel_id=sender_id))

                result = await db.execute(
                    select(Conversation).where(Conversation.customer_id == customer_id, Conversation.channel == "tiktok", Conversation.status == "open")
                )
                conv = result.scalar_one_or_none()
                if not conv:
                    conv = Conversation(customer_id=customer_id, channel="tiktok", status="open")
                    db.add(conv)
                    await db.flush()

                now = datetime.now(timezone.utc)
                db.add(ChatMessage(
                    conversation_id=conv.id, sender_type="contact", sender_id=customer_id,
                    content_type=msg.get("content_type", "text"), content=msg.get("content", ""),
                    channel_message_id=msg.get("channel_message_id"), created_at=now,
                ))
                conv.last_message_at = now
                await notify_chat_event({
                    "event": "new_message", "channel": "tiktok",
                    "conversation_id": str(conv.id),
                    "sender_type": "contact", "sender_id": sender_id,
                    "content": msg.get("content", ""),
                })
                content = msg.get("content", "")
                if content:
                    from app.services.message_pipeline import process_incoming_message
                    cust = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
                    if cust:
                        pr = await process_incoming_message(db, conv, cust, content)
                        if pr.get("bot_messages"):
                            from app.services.channels.dispatcher import dispatcher
                            for bot_msg in pr["bot_messages"]:
                                await dispatcher.send("tiktok", sender_id, bot_msg)
            await db.commit()
    return {"status": "ok"}
