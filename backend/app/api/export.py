"""RF-032: Export tickets to CSV with streaming."""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket, STATUS_LABELS
from app.models.customer import Customer

router = APIRouter(prefix="/export", tags=["export"])

BATCH_SIZE = 500


@router.get("/tickets/csv")
async def export_tickets_csv(
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export filtered tickets as CSV file (streamed in batches)."""
    query = select(Ticket).join(Customer, isouter=True)

    if status:
        query = query.where(Ticket.status == status)
    if priority:
        query = query.where(Ticket.priority == priority)
    if category:
        query = query.where(Ticket.category == category)
    if date_from:
        try:
            query = query.where(Ticket.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.where(Ticket.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    query = query.order_by(Ticket.created_at.desc())

    async def generate_csv():
        # Write BOM for Excel UTF-8 compatibility
        yield b'\xef\xbb\xbf'

        # Header
        header = io.StringIO()
        writer = csv.writer(header)
        writer.writerow([
            "Numero", "Assunto", "Status", "Prioridade", "Categoria",
            "Cliente", "Email Cliente", "Agente", "Fonte",
            "Sentimento", "Risco Juridico", "SLA Estourado",
            "Tags", "Codigo Rastreio",
            "Criado em", "Primeira Resposta", "Resolvido em",
        ])
        yield header.getvalue().encode("utf-8")

        # Stream tickets in batches
        offset = 0
        while True:
            batch_query = query.offset(offset).limit(BATCH_SIZE)
            result = await db.execute(batch_query)
            tickets = result.scalars().all()

            if not tickets:
                break

            batch_output = io.StringIO()
            writer = csv.writer(batch_output)
            for t in tickets:
                writer.writerow([
                    t.number,
                    t.subject,
                    STATUS_LABELS.get(t.status, t.status),
                    t.priority,
                    t.category or "",
                    t.customer.name if t.customer else "",
                    t.customer.email if t.customer else "",
                    t.agent.name if t.agent else "Nao atribuido",
                    t.source or "web",
                    t.sentiment or "",
                    "Sim" if t.legal_risk else "Nao",
                    "Sim" if t.sla_breached else "Nao",
                    ", ".join(t.tags) if t.tags else "",
                    t.tracking_code or "",
                    t.created_at.strftime("%d/%m/%Y %H:%M") if t.created_at else "",
                    t.first_response_at.strftime("%d/%m/%Y %H:%M") if t.first_response_at else "",
                    t.resolved_at.strftime("%d/%m/%Y %H:%M") if t.resolved_at else "",
                ])
            yield batch_output.getvalue().encode("utf-8")

            if len(tickets) < BATCH_SIZE:
                break
            offset += BATCH_SIZE

    filename = f"tickets_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
