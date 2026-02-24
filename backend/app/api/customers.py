"""Customer management endpoints."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.customer import Customer
from app.models.ticket import Ticket, STATUS_LABELS
from app.models.message import Message
from app.models.user import User
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])


# ── Schemas ──

class CustomerMergeRequest(BaseModel):
    source_customer_id: str
    target_customer_id: str


# ── Search ──

@router.get("/search")
async def search_customers(
    q: str = Query(..., min_length=1, description="Busca por nome, email, CPF ou telefone"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Search customers by name, email, CPF, or phone (case-insensitive, max 20)."""
    search_term = f"%{q.strip()}%"
    result = await db.execute(
        select(Customer)
        .where(
            Customer.merged_into_id.is_(None),  # Exclude merged customers
            or_(
                func.lower(Customer.name).like(func.lower(search_term)),
                func.lower(Customer.email).like(func.lower(search_term)),
                Customer.cpf.like(search_term),
                Customer.phone.like(search_term),
            ),
        )
        .order_by(Customer.name.asc())
        .limit(20)
    )
    customers = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "cpf": c.cpf,
            "phone": c.phone,
            "total_tickets": c.total_tickets,
            "is_blacklisted": c.is_blacklisted,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in customers
    ]


# ── Detail ──

@router.get("/{customer_id}")
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get customer details with their ticket history."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Fetch tickets for this customer
    tickets_result = await db.execute(
        select(Ticket)
        .where(Ticket.customer_id == customer_id)
        .order_by(Ticket.created_at.desc())
        .limit(50)
    )
    tickets = tickets_result.scalars().all()

    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "cpf": customer.cpf,
        "phone": customer.phone,
        "total_tickets": customer.total_tickets,
        "is_repeat": customer.is_repeat,
        "risk_score": customer.risk_score,
        "is_blacklisted": customer.is_blacklisted,
        "blacklist_reason": customer.blacklist_reason,
        "blacklisted_at": customer.blacklisted_at.isoformat() if customer.blacklisted_at else None,
        "chargeback_count": customer.chargeback_count,
        "resend_count": customer.resend_count,
        "abuse_flags": customer.abuse_flags,
        "notes": customer.notes,
        "tags": customer.tags,
        "merged_into_id": customer.merged_into_id,
        "alternate_emails": customer.alternate_emails,
        "meta_user_id": customer.meta_user_id,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "tickets": [
            {
                "id": t.id,
                "number": t.number,
                "subject": t.subject,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tickets
        ],
    }


# ── Full History ──

@router.get("/{customer_id}/history")
async def get_customer_full_history(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get ALL messages from ALL tickets of a customer, ordered chronologically.
    Returns messages grouped with ticket metadata for timeline view."""
    # Verify customer exists
    cust_result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Get all tickets for this customer
    tickets_result = await db.execute(
        select(Ticket)
        .where(Ticket.customer_id == customer_id)
        .order_by(Ticket.created_at.asc())
    )
    tickets = tickets_result.scalars().all()
    ticket_map = {t.id: t for t in tickets}

    if not tickets:
        return {"customer_name": customer.name, "tickets": [], "messages": []}

    # Get ALL messages from all tickets, ordered by created_at
    ticket_ids = [t.id for t in tickets]
    msgs_result = await db.execute(
        select(Message)
        .where(Message.ticket_id.in_(ticket_ids))
        .order_by(Message.created_at.asc())
    )
    messages = msgs_result.scalars().all()

    return {
        "customer_name": customer.name,
        "tickets": [
            {
                "id": t.id,
                "number": t.number,
                "subject": t.subject,
                "status": t.status,
                "status_label": STATUS_LABELS.get(t.status, t.status),
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tickets
        ],
        "messages": [
            {
                "id": m.id,
                "ticket_id": m.ticket_id,
                "ticket_number": ticket_map[m.ticket_id].number if m.ticket_id in ticket_map else None,
                "ticket_subject": ticket_map[m.ticket_id].subject if m.ticket_id in ticket_map else None,
                "type": m.type,
                "sender_name": m.sender_name,
                "sender_email": m.sender_email,
                "body_text": m.body_text,
                "body_html": m.body_html,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


# ── Merge ──

@router.post("/merge")
async def merge_customers(
    body: CustomerMergeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Merge two customers: transfers tickets, merges data, marks source as merged.
    Requires admin, supervisor, or super_admin role."""
    if user.role not in ("admin", "supervisor", "super_admin"):
        raise HTTPException(status_code=403, detail="Apenas admins/supervisores podem mesclar clientes")

    if body.source_customer_id == body.target_customer_id:
        raise HTTPException(status_code=400, detail="Não é possível mesclar um cliente com ele mesmo")

    # Fetch both customers
    source_result = await db.execute(select(Customer).where(Customer.id == body.source_customer_id))
    source = source_result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Cliente de origem não encontrado")

    target_result = await db.execute(select(Customer).where(Customer.id == body.target_customer_id))
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Cliente de destino não encontrado")

    # Prevent merging already-merged customers
    if source.merged_into_id:
        raise HTTPException(status_code=400, detail="Cliente de origem já foi mesclado anteriormente")
    if target.merged_into_id:
        raise HTTPException(status_code=400, detail="Cliente de destino já foi mesclado anteriormente")

    # 1. Transfer all tickets from source to target
    tickets_result = await db.execute(
        select(Ticket).where(Ticket.customer_id == source.id)
    )
    source_tickets = tickets_result.scalars().all()
    transferred_count = 0
    for ticket in source_tickets:
        ticket.customer_id = target.id
        ticket.updated_at = datetime.now(timezone.utc)
        transferred_count += 1

    # 2. Merge data: fill empty fields on target from source
    if not target.cpf and source.cpf:
        target.cpf = source.cpf
    if not target.phone and source.phone:
        target.phone = source.phone
    if not target.notes and source.notes:
        target.notes = source.notes
    if not target.meta_user_id and source.meta_user_id:
        target.meta_user_id = source.meta_user_id

    # Merge tags
    if source.tags:
        existing_tags = target.tags or []
        merged_tags = list(set(existing_tags + source.tags))
        target.tags = merged_tags

    # Merge abuse flags
    if source.abuse_flags:
        existing_flags = target.abuse_flags or []
        merged_flags = list(set(existing_flags + source.abuse_flags))
        target.abuse_flags = merged_flags

    # Accumulate counts
    target.total_tickets += source.total_tickets
    target.chargeback_count += source.chargeback_count
    target.resend_count += source.resend_count
    if source.risk_score > target.risk_score:
        target.risk_score = source.risk_score
    if source.is_blacklisted and not target.is_blacklisted:
        target.is_blacklisted = True
        target.blacklist_reason = source.blacklist_reason
        target.blacklisted_at = source.blacklisted_at
    if source.is_repeat:
        target.is_repeat = True

    # 3. Handle alternate emails
    alternate = target.alternate_emails or []
    if source.email and source.email != target.email and source.email not in alternate:
        alternate.append(source.email)
    # Also bring over source's alternate emails
    if source.alternate_emails:
        for alt_email in source.alternate_emails:
            if alt_email != target.email and alt_email not in alternate:
                alternate.append(alt_email)
    target.alternate_emails = alternate if alternate else None

    # 4. Mark source as merged
    source.merged_into_id = target.id

    # 5. Audit log
    db.add(AuditLog(
        user_id=user.id,
        action="customer_merge",
        details={
            "source_customer_id": source.id,
            "source_name": source.name,
            "source_email": source.email,
            "target_customer_id": target.id,
            "target_name": target.name,
            "target_email": target.email,
            "tickets_transferred": transferred_count,
        },
    ))

    await db.commit()

    logger.info(
        f"Customer merge: {source.email} -> {target.email} "
        f"({transferred_count} tickets transferred) by {user.name}"
    )

    return {
        "ok": True,
        "message": f"Cliente {source.name} mesclado com {target.name}",
        "tickets_transferred": transferred_count,
        "target_customer_id": target.id,
    }
