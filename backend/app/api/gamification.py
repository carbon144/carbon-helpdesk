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
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get all agents
    agents_result = await db.execute(select(User).where(User.is_active == True))
    agents = agents_result.scalars().all()

    leaderboard = []
    for agent in agents:
        # Count resolved tickets
        resolved = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assigned_to == agent.id,
                Ticket.status.in_(["resolved", "closed"]),
                Ticket.updated_at >= since,
            )
        )
        resolved_count = resolved.scalar() or 0

        # Count total assigned
        total = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assigned_to == agent.id,
                Ticket.created_at >= since,
            )
        )
        total_count = total.scalar() or 0

        # SLA compliance (not breached)
        sla_ok = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assigned_to == agent.id,
                Ticket.sla_breached == False,
                Ticket.updated_at >= since,
                Ticket.status.in_(["resolved", "closed"]),
            )
        )
        sla_ok_count = sla_ok.scalar() or 0
        sla_rate = round((sla_ok_count / resolved_count * 100) if resolved_count > 0 else 100)

        # Pending (open) tickets
        pending = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assigned_to == agent.id,
                Ticket.status.in_(["open", "in_progress", "waiting", "analyzing"]),
            )
        )
        pending_count = pending.scalar() or 0

        # Score = resolved * 10 + sla_rate bonus
        score = resolved_count * 10 + (sla_rate // 10)

        leaderboard.append({
            "agent_id": agent.id,
            "agent_name": agent.name,
            "role": agent.role,
            "resolved": resolved_count,
            "total": total_count,
            "pending": pending_count,
            "sla_rate": sla_rate,
            "score": score,
        })

    # Sort by score desc
    leaderboard.sort(key=lambda x: x["score"], reverse=True)

    # Add rank
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1

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
            Ticket.sla_deadline != None,
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
