"""Reports, CSAT, NPS, and AI agent analysis endpoints."""
import logging
import json as json_lib
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, or_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.customer import Customer
from app.models.csat import CSATRating

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


# ── Agent Performance ──

@router.get("/agents")
async def agent_performance(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    q = await db.execute(
        select(
            User.id,
            User.name,
            func.count(Ticket.id).label("total"),
            func.count().filter(Ticket.status == "resolved").label("resolved"),
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
                .filter(Ticket.resolved_at.isnot(None)).label("avg_resolution_h"),
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
                .filter(Ticket.first_response_at.isnot(None)).label("avg_response_h"),
            func.count().filter(Ticket.sla_breached == True).label("sla_breached"),
        )
        .join(User, Ticket.assigned_to == User.id)
        .where(Ticket.created_at >= since)
        .group_by(User.id, User.name)
        .order_by(func.count(Ticket.id).desc())
    )

    # Pre-fetch all CSAT data in a single query (avoid O(n) per-agent queries)
    csat_q = await db.execute(
        select(
            CSATRating.agent_id,
            func.avg(CSATRating.score),
            func.count(CSATRating.id),
            func.avg(CSATRating.nps_score),
        ).where(CSATRating.created_at >= since)
        .group_by(CSATRating.agent_id)
    )
    csat_map = {}
    for crow in csat_q.all():
        csat_map[crow[0]] = {"avg": crow[1], "count": crow[2], "nps": crow[3]}

    agents = []
    for row in q.all():
        csat_data = csat_map.get(row[0], {"avg": 0, "count": 0, "nps": 0})
        total = max(row[2], 1)
        agents.append({
            "id": row[0],
            "name": row[1],
            "total_tickets": row[2],
            "resolved": row[3],
            "resolution_rate": round((row[3] / total) * 100, 1),
            "avg_resolution_hours": round(row[4] or 0, 1),
            "avg_response_hours": round(row[5] or 0, 1),
            "sla_breached": row[6],
            "sla_compliance": round((1 - row[6] / total) * 100, 1),
            "csat_avg": round(csat_data["avg"] or 0, 2),
            "csat_count": csat_data["count"] or 0,
            "nps_avg": round(csat_data["nps"] or 0, 1),
        })

    return {"period_days": days, "agents": agents}


# ── CSAT & NPS ──

@router.get("/csat")
async def csat_report(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Overall CSAT
    overall = await db.execute(
        select(
            func.avg(CSATRating.score),
            func.count(CSATRating.id),
        ).where(CSATRating.created_at >= since)
    )
    overall_row = overall.one()

    # CSAT distribution (1-5)
    dist_q = await db.execute(
        select(CSATRating.score, func.count())
        .where(CSATRating.created_at >= since)
        .group_by(CSATRating.score)
        .order_by(CSATRating.score)
    )
    distribution = {str(r[0]): r[1] for r in dist_q.all()}

    # NPS calculation
    nps_q = await db.execute(
        select(CSATRating.nps_score)
        .where(CSATRating.created_at >= since, CSATRating.nps_score.isnot(None))
    )
    nps_scores = [r[0] for r in nps_q.all()]
    promoters = sum(1 for s in nps_scores if s >= 9)
    detractors = sum(1 for s in nps_scores if s <= 6)
    nps_total = len(nps_scores)
    nps_score = round(((promoters - detractors) / max(nps_total, 1)) * 100, 1) if nps_total > 0 else 0

    # Daily CSAT trend
    daily_q = await db.execute(
        select(
            func.date(CSATRating.created_at).label("day"),
            func.avg(CSATRating.score).label("avg"),
            func.count().label("count"),
        )
        .where(CSATRating.created_at >= since)
        .group_by(func.date(CSATRating.created_at))
        .order_by(func.date(CSATRating.created_at))
    )
    daily_trend = [{"date": str(r[0]), "avg": round(r[1], 2), "count": r[2]} for r in daily_q.all()]

    # Recent comments
    comments_q = await db.execute(
        select(CSATRating)
        .where(CSATRating.created_at >= since, CSATRating.comment.isnot(None), CSATRating.comment != "")
        .order_by(CSATRating.created_at.desc())
        .limit(20)
    )
    recent_comments = [
        {
            "score": r.score,
            "nps_score": r.nps_score,
            "comment": r.comment,
            "date": r.created_at.isoformat(),
        }
        for r in comments_q.scalars().all()
    ]

    return {
        "period_days": days,
        "csat_avg": round(overall_row[0] or 0, 2),
        "total_ratings": overall_row[1] or 0,
        "distribution": distribution,
        "nps_score": nps_score,
        "nps_total": nps_total,
        "nps_promoters": promoters,
        "nps_detractors": detractors,
        "nps_passives": nps_total - promoters - detractors,
        "daily_trend": daily_trend,
        "recent_comments": recent_comments,
    }


# ── AI Agent Analysis ──

@router.get("/agent-analysis/{agent_id}")
async def agent_ai_analysis(
    agent_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI-powered analysis of individual agent performance."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get agent info
    agent_result = await db.execute(select(User).where(User.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agente não encontrado")

    # Collect metrics
    tickets_q = await db.execute(
        select(
            func.count(Ticket.id),
            func.count().filter(Ticket.status == "resolved"),
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
                .filter(Ticket.resolved_at.isnot(None)),
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
                .filter(Ticket.first_response_at.isnot(None)),
            func.count().filter(Ticket.sla_breached == True),
            func.count().filter(Ticket.legal_risk == True),
        )
        .where(Ticket.assigned_to == agent_id, Ticket.created_at >= since)
    )
    t = tickets_q.one()

    # Category breakdown
    cat_q = await db.execute(
        select(Ticket.category, func.count())
        .where(Ticket.assigned_to == agent_id, Ticket.created_at >= since, Ticket.category.isnot(None))
        .group_by(Ticket.category)
    )
    categories = {r[0]: r[1] for r in cat_q.all()}

    # Sentiment breakdown
    sent_q = await db.execute(
        select(Ticket.sentiment, func.count())
        .where(Ticket.assigned_to == agent_id, Ticket.created_at >= since, Ticket.sentiment.isnot(None))
        .group_by(Ticket.sentiment)
    )
    sentiments = {r[0]: r[1] for r in sent_q.all()}

    # CSAT for this agent
    csat_q = await db.execute(
        select(
            func.avg(CSATRating.score),
            func.count(CSATRating.id),
            func.avg(CSATRating.nps_score),
        ).where(CSATRating.agent_id == agent_id, CSATRating.created_at >= since)
    )
    csat = csat_q.one()

    # Get negative comments for context
    neg_comments = await db.execute(
        select(CSATRating.comment, CSATRating.score)
        .where(
            CSATRating.agent_id == agent_id,
            CSATRating.created_at >= since,
            CSATRating.score <= 2,
            CSATRating.comment.isnot(None),
        ).limit(5)
    )
    bad_feedback = [{"comment": r[0], "score": r[1]} for r in neg_comments.all()]

    pos_comments = await db.execute(
        select(CSATRating.comment, CSATRating.score)
        .where(
            CSATRating.agent_id == agent_id,
            CSATRating.created_at >= since,
            CSATRating.score >= 4,
            CSATRating.comment.isnot(None),
        ).limit(5)
    )
    good_feedback = [{"comment": r[0], "score": r[1]} for r in pos_comments.all()]

    metrics = {
        "agent_name": agent.name,
        "total_tickets": t[0],
        "resolved": t[1],
        "resolution_rate": round((t[1] / max(t[0], 1)) * 100, 1),
        "avg_resolution_hours": round(t[2] or 0, 1),
        "avg_response_hours": round(t[3] or 0, 1),
        "sla_breached": t[4],
        "sla_compliance": round((1 - t[4] / max(t[0], 1)) * 100, 1),
        "legal_risk_handled": t[5],
        "categories": categories,
        "sentiments": sentiments,
        "csat_avg": round(csat[0] or 0, 2),
        "csat_count": csat[1] or 0,
        "nps_avg": round(csat[2] or 0, 1),
        "bad_feedback": bad_feedback,
        "good_feedback": good_feedback,
    }

    # AI Analysis
    ai_analysis = None
    try:
        from app.services.ai_service import get_client
        import json

        ai = get_client()
        prompt = f"""Analise o desempenho deste agente de suporte e forneça feedback em JSON:

Agente: {agent.name}
Período: {days} dias
Tickets atendidos: {t[0]}
Resolvidos: {t[1]} ({metrics['resolution_rate']}%)
Tempo médio de resposta: {metrics['avg_response_hours']}h
Tempo médio de resolução: {metrics['avg_resolution_hours']}h
SLA cumprido: {metrics['sla_compliance']}%
Tickets risco jurídico: {t[5]}
CSAT médio: {metrics['csat_avg']}/5 ({metrics['csat_count']} avaliações)
NPS médio: {metrics['nps_avg']}
Categorias: {json.dumps(categories)}
Sentimentos: {json.dumps(sentiments)}
Feedback negativo: {json.dumps(bad_feedback[:3])}
Feedback positivo: {json.dumps(good_feedback[:3])}

Retorne APENAS JSON:
{{
  "nota_geral": 0-10,
  "pontos_fortes": ["lista de 3 pontos"],
  "pontos_melhoria": ["lista de 3 pontos"],
  "recomendacoes": ["lista de 3 recomendações"],
  "resumo": "resumo de 2 frases sobre o agente"
}}"""

        response = ai.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        ai_analysis = json.loads(response.content[0].text.strip())
    except Exception as e:
        logger.warning(f"AI agent analysis failed: {e}")

    return {
        "period_days": days,
        "metrics": metrics,
        "ai_analysis": ai_analysis,
    }


# ── Sources ──

@router.get("/sources")
async def tickets_by_source(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = await db.execute(
        select(func.coalesce(Ticket.source, "web").label("source"), func.count().label("count"))
        .where(Ticket.created_at >= since)
        .group_by(Ticket.source)
    )
    return {"period_days": days, "by_source": {row[0]: row[1] for row in q.all()}}


# ── Sentiment ──

@router.get("/sentiment")
async def sentiment_breakdown(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = await db.execute(
        select(Ticket.sentiment, func.count())
        .where(Ticket.created_at >= since, Ticket.sentiment.isnot(None))
        .group_by(Ticket.sentiment)
    )
    return {"period_days": days, "by_sentiment": {row[0]: row[1] for row in q.all()}}


# ── Top Customers ──

@router.get("/top-customers")
async def top_customers(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = await db.execute(
        select(
            Customer.name, Customer.email,
            func.count(Ticket.id).label("c"),
            Customer.risk_score,
        )
        .join(Customer, Ticket.customer_id == Customer.id)
        .where(Ticket.created_at >= since)
        .group_by(Customer.id, Customer.name, Customer.email, Customer.risk_score)
        .order_by(func.count(Ticket.id).desc())
        .limit(limit)
    )
    return {
        "period_days": days,
        "customers": [{"name": r[0], "email": r[1], "ticket_count": r[2], "risk_score": round(r[3] or 0, 2)} for r in q.all()],
    }


# ── Daily Trends (time series) ──

@router.get("/trends")
async def daily_trends(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Daily ticket volume, resolution, and response time trends."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    q = await db.execute(
        select(
            func.date(Ticket.created_at).label("day"),
            func.count(Ticket.id).label("total"),
            func.count().filter(Ticket.status == "resolved").label("resolved"),
            func.count().filter(Ticket.sla_breached == True).label("sla_breached"),
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
                .filter(Ticket.first_response_at.isnot(None)).label("avg_response_h"),
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
                .filter(Ticket.resolved_at.isnot(None)).label("avg_resolution_h"),
        )
        .where(Ticket.created_at >= since)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
    )

    return {
        "period_days": days,
        "trends": [
            {
                "date": str(r[0]),
                "total": r[1],
                "resolved": r[2],
                "sla_breached": r[3],
                "avg_response_hours": round(r[4] or 0, 1),
                "avg_resolution_hours": round(r[5] or 0, 1),
            }
            for r in q.all()
        ],
    }


# ── Patterns & Recurring Issues ──

@router.get("/patterns")
async def recurring_patterns(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Detect recurring patterns: repeat customers, common categories, high-risk areas."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Repeat customers (3+ tickets)
    repeat_q = await db.execute(
        select(Customer.name, Customer.email, func.count(Ticket.id).label("c"))
        .join(Customer, Ticket.customer_id == Customer.id)
        .where(Ticket.created_at >= since)
        .group_by(Customer.id, Customer.name, Customer.email)
        .having(func.count(Ticket.id) >= 3)
        .order_by(func.count(Ticket.id).desc())
        .limit(20)
    )
    repeat_customers = [{"name": r[0], "email": r[1], "count": r[2]} for r in repeat_q.all()]

    # Category + priority hotspots
    hotspot_q = await db.execute(
        select(
            Ticket.category, Ticket.priority,
            func.count(Ticket.id),
            func.count().filter(Ticket.sla_breached == True),
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
                .filter(Ticket.resolved_at.isnot(None)),
        )
        .where(Ticket.created_at >= since, Ticket.category.isnot(None))
        .group_by(Ticket.category, Ticket.priority)
        .order_by(func.count(Ticket.id).desc())
        .limit(20)
    )
    hotspots = [
        {
            "category": r[0], "priority": r[1], "count": r[2],
            "sla_breached": r[3],
            "avg_resolution_hours": round(r[4] or 0, 1),
        }
        for r in hotspot_q.all()
    ]

    # Common tags
    tag_q = await db.execute(
        select(func.unnest(Ticket.tags).label("tag"), func.count().label("c"))
        .where(Ticket.created_at >= since, Ticket.tags.isnot(None))
        .group_by("tag")
        .order_by(func.count().desc())
        .limit(15)
    )
    top_tags = [{"tag": r[0], "count": r[1]} for r in tag_q.all()]

    # Escalation rate
    esc_q = await db.execute(
        select(
            func.count(Ticket.id),
            func.count().filter(Ticket.status == "escalated"),
            func.count().filter(Ticket.legal_risk == True),
        ).where(Ticket.created_at >= since)
    )
    esc = esc_q.one()

    return {
        "period_days": days,
        "repeat_customers": repeat_customers,
        "hotspots": hotspots,
        "top_tags": top_tags,
        "total_tickets": esc[0],
        "escalated": esc[1],
        "escalation_rate": round((esc[1] / max(esc[0], 1)) * 100, 1),
        "legal_risk_count": esc[2],
    }


# ── Full AI Analysis (panorama geral) ──

@router.get("/ai-full-analysis")
async def ai_full_analysis(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Deep AI analysis of the entire helpdesk operation."""
    if user.role != "admin":
        raise HTTPException(403, "Apenas admins podem gerar análise completa")

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Collect all the data
    # Overall stats
    overall = await db.execute(
        select(
            func.count(Ticket.id),
            func.count().filter(Ticket.status == "resolved"),
            func.count().filter(Ticket.sla_breached == True),
            func.count().filter(Ticket.legal_risk == True),
            func.count().filter(Ticket.status == "escalated"),
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
                .filter(Ticket.first_response_at.isnot(None)),
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
                .filter(Ticket.resolved_at.isnot(None)),
        ).where(Ticket.created_at >= since)
    )
    o = overall.one()

    # By category
    cat_q = await db.execute(
        select(Ticket.category, func.count())
        .where(Ticket.created_at >= since, Ticket.category.isnot(None))
        .group_by(Ticket.category).order_by(func.count().desc())
    )
    categories = {r[0]: r[1] for r in cat_q.all()}

    # By sentiment
    sent_q = await db.execute(
        select(Ticket.sentiment, func.count())
        .where(Ticket.created_at >= since, Ticket.sentiment.isnot(None))
        .group_by(Ticket.sentiment)
    )
    sentiments = {r[0]: r[1] for r in sent_q.all()}

    # Agent performance summary
    agents_q = await db.execute(
        select(
            User.name,
            func.count(Ticket.id),
            func.count().filter(Ticket.status == "resolved"),
            func.count().filter(Ticket.sla_breached == True),
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
                .filter(Ticket.resolved_at.isnot(None)),
        )
        .join(User, Ticket.assigned_to == User.id)
        .where(Ticket.created_at >= since)
        .group_by(User.id, User.name)
    )
    agents_summary = [
        {"name": r[0], "total": r[1], "resolved": r[2], "sla_breached": r[3], "avg_resolution_h": round(r[4] or 0, 1)}
        for r in agents_q.all()
    ]

    # CSAT
    csat_q = await db.execute(
        select(func.avg(CSATRating.score), func.count(CSATRating.id))
        .where(CSATRating.created_at >= since)
    )
    csat = csat_q.one()

    # Negative feedback
    neg_q = await db.execute(
        select(CSATRating.comment, CSATRating.score)
        .where(CSATRating.created_at >= since, CSATRating.score <= 2, CSATRating.comment.isnot(None))
        .order_by(CSATRating.created_at.desc()).limit(10)
    )
    negative_feedback = [{"comment": r[0], "score": r[1]} for r in neg_q.all()]

    # Repeat customers
    repeat_q = await db.execute(
        select(func.count()).select_from(
            select(Customer.id)
            .join(Ticket, Ticket.customer_id == Customer.id)
            .where(Ticket.created_at >= since)
            .group_by(Customer.id)
            .having(func.count(Ticket.id) >= 3)
            .subquery()
        )
    )
    repeat_count = repeat_q.scalar() or 0

    data = {
        "periodo_dias": days,
        "total_tickets": o[0],
        "resolvidos": o[1],
        "taxa_resolucao": round((o[1] / max(o[0], 1)) * 100, 1),
        "sla_estourados": o[2],
        "sla_compliance": round((1 - o[2] / max(o[0], 1)) * 100, 1),
        "risco_juridico": o[3],
        "escalados": o[4],
        "tempo_medio_resposta_horas": round(o[5] or 0, 1),
        "tempo_medio_resolucao_horas": round(o[6] or 0, 1),
        "categorias": categories,
        "sentimentos": sentiments,
        "csat_medio": round(csat[0] or 0, 2),
        "total_avaliacoes": csat[1] or 0,
        "clientes_recorrentes": repeat_count,
        "agentes": agents_summary,
        "feedback_negativo": negative_feedback[:5],
    }

    # AI Analysis
    ai_analysis = None
    try:
        from app.services.ai_service import get_client

        ai = get_client()
        prompt = f"""Você é um consultor sênior de customer success. Analise profundamente a operação de suporte desta empresa de smartwatches e forneça insights acionáveis.

DADOS DO PERÍODO ({days} dias):
{json_lib.dumps(data, ensure_ascii=False, indent=2)}

Forneça análise DETALHADA em JSON com a seguinte estrutura:
{{
  "nota_operacao": 0-10,
  "resumo_executivo": "Resumo de 3-4 frases do estado geral da operação",
  "indicadores_criticos": [
    {{"indicador": "nome", "valor": "valor", "status": "bom/atencao/critico", "explicacao": "por que isso importa"}}
  ],
  "padroes_identificados": [
    {{"padrao": "descrição do padrão", "impacto": "alto/medio/baixo", "acao_sugerida": "o que fazer"}}
  ],
  "erros_recorrentes": [
    {{"problema": "descrição", "frequencia": "estimativa", "causa_provavel": "análise", "solucao": "recomendação"}}
  ],
  "analise_equipe": {{
    "destaque_positivo": "quem está performando bem e por que",
    "ponto_atencao": "quem precisa de suporte e por que",
    "recomendacao_treinamento": "que treinamento priorizar"
  }},
  "analise_clientes": {{
    "perfil_reclamacoes": "que tipo de cliente mais reclama",
    "risco_churn": "avaliação de risco de perda de clientes",
    "oportunidades": "onde melhorar experiência"
  }},
  "plano_acao": [
    {{"prioridade": 1, "acao": "o que fazer", "prazo": "curto/medio/longo", "impacto_esperado": "resultado esperado"}}
  ],
  "previsoes": {{
    "tendencia_volume": "aumentando/estavel/diminuindo",
    "areas_risco": ["lista de áreas que precisam atenção"],
    "oportunidades_melhoria": ["lista de quick wins"]
  }}
}}"""

        response = ai.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        ai_text = response.content[0].text.strip()
        # Try to extract JSON from response
        if "```json" in ai_text:
            ai_text = ai_text.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_text:
            ai_text = ai_text.split("```")[1].split("```")[0].strip()
        ai_analysis = json_lib.loads(ai_text)
    except Exception as e:
        logger.warning(f"AI full analysis failed: {e}")
        ai_analysis = {"error": str(e)}

    return {
        "period_days": days,
        "data": data,
        "ai_analysis": ai_analysis,
    }
