"""Endpoint único de métricas simplificadas."""
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


@router.get("/metricas")
async def get_metricas(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    period_start = today_start - timedelta(days=days)

    # --- Cards ---
    cards_q = await db.execute(
        select(
            # Tickets criados hoje
            func.count(case((Ticket.created_at >= today_start, 1))).label("tickets_hoje"),
            # Resolvidos hoje
            func.count(case((Ticket.resolved_at >= today_start, 1))).label("resolvidos_hoje"),
            # Sem resposta (abertos sem first_response)
            func.count(case((
                and_(
                    Ticket.first_response_at.is_(None),
                    Ticket.status.notin_(["resolved", "closed", "archived", "merged"]),
                ), 1
            ))).label("sem_resposta"),
            # Auto-replies hoje
            func.count(case((
                and_(Ticket.auto_replied == True, Ticket.auto_reply_at >= today_start), 1
            ))).label("auto_replies_hoje"),
            # Tempo médio de primeira resposta (últimos 7 dias, em horas)
            func.avg(
                func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600
            ).filter(
                Ticket.first_response_at.isnot(None),
                Ticket.created_at >= today_start - timedelta(days=7),
            ).label("tempo_medio_h"),
        ).select_from(Ticket)
    )
    c = cards_q.one()

    # --- Agentes ---
    agents_q = await db.execute(
        select(User).where(User.is_active == True, User.role.in_(["agent", "admin", "supervisor"]))
    )
    agents = agents_q.scalars().all()
    agent_ids = [a.id for a in agents]

    # Abertos por agente
    open_q = await db.execute(
        select(Ticket.assigned_to, func.count())
        .where(Ticket.assigned_to.in_(agent_ids), Ticket.status.notin_(["resolved", "closed", "archived", "merged"]))
        .group_by(Ticket.assigned_to)
    )
    open_map = dict(open_q.all())

    # Resolvidos hoje por agente
    res_today_q = await db.execute(
        select(Ticket.assigned_to, func.count())
        .where(Ticket.assigned_to.in_(agent_ids), Ticket.resolved_at >= today_start)
        .group_by(Ticket.assigned_to)
    )
    res_today_map = dict(res_today_q.all())

    # Resolvidos semana por agente
    res_week_q = await db.execute(
        select(Ticket.assigned_to, func.count())
        .where(Ticket.assigned_to.in_(agent_ids), Ticket.resolved_at >= week_start)
        .group_by(Ticket.assigned_to)
    )
    res_week_map = dict(res_week_q.all())

    # Tempo médio resposta por agente (período selecionado)
    avg_resp_q = await db.execute(
        select(
            Ticket.assigned_to,
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600),
        )
        .where(
            Ticket.assigned_to.in_(agent_ids),
            Ticket.first_response_at.isnot(None),
            Ticket.created_at >= period_start,
        )
        .group_by(Ticket.assigned_to)
    )
    avg_resp_map = {r[0]: round(r[1] or 0, 1) for r in avg_resp_q.all()}

    agentes = []
    for agent in agents:
        agentes.append({
            "nome": agent.name,
            "abertos": open_map.get(agent.id, 0),
            "resolvidos_hoje": res_today_map.get(agent.id, 0),
            "resolvidos_semana": res_week_map.get(agent.id, 0),
            "tempo_medio_h": avg_resp_map.get(agent.id, 0),
        })
    agentes.sort(key=lambda x: x["resolvidos_hoje"], reverse=True)

    # --- Volume diário (30 dias) ---
    daily_q = await db.execute(
        select(
            func.date(Ticket.created_at).label("dia"),
            func.count().label("criados"),
            func.count(case((Ticket.status.in_(["resolved", "closed"]), 1))).label("resolvidos"),
        )
        .where(Ticket.created_at >= period_start)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
    )
    volume_diario = [
        {"data": str(r[0]), "criados": r[1], "resolvidos": r[2]}
        for r in daily_q.all()
    ]

    return {
        "cards": {
            "tickets_hoje": c.tickets_hoje,
            "resolvidos_hoje": c.resolvidos_hoje,
            "sem_resposta": c.sem_resposta,
            "tempo_medio_resposta_h": round(c.tempo_medio_h or 0, 1),
            "auto_replies_hoje": c.auto_replies_hoje,
        },
        "agentes": agentes,
        "volume_diario": volume_diario,
    }
