"""Message pipeline orchestrator — Chatbot -> AI -> Human handoff."""

import logging
from datetime import datetime, timezone
from sqlalchemy import select, or_, case, literal
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


def _extract_order_number(text: str) -> str | None:
    """Extract order number from text like '#126338', '126338', 'pedido 126338'."""
    import re
    text = text.strip()
    # Direct number with optional #
    m = re.match(r'^#?(\d{4,7})$', text)
    if m:
        return m.group(1)
    # "pedido 126338" or "pedido #126338"
    m = re.search(r'pedido\s*#?(\d{4,7})', text, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def _extract_email(text: str) -> str | None:
    """Extract email address from message text."""
    import re
    text = text.strip()
    m = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if m:
        return m.group(0).lower()
    return None


def _is_bot_looping(conversation, new_message: str, threshold: int = 2) -> bool:
    """Detect if bot is repeating the same message (loop). Returns True if looping."""
    meta = getattr(conversation, "metadata_", None) or {}
    recent = meta.get("_recent_bot_msgs", [])
    # Count how many of the last N messages are identical to this one
    count = sum(1 for m in recent[-3:] if m == new_message)
    return count >= threshold


def _track_bot_message(conversation, message: str):
    """Track bot message in metadata for loop detection."""
    from sqlalchemy.orm.attributes import flag_modified
    meta = dict(getattr(conversation, "metadata_", None) or {})
    recent = meta.get("_recent_bot_msgs", [])
    recent.append(message)
    # Keep only last 5
    meta["_recent_bot_msgs"] = recent[-5:]
    conversation.metadata_ = meta
    flag_modified(conversation, "metadata_")

def _is_business_hours() -> tuple[bool, str]:
    """Check if current time is within business hours (Mon-Fri 9h-18h BRT).
    Returns (is_open, message)."""
    from datetime import timezone, timedelta
    BRT = timezone(timedelta(hours=-3))
    now = datetime.now(BRT)
    weekday = now.weekday()  # 0=Mon, 6=Sun
    hour = now.hour

    if weekday >= 5:  # Saturday or Sunday
        day_name = "sábado" if weekday == 5 else "domingo"
        return False, (
            f"Hoje é {day_name}, estamos fora do horário de atendimento.\n"
            f"Nosso time atende de *segunda a sexta, das 9h às 18h*.\n\n"
            f"Sua mensagem ficou registrada e será respondida no próximo dia útil."
        )
    elif hour < 9:
        return False, (
            f"Nosso atendimento começa às *9h* (faltam {9 - hour}h).\n"
            f"Horário: *segunda a sexta, 9h às 18h*.\n\n"
            f"Sua mensagem ficou registrada e será respondida assim que abrirmos."
        )
    elif hour >= 18:
        return False, (
            f"Nosso atendimento encerrou às *18h*.\n"
            f"Horário: *segunda a sexta, 9h às 18h*.\n\n"
            f"Sua mensagem ficou registrada e será respondida amanhã."
        )
    return True, ""


_chatbot_engine = ChatbotEngine()

# ── Status maps (Portuguese) ──

DELIVERY_STATUS_PT = {
    "pending": "Pendente",
    "shipped": "Enviado",
    "in_transit": "Em trânsito",
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
    import re as _re
    # Extract meaningful words (3+ chars, skip stopwords)
    stopwords = {
        "que", "para", "com", "por", "uma", "uns", "dos", "das", "nos", "nas",
        "seu", "sua", "meu", "minha", "como", "mais", "muito", "está", "esse",
        "esta", "isso", "ele", "ela", "não", "nao", "sim", "tem", "ter", "ser",
        "foi", "são", "era", "vai", "vou", "pode", "quero", "preciso", "estou",
        "sobre", "ainda", "também", "qual", "quando", "onde", "aqui",
    }
    words = [w for w in _re.findall(r"[a-záéíóúâêôãõç]+", query.lower()) if len(w) >= 3 and w not in stopwords]
    if not words:
        words = [w for w in _re.findall(r"[a-záéíóúâêôãõç]+", query.lower()) if len(w) >= 2]
    if not words:
        return []

    # Build conditions: each word must match title OR content — rank by number of matching words
    word_scores = []
    conditions = []
    for word in words[:6]:  # Max 6 words to avoid query explosion
        pattern = f"%{word}%"
        word_match = or_(KBArticle.title.ilike(pattern), KBArticle.content.ilike(pattern))
        conditions.append(word_match)
        # Title matches score higher
        word_scores.append(
            case((KBArticle.title.ilike(pattern), literal(2)), else_=literal(0))
            + case((KBArticle.content.ilike(pattern), literal(1)), else_=literal(0))
        )

    # Must match at least one word
    relevance = sum(word_scores)
    result = await db.execute(
        select(KBArticle)
        .where(
            KBArticle.is_published.is_(True),
            or_(*conditions),
        )
        .order_by(relevance.desc())
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
        "document_messages": [],
        "escalated": False,
    }

    # Layer -2: Check if we're waiting for observation after email
    _conv_meta_pre = getattr(conversation, "metadata_", None)
    if not isinstance(_conv_meta_pre, dict):
        _conv_meta_pre = {}
    pending_obs = _conv_meta_pre.get("pending_observation")
    if pending_obs and conversation.handler == "agent":
        return await _handle_pending_observation(db, conversation, customer, message_text, result, pending_obs)

    # Layer -1: Check if we're waiting for email to complete escalation
    pending_esc = _conv_meta_pre.get("pending_escalation")
    if pending_esc and conversation.handler == "agent":
        return await _handle_pending_email(db, conversation, customer, message_text, result, pending_esc)

    # Layer 0: Allow "menu/voltar" to reset back to chatbot even from agent/resolved
    _text_lower = message_text.strip().lower()
    _menu_words = ("menu", "voltar", "inicio", "início", "0", "oi", "olá", "ola", "meni", "memu")
    if _text_lower in _menu_words and conversation.handler in ("agent", "chatbot", None):
        conversation.handler = "chatbot"
        conversation.ai_enabled = True
        conversation.status = "open"
        # Clear any pending state
        _meta_reset = dict(getattr(conversation, "metadata_", None) or {})
        _meta_reset.pop("pending_escalation", None)
        _meta_reset.pop("pending_observation", None)
        _meta_reset.pop("chatbot_state", None)
        conversation.metadata_ = _meta_reset
        # Fall through to chatbot layer below

    # Layer 0: If agent handler — keep AI available for follow-up questions
    elif conversation.handler == "agent" and not conversation.ai_enabled:
        return result

    # Check if chatbot has active state (waiting for input) — skip auto-lookups
    _conv_meta = getattr(conversation, "metadata_", None)
    if not isinstance(_conv_meta, dict):
        _conv_meta = {}
    _has_active_flow = bool(_conv_meta.get("chatbot_state"))

    # Layer 0.5: Auto order lookup if message looks like an order number or email
    # Skip if chatbot is waiting for input (e.g., NF flow collecting order number)
    if not _has_active_flow and conversation.handler in ("chatbot", None, "ai"):
        order_num = _extract_order_number(message_text)
        email_input = _extract_email(message_text) if not order_num else None

        if order_num:
            from app.services import shopify_service
            order = await shopify_service.get_order_by_number(order_num)
            if order and not order.get("error"):
                detail_msgs = await _format_order_messages(order)
                detail_msgs.append("Precisa de mais alguma coisa? Digite *menu* para ver as opções.")
                for m in detail_msgs:
                    result["bot_messages"].append(m)
                    await _save_bot_message(db, conversation, m)
                result["handler"] = "chatbot"
                conversation.handler = "chatbot"
                await db.commit()
                return result
            else:
                # Order not found — give helpful message instead of falling to chatbot "nao entendi"
                msg = (
                    f"Não encontrei o pedido *#{order_num}* no sistema.\n\n"
                    f"Isso pode acontecer se o pedido foi feito antes de março/2025 (plataforma antiga).\n"
                    f"Tente enviar o *e-mail* cadastrado no pedido que busco por lá.\n\n"
                    f"Ou digite *menu* para ver outras opções."
                )
                result["bot_messages"].append(msg)
                await _save_bot_message(db, conversation, msg)
                result["handler"] = "chatbot"
                conversation.handler = "chatbot"
                await db.commit()
                return result

        elif email_input:
            # Search orders by email in Shopify + Yampi
            from app.services import shopify_service
            shopify_result = await shopify_service.get_orders_by_email(email_input, limit=5)
            orders = shopify_result.get("orders", [])

            # Fallback: try Yampi for older orders
            if not orders:
                try:
                    from app.services import yampi_service
                    yampi_result = await yampi_service.get_orders_by_email(email_input, limit=5)
                    orders = yampi_result.get("orders", [])
                except Exception as e:
                    logger.warning("Yampi email lookup failed: %s", e)

            if orders:
                msgs = []
                for o in orders[:3]:
                    order_msgs = await _format_order_messages(o)
                    msgs.extend(order_msgs)
                if len(orders) > 3:
                    msgs.append(f"Você tem mais {len(orders) - 3} pedido(s). Envie o número pra ver detalhes (ex: #12345).")
                msgs.append("Precisa de mais alguma coisa? Digite *menu* para ver as opções.")
                for m in msgs:
                    result["bot_messages"].append(m)
                    await _save_bot_message(db, conversation, m)
                result["handler"] = "chatbot"
                conversation.handler = "chatbot"
                await db.commit()
                return result
            else:
                msg = (
                    f"Não encontrei pedidos com o e-mail *{email_input}*.\n\n"
                    f"Verifique se é o mesmo e-mail usado na compra.\n"
                    f"Ou envie o *número do pedido* (ex: #12345).\n\n"
                    f"Digite *menu* para ver outras opções."
                )
                result["bot_messages"].append(msg)
                await _save_bot_message(db, conversation, msg)
                result["handler"] = "chatbot"
                conversation.handler = "chatbot"
                await db.commit()
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

                if resp_type == "transfer_to_ai":
                    conversation.handler = "ai"
                    conversation.ai_enabled = True
                    # Don't return — fall through to AI layer below
                    break

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
                    # Only save to DB, don't send as separate bot_message (interactive includes the text)
                    if content:
                        await _save_bot_message(db, conversation, content)
                    # Add interactive message for channel adapters
                    if options:
                        result["interactive_messages"].append({
                            "type": "menu",
                            "content": content,
                            "options": options,
                        })

                elif resp_type == "collect_input":
                    field = resp.get("field", "")
                    # Auto-lookup: if collecting order_number and we have phone, try Shopify first
                    # But skip if the flow explicitly needs the number (e.g., NF lookup)
                    _flow_name = chatbot_result.get("flow_name", "")
                    _skip_auto = "nota fiscal" in _flow_name.lower()
                    if not _skip_auto and field in ("order_number", "pedido") and conversation.channel == "whatsapp":
                        phone = getattr(customer, "phone", None)
                        if phone:
                            auto_msgs = await _auto_lookup_by_phone(customer, phone)
                            if auto_msgs:
                                for msg in auto_msgs:
                                    result["bot_messages"].append(msg)
                                    await _save_bot_message(db, conversation, msg)
                                # Clear chatbot state so it doesn't wait for input
                                meta = conversation.metadata_ or {}
                                meta.pop("chatbot_state", None)
                                conversation.metadata_ = meta
                                continue  # skip the collect_input prompt
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

                elif resp_type == "lookup_invoice":
                    collected_data = resp.get("collected_data", {})
                    order_num = collected_data.get(resp.get("variable", "order_number"), "")
                    # Clean order number
                    clean_num = order_num.strip().lstrip("#")
                    invoice = await _lookup_invoice(clean_num)

                    # Auto-generate NF if not found
                    if not invoice:
                        logger.info("[NF-AUTO] NF not found for order %s, attempting auto-generation", clean_num)
                        gen_result = await _generate_invoice(clean_num)
                        if gen_result and gen_result.get("found"):
                            invoice = gen_result
                            if gen_result.get("generated"):
                                logger.info("[NF-AUTO] NF generated for order %s", clean_num)
                            elif gen_result.get("already_exists"):
                                logger.info("[NF-AUTO] NF already existed for order %s", clean_num)
                        elif gen_result:
                            logger.warning("[NF-AUTO] Failed to generate NF for order %s: %s", clean_num, gen_result.get("error"))

                    if invoice:
                        # LGPD: verify customer identity before sending NF
                        customer_phone = getattr(customer, "phone", "") or ""
                        is_owner = _verify_invoice_owner(invoice, customer_phone)
                        logger.info("[NF-LGPD] order=%s customer_phone=%s invoice_phone=%s is_owner=%s", clean_num, customer_phone, invoice.get('customer_phone',''), is_owner)
                        if not is_owner:
                            # Send NF to the order email instead, and inform the customer
                            inv_email = invoice.get("customer_email", "") or ""
                            if inv_email:
                                masked_email = _mask_email(inv_email)
                                # Send NF by email
                                await _send_invoice_by_email(
                                    inv_email,
                                    invoice,
                                    _get_invoice_pdf_url(clean_num),
                                )
                                lgpd_msg = (
                                    f"Encontrei a nota fiscal desse pedido! Por questões de "
                                    f"segurança (LGPD), enviei o PDF para o e-mail cadastrado "
                                    f"no pedido: *{masked_email}*\n\n"
                                    f"Verifique sua caixa de entrada e spam."
                                )
                            else:
                                lgpd_msg = (
                                    "Encontrei a nota fiscal desse pedido, mas por questões de "
                                    "segurança e LGPD, só posso enviar para o titular.\n\n"
                                    "Entre em contato pelo mesmo número ou e-mail cadastrado no pedido."
                                )
                            result["bot_messages"].append(lgpd_msg)
                            await _save_bot_message(db, conversation, lgpd_msg)
                        else:
                            nfse_num = str(invoice.get("nfse_number", ""))
                            valor = str(invoice.get("valor_servico", ""))
                            link = invoice.get("link_pdf", "") or ""
                            was_generated = invoice.get("generated", False)
                            msg = f"Sua Nota Fiscal de Serviço:\n\n"
                            if was_generated:
                                msg = f"Gerei sua Nota Fiscal de Serviço agora mesmo!\n\n"
                            msg += f"NFS-e: *{nfse_num}*\n"
                            msg += f"Valor: R$ {valor}\n"
                            if link:
                                msg += f"\nLink para visualização:\n{link}\n"
                                msg += "\n_O link pode demorar alguns segundos para carregar (servidor da prefeitura)._"
                            result["bot_messages"].append(msg)
                            await _save_bot_message(db, conversation, msg)
                    else:
                        msg = (
                            "Não foi possível encontrar ou gerar a nota fiscal para esse pedido.\n\n"
                            "Isso pode acontecer se o pedido ainda não foi processado ou se houve algum problema.\n"
                            "Vou transferir para um atendente que pode te ajudar."
                        )
                        result["bot_messages"].append(msg)
                        await _save_bot_message(db, conversation, msg)
                        # Escalate since we couldn't provide the NF
                        return await _escalate_to_agent(
                            db, conversation, result,
                            escalation_message="Transferindo para um atendente...",
                        )

            if result["bot_messages"] or result["interactive_messages"] or result["document_messages"]:
                # Anti-loop: check if bot is repeating itself
                if result["bot_messages"] and _is_bot_looping(conversation, result["bot_messages"][0]):
                    logger.warning("[ANTI-LOOP] Bot repeating for conversation %s, escalating", conversation.id)
                    result["bot_messages"] = [
                        "Parece que não estou conseguindo te ajudar direito. "
                        "Vou transferir para um atendente humano."
                    ]
                    await _save_bot_message(db, conversation, result["bot_messages"][0])
                    return await _escalate_to_agent(db, conversation, result)

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

async def _lookup_invoice(order_number: str) -> dict | None:
    """Fetch invoice from Carbon NF system (same server, port 8002)."""
    import httpx
    import os
    nf_host = os.environ.get("CARBON_NF_URL", "http://172.17.0.1:8002")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{nf_host}/api/internal/invoice-by-order",
                params={"order_number": order_number},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("found"):
                    return data
    except Exception as e:
        logger.warning("Invoice lookup failed: %s", e)
    return None


async def _generate_invoice(order_number: str) -> dict | None:
    """Auto-generate NF via Carbon NF system (calls Bling API)."""
    import httpx
    import os
    nf_host = os.environ.get("CARBON_NF_URL", "http://172.17.0.1:8002")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{nf_host}/api/internal/generate-invoice",
                params={"order_number": order_number},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning("Invoice generation failed: %s", e)
    return None


def _get_invoice_pdf_url(order_number: str) -> str | None:
    """Get the public proxied PDF URL (accessible by WhatsApp Cloud API)."""
    import os
    # Public URL that WhatsApp can fetch — proxies through helpdesk → carbon-nf → prefeitura
    helpdesk_host = os.environ.get("HELPDESK_PUBLIC_URL", "https://helpdesk.brutodeverdade.com.br")
    nf_token = os.environ.get("NF_PDF_TOKEN", "carbon-nf-2026")
    return f"{helpdesk_host}/api/public/invoice-pdf?order_number={order_number}&token={nf_token}"


def _mask_email(email: str) -> str:
    """Mask email for LGPD: pe***@gm***.com"""
    parts = email.split("@")
    if len(parts) != 2:
        return "***@***.com"
    user = parts[0]
    domain = parts[1]
    domain_parts = domain.split(".")
    masked_user = user[:2] + "***" if len(user) > 2 else user[0] + "***"
    masked_domain = domain_parts[0][:2] + "***" if len(domain_parts[0]) > 2 else domain_parts[0]
    return f"{masked_user}@{masked_domain}.{'.'.join(domain_parts[1:])}"


async def _send_invoice_by_email(email: str, invoice: dict, pdf_url: str | None):
    """Send NF to customer email via Gmail API (reuses helpdesk gmail_service)."""
    from app.services.gmail_service import send_email
    import httpx
    import tempfile
    import os

    nfse_number = invoice.get("nfse_number", "")
    customer_name = invoice.get("customer_name", "Cliente")
    link = invoice.get("link_pdf", "")

    subject = f"Sua Nota Fiscal - Carbon Smartwatch (NFS-e {nfse_number})"
    body = (
        f"Olá {customer_name},\n\n"
        f"Segue sua Nota Fiscal de Serviço (NFS-e {nfse_number}).\n\n"
    )
    if link:
        body += f"Link para visualização: {link}\n\n"
    body += (
        "Qualquer dúvida, estamos à disposição.\n\n"
        "Atenciosamente,\nCarbon Smartwatch\n"
        "atendimento@carbonsmartwatch.com.br"
    )

    try:
        result = send_email(to=email, subject=subject, body_text=body)
        if result:
            print(f"[NF-EMAIL] Invoice NF {nfse_number} sent to {email} via Gmail — id={result.get('id')}", flush=True)
        else:
            print(f"[NF-EMAIL] FAILED to send invoice to {email} via Gmail (no result)", flush=True)
    except Exception as e:
        print(f"[NF-EMAIL] ERROR sending invoice to {email}: {e}", flush=True)


def _verify_invoice_owner(invoice: dict, customer_phone: str) -> bool:
    """LGPD: verify that the requesting customer is the order owner by matching phone number."""
    import re
    if not customer_phone:
        return False
    # Normalize phones to digits only for comparison
    req_digits = re.sub(r"\D", "", customer_phone)
    inv_phone = invoice.get("customer_phone", "") or ""
    inv_digits = re.sub(r"\D", "", inv_phone)
    if not inv_digits:
        # No phone on order — can't verify, deny for safety
        return False
    # Match last 8-9 digits (ignores country code / area code differences)
    return req_digits[-9:] == inv_digits[-9:]


async def _auto_lookup_by_phone(customer: Customer, phone: str) -> list[str]:
    """Try to find recent orders by customer phone number in Shopify."""
    from app.services import shopify_service
    from app.services.tracking_service import track_package

    try:
        result = await shopify_service.get_orders_by_phone(phone, limit=5)
        orders = result.get("orders", [])
        if not orders:
            return []  # No orders found — fall back to asking

        msgs = []

        # For each order, show full details with live tracking
        for o in orders[:3]:
            order_msgs = await _format_order_messages(o)
            msgs.extend(order_msgs)

        if len(orders) > 3:
            msgs.append(f"Você tem mais {len(orders) - 3} pedido(s). Envie o número pra ver detalhes (ex: #12345).")

        msgs.append("Precisa de mais alguma coisa? Digite *menu* para ver as opções.")
        return msgs
    except Exception as e:
        logger.warning("Auto phone lookup failed: %s", e)
        return []


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
        # Clean the order number
        clean_num = order_number.strip().lstrip("#")
        order = await shopify_service.get_order_by_number(clean_num)
        if order and not order.get("error"):
            # Use _format_order_messages to include live tracking from 17track
            msgs = await _format_order_messages(order)
            messages.extend(msgs)
            return messages
        else:
            # Not found in Shopify — helpful message about old orders
            messages.append(
                f"Não encontrei o pedido *#{clean_num}* no sistema.\n\n"
                f"Se foi feito antes de março/2025, pode estar na plataforma antiga.\n"
                f"Tente enviar o *e-mail* cadastrado no pedido que busco por lá."
            )
            return messages

    # Fallback: try by customer email (Shopify + Yampi)
    email = getattr(customer, "email", None)
    if email:
        result = await shopify_service.get_orders_by_email(email, limit=5)
        orders = result.get("orders", [])
        if not orders:
            try:
                from app.services import yampi_service
                yampi_result = await yampi_service.get_orders_by_email(email, limit=5)
                orders = yampi_result.get("orders", [])
            except Exception as e:
                logger.warning("Yampi fallback failed: %s", e)
        if orders:
            messages.append(_format_orders_list(orders))
            return messages

    messages.append("Não encontrei pedidos associados. Pode informar o número do pedido? (ex: #12345)")
    return messages


def _format_date_br(dt_str: str) -> str:
    """Convert datetime string to Brazilian format (DD/MM HH:MM)."""
    if not dt_str:
        return ""
    try:
        # Handle "2026-03-05 14:24:34" or "2026-03-05T14:24:34"
        dt_str = dt_str.replace("T", " ")[:19]
        from datetime import datetime
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return dt_str[:16] if len(dt_str) > 16 else dt_str


async def _format_order_messages(order: dict) -> list[str]:
    """Format order into a single rich message with live tracking timeline."""
    from app.services.tracking_service import track_package

    number = order.get("order_number", "?")
    financial = FINANCIAL_STATUS_PT.get(order.get("financial_status", ""), order.get("financial_status", ""))
    delivery = DELIVERY_STATUS_PT.get(order.get("delivery_status", ""), order.get("delivery_status", ""))
    total = order.get("total_price", "0.00")
    tracking = order.get("tracking_code", "")
    items_list = order.get("items", [])

    # Build items text
    items_text = ""
    if items_list:
        lines = []
        for item in items_list[:5]:
            qty = item.get("quantity", 1)
            title = item.get("title", "")
            variant = item.get("variant_title", "")
            line = f"  • {qty}x {title}"
            if variant:
                line += f" ({variant})"
            lines.append(line)
        items_text = "\n".join(lines)

    # Start building message
    msg = f"*Pedido {number}* — R$ {total}\n"
    msg += f"Pagamento: {financial}\n"
    if items_text:
        msg += f"\n{items_text}\n"

    msgs = []

    if tracking:
        try:
            track_result = await track_package(tracking)
            events = track_result.get("events", [])
            eta = track_result.get("estimated_delivery", "")

            if events:
                last_event = events[0]
                last_status = last_event.get("status", "")
                last_location = last_event.get("location", "")
                is_delivered = track_result.get("delivered", False)

                # Status header with emoji-like markers
                if is_delivered:
                    msg += f"\n*ENTREGUE*"
                else:
                    msg += f"\n*Status:* {last_status}"
                if last_location:
                    msg += f"\n*Local:* {last_location}"
                if eta and not is_delivered:
                    msg += f"\n*Previsão de entrega:* {eta}"

                # Timeline
                msg += f"\n\n*Rastreio:* {tracking}\n"
                for ev in events[:5]:
                    ev_date = _format_date_br(ev.get("date", ""))
                    ev_status = ev.get("status", "")
                    ev_loc = ev.get("location", "")
                    line = f"  {ev_date} — {ev_status}"
                    if ev_loc:
                        line += f" ({ev_loc})"
                    msg += f"\n{line}"
            else:
                # Tracking code exists but no events yet
                msg += f"\n*Rastreio:* {tracking}"
                msg += f"\n_Pacote registrado, aguardando movimentação da transportadora._"

        except Exception as e:
            logger.warning("Tracking lookup failed for %s: %s", tracking, e)
            msg += f"\n*Rastreio:* {tracking}"

    else:
        # No tracking code
        msg += f"\nEntrega: {delivery}"
        if delivery in ("Pendente", "pending"):
            msg += "\n_Seu pedido está sendo preparado. O código de rastreio será enviado assim que for despachado._"

    msgs.append(msg.strip())
    return msgs


def _format_orders_list(orders: list[dict]) -> str:
    """Format a list of orders into a summary message."""
    lines = ["Encontrei seus pedidos recentes:\n"]
    for o in orders[:5]:
        number = o.get("order_number", "?")
        financial = FINANCIAL_STATUS_PT.get(o.get("financial_status", ""), o.get("financial_status", ""))
        delivery = DELIVERY_STATUS_PT.get(o.get("delivery_status", ""), o.get("delivery_status", ""))
        total = o.get("total_price", "0.00")
        lines.append(f"  {number} — R$ {total} — {financial} — {delivery}")
    lines.append("\nEnvie o número do pedido para ver os detalhes.")
    return "\n".join(lines)


# ── Email lookup + pending escalation ──

async def _find_email_by_phone(phone: str) -> str | None:
    """Try to find customer email via Shopify orders by phone."""
    from app.services import shopify_service
    try:
        result = await shopify_service.get_orders_by_phone(phone, limit=1)
        orders = result.get("orders", [])
        if orders:
            email = orders[0].get("email") or orders[0].get("customer_email")
            if email:
                return email
    except Exception as e:
        logger.warning("Email lookup by phone failed: %s", e)
    return None


async def _handle_pending_email(
    db: AsyncSession, conversation: Conversation, customer: Customer,
    message_text: str, result: dict, pending_esc: dict,
) -> dict:
    """Handle email input/confirmation after bot asked during escalation."""
    import re
    text = message_text.strip().lower()
    found_email = pending_esc.get("found_email")

    # Handle confirmation of Shopify email
    if found_email:
        if text in ("sim", "sim, usar esse", "confirm_email_yes", "s", "1"):
            customer.email = found_email
            meta = conversation.metadata_ if isinstance(conversation.metadata_, dict) else {}
            meta.pop("pending_escalation", None)
            # Transition to pending_observation
            meta["pending_observation"] = {
                "email": found_email,
                "asked_at": datetime.now(timezone.utc).isoformat(),
            }
            conversation.metadata_ = meta
            msg = (
                "Quer adicionar alguma observação ou detalhe sobre o seu problema?\n\n"
                "Se não quiser, é só aguardar que já vamos encaminhar."
            )
            result["bot_messages"].append(msg)
            await _save_bot_message(db, conversation, msg)
            # Schedule auto-finalize in 15 min
            _schedule_observation_timeout(conversation.id)
            await db.commit()
            result["handler"] = "agent"
            return result
        elif text in ("não", "nao", "não, usar outro", "confirm_email_no", "n", "2"):
            # Clear found_email, ask for new one
            meta = conversation.metadata_ if isinstance(conversation.metadata_, dict) else {}
            meta["pending_escalation"] = {"escalation_message": pending_esc.get("escalation_message", "")}
            conversation.metadata_ = meta
            msg = "Sem problema! Digite o e-mail que deseja usar:"
            result["bot_messages"].append(msg)
            await _save_bot_message(db, conversation, msg)
            await db.commit()
            result["handler"] = "agent"
            return result
        else:
            msg = "Por favor, responda *Sim* ou *Não*:"
            result["bot_messages"].append(msg)
            await _save_bot_message(db, conversation, msg)
            await db.commit()
            result["handler"] = "agent"
            return result

    # Handle typed email
    text = message_text.strip()  # Use original case for email
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text):
        # Save email to customer
        customer.email = text
        # Transition to pending_observation
        meta = conversation.metadata_ if isinstance(conversation.metadata_, dict) else {}
        meta.pop("pending_escalation", None)
        meta["pending_observation"] = {
            "email": text,
            "asked_at": datetime.now(timezone.utc).isoformat(),
        }
        conversation.metadata_ = meta
        msg = (
            "Obrigado! Quer adicionar alguma observação ou detalhe sobre o seu problema?\n\n"
            "Se não quiser, é só aguardar que já vamos encaminhar."
        )
        result["bot_messages"].append(msg)
        await _save_bot_message(db, conversation, msg)
        _schedule_observation_timeout(conversation.id)
        await db.commit()
        result["handler"] = "agent"
        return result
    else:
        msg = "Não reconheci um e-mail válido. Por favor, digite seu e-mail (ex: nome@email.com):"
        result["bot_messages"].append(msg)
        await _save_bot_message(db, conversation, msg)
        await db.commit()
        result["handler"] = "agent"
        return result


# ── Escalation + helpers ──

async def _handle_pending_observation(
    db: AsyncSession, conversation: Conversation, customer: Customer,
    message_text: str, result: dict, pending_obs: dict,
) -> dict:
    """Handle observation input after email was provided."""
    text = message_text.strip()
    email = pending_obs.get("email", "")
    observation = pending_obs.get("observation")

    # Skip if they just say "nao", "não", "n" — finalize without observation
    text_lower = text.lower()
    if text_lower in ("nao", "não", "n", "nenhuma", "sem observação", "sem observacao", "não tenho", "nao tenho"):
        text = None  # No observation

    # Clear pending state
    meta = conversation.metadata_ if isinstance(conversation.metadata_, dict) else {}
    meta.pop("pending_observation", None)
    conversation.metadata_ = meta

    # Save observation in conversation metadata for the agent
    if text and text_lower not in ("nao", "não", "n", "nenhuma", "sem observação", "sem observacao", "não tenho", "nao tenho"):
        obs_meta = dict(getattr(conversation, "metadata_", None) or {})
        obs_meta["customer_observation"] = text
        conversation.metadata_ = obs_meta

    # Create ticket
    ticket_number = await _create_ticket_from_conversation(db, conversation)
    masked = _mask_email(email)
    is_open, hours_msg = _is_business_hours()

    if ticket_number:
        msg = (
            f"Sua solicitação foi enviada para nossa equipe! Chamado *#{ticket_number}*.\n\n"
            f"O retorno será feito pelo e-mail *{masked}* em até *48 horas úteis*.\n"
            f"Fique de olho na sua caixa de entrada e na pasta de *spam*.\n\n"
        )
        if not is_open:
            msg += hours_msg + "\n\n"
        msg += "Se precisar de algo mais, é só mandar um *oi* a qualquer momento!"
    else:
        msg = (
            f"Registrado! Nosso time vai responder no e-mail *{masked}* em até *48 horas úteis*.\n"
            f"Fique de olho na caixa de entrada e no *spam*.\n\n"
            f"Se precisar de algo mais, é só mandar um *oi* a qualquer momento!"
        )
    result["bot_messages"].append(msg)
    await _save_bot_message(db, conversation, msg)

    # Resolve conversation (don't leave in queue)
    conversation.status = "resolved"
    await db.commit()
    result["handler"] = "agent"
    return result


def _schedule_observation_timeout(conversation_id):
    """Schedule auto-finalize if customer doesn't respond in 15 min."""
    import asyncio

    async def _auto_finalize():
        await asyncio.sleep(15 * 60)  # 15 minutes
        await _finalize_observation_timeout(conversation_id)

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_auto_finalize())
    except RuntimeError:
        pass  # No event loop — skip (won't happen in prod)


async def _finalize_observation_timeout(conversation_id):
    """Auto-finalize escalation after 15min timeout on observation."""
    from app.core.database import AsyncSessionLocal
    from app.services.channels.dispatcher import dispatcher
    from app.models.channel_identity import ChannelIdentity

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if not conversation:
                return

            meta = conversation.metadata_ if isinstance(conversation.metadata_, dict) else {}
            pending = meta.get("pending_observation")
            if not pending:
                return  # Already handled by customer response

            email = pending.get("email", "")
            meta.pop("pending_observation", None)
            conversation.metadata_ = meta

            ticket_number = await _create_ticket_from_conversation(db, conversation)
            masked = _mask_email(email)

            msg = "Sua solicitação foi enviada para nossa equipe!"
            if ticket_number:
                msg += f" Chamado *#{ticket_number}*."
            msg += (
                f"\n\nO retorno será feito pelo e-mail *{masked}* em até *48 horas úteis*.\n"
                f"Fique de olho na sua caixa de entrada e na pasta de *spam*.\n\n"
                f"Se precisar de algo mais, é só mandar um *oi* a qualquer momento!"
            )

            bot_msg = ChatMessage(
                conversation_id=conversation.id,
                sender_type="bot",
                sender_id=None,
                content_type="text",
                content=msg,
                created_at=datetime.now(timezone.utc),
            )
            db.add(bot_msg)
            conversation.last_message_at = datetime.now(timezone.utc)
            conversation.status = "resolved"
            await db.commit()

            # Send via channel adapter — find recipient from ChannelIdentity
            try:
                channel = conversation.channel or "whatsapp"
                ci_result = await db.execute(
                    select(ChannelIdentity).where(
                        ChannelIdentity.customer_id == conversation.customer_id,
                        ChannelIdentity.channel == channel,
                    )
                )
                ci = ci_result.scalar_one_or_none()
                if ci:
                    kwargs = {}
                    phone_number_id = meta.get("phone_number_id")
                    if phone_number_id:
                        kwargs["phone_number_id"] = phone_number_id
                    await dispatcher.send(channel, ci.channel_id, msg, **kwargs)
            except Exception as e:
                logger.warning("[OBS-TIMEOUT] Failed to send timeout message: %s", e)

            logger.info("[OBS-TIMEOUT] Auto-finalized conversation %s after 15min", conversation_id)
    except Exception as e:
        logger.error("[OBS-TIMEOUT] Error: %s", e)


async def _escalate_to_agent(
    db: AsyncSession,
    conversation: Conversation,
    result: dict,
    escalation_message: str = "Vou transferir você para um de nossos atendentes. Um momento, por favor.",
) -> dict:
    conversation.handler = "agent"
    conversation.ai_enabled = True  # Keep AI in standby — agent responds via email, AI handles follow-ups
    conversation.ai_attempts = 0

    # Check business hours and inform customer
    is_open, hours_msg = _is_business_hours()

    await routing_service.auto_assign(db, conversation)

    system_msg = ChatMessage(
        conversation_id=conversation.id,
        sender_type="system",
        sender_id=None,
        content_type="text",
        content="Conversa transferida para atendimento humano.",
    )
    db.add(system_msg)

    if is_open:
        result["bot_messages"].append(escalation_message)
        await _save_bot_message(db, conversation, escalation_message)
    else:
        # Outside business hours — inform and keep the message
        result["bot_messages"].append(hours_msg)
        await _save_bot_message(db, conversation, hours_msg)

    # Try to find/enrich customer email before creating ticket
    customer = conversation.customer
    customer_email = getattr(customer, "email", None) if customer else None

    if not customer_email and customer:
        # Try Shopify lookup by phone
        phone = getattr(customer, "phone", None)
        if phone:
            found_email = await _find_email_by_phone(phone)
            if found_email:
                logger.info("[ESCALATE] Found email %s via Shopify for phone %s", found_email, phone)
                # Ask customer to confirm the email
                meta = conversation.metadata_ if isinstance(conversation.metadata_, dict) else {}
                meta["pending_escalation"] = {
                    "escalation_message": escalation_message,
                    "found_email": found_email,
                }
                conversation.metadata_ = meta
                masked = _mask_email(found_email)
                confirm_msg = f"Encontrei o e-mail *{masked}* no seu cadastro.\nPosso usar esse e-mail para abrir seu chamado?"
                result["bot_messages"].append(confirm_msg)
                await _save_bot_message(db, conversation, confirm_msg)
                result["interactive_messages"].append({
                    "type": "menu",
                    "content": confirm_msg,
                    "options": [
                        {"id": "confirm_email_yes", "label": "Sim, usar esse"},
                        {"id": "confirm_email_no", "label": "Não, usar outro"},
                    ],
                })
                await db.commit()
                result["handler"] = "agent"
                result["escalated"] = True
                return result

    if not customer_email:
        # Ask for email — save state so we can resume after they reply
        meta = conversation.metadata_ if isinstance(conversation.metadata_, dict) else {}
        meta["pending_escalation"] = {
            "escalation_message": escalation_message,
        }
        conversation.metadata_ = meta
        # Keep handler as agent but flag we need email
        ask_msg = (
            "Para abrir seu chamado, preciso do seu e-mail.\n"
            "Nosso time vai responder por lá.\n\n"
            "Por favor, digite seu e-mail:"
        )
        result["bot_messages"].append(ask_msg)
        await _save_bot_message(db, conversation, ask_msg)
        await db.commit()
        result["handler"] = "agent"
        result["escalated"] = True
        return result

    # Create email ticket from chat conversation
    ticket_number = await _create_ticket_from_conversation(db, conversation)

    masked = _mask_email(customer_email)
    if ticket_number:
        ticket_msg = (
            f"Criei o chamado *#{ticket_number}* para você.\n"
            f"Nosso time vai responder pelo e-mail: *{masked}*\n\n"
            f"Horário de atendimento: *segunda a sexta, 9h às 18h*.\n"
            f"Sua mensagem será respondida assim que possível."
        )
    else:
        ticket_msg = (
            "Nosso horário de atendimento é *segunda a sexta, 9h às 18h*.\n\n"
            "Envie um e-mail para *atendimento@carbonsmartwatch.com.br* "
            "que nosso time vai te responder o mais rápido possível."
        )

    result["bot_messages"].append(ticket_msg)
    await _save_bot_message(db, conversation, ticket_msg)

    await db.commit()

    result["handler"] = "agent"
    result["escalated"] = True
    return result


async def _create_ticket_from_conversation(db: AsyncSession, conversation: Conversation) -> int | None:
    """Create an email ticket from a WhatsApp/IG/FB conversation so the team sees it."""
    from app.models.ticket import Ticket
    from app.models.message import Message

    try:
        # Build conversation transcript
        messages = []
        for msg in (conversation.chat_messages or []):
            if msg.sender_type == "system":
                continue
            sender = "Cliente" if msg.sender_type == "contact" else "Bot"
            messages.append(f"[{sender}] {msg.content}")

        transcript = "\n".join(messages[-20:])  # Last 20 messages

        # Determine subject from conversation context
        _meta = conversation.metadata_ if isinstance(conversation.metadata_, dict) else {}
        collected = _meta.get("collected_by_bot", {})
        subject_parts = []
        channel_name = {"whatsapp": "WhatsApp", "instagram": "Instagram", "facebook": "Facebook"}.get(
            conversation.channel, conversation.channel or "Chat"
        )
        subject_parts.append(f"[{channel_name}]")

        customer_name = conversation.customer.name if conversation.customer else "Cliente"
        subject_parts.append(customer_name)

        # Try to extract intent from first customer message
        first_msg = ""
        for msg in (conversation.chat_messages or []):
            if msg.sender_type == "contact":
                first_msg = (msg.content or "")[:80]
                break
        if first_msg:
            subject_parts.append(f"— {first_msg}")

        subject = " ".join(subject_parts)[:500]

        # Determine priority
        priority = conversation.priority if hasattr(conversation, "priority") and conversation.priority != "normal" else "medium"
        if _meta.get("chatbot_state", {}).get("flow_name", ""):
            flow = _meta["chatbot_state"]["flow_name"].lower()
            if any(w in flow for w in ("procon", "juridico", "chargeback")):
                priority = "high"

        # Determine category from tags or flow
        category = None
        tags_list = []
        if conversation.tags and isinstance(conversation.tags, list):
            tags_list = conversation.tags
        tags_list.append(f"chat_{conversation.channel or 'unknown'}")
        tags_list.append("auto_escalado")

        # Get next ticket number
        from sqlalchemy import func as sqlfunc
        max_num = await db.execute(select(sqlfunc.max(Ticket.number)))
        next_number = (max_num.scalar() or 0) + 1

        ticket = Ticket(
            number=next_number,
            subject=subject,
            status="open",
            priority=priority,
            category=category,
            customer_id=conversation.customer_id,
            source=conversation.channel or "chat",
            meta_conversation_id=conversation.id,
            meta_platform=conversation.channel,
            tags=tags_list,
        )
        db.add(ticket)
        await db.flush()  # Get ticket.id

        # Add transcript as first message
        body_text = f"Conversa escalada do {channel_name}:\n\n{transcript}"
        body_html = f"<p><strong>Conversa escalada do {channel_name}:</strong></p><pre>{transcript}</pre>"

        message = Message(
            ticket_id=ticket.id,
            type="inbound",
            sender_name=customer_name,
            sender_email=getattr(conversation.customer, "email", None) or f"{conversation.channel}@chat.internal",
            body_text=body_text,
            body_html=body_html,
        )
        db.add(message)

        logger.info("[ESCALATE] Created ticket #%s from %s conversation %s", next_number, conversation.channel, conversation.id)
        return next_number

    except Exception as e:
        logger.error("[ESCALATE] Failed to create ticket from conversation: %s", e)
        return None


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
    _track_bot_message(conversation, content)


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
