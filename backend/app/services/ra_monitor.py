"""Reclame Aqui monitor — fetches complaints via Gmail notifications."""
import logging
import re
from datetime import datetime, timezone
from html import unescape as html_unescape

logger = logging.getLogger(__name__)

RA_COMPANY_SLUG = "carbon-smartwatch"
RA_SENDER_PATTERNS = [
    "reclameaqui.com.br",
    "reclameaqui.com",
]


def _is_ra_email(from_email: str) -> bool:
    """Check if email is from Reclame Aqui."""
    email_lower = from_email.lower()
    return any(p in email_lower for p in RA_SENDER_PATTERNS)


def _extract_ra_id_from_url(url: str) -> str:
    """Extract RA complaint ID from URL like /carbon-smartwatch/titulo_ABC123XYZ/"""
    match = re.search(r'_([a-zA-Z0-9_-]{8,})/?$', url)
    return match.group(1) if match else ""


def _extract_ra_url(text: str) -> str:
    """Extract reclameaqui.com.br complaint URL from email body."""
    # Match full complaint URLs (not empresa/lista pages)
    patterns = [
        r'https?://(?:www\.)?reclameaqui\.com\.br/' + RA_COMPANY_SLUG + r'/[^\s<>"\']+',
        r'https?://(?:www\.)?reclameaqui\.com\.br/[^\s<>"\']+_[a-zA-Z0-9_-]{8,}/?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            url = match.group(0).rstrip(")")
            # Skip non-complaint pages
            if "/empresa/" in url or "/lista-reclamacoes" in url or "/sobre/" in url:
                continue
            return url
    return ""


def _clean_html(text: str) -> str:
    """Strip HTML tags and clean whitespace."""
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html_unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def _parse_ra_email(email_data: dict) -> dict | None:
    """Parse a Reclame Aqui notification email into complaint data.

    RA notifications typically contain:
    - Subject with complaint title or notification type
    - Body with complaint details, customer name, and link
    """
    subject = email_data.get("subject", "")
    body_text = email_data.get("body_text", "")
    body_html = email_data.get("body_html", "")

    # Use HTML body for URL extraction (more reliable), text for content
    full_text = body_text or _clean_html(body_html) if body_html else ""
    url_source = body_html or body_text

    # Skip non-complaint notifications (responses, ratings, etc)
    skip_subjects = [
        "avaliou sua resposta",
        "avaliação",
        "sua resposta foi",
        "parabéns",
        "ranking",
        "relatório",
        "newsletter",
    ]
    subject_lower = subject.lower()
    if any(s in subject_lower for s in skip_subjects):
        return None

    # Extract URL
    ra_url = _extract_ra_url(url_source)
    if not ra_url:
        ra_url = _extract_ra_url(full_text)

    # Extract RA ID
    ra_id = _extract_ra_id_from_url(ra_url) if ra_url else ""

    # If no URL/ID found, try to extract from email content
    if not ra_id:
        # Try to find any RA complaint ID in the text
        id_match = re.search(r'(?:reclamação|complaint|protocolo)[^\n]*?([a-zA-Z0-9]{10,})', full_text, re.IGNORECASE)
        if id_match:
            ra_id = id_match.group(1)

    # No complaint data found
    if not ra_id and not ra_url:
        return None

    # Extract title from subject or body
    title = subject
    # Clean common RA subject prefixes
    title = re.sub(r'^(?:Nova\s+)?(?:reclamação|Reclamação)\s*[-:–]\s*', '', title)
    title = re.sub(r'\s*[-–]\s*Carbon\s*Smartwatch.*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s*[-–]\s*Reclame\s*(?:AQUI|Aqui).*$', '', title, flags=re.IGNORECASE)
    title = title.strip()

    if not title or len(title) < 5:
        title = subject  # fallback to full subject

    # Extract description snippet from body
    description = ""
    if full_text:
        # Try to find the complaint text (usually after "Reclamação:" or similar)
        desc_patterns = [
            r'(?:reclamação|descrição|problema|relato)[:\s]*\n?\s*(.{20,500})',
            r'(?:o consumidor|o cliente|cliente)\s+(?:disse|escreveu|relatou)[:\s]*\n?\s*(.{20,500})',
        ]
        for dp in desc_patterns:
            desc_match = re.search(dp, full_text, re.IGNORECASE)
            if desc_match:
                description = desc_match.group(1).strip()[:500]
                break

        if not description:
            # Use first meaningful paragraph
            lines = [l.strip() for l in full_text.split('\n') if len(l.strip()) > 30]
            for line in lines:
                if not any(skip in line.lower() for skip in ['reclame aqui', 'clique aqui', 'ver reclamação', 'responder']):
                    description = line[:500]
                    break

    return {
        "id": ra_id or f"gmail_{email_data.get('gmail_id', 'unknown')}",
        "title": title[:500],
        "description": description,
        "created": email_data.get("date", ""),
        "status": "NEW",
        "url": ra_url,
        "answered": False,
        "gmail_id": email_data.get("gmail_id", ""),
    }


def fetch_ra_emails(max_results: int = 20) -> list[dict]:
    """Fetch RA notification emails from Gmail inbox.

    Uses the existing Gmail service to search for emails from RA.
    """
    from app.services.gmail_service import get_gmail_service

    service = get_gmail_service()
    if not service:
        logger.warning("Gmail service unavailable for RA monitoring")
        return []

    try:
        # Search for RA emails — both read and unread, last 30 days
        import time
        thirty_days_ago = int(time.time()) - (30 * 24 * 3600)
        query = f"from:reclameaqui.com.br after:{thirty_days_ago}"

        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return []

        emails = []
        for msg_ref in messages:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                ).execute()

                headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}

                from app.services.gmail_service import _extract_body, _extract_email, _extract_name
                body_text, body_html = _extract_body(msg["payload"])

                if not body_text and body_html:
                    body_text = _clean_html(body_html)

                if not body_text and not body_html:
                    body_text = msg.get("snippet", "")

                emails.append({
                    "gmail_id": msg["id"],
                    "thread_id": msg.get("threadId"),
                    "subject": headers.get("subject", "(Sem assunto)"),
                    "from_email": _extract_email(headers.get("from", "")),
                    "from_name": _extract_name(headers.get("from", "")),
                    "date": headers.get("date", ""),
                    "body_text": body_text[:5000],
                    "body_html": body_html[:10000] if body_html else None,
                })
            except Exception as e:
                logger.warning(f"Failed to fetch RA email {msg_ref['id']}: {e}")

        return emails

    except Exception as e:
        logger.error(f"Failed to fetch RA emails from Gmail: {e}")
        return []


async def fetch_ra_complaints(limit: int = 10) -> list[dict]:
    """Fetch RA complaints from Gmail notification emails."""
    emails = fetch_ra_emails(max_results=limit * 2)  # fetch more to account for non-complaint emails

    complaints = []
    seen_ids = set()

    for email_data in emails:
        complaint = _parse_ra_email(email_data)
        if not complaint:
            continue

        ra_id = complaint["id"]
        if ra_id in seen_ids:
            continue

        seen_ids.add(ra_id)
        complaints.append(complaint)

        if len(complaints) >= limit:
            break

    return complaints


async def fetch_ra_reputation() -> dict | None:
    """Return cached reputation data (RA site blocked by Cloudflare)."""
    # Hardcoded from session 19 analysis (1,518 complaints, rating 6.9/10)
    # TODO: update periodically when accessible
    return {
        "rating": "6.9",
        "level": "Regular",
        "total_complaints": "1518+",
        "response_rate": "98%",
        "resolution_rate": "72%",
        "would_buy_again": "47%",
        "last_updated": "2026-03-09",
    }


async def check_new_complaints(db) -> list[dict]:
    """Check for new RA complaints not yet tracked as tickets."""
    from sqlalchemy import select, text
    from app.models.ticket import Ticket

    complaints = await fetch_ra_complaints(limit=10)
    new_complaints = []

    for complaint in complaints:
        ra_id = complaint.get("id", "")
        if not ra_id:
            continue

        tag = f"ra:{ra_id}"
        existing = await db.execute(
            select(Ticket).where(
                text("tags @> ARRAY[:tag]::varchar[]").bindparams(tag=tag)
            )
        )
        if existing.scalars().first():
            continue

        new_complaints.append(complaint)

    return new_complaints


async def create_ra_ticket(complaint: dict, db) -> dict:
    """Create an urgent ticket from an RA complaint."""
    from app.models.ticket import Ticket
    from app.models.customer import Customer
    from app.models.message import Message
    from app.services.ticket_number import get_next_ticket_number
    from datetime import timedelta
    from sqlalchemy import select

    ra_id = str(complaint["id"])
    next_num = await get_next_ticket_number(db)

    ra_email = "reclameaqui@carbon.placeholder"
    existing_customer = await db.execute(
        select(Customer).where(Customer.email == ra_email)
    )
    customer = existing_customer.scalars().first()

    if not customer:
        customer = Customer(
            name="Cliente Reclame Aqui",
            email=ra_email,
            tags=["reclame_aqui"],
            risk_score=8.0,
        )
        db.add(customer)
        await db.flush()

    ticket = Ticket(
        number=next_num,
        subject=f"[RECLAME AQUI] {complaint['title'][:450]}",
        status="open",
        priority="urgent",
        category="reclamacao",
        source="reclame_aqui",
        legal_risk=True,
        tags=[f"ra:{ra_id}", "reclame_aqui", "urgente"],
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=4),
        ai_summary=complaint.get("description", "")[:500] or complaint.get("title", ""),
        customer_id=customer.id,
    )
    db.add(ticket)
    await db.flush()

    body_parts = [f"[Reclamação no Reclame Aqui]\n\nTítulo: {complaint['title']}"]
    if complaint.get("description"):
        body_parts.append(f"\n{complaint['description']}")
    if complaint.get("url"):
        body_parts.append(f"\nLink: {complaint['url']}")

    msg = Message(
        ticket_id=ticket.id,
        type="inbound",
        sender_name="Cliente Reclame Aqui",
        sender_email=ra_email,
        body_text="\n".join(body_parts),
    )
    db.add(msg)

    return {
        "ticket_number": ticket.number,
        "ra_id": ra_id,
        "title": complaint["title"],
        "url": complaint.get("url", ""),
    }
