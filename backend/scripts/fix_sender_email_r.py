"""Fix messages with sender_email='r' (or single char) caused by broken _parse_from regex.

Re-fetches the From header from Gmail API for each affected message and updates sender_email + sender_name.

Usage: docker exec carbon-backend python -m scripts.fix_sender_email_r [--dry-run]
"""
import asyncio
import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from app.core.database import async_session
from app.models.message import Message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def _extract_email(from_header: str) -> str:
    import re
    match = re.search(r"<([^>]+)>", from_header)
    email = match.group(1) if match else from_header.strip()
    if "@" not in email:
        email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', from_header)
        if email_match:
            return email_match.group(0)
    return email


def _extract_name(from_header: str) -> str:
    import re
    match = re.match(r"^([^<]+)", from_header)
    name = match.group(1).strip().strip('"') if match else ""
    return name or _extract_email(from_header)


async def fix_sender_emails(dry_run: bool = False):
    from app.services.gmail_service import get_gmail_service

    service = get_gmail_service()
    if not service:
        logger.error("Gmail service not available")
        return

    async with async_session() as db:
        # Find all messages with truncated sender_email (single char or no @)
        result = await db.execute(
            text("""
                SELECT id, gmail_message_id, sender_email, sender_name
                FROM messages
                WHERE gmail_message_id IS NOT NULL
                  AND sender_email IS NOT NULL
                  AND (length(sender_email) <= 2 OR sender_email NOT LIKE '%%@%%')
                ORDER BY created_at DESC
            """)
        )
        rows = result.fetchall()
        logger.info(f"Found {len(rows)} messages with truncated sender_email")

        fixed = 0
        failed = 0
        for row in rows:
            msg_id, gmail_msg_id, old_email, old_name = row
            try:
                # Fetch message metadata from Gmail
                msg = service.users().messages().get(
                    userId="me", id=gmail_msg_id, format="metadata",
                    metadataHeaders=["From"]
                ).execute()

                from_header = None
                for header in msg.get("payload", {}).get("headers", []):
                    if header["name"].lower() == "from":
                        from_header = header["value"]
                        break

                if not from_header:
                    logger.warning(f"  [{msg_id}] No From header in Gmail msg {gmail_msg_id}")
                    failed += 1
                    continue

                new_email = _extract_email(from_header)
                new_name = _extract_name(from_header)

                if "@" not in new_email:
                    logger.warning(f"  [{msg_id}] Still invalid after re-extract: {new_email!r} from {from_header!r}")
                    failed += 1
                    continue

                logger.info(f"  [{msg_id}] {old_email!r} -> {new_email!r} (name: {old_name!r} -> {new_name!r})")

                if not dry_run:
                    await db.execute(
                        text("UPDATE messages SET sender_email = :email, sender_name = :name WHERE id = :id"),
                        {"email": new_email, "name": new_name, "id": msg_id}
                    )
                fixed += 1

            except Exception as e:
                logger.warning(f"  [{msg_id}] Gmail fetch failed for {gmail_msg_id}: {e}")
                failed += 1

        if not dry_run:
            await db.commit()

        logger.info(f"Done. Fixed: {fixed}, Failed: {failed}, Total: {len(rows)}")
        if dry_run:
            logger.info("(DRY RUN — no changes written)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(fix_sender_emails(dry_run=args.dry_run))
