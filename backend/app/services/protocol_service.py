"""Protocol generation and notification service."""
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.ticket import Ticket
from app.services.gmail_service import send_email

logger = logging.getLogger(__name__)


async def generate_protocol(db: AsyncSession) -> str:
    """Generate a unique protocol number like CARBON-2026-000123."""
    year = datetime.now(timezone.utc).year
    prefix = f"CARBON-{year}-"

    result = await db.execute(
        select(func.max(Ticket.protocol)).where(
            Ticket.protocol.like(f"{prefix}%")
        )
    )
    last = result.scalar()

    if last:
        try:
            seq = int(last.replace(prefix, "")) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1

    return f"{prefix}{seq:06d}"


async def assign_protocol(ticket: Ticket, db: AsyncSession):
    """Assign a protocol number to a ticket (does NOT send email)."""
    if ticket.protocol:
        logger.info(f"Ticket #{ticket.number} already has protocol: {ticket.protocol}")
        return
    try:
        protocol = await generate_protocol(db)
        ticket.protocol = protocol
        await db.flush()
        logger.info(f"Protocol {protocol} assigned to ticket #{ticket.number}")
    except Exception as e:
        logger.error(f"Failed to assign protocol to ticket #{ticket.number}: {e}")
        raise


def send_protocol_email(ticket: Ticket) -> bool:
    """Send protocol confirmation email to customer. Returns True if sent."""
    if not ticket.customer or not ticket.customer.email:
        return False
    if not ticket.protocol:
        return False

    try:
        subject = f"Protocolo {ticket.protocol} - {ticket.subject}"
        body = f"""Olá {ticket.customer.name or 'Cliente'},

Recebemos sua solicitação e ela foi registrada com sucesso em nosso sistema.

📋 Número de Protocolo: {ticket.protocol}
📌 Assunto: {ticket.subject}
🔢 Ticket: #{ticket.number}

Guarde este número de protocolo para acompanhamento. Nossa equipe irá analisar sua solicitação e retornar o mais breve possível.

Atenciosamente,
Equipe Carbon Smartwatch
atendimento@carbonsmartwatch.com.br"""

        result = send_email(
            to=ticket.customer.email,
            subject=subject,
            body_text=body,
        )
        if result:
            logger.info(f"Protocol email sent for ticket #{ticket.number} to {ticket.customer.email}")
            return True
        else:
            logger.warning(f"Failed to send protocol email for ticket #{ticket.number}")
            return False
    except Exception as e:
        logger.error(f"Error sending protocol email: {e}")
        return False
