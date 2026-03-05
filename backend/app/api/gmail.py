"""Gmail integration endpoints."""
from __future__ import annotations
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
    fetch_spam_emails,
    move_from_spam,
    send_email,
    mark_as_read,
    test_gmail_connection,
)
from app.services.protocol_service import assign_protocol
from app.services.data_extractor import extract_customer_data
from app.services.customer_matcher import find_matching_customer

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

        # Extract email thread headers
        email_message_id = email_data.get("message_id")  # Message-ID header
        in_reply_to = email_data.get("in_reply_to")  # In-Reply-To header
        email_references = email_data.get("references")  # References header

        # Check if this message was already processed
        existing_msg = await db.execute(
            select(Message).where(Message.gmail_message_id == gmail_message_id)
        )
        if existing_msg.scalars().first():
            continue

        # Check email thread matching via In-Reply-To header
        existing_ticket = None
        if in_reply_to:
            ref_msg_result = await db.execute(
                select(Message).where(Message.email_message_id == in_reply_to)
            )
            ref_msg = ref_msg_result.scalar_one_or_none()
            if ref_msg:
                # Add as reply to existing ticket instead of creating new one
                msg = Message(
                    ticket_id=ref_msg.ticket_id,
                    type="inbound",
                    sender_name=email_data["from_name"],
                    sender_email=email_data["from_email"],
                    body_text=email_data["body_text"],
                    body_html=email_data.get("body_html"),
                    gmail_message_id=gmail_message_id,
                    gmail_thread_id=gmail_thread_id,
                    email_message_id=email_message_id,
                    email_references=email_references,
                )
                db.add(msg)

                # Update the ticket
                ticket_result = await db.execute(
                    select(Ticket).where(Ticket.id == ref_msg.ticket_id)
                )
                matched_ticket = ticket_result.scalar_one_or_none()
                if matched_ticket:
                    was_resolved = matched_ticket.status == "resolved"
                    if matched_ticket.status in ("resolved", "waiting", "waiting_supplier", "waiting_resend"):
                        matched_ticket.status = "open"
                    if was_resolved:
                        matched_ticket.resolved_at = None
                    now = datetime.now(timezone.utc)
                    from app.core.sla_config import get_sla_for_ticket
                    sla = get_sla_for_ticket(matched_ticket.category, matched_ticket.priority)
                    matched_ticket.sla_deadline = now + timedelta(hours=sla["resolution_hours"])
                    matched_ticket.sla_response_deadline = now + timedelta(hours=sla["response_hours"])
                    matched_ticket.sla_breached = False
                    matched_ticket.first_response_at = None
                    matched_ticket.updated_at = now

                mark_as_read(gmail_message_id)
                updated += 1
                continue

        # Check if there's an existing ticket for this Gmail thread
        if gmail_thread_id:
            result = await db.execute(
                select(Ticket).join(Message).where(Message.gmail_thread_id == gmail_thread_id)
            )
            existing_ticket = result.scalars().first()

        # If no thread match, try to find open ticket from same customer
        if not existing_ticket:
            resolved_customer = await _find_or_create_customer(
                db, email_data["from_email"], email_data["from_name"]
            )
            result = await db.execute(
                select(Ticket).where(
                    Ticket.customer_id == resolved_customer.id,
                    Ticket.status.notin_(["resolved", "closed", "archived", "merged"]),
                ).order_by(Ticket.updated_at.desc())
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
                email_message_id=email_message_id,
                email_references=email_references,
            )
            db.add(msg)

            # Reopen if resolved or move back from waiting (Respondidos → Novos)
            if existing_ticket.status == "resolved":
                existing_ticket.status = "open"
                existing_ticket.resolved_at = None
            elif existing_ticket.status in ("waiting", "waiting_supplier", "waiting_resend"):
                existing_ticket.status = "open"

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
            # Extract customer data from email body for matching
            body_text = email_data.get("body_text", "")
            extracted_data = extract_customer_data(body_text)

            # Try to find matching customer by extracted data (CPF, phone, email)
            matched_customer = None
            if any(extracted_data.get(k) for k in ("cpf", "phone", "email")):
                try:
                    matched_customer = await find_matching_customer(
                        db,
                        cpf=extracted_data.get("cpf"),
                        phone=extracted_data.get("phone"),
                        email=extracted_data.get("email"),
                        shopify_order_id=extracted_data.get("shopify_order_id"),
                    )
                except Exception as e:
                    logger.warning(f"Customer matching failed: {e}")

            if matched_customer:
                customer = matched_customer
                # Update customer data if we found new info
                if extracted_data.get("cpf") and not customer.cpf:
                    customer.cpf = extracted_data["cpf"]
                if extracted_data.get("phone") and not customer.phone:
                    customer.phone = extracted_data["phone"]
            else:
                # Create new ticket
                customer = await _find_or_create_customer(
                    db, email_data["from_email"], email_data["from_name"]
                )
                # Enrich new customer with extracted data
                if extracted_data.get("cpf") and not customer.cpf:
                    customer.cpf = extracted_data["cpf"]
                if extracted_data.get("phone") and not customer.phone:
                    customer.phone = extracted_data["phone"]

            from app.services.ticket_number import get_next_ticket_number
            next_num = await get_next_ticket_number(db)

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
                email_message_id=email_message_id,
                email_references=email_references,
            )
            db.add(msg)

            # AI Triage for new ticket
            try:
                from app.services.ai_service import triage_ticket as ai_triage, apply_triage_results
                triage = await ai_triage(
                    subject=email_data["subject"],
                    body=email_data["body_text"][:2000],
                    customer_name=email_data["from_name"],
                    is_repeat=customer.is_repeat,
                )
                apply_triage_results(ticket, triage, customer=customer)
                if triage and triage.get("priority"):
                    from app.core.config import settings as cfg
                    hours_map = {"urgent": cfg.SLA_URGENT_HOURS, "high": cfg.SLA_HIGH_HOURS, "medium": cfg.SLA_MEDIUM_HOURS, "low": cfg.SLA_LOW_HOURS}
                    ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=hours_map.get(triage["priority"], 24))
            except Exception as e:
                logger.warning(f"AI triage skipped for gmail ticket: {e}")

            # Generate protocol (email sent later by agent)
            try:
                await assign_protocol(ticket, db)
            except Exception as e:
                logger.warning(f"Protocol assignment skipped: {e}")

            # Auto-assign to available agent
            try:
                from app.api.tickets import _auto_assign_single
                await _auto_assign_single(ticket, db, user)
            except Exception as e:
                logger.warning(f"Auto-assign skipped for gmail ticket: {e}")

            created += 1

        # Mark as read in Gmail
        mark_as_read(gmail_message_id)

    await db.commit()

    if created or updated:
        from app.services.cache import cache_delete_pattern
        await cache_delete_pattern("dashboard:*")
        await cache_delete_pattern("gamification:*")

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
        all_emails = fetch_new_emails(after_timestamp=cutoff, max_results=500, include_read=True)
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

        # Extract email thread headers
        email_message_id = email_data.get("message_id")
        in_reply_to = email_data.get("in_reply_to")
        email_references = email_data.get("references")

        # Check if already processed
        existing_msg = await db.execute(
            select(Message).where(Message.gmail_message_id == gmail_message_id)
        )
        if existing_msg.scalars().first():
            skipped += 1
            continue

        # Check email thread matching via In-Reply-To header
        existing_ticket = None
        if in_reply_to:
            ref_msg_result = await db.execute(
                select(Message).where(Message.email_message_id == in_reply_to)
            )
            ref_msg = ref_msg_result.scalar_one_or_none()
            if ref_msg:
                msg = Message(
                    ticket_id=ref_msg.ticket_id,
                    type="inbound",
                    sender_name=email_data["from_name"],
                    sender_email=email_data["from_email"],
                    body_text=email_data["body_text"],
                    body_html=email_data.get("body_html"),
                    gmail_message_id=gmail_message_id,
                    gmail_thread_id=gmail_thread_id,
                    email_message_id=email_message_id,
                    email_references=email_references,
                )
                db.add(msg)
                # Update the ticket SLA
                ticket_result = await db.execute(
                    select(Ticket).where(Ticket.id == ref_msg.ticket_id)
                )
                matched_ticket = ticket_result.scalar_one_or_none()
                if matched_ticket:
                    now = datetime.now(timezone.utc)
                    from app.core.sla_config import get_sla_for_ticket
                    sla = get_sla_for_ticket(matched_ticket.category, matched_ticket.priority)
                    matched_ticket.sla_deadline = now + timedelta(hours=sla["resolution_hours"])
                    matched_ticket.sla_response_deadline = now + timedelta(hours=sla["response_hours"])
                    matched_ticket.sla_breached = False
                    matched_ticket.updated_at = now
                updated += 1
                continue

        # Check existing ticket for this thread
        if gmail_thread_id:
            result = await db.execute(
                select(Ticket).join(Message).where(Message.gmail_thread_id == gmail_thread_id)
            )
            existing_ticket = result.scalars().first()

        # If no thread match, try to find open ticket from same customer
        if not existing_ticket:
            resolved_customer = await _find_or_create_customer(
                db, email_data["from_email"], email_data["from_name"]
            )
            result = await db.execute(
                select(Ticket).where(
                    Ticket.customer_id == resolved_customer.id,
                    Ticket.status.notin_(["resolved", "closed", "archived", "merged"]),
                ).order_by(Ticket.updated_at.desc())
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
                email_message_id=email_message_id,
                email_references=email_references,
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
            # Extract customer data from email body for matching
            body_text = email_data.get("body_text", "")
            extracted_data = extract_customer_data(body_text)

            # Try to find matching customer by extracted data
            matched_customer = None
            if any(extracted_data.get(k) for k in ("cpf", "phone", "email")):
                try:
                    matched_customer = await find_matching_customer(
                        db,
                        cpf=extracted_data.get("cpf"),
                        phone=extracted_data.get("phone"),
                        email=extracted_data.get("email"),
                        shopify_order_id=extracted_data.get("shopify_order_id"),
                    )
                except Exception as e:
                    logger.warning(f"Customer matching failed: {e}")

            if matched_customer:
                customer = matched_customer
                if extracted_data.get("cpf") and not customer.cpf:
                    customer.cpf = extracted_data["cpf"]
                if extracted_data.get("phone") and not customer.phone:
                    customer.phone = extracted_data["phone"]
            else:
                customer = await _find_or_create_customer(
                    db, email_data["from_email"], email_data["from_name"]
                )
                if extracted_data.get("cpf") and not customer.cpf:
                    customer.cpf = extracted_data["cpf"]
                if extracted_data.get("phone") and not customer.phone:
                    customer.phone = extracted_data["phone"]

            from app.services.ticket_number import get_next_ticket_number
            next_num = await get_next_ticket_number(db)
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
                email_message_id=email_message_id,
                email_references=email_references,
            )
            db.add(msg)

            # AI Triage
            try:
                from app.services.ai_service import triage_ticket as ai_triage, apply_triage_results
                triage = await ai_triage(
                    subject=email_data["subject"],
                    body=email_data["body_text"][:2000],
                    customer_name=email_data["from_name"],
                    is_repeat=customer.is_repeat,
                )
                apply_triage_results(ticket, triage, customer=customer)
                if triage and triage.get("priority"):
                    from app.core.config import settings as cfg
                    hours_map = {"urgent": cfg.SLA_URGENT_HOURS, "high": cfg.SLA_HIGH_HOURS, "medium": cfg.SLA_MEDIUM_HOURS, "low": cfg.SLA_LOW_HOURS}
                    ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=hours_map.get(triage["priority"], 24))
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
    cc = data.get("cc")  # list of emails
    bcc = data.get("bcc")  # list of emails
    attachments = data.get("attachments")  # list of attachment dicts

    if not ticket_id or not message_text:
        raise HTTPException(400, "ticket_id e message são obrigatórios")

    # Clean cc/bcc: filter empty strings
    if cc:
        cc = [e.strip() for e in cc if e.strip()]
    if bcc:
        bcc = [e.strip() for e in bcc if e.strip()]

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
        cc=cc or None,
        bcc=bcc or None,
        attachments=attachments if attachments else None,
    )

    if not response:
        raise HTTPException(500, "Falha ao enviar email")

    return {"ok": True, "gmail_id": response.get("id")}


@router.post("/compose")
async def compose_email(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compose and send a new email (not a reply to an existing ticket)."""
    from datetime import datetime as dt_cls
    data = await request.json()
    to_email = data.get("to")
    to_name = data.get("to_name", "")
    subject = data.get("subject")
    body_text = data.get("body")
    cc = data.get("cc")  # list of emails
    bcc = data.get("bcc")  # list of emails
    scheduled_at_str = data.get("scheduled_at")  # ISO datetime string
    attachments = data.get("attachments")  # list of attachment dicts

    if not to_email or not subject or not body_text:
        raise HTTPException(400, "to, subject e body são obrigatórios")

    # Clean cc/bcc: filter empty strings
    if cc:
        cc = [e.strip() for e in cc if e.strip()]
    if bcc:
        bcc = [e.strip() for e in bcc if e.strip()]

    # Parse scheduled_at
    scheduled_at = None
    if scheduled_at_str:
        try:
            scheduled_at = dt_cls.fromisoformat(scheduled_at_str.replace("Z", "+00:00"))
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        except Exception:
            scheduled_at = None

    is_scheduled = scheduled_at is not None and scheduled_at > datetime.now(timezone.utc)

    # Append agent email signature if exists
    full_message = body_text
    if user.email_signature:
        full_message += f"\n\n--\n{user.email_signature}"

    response = None
    if not is_scheduled:
        # Send the email immediately
        response = send_email(
            to=to_email,
            subject=subject,
            body_text=full_message,
            cc=cc or None,
            bcc=bcc or None,
            attachments=attachments if attachments else None,
        )

        if not response:
            raise HTTPException(500, "Falha ao enviar email")

    # Create ticket for tracking
    customer = await _find_or_create_customer(db, to_email, to_name or to_email.split("@")[0])

    from app.services.ticket_number import get_next_ticket_number
    next_num = await get_next_ticket_number(db)

    sla_deadline = datetime.now(timezone.utc) + timedelta(hours=settings.SLA_MEDIUM_HOURS)

    ticket = Ticket(
        number=next_num,
        subject=subject[:500],
        status="open",
        priority="medium",
        customer_id=customer.id,
        assigned_to=user.id,
        source="gmail",
        sla_deadline=sla_deadline,
        first_response_at=None if is_scheduled else datetime.now(timezone.utc),
    )
    db.add(ticket)
    await db.flush()

    msg = Message(
        ticket_id=ticket.id,
        type="outbound",
        sender_name=user.name,
        sender_email=settings.GMAIL_SUPPORT_EMAIL or user.email,
        body_text=body_text,
        gmail_message_id=response.get("id") if response else None,
        gmail_thread_id=response.get("threadId") if response else None,
        cc=", ".join(cc) if cc else None,
        bcc=", ".join(bcc) if bcc else None,
        attachments=attachments if attachments else None,
        scheduled_at=scheduled_at if is_scheduled else None,
        is_scheduled=is_scheduled,
    )
    db.add(msg)

    try:
        await assign_protocol(ticket, db)
    except Exception:
        pass

    await db.commit()

    from app.services.cache import cache_delete_pattern
    await cache_delete_pattern("dashboard:*")
    await cache_delete_pattern("gamification:*")

    return {
        "ok": True,
        "ticket_id": ticket.id,
        "ticket_number": ticket.number,
        "scheduled": is_scheduled,
    }


# ---- Spam ----

@router.get("/spam")
async def get_spam_emails(user: User = Depends(get_current_user)):
    """Fetch emails from Gmail SPAM folder."""
    emails = fetch_spam_emails(max_results=50)
    return {"emails": emails, "total": len(emails)}


@router.post("/spam/rescue-bulk")
async def bulk_rescue_from_spam(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move multiple emails from SPAM to INBOX."""
    data = await request.json()
    message_ids = data.get("message_ids", [])
    if not message_ids:
        raise HTTPException(400, "message_ids é obrigatório")

    rescued = []
    failed = []
    for mid in message_ids:
        try:
            success = move_from_spam(mid)
            if success:
                rescued.append(mid)
            else:
                failed.append(mid)
        except Exception:
            failed.append(mid)

    return {
        "ok": True,
        "rescued": len(rescued),
        "failed": len(failed),
        "rescued_ids": rescued,
        "failed_ids": failed,
    }


@router.post("/spam/rescue/{message_id}")
async def rescue_from_spam(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move an email from SPAM to INBOX and optionally create a ticket."""
    success = move_from_spam(message_id)
    if not success:
        raise HTTPException(500, "Falha ao mover email do spam")

    return {"ok": True, "message": "Email movido para a caixa de entrada"}


@router.post("/spam/rescue-and-create/{message_id}")
async def rescue_and_create_ticket(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move email from SPAM to INBOX and create a ticket from it."""
    # Move from spam first
    success = move_from_spam(message_id)
    if not success:
        raise HTTPException(500, "Falha ao mover email do spam")

    # Get the email data from request body
    data = await request.json()
    from_email = data.get("from_email", "")
    from_name = data.get("from_name", "")
    subject = data.get("subject", "(Sem assunto)")
    body_text = data.get("body_text", "")
    gmail_thread_id = data.get("thread_id")

    if not from_email:
        raise HTTPException(400, "from_email é obrigatório")

    # Check if message already processed
    existing_msg = await db.execute(
        select(Message).where(Message.gmail_message_id == message_id)
    )
    if existing_msg.scalars().first():
        return {"ok": True, "message": "Email já processado anteriormente"}

    # Create customer + ticket
    customer = await _find_or_create_customer(db, from_email, from_name)

    from app.services.ticket_number import get_next_ticket_number
    next_num = await get_next_ticket_number(db)

    sla_deadline = datetime.now(timezone.utc) + timedelta(hours=settings.SLA_MEDIUM_HOURS)

    ticket = Ticket(
        number=next_num,
        subject=subject[:500],
        status="open",
        priority="medium",
        customer_id=customer.id,
        source="gmail",
        sla_deadline=sla_deadline,
        tags=["RESGATADO_SPAM"],
    )
    db.add(ticket)
    await db.flush()

    msg = Message(
        ticket_id=ticket.id,
        type="inbound",
        sender_name=from_name,
        sender_email=from_email,
        body_text=body_text,
        gmail_message_id=message_id,
        gmail_thread_id=gmail_thread_id,
    )
    db.add(msg)

    # AI Triage
    try:
        from app.services.ai_service import triage_ticket as ai_triage, apply_triage_results
        triage = await ai_triage(
            subject=subject,
            body=body_text[:2000],
            customer_name=from_name,
            is_repeat=customer.is_repeat,
        )
        apply_triage_results(ticket, triage, customer=customer)
    except Exception as e:
        logger.warning(f"AI triage skipped for spam-rescued ticket: {e}")

    # Generate protocol
    try:
        await assign_protocol(ticket, db)
    except Exception:
        pass

    # Mark as read
    mark_as_read(message_id)

    await db.commit()

    return {
        "ok": True,
        "ticket_id": ticket.id,
        "ticket_number": ticket.number,
        "message": f"Ticket #{ticket.number} criado a partir do email resgatado",
    }


async def _find_or_create_customer(db: AsyncSession, email: str, name: str) -> Customer:
    """Find or create a customer by email, following merge chain."""
    from app.services.customer_matcher import _follow_merge_chain

    result = await db.execute(select(Customer).where(Customer.email == email))
    customer = result.scalars().first()
    if not customer:
        customer = Customer(name=name, email=email)
        db.add(customer)
        await db.flush()
    else:
        # Follow merge chain — if customer was merged, use the target customer
        customer = await _follow_merge_chain(db, customer)
    return customer
