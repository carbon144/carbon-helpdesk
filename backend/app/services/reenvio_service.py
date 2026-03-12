"""Reenvio detection, limit checking, draft order creation, and Slack notification."""
from __future__ import annotations
import logging
from datetime import datetime, timezone, date

from app.core.config import settings
from app.services.slack_service import send_slack_message

logger = logging.getLogger(__name__)

REENVIO_KEYWORDS = [
    "reenvio", "reenviar", "novo envio", "enviar novamente",
    "reenviei", "providenciei o reenvio", "reenvio sem custo",
    "novo pedido de reenvio", "reenvio imediato",
    "providenciar o reenvio", "seguir com o reenvio",
]

# Dias permitidos para reenvio: Segunda(0), Quarta(2), Sexta(4)
DIAS_REENVIO = {0, 2, 4}


def detect_reenvio(reply_text: str, category: str | None = None) -> bool:
    """Detect if an AI reply mentions reenvio actions."""
    if not reply_text:
        return False
    text_lower = reply_text.lower()
    for kw in REENVIO_KEYWORDS:
        if kw in text_lower:
            return True
    return False


async def check_reenvio_limit(db) -> dict:
    """Check if reenvio is allowed today.
    1. Must be a reenvio day (Mon/Wed/Fri)
    2. Must not exceed MAX_REENVIOS_DIA
    """
    from sqlalchemy import select, func
    from app.models.ticket import Ticket

    today = date.today()
    weekday = today.weekday()

    if weekday not in DIAS_REENVIO:
        dia_names = {0: "segunda", 1: "terca", 2: "quarta", 3: "quinta", 4: "sexta", 5: "sabado", 6: "domingo"}
        next_reenvio = None
        for d in sorted(DIAS_REENVIO):
            if d > weekday:
                next_reenvio = dia_names[d]
                break
        if not next_reenvio:
            next_reenvio = dia_names[min(DIAS_REENVIO)]

        return {
            "allowed": False,
            "count": 0,
            "max": settings.MAX_REENVIOS_DIA,
            "reason": "dia_nao_permitido",
            "message": f"Reenvios so acontecem em Seg/Qua/Sex. Proximo dia: {next_reenvio}.",
        }

    # Count reenvios today by checking tickets with tag "reenvio-ia" created today
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)

    result = await db.execute(
        select(func.count()).select_from(Ticket).where(
            Ticket.tags.contains(["reenvio-ia"]),
            Ticket.updated_at >= today_start,
            Ticket.updated_at <= today_end,
        )
    )
    count = result.scalar() or 0
    max_limit = settings.MAX_REENVIOS_DIA

    if count >= max_limit:
        return {
            "allowed": False,
            "count": count,
            "max": max_limit,
            "reason": "limite_diario",
            "message": f"Limite de {max_limit} reenvios/dia atingido ({count}/{max_limit}).",
        }

    return {
        "allowed": True,
        "count": count,
        "max": max_limit,
        "reason": None,
        "message": None,
    }


async def create_reenvio_draft_order(order_data: dict) -> dict:
    """Create a Shopify draft order for reenvio."""
    from app.services.shopify_service import create_draft_order
    return await create_draft_order(order_data, note="Reenvio IA")


async def notify_reenvio_slack(
    ticket,
    order_data: dict | None,
    draft_result: dict,
    limit_info: dict | None = None,
) -> dict | None:
    """Post reenvio notification to #ia-estornos Slack channel."""
    channel = settings.SLACK_IA_ESTORNOS_CHANNEL
    if not channel:
        logger.warning("SLACK_IA_ESTORNOS_CHANNEL not configured, skipping reenvio notification")
        return None

    customer_name = ""
    if ticket.customer:
        customer_name = ticket.customer.name or ""

    order_number = ""
    items_str = ""
    address_str = ""
    agent_name = ""

    if order_data:
        order_number = order_data.get("order_number", "")
        items = order_data.get("items", [])
        items_str = ", ".join(
            f"{i.get('title', '?')} x{i.get('quantity', 1)}" for i in items
        ) or "?"
        shipping = order_data.get("shipping_address") or {}
        if shipping:
            address_str = f"{shipping.get('city', '')}, {shipping.get('province', '')}"

    if hasattr(ticket, "ai_agent") and ticket.ai_agent:
        agent_name = ticket.ai_agent.name

    draft_name = draft_result.get("draft_order_name", "?")
    count = limit_info.get("count", "?") if limit_info else "?"
    max_limit = limit_info.get("max", 10) if limit_info else 10

    text = (
        f":package: *REENVIO CRIADO*\n"
        f"*Ticket:* #{ticket.number} | *Cliente:* {customer_name}\n"
        f"*Pedido original:* {order_number} | *Draft:* {draft_name}\n"
        f"*Produtos:* {items_str}\n"
        f"*Endereco:* {address_str}\n"
        f"*Agente IA:* {agent_name}\n"
        f"[{count}/{max_limit} reenvios hoje]"
    )

    return await send_slack_message(channel, text)
