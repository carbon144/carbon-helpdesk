"""Re-import emails from Gmail after TRUNCATE CASCADE incident.

Pulls ALL emails (inbox + sent) in batches, reconstructs tickets with full thread history.
Detects which tickets already have our replies and marks them appropriately.
Auto-reply is disabled via EMAIL_AUTO_REPLY_ENABLED=false in .env.

Usage: docker exec carbon-backend python scripts/reimport_emails.py [--batch-size 50] [--max-total 5000] [--dry-run]
"""
import asyncio
import argparse
import logging
import re
import sys
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Our email addresses (outbound detection)
OUR_EMAILS = {
    "atendimento@carbonsmartwatch.com.br",
    "suporte@carbonsmartwatch.com.br",
    "pedro@carbonsmartwatch.com.br",
    "victor@carbonsmartwatch.com.br",
    "tauane@carbonsmartwatch.com.br",
    "luana@carbonsmartwatch.com.br",
    "daniele@carbonsmartwatch.com.br",
    "lyvia@carbonsmartwatch.com.br",
    "taxas@carbonsmartwatch.com.br",
}

SPAM_KEYWORDS = [
    "sefaz", "bounce", "mailer-daemon", "noreply@", "no-reply@",
    "meta-verified", "newsletter", "marketing@", "promo@",
    "notification@facebookmail", "amazonses",
]


def _is_our_email(email: str) -> bool:
    return email.lower().strip() in OUR_EMAILS or "carbonsmartwatch.com.br" in email.lower()


def _is_spam(from_email: str, subject: str) -> bool:
    combined = (from_email + " " + subject).lower()
    return any(s in combined for s in SPAM_KEYWORDS)


def _parse_from(from_header: str) -> tuple[str, str]:
    # Try "Name <email>" format first (angle brackets required)
    match = re.match(r'"?([^"<]+)"?\s*<([^>]+)>', from_header)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    # Bare email address (no angle brackets)
    email = from_header.strip().strip('"')
    return email, email


async def reimport(batch_size: int = 50, max_total: int = 5000, dry_run: bool = False):
    from app.services.gmail_service import get_gmail_service, _extract_body
    try:
        from app.services.gmail_service import _clean_html
    except ImportError:
        from html import unescape
        import re as _re
        def _clean_html(html: str) -> str:
            text = _re.sub(r'<[^>]+>', ' ', html)
            return unescape(text).strip()
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text, select
    from app.core.config import settings
    from app.models.message import Message
    from app.models.ticket import Ticket
    from app.models.customer import Customer

    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    service = get_gmail_service()
    if not service:
        logger.error("Gmail service not available")
        return

    # ── Phase 1: Collect all threads from inbox ──
    logger.info("Phase 1: Collecting message IDs from inbox...")
    all_msg_ids = []
    page_token = None
    while len(all_msg_ids) < max_total:
        fetch_size = min(500, max_total - len(all_msg_ids))
        kwargs = {"userId": "me", "q": "in:inbox OR in:sent", "maxResults": fetch_size}
        if page_token:
            kwargs["pageToken"] = page_token
        result = service.users().messages().list(**kwargs).execute()
        msgs = result.get("messages", [])
        if not msgs:
            break
        all_msg_ids.extend(msgs)
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    logger.info(f"Found {len(all_msg_ids)} messages total")

    if dry_run:
        logger.info("DRY RUN — would process up to %d messages", len(all_msg_ids))
        return

    # ── Phase 2: Group by thread ──
    logger.info("Phase 2: Fetching and grouping by thread...")
    threads = defaultdict(list)  # thread_id -> [email_data]
    fetched = 0
    fetch_errors = 0

    for i in range(0, len(all_msg_ids), batch_size):
        batch = all_msg_ids[i:i + batch_size]
        for msg_ref in batch:
            msg_id = msg_ref["id"]
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()

                headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
                body_text, body_html = _extract_body(msg["payload"])

                if not body_text and body_html:
                    body_text = _clean_html(body_html)

                if not body_text:
                    continue

                from_name, from_email = _parse_from(headers.get("from", ""))

                # Skip spam
                if _is_spam(from_email, headers.get("subject", "")):
                    continue

                # Skip RA notification emails
                if "reclameaqui.com" in from_email.lower():
                    continue

                thread_id = msg.get("threadId", msg_id)

                # Parse date
                email_date = None
                try:
                    email_date = parsedate_to_datetime(headers.get("date", ""))
                except Exception:
                    email_date = datetime.now(timezone.utc)

                threads[thread_id].append({
                    "gmail_id": msg_id,
                    "thread_id": thread_id,
                    "subject": headers.get("subject", "(sem assunto)"),
                    "from_name": from_name,
                    "from_email": from_email,
                    "body_text": body_text,
                    "body_html": body_html,
                    "date": email_date,
                    "message_id": headers.get("message-id"),
                    "in_reply_to": headers.get("in-reply-to"),
                    "references": headers.get("references"),
                    "is_outbound": _is_our_email(from_email),
                })
                fetched += 1
            except Exception as e:
                logger.warning(f"Failed to fetch message {msg_id}: {e}")
                fetch_errors += 1

        logger.info(f"Fetched {fetched}/{len(all_msg_ids)} messages ({len(threads)} threads)")

    # Sort messages within each thread by date
    for thread_id in threads:
        threads[thread_id].sort(key=lambda x: x["date"] or datetime.min.replace(tzinfo=timezone.utc))

    logger.info(f"Phase 2 done: {len(threads)} threads, {fetched} messages, {fetch_errors} errors")

    # ── Phase 3: Create tickets ──
    logger.info("Phase 3: Creating tickets...")
    created_tickets = 0
    created_messages = 0
    skipped_threads = 0

    async with SessionLocal() as db:
        # Check existing messages
        existing = await db.execute(
            text("SELECT gmail_message_id FROM messages WHERE gmail_message_id IS NOT NULL")
        )
        existing_ids = {row[0] for row in existing.fetchall()}
        logger.info(f"Already in DB: {len(existing_ids)} messages")

        batch_count = 0
        for thread_id, messages in threads.items():
            # Filter out already-imported messages
            new_messages = [m for m in messages if m["gmail_id"] not in existing_ids]
            if not new_messages:
                skipped_threads += 1
                continue

            # Find the first inbound message (customer) to create the ticket
            inbound_msgs = [m for m in messages if not m["is_outbound"]]
            outbound_msgs = [m for m in messages if m["is_outbound"]]

            if not inbound_msgs:
                # Thread with only our outbound messages — skip
                skipped_threads += 1
                continue

            first_inbound = inbound_msgs[0]
            customer_email = first_inbound["from_email"].lower().strip()

            # Find or create customer
            cust_result = await db.execute(
                select(Customer).where(Customer.email == customer_email)
            )
            customer = cust_result.scalars().first()
            if not customer:
                customer = Customer(
                    name=first_inbound["from_name"],
                    email=customer_email,
                )
                db.add(customer)
                await db.flush()

            # Check if ticket already exists for this thread
            existing_ticket_result = await db.execute(
                select(Ticket).join(Message).where(Message.gmail_thread_id == thread_id)
            )
            ticket = existing_ticket_result.scalars().first()

            if not ticket:
                # Create new ticket
                from app.services.ticket_number import get_next_ticket_number
                next_num = await get_next_ticket_number(db)

                from app.core.config import settings as cfg
                sla_deadline = datetime.now(timezone.utc) + timedelta(hours=cfg.SLA_MEDIUM_HOURS)

                ticket = Ticket(
                    number=next_num,
                    subject=first_inbound["subject"][:500],
                    status="open",
                    priority="medium",
                    customer_id=customer.id,
                    source="gmail",
                    sla_deadline=sla_deadline,
                    received_at=first_inbound["date"] or datetime.now(timezone.utc),
                )
                db.add(ticket)
                await db.flush()

                # AI Triage (no auto-reply)
                try:
                    from app.services.ai_service import triage_ticket as ai_triage, apply_triage_results
                    triage = await ai_triage(
                        subject=first_inbound["subject"],
                        body=first_inbound["body_text"][:2000],
                        customer_name=first_inbound["from_name"],
                        is_repeat=False,
                    )
                    apply_triage_results(ticket, triage, customer=customer)
                except Exception as e:
                    logger.warning(f"Triage skipped for ticket #{next_num}: {e}")

                created_tickets += 1

            # Add all messages to this ticket
            for email_data in new_messages:
                if email_data["gmail_id"] in existing_ids:
                    continue

                msg = Message(
                    ticket_id=ticket.id,
                    type="outbound" if email_data["is_outbound"] else "inbound",
                    sender_name=email_data["from_name"],
                    sender_email=email_data["from_email"],
                    body_text=email_data["body_text"],
                    body_html=email_data.get("body_html"),
                    gmail_message_id=email_data["gmail_id"],
                    gmail_thread_id=thread_id,
                    email_message_id=email_data.get("message_id"),
                    email_references=email_data.get("references"),
                )
                db.add(msg)
                existing_ids.add(email_data["gmail_id"])
                created_messages += 1

            # ── Determine ticket status based on thread content ──
            has_our_reply = len(outbound_msgs) > 0
            last_msg = messages[-1]
            last_is_ours = last_msg["is_outbound"]

            if has_our_reply and last_is_ours:
                # We replied last → waiting for customer
                ticket.status = "waiting"
                ticket.first_response_at = outbound_msgs[0]["date"]
                ticket.auto_replied = True
            elif has_our_reply and not last_is_ours:
                # Customer replied after us → open (needs attention)
                ticket.status = "open"
                ticket.first_response_at = outbound_msgs[0]["date"]
            else:
                # No reply from us → open
                ticket.status = "open"

            # Commit every N threads to avoid huge transactions
            batch_count += 1
            if batch_count % 100 == 0:
                await db.commit()
                logger.info(f"Progress: {created_tickets} tickets, {created_messages} messages")

        await db.commit()

    logger.info(f"""
=== REIMPORT COMPLETE ===
Threads processed: {len(threads)}
Threads skipped (already imported): {skipped_threads}
Tickets created: {created_tickets}
Messages created: {created_messages}
Fetch errors: {fetch_errors}
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=50, help="Messages per Gmail API batch")
    parser.add_argument("--max-total", type=int, default=5000, help="Max messages to fetch from Gmail")
    parser.add_argument("--dry-run", action="store_true", help="Only count, don't import")
    args = parser.parse_args()
    asyncio.run(reimport(batch_size=args.batch_size, max_total=args.max_total, dry_run=args.dry_run))
