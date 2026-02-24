from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Total tickets
    total = await db.execute(
        select(func.count()).select_from(Ticket).where(Ticket.created_at >= since)
    )
    total_tickets = total.scalar()

    # By status
    status_q = await db.execute(
        select(Ticket.status, func.count())
        .where(Ticket.created_at >= since)
        .group_by(Ticket.status)
    )
    by_status = {row[0]: row[1] for row in status_q.all()}

    # By priority
    priority_q = await db.execute(
        select(Ticket.priority, func.count())
        .where(Ticket.created_at >= since)
        .group_by(Ticket.priority)
    )
    by_priority = {row[0]: row[1] for row in priority_q.all()}

    # SLA breached
    breached = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.sla_breached == True)
    )
    sla_breached = breached.scalar()

    # Avg first response time (in hours)
    avg_response = await db.execute(
        select(
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
        ).where(Ticket.first_response_at.isnot(None), Ticket.created_at >= since)
    )
    avg_response_hours = round(avg_response.scalar() or 0, 1)

    # Avg resolution time (in hours)
    avg_resolution = await db.execute(
        select(
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
        ).where(Ticket.resolved_at.isnot(None), Ticket.created_at >= since)
    )
    avg_resolution_hours = round(avg_resolution.scalar() or 0, 1)

    # Legal risk count
    legal = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.legal_risk == True)
    )
    legal_risk_count = legal.scalar()

    # By category
    cat_q = await db.execute(
        select(Ticket.category, func.count())
        .where(Ticket.created_at >= since, Ticket.category.isnot(None))
        .group_by(Ticket.category)
    )
    by_category = {row[0]: row[1] for row in cat_q.all()}

    # Daily volume (last N days)
    daily_q = await db.execute(
        select(
            func.date(Ticket.created_at).label("day"),
            func.count().label("count"),
        )
        .where(Ticket.created_at >= since)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
    )
    daily_volume = [{"date": str(row[0]), "count": row[1]} for row in daily_q.all()]

    # By source
    source_q = await db.execute(
        select(Ticket.source, func.count())
        .where(Ticket.created_at >= since, Ticket.source.isnot(None))
        .group_by(Ticket.source)
    )
    by_source = {row[0]: row[1] for row in source_q.all()}

    # By sentiment
    sentiment_q = await db.execute(
        select(Ticket.sentiment, func.count())
        .where(Ticket.created_at >= since, Ticket.sentiment.isnot(None))
        .group_by(Ticket.sentiment)
    )
    by_sentiment = {row[0]: row[1] for row in sentiment_q.all()}

    # Trocas count
    trocas = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.category == "troca")
    )
    trocas_count = trocas.scalar()

    # Reclamações count
    reclamacoes = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.category == "reclamacao")
    )
    reclamacoes_count = reclamacoes.scalar()

    # Problemas (garantia + mau_uso + suporte_tecnico + carregador)
    problemas = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.category.in_(["garantia", "mau_uso", "suporte_tecnico", "carregador"]))
    )
    problemas_count = problemas.scalar()

    # Escalated count
    escalated = by_status.get("escalated", 0)

    # Open tickets (not resolved/closed)
    open_tickets = sum(v for k, v in by_status.items() if k not in ("resolved", "closed"))

    # Resolved today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.resolved_at >= today_start)
    )
    resolved_today = resolved_today_q.scalar()

    # Responded today (distinct tickets with outbound messages today)
    responded_result = await db.execute(
        select(func.count(func.distinct(Message.ticket_id)))
        .where(
            Message.type == "outbound",
            Message.created_at >= today_start,
        )
    )
    responded_today = responded_result.scalar() or 0

    # FCR - First Contact Resolution (resolved tickets with <=1 outbound message)
    from sqlalchemy import literal_column
    fcr_subq = (
        select(
            Message.ticket_id,
            func.count().label("outbound_count")
        )
        .where(Message.type == "outbound")
        .group_by(Message.ticket_id)
        .subquery()
    )
    fcr_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .outerjoin(fcr_subq, Ticket.id == fcr_subq.c.ticket_id)
        .where(
            Ticket.created_at >= since,
            Ticket.status == "resolved",
            func.coalesce(fcr_subq.c.outbound_count, 0) <= 1,
        )
    )
    fcr_count = fcr_q.scalar() or 0
    total_resolved = by_status.get("resolved", 0)
    fcr_rate = round((fcr_count / max(total_resolved, 1)) * 100, 1) if total_resolved > 0 else 0

    # Unassigned tickets
    unassigned_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.assigned_to.is_(None), Ticket.status.notin_(["resolved", "closed"]))
    )
    unassigned_count = unassigned_q.scalar()

    return {
        "period_days": days,
        "total_tickets": total_tickets,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "by_source": by_source,
        "by_sentiment": by_sentiment,
        "sla_breached": sla_breached,
        "sla_compliance": round((1 - sla_breached / max(total_tickets, 1)) * 100, 1),
        "avg_response_hours": avg_response_hours,
        "avg_resolution_hours": avg_resolution_hours,
        "legal_risk_count": legal_risk_count,
        "daily_volume": daily_volume,
        "trocas_count": trocas_count,
        "reclamacoes_count": reclamacoes_count,
        "problemas_count": problemas_count,
        "escalated_count": escalated,
        "open_tickets": open_tickets,
        "resolved_today": resolved_today,
        "responded_today": responded_today,
        "fcr_count": fcr_count,
        "fcr_rate": fcr_rate,
        "unassigned_count": unassigned_count,
    }


@router.get("/agent-stats")
async def get_agent_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stats específicas do agente logado."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Meus tickets abertos
    my_open = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.assigned_to == user.id, Ticket.status.notin_(["resolved", "closed"]))
    )
    my_open_count = my_open.scalar()

    # Meus tickets resolvidos no período
    my_resolved = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.assigned_to == user.id, Ticket.resolved_at >= since)
    )
    my_resolved_count = my_resolved.scalar()

    # Meu tempo médio de resposta
    my_avg_resp = await db.execute(
        select(
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
        ).where(
            Ticket.assigned_to == user.id,
            Ticket.first_response_at.isnot(None),
            Ticket.created_at >= since,
        )
    )
    my_avg_response = round(my_avg_resp.scalar() or 0, 1)

    # Meu SLA
    my_sla_breach = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.assigned_to == user.id, Ticket.created_at >= since, Ticket.sla_breached == True)
    )
    my_sla_breached = my_sla_breach.scalar()

    my_total = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.assigned_to == user.id, Ticket.created_at >= since)
    )
    my_total_count = my_total.scalar()

    # Meus tickets por categoria
    my_cat_q = await db.execute(
        select(Ticket.category, func.count())
        .where(Ticket.assigned_to == user.id, Ticket.created_at >= since, Ticket.category.isnot(None))
        .group_by(Ticket.category)
    )
    my_by_category = {row[0]: row[1] for row in my_cat_q.all()}

    # Meus tickets por status
    my_status_q = await db.execute(
        select(Ticket.status, func.count())
        .where(Ticket.assigned_to == user.id, Ticket.created_at >= since)
        .group_by(Ticket.status)
    )
    my_by_status = {row[0]: row[1] for row in my_status_q.all()}

    return {
        "my_open": my_open_count,
        "my_resolved": my_resolved_count,
        "my_total": my_total_count,
        "my_avg_response_hours": my_avg_response,
        "my_sla_breached": my_sla_breached,
        "my_sla_compliance": round((1 - my_sla_breached / max(my_total_count, 1)) * 100, 1),
        "my_by_category": my_by_category,
        "my_by_status": my_by_status,
    }
