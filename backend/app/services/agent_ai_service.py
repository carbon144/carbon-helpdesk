"""Agent AI Service — routes tickets to specialized AI agents and generates replies."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.ai_agent import AIAgent
from app.models.ticket import Ticket
from app.models.kb_article import KBArticle
from app.services import ai_service
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_agent_for_ticket(ticket: Ticket, db: AsyncSession) -> AIAgent | None:
    """Find the best AI agent for this ticket based on category matching.

    Priority: match by category, then pick lowest level agent.
    If multiple match at same level, pick one with fewer total_replies (round-robin-ish).
    """
    if not ticket.category:
        return None

    # Get all active agents whose categories include this ticket's category
    result = await db.execute(
        select(AIAgent).where(
            AIAgent.is_active == True,
        )
    )
    agents = list(result.scalars().all())

    # Filter by category match
    matching = []
    for agent in agents:
        if agent.categories and ticket.category in agent.categories:
            matching.append(agent)

    if not matching:
        return None

    # Sort by level ASC (prefer lower level), then by total_replies ASC (load balance)
    matching.sort(key=lambda a: (a.level, a.total_replies))
    return matching[0]


async def _get_kb_context_from_db(category: str, db: AsyncSession) -> str:
    """Get KB articles from database for the given category."""
    result = await db.execute(
        select(KBArticle).where(
            KBArticle.category == category,
            KBArticle.is_published == True,
        ).limit(5)
    )
    articles = list(result.scalars().all())

    if not articles:
        # Fallback: get any 3 articles
        result = await db.execute(
            select(KBArticle).where(KBArticle.is_published == True).limit(3)
        )
        articles = list(result.scalars().all())

    texts = []
    for a in articles[:5]:
        texts.append(f"Artigo: {a.title}\n{a.content[:600]}")
    return "\n\n".join(texts)


async def generate_agent_reply(
    agent: AIAgent,
    ticket: Ticket,
    email_body: str,
    customer_name: str,
    db: AsyncSession,
    order_data: dict | None = None,
) -> dict:
    """Generate a reply using the agent's specialized prompt.

    Returns: {reply_text, confidence, should_escalate, escalation_reason}
    """
    if ai_service.is_credits_exhausted():
        return {"reply_text": None, "confidence": 0, "should_escalate": False, "escalation_reason": "credits_exhausted"}

    # Check escalation keywords first
    text_lower = f"{ticket.subject or ''} {email_body}".lower()
    for kw in (agent.escalation_keywords or []):
        if kw.lower() in text_lower:
            return {
                "reply_text": None,
                "confidence": 0,
                "should_escalate": True,
                "escalation_reason": f"keyword:{kw}",
            }

    # Build context
    kb_context = await _get_kb_context_from_db(ticket.category or "duvida", db)

    # Build few-shot examples
    few_shot_text = ""
    if agent.few_shot_examples:
        examples = agent.few_shot_examples if isinstance(agent.few_shot_examples, list) else []
        for i, ex in enumerate(examples[:3], 1):
            few_shot_text += f"\n--- Exemplo {i} ---\nCliente: {ex.get('input', '')}\nResposta: {ex.get('output', '')}\n"

    # Build user message
    user_msg = f"Assunto: {ticket.subject or 'Sem assunto'}\nCliente: {customer_name}\nCategoria: {ticket.category or 'geral'}\n"
    if ticket.protocol:
        user_msg += f"Protocolo: {ticket.protocol}\n"

    # Add order data if available
    if order_data:
        from app.services.email_auto_reply_service import _format_order_context
        order_context = _format_order_context(order_data)
        user_msg += f"\n=== DADOS REAIS DO PEDIDO ===\n{order_context}\n=== FIM DADOS ===\n"

    user_msg += f"\nEmail do cliente:\n{email_body[:2000]}"
    if kb_context:
        user_msg += f"\n\n--- Base de Conhecimento ---\n{kb_context}"
    if few_shot_text:
        user_msg += f"\n\n--- Exemplos de Resposta ---\n{few_shot_text}"

    try:
        ai = ai_service.get_client()
        response = await ai_service._call_with_retry(
            lambda: ai.messages.create(
                model=settings.ANTHROPIC_AGENT_MODEL or settings.ANTHROPIC_MODEL,
                max_tokens=800,
                system=agent.system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
        )
        reply_text = response.content[0].text.strip()

        # Calculate confidence based on response quality signals
        confidence = _estimate_confidence(reply_text, agent, text_lower)

        return {
            "reply_text": reply_text,
            "confidence": confidence,
            "should_escalate": False,
            "escalation_reason": None,
        }
    except Exception as e:
        ai_service._handle_credit_error(e)
        logger.error(f"Agent {agent.name} reply generation failed: {e}")
        return {"reply_text": None, "confidence": 0, "should_escalate": False, "escalation_reason": f"error:{e}"}


def _estimate_confidence(reply_text: str, agent: AIAgent, original_text: str) -> float:
    """Estimate confidence of the generated reply.

    Higher confidence when:
    - Reply is substantive (not too short)
    - No hedging language
    - Agent category matches well
    """
    confidence = 0.8  # Base confidence

    # Short replies indicate uncertainty
    if len(reply_text) < 100:
        confidence -= 0.15

    # Hedging language reduces confidence
    hedging = ["nao tenho certeza", "nao sei", "vou verificar", "equipe vai analisar",
               "encaminhar", "escalar", "supervisor"]
    for h in hedging:
        if h in reply_text.lower():
            confidence -= 0.1
            break

    # Complex topics reduce confidence
    complex_signals = ["garantia", "defeito", "reembolso", "estorno", "troca", "cancelar"]
    for s in complex_signals:
        if s in original_text:
            confidence -= 0.05

    return max(0.1, min(1.0, confidence))


async def should_auto_send(agent: AIAgent, confidence: float) -> bool:
    """Check if this reply should be sent automatically."""
    return agent.auto_send and confidence >= agent.confidence_threshold
