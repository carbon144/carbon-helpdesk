"""Gmail integration endpoints."""
import logging
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from google_auth_oauthlib.flow import Flow

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.customer import Customer
from app.services.gmail_service import (
    fetch_new_emails,
    send_email,
    mark_as_read,
    test_gmail_connection,
)
from app.services.protocol_service import assign_protocol

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gmail", tags=["gmail"])

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


# ---- OAuth flow ----

@router.get("/auth-url")
async def get_auth_url(user: User = Depends(get_current_user)):
    """Generate Gmail OAuth URL for admin to authorize."""
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_CLIENT_SECRET:
        raise HTTPException(400, "GMAIL_CLIENT_ID e GMAIL_CLIENT_SECRET não configurados no .env")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.GMAIL_REDIRECT_URI,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return {"auth_url": auth_url}


@router.get("/callback")
async def gmail_callback(code: str):
    """Handle Gmail OAuth callback."""
    if not settings.GMAIL_CLIENT_ID:
        raise HTTPException(400, "Gmail not configured")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.GMAIL_REDIRECT_URI,
    )

    flow.fetch_token(code=code)
    creds = flow.credentials

    # Return the refresh token to the user so they can add it to .env
    return {
        "status": "success",
        "message": "Gmail conectado! Copie o refresh_token abaixo e adicione no seu .env como GMAIL_REFRESH_TOKEN",
        "refresh_token": creds.refresh_token,
        "email": "Verifique com /api/gmail/status",
    }


# ---- Status ----

@router.get("/status")
async def gmail_status(user: User = Depends(get_current_user)):
    """Check Gmail integration status."""
    if not settings.GMAIL_CLIENT_ID:
        return {"configured": False, "connected": False}

    result = test_gmail_connection()
    return {
        "configured": bool(settings.GMAIL_CLIENT_ID),
        "has_refresh_token": bool(settings.GMAIL_REFRESH_TOKEN),
        "connected": result["ok"],
        "email": result.get("email"),
        "error": result.get("error"),
    }


def _parse_email_date(date_str: str) -> datetime | None:
    """Parse email Date header to datetime."""
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


# ---- Fetch and process emails ----

@router.post("/fetch")
async def fetch_emails(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fetch new emails and create tickets."""
    emails = fetch_new_emails(max_results=20)
    if not emails:
        return {"fetched": 0, "created": 0, "updated": 0}

    created = 0
    updated = 0

    for email_data in emails:
        gmail_thread_id = email_data.get("thread_id")
        gmail_message_id = email_data.get("gmail_id")

        # Check if this message was already processed
        existing_msg = await db.execute(
            select(Message).where(Message.gmail_message_id == gmail_message_id)
        )
        if existing_msg.scalars().first():
            continue

        # Check if there's an existing ticket for this Gmail thread
        existing_ticket = None
        if gmail_thread_id:
            result = await db.execute(
                select(Ticket).join(Message).where(Message.gmail_thread_id == gmail_thread_id)
            )
            existing_ticket = result.scalars().first()

        if existing_ticket:
            # Add message to existing ticket
            msg = Message(
                ticket_id=existing_ticket.id,
                type="inbound",
                sender_name=email_data["from_name"],
                sender_email=email_data["from_email"],
                body_text=email_data["body_text"],
                body_html=email_data.get("body_html"),
                gmail_message_id=gmail_message_id,
                gmail_thread_id=gmail_thread_id,
            )
            db.add(msg)

            # Reopen if resolved
            if existing_ticket.status == "resolved":
                existing_ticket.status = "open"
                existing_ticket.resolved_at = None

            # Reset SLA on new inbound email — starts from now
            now = datetime.now(timezone.utc)
            from app.core.sla_config import get_sla_for_ticket
            sla = get_sla_for_ticket(existing_ticket.category, existing_ticket.priority)
            existing_ticket.sla_deadline = now + timedelta(hours=sla["resolution_hours"])
            existing_ticket.sla_response_deadline = now + timedelta(hours=sla["response_hours"])
            existing_ticket.sla_breached = False
            existing_ticket.first_response_at = None  # Reset first response tracking

            existing_ticket.updated_at = now
            updated += 1
        else:
            # Create new ticket
            customer = await _find_or_create_customer(
                db, email_data["from_email"], email_data["from_name"]
            )

            max_num = await db.execute(select(func.max(Ticket.number)))
            next_num = (max_num.scalar() or 1000) + 1

            sla_deadline = datetime.now(timezone.utc) + timedelta(hours=settings.SLA_MEDIUM_HOURS)

            email_date = _parse_email_date(email_data.get("date", ""))

            ticket = Ticket(
                number=next_num,
                subject=email_data["subject"][:500],
                status="open",
                priority="medium",
                customer_id=customer.id,
                source="gmail",
                sla_deadline=sla_deadline,
                received_at=email_date or datetime.now(timezone.utc),
            )
            db.add(ticket)
            await db.flush()

            msg = Message(
                ticket_id=ticket.id,
                type="inbound",
                sender_name=email_data["from_name"],
                sender_email=email_data["from_email"],
                body_text=email_data["body_text"],
                body_html=email_data.get("body_html"),
                gmail_message_id=gmail_message_id,
                gmail_thread_id=gmail_thread_id,
            )
            db.add(msg)

            # AI Triage for new ticket
            try:
                from app.services.ai_service import triage_ticket as ai_triage
                triage = ai_triage(
                    subject=email_data["subject"],
                    body=email_data["body_text"][:2000],
                    customer_name=email_data["from_name"],
                    is_repeat=customer.is_repeat,
                )
                if triage:
                    if triage.get("category"):
                        ticket.ai_category = triage["category"]
                        ticket.category = triage["category"]
                    if triage.get("priority"):
                        ticket.priority = triage["priority"]
                        from app.core.config import settings as cfg
                        hours_map = {"urgent": cfg.SLA_URGENT_HOURS, "high": cfg.SLA_HIGH_HOURS, "medium": cfg.SLA_MEDIUM_HOURS, "low": cfg.SLA_LOW_HOURS}
                        ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=hours_map.get(triage["priority"], 24))
                    if triage.get("sentiment"):
                        ticket.sentiment = triage["sentiment"]
                    if triage.get("legal_risk") is not None:
                        ticket.legal_risk = triage["legal_risk"]
                    if triage.get("tags"):
                        ticket.tags = triage["tags"]
                    if triage.get("confidence"):
                        ticket.ai_confidence = triage["confidence"]
            except Exception as e:
                logger.warning(f"AI triage skipped for gmail ticket: {e}")

            # Generate protocol (email sent later by agent)
            try:
                await assign_protocol(ticket, db)
            except Exception as e:
                logger.warning(f"Protocol assignment skipped: {e}")

            created += 1

        # Mark as read in Gmail
        mark_as_read(gmail_message_id)

    await db.commit()

    return {"fetched": len(emails), "created": created, "updated": updated}


# ---- Fetch email history (last 30 days) ----

@router.post("/fetch-history")
async def fetch_email_history(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fetch email history from specified period and create tickets."""
    import time
    try:
        body = await request.json()
        days = body.get("days", 30)
    except Exception:
        days = 30
    days = max(1, min(days, 365))
    cutoff = int(time.time()) - (days * 24 * 3600)

    try:
        all_emails = fetch_new_emails(after_timestamp=cutoff, max_results=200, include_read=True)
    except Exception as e:
        logger.error(f"Failed to fetch email history: {e}")
        raise HTTPException(500, f"Erro ao buscar emails do Gmail: {str(e)}")

    if not all_emails:
        return {"fetched": 0, "created": 0, "updated": 0}

    created = 0
    updated = 0
    skipped = 0

    for email_data in all_emails:
        gmail_thread_id = email_data.get("thread_id")
        gmail_message_id = email_data.get("gmail_id")

        # Check if already processed
        existing_msg = await db.execute(
            select(Message).where(Message.gmail_message_id == gmail_message_id)
        )
        if existing_msg.scalars().first():
            skipped += 1
            continue

        # Check existing ticket for this thread
        existing_ticket = None
        if gmail_thread_id:
            result = await db.execute(
                select(Ticket).join(Message).where(Message.gmail_thread_id == gmail_thread_id)
            )
            existing_ticket = result.scalars().first()

        if existing_ticket:
            msg = Message(
                ticket_id=existing_ticket.id,
                type="inbound",
                sender_name=email_data["from_name"],
                sender_email=email_data["from_email"],
                body_text=email_data["body_text"],
                body_html=email_data.get("body_html"),
                gmail_message_id=gmail_message_id,
                gmail_thread_id=gmail_thread_id,
            )
            db.add(msg)
            # Reset SLA on new inbound email
            now = datetime.now(timezone.utc)
            from app.core.sla_config import get_sla_for_ticket
            sla = get_sla_for_ticket(existing_ticket.category, existing_ticket.priority)
            existing_ticket.sla_deadline = now + timedelta(hours=sla["resolution_hours"])
            existing_ticket.sla_response_deadline = now + timedelta(hours=sla["response_hours"])
            existing_ticket.sla_breached = False
            existing_ticket.updated_at = now
            updated += 1
        else:
            customer = await _find_or_create_customer(
                db, email_data["from_email"], email_data["from_name"]
            )
            max_num = await db.execute(select(func.max(Ticket.number)))
            next_num = (max_num.scalar() or 1000) + 1
            sla_deadline = datetime.now(timezone.utc) + timedelta(hours=settings.SLA_MEDIUM_HOURS)
            email_date = _parse_email_date(email_data.get("date", ""))

            ticket = Ticket(
                number=next_num,
                subject=email_data["subject"][:500],
                status="open",
                priority="medium",
                customer_id=customer.id,
                source="gmail",
                sla_deadline=sla_deadline,
                received_at=email_date or datetime.now(timezone.utc),
            )
            db.add(ticket)
            await db.flush()

            msg = Message(
                ticket_id=ticket.id,
                type="inbound",
                sender_name=email_data["from_name"],
                sender_email=email_data["from_email"],
                body_text=email_data["body_text"],
                body_html=email_data.get("body_html"),
                gmail_message_id=gmail_message_id,
                gmail_thread_id=gmail_thread_id,
            )
            db.add(msg)

            # AI Triage
            try:
                from app.services.ai_service import triage_ticket as ai_triage
                triage = ai_triage(
                    subject=email_data["subject"],
                    body=email_data["body_text"][:2000],
                    customer_name=email_data["from_name"],
                    is_repeat=customer.is_repeat,
                )
                if triage:
                    if triage.get("category"):
                        ticket.ai_category = triage["category"]
                        ticket.category = triage["category"]
                    if triage.get("priority"):
                        ticket.priority = triage["priority"]
                        from app.core.config import settings as cfg
                        hours_map = {"urgent": cfg.SLA_URGENT_HOURS, "high": cfg.SLA_HIGH_HOURS, "medium": cfg.SLA_MEDIUM_HOURS, "low": cfg.SLA_LOW_HOURS}
                        ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=hours_map.get(triage["priority"], 24))
                    if triage.get("sentiment"):
                        ticket.sentiment = triage["sentiment"]
                    if triage.get("legal_risk") is not None:
                        ticket.legal_risk = triage["legal_risk"]
                    if triage.get("tags"):
                        ticket.tags = triage["tags"]
                    if triage.get("confidence"):
                        ticket.ai_confidence = triage["confidence"]
            except Exception as e:
                logger.warning(f"AI triage skipped for history ticket: {e}")

            # Generate protocol (email sent later by agent)
            try:
                await assign_protocol(ticket, db)
            except Exception as e:
                logger.warning(f"Protocol assignment skipped: {e}")

            created += 1

    await db.commit()
    return {"fetched": len(all_emails), "created": created, "updated": updated, "skipped": skipped}


# ---- Send reply via Gmail ----

@router.post("/send-reply")
async def send_gmail_reply(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send an agent reply via Gmail."""
    data = await request.json()
    ticket_id = data.get("ticket_id")
    message_text = data.get("message")

    if not ticket_id or not message_text:
        raise HTTPException(400, "ticket_id e message são obrigatórios")

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")

    if ticket.source != "gmail":
        raise HTTPException(400, "Este ticket não veio do Gmail")

    # Get customer email
    customer = ticket.customer
    if not customer:
        raise HTTPException(400, "Cliente não encontrado")

    # Find the Gmail thread ID from the first message
    msg_result = await db.execute(
        select(Message).where(
            Message.ticket_id == ticket.id,
            Message.gmail_thread_id.isnot(None),
        ).limit(1)
    )
    first_msg = msg_result.scalars().first()
    gmail_thread_id = first_msg.gmail_thread_id if first_msg else None
    in_reply_to = first_msg.gmail_message_id if first_msg else None

    subject = f"Re: {ticket.subject}"

    # Append agent email signature if exists
    full_message = message_text
    if user.email_signature:
        full_message += f"\n\n--\n{user.email_signature}"

    response = send_email(
        to=customer.email,
        subject=subject,
        body_text=full_message,
        thread_id=gmail_thread_id,
        in_reply_to=in_reply_to,
    )

    if not response:
        raise HTTPException(500, "Falha ao enviar email")

    return {"ok": True, "gmail_id": response.get("id")}


async def _find_or_create_customer(db: AsyncSession, email: str, name: str) -> Customer:
    """Find or create a customer by email."""
    result = await db.execute(select(Customer).where(Customer.email == email))
    customer = result.scalars().first()
    if not customer:
        customer = Customer(name=name, email=email)
        db.add(customer)
        await db.flush()
    else:
        customer.total_tickets += 1
        if customer.total_tickets > 2:
            customer.is_repeat = True
    return customer
