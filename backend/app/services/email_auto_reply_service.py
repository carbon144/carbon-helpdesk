"""Email Auto-Reply Service — IA responds to simple email tickets automatically.

V2: Enriched with real Shopify order data + tracking before generating replies.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import ai_service
from app.services.gmail_service import send_email
from app.services.kb_real_data import KB_ARTICLES
from app.services.data_extractor import extract_customer_data
from app.services.carlos_rules import CARLOS_SHARED_RULES

logger = logging.getLogger(__name__)

# Categories that IA can auto-resolve
AUTO_RESOLVE_CATEGORIES = {"meu_pedido", "duvida", "reenvio"}

# Categories that get ACK only (agent handles)
ACK_CATEGORIES = {"garantia", "financeiro", "reclamacao"}

EMAIL_AUTO_REPLY_PROMPT = f"""Voce eh o Carlos, assistente de suporte da Carbon por email.
A Carbon eh uma marca brasileira de smartwatches.

Voce esta respondendo a um email de cliente automaticamente. O email ja foi classificado pela triagem.

{CARLOS_SHARED_RULES}

=== DADOS DO PEDIDO (quando disponivel) ===
Se o email contiver uma secao "DADOS REAIS DO PEDIDO", use APENAS esses dados para responder. Sao factuais do sistema Shopify + rastreio.

REGRAS com dados do pedido:
- Se tem tracking com eventos → informar ultimo status e dizer que pode acompanhar em carbonsmartwatch.com.br/a/rastreio
- Se pedido esta "shipped" mas sem eventos detalhados → informar que foi enviado e dar prazo pela regiao do destino
- Se pedido esta "delivered" / consta entregue → informar que consta entregue no sistema, perguntar se recebeu
- Se pedido esta "pending" / "unfulfilled" → informar que esta sendo preparado + prazo pela regiao
- Se cliente quer cancelar mas pedido ja esta "shipped" → informar que ja foi enviado, orientar recusa na entrega ou devolucao em 7 dias
- Se cliente pergunta nota fiscal → NF em processo de regularizacao, disponibilizadas em breve
- Se estorno/reembolso e financial_status = "refunded" → informar que ja foi estornado
- NUNCA inventar informacoes alem dos dados fornecidos

=== FORMATO ===
Responda APENAS com o texto do email. Sem JSON, sem markdown.
Comece com "Ola, [nome]!" e termine com:

Fico a disposicao.

Atenciosamente,
Equipe Carbon"""

ACK_TEMPLATE = """Ola, {name}!

Recebemos sua mensagem e nosso time ja esta analisando o seu caso.{extra_info}

Enquanto isso, algumas informacoes uteis:
- Rastreio do seu pedido: https://carbonsmartwatch.com.br/a/rastreio
- Portal de trocas/devolucoes: carbonsmartwatch.troque.app.br

Fico a disposicao.

Atenciosamente,
Equipe Carbon"""


async def _enrich_with_order_data(subject: str, body: str, from_email: str) -> dict | None:
    """Enrich auto-reply with real Shopify order data + tracking.

    Returns dict with order_data formatted for the prompt, or None if no data found.
    """
    from app.services.shopify_service import get_order_by_number, get_orders_by_email
    from app.services.tracking_service import track_package

    extracted = extract_customer_data(f"{subject} {body}")
    order = None

    # Strategy 1: order number from subject/body
    order_number = extracted.get("shopify_order_id")
    if order_number:
        result = await get_order_by_number(order_number)
        if not result.get("error"):
            order = result

    # Strategy 2: email lookup (most recent order)
    if not order and from_email:
        result = await get_orders_by_email(from_email, limit=3)
        orders = result.get("orders", [])
        if orders:
            order = orders[0]  # most recent

    if not order:
        return None

    # Enrich with live tracking if available
    tracking_info = None
    tracking_code = order.get("tracking_code", "")
    if tracking_code:
        try:
            tracking_info = await track_package(tracking_code)
        except Exception as e:
            logger.warning(f"Tracking lookup failed for {tracking_code}: {e}")

    # Format for prompt
    items_str = ", ".join(
        f"{it.get('title', '?')} (x{it.get('quantity', 1)})"
        for it in order.get("items", [])
    ) or "N/A"

    shipping = order.get("shipping_address") or {}
    region = shipping.get("province", "") or ""

    data = {
        "order_number": order.get("order_number", ""),
        "items": items_str,
        "total": order.get("total_price", ""),
        "financial_status": order.get("financial_status", ""),
        "delivery_status": order.get("delivery_status", ""),
        "tracking_code": tracking_code,
        "carrier": order.get("carrier", ""),
        "region": region,
        "created_at": (order.get("created_at") or "")[:10],
    }

    if tracking_info and tracking_info.get("events"):
        events = tracking_info["events"][:5]
        events_str = "\n".join(
            f"  - {ev.get('date', '')[:16]} | {ev.get('status', '')} | {ev.get('location', '')}"
            for ev in events
        )
        data["tracking_status"] = tracking_info.get("status", "")
        data["tracking_events"] = events_str
        data["delivered"] = tracking_info.get("delivered", False)
        data["estimated_delivery"] = tracking_info.get("estimated_delivery", "")
    elif tracking_info:
        data["tracking_status"] = tracking_info.get("status", "Sem eventos ainda")
        data["tracking_events"] = ""
        data["delivered"] = tracking_info.get("delivered", False)

    return data


def _format_order_context(order_data: dict) -> str:
    """Format enriched order data into a text block for the AI prompt."""
    lines = [
        f"Pedido: {order_data['order_number']}",
        f"Produtos: {order_data['items']}",
        f"Valor total: R$ {order_data['total']}",
        f"Status financeiro: {order_data['financial_status']}",
        f"Status entrega: {order_data['delivery_status']}",
        f"Data do pedido: {order_data['created_at']}",
    ]
    if order_data.get("tracking_code"):
        lines.append(f"Código de rastreio: {order_data['tracking_code']}")
        lines.append(f"Transportadora: {order_data.get('carrier', 'N/A')}")
    if order_data.get("tracking_status"):
        lines.append(f"Último status rastreio: {order_data['tracking_status']}")
    if order_data.get("tracking_events"):
        lines.append(f"Eventos recentes:\n{order_data['tracking_events']}")
    if order_data.get("estimated_delivery"):
        lines.append(f"Previsão de entrega: {order_data['estimated_delivery']}")
    if order_data.get("delivered"):
        lines.append(">>> CONSTA COMO ENTREGUE NO SISTEMA <<<")
    if order_data.get("region"):
        lines.append(f"Estado destino: {order_data['region']}")
    return "\n".join(lines)


async def _get_kb_context(category: str, db: Optional[AsyncSession] = None) -> str:
    """Get relevant KB articles for the category.

    If a db session is provided, queries the kb_articles table first.
    Falls back to hardcoded KB_ARTICLES if no db or empty result.
    """
    articles = []

    # Try DB first
    if db is not None:
        try:
            from sqlalchemy import select
            from app.models.kb_article import KBArticle

            stmt = (
                select(KBArticle)
                .where(KBArticle.category == category, KBArticle.is_published == True)  # noqa: E712
                .limit(5)
            )
            result = await db.execute(stmt)
            rows = result.scalars().all()
            if rows:
                articles = [{"title": r.title, "content": r.content} for r in rows]
        except Exception as e:
            logger.warning(f"DB KB lookup failed, falling back to hardcoded: {e}")

    # Fallback to hardcoded
    if not articles:
        relevant = [a for a in KB_ARTICLES if a.get("category") == category]
        if not relevant:
            relevant = KB_ARTICLES[:3]
        articles = relevant

    texts = []
    for a in articles[:3]:
        texts.append(f"Artigo: {a['title']}\n{a['content'][:500]}")
    return "\n\n".join(texts)


async def generate_auto_reply(
    subject: str,
    body: str,
    customer_name: str,
    category: str,
    triage: dict | None = None,
    protocol: str | None = None,
    from_email: str = "",
    db: Optional[AsyncSession] = None,
) -> dict:
    """Generate an automatic email reply.

    Returns:
        {
            "type": "auto_reply" | "ack" | "skip",
            "body": str (email text),
            "reason": str,
        }
    """
    if not settings.EMAIL_AUTO_REPLY_ENABLED:
        return {"type": "skip", "body": "", "reason": "disabled"}

    # Reclame Aqui: SKIP total — sem ACK, sem resposta, atribuir Lyvia
    if from_email and ("reclameaqui.com.br" in from_email.lower() or "reclameaqui.com" in from_email.lower()):
        return {"type": "skip", "body": "", "reason": "reclame_aqui_skip_lyvia"}

    # NEVER auto-reply to legal risk or urgent
    if triage and (triage.get("legal_risk") or triage.get("priority") == "urgent"):
        return {"type": "skip", "body": "", "reason": "legal_risk_or_urgent"}

    confidence = triage.get("confidence", 0) if triage else 0

    # Detect complex topics that should NOT be auto-resolved
    _text = f"{subject} {body}".lower()

    # ALWAYS escalate: legal risk, defects, warranty claims, water damage
    HARD_ESCALATE = [
        "garantia", "carbon care", "carboncare", "defeito", "quebrou", "parou de funcionar",
        "nao funciona", "não funciona", "tela apagou", "nao liga", "não liga",
        "procon", "advogado", "juridico", "jurídico",
        "troca", "devolu", "arrependimento", "produto errado",
        "termo de garantia", "certificado",
        "natação", "natacao", "nadar", "mergulh", "piscina", "prova d'água",
        "prova d'agua", "prova dagua", "ip68", "ip67", "ip66",
        "a prova de agua", "à prova de água", "resistente a agua", "resistente à água",
    ]

    # SOFT escalate: can be resolved WITH order data
    SOFT_ESCALATE = [
        "cancelar compra", "cancelar", "nota fiscal",
        "reembolso", "estorno", "dinheiro de volta",
    ]

    if any(kw in _text for kw in HARD_ESCALATE):
        name = customer_name.split()[0] if customer_name else "Cliente"
        extra_info = ""
        if protocol:
            extra_info = f"\nSeu protocolo de atendimento: {protocol}"
        ack_body = ACK_TEMPLATE.format(name=name, extra_info=extra_info)
        return {"type": "ack", "body": ack_body, "reason": "escalate_keyword_detected"}

    # Enrich with real order data
    order_data = None
    if from_email:
        try:
            order_data = await _enrich_with_order_data(subject, body, from_email)
        except Exception as e:
            logger.warning(f"Order enrichment failed: {e}")

    # Soft escalate keywords: ACK only if we DON'T have order data to help
    has_soft_kw = any(kw in _text for kw in SOFT_ESCALATE)
    if has_soft_kw and not order_data:
        name = customer_name.split()[0] if customer_name else "Cliente"
        extra_info = ""
        if protocol:
            extra_info = f"\nSeu protocolo de atendimento: {protocol}"
        ack_body = ACK_TEMPLATE.format(name=name, extra_info=extra_info)
        return {"type": "ack", "body": ack_body, "reason": "soft_escalate_no_data"}

    # Auto-resolve: simple categories with high confidence OR we have order data
    can_resolve = (category in AUTO_RESOLVE_CATEGORIES and confidence >= 0.5) or order_data is not None
    if can_resolve:
        try:
            reply_text = await _generate_ai_reply(
                subject, body, customer_name, category, protocol, order_data, db=db
            )
            if reply_text:
                return {
                    "type": "auto_reply",
                    "body": reply_text,
                    "reason": f"auto_resolve_{category}" + ("_enriched" if order_data else ""),
                }
        except Exception as e:
            logger.error(f"AI auto-reply generation failed: {e}")

    # ACK: everything else that's not skipped
    name = customer_name.split()[0] if customer_name else "Cliente"
    extra_info = ""
    if protocol:
        extra_info = f"\nSeu protocolo de atendimento: {protocol}"

    ack_body = ACK_TEMPLATE.format(name=name, extra_info=extra_info)
    return {"type": "ack", "body": ack_body, "reason": f"ack_{category}"}


async def _generate_ai_reply(
    subject: str,
    body: str,
    customer_name: str,
    category: str,
    protocol: str | None = None,
    order_data: dict | None = None,
    db: Optional[AsyncSession] = None,
) -> str | None:
    """Use Claude to generate a full auto-reply for simple tickets."""
    if ai_service.is_credits_exhausted():
        return None

    kb_context = await _get_kb_context(category, db=db)

    user_msg = f"Assunto: {subject}\nCliente: {customer_name}\nCategoria: {category}\n"
    if protocol:
        user_msg += f"Protocolo: {protocol}\n"

    # Inject real order data if available
    if order_data:
        order_context = _format_order_context(order_data)
        user_msg += f"\n=== DADOS REAIS DO PEDIDO (do Shopify + rastreio) ===\n{order_context}\n=== FIM DADOS DO PEDIDO ===\n"

    user_msg += f"\nEmail do cliente:\n{body[:2000]}"
    if kb_context:
        user_msg += f"\n\n--- Base de Conhecimento ---\n{kb_context}"

    try:
        ai = ai_service.get_client()
        response = await ai_service._call_with_retry(
            lambda: ai.messages.create(
                model=settings.ANTHROPIC_AUTO_REPLY_MODEL or settings.ANTHROPIC_MODEL,
                max_tokens=800,
                system=EMAIL_AUTO_REPLY_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
        )
        return response.content[0].text.strip()
    except Exception as e:
        ai_service._handle_credit_error(e)
        logger.error(f"Email auto-reply AI failed: {e}")
        return None


async def send_auto_reply(
    to_email: str,
    subject: str,
    body_text: str,
    gmail_thread_id: str | None = None,
    gmail_message_id: str | None = None,
) -> dict | None:
    """Send the auto-reply email via Gmail in the same thread."""
    reply_subject = subject if subject.startswith("Re:") else f"Re: {subject}"

    import asyncio
    result = await asyncio.to_thread(
        send_email,
        to=to_email,
        subject=reply_subject,
        body_text=body_text,
        thread_id=gmail_thread_id,
        in_reply_to=gmail_message_id,
    )
    if result:
        logger.info(f"Auto-reply sent to {to_email}, gmail_id={result.get('id')}")
    return result
