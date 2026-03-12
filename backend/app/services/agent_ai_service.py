"""Agent AI Service — routes tickets to specialized AI agents and generates replies.

Routing hierarchy:
  N1 (atendentes) — handle tickets directly, matched by category→sector
  N2 (coordenadores) — only receive escalations from N1 of same sector
  N3 (Carlos supervisor) — only receives escalations from N2
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.ai_agent import AIAgent
from app.models.ticket import Ticket
from app.models.kb_article import KBArticle
from app.services import ai_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# Maximum AI interactions before auto-escalation to N2
MAX_N1_INTERACTIONS = 3


async def get_agent_for_ticket(ticket: Ticket, db: AsyncSession) -> AIAgent | None:
    """Find the best AI agent for this ticket based on category → sector matching.

    Rules:
    - If ticket already has ai_agent_id (re-reply), return the SAME agent
    - Match by category: find N1 agents whose categories include this ticket's category
    - If multiple N1 match, pick the one with fewer total_replies (load balance)
    - NEVER route directly to N2/N3 — they only get escalations
    """
    if not ticket.category:
        return None

    # Re-reply: if ticket already assigned to an agent, return the same one
    if hasattr(ticket, 'ai_agent_id') and ticket.ai_agent_id:
        result = await db.execute(
            select(AIAgent).where(
                AIAgent.id == ticket.ai_agent_id,
                AIAgent.is_active == True,
            )
        )
        existing_agent = result.scalars().first()
        if existing_agent:
            logger.info(f"Re-reply: ticket #{ticket.number} reassigned to same agent {existing_agent.name}")
            return existing_agent

    # Get all active N1 agents (NEVER route directly to N2/N3)
    result = await db.execute(
        select(AIAgent).where(
            AIAgent.is_active == True,
            AIAgent.level == 1,
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

    # Load balance: pick N1 with fewer total_replies
    matching.sort(key=lambda a: (a.total_replies or 0))
    return matching[0]


async def get_coordinator_for_agent(agent: AIAgent, db: AsyncSession) -> AIAgent | None:
    """Return the N2 coordinator for a given N1 agent (same sector)."""
    if not agent.sector:
        return None

    result = await db.execute(
        select(AIAgent).where(
            AIAgent.is_active == True,
            AIAgent.level == 2,
            AIAgent.sector == agent.sector,
        )
    )
    coordinator = result.scalars().first()
    return coordinator


async def get_supervisor(db: AsyncSession) -> AIAgent | None:
    """Return Carlos (N3 supervisor)."""
    result = await db.execute(
        select(AIAgent).where(
            AIAgent.is_active == True,
            AIAgent.level == 3,
        )
    )
    return result.scalars().first()


async def escalate_to_coordinator(
    ticket: Ticket, current_agent: AIAgent, reason: str, db: AsyncSession
) -> AIAgent | None:
    """Escalate ticket from N1 to N2 coordinator of the same sector.

    Returns the N2 agent if escalation succeeded, None otherwise.
    """
    coordinator = await get_coordinator_for_agent(current_agent, db)
    if not coordinator:
        logger.warning(f"No N2 coordinator found for sector {current_agent.sector}, escalating to N3")
        return await escalate_to_supervisor(ticket, current_agent, reason, db)

    ticket.ai_agent_id = coordinator.id
    ticket.priority = max(ticket.priority or 1, 2)  # Bump priority on escalation
    logger.info(
        f"Escalation N1→N2: ticket #{ticket.number} from {current_agent.name} to {coordinator.name} — {reason}"
    )

    # Send Slack notification
    try:
        from app.services.slack_service import send_agent_escalation
        channel = coordinator.slack_channel or "#ia-operacao"
        await send_agent_escalation(current_agent.name, coordinator.name, ticket.number, reason, channel)
    except Exception as e:
        logger.error(f"Slack escalation notification failed: {e}")

    return coordinator


async def escalate_to_supervisor(
    ticket: Ticket, current_agent: AIAgent, reason: str, db: AsyncSession
) -> AIAgent | None:
    """Escalate ticket to Carlos (N3 supervisor).

    Returns Carlos agent if found, None otherwise.
    """
    carlos = await get_supervisor(db)
    if not carlos:
        logger.error("No N3 supervisor found — cannot escalate")
        return None

    ticket.ai_agent_id = carlos.id
    ticket.priority = max(ticket.priority or 1, 3)  # High priority for N3
    logger.info(
        f"Escalation →N3: ticket #{ticket.number} from {current_agent.name} to Carlos — {reason}"
    )

    # Send Slack notification
    try:
        from app.services.slack_service import send_agent_escalation
        channel = carlos.slack_channel or "#ia-pendencias"
        await send_agent_escalation(current_agent.name, carlos.name, ticket.number, reason, channel)
    except Exception as e:
        logger.error(f"Slack escalation notification failed: {e}")

    return carlos


async def check_auto_escalation(ticket: Ticket, agent: AIAgent, db: AsyncSession) -> AIAgent | None:
    """Check if ticket should be auto-escalated based on interaction count.

    After MAX_N1_INTERACTIONS without resolution → escalate N1→N2.
    When N2 sets should_escalate → escalate to Carlos (N3).
    """
    interaction_count = getattr(ticket, 'ai_interaction_count', 0) or 0

    if agent.level == 1 and interaction_count >= MAX_N1_INTERACTIONS:
        reason = f"Auto-escalacao: {interaction_count} interacoes sem resolucao"
        return await escalate_to_coordinator(ticket, agent, reason, db)

    if agent.level == 2:
        # N2 escalation is handled via should_escalate flag in generate_agent_reply
        pass

    return None


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

    # Special: client disputes delivery ("entregue" in tracking but says didn't receive)
    _delivery_dispute = (
        ("entregue" in text_lower or "entrega" in text_lower)
        and ("nao recebi" in text_lower or "não recebi" in text_lower or "nao chegou" in text_lower)
    )
    if _delivery_dispute:
        return {
            "reply_text": None,
            "confidence": 0,
            "should_escalate": True,
            "escalation_reason": "delivery_dispute_escalate",
        }

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
    - Agent sector matches the topic well
    - Agent specialty aligns with the request
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

    # Sector-specific boost: if agent specialty matches topic keywords, boost confidence
    sector_keywords = {
        "logistica": ["rastreio", "entrega", "correios", "transportadora", "envio", "prazo"],
        "garantia": ["defeito", "troca", "garantia", "assistencia", "reparo", "troquecommerce"],
        "retencao": ["cancelar", "estorno", "reembolso", "reclame aqui", "procon", "insatisfeito"],
        "operacional": ["pedido", "nota fiscal", "boleto", "pagamento", "pix"],
    }
    agent_sector = getattr(agent, 'sector', None)
    if agent_sector and agent_sector in sector_keywords:
        for kw in sector_keywords[agent_sector]:
            if kw in original_text:
                confidence += 0.03  # Small boost per matching keyword

    return max(0.1, min(1.0, confidence))


async def should_auto_send(agent: AIAgent, confidence: float) -> bool:
    """Check if this reply should be sent automatically."""
    return agent.auto_send and confidence >= agent.confidence_threshold
