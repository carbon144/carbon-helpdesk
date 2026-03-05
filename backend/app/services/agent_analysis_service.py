"""Agent deep analysis service."""
import json
import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract

from app.models.ticket import Ticket
from app.models.message import Message
from app.models.csat import CSATRating

logger = logging.getLogger(__name__)


async def calculate_quantitative_metrics(
    db: AsyncSession, agent_id: str, period_start: datetime, period_end: datetime
) -> dict:
    """Calculate all quantitative metrics for an agent in a period.

    Uses separate simple queries for robustness — each metric is independent
    so a failure in one doesn't break the rest.
    """
    from app.models.user import User

    metrics = {
        "tickets_total": 0,
        "tickets_resolved": 0,
        "tickets_escalated": 0,
        "avg_first_response_h": 0,
        "avg_resolution_h": 0,
        "sla_compliance_pct": 0,
        "csat_avg": 0,
        "csat_count": 0,
        "fcr_rate": 0,
        "messages_per_ticket_avg": 0,
        "tickets_by_category": {},
        "hourly_distribution": {},
        "daily_volume": [],
    }

    # Get agent info for sender matching
    agent = await db.get(User, agent_id)

    # Find tickets where agent acted: currently assigned OR sent outbound messages
    # This ensures reassigned tickets still count for the original agent
    acted_ticket_ids_q = select(Message.ticket_id).where(
        Message.type == "outbound",
        Message.created_at >= period_start,
        Message.created_at <= period_end,
    )
    if agent:
        email_prefix = agent.email.split("@")[0] if agent.email else ""
        acted_ticket_ids_q = acted_ticket_ids_q.where(
            or_(
                func.coalesce(Message.sender_email, "").ilike(f"%{email_prefix}%"),
                func.coalesce(Message.sender_name, "").ilike(f"%{agent.name}%"),
            )
        )
    acted_ticket_ids_q = acted_ticket_ids_q.distinct()

    period_filter = or_(
        and_(Ticket.created_at >= period_start, Ticket.created_at <= period_end),
        and_(Ticket.updated_at >= period_start, Ticket.updated_at <= period_end),
        and_(Ticket.resolved_at.isnot(None), Ticket.resolved_at >= period_start, Ticket.resolved_at <= period_end),
    )

    # Base filter: tickets assigned to agent OR where agent sent messages, active in period
    base_where = [
        or_(
            Ticket.assigned_to == agent_id,
            Ticket.id.in_(acted_ticket_ids_q),
        ),
        period_filter,
    ]

    # ── Total tickets ──
    try:
        r = await db.execute(select(func.count(Ticket.id)).where(*base_where))
        metrics["tickets_total"] = r.scalar() or 0
    except Exception as e:
        logger.error(f"Metrics: tickets_total failed: {e}")

    total = metrics["tickets_total"]

    # ── Resolved tickets ──
    try:
        r = await db.execute(
            select(func.count(Ticket.id)).where(
                *base_where,
                Ticket.status.in_(["resolved", "closed"]),
            )
        )
        metrics["tickets_resolved"] = r.scalar() or 0
    except Exception as e:
        logger.error(f"Metrics: tickets_resolved failed: {e}")

    resolved = metrics["tickets_resolved"]

    # ── Escalated tickets ──
    try:
        r = await db.execute(
            select(func.count(Ticket.id)).where(
                *base_where,
                Ticket.status == "escalated",
            )
        )
        metrics["tickets_escalated"] = r.scalar() or 0
    except Exception as e:
        logger.error(f"Metrics: tickets_escalated failed: {e}")

    # ── SLA compliance ──
    try:
        r = await db.execute(
            select(func.count(Ticket.id)).where(
                *base_where,
                Ticket.status.in_(["resolved", "closed"]),
                Ticket.sla_breached == False,
            )
        )
        sla_ok = r.scalar() or 0
        metrics["sla_compliance_pct"] = round((sla_ok / resolved * 100) if resolved > 0 else 100, 1)
    except Exception as e:
        logger.error(f"Metrics: sla_compliance_pct failed: {e}")

    # ── Avg first response time ──
    try:
        r = await db.execute(
            select(
                func.avg(extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
            ).where(
                *base_where,
                Ticket.first_response_at.isnot(None),
            )
        )
        val = r.scalar()
        metrics["avg_first_response_h"] = round(float(val), 1) if val else 0
    except Exception as e:
        logger.error(f"Metrics: avg_first_response_h failed: {e}")

    # ── Avg resolution time ──
    try:
        r = await db.execute(
            select(
                func.avg(extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
            ).where(
                *base_where,
                Ticket.resolved_at.isnot(None),
            )
        )
        val = r.scalar()
        metrics["avg_resolution_h"] = round(float(val), 1) if val else 0
    except Exception as e:
        logger.error(f"Metrics: avg_resolution_h failed: {e}")

    # ── FCR (resolved within 5 min of first response) ──
    try:
        r = await db.execute(
            select(func.count(Ticket.id)).where(
                *base_where,
                Ticket.status.in_(["resolved", "closed"]),
                Ticket.first_response_at.isnot(None),
                Ticket.resolved_at.isnot(None),
                extract("epoch", Ticket.resolved_at - Ticket.first_response_at) < 300,
            )
        )
        fcr_count = r.scalar() or 0
        metrics["fcr_rate"] = round((fcr_count / resolved * 100) if resolved > 0 else 0, 1)
    except Exception as e:
        logger.error(f"Metrics: fcr_rate failed: {e}")

    # ── CSAT ──
    try:
        r = await db.execute(
            select(
                func.avg(CSATRating.score),
                func.count(CSATRating.id),
            ).where(
                CSATRating.agent_id == agent_id,
                CSATRating.created_at >= period_start,
                CSATRating.created_at <= period_end,
            )
        )
        row = r.one()
        metrics["csat_avg"] = round(float(row[0]), 1) if row[0] else 0
        metrics["csat_count"] = row[1] or 0
    except Exception as e:
        logger.error(f"Metrics: csat failed: {e}")

    # ── Messages per ticket ──
    try:
        ticket_ids_q = select(Ticket.id).where(*base_where)
        r = await db.execute(
            select(func.count(Message.id)).where(
                Message.type == "outbound",
                Message.ticket_id.in_(ticket_ids_q),
            )
        )
        total_outbound = r.scalar() or 0
        metrics["messages_per_ticket_avg"] = round(total_outbound / total, 1) if total > 0 else 0
    except Exception as e:
        logger.error(f"Metrics: messages_per_ticket failed: {e}")

    # ── Tickets by category ──
    try:
        r = await db.execute(
            select(Ticket.category, func.count(Ticket.id))
            .where(*base_where)
            .group_by(Ticket.category)
        )
        metrics["tickets_by_category"] = {(row[0] or "sem_categoria"): row[1] for row in r.all()}
    except Exception as e:
        logger.error(f"Metrics: tickets_by_category failed: {e}")

    # ── Hourly distribution ──
    try:
        ticket_ids_broad = select(Ticket.id).where(*base_where)
        r = await db.execute(
            select(
                extract("hour", Message.created_at).label("h"),
                func.count(Message.id),
            ).where(
                Message.type == "outbound",
                Message.created_at >= period_start,
                Message.created_at <= period_end,
                Message.ticket_id.in_(ticket_ids_broad),
            ).group_by("h").order_by("h")
        )
        metrics["hourly_distribution"] = {int(row[0]): row[1] for row in r.all()}
    except Exception as e:
        logger.error(f"Metrics: hourly_distribution failed: {e}")

    # ── Daily volume ──
    try:
        r = await db.execute(
            select(
                func.date_trunc("day", Ticket.created_at).label("day"),
                func.count(Ticket.id),
            ).where(*base_where)
            .group_by("day").order_by("day")
        )
        metrics["daily_volume"] = [{"date": row[0].isoformat()[:10], "count": row[1]} for row in r.all()]
    except Exception as e:
        logger.error(f"Metrics: daily_volume failed: {e}")

    logger.info(f"Metrics for agent {agent_id}: total={metrics['tickets_total']}, resolved={metrics['tickets_resolved']}")
    return metrics


async def fetch_kb_context(db: AsyncSession) -> str:
    """Fetch macros and KB articles to give the AI context about templates and policies."""
    from app.models.macro import Macro
    from app.models.kb_article import KBArticle

    parts = []

    try:
        r = await db.execute(select(Macro.name, Macro.content, Macro.category).where(Macro.is_active == True))
        macros = r.all()
        if macros:
            parts.append("TEMPLATES/MACROS DISPONIVEIS (respostas prontas que os atendentes podem usar):")
            for m in macros:
                parts.append(f"- [{m[2] or 'geral'}] {m[0]}: {m[1][:200]}")
    except Exception as e:
        logger.error(f"Failed to fetch macros: {e}")

    try:
        r = await db.execute(
            select(KBArticle.title, KBArticle.content, KBArticle.category)
            .where(KBArticle.is_published == True)
        )
        articles = r.all()
        if articles:
            parts.append("\nBASE DE CONHECIMENTO (politicas e procedimentos oficiais):")
            for a in articles:
                parts.append(f"- [{a[2]}] {a[0]}: {a[1][:300]}")
    except Exception as e:
        logger.error(f"Failed to fetch KB articles: {e}")

    return "\n".join(parts) if parts else ""


async def generate_ai_analysis(agent_name: str, messages: list[str], metrics: dict = None, kb_context: str = "") -> dict:
    """Send agent messages to Claude for qualitative analysis using tool_use for guaranteed valid JSON."""
    from app.services.ai_service import get_client, is_credits_exhausted, _handle_credit_error, _call_with_retry

    if is_credits_exhausted():
        return {"error": "credits_exhausted"}

    try:
        ai = get_client()
    except RuntimeError:
        return {"error": "AI not configured"}

    messages_text = "\n---\n".join(messages[:200])

    # Build metrics context if available
    metrics_context = ""
    if metrics:
        metrics_context = f"""
METRICAS QUANTITATIVAS DO PERIODO:
- Tickets totais: {metrics.get('tickets_total', 0)}
- Tickets resolvidos: {metrics.get('tickets_resolved', 0)}
- Tickets escalados: {metrics.get('tickets_escalated', 0)}
- SLA cumprido: {metrics.get('sla_compliance_pct', 0)}%
- Tempo medio 1a resposta: {metrics.get('avg_first_response_h', 0)}h
- Tempo medio resolucao: {metrics.get('avg_resolution_h', 0)}h
- CSAT medio: {metrics.get('csat_avg', 0)} ({metrics.get('csat_count', 0)} avaliacoes)
- FCR (resolucao no 1o contato): {metrics.get('fcr_rate', 0)}%
- Media de mensagens por ticket: {metrics.get('messages_per_ticket_avg', 0)}

Use estas metricas para contextualizar sua analise qualitativa.
"""

    # Build KB/guidelines context
    kb_section = ""
    if kb_context:
        kb_section = f"""
{kb_context}

IMPORTANTE SOBRE TEMPLATES: Compare as mensagens do atendente com os templates/macros acima.
- Se o atendente usa templates sem nenhuma personalizacao, penalize em PERSONALIZACAO.
- Se personaliza e adapta os templates ao contexto do cliente, valorize.
- Se segue os procedimentos documentados na base de conhecimento, valorize em ADERENCIA AO PLAYBOOK.
- Se contradiz ou ignora as politicas oficiais, penalize com exemplos concretos.
"""

    prompt = f"""Voce e um supervisor senior de atendimento ao cliente da Carbon (marca brasileira de smartwatches e acessorios).
A diretora e co-fundadora e a Lyvia, e o gerente de atendimento e o Victor.
Faca uma analise profunda das mensagens do atendente "{agent_name}".
{metrics_context}{kb_section}
Avalie cada criterio de 1 a 10 com rigor (9-10 excepcional, 7-8 bom, 5-6 regular, <5 insuficiente):

1. TOM E EMPATIA - Acolhimento genuino, cordialidade, usa nome do cliente
2. CLAREZA - Explicacoes sem ambiguidade, instrucoes claras
3. ADERENCIA AO PLAYBOOK - Procedimentos corretos, pediu dados necessarios
4. PROATIVIDADE - Antecipou duvidas, ofereceu alternativas
5. PORTUGUES - Gramatica, ortografia, acentuacao, formalidade
6. RESOLUCAO EFETIVA - Resolveu o problema ou enrolou
7. CONHECIMENTO TECNICO - Dominio sobre produtos Carbon
8. GESTAO DE CONFLITOS - Como lida com clientes irritados
9. PERSONALIZACAO - Respostas personalizadas vs copiar/colar
10. SENSO DE URGENCIA - Prioriza casos criticos

DIAGNOSTICO DE PORTUGUES - Para cada categoria, liste erros REAIS das mensagens:
- ortografia_acentuacao: palavras erradas, falta de acentos
- informalidade: abreviacoes (vc, tb, pq), girias
- gramatica_concordancia: concordancia verbal/nominal, regencia
- pontuacao_estrutura: falta de virgulas, frases sem ponto
- formalidade: nivel adequado para representar uma marca

REGRAS: NUNCA invente dados. Use SOMENTE trechos reais. Se nao encontrar erros, score 10 e errors vazio.

Use a tool "submit_analysis" para enviar sua analise.

MENSAGENS ({len(messages)} analisadas):
{messages_text}"""

    # Tool definition — forces structured JSON output
    analysis_tool = {
        "name": "submit_analysis",
        "description": "Submit the complete agent performance analysis",
        "input_schema": {
            "type": "object",
            "required": ["scores", "summary", "strengths", "improvements", "recommendations",
                         "notable_examples", "training_priorities", "portuguese_diagnosis"],
            "properties": {
                "scores": {
                    "type": "object",
                    "required": ["tone_empathy", "clarity", "playbook_adherence", "proactivity",
                                 "grammar", "resolution_quality", "technical_knowledge",
                                 "conflict_management", "personalization", "urgency_awareness", "overall"],
                    "properties": {k: {"type": "number", "minimum": 1, "maximum": 10}
                                   for k in ["tone_empathy", "clarity", "playbook_adherence", "proactivity",
                                             "grammar", "resolution_quality", "technical_knowledge",
                                             "conflict_management", "personalization", "urgency_awareness", "overall"]},
                },
                "summary": {"type": "string", "description": "Parecer geral detalhado em 4-6 paragrafos"},
                "strengths": {"type": "array", "items": {"type": "string"}, "description": "Pontos fortes com exemplos reais"},
                "improvements": {"type": "array", "items": {"type": "string"}, "description": "Melhorias com exemplos reais"},
                "recommendations": {"type": "array", "items": {"type": "string"}, "description": "Acoes concretas de treinamento"},
                "notable_examples": {
                    "type": "object",
                    "properties": {
                        "best": {"type": "string", "description": "Melhor mensagem e por que"},
                        "worst": {"type": "string", "description": "Pior mensagem e como deveria ter sido"},
                    },
                },
                "training_priorities": {"type": "array", "items": {"type": "string"}},
                "portuguese_diagnosis": {
                    "type": "object",
                    "required": ["level", "overall_score", "categories", "top_corrections", "training_suggestion"],
                    "properties": {
                        "level": {"type": "string", "enum": ["basico", "intermediario", "avancado"]},
                        "overall_score": {"type": "number", "minimum": 1, "maximum": 10},
                        "categories": {
                            "type": "object",
                            "properties": {
                                cat: {
                                    "type": "object",
                                    "properties": {
                                        "score": {"type": "number", "minimum": 1, "maximum": 10},
                                        "severity": {"type": "string", "enum": ["critico", "moderado", "leve"]},
                                        "frequency": {"type": "string", "enum": ["frequente", "ocasional", "raro"]},
                                        "errors": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "wrote": {"type": "string"},
                                                    "correct": {"type": "string"},
                                                    "context": {"type": "string"},
                                                },
                                            },
                                        },
                                    },
                                }
                                for cat in ["ortografia_acentuacao", "informalidade",
                                            "gramatica_concordancia", "pontuacao_estrutura", "formalidade"]
                            },
                        },
                        "top_corrections": {"type": "array", "items": {"type": "string"}},
                        "training_suggestion": {"type": "string"},
                    },
                },
            },
        },
    }

    try:
        response = await _call_with_retry(
            lambda: ai.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}],
                tools=[analysis_tool],
                tool_choice={"type": "tool", "name": "submit_analysis"},
            )
        )

        # Extract the tool_use result — guaranteed valid JSON
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_analysis":
                return block.input

        # Fallback: if no tool_use block found, try text
        for block in response.content:
            if hasattr(block, "text") and block.text:
                return _robust_json_parse(block.text)

        return {"error": "AI returned no analysis"}
    except Exception as e:
        _handle_credit_error(e)
        logger.error(f"Agent analysis AI failed: {e}")
        return {"error": str(e)[:200]}


def _robust_json_parse(text: str) -> dict:
    """Fallback JSON parser for text responses."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"error": "Failed to parse AI response", "raw": text[:500]}


async def fetch_agent_messages(
    db: AsyncSession, agent_id: str, period_start: datetime, period_end: datetime,
    sample_size: Optional[int] = 50,
) -> list[str]:
    """Fetch outbound messages from an agent for AI analysis.

    Uses sender_email/sender_name to match messages actually sent by this agent,
    regardless of current ticket assignment. Falls back to ticket assignment
    if no sender match is found.
    """
    from app.models.user import User

    # Get agent info for matching
    agent = await db.get(User, agent_id)
    if not agent:
        return []

    # Primary: match by sender_email or sender_name (actual authorship)
    sender_filter = func.coalesce(Message.sender_email, "").ilike(f"%{agent.email.split('@')[0]}%")
    name_filter = func.coalesce(Message.sender_name, "").ilike(f"%{agent.name}%")

    q = (
        select(Message.body_text)
        .where(
            Message.type == "outbound",
            Message.body_text.isnot(None),
            Message.body_text != "",
            Message.created_at >= period_start,
            Message.created_at <= period_end,
            (sender_filter | name_filter),
        )
        .order_by(Message.created_at.desc())
    )
    if sample_size:
        q = q.limit(sample_size)

    result = await db.execute(q)
    messages = _filter_real_messages([row[0] for row in result.all()])

    # Fallback: if no sender match, use ticket assignment (legacy behavior)
    if not messages:
        q2 = (
            select(Message.body_text)
            .join(Ticket, Message.ticket_id == Ticket.id)
            .where(
                Ticket.assigned_to == agent_id,
                Message.type == "outbound",
                Message.body_text.isnot(None),
                Message.body_text != "",
                Message.created_at >= period_start,
                Message.created_at <= period_end,
            )
            .order_by(Message.created_at.desc())
        )
        if sample_size:
            q2 = q2.limit(sample_size)
        result2 = await db.execute(q2)
        messages = _filter_real_messages([row[0] for row in result2.all()])

    return messages


def _filter_real_messages(raw_messages: list) -> list[str]:
    """Filter out test messages, junk, and too-short messages."""
    # Patterns that indicate test/junk messages
    junk_patterns = re.compile(
        r'^(oi+|ola+|teste+|test|ok+|sim|nao|asdf|qwer|aaa+|bbb+|xxx+|kkk+|haha+|hehe+|oioioi|blabla|hello|hi)\s*[!?.]*$',
        re.IGNORECASE,
    )

    filtered = []
    for msg in raw_messages:
        if not msg:
            continue
        text = msg.strip()
        # Skip too short (less than 30 chars — real replies are longer)
        if len(text) < 30:
            continue
        # Skip junk/test patterns
        if junk_patterns.match(text):
            continue
        # Skip messages that are just signatures or greetings without substance
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) <= 1 and len(text) < 50:
            continue
        filtered.append(text)

    return filtered
