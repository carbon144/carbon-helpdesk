from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.inbox import Inbox
from app.models.ticket import Ticket
from app.schemas.inbox import InboxCreate, InboxUpdate, InboxResponse

router = APIRouter(prefix="/inboxes", tags=["inboxes"])


@router.get("", response_model=list[InboxResponse])
async def list_inboxes(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Inbox).where(Inbox.is_active == True).order_by(Inbox.sort_order))
    inboxes = result.scalars().all()

    response = []
    for inbox in inboxes:
        # Count tickets in this inbox
        count_result = await db.execute(
            select(func.count()).select_from(Ticket).where(Ticket.inbox_id == inbox.id)
        )
        count = count_result.scalar()

        r = InboxResponse.model_validate(inbox)
        r.ticket_count = count
        response.append(r)

    return response


@router.post("", response_model=InboxResponse, status_code=201)
async def create_inbox(body: InboxCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem criar inboxes")

    max_order = await db.execute(select(func.max(Inbox.sort_order)))
    next_order = (max_order.scalar() or 0) + 1

    inbox = Inbox(
        name=body.name,
        type=body.type,
        icon=body.icon,
        color=body.color,
        filter_tags=body.filter_tags,
        filter_rules=body.filter_rules,
        sort_order=next_order,
    )
    db.add(inbox)
    await db.commit()
    await db.refresh(inbox)

    r = InboxResponse.model_validate(inbox)
    r.ticket_count = 0
    return r


@router.patch("/{inbox_id}", response_model=InboxResponse)
async def update_inbox(inbox_id: str, body: InboxUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Inbox).where(Inbox.id == inbox_id))
    inbox = result.scalar_one_or_none()
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox não encontrada")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(inbox, field, value)

    await db.commit()
    await db.refresh(inbox)
    r = InboxResponse.model_validate(inbox)
    return r
