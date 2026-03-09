"""Reclame Aqui monitoring endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ra-monitor", tags=["reclame-aqui"])


@router.get("/complaints")
async def get_ra_complaints(limit: int = 10, user: User = Depends(get_current_user)):
    """Fetch latest RA complaints via Google Search."""
    from app.services.ra_monitor import fetch_ra_complaints
    complaints = await fetch_ra_complaints(limit=limit)
    return {"complaints": complaints, "total": len(complaints)}


@router.get("/reputation")
async def get_ra_reputation(user: User = Depends(get_current_user)):
    """Fetch RA company reputation."""
    from app.services.ra_monitor import fetch_ra_reputation
    reputation = await fetch_ra_reputation()
    return {"reputation": reputation}


@router.post("/sync")
async def sync_ra_complaints(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check for new RA complaints and create urgent tickets."""
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
