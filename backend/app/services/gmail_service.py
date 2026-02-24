"""Gmail integration service for Carbon Expert Hub."""
from __future__ import annotations
import base64
import logging
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_gmail_credentials() -> Credentials | None:
    """Build Gmail credentials from refresh token."""
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_REFRESH_TOKEN:
        return None

    creds = Credentials(
        token=None,
        refresh_token=settings.GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GMAIL_CLIENT_ID,
        client_secret=settings.GMAIL_CLIENT_SECRET,
        scopes=SCOPES,
    )

    try:
        creds.refresh(GoogleRequest())
        return creds
    except Exception as e:
        logger.error(f"Failed to refresh Gmail credentials: {e}")
        return None


def get_gmail_service():
    """Get Gmail API service."""
    creds = get_gmail_credentials()
    if not creds:
        return None
    return build("gmail", "v1", credentials=creds)


def fetch_new_emails(after_timestamp: int | None = None, max_results: int = 20, include_read: bool = False) -> list[dict]:
    """Fetch emails from Gmail inbox."""
    service = get_gmail_service()
    if not service:
        return []

    try:
        query = "in:inbox" if include_read else "is:unread in:inbox"
        if after_timestamp:
            query += f" after:{after_timestamp}"

        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        emails = []

        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()

            headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}

            # Extract body
            body_text = ""
            body_html = ""
            payload = msg["payload"]

            if "parts" in payload:
                for part in payload["parts"]:
                    mime = part.get("mimeType", "")
                    data = part.get("body", {}).get("data", "")
                    if data:
                        decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                        if mime == "text/plain":
                            body_text = decoded
                        elif mime == "text/html":
                            body_html = decoded
            else:
                data = payload.get("body", {}).get("data", "")
                if data:
                    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    if payload.get("mimeType") == "text/html":
                        body_html = decoded
                    else:
                        body_text = decoded

            # Clean body text from HTML if no plain text
            if not body_text and body_html:
                body_text = re.sub(r"<[^>]+>", "", body_html)[:2000]

            emails.append({
                "gmail_id": msg["id"],
                "thread_id": msg.get("threadId"),
                "subject": headers.get("subject", "(Sem assunto)"),
                "from_email": _extract_email(headers.get("from", "")),
                "from_name": _extract_name(headers.get("from", "")),
                "to": headers.get("to", ""),
                "date": headers.get("date", ""),
                "body_text": body_text[:5000],
                "body_html": body_html[:10000] if body_html else None,
                "message_id": headers.get("message-id"),
                "in_reply_to": headers.get("in-reply-to"),
                "references": headers.get("references"),
            })

        return emails
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        return []


def fetch_spam_emails(max_results: int = 50) -> list[dict]:
    """Fetch emails from Gmail SPAM folder."""
    service = get_gmail_service()
    if not service:
        return []

    try:
        query = "in:spam"

        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        emails = []

        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()

            headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}

            # Extract body
            body_text = ""
            body_html = ""
            payload = msg["payload"]

            if "parts" in payload:
                for part in payload["parts"]:
                    mime = part.get("mimeType", "")
                    data = part.get("body", {}).get("data", "")
                    if data:
                        decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                        if mime == "text/plain":
                            body_text = decoded
                        elif mime == "text/html":
                            body_html = decoded
            else:
                data = payload.get("body", {}).get("data", "")
                if data:
                    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    if payload.get("mimeType") == "text/html":
                        body_html = decoded
                    else:
                        body_text = decoded

            # Clean body text from HTML if no plain text
            if not body_text and body_html:
                body_text = re.sub(r"<[^>]+>", "", body_html)[:2000]

            emails.append({
                "gmail_id": msg["id"],
                "thread_id": msg.get("threadId"),
                "subject": headers.get("subject", "(Sem assunto)"),
                "from_email": _extract_email(headers.get("from", "")),
                "from_name": _extract_name(headers.get("from", "")),
                "to": headers.get("to", ""),
                "date": headers.get("date", ""),
                "body_text": body_text[:5000],
                "body_html": body_html[:10000] if body_html else None,
                "snippet": msg.get("snippet", ""),
            })

        return emails
    except Exception as e:
        logger.error(f"Failed to fetch spam emails: {e}")
        return []


def move_from_spam(message_id: str) -> bool:
    """Move an email from SPAM to INBOX (mark as not spam)."""
    service = get_gmail_service()
    if not service:
        return False

    try:
        service.users().messages().modify(
            userId="me", id=message_id,
            body={"removeLabelIds": ["SPAM"], "addLabelIds": ["INBOX"]}
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to move email from spam: {e}")
        return False


def send_email(to: str, subject: str, body_text: str, thread_id: str | None = None, in_reply_to: str | None = None, cc: list[str] | None = None, bcc: list[str] | None = None, attachments: list[dict] | None = None) -> dict | None:
    """Send an email via Gmail API. Supports file attachments."""
    service = get_gmail_service()
    if not service:
        return None

    try:
        if attachments:
            message = MIMEMultipart()
            message.attach(MIMEText(body_text))
            for att in attachments:
                file_path = att.get("file_path")
                if not file_path:
                    continue
                try:
                    from pathlib import Path
                    path = Path(file_path)
                    if not path.exists():
                        continue
                    mime_type = att.get("mime_type", "application/octet-stream")
                    maintype, subtype = mime_type.split("/", 1) if "/" in mime_type else ("application", "octet-stream")
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(path.read_bytes())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", "attachment", filename=att.get("name", path.name))
                    message.attach(part)
                except Exception as e:
                    logger.warning(f"Failed to attach file {att.get('name')}: {e}")
        else:
            message = MIMEText(body_text)

        message["to"] = to
        message["subject"] = subject
        if settings.GMAIL_SUPPORT_EMAIL:
            message["from"] = settings.GMAIL_SUPPORT_EMAIL
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = in_reply_to
        if cc:
            message["Cc"] = ", ".join(cc)
        if bcc:
            message["Bcc"] = ", ".join(bcc)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {"raw": raw}
        if thread_id:
            body["threadId"] = thread_id

        result = service.users().messages().send(userId="me", body=body).execute()
        return {"id": result["id"], "threadId": result.get("threadId")}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return None


def mark_as_read(message_id: str):
    """Mark a Gmail message as read."""
    service = get_gmail_service()
    if not service:
        return

    try:
        service.users().messages().modify(
            userId="me", id=message_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    except Exception as e:
        logger.error(f"Failed to mark email as read: {e}")


def test_gmail_connection() -> dict:
    """Test if Gmail connection is working."""
    if not settings.GMAIL_CLIENT_ID:
        return {"ok": False, "error": "GMAIL_CLIENT_ID não configurado"}
    if not settings.GMAIL_REFRESH_TOKEN:
        return {"ok": False, "error": "GMAIL_REFRESH_TOKEN não configurado"}

    service = get_gmail_service()
    if not service:
        return {"ok": False, "error": "Falha ao conectar com Gmail"}

    try:
        profile = service.users().getProfile(userId="me").execute()
        return {
            "ok": True,
            "email": profile.get("emailAddress"),
            "messages_total": profile.get("messagesTotal"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _extract_email(from_header: str) -> str:
    """Extract email from 'Name <email>' format."""
    match = re.search(r"<([^>]+)>", from_header)
    return match.group(1) if match else from_header.strip()


def _extract_name(from_header: str) -> str:
    """Extract name from 'Name <email>' format."""
    match = re.match(r"^([^<]+)", from_header)
    name = match.group(1).strip().strip('"') if match else ""
    return name or _extract_email(from_header)
