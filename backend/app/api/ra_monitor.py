"""Reclame Aqui monitoring endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ra-monitor", tags=["reclame-aqui"])


@router.get("/complaints")
async def get_ra_complaints(limit: int = 10, user: User = Depends(get_current_user)):
    """Fetch latest RA complaints from Gmail notifications."""
    from app.services.ra_monitor import fetch_ra_complaints
    complaints = await fetch_ra_complaints(limit=limit)
    return {"complaints": complaints, "total": len(complaints)}


@router.get("/reputation")
async def get_ra_reputation(user: User = Depends(get_current_user)):
    """Fetch RA company reputation."""
    from app.services.ra_monitor import fetch_ra_reputation
    reputation = await fetch_ra_reputation()
    return {"reputation": reputation}


@router.get("/tickets")
async def get_ra_tickets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 20,
):
    """List tickets created from Reclame Aqui complaints."""
    from sqlalchemy import text as sa_text
    result = await db.execute(
        select(Ticket).where(
            sa_text("tags @> ARRAY['reclame_aqui']::varchar[]")
        ).order_by(Ticket.created_at.desc()).limit(limit)
    )
    tickets = result.scalars().all()
    return {
        "tickets": [
            {
                "id": t.id,
                "number": t.number,
                "subject": t.subject,
                "status": t.status,
                "priority": t.priority,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "tags": t.tags or [],
            }
            for t in tickets
        ],
        "total": len(tickets),
    }


@router.post("/sync")
async def sync_ra_complaints(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually sync RA complaints from Gmail and create urgent tickets."""
    if user.role not in ("admin", "super_admin", "supervisor"):
        raise HTTPException(403, "Apenas admin/supervisor pode sincronizar")

    from app.services.ra_monitor import check_new_complaints, create_ra_ticket

    new = await check_new_complaints(db)
    created = []
    errors = []

    for complaint in new:
        try:
            result = await create_ra_ticket(complaint, db)
            created.append(result)
        except Exception as e:
            logger.error(f"Failed to create RA ticket: {e}")
            errors.append({"ra_id": complaint.get("id"), "error": str(e)})

    if created:
        await db.commit()

    return {
        "new_complaints": len(new),
        "tickets_created": len(created),
        "details": created,
        "errors": errors,
    }
