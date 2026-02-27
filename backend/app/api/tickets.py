from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File

logger = logging.getLogger(__name__)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, case
from sqlalchemy.orm import selectinload, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.sla_config import get_sla_for_ticket, BLACKLIST_RULES, CATEGORY_ROUTING
from app.models.user import User
from app.models.ticket import Ticket, VALID_STATUSES, VALID_PRIORITIES, STATUS_LABELS
from app.models.message import Message
from app.models.customer import Customer
from app.models.audit_log import AuditLog
from app.models.ticket_view import TicketView
from app.schemas.ticket import (
    TicketCreate, TicketUpdate, TicketBulkAssign, TicketBulkUpdate,
    TicketResponse, TicketListResponse, MessageCreate, MessageResponse,
)
from app.api.ws import notify_new_ticket, notify_ticket_update, notify_assignment

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _calc_sla(category: str | None, priority: str, from_time: datetime | None = None) -> dict:
    """Calculate SLA deadlines based on category and priority.
    SLA starts from from_time (received_at) or now if not provided."""
    sla = get_sla_for_ticket(category, priority)
    start = from_time or datetime.now(timezone.utc)
    return {
        "sla_deadline": start + timedelta(hours=sla["resolution_hours"]),
        "sla_response_deadline": start + timedelta(hours=sla["response_hours"]),
        "priority": sla.get("priority", priority),
    }


def _ticket_to_response(ticket: Ticket, include_messages: bool = False, is_unread: bool = False) -> TicketResponse:
    messages = None
    if include_messages:
        try:
            messages = [MessageResponse.model_validate(m) for m in ticket.messages] if ticket.messages else None
        except Exception:
            messages = None
    return TicketResponse(
        id=ticket.id,
        number=ticket.number,
        subject=ticket.subject,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        customer=ticket.customer if ticket.customer else None,
        assigned_to=ticket.assigned_to,
        agent_name=ticket.agent.name if ticket.agent else None,
        inbox_id=ticket.inbox_id,
        sla_deadline=ticket.sla_deadline,
        sla_response_deadline=getattr(ticket, 'sla_response_deadline', None),
        sla_breached=ticket.sla_breached,
        sentiment=ticket.sentiment,
        ai_category=ticket.ai_category,
        ai_confidence=ticket.ai_confidence,
        ai_summary=getattr(ticket, 'ai_summary', None),
        legal_risk=ticket.legal_risk,
        is_locked=ticket.is_locked,
        tags=ticket.tags,
        source=ticket.source,
        slack_channel_id=ticket.slack_channel_id,
        slack_thread_ts=ticket.slack_thread_ts,
        protocol=getattr(ticket, 'protocol', None),
        protocol_sent=getattr(ticket, 'protocol_sent', False),
        internal_notes=getattr(ticket, 'internal_notes', None),
        supplier_notes=getattr(ticket, 'supplier_notes', None),
        tracking_code=getattr(ticket, 'tracking_code', None),
        tracking_status=getattr(ticket, 'tracking_status', None),
        escalated_at=getattr(ticket, 'escalated_at', None),
        escalation_reason=getattr(ticket, 'escalation_reason', None),
        received_at=getattr(ticket, 'received_at', None),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        first_response_at=ticket.first_response_at,
        last_agent_response_at=getattr(ticket, 'last_agent_response_at', None),
        customer_name=ticket.customer.name if ticket.customer else None,
        messages=messages,
        is_unread=is_unread,
    )


@router.post("/{ticket_id}/view")
async def mark_ticket_viewed(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upsert ticket_views: mark ticket as viewed by current user."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(TicketView).values(
        id=str(__import__("uuid").uuid4()),
        user_id=user.id,
        ticket_id=ticket_id,
        viewed_at=datetime.now(timezone.utc),
    ).on_conflict_do_update(
        constraint="uq_ticket_views_user_ticket",
        set_={"viewed_at": datetime.now(timezone.utc)},
    )
    await db.execute(stmt)
    await db.commit()
    return {"ok": True}


@router.get("/counts")
async def get_ticket_counts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get ticket counts for dashboard cards — single query with CASE WHEN."""
    from sqlalchemy import case, literal_column

    excluded = ["resolved", "closed", "archived"]
    waiting_statuses = ["waiting", "waiting_supplier", "waiting_resend"]
    meta_sources = ["whatsapp", "instagram", "facebook"]

    is_open = Ticket.status.notin_(excluded)
    is_active = Ticket.status.notin_(excluded + waiting_statuses)
    is_waiting = Ticket.status.in_(waiting_statuses)

    result = await db.execute(
        select(
            func.count().filter(is_open).label("total_open"),
            func.count().filter(is_active & (Ticket.assigned_to == user.id)).label("mine"),
            func.count().filter(is_active & Ticket.assigned_to.is_(None)).label("unassigned"),
            func.count().filter(Ticket.status == "escalated").label("escalated"),
            func.count().filter(is_active & Ticket.assigned_to.isnot(None)).label("team"),
            func.count().filter(is_waiting).label("waiting"),
            func.count().filter(Ticket.status == "archived").label("archived"),
            func.count().filter(is_open & Ticket.source.in_(meta_sources)).label("meta_channels"),
        ).select_from(Ticket)
    )
    row = result.one()

    # Unread count: tickets updated since user last viewed them (or never viewed)
    unread_sub = (
        select(func.count())
        .select_from(Ticket)
        .outerjoin(TicketView, (TicketView.ticket_id == Ticket.id) & (TicketView.user_id == user.id))
        .where(
            is_open,
            or_(
                TicketView.viewed_at.is_(None),
                Ticket.updated_at > TicketView.viewed_at,
            ),
        )
    )
    unread_result = await db.execute(unread_sub)
    unread = unread_result.scalar() or 0

    return {
        "total_open": row.total_open or 0,
        "mine": row.mine or 0,
        "team": row.team or 0,
        "unassigned": row.unassigned or 0,
        "escalated": row.escalated or 0,
        "waiting": row.waiting or 0,
        "archived": row.archived or 0,
        "meta_channels": row.meta_channels or 0,
        "unread": unread,
    }


@router.get("/sent-messages")
async def get_sent_messages(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return outbound email messages (not Meta) with ticket info."""
    base_query = (
        select(Message, Ticket)
        .join(Ticket, Message.ticket_id == Ticket.id)
        .where(
            Message.type == "outbound",
            Message.meta_message_id.is_(None),
        )
    )

    if search:
        term = f"%{search}%"
        base_query = base_query.outerjoin(Customer, Ticket.customer_id == Customer.id).where(
            or_(
                Ticket.subject.ilike(term),
                Customer.name.ilike(term),
                Customer.email.ilike(term),
                Message.body_text.ilike(term),
            )
        )

    count_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar()

    results = await db.execute(
        base_query
        .options(joinedload(Ticket.customer))
        .order_by(Message.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = results.unique().all()

    items = []
    for msg, ticket in rows:
        items.append({
            "message_id": msg.id,
            "ticket_id": ticket.id,
            "ticket_number": ticket.number,
            "ticket_subject": ticket.subject,
            "sender_name": msg.sender_name,
            "sender_email": msg.sender_email,
            "body_text": (msg.body_text or "")[:200],
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "customer_name": ticket.customer.name if ticket.customer else None,
            "customer_email": ticket.customer.email if ticket.customer else None,
        })

    return {"items": items, "total": total or 0, "page": page, "per_page": per_page}


@router.get("/statuses")
async def get_statuses():
    """Return all valid statuses with labels."""
    return [{"id": s, "label": STATUS_LABELS.get(s, s)} for s in VALID_STATUSES]


@router.post("/backfill-protocols")
async def backfill_protocols(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Generate protocol numbers for all tickets that don't have one."""
    from app.services.protocol_service import assign_protocol
    result = await db.execute(
        select(Ticket).where(Ticket.protocol.is_(None)).order_by(Ticket.created_at.asc())
    )
    tickets = result.scalars().all()
    count = 0
    for t in tickets:
        try:
            await assign_protocol(t, db)
            count += 1
        except Exception as e:
            logger.warning(f"Backfill protocol failed for ticket #{t.number}: {e}")
    await db.commit()
    return {"ok": True, "updated": count, "total_without_protocol": len(tickets)}


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    status: str | None = None,
    exclude_status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    assigned: str | None = None,
    inbox_id: str | None = None,
    search: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    sort: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    customer_name: str | None = None,
    source: str | None = None,
    exclude_sources: str | None = None,
    sla_breached: bool | None = None,
    legal_risk: bool | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Ticket)

    if status:
        if "," in status:
            query = query.where(Ticket.status.in_(status.split(",")))
        else:
            query = query.where(Ticket.status == status)
    if exclude_status:
        if "," in exclude_status:
            for es in exclude_status.split(","):
                query = query.where(Ticket.status != es.strip())
        else:
            query = query.where(Ticket.status != exclude_status)
    if priority:
        query = query.where(Ticket.priority == priority)
    if assigned:
        if assigned == "any":
            query = query.where(Ticket.assigned_to.isnot(None))
        elif assigned == "none":
            query = query.where(Ticket.assigned_to.is_(None))
    if assigned_to:
        if assigned_to == "me":
            query = query.where(Ticket.assigned_to == user.id)
        else:
            query = query.where(Ticket.assigned_to == assigned_to)
    if inbox_id:
        query = query.where(Ticket.inbox_id == inbox_id)
    if category:
        query = query.where(Ticket.category == category)
    if tag:
        query = query.where(Ticket.tags.any(tag))
    if source:
        if "," in source:
            query = query.where(Ticket.source.in_(source.split(",")))
        else:
            query = query.where(Ticket.source == source)
    if exclude_sources:
        query = query.where(Ticket.source.notin_(exclude_sources.split(",")))
    if sla_breached is not None:
        query = query.where(Ticket.sla_breached == sla_breached)
    if legal_risk is not None:
        query = query.where(Ticket.legal_risk == legal_risk)
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            query = query.where(Ticket.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(Ticket.created_at <= dt)
        except ValueError:
            pass
    if customer_name:
        query = query.join(Customer).where(Customer.name.ilike(f"%{customer_name}%"))
    if search:
        # Busca ampla: assunto, número, nome do cliente, email, tracking, texto das mensagens
        search_filters = [
            Ticket.subject.ilike(f"%{search}%"),
            Ticket.tracking_code.ilike(f"%{search}%"),
        ]
        if search.isdigit():
            search_filters.append(Ticket.number == int(search))
        # Busca no nome/email do cliente
        search_filters.append(
            Ticket.customer_id.in_(
                select(Customer.id).where(
                    or_(
                        Customer.name.ilike(f"%{search}%"),
                        Customer.email.ilike(f"%{search}%"),
                    )
                )
            )
        )
        # Busca no conteúdo das mensagens (pedido, textos gerais)
        search_filters.append(
            Ticket.id.in_(
                select(Message.ticket_id).where(
                    Message.body_text.ilike(f"%{search}%")
                ).distinct()
            )
        )
        query = query.where(or_(*search_filters))

    count_q = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar()

    effective_date = func.coalesce(Ticket.received_at, Ticket.created_at)
    if sort == "sla":
        query = query.order_by(Ticket.sla_deadline.asc().nulls_last())
    elif sort == "priority":
        query = query.order_by(Ticket.priority.desc())
    elif sort == "newest":
        query = query.order_by(effective_date.desc())
    elif sort == "updated":
        query = query.order_by(Ticket.updated_at.desc().nulls_last())
    else:
        query = query.order_by(effective_date.asc())

    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.options(joinedload(Ticket.customer), joinedload(Ticket.agent))
    result = await db.execute(query)
    tickets = result.unique().scalars().all()

    # Compute is_unread for each ticket
    ticket_ids = [t.id for t in tickets]
    unread_set = set()
    if ticket_ids:
        viewed_q = await db.execute(
            select(TicketView.ticket_id, TicketView.viewed_at)
            .where(TicketView.user_id == user.id, TicketView.ticket_id.in_(ticket_ids))
        )
        viewed_map = {row[0]: row[1] for row in viewed_q.all()}
        for t in tickets:
            view_time = viewed_map.get(t.id)
            if view_time is None or t.updated_at > view_time:
                unread_set.add(t.id)

    return TicketListResponse(
        tickets=[_ticket_to_response(t, is_unread=(t.id in unread_set)) for t in tickets],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/next")
async def next_ticket(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Fila inteligente: retorna o próximo ticket mais urgente para o agente."""
    query = select(Ticket).where(
        Ticket.status.in_(["open", "in_progress", "waiting", "analyzing", "waiting_supplier", "waiting_resend"]),
    )
    # Agentes veem só os deles
    if user.role == "agent":
        query = query.where(Ticket.assigned_to == user.id)
    else:
        # Admins/supervisores: prioriza tickets atribuídos a eles, depois sem agente
        query = query.where(or_(Ticket.assigned_to == user.id, Ticket.assigned_to.is_(None)))

    # Ordena: SLA mais urgente primeiro, depois prioridade
    query = query.order_by(
        Ticket.sla_breached.desc(),  # SLA estourado primeiro
        Ticket.sla_deadline.asc().nulls_last(),  # Mais próximo de estourar
    ).limit(1)

    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    if not ticket:
        return {"ticket_id": None, "message": "Nenhum ticket pendente na sua fila"}
    return {"ticket_id": ticket.id, "number": ticket.number, "subject": ticket.subject, "priority": ticket.priority}


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(selectinload(Ticket.messages), joinedload(Ticket.customer), joinedload(Ticket.agent))
    )
    ticket = result.unique().scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    return _ticket_to_response(ticket, include_messages=True)


async def _check_duplicate(db: AsyncSession, customer_email: str, subject: str) -> Ticket | None:
    """RF-007: Check for duplicate ticket from same customer with matching subject in last 24h."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await db.execute(
        select(Ticket)
        .join(Customer)
        .where(
            Customer.email == customer_email,
            Ticket.created_at >= cutoff,
            Ticket.status.notin_(["resolved", "closed"]),
            Ticket.subject == subject,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _check_blacklist(customer: Customer) -> dict | None:
    """RF-025: Auto-check blacklist rules."""
    reasons = []
    if customer.is_blacklisted:
        return {"blacklisted": True, "reason": customer.blacklist_reason or "Cliente na blacklist"}
    if customer.chargeback_count >= BLACKLIST_RULES["max_chargebacks"]:
        reasons.append(f"{customer.chargeback_count} chargebacks")
    if customer.resend_count >= BLACKLIST_RULES["max_resends"]:
        reasons.append(f"{customer.resend_count} reenvios")
    if reasons:
        return {"blacklisted": False, "warning": True, "reasons": reasons}
    return None


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(body: TicketCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # Find or create customer
    result = await db.execute(select(Customer).where(Customer.email == body.customer_email))
    customer = result.scalar_one_or_none()
    if not customer:
        customer = Customer(name=body.customer_name, email=body.customer_email)
        db.add(customer)
        await db.flush()

    customer.total_tickets += 1
    if customer.total_tickets >= 3:
        customer.is_repeat = True

    # RF-007: Anti-duplication check
    duplicate = await _check_duplicate(db, body.customer_email, body.subject)
    if duplicate:
        msg = Message(
            ticket_id=duplicate.id,
            type="inbound",
            sender_email=customer.email,
            sender_name=customer.name,
            body_text=body.body,
        )
        db.add(msg)
        duplicate.updated_at = datetime.now(timezone.utc)
        db.add(AuditLog(ticket_id=duplicate.id, user_id=user.id, action="duplicate_merged",
                        details={"original_subject": body.subject}))
        await db.commit()
        await db.refresh(duplicate)
        return _ticket_to_response(duplicate)

    from app.services.ticket_number import get_next_ticket_number
    next_num = await get_next_ticket_number(db)

    sla_info = _calc_sla(None, body.priority)

    ticket = Ticket(
        number=next_num,
        subject=body.subject,
        customer_id=customer.id,
        priority=sla_info["priority"],
        tags=body.tags or [],
        sla_deadline=sla_info["sla_deadline"],
        sla_response_deadline=sla_info["sla_response_deadline"],
    )
    db.add(ticket)
    await db.flush()

    msg = Message(
        ticket_id=ticket.id,
        type="inbound",
        sender_email=customer.email,
        sender_name=customer.name,
        body_text=body.body,
    )
    db.add(msg)
    db.add(AuditLog(ticket_id=ticket.id, user_id=user.id, action="ticket_created"))

    # RF-025: Check blacklist
    bl_check = await _check_blacklist(customer)
    if bl_check:
        if bl_check.get("blacklisted"):
            ticket.tags = (ticket.tags or []) + ["BLACKLIST"]
            ticket.priority = "urgent"
            ticket.legal_risk = True
        elif bl_check.get("warning"):
            ticket.tags = (ticket.tags or []) + ["ALERTA_CLIENTE"]

    # AI Triage (non-blocking)
    try:
        from app.services.ai_service import triage_ticket as ai_triage
        triage = await ai_triage(
            subject=body.subject,
            body=body.body,
            customer_name=body.customer_name,
            is_repeat=customer.is_repeat,
        )
        if triage:
            if triage.get("category"):
                ticket.ai_category = triage["category"]
                ticket.category = triage["category"]
                sla_info = _calc_sla(triage["category"], ticket.priority)
                ticket.sla_deadline = sla_info["sla_deadline"]
                ticket.sla_response_deadline = sla_info["sla_response_deadline"]
                ticket.priority = sla_info["priority"]
            if triage.get("priority"):
                ticket.priority = triage["priority"]
                sla_info = _calc_sla(ticket.category, triage["priority"])
                ticket.sla_deadline = sla_info["sla_deadline"]
                ticket.sla_response_deadline = sla_info["sla_response_deadline"]
            if triage.get("sentiment"):
                ticket.sentiment = triage["sentiment"]
            if triage.get("legal_risk") is not None:
                ticket.legal_risk = triage["legal_risk"]
            if triage.get("tags"):
                ticket.tags = list(set((ticket.tags or []) + triage["tags"]))
            if triage.get("confidence"):
                ticket.ai_confidence = triage["confidence"]
            if triage.get("summary"):
                ticket.ai_summary = triage["summary"]
    except Exception as e:
        logger.warning(f"AI triage skipped: {e}")

    # Generate protocol
    try:
        from app.services.protocol_service import assign_protocol
        await assign_protocol(ticket, db)
    except Exception as e:
        logger.warning(f"Protocol assignment skipped: {e}")

    # Auto-assign if not manually assigned
    if not ticket.assigned_to:
        try:
            await _auto_assign_single(ticket, db, user)
        except Exception as e:
            logger.warning(f"Auto-assign skipped: {e}")

    await db.commit()

    from app.services.cache import cache_delete_pattern
    await cache_delete_pattern("dashboard:*")
    await cache_delete_pattern("gamification:*")

    await db.refresh(ticket)

    # Real-time notification
    try:
        await notify_new_ticket(ticket.id, ticket.number, ticket.subject, ticket.customer.name if ticket.customer else "")
    except Exception as e:
        logger.warning(f"WS notify_new_ticket failed: {e}")

    return _ticket_to_response(ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: str, body: TicketUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id).options(joinedload(Ticket.customer))
    )
    ticket = result.unique().scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    changes = {}
    update_data = body.model_dump(exclude_unset=True)

    # Validate status and priority values
    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status inválido: {body.status}")
    if body.priority and body.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Prioridade inválida: {body.priority}")

    for field, value in update_data.items():
        old = getattr(ticket, field, None)
        setattr(ticket, field, value)
        changes[field] = {"from": old, "to": value}

    if body.status in ("resolved", "closed") and not ticket.resolved_at:
        ticket.resolved_at = datetime.now(timezone.utc)
    # Send CSAT email only when resolved (not closed)
    if body.status == "resolved":
        try:
            from app.services.csat_service import send_csat_email
            send_csat_email(ticket)
        except Exception as e:
            logger.warning(f"Failed to send CSAT email for ticket {ticket_id}: {e}")
    if body.status == "escalated" and not ticket.escalated_at:
        ticket.escalated_at = datetime.now(timezone.utc)

    if body.category or body.priority:
        sla_info = _calc_sla(body.category or ticket.category, body.priority or ticket.priority)
        ticket.sla_deadline = sla_info["sla_deadline"]
        ticket.sla_response_deadline = sla_info["sla_response_deadline"]

    ticket.updated_at = datetime.now(timezone.utc)
    db.add(AuditLog(ticket_id=ticket.id, user_id=user.id, action="ticket_updated", details=changes))
    await db.commit()

    from app.services.cache import cache_delete_pattern
    await cache_delete_pattern("dashboard:*")
    await cache_delete_pattern("gamification:*")

    await db.refresh(ticket)

    # Real-time notifications
    try:
        desc = ", ".join(f"{k}: {v['to']}" for k, v in changes.items())
        await notify_ticket_update(ticket.id, ticket.number, "updated", user.name, desc, exclude_user=user.id)
        if "assigned_to" in changes and changes["assigned_to"]["to"]:
            agent = await db.execute(select(User).where(User.id == changes["assigned_to"]["to"]))
            agent = agent.scalar_one_or_none()
            if agent:
                await notify_assignment(ticket.id, ticket.number, agent.id, agent.name)
    except Exception as e:
        logger.warning(f"WS notify_ticket_update failed: {e}")

    return _ticket_to_response(ticket)


@router.post("/bulk-assign")
async def bulk_assign(body: TicketBulkAssign, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Ticket).where(Ticket.id.in_(body.ticket_ids)))
    tickets = result.scalars().all()
    for ticket in tickets:
        if body.assigned_to:
            ticket.assigned_to = body.assigned_to
        if body.inbox_id:
            ticket.inbox_id = body.inbox_id
        ticket.updated_at = datetime.now(timezone.utc)
        db.add(AuditLog(ticket_id=ticket.id, user_id=user.id, action="bulk_assign",
                        details={"assigned_to": body.assigned_to, "inbox_id": body.inbox_id}))
    await db.commit()
    return {"updated": len(tickets)}


@router.post("/bulk-update")
async def bulk_update(body: TicketBulkUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status inválido: {body.status}")
    if body.priority and body.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Prioridade inválida: {body.priority}")
    result = await db.execute(
        select(Ticket).where(Ticket.id.in_(body.ticket_ids)).options(joinedload(Ticket.customer))
    )
    tickets = result.unique().scalars().all()
    csat_tickets = []
    for ticket in tickets:
        changes = {}
        if body.status:
            changes["status"] = {"from": ticket.status, "to": body.status}
            ticket.status = body.status
            if body.status in ("resolved", "closed") and not ticket.resolved_at:
                ticket.resolved_at = datetime.now(timezone.utc)
            if body.status == "resolved":
                csat_tickets.append(ticket)
        if body.priority:
            changes["priority"] = {"from": ticket.priority, "to": body.priority}
            ticket.priority = body.priority
            sla_info = _calc_sla(ticket.category, body.priority)
            ticket.sla_deadline = sla_info["sla_deadline"]
            ticket.sla_response_deadline = sla_info["sla_response_deadline"]
        if body.assigned_to:
            changes["assigned_to"] = {"from": ticket.assigned_to, "to": body.assigned_to}
            ticket.assigned_to = body.assigned_to
        if body.inbox_id:
            changes["inbox_id"] = {"from": ticket.inbox_id, "to": body.inbox_id}
            ticket.inbox_id = body.inbox_id
        ticket.updated_at = datetime.now(timezone.utc)
        db.add(AuditLog(ticket_id=ticket.id, user_id=user.id, action="bulk_update", details=changes))
    await db.commit()

    from app.services.cache import cache_delete_pattern
    await cache_delete_pattern("dashboard:*")
    await cache_delete_pattern("gamification:*")

    # Send CSAT emails only for resolved tickets (not closed)
    for ticket in csat_tickets:
        try:
            from app.services.csat_service import send_csat_email
            send_csat_email(ticket)
        except Exception as e:
            logger.warning(f"Failed to send CSAT email for ticket #{ticket.number}: {e}")

    return {"updated": len(tickets)}


async def _auto_assign_single(ticket: Ticket, db: AsyncSession, user: User):
    """Auto-assign a single ticket using specialty routing + round-robin."""
    agents_result = await db.execute(
        select(User).where(User.is_active == True, User.role.in_(["agent", "supervisor", "admin"]))
    )
    agents = agents_result.scalars().all()
    if not agents:
        return

    # Build load map
    agent_loads = {}
    agent_map = {}
    for agent in agents:
        count_result = await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.assigned_to == agent.id,
                Ticket.status.in_(["open", "in_progress", "waiting", "analyzing", "waiting_supplier", "waiting_resend"])
            )
        )
        agent_loads[agent.id] = count_result.scalar()
        agent_map[agent.id] = agent

    # Group by specialty
    specialty_agents = {}
    general_agents = []
    for agent in agents:
        spec = getattr(agent, 'specialty', None) or 'geral'
        if spec != 'geral':
            specialty_agents.setdefault(spec, []).append(agent.id)
        general_agents.append(agent.id)

    def pick_agent(candidates):
        available = [
            aid for aid in candidates
            if agent_loads.get(aid, 0) < getattr(agent_map[aid], 'max_tickets', 20)
        ]
        if not available:
            return None
        return min(available, key=lambda aid: agent_loads.get(aid, 0))

    # Try specialty routing
    needed_specialty = CATEGORY_ROUTING.get(ticket.category)
    chosen = None
    if needed_specialty and needed_specialty in specialty_agents:
        chosen = pick_agent(specialty_agents[needed_specialty])

    # Fallback to general round-robin
    if not chosen:
        chosen = pick_agent(general_agents)

    if not chosen:
        return

    ticket.assigned_to = chosen
    db.add(AuditLog(ticket_id=ticket.id, user_id=user.id, action="auto_assign",
                    details={"assigned_to": chosen, "specialty_match": needed_specialty}))

    # Notify agent
    try:
        agent = agent_map[chosen]
        await notify_assignment(ticket.id, ticket.number, agent.id, agent.name)
    except Exception as e:
        logger.warning(f"WS notify_assignment failed: {e}")


@router.post("/auto-assign")
async def auto_assign(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """RF-013: Auto-assign with specialty routing.
    1) Match ticket category -> specialty via CATEGORY_ROUTING
    2) Find specialist agents with capacity
    3) Fallback to any agent (round-robin by load)
    """
    agents_result = await db.execute(
        select(User).where(User.is_active == True, User.role.in_(["agent", "supervisor", "admin"]))
    )
    agents = agents_result.scalars().all()
    if not agents:
        return {"assigned": 0, "message": "Nenhum agente disponível"}

    # Build load map: agent_id -> current open ticket count
    agent_loads = {}
    agent_map = {}
    for agent in agents:
        count_result = await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.assigned_to == agent.id,
                Ticket.status.in_(["open", "in_progress", "waiting", "analyzing", "waiting_supplier", "waiting_resend"])
            )
        )
        load = count_result.scalar()
        agent_loads[agent.id] = load
        agent_map[agent.id] = agent

    # Group agents by specialty
    specialty_agents = {}  # specialty -> [agent_ids sorted by load]
    general_agents = []
    for agent in agents:
        spec = getattr(agent, 'specialty', None) or 'geral'
        if spec != 'geral':
            specialty_agents.setdefault(spec, []).append(agent.id)
        general_agents.append(agent.id)

    def pick_agent(candidates):
        """Pick agent with lowest load that hasn't hit max_tickets."""
        available = [
            aid for aid in candidates
            if agent_loads.get(aid, 0) < getattr(agent_map[aid], 'max_tickets', 20)
        ]
        if not available:
            return None  # All agents at capacity
        return min(available, key=lambda aid: agent_loads.get(aid, 0))

    unassigned = await db.execute(
        select(Ticket).where(
            Ticket.assigned_to.is_(None),
            Ticket.status.in_(["open", "in_progress"])
        ).order_by(Ticket.sla_deadline.asc())
    )
    tickets = unassigned.scalars().all()
    assigned_count = 0
    routed_by_specialty = 0

    for ticket in tickets:
        # Step 1: Try specialty routing
        needed_specialty = CATEGORY_ROUTING.get(ticket.category)
        chosen = None

        if needed_specialty and needed_specialty in specialty_agents:
            specialists = specialty_agents[needed_specialty]
            if specialists:
                chosen = pick_agent(specialists)
                if chosen:
                    routed_by_specialty += 1

        # Step 2: Fallback to general round-robin
        if not chosen:
            chosen = pick_agent(general_agents)

        # Skip if no agent available (all at capacity)
        if not chosen:
            continue

        ticket.assigned_to = chosen
        ticket.updated_at = datetime.now(timezone.utc)
        agent_loads[chosen] = agent_loads.get(chosen, 0) + 1
        db.add(AuditLog(ticket_id=ticket.id, user_id=user.id, action="auto_assign",
                        details={"assigned_to": chosen, "specialty_match": needed_specialty}))
        assigned_count += 1

        # Notify agent
        try:
            agent = agent_map[chosen]
            await notify_assignment(ticket.id, ticket.number, agent.id, agent.name)
        except Exception as e:
            logger.warning(f"WS notify_assignment failed: {e}")

    await db.commit()
    return {"assigned": assigned_count, "routed_by_specialty": routed_by_specialty}


@router.get("/customer/{customer_id}/history")
async def customer_history(customer_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Ticket).where(Ticket.customer_id == customer_id)
        .order_by(Ticket.created_at.desc()).limit(20)
    )
    tickets = result.scalars().all()
    return [
        {
            "id": t.id, "number": t.number, "subject": t.subject,
            "status": t.status, "priority": t.priority, "category": t.category,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
        }
        for t in tickets
    ]


@router.get("/{ticket_id}/preview")
async def ticket_preview(ticket_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    msg_result = await db.execute(
        select(Message).where(Message.ticket_id == ticket_id)
        .order_by(Message.created_at.desc()).limit(1)
    )
    last_msg = msg_result.scalar_one_or_none()
    return {
        "ticket_id": ticket.id, "number": ticket.number, "subject": ticket.subject,
        "customer_name": ticket.customer.name if ticket.customer else None,
        "last_message": {
            "body_text": last_msg.body_text[:300] if last_msg else None,
            "type": last_msg.type if last_msg else None,
            "sender_name": last_msg.sender_name if last_msg else None,
            "created_at": last_msg.created_at.isoformat() if last_msg else None,
        } if last_msg else None,
    }


# ── Supplier Notes (RF-026) ──

class SupplierNoteUpdate(BaseModel):
    supplier_notes: str


@router.patch("/{ticket_id}/supplier-notes")
async def update_supplier_notes(ticket_id: str, body: SupplierNoteUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    ticket.supplier_notes = body.supplier_notes
    ticket.updated_at = datetime.now(timezone.utc)
    db.add(AuditLog(ticket_id=ticket.id, user_id=user.id, action="supplier_notes_updated"))
    await db.commit()
    return {"ok": True}


# ── Internal Notes ──

class InternalNotesUpdate(BaseModel):
    internal_notes: str

@router.patch("/{ticket_id}/internal-notes")
async def update_internal_notes(ticket_id: str, body: InternalNotesUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    ticket.internal_notes = body.internal_notes
    ticket.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


# ── Protocol Email ──

@router.post("/{ticket_id}/send-protocol")
async def send_protocol_email_endpoint(ticket_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Send protocol confirmation email to customer (agent-triggered)."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    if not ticket.protocol:
        # Generate one if missing
        from app.services.protocol_service import assign_protocol
        await assign_protocol(ticket, db)
    if ticket.protocol_sent:
        return {"ok": True, "message": "Protocolo já foi enviado anteriormente", "protocol": ticket.protocol}

    from app.services.protocol_service import send_protocol_email
    sent = send_protocol_email(ticket)
    if sent:
        ticket.protocol_sent = True
        await db.commit()
        return {"ok": True, "message": "Email de protocolo enviado com sucesso", "protocol": ticket.protocol}
    else:
        raise HTTPException(500, "Falha ao enviar email de protocolo")


# ── Tracking (RF-021) ──

class TrackingUpdate(BaseModel):
    tracking_code: str
    tracking_status: str | None = None


@router.patch("/{ticket_id}/tracking")
async def update_tracking(ticket_id: str, body: TrackingUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """RF-021: Save tracking code and auto-query carrier API."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    ticket.tracking_code = body.tracking_code
    if body.tracking_status:
        ticket.tracking_status = body.tracking_status
    ticket.updated_at = datetime.now(timezone.utc)
    db.add(AuditLog(ticket_id=ticket.id, user_id=user.id, action="tracking_updated",
                    details={"tracking_code": body.tracking_code}))

    # Auto-query tracking API
    tracking_result = None
    try:
        from app.services.tracking_service import track_and_update_ticket
        tracking_result = await track_and_update_ticket(db, ticket)
    except Exception as e:
        logger.warning(f"Tracking query failed: {e}")

    await db.commit()
    return {"ok": True, "tracking": tracking_result}


@router.get("/{ticket_id}/tracking")
async def get_tracking(ticket_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """RF-022: Refresh tracking status from carrier API."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    if not ticket.tracking_code:
        return {"error": "Sem código de rastreio"}

    from app.services.tracking_service import track_and_update_ticket
    tracking_result = await track_and_update_ticket(db, ticket)
    return tracking_result


# ── Attachment Upload ──

@router.post("/upload-attachment")
async def upload_attachment(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Upload a file for email attachment. Stores locally."""
    import uuid
    from pathlib import Path

    # 25MB limit
    MAX_SIZE = 25 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, f"Arquivo muito grande. Máximo: 25MB")

    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)

    # UUID prefix to avoid collisions
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename or 'attachment'}"
    file_path = uploads_dir / safe_name
    file_path.write_bytes(content)

    return {
        "name": file.filename,
        "file_path": str(file_path),
        "url": f"/api/uploads/{safe_name}",
        "size": len(content),
        "mime_type": file.content_type,
    }


# ── Messages ──

@router.post("/{ticket_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(ticket_id: str, body: MessageCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    # Clean cc/bcc from body
    cc_list = [e.strip() for e in body.cc if e.strip()] if body.cc else None
    bcc_list = [e.strip() for e in body.bcc if e.strip()] if body.bcc else None

    # Parse scheduled_at
    is_scheduled = False
    scheduled_at = body.scheduled_at
    if scheduled_at:
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        is_scheduled = scheduled_at > datetime.now(timezone.utc)

    # For outbound gmail messages, try to send email BEFORE saving to DB
    # This way if email fails, the agent sees the error and can retry
    if body.type == "outbound" and not is_scheduled and ticket.source == "gmail" and ticket.customer:
        from app.services.gmail_service import send_email
        thread_msg = await db.execute(
            select(Message).where(
                Message.ticket_id == ticket.id,
                Message.gmail_thread_id.isnot(None),
            ).limit(1)
        )
        first_msg = thread_msg.scalars().first()
        email_body = body.body_text or ""
        if user.email_signature:
            email_body += f"\n\n--\n{user.email_signature}"
        email_result = send_email(
            to=ticket.customer.email,
            subject=f"Re: {ticket.subject}",
            body_text=email_body,
            thread_id=first_msg.gmail_thread_id if first_msg else None,
            in_reply_to=first_msg.gmail_message_id if first_msg else None,
            cc=cc_list,
            bcc=bcc_list,
            attachments=body.attachments if body.attachments else None,
        )
        if not email_result:
            raise HTTPException(status_code=502, detail="Falha ao enviar email. Verifique a conexão com o Gmail.")

    msg = Message(
        ticket_id=ticket.id,
        type=body.type,
        sender_email=user.email,
        sender_name=user.name,
        body_text=body.body_text,
        body_html=body.body_html,
        cc=", ".join(cc_list) if cc_list else None,
        bcc=", ".join(bcc_list) if bcc_list else None,
        attachments=body.attachments if body.attachments else None,
        scheduled_at=scheduled_at if is_scheduled else None,
        is_scheduled=is_scheduled,
    )
    db.add(msg)
    if body.type == "outbound" and not is_scheduled and not ticket.first_response_at:
        ticket.first_response_at = datetime.now(timezone.utc)
    if body.type == "outbound" and not is_scheduled:
        ticket.last_agent_response_at = datetime.now(timezone.utc)
        # Auto-move to "Respondidos": when agent replies, set status to waiting
        if ticket.status in ("open", "in_progress", "analyzing"):
            ticket.status = "waiting"
    ticket.updated_at = datetime.now(timezone.utc)
    db.add(AuditLog(ticket_id=ticket.id, user_id=user.id, action=f"message_{body.type}"))
    await db.commit()
    await db.refresh(msg)

    # For outbound slack messages, send after saving (best-effort)
    if body.type == "outbound" and not is_scheduled:
        try:
            if ticket.source == "slack" and ticket.slack_channel_id and ticket.slack_thread_ts:
                from app.services.slack_service import send_agent_reply_to_slack
                await send_agent_reply_to_slack(
                    channel=ticket.slack_channel_id,
                    thread_ts=ticket.slack_thread_ts,
                    agent_name=user.name,
                    message_text=body.body_text or "",
                )
        except Exception as e:
            logger.error(f"Failed to send reply to Slack: {e}")

    # RF-019: Auto-generate summary every 3 messages
    try:
        msg_count = await db.execute(
            select(func.count()).select_from(Message).where(Message.ticket_id == ticket.id)
        )
        total_msgs = msg_count.scalar()
        if total_msgs >= 3 and total_msgs % 3 == 0:
            # Fetch recent messages for summary
            recent = await db.execute(
                select(Message).where(Message.ticket_id == ticket.id)
                .order_by(Message.created_at.desc()).limit(15)
            )
            msgs = [
                {"sender_name": m.sender_name, "type": m.type, "body_text": m.body_text}
                for m in reversed(recent.scalars().all())
            ]
            from app.services.ai_service import summarize_ticket
            summary = await summarize_ticket(
                ticket.subject, msgs,
                category=ticket.category or "",
                customer_name=ticket.customer.name if ticket.customer else "",
            )
            if summary:
                ticket.ai_summary = summary
                await db.commit()
    except Exception as e:
        logger.warning(f"Auto-summary failed: {e}")

    return MessageResponse.model_validate(msg)


@router.post("/{ticket_id}/summarize")
async def generate_summary(ticket_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """RF-019: Manually trigger AI summary generation."""
    from app.services.ai_service import is_credits_exhausted, CreditExhaustedError
    if is_credits_exhausted():
        raise HTTPException(402, detail={"error": "credits_exhausted", "message": "Creditos IA esgotados. Recarregue em console.anthropic.com"})

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")

    msgs_result = await db.execute(
        select(Message).where(Message.ticket_id == ticket_id)
        .order_by(Message.created_at.asc()).limit(20)
    )
    msgs = [
        {"sender_name": m.sender_name, "type": m.type, "body_text": m.body_text}
        for m in msgs_result.scalars().all()
    ]

    if not msgs:
        return {"summary": None, "message": "Nenhuma mensagem para resumir"}

    from app.services.ai_service import summarize_ticket
    try:
        summary = await summarize_ticket(
            ticket.subject, msgs,
            category=ticket.category or "",
            customer_name=ticket.customer.name if ticket.customer else "",
        )
    except CreditExhaustedError:
        raise HTTPException(402, detail={"error": "credits_exhausted", "message": "Creditos IA esgotados. Recarregue em console.anthropic.com"})
    if summary:
        ticket.ai_summary = summary
        ticket.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return {"summary": summary}
    return {"summary": None, "message": "Erro ao gerar resumo"}


# ── CSAT ──

class CSATSubmit(BaseModel):
    score: int
    nps_score: int | None = None
    comment: str | None = None


@router.post("/{ticket_id}/csat")
async def submit_csat(ticket_id: str, body: CSATSubmit, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    from app.models.csat import CSATRating
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    existing = await db.execute(select(CSATRating).where(CSATRating.ticket_id == ticket_id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Avaliação já enviada para este ticket")
    rating = CSATRating(
        ticket_id=ticket_id,
        agent_id=ticket.assigned_to,
        score=max(1, min(5, body.score)),
        nps_score=max(0, min(10, body.nps_score)) if body.nps_score is not None else None,
        comment=body.comment,
    )
    db.add(rating)
    await db.commit()
    return {"ok": True}


# ── Blacklist Customer (RF-025) ──

class BlacklistBody(BaseModel):
    reason: str


@router.post("/customer/{customer_id}/blacklist")
async def blacklist_customer(customer_id: str, body: BlacklistBody, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("admin", "supervisor"):
        raise HTTPException(403, "Apenas admins/supervisores podem gerenciar blacklist")
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(404, "Cliente não encontrado")
    customer.is_blacklisted = True
    customer.blacklist_reason = body.reason
    customer.blacklisted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "message": f"Cliente {customer.name} adicionado à blacklist"}


@router.delete("/customer/{customer_id}/blacklist")
async def unblacklist_customer(customer_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("admin", "supervisor"):
        raise HTTPException(403, "Apenas admins/supervisores podem gerenciar blacklist")
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(404, "Cliente não encontrado")
    customer.is_blacklisted = False
    customer.blacklist_reason = None
    customer.blacklisted_at = None
    await db.commit()
    return {"ok": True}


# ── Ticket Merge ──

class TicketMergeRequest(BaseModel):
    source_ticket_id: str
    target_ticket_id: str


@router.post("/merge")
async def merge_tickets(
    body: TicketMergeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Merge two tickets: move messages from source to target, mark source as merged."""
    if body.source_ticket_id == body.target_ticket_id:
        raise HTTPException(status_code=400, detail="Não é possível mesclar um ticket com ele mesmo")

    # Fetch both tickets
    source_result = await db.execute(
        select(Ticket).where(Ticket.id == body.source_ticket_id)
    )
    source = source_result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Ticket de origem não encontrado")

    target_result = await db.execute(
        select(Ticket).where(Ticket.id == body.target_ticket_id)
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Ticket de destino não encontrado")

    # Prevent merging already-merged tickets
    if source.status == "merged":
        raise HTTPException(status_code=400, detail="Ticket de origem já foi mesclado anteriormente")
    if target.status == "merged":
        raise HTTPException(status_code=400, detail="Ticket de destino já foi mesclado anteriormente")

    # 1. Move all messages from source to target
    messages_result = await db.execute(
        select(Message).where(Message.ticket_id == source.id)
    )
    source_messages = messages_result.scalars().all()
    moved_message_ids = []
    for msg in source_messages:
        moved_message_ids.append(msg.id)
        msg.ticket_id = target.id

    # 2. Copy internal notes from source to target (append)
    if source.internal_notes:
        separator = f"\n\n--- Notas do ticket #{source.number} (mesclado) ---\n"
        if target.internal_notes:
            target.internal_notes = target.internal_notes + separator + source.internal_notes
        else:
            target.internal_notes = separator.strip() + "\n" + source.internal_notes

    # 3. Mark source as merged
    source.status = "merged"
    source.merged_into_id = target.id
    source.updated_at = datetime.now(timezone.utc)

    # 4. Update target
    target.updated_at = datetime.now(timezone.utc)

    # 5. Audit log
    db.add(AuditLog(
        ticket_id=target.id,
        user_id=user.id,
        action="ticket_merge",
        details={
            "source_ticket_id": source.id,
            "source_ticket_number": source.number,
            "target_ticket_id": target.id,
            "target_ticket_number": target.number,
            "messages_moved": len(moved_message_ids),
            "moved_message_ids": moved_message_ids,
        },
    ))

    await db.commit()

    # Refresh target to get updated data
    await db.refresh(target)

    logger.info(
        f"Ticket merge: #{source.number} -> #{target.number} "
        f"({len(moved_message_ids)} messages moved) by {user.name}"
    )

    return _ticket_to_response(target)


# ── Ticket Unmerge ──

@router.post("/{ticket_id}/unmerge")
async def unmerge_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Undo a ticket merge: restore the source ticket and move its messages back.
    Uses audit log to find which messages were moved."""
    # Find the merged ticket
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    if source.status != "merged" or not source.merged_into_id:
        raise HTTPException(status_code=400, detail="Este ticket não foi mesclado")

    target_id = source.merged_into_id

    # Find the target ticket
    target_result = await db.execute(select(Ticket).where(Ticket.id == target_id))
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Ticket destino não encontrado")

    # Find the merge audit log to know which messages were moved
    audit_result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.action == "ticket_merge",
            AuditLog.details["source_ticket_id"].as_string() == ticket_id,
        )
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    audit = audit_result.scalar_one_or_none()

    # Move messages back using the exact IDs stored in the merge audit log
    restored_count = 0
    moved_ids = audit.details.get("moved_message_ids", []) if audit and audit.details else []

    if moved_ids:
        msgs_result = await db.execute(
            select(Message).where(Message.id.in_(moved_ids))
        )
        for msg in msgs_result.scalars().all():
            msg.ticket_id = source.id
            restored_count += 1

    # Restore source ticket status
    source.status = "open"
    source.merged_into_id = None
    source.updated_at = datetime.now(timezone.utc)

    # Update target
    target.updated_at = datetime.now(timezone.utc)

    # Remove merged notes from target
    if target.internal_notes and f"ticket #{source.number} (mesclado)" in target.internal_notes:
        separator = f"\n\n--- Notas do ticket #{source.number} (mesclado) ---\n"
        parts = target.internal_notes.split(separator)
        if len(parts) > 1:
            target.internal_notes = parts[0].rstrip() or None

    # Audit log
    db.add(AuditLog(
        ticket_id=source.id,
        user_id=user.id,
        action="ticket_unmerge",
        details={
            "source_ticket_id": source.id,
            "source_ticket_number": source.number,
            "target_ticket_id": target.id,
            "target_ticket_number": target.number,
            "messages_restored": restored_count,
        },
    ))

    await db.commit()

    logger.info(
        f"Ticket unmerge: #{source.number} from #{target.number} "
        f"({restored_count} messages restored) by {user.name}"
    )

    return {
        "ok": True,
        "message": f"Merge desfeito. Ticket #{source.number} restaurado.",
        "messages_restored": restored_count,
        "source_ticket_id": source.id,
    }
