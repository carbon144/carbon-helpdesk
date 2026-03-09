from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message
from app.services.cache import cache_get, cache_set

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cache_key = f"dashboard:stats:{days}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Query 1: All ticket counts in one pass
    q1 = await db.execute(
        select(
            func.count().label("total"),
            # By status
            func.count(case((Ticket.status == "open", 1))).label("s_open"),
            func.count(case((Ticket.status == "in_progress", 1))).label("s_in_progress"),
            func.count(case((Ticket.status == "waiting", 1))).label("s_waiting"),
            func.count(case((Ticket.status == "waiting_supplier", 1))).label("s_waiting_supplier"),
            func.count(case((Ticket.status == "waiting_resend", 1))).label("s_waiting_resend"),
            func.count(case((Ticket.status == "analyzing", 1))).label("s_analyzing"),
            func.count(case((Ticket.status == "resolved", 1))).label("s_resolved"),
            func.count(case((Ticket.status == "closed", 1))).label("s_closed"),
            func.count(case((Ticket.status == "escalated", 1))).label("s_escalated"),
            # By priority
            func.count(case((Ticket.priority == "low", 1))).label("p_low"),
            func.count(case((Ticket.priority == "medium", 1))).label("p_medium"),
            func.count(case((Ticket.priority == "high", 1))).label("p_high"),
            func.count(case((Ticket.priority == "urgent", 1))).label("p_urgent"),
            # Flags
            func.count(case((Ticket.sla_breached == True, 1))).label("sla_breached"),
            func.count(case((Ticket.legal_risk == True, 1))).label("legal_risk"),
            # Resolved today
            func.count(case((Ticket.resolved_at >= today_start, 1))).label("resolved_today"),
            # Unassigned open
            func.count(case((and_(Ticket.assigned_to.is_(None), Ticket.status.notin_(["resolved", "closed"])), 1))).label("unassigned"),
        )
        .select_from(Ticket)
        .where(Ticket.created_at >= since)
    )
    r = q1.one()

    by_status = {}
    for s in ["open", "in_progress", "waiting", "waiting_supplier", "waiting_resend", "analyzing", "resolved", "closed", "escalated"]:
        val = getattr(r, f"s_{s}")
        if val:
            by_status[s] = val

    by_priority = {}
    for p in ["low", "medium", "high", "urgent"]:
        val = getattr(r, f"p_{p}")
        if val:
            by_priority[p] = val

    total_tickets = r.total

    # By category (dynamic - need separate small query)
    cat_q = await db.execute(
        select(Ticket.category, func.count())
        .where(Ticket.created_at >= since, Ticket.category.isnot(None))
        .group_by(Ticket.category)
    )
    by_category = {row[0]: row[1] for row in cat_q.all()}

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

    # Query 2: Time averages
    q2 = await db.execute(
        select(
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
            .filter(Ticket.first_response_at.isnot(None)).label("avg_resp"),
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
            .filter(Ticket.resolved_at.isnot(None)).label("avg_res"),
        )
        .where(Ticket.created_at >= since)
    )
    times = q2.one()
    avg_response_hours = round(times.avg_resp or 0, 1)
    avg_resolution_hours = round(times.avg_res or 0, 1)

    # Query 3: Daily volume
    daily_q = await db.execute(
        select(func.date(Ticket.created_at).label("day"), func.count().label("count"))
        .where(Ticket.created_at >= since)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
    )
    daily_volume = [{"date": str(row[0]), "count": row[1]} for row in daily_q.all()]

    # Query 4: Responded today + FCR (messages)
    responded_result = await db.execute(
        select(func.count(func.distinct(Message.ticket_id)))
        .where(Message.type == "outbound", Message.created_at >= today_start)
    )
    responded_today = responded_result.scalar() or 0

    # FCR - with date filter fix
    fcr_subq = (
        select(Message.ticket_id, func.count().label("outbound_count"))
        .where(Message.type == "outbound", Message.created_at >= since)
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

    open_tickets = sum(v for k, v in by_status.items() if k not in ("resolved", "closed"))

    result = {
        "period_days": days,
        "total_tickets": total_tickets,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "by_source": by_source,
        "by_sentiment": by_sentiment,
        "sla_breached": r.sla_breached,
        "sla_compliance": round((1 - r.sla_breached / max(total_tickets, 1)) * 100, 1),
        "avg_response_hours": avg_response_hours,
        "avg_resolution_hours": avg_resolution_hours,
        "legal_risk_count": r.legal_risk,
        "daily_volume": daily_volume,
        "escalated_count": by_status.get("escalated", 0),
        "open_tickets": open_tickets,
        "resolved_today": r.resolved_today,
        "responded_today": responded_today,
        "fcr_count": fcr_count,
        "fcr_rate": fcr_rate,
        "unassigned_count": r.unassigned,
    }

    await cache_set(cache_key, result, ttl_seconds=300)
    return result


@router.get("/agent-stats")
async def get_agent_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stats específicas do agente logado."""
    cache_key = f"dashboard:agent:{user.id}:{days}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

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

    result = {
        "my_open": my_open_count,
        "my_resolved": my_resolved_count,
        "my_total": my_total_count,
        "my_avg_response_hours": my_avg_response,
        "my_sla_breached": my_sla_breached,
        "my_sla_compliance": round((1 - my_sla_breached / max(my_total_count, 1)) * 100, 1),
        "my_by_category": my_by_category,
        "my_by_status": my_by_status,
    }

    await cache_set(cache_key, result, ttl_seconds=120)
    return result


@router.get("/leader")
async def get_leader_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dashboard do lider: KPIs por agente, presenca, alertas."""
    from app.services.triage_service import get_online_agents

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # All agents
    agents_result = await db.execute(
        select(User).where(User.is_active == True, User.role.in_(["agent", "supervisor", "admin"]))
    )
    all_agents = agents_result.scalars().all()
    online_agents = await get_online_agents(db)
    online_ids = {a.id for a in online_agents}
    agent_ids = [a.id for a in all_agents]

    # Batch: open tickets per agent
    open_q = await db.execute(
        select(Ticket.assigned_to, func.count())
        .where(
            Ticket.assigned_to.in_(agent_ids),
            Ticket.status.notin_(["resolved", "closed", "archived", "merged"])
        )
        .group_by(Ticket.assigned_to)
    )
    open_map = dict(open_q.all())

    # Batch: resolved today per agent
    resolved_today_q = await db.execute(
        select(Ticket.assigned_to, func.count())
        .where(Ticket.assigned_to.in_(agent_ids), Ticket.resolved_at >= today_start)
        .group_by(Ticket.assigned_to)
    )
    resolved_today_map = dict(resolved_today_q.all())

    # Batch: resolved this week per agent
    resolved_week_q = await db.execute(
        select(Ticket.assigned_to, func.count())
        .where(Ticket.assigned_to.in_(agent_ids), Ticket.resolved_at >= week_start)
        .group_by(Ticket.assigned_to)
    )
    resolved_week_map = dict(resolved_week_q.all())

    # Batch: avg response time (last 7 days) per agent
    avg_resp_q = await db.execute(
        select(
            Ticket.assigned_to,
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
        )
        .where(
            Ticket.assigned_to.in_(agent_ids),
            Ticket.first_response_at.isnot(None),
            Ticket.created_at >= today_start - timedelta(days=7),
        )
        .group_by(Ticket.assigned_to)
    )
    avg_resp_map = {row[0]: round(row[1] or 0, 1) for row in avg_resp_q.all()}

    agent_stats = []
    for agent in all_agents:
        agent_stats.append({
            "id": agent.id, "name": agent.name, "role": agent.role,
            "specialty": agent.specialty,
            "is_online": agent.id in online_ids,
            "last_activity": agent.last_activity_at.isoformat() if agent.last_activity_at else None,
            "open_tickets": open_map.get(agent.id, 0),
            "resolved_today": resolved_today_map.get(agent.id, 0),
            "resolved_week": resolved_week_map.get(agent.id, 0),
            "avg_response_hours": avg_resp_map.get(agent.id, 0),
        })

    # Global: unassigned tickets
    unassigned_q = await db.execute(
        select(func.count()).select_from(Ticket).where(
            Ticket.assigned_to.is_(None),
            Ticket.status.notin_(["resolved", "closed", "archived", "merged"])
        )
    )
    unassigned = unassigned_q.scalar()

    # Alerts
    alerts = []
    if unassigned > 10:
        alerts.append({"type": "warning", "message": f"{unassigned} tickets sem agente"})
    if len(online_ids) < 2:
        alerts.append({"type": "critical", "message": f"Apenas {len(online_ids)} agente(s) online"})

    # AI auto-replies today
    ai_replied_q = await db.execute(
        select(func.count()).select_from(Ticket).where(
            Ticket.auto_replied == True, Ticket.auto_reply_at >= today_start,
        )
    )
    ai_replied_today = ai_replied_q.scalar()

    return {
        "agents": sorted(agent_stats, key=lambda x: x["resolved_today"], reverse=True),
        "online_count": len(online_ids),
        "total_agents": len(all_agents),
        "alerts": alerts,
        "ai_replies_today": ai_replied_today,
        "unassigned_count": unassigned,
    }
