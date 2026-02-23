"""Tracking management endpoints - painel de rastreamento de pacotes."""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.services.tracking_service import track_and_update_ticket

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/list")
async def list_all_trackings(
    status_filter: str = Query("all", regex="^(all|pending|in_transit|delivered|error|problem)$"),
    carrier_filter: str = Query("all"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lista todos os tickets com código de rastreio."""
    query = (
        select(Ticket)
        .where(Ticket.tracking_code.isnot(None), Ticket.tracking_code != "")
        .order_by(Ticket.updated_at.desc())
    )

    if status_filter == "pending":
        query = query.where(
            or_(
                Ticket.tracking_status.is_(None),
                Ticket.tracking_status == "",
                Ticket.tracking_status.ilike("%aguardando%"),
                Ticket.tracking_status.ilike("%registrado%"),
                Ticket.tracking_status.ilike("%postado%"),
            )
        )
    elif status_filter == "in_transit":
        query = query.where(
            Ticket.tracking_status.isnot(None),
            ~Ticket.tracking_status.ilike("%entregue%"),
            ~Ticket.tracking_status.ilike("%aguardando%"),
            Ticket.tracking_status != "",
        )
    elif status_filter == "delivered":
        query = query.where(Ticket.tracking_status.ilike("%entregue%"))
    elif status_filter == "error":
        query = query.where(Ticket.tracking_status.ilike("%erro%"))
    elif status_filter == "problem":
        # Barrados, exceções, tentativas de entrega falhas, devolvido, extraviado, etc.
        query = query.where(
            or_(
                Ticket.tracking_status.ilike("%barr%"),
                Ticket.tracking_status.ilike("%exce%"),
                Ticket.tracking_status.ilike("%devol%"),
                Ticket.tracking_status.ilike("%extrav%"),
                Ticket.tracking_status.ilike("%ausente%"),
                Ticket.tracking_status.ilike("%recusad%"),
                Ticket.tracking_status.ilike("%não encontr%"),
                Ticket.tracking_status.ilike("%tentativa%"),
                Ticket.tracking_status.ilike("%retorn%"),
                Ticket.tracking_status.ilike("%falh%"),
                Ticket.tracking_status.ilike("%sinistro%"),
                Ticket.tracking_status.ilike("%roub%"),
                Ticket.tracking_status.ilike("%avaria%"),
                Ticket.tracking_status.ilike("%cancel%"),
                Ticket.tracking_status.ilike("%erro%"),
                Ticket.tracking_status.ilike("%bloqueado%"),
                Ticket.tracking_status.ilike("%fiscaliz%"),
                Ticket.tracking_status.ilike("%tribut%"),
                Ticket.tracking_status.ilike("%retido%"),
                Ticket.tracking_status.ilike("%apreend%"),
            )
        )

    if carrier_filter != "all":
        # Filtrar pelo carrier armazenado no tracking_data
        query = query.where(
            Ticket.tracking_data["carrier"].astext == carrier_filter
        )

    # Count total
    count_q = select(func.count()).select_from(
        query.subquery()
    )
    total = (await db.execute(count_q)).scalar()

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    tickets = result.scalars().all()

    items = []
    for t in tickets:
        items.append({
            "ticket_id": t.id,
            "ticket_number": t.number,
            "subject": t.subject,
            "customer_name": t.customer.name if t.customer else "N/A",
            "customer_email": t.customer.email if t.customer else "",
            "category": t.category,
            "status": t.status,
            "tracking_code": t.tracking_code,
            "tracking_status": t.tracking_status or "Sem atualização",
            "tracking_data": t.tracking_data,
            "carrier": (t.tracking_data or {}).get("carrier", "desconhecido"),
            "delivered": (t.tracking_data or {}).get("delivered", False),
            "last_event": ((t.tracking_data or {}).get("events", [{}])[0] if (t.tracking_data or {}).get("events") else None),
            "created_at": str(t.created_at),
            "updated_at": str(t.updated_at),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/summary")
async def tracking_summary(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Resumo geral dos rastreamentos."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Total com rastreio
    total_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.tracking_code.isnot(None), Ticket.tracking_code != "", Ticket.created_at >= since)
    )
    total = total_q.scalar()

    # Entregues
    delivered_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(
            Ticket.tracking_code.isnot(None),
            Ticket.tracking_status.ilike("%entregue%"),
            Ticket.created_at >= since,
        )
    )
    delivered = delivered_q.scalar()

    # Em trânsito
    in_transit_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(
            Ticket.tracking_code.isnot(None),
            Ticket.tracking_code != "",
            Ticket.tracking_status.isnot(None),
            ~Ticket.tracking_status.ilike("%entregue%"),
            ~Ticket.tracking_status.ilike("%aguardando%"),
            ~Ticket.tracking_status.ilike("%erro%"),
            Ticket.tracking_status != "",
            Ticket.created_at >= since,
        )
    )
    in_transit = in_transit_q.scalar()

    # Com problema (barrados, exceção, devolvido, etc.)
    problem_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(
            Ticket.tracking_code.isnot(None),
            Ticket.tracking_code != "",
            Ticket.created_at >= since,
            or_(
                Ticket.tracking_status.ilike("%barr%"),
                Ticket.tracking_status.ilike("%exce%"),
                Ticket.tracking_status.ilike("%devol%"),
                Ticket.tracking_status.ilike("%extrav%"),
                Ticket.tracking_status.ilike("%ausente%"),
                Ticket.tracking_status.ilike("%recusad%"),
                Ticket.tracking_status.ilike("%não encontr%"),
                Ticket.tracking_status.ilike("%tentativa%"),
                Ticket.tracking_status.ilike("%retorn%"),
                Ticket.tracking_status.ilike("%falh%"),
                Ticket.tracking_status.ilike("%sinistro%"),
                Ticket.tracking_status.ilike("%roub%"),
                Ticket.tracking_status.ilike("%avaria%"),
                Ticket.tracking_status.ilike("%cancel%"),
                Ticket.tracking_status.ilike("%erro%"),
                Ticket.tracking_status.ilike("%bloqueado%"),
                Ticket.tracking_status.ilike("%fiscaliz%"),
                Ticket.tracking_status.ilike("%tribut%"),
                Ticket.tracking_status.ilike("%retido%"),
                Ticket.tracking_status.ilike("%apreend%"),
            ),
        )
    )
    problems = problem_q.scalar()

    # Pendentes (sem atualização)
    pending = total - delivered - in_transit - problems

    # Por transportadora
    # Buscamos todos os tickets com tracking_data para contar carriers
    carrier_q = await db.execute(
        select(Ticket.tracking_data).where(
            Ticket.tracking_code.isnot(None),
            Ticket.tracking_data.isnot(None),
            Ticket.created_at >= since,
        )
    )
    carriers = {}
    for row in carrier_q.all():
        data = row[0] if row[0] else {}
        carrier = data.get("carrier", "desconhecido")
        carriers[carrier] = carriers.get(carrier, 0) + 1

    return {
        "total": total,
        "delivered": delivered,
        "in_transit": in_transit,
        "pending": pending,
        "problems": problems,
        "delivery_rate": round(delivered / max(total, 1) * 100, 1),
        "by_carrier": carriers,
    }


@router.post("/refresh-all")
async def refresh_all_trackings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Atualiza todos os rastreios ativos (não entregues)."""
    if user.role not in ("admin", "supervisor"):
        from fastapi import HTTPException
        raise HTTPException(403, "Apenas admin/supervisor")

    result = await db.execute(
        select(Ticket).where(
            Ticket.tracking_code.isnot(None),
            Ticket.tracking_code != "",
            Ticket.status.notin_(["resolved", "closed"]),
        ).limit(100)  # Limit to prevent timeout
    )
    tickets = result.scalars().all()

    updated = 0
    errors = 0
    for ticket in tickets:
        try:
            await track_and_update_ticket(db, ticket)
            updated += 1
        except Exception as e:
            logger.warning(f"Failed to refresh tracking for ticket {ticket.number}: {e}")
            errors += 1

    return {
        "updated": updated,
        "errors": errors,
        "total_processed": len(tickets),
    }


@router.post("/refresh/{ticket_id}")
async def refresh_single_tracking(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Atualiza rastreio de um ticket específico."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        from fastapi import HTTPException
        raise HTTPException(404, "Ticket não encontrado")
    if not ticket.tracking_code:
        return {"error": "Sem código de rastreio"}

    tracking_result = await track_and_update_ticket(db, ticket)
    return tracking_result


@router.post("/sync-shopify")
async def sync_shopify_tracking(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sincroniza tracking codes da Shopify para tickets que tem cliente com email.
    Busca pedidos Shopify pelo email do cliente e preenche tracking_code nos tickets."""
    if user.role not in ("admin", "supervisor"):
        from fastapi import HTTPException
        raise HTTPException(403, "Apenas admin/supervisor")

    from app.services.shopify_service import get_orders_by_email
    from app.models.customer import Customer

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Buscar tickets sem tracking_code que tem cliente com email
    result = await db.execute(
        select(Ticket)
        .where(
            or_(Ticket.tracking_code.is_(None), Ticket.tracking_code == ""),
            Ticket.customer_id.isnot(None),
            Ticket.created_at >= since,
        )
        .limit(200)
    )
    tickets = result.scalars().all()

    synced = 0
    errors = 0
    already_has = 0

    # Agrupar por email pra não fazer chamadas duplicadas
    email_cache = {}

    for ticket in tickets:
        try:
            if not ticket.customer or not ticket.customer.email:
                continue

            email = ticket.customer.email
            if email not in email_cache:
                shopify_result = await get_orders_by_email(email, limit=20)
                email_cache[email] = shopify_result.get("orders", [])

            orders = email_cache[email]

            # Tentar encontrar um pedido com tracking code
            for order in orders:
                tc = order.get("tracking_code", "")
                if tc:
                    ticket.tracking_code = tc
                    ticket.tracking_status = "Sincronizado via Shopify"
                    ticket.updated_at = datetime.now(timezone.utc)

                    # Tentar buscar status detalhado via 17track
                    try:
                        await track_and_update_ticket(db, ticket)
                    except Exception:
                        pass

                    synced += 1
                    break
            else:
                already_has += 1

        except Exception as e:
            logger.warning(f"Sync error for ticket {ticket.number}: {e}")
            errors += 1

    await db.commit()

    return {
        "synced": synced,
        "errors": errors,
        "no_tracking": already_has,
        "total_checked": len(tickets),
    }
