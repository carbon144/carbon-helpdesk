"""Auto-close stale tickets where agent replied and customer didn't respond."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.models.message import Message

logger = logging.getLogger(__name__)

STALE_DAYS = 5


async def auto_close_stale_tickets(db: AsyncSession) -> dict:
    """Close tickets where last message is outbound and older than STALE_DAYS."""
    threshold = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)

    subq = (
        select(
            Message.ticket_id,
            func.max(Message.created_at).label("last_msg_at"),
            func.max(case((Message.type == "outbound", Message.created_at))).label("last_outbound"),
        )
        .group_by(Message.ticket_id)
        .subquery()
    )

    stale_q = await db.execute(
        select(Ticket).join(subq, Ticket.id == subq.c.ticket_id).where(
            Ticket.status.in_(["waiting", "open", "in_progress"]),
            subq.c.last_outbound.isnot(None),
            subq.c.last_msg_at == subq.c.last_outbound,
            subq.c.last_outbound < threshold,
        )
    )
    stale_tickets = stale_q.scalars().all()

    closed = 0
    for ticket in stale_tickets:
        ticket.status = "resolved"
        ticket.resolved_at = datetime.now(timezone.utc)
        ticket.tags = list(set((ticket.tags or []) + ["auto_closed"]))
        closed += 1

    if closed:
        await db.commit()
        logger.info(f"Auto-closed {closed} stale tickets (>{STALE_DAYS} days no customer reply)")

    return {"checked": len(stale_tickets), "auto_closed": closed}
