"""Gamification & speed metrics endpoints."""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/leaderboard")
async def get_leaderboard(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Agent leaderboard — resolved tickets, avg response time, SLA compliance."""
    from app.services.cache import cache_get, cache_set
    cache_key = f"gamification:leaderboard:{days}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get all agents
    agents_result = await db.execute(select(User).where(User.is_active == True))
    agents = agents_result.scalars().all()
    agent_map = {a.id: a for a in agents}
    agent_ids = list(agent_map.keys())

    if not agent_ids:
        return []

    # Single aggregated query for resolved, total, sla_ok counts
    stats_query = (
        select(
            Ticket.assigned_to,
            func.count(case((and_(
                Ticket.status.in_(["resolved", "closed"]),
                Ticket.updated_at >= since,
            ), Ticket.id))).label("resolved"),
            func.count(case((
                Ticket.created_at >= since,
                Ticket.id,
            ))).label("total"),
            func.count(case((and_(
                Ticket.status.in_(["resolved", "closed"]),
                Ticket.updated_at >= since,
                Ticket.sla_breached == False,
            ), Ticket.id))).label("sla_ok"),
            func.count(case((
                Ticket.status.in_(["open", "in_progress", "waiting", "analyzing"]),
                Ticket.id,
            ))).label("pending"),
        )
        .where(Ticket.assigned_to.in_(agent_ids))
        .group_by(Ticket.assigned_to)
    )
    result = await db.execute(stats_query)
    stats_map = {}
    for row in result.all():
        stats_map[row[0]] = {
            "resolved": row[1] or 0,
            "total": row[2] or 0,
            "sla_ok": row[3] or 0,
            "pending": row[4] or 0,
        }

    leaderboard = []
    for aid, agent in agent_map.items():
        s = stats_map.get(aid, {"resolved": 0, "total": 0, "sla_ok": 0, "pending": 0})
        sla_rate = round((s["sla_ok"] / s["resolved"] * 100) if s["resolved"] > 0 else 100)
        score = s["resolved"] * 10 + (sla_rate // 10)

        leaderboard.append({
            "agent_id": aid,
            "agent_name": agent.name,
            "role": agent.role,
            "resolved": s["resolved"],
            "total": s["total"],
            "pending": s["pending"],
            "sla_rate": sla_rate,
            "score": score,
        })

    # Sort by score desc
    leaderboard.sort(key=lambda x: x["score"], reverse=True)

    # Add rank
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1

    await cache_set(cache_key, leaderboard, ttl_seconds=120)
    return leaderboard


@router.get("/my-stats")
async def my_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Current agent's personal stats and goals."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Today's resolved
    today_resolved = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assigned_to == user.id,
            Ticket.status.in_(["resolved", "closed"]),
            Ticket.updated_at >= today_start,
        )
    )
    today_count = today_resolved.scalar() or 0

    # Week's resolved
    week_resolved = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assigned_to == user.id,
            Ticket.status.in_(["resolved", "closed"]),
            Ticket.updated_at >= week_start,
        )
    )
    week_count = week_resolved.scalar() or 0

    # Pending right now
    pending = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assigned_to == user.id,
            Ticket.status.in_(["open", "in_progress", "waiting", "analyzing"]),
        )
    )
    pending_count = pending.scalar() or 0

    # SLA about to breach (< 1 hour remaining)
    sla_urgent = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assigned_to == user.id,
            Ticket.status.notin_(["resolved", "closed"]),
            Ticket.sla_deadline.isnot(None),
            Ticket.sla_deadline <= now + timedelta(hours=1),
            Ticket.sla_breached == False,
        )
    )
    sla_urgent_count = sla_urgent.scalar() or 0

    # Already breached
    breached = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assigned_to == user.id,
            Ticket.status.notin_(["resolved", "closed"]),
            Ticket.sla_breached == True,
        )
    )
    breached_count = breached.scalar() or 0

    # Goals
    daily_goal = 15
    weekly_goal = 60

    return {
        "today_resolved": today_count,
        "week_resolved": week_count,
        "pending": pending_count,
        "sla_urgent": sla_urgent_count,
        "sla_breached": breached_count,
        "daily_goal": daily_goal,
        "weekly_goal": weekly_goal,
        "daily_progress": round(today_count / daily_goal * 100) if daily_goal else 0,
        "weekly_progress": round(week_count / weekly_goal * 100) if weekly_goal else 0,
        "streak_message": _get_streak_message(today_count, pending_count, sla_urgent_count),
    }


async def _calc_agent_score(db: AsyncSession, agent_id: str, days: int = 30) -> int:
    """Calculate agent score for reward eligibility."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    resolved = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assigned_to == agent_id,
            Ticket.status.in_(["resolved", "closed"]),
            Ticket.updated_at >= since,
        )
    )
    resolved_count = resolved.scalar() or 0
    sla_ok = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assigned_to == agent_id,
            Ticket.sla_breached == False,
            Ticket.updated_at >= since,
            Ticket.status.in_(["resolved", "closed"]),
        )
    )
    sla_ok_count = sla_ok.scalar() or 0
    sla_rate = round((sla_ok_count / resolved_count * 100) if resolved_count > 0 else 100)
    return resolved_count * 10 + (sla_rate // 10)


def _get_streak_message(resolved_today: int, pending: int, sla_urgent: int) -> str:
    """Generate motivational streak message."""
    if sla_urgent > 0:
        return f"🔥 {sla_urgent} ticket(s) quase estourando SLA! Priorize agora!"
    if pending == 0:
        return "🎉 Fila zerada! Excelente trabalho!"
    if resolved_today >= 15:
        return f"🏆 {resolved_today} resolvidos hoje! Você está on fire!"
    if resolved_today >= 10:
        return f"💪 {resolved_today} resolvidos! Faltam {15 - resolved_today} pra meta!"
    if resolved_today >= 5:
        return f"👍 Bom ritmo! {resolved_today}/15 na meta diária"
    if pending <= 3:
        return f"✨ Quase lá! Só {pending} na fila!"
    return f"📋 {pending} tickets na fila. Bora resolver!"
