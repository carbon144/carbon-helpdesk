"""Triage engine: applies Victor's rules + fallback round-robin."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.triage_rule import TriageRule
from app.models.ticket import Ticket
from app.models.user import User

logger = logging.getLogger(__name__)

ONLINE_THRESHOLD_MINUTES = 15


async def get_online_agents(db: AsyncSession) -> list[User]:
    """Return agents who are online (activity < 15min)."""
    threshold = datetime.now(timezone.utc) - timedelta(minutes=ONLINE_THRESHOLD_MINUTES)
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.role.in_(["agent", "supervisor", "admin"]),
            User.last_activity_at >= threshold,
        )
    )
    return list(result.scalars().all())


async def apply_triage_rules(ticket: Ticket, db: AsyncSession) -> dict:
    """Apply triage rules to a ticket. Returns action taken."""
    rules = await db.execute(
        select(TriageRule)
        .where(TriageRule.is_active == True)
        .order_by(TriageRule.priority.desc())
    )
    rules = list(rules.scalars().all())

    for rule in rules:
        if _rule_matches(rule, ticket):
            return await _apply_rule(rule, ticket, db)

    # Fallback: round-robin among online agents
    return await _fallback_round_robin(ticket, db)


def _rule_matches(rule: TriageRule, ticket: Ticket) -> bool:
    """Check if category condition matches."""
    if rule.category and ticket.category != rule.category:
        return False
    return True


async def _apply_rule(rule: TriageRule, ticket: Ticket, db: AsyncSession) -> dict:
    """Apply a matched rule's actions."""
    result = {"rule_id": rule.id, "rule_name": rule.name, "actions": []}

    if rule.set_priority:
        ticket.priority = rule.set_priority
        result["actions"].append(f"priority={rule.set_priority}")

    if rule.assign_to:
        ticket.assigned_to = rule.assign_to
        result["actions"].append(f"assigned_to={rule.assign_to}")

    result["auto_reply"] = rule.auto_reply
    return result


async def _fallback_round_robin(ticket: Ticket, db: AsyncSession) -> dict:
    """Fallback: assign to online agent with least tickets."""
    agent = await _pick_online_agent(db)
    if agent:
        ticket.assigned_to = agent.id
        return {"rule_id": None, "rule_name": "round-robin", "actions": [f"assigned_to={agent.name}"], "auto_reply": False}
    # Nobody online
    return {"rule_id": None, "rule_name": "no-agents-online", "actions": ["queued"], "auto_reply": True}


async def _pick_online_agent(db: AsyncSession) -> User | None:
    """Pick online agent with fewest open tickets."""
    online = await get_online_agents(db)
    if not online:
        return None

    agent_loads = {}
    for agent in online:
        count_result = await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.assigned_to == agent.id,
                Ticket.status.in_(["open", "in_progress", "waiting", "analyzing", "waiting_supplier", "waiting_resend"])
            )
        )
        load = count_result.scalar()
        if load < agent.max_tickets:
            agent_loads[agent.id] = (load, agent)

    if not agent_loads:
        return None

    _, chosen = min(agent_loads.values(), key=lambda x: x[0])
    return chosen
