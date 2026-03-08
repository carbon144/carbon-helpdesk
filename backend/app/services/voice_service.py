"""Voice AI Carol — tool handlers for Vapi webhook integration.

Each handler translates a Vapi tool call into existing service calls
and returns plain text optimized for TTS (no emojis, no markdown).
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy import func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.models.voice_call import VoiceCall
from app.services import shopify_service, tracking_service, troque_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Lookup order
# ---------------------------------------------------------------------------

async def handle_lookup_order(args: dict) -> str:
    """Look up a Shopify order by number. Returns TTS-friendly text."""
    order_number = args.get("order_number", "").strip()
    if not order_number:
        return "Desculpe, nao consegui identificar o numero do pedido. Pode repetir, por favor?"

    try:
        result = await shopify_service.get_order_by_number(order_number)
    except Exception as exc:
        logger.error("voice handle_lookup_order error: %s", exc)
        return "Desculpe, tive um problema ao buscar seu pedido. Pode tentar novamente em instantes?"

    if "error" in result:
        return f"Nao encontrei nenhum pedido com o numero {order_number}. Verifique o numero e tente novamente."

    # Build TTS response
    status_map = {
        "paid": "pago",
        "pending": "pendente",
        "refunded": "reembolsado",
        "partially_refunded": "parcialmente reembolsado",
        "voided": "cancelado",
        "authorized": "autorizado",
    }
    delivery_map = {
        "pending": "aguardando envio",
        "shipped": "enviado",
        "in_transit": "em transito",
        "out_for_delivery": "saiu para entrega",
        "delivered": "entregue",
    }

    financial = status_map.get(result.get("financial_status", ""), result.get("financial_status", "desconhecido"))
    delivery = delivery_map.get(result.get("delivery_status", ""), result.get("delivery_status", "desconhecido"))

    items = result.get("items", [])
    items_text = ""
    if items:
        names = [it.get("title", "item") for it in items[:3]]
        items_text = ", ".join(names)
        if len(items) > 3:
            items_text += f" e mais {len(items) - 3} itens"

    parts = [
        f"Encontrei o pedido numero {result.get('order_number', order_number)}.",
        f"Status do pagamento: {financial}.",
        f"Status da entrega: {delivery}.",
    ]

    tracking = result.get("tracking_code")
    if tracking:
        parts.append(f"Codigo de rastreio: {tracking}.")

    if items_text:
        parts.append(f"Itens: {items_text}.")

    total = result.get("total_price")
    if total:
        parts.append(f"Valor total: {total} reais.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# 2. Lookup tracking
# ---------------------------------------------------------------------------

async def handle_lookup_tracking(args: dict) -> str:
    """Track a package by tracking code. Returns TTS-friendly text."""
    code = args.get("tracking_code", "").strip()
    if not code:
        return "Desculpe, nao consegui identificar o codigo de rastreio. Pode repetir, por favor?"

    try:
        result = await tracking_service.track_package(code)
    except Exception as exc:
        logger.error("voice handle_lookup_tracking error: %s", exc)
        return "Desculpe, tive um problema ao rastrear seu pacote. Pode tentar novamente?"

    status = result.get("status", "desconhecido")
    delivered = result.get("delivered", False)

    if delivered:
        parts = [f"O pacote com codigo {code} ja foi entregue."]
    else:
        parts = [f"O pacote com codigo {code} esta com status: {status}."]

    carrier = result.get("carrier", "")
    if carrier and carrier != "unknown":
        parts.append(f"Transportadora: {carrier}.")

    events = result.get("events", [])
    if events:
        last = events[0]
        desc = last.get("description", "")
        date = last.get("date", "")
        if desc:
            parts.append(f"Ultima atualizacao: {desc}.")
        if date:
            parts.append(f"Data: {date}.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# 3. Lookup troque (reversals)
# ---------------------------------------------------------------------------

async def handle_lookup_troque(args: dict) -> str:
    """Look up TroqueCommerce reversals by order number or phone."""
    order_number = args.get("order_number", "").strip()
    phone = args.get("phone", "").strip()

    if not order_number and not phone:
        return "Preciso do numero do pedido ou do seu telefone para consultar a troca. Pode informar?"

    try:
        if order_number:
            reversals = await troque_service.search_by_order_number(order_number)
        else:
            reversals = await troque_service.search_by_phone(phone)
    except Exception as exc:
        logger.error("voice handle_lookup_troque error: %s", exc)
        return "Desculpe, tive um problema ao consultar sua solicitacao de troca. Pode tentar novamente?"

    if not reversals:
        identifier = f"pedido {order_number}" if order_number else f"telefone informado"
        return f"Nao encontrei nenhuma solicitacao de troca para o {identifier}."

    status_map = {
        "Em Análise": "em analise pelo nosso time",
        "Aprovado": "aprovada, aguardando envio do produto",
        "Aguardando Envio": "aguardando voce enviar o produto",
        "Enviado": "produto enviado, aguardando recebimento",
        "Recebido": "produto recebido, processando troca ou reembolso",
        "Finalizado": "finalizada com sucesso",
        "Cancelado": "cancelada",
        "Reprovado": "reprovada",
    }

    if len(reversals) == 1:
        r = reversals[0]
        status_raw = r.get("status", "desconhecido")
        status_text = status_map.get(status_raw, status_raw)
        order_ref = r.get("ecommerce_number", order_number or "")
        rtype = r.get("reverse_type", "")
        type_text = f" do tipo {rtype}" if rtype else ""
        return (
            f"Encontrei uma solicitacao{type_text} para o pedido {order_ref}. "
            f"Status atual: {status_text}."
        )

    # Multiple reversals
    parts = [f"Encontrei {len(reversals)} solicitacoes de troca."]
    for i, r in enumerate(reversals[:3], 1):
        status_raw = r.get("status", "desconhecido")
        status_text = status_map.get(status_raw, status_raw)
        order_ref = r.get("ecommerce_number", "")
        parts.append(f"Solicitacao {i}, pedido {order_ref}: {status_text}.")

    if len(reversals) > 3:
        parts.append(f"E mais {len(reversals) - 3} solicitacoes.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# 4. Create ticket (needs db)
# ---------------------------------------------------------------------------

async def handle_create_ticket(db: AsyncSession, args: dict) -> str:
    """Create a support ticket from a voice call. Returns confirmation text."""
    subject = args.get("subject", "Chamada telefonica").strip()
    description = args.get("description", "").strip()
    caller_phone = args.get("caller_phone", "").strip()
    customer_id = args.get("customer_id")
    priority = args.get("priority", "medium")

    if priority not in ("low", "medium", "high", "urgent"):
        priority = "medium"

    try:
        # Get next ticket number
        max_num = await db.execute(select(sqlfunc.max(Ticket.number)))
        next_number = (max_num.scalar() or 0) + 1

        ticket = Ticket(
            number=next_number,
            subject=subject,
            status="open",
            priority=priority,
            source="phone",
            customer_id=customer_id,
            tags=["voice-ai", "carol"],
        )
        db.add(ticket)
        await db.flush()

        logger.info("Voice ticket created: #%s (id=%s)", ticket.number, ticket.id)
        return (
            f"Pronto, criei o chamado numero {ticket.number} para voce. "
            f"Nossa equipe vai analisar e retornar em ate 48 horas. "
            f"Guarde o numero {ticket.number} como referencia."
        )
    except Exception as exc:
        logger.error("voice handle_create_ticket error: %s", exc)
        return "Desculpe, tive um problema ao criar seu chamado. Por favor, tente novamente pelo nosso WhatsApp."


# ---------------------------------------------------------------------------
# 5. Save call record (end-of-call)
# ---------------------------------------------------------------------------

async def save_call_record(db: AsyncSession, data: dict) -> VoiceCall:
    """Persist end-of-call data from Vapi into the voice_calls table."""
    call = VoiceCall(
        id=str(uuid.uuid4()),
        vapi_call_id=data.get("call_id", str(uuid.uuid4())),
        caller_phone=data.get("caller_phone"),
        duration_seconds=data.get("duration_seconds", 0),
        recording_url=data.get("recording_url"),
        transcript=data.get("transcript"),
        summary=data.get("summary"),
        ended_reason=data.get("ended_reason"),
        ticket_id=data.get("ticket_id"),
        conversation_id=data.get("conversation_id"),
    )
    db.add(call)
    await db.flush()
    logger.info("Voice call saved: vapi_id=%s, duration=%.0fs", call.vapi_call_id, call.duration_seconds)
    return call


# ---------------------------------------------------------------------------
# 6. Tool handler registry
# ---------------------------------------------------------------------------

TOOL_HANDLERS = {
    "lookup_order": handle_lookup_order,
    "lookup_tracking": handle_lookup_tracking,
    "lookup_troque": handle_lookup_troque,
    "create_ticket": handle_create_ticket,
}
