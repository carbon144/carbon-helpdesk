"""Slack webhook and integration endpoints."""
import hashlib
import hmac
import time
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, HTTPException, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.customer import Customer
from app.services.slack_service import (
    send_ticket_created_notification,
    send_agent_reply_to_slack,
    get_slack_user_info,
    test_slack_connection,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["slack"])


# ---- Verification helpers ----

def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """Verify that the request actually came from Slack."""
    if not settings.SLACK_SIGNING_SECRET:
        return True  # Skip verification if not configured (dev mode)

    # Prevent replay attacks (5 min window)
    if abs(time.time() - int(timestamp)) > 300:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_signature = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)


# ---- Webhook endpoint (receives Slack events) ----

@router.post("/events")
async def slack_events(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Slack Events API webhook."""
    body = await request.body()
    data = await request.json()

    # Handle URL verification challenge
    if data.get("type") == "url_verification":
        return {"challenge": data["challenge"]}

    # Verify signature
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "0")
    signature = request.headers.get("X-Slack-Signature", "")
    if not verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Handle events
    event = data.get("event", {})
    event_type = event.get("type")

    if event_type == "message":
        # Ignore bot messages, edits, and thread replies (we handle those separately)
        if event.get("bot_id") or event.get("subtype"):
            return {"ok": True}

        # Only process messages in the support channel
        channel = event.get("channel", "")
        if settings.SLACK_SUPPORT_CHANNEL and channel != settings.SLACK_SUPPORT_CHANNEL:
            return {"ok": True}

        # If it's a thread reply, add as message to existing ticket
        thread_ts = event.get("thread_ts")
        if thread_ts:
            await handle_slack_thread_reply(db, event, channel, thread_ts)
        else:
            # New top-level message = new ticket
            await handle_new_slack_ticket(db, event, channel)

    return {"ok": True}


async def handle_new_slack_ticket(db: AsyncSession, event: dict, channel: str):
    """Create a new ticket from a Slack message."""
    slack_user_id = event.get("user", "")
    text = event.get("text", "Sem assunto")
    ts = event.get("ts", "")

    # Get Slack user info
    user_info = await get_slack_user_info(slack_user_id)
    customer_name = user_info["name"] if user_info else f"Slack User {slack_user_id}"
    customer_email = user_info.get("email", f"{slack_user_id}@slack.local") if user_info else f"{slack_user_id}@slack.local"

    # Find or create customer
    result = await db.execute(select(Customer).where(Customer.email == customer_email))
    customer = result.scalars().first()
    if not customer:
        customer = Customer(
            name=customer_name,
            email=customer_email,
        )
        db.add(customer)
        await db.flush()
    else:
        customer.total_tickets += 1
        if customer.total_tickets > 2:
            customer.is_repeat = True

    # Create subject from first line (max 100 chars)
    subject = text.split("\n")[0][:100] if text else "Mensagem via Slack"

    # Get next ticket number
    max_num = await db.execute(select(func.max(Ticket.number)))
    next_num = (max_num.scalar() or 0) + 1

    # Calculate SLA
    sla_hours = settings.SLA_MEDIUM_HOURS
    sla_deadline = datetime.now(timezone.utc) + timedelta(hours=sla_hours)

    ticket = Ticket(
        number=next_num,
        subject=subject,
        status="open",
        priority="medium",
        customer_id=customer.id,
        slack_channel_id=channel,
        slack_thread_ts=ts,
        source="slack",
        sla_deadline=sla_deadline,
    )
    db.add(ticket)
    await db.flush()

    # Create the initial message
    message = Message(
        ticket_id=ticket.id,
        type="inbound",
        sender_name=customer_name,
        sender_email=customer_email,
        body_text=text,
        slack_ts=ts,
    )
    db.add(message)

    await db.commit()

    # Send confirmation back to Slack
    await send_ticket_created_notification(channel, ts, ticket.number, subject)

    logger.info(f"Created ticket #{ticket.number} from Slack message by {customer_name}")


async def handle_slack_thread_reply(db: AsyncSession, event: dict, channel: str, thread_ts: str):
    """Add a Slack thread reply as a message to an existing ticket."""
    # Find ticket by thread_ts
    result = await db.execute(
        select(Ticket).where(Ticket.slack_thread_ts == thread_ts)
    )
    ticket = result.scalars().first()
    if not ticket:
        return  # No matching ticket, ignore

    slack_user_id = event.get("user", "")
    text = event.get("text", "")
    ts = event.get("ts", "")

    user_info = await get_slack_user_info(slack_user_id)
    sender_name = user_info["name"] if user_info else f"Slack User {slack_user_id}"
    sender_email = user_info.get("email", "") if user_info else ""

    message = Message(
        ticket_id=ticket.id,
        type="inbound",
        sender_name=sender_name,
        sender_email=sender_email,
        body_text=text,
        slack_ts=ts,
    )
    db.add(message)

    # Reopen ticket if it was resolved
    if ticket.status == "resolved":
        ticket.status = "open"
        ticket.resolved_at = None

    await db.commit()
    logger.info(f"Added Slack reply to ticket #{ticket.number}")


# ---- API endpoints for agents ----

@router.get("/status")
async def slack_status(user: User = Depends(get_current_user)):
    """Check if Slack integration is configured and working."""
    if not settings.SLACK_BOT_TOKEN:
        return {
            "configured": False,
            "connected": False,
            "channel": None,
        }

    connection = await test_slack_connection()
    return {
        "configured": True,
        "connected": connection["ok"],
        "bot_name": connection.get("bot_name"),
        "team": connection.get("team"),
        "channel": settings.SLACK_SUPPORT_CHANNEL or None,
        "error": connection.get("error"),
    }


@router.post("/send-reply")
async def send_reply_to_slack(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send an agent reply back to the Slack thread."""
    data = await request.json()
    ticket_id = data.get("ticket_id")
    message_text = data.get("message")

    if not ticket_id or not message_text:
        raise HTTPException(400, "ticket_id e message são obrigatórios")

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")

    if not ticket.slack_channel_id or not ticket.slack_thread_ts:
        raise HTTPException(400, "Este ticket não veio do Slack")

    response = await send_agent_reply_to_slack(
        channel=ticket.slack_channel_id,
        thread_ts=ticket.slack_thread_ts,
        agent_name=user.name,
        message_text=message_text,
    )

    if not response:
        raise HTTPException(500, "Falha ao enviar mensagem ao Slack")

    return {"ok": True, "slack_ts": response.get("ts")}

