"""Message pipeline orchestrator — Chatbot -> AI -> Human handoff."""

import logging
from datetime import datetime, timezone
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.chat_message import ChatMessage
from app.models.kb_article import KBArticle
from app.services.chatbot_engine import ChatbotEngine
from app.services import ai_service
from app.services import chat_routing_service as routing_service

logger = logging.getLogger(__name__)

MAX_AI_ATTEMPTS = 3

_chatbot_engine = ChatbotEngine()

# ── Status maps (Portuguese) ──

DELIVERY_STATUS_PT = {
    "pending": "Pendente",
    "shipped": "Enviado",
    "in_transit": "Em transito",
    "out_for_delivery": "Saiu para entrega",
    "delivered": "Entregue",
    "failed": "Falha na entrega",
}

FINANCIAL_STATUS_PT = {
    "paid": "Pago",
    "pending": "Pendente",
    "refunded": "Reembolsado",
    "partially_refunded": "Parcialmente reembolsado",
    "voided": "Cancelado",
    "authorized": "Autorizado",
    "partially_paid": "Parcialmente pago",
}


async def _search_kb(db: AsyncSession, query: str, limit: int = 3) -> list[KBArticle]:
    pattern = f"%{query}%"
    result = await db.execute(
        select(KBArticle)
        .where(
            KBArticle.is_published.is_(True),
            or_(KBArticle.title.ilike(pattern), KBArticle.content.ilike(pattern)),
        )
        .order_by(KBArticle.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def process_incoming_message(
    db: AsyncSession,
    conversation: Conversation,
    customer: Customer,
    message_text: str,
    visitor_id: str | None = None,
) -> dict:
    result = {
        "handler": conversation.handler or "chatbot",
        "bot_messages": [],
        "interactive_messages": [],
        "escalated": False,
    }

    # Layer 0: If agent is in control and AI is off, skip everything
    if conversation.handler == "agent" and not conversation.ai_enabled:
        return result

    # Layer 1: Chatbot flows
    if conversation.handler in ("chatbot", None):
        chatbot_result = await _chatbot_engine.process_message(
            db, conversation, message_text, visitor_id=visitor_id,
        )

        if chatbot_result and chatbot_result.get("matched"):
            responses = chatbot_result.get("responses", [])
            for resp in responses:
                resp_type = resp.get("type")

                if resp_type == "transfer_to_agent":
                    # Save collected data for the agent to see
                    collected = resp.get("collected_data")
                    if collected:
                        meta = conversation.metadata_ or {}
                        meta["collected_by_bot"] = collected
                        conversation.metadata_ = meta
                    return await _escalate_to_agent(
                        db, conversation, result,
                        escalation_message=resp.get("message", "Transferindo para um atendente..."),
                    )

                if resp_type == "send_message":
                    content = resp.get("content", "")
                    if content:
                        result["bot_messages"].append(content)
                        await _save_bot_message(db, conversation, content)

                elif resp_type == "send_menu":
                    content = resp.get("content", "")
                    options = resp.get("options", [])
                    # Send the text prompt as a bot message too
                    if content:
                        result["bot_messages"].append(content)
                        await _save_bot_message(db, conversation, content)
                    # Add interactive message for channel adapters
                    if options:
                        result["interactive_messages"].append({
                            "type": "menu",
                            "content": content,
                            "options": options,
                        })

                elif resp_type == "collect_input":
                    content = resp.get("content", "")
                    if content:
                        result["bot_messages"].append(content)
                        await _save_bot_message(db, conversation, content)

                elif resp_type == "lookup_order":
                    collected_data = resp.get("collected_data", {})
                    order_field = resp.get("order_field", "order_number")
                    lookup_msgs = await _handle_order_lookup(
                        customer, collected_data, order_field,
                    )
                    for msg in lookup_msgs:
                        result["bot_messages"].append(msg)
                        await _save_bot_message(db, conversation, msg)

            if result["bot_messages"] or result["interactive_messages"]:
                result["handler"] = "chatbot"
                await db.commit()
                return result

        # No chatbot match — fall through to AI
        conversation.handler = "ai"

    # Layer 2: AI auto-reply
    if conversation.handler == "ai" and conversation.ai_enabled:
        kb_articles = []
        try:
            articles = await _search_kb(db, message_text, limit=3)
            kb_articles = [{"title": a.title, "content": a.content} for a in articles]
        except Exception:
            logger.warning("KB search failed, continuing without KB context")

        messages_history = await _build_history(db, conversation)
        messages_history.append({"role": "contact", "content": message_text})

        shopify_data = getattr(customer, "shopify_data", None)

        ai_result = await ai_service.chat_auto_reply(
            messages=messages_history,
            contact_shopify_data=shopify_data,
            kb_articles=kb_articles if kb_articles else None,
        )

        if ai_result["resolved"]:
            conversation.ai_attempts = 0
            result["handler"] = "ai"
            result["bot_messages"].append(ai_result["response"])
            await _save_bot_message(db, conversation, ai_result["response"])
            await db.commit()
            return result
        else:
            conversation.ai_attempts = (conversation.ai_attempts or 0) + 1
            await db.commit()

            if conversation.ai_attempts >= MAX_AI_ATTEMPTS:
                return await _escalate_to_agent(db, conversation, result)
            else:
                if ai_result["response"]:
                    result["handler"] = "ai"
                    result["bot_messages"].append(ai_result["response"])
                    await _save_bot_message(db, conversation, ai_result["response"])
                await db.commit()
                return result

    return result


# ── Order lookup helpers ──

async def _handle_order_lookup(
    customer: Customer,
    collected_data: dict,
    order_field: str,
) -> list[str]:
    """Perform real Shopify order lookup and return formatted messages."""
    from app.services import shopify_service

    messages = []

    # Try by order number first (from collected data)
    order_number = collected_data.get(order_field) or collected_data.get("order_number") or collected_data.get("pedido")
    if order_number:
        order = await shopify_service.get_order_by_number(order_number)
        if order and not order.get("error"):
            messages.append(_format_order_detail(order))
            return messages
        elif order and order.get("error"):
            messages.append(f"Nao encontrei o pedido {order_number}. Verifique o numero e tente novamente.")
            return messages

    # Fallback: try by customer email
    email = getattr(customer, "email", None)
    if email:
        result = await shopify_service.get_orders_by_email(email, limit=5)
        orders = result.get("orders", [])
        if orders:
            messages.append(_format_orders_list(orders))
            return messages

    messages.append("Nao encontrei pedidos associados. Pode informar o numero do pedido? (ex: #12345)")
    return messages


def _format_order_detail(order: dict) -> str:
    """Format a single order into a readable message."""
    number = order.get("order_number", "?")
    financial = FINANCIAL_STATUS_PT.get(order.get("financial_status", ""), order.get("financial_status", ""))
    delivery = DELIVERY_STATUS_PT.get(order.get("delivery_status", ""), order.get("delivery_status", ""))
    total = order.get("total_price", "0.00")
    tracking = order.get("tracking_code", "")
    carrier = order.get("carrier", "")

    items_list = order.get("items", [])
    items_text = ""
    if items_list:
        lines = []
        for item in items_list[:5]:
            qty = item.get("quantity", 1)
            title = item.get("title", "")
            variant = item.get("variant_title", "")
            line = f"  - {qty}x {title}"
            if variant:
                line += f" ({variant})"
            lines.append(line)
        items_text = "\n".join(lines)

    msg = f"Pedido {number}\n"
    msg += f"Pagamento: {financial}\n"
    msg += f"Entrega: {delivery}\n"
    msg += f"Valor: R$ {total}\n"

    if items_text:
        msg += f"Itens:\n{items_text}\n"

    if tracking:
        msg += f"Rastreio: {tracking}"
        if carrier:
            msg += f" ({carrier})"
        msg += "\n"

    return msg.strip()


def _format_orders_list(orders: list[dict]) -> str:
    """Format a list of orders into a summary message."""
    lines = ["Encontrei seus pedidos recentes:\n"]
    for o in orders[:5]:
        number = o.get("order_number", "?")
        financial = FINANCIAL_STATUS_PT.get(o.get("financial_status", ""), o.get("financial_status", ""))
        delivery = DELIVERY_STATUS_PT.get(o.get("delivery_status", ""), o.get("delivery_status", ""))
        total = o.get("total_price", "0.00")
        lines.append(f"  {number} — R$ {total} — {financial} — {delivery}")
    lines.append("\nEnvie o numero do pedido para ver os detalhes.")
    return "\n".join(lines)


# ── Escalation + helpers ──

async def _escalate_to_agent(
    db: AsyncSession,
    conversation: Conversation,
    result: dict,
    escalation_message: str = "Vou transferir voce para um de nossos atendentes. Um momento, por favor.",
) -> dict:
    conversation.handler = "agent"
    conversation.ai_enabled = False
    conversation.ai_attempts = 0

    await routing_service.auto_assign(db, conversation)

    system_msg = ChatMessage(
        conversation_id=conversation.id,
        sender_type="system",
        sender_id=None,
        content_type="text",
        content="Conversa transferida para atendimento humano.",
    )
    db.add(system_msg)

    result["bot_messages"].append(escalation_message)
    await _save_bot_message(db, conversation, escalation_message)

    await db.commit()

    result["handler"] = "agent"
    result["escalated"] = True
    return result


async def _save_bot_message(db: AsyncSession, conversation: Conversation, content: str):
    now = datetime.now(timezone.utc)
    msg = ChatMessage(
        conversation_id=conversation.id,
        sender_type="bot",
        sender_id=None,
        content_type="text",
        content=content,
        created_at=now,
    )
    db.add(msg)
    conversation.last_message_at = now


async def _build_history(db: AsyncSession, conversation: Conversation) -> list[dict]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id, ChatMessage.content_type != "note")
        .order_by(ChatMessage.created_at.asc())
        .limit(20)
    )
    history = []
    for msg in result.scalars().all():
        role = "contact" if msg.sender_type == "contact" else "agent"
        history.append({"role": role, "content": msg.content})
    return history
