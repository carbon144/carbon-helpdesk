"""Estorno detection, Slack notification, and Google Sheets logging."""
from __future__ import annotations
import logging
import re
from datetime import datetime, timezone

from app.core.config import settings
from app.services.slack_service import send_slack_message

logger = logging.getLogger(__name__)

ESTORNO_KEYWORDS = [
    "estorno", "cancelamento", "reembolso", "dinheiro de volta",
    "devolver valor", "devolver o valor", "devolver o dinheiro",
    "cancelar pedido", "cancelei", "cancela", "estornei",
    "registrei o cancelamento", "registrei o estorno",
    "solicitar estorno", "solicitar cancelamento",
    "reembolsar", "reembolsado",
]


def detect_estorno(reply_text: str, category: str | None = None) -> bool:
    """Detect if an AI reply mentions estorno/cancelamento actions."""
    if not reply_text:
        return False
    text_lower = reply_text.lower()
    # Category hint: financeiro/reclamacao are more likely
    for kw in ESTORNO_KEYWORDS:
        if kw in text_lower:
            return True
    return False


async def notify_estorno_slack(
    ticket,
    order_data: dict | None,
    agent_name: str,
    reply_text: str,
) -> dict | None:
    """Post estorno notification to #ia-estornos Slack channel."""
    channel = settings.SLACK_IA_ESTORNOS_CHANNEL
    if not channel:
        logger.warning("SLACK_IA_ESTORNOS_CHANNEL not configured, skipping estorno notification")
        return None

    customer_name = ""
    customer_email = ""
    if ticket.customer:
        customer_name = ticket.customer.name or ""
        customer_email = ticket.customer.email or ""

    order_number = ""
    total_price = ""
    financial_status = ""
    if order_data:
        order_number = order_data.get("order_number", "")
        total_price = order_data.get("total_price", "")
        financial_status = order_data.get("financial_status", "")

    text = (
        f":moneybag: *ESTORNO PENDENTE*\n"
        f"*Ticket:* #{ticket.number} | *Cliente:* {customer_name}\n"
        f"*Email:* {customer_email}\n"
        f"*Pedido:* {order_number} | *Valor:* R$ {total_price}\n"
        f"*Status pagamento:* {financial_status}\n"
        f"*Agente IA:* {agent_name}\n"
        f":arrow_right: Executar na Appmax"
    )

    return await send_slack_message(channel, text)


async def log_estorno_to_sheet(ticket, order_data: dict | None) -> bool:
    """Log estorno to Google Sheets. Graceful: skips if not configured."""
    sheet_id = settings.GOOGLE_SHEET_ESTORNOS_ID
    sa_json = settings.GOOGLE_SERVICE_ACCOUNT_JSON

    if not sheet_id or not sa_json:
        logger.info("Google Sheets estorno logging skipped (not configured)")
        return False

    try:
        import json
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds_dict = json.loads(sa_json)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        service = build("sheets", "v4", credentials=creds)

        customer_name = ticket.customer.name if ticket.customer else ""
        customer_email = ticket.customer.email if ticket.customer else ""

        order_number = ""
        total_price = ""
        financial_status = ""
        agent_name = ""
        if order_data:
            order_number = order_data.get("order_number", "")
            total_price = order_data.get("total_price", "")
            financial_status = order_data.get("financial_status", "")

        if hasattr(ticket, "ai_agent") and ticket.ai_agent:
            agent_name = ticket.ai_agent.name

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        row = [
            now,
            str(ticket.number),
            order_number,
            customer_name,
            customer_email,
            total_price,
            financial_status,
            "pendente",
            agent_name,
        ]

        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Estornos!A:I",
            valueInputOption="USER_ENTERED",
            body={"values": [row]},
        ).execute()

        logger.info(f"Estorno logged to sheet for ticket #{ticket.number}")
        return True

    except Exception as e:
        logger.error(f"Failed to log estorno to sheet: {e}")
        return False
