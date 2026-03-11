"""RF-014: Auto-escalation service for tickets without agent response."""
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.ticket import Ticket
from app.models.audit_log import AuditLog
from app.core.sla_config import ESCALATION_RULES

logger = logging.getLogger(__name__)


async def check_and_escalate(db: AsyncSession) -> dict:
    """Check all active tickets and escalate those without response beyond threshold."""
    now = datetime.now(timezone.utc)
    escalated = 0
    warned = 0

    # Get active tickets with an agent assigned but no response
    # Skip tickets that already have auto_replied (IA already responded)
    result = await db.execute(
        select(Ticket).where(
            Ticket.status.in_(["open", "in_progress"]),
            Ticket.assigned_to.isnot(None),
            Ticket.first_response_at.is_(None),
            Ticket.auto_replied == False,
        )
    )
    tickets = result.scalars().all()

    for ticket in tickets:
        rules = ESCALATION_RULES.get(ticket.priority, ESCALATION_RULES["medium"])
        time_since_created = (now - ticket.created_at).total_seconds() / 3600

        already_escalated = "AUTO_ESCALADO" in (ticket.tags or [])
        if time_since_created >= rules["escalate_hours"] and ticket.status != "escalated" and not already_escalated:
            ticket.status = "escalated"
            ticket.escalated_at = now
            ticket.escalation_reason = f"Sem resposta há {time_since_created:.0f}h (limite: {rules['escalate_hours']}h)"
            ticket.tags = list(set((ticket.tags or []) + ["AUTO_ESCALADO"]))
            db.add(AuditLog(
                ticket_id=ticket.id,
                action="auto_escalated",
                details={"hours_without_response": round(time_since_created, 1)},
            ))
            escalated += 1
            logger.info(f"Ticket #{ticket.number} auto-escalated ({time_since_created:.1f}h without response)")

        elif time_since_created >= rules["warn_hours"] and "SLA_ALERTA" not in (ticket.tags or []):
            ticket.tags = list(set((ticket.tags or []) + ["SLA_ALERTA"]))
            warned += 1

    # Also check tickets approaching SLA deadline
    result2 = await db.execute(
        select(Ticket).where(
            Ticket.status.notin_(["resolved", "closed", "escalated"]),
            Ticket.sla_deadline.isnot(None),
            Ticket.sla_deadline <= now,
            Ticket.sla_breached == False,
        )
    )
    sla_tickets = result2.scalars().all()
    sla_breached = 0
    for ticket in sla_tickets:
        ticket.sla_breached = True
        ticket.tags = list(set((ticket.tags or []) + ["SLA_ESTOURADO"]))
        db.add(AuditLog(
            ticket_id=ticket.id,
            action="sla_breached",
            details={"sla_deadline": ticket.sla_deadline.isoformat()},
        ))
        sla_breached += 1

    await db.commit()
    return {"escalated": escalated, "warned": warned, "sla_breached": sla_breached}
