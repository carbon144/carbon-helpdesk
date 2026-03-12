"""Carlos Supervisor Service — monitors human pending actions and sends Slack reminders."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.services.slack_service import send_slack_message

logger = logging.getLogger(__name__)

# Human team members
HUMANS = {
    "victor": {"name": "Victor", "role": "gerente", "slack_id": None, "handles": ["financeiro", "juridico", "estorno_alto"]},
    "tauane": {"name": "Tauane", "role": "supervisora", "slack_id": None, "handles": ["garantia", "reenvio", "operacional"]},
}

SLACK_CHANNELS = {
    "pendencias": "#ia-pendencias",
    "operacao": "#ia-operacao",
    "logistica": "#ia-logistica",
    "garantia": "#ia-garantia",
    "retencao": "#ia-retencao",
}

async def run_supervisor_check(db: AsyncSession) -> dict:
    """Carlos checks for human pending tickets and sends Slack reminders.

    Escalation timeline:
    - 0-6h: message in sector channel
    - 6-24h: message + @mention responsible human
    - >24h: DM to responsible human
    - >48h: DM to Victor (manager) if Tauane didn't act
    """
    result = {"checked": 0, "cobrados": 0, "escalados": 0}

    now = datetime.now(timezone.utc)

    # Find tickets with human_pending_action set
    stmt = select(Ticket).where(
        and_(
            Ticket.human_pending_action.isnot(None),
            Ticket.human_pending_since.isnot(None),
            Ticket.status.notin_(["resolved", "closed", "archived"]),
        )
    )
    tickets_result = await db.execute(stmt)
    pending_tickets = list(tickets_result.scalars().all())

    result["checked"] = len(pending_tickets)

    for ticket in pending_tickets:
        hours_pending = (now - ticket.human_pending_since).total_seconds() / 3600
        cobro_count = ticket.slack_cobro_count or 0

        # Determine channel based on category
        channel = SLACK_CHANNELS.get("pendencias", "#ia-pendencias")
        if ticket.category in ("reenvio", "meu_pedido"):
            channel = SLACK_CHANNELS.get("logistica", "#ia-logistica")
        elif ticket.category == "garantia":
            channel = SLACK_CHANNELS.get("garantia", "#ia-garantia")
        elif ticket.category in ("financeiro", "reclamacao"):
            channel = SLACK_CHANNELS.get("retencao", "#ia-retencao")

        # Determine responsible human
        responsible = "victor"  # default
        if ticket.category in ("garantia", "reenvio"):
            responsible = "tauane"
        human = HUMANS[responsible]

        msg = None

        if hours_pending < 6 and cobro_count == 0:
            # First notice — sector channel
            msg = (
                f":hourglass: *Pendencia humana — Ticket #{ticket.number}*\n"
                f"Acao necessaria: {ticket.human_pending_action}\n"
                f"Categoria: {ticket.category} | Prioridade: {ticket.priority}\n"
                f"Aguardando ha {hours_pending:.0f}h"
            )
        elif hours_pending >= 6 and hours_pending < 24 and cobro_count < 2:
            # Second notice — mention responsible
            mention = f"@{human['name'].lower()}" if not human.get('slack_id') else f"<@{human['slack_id']}>"
            msg = (
                f":warning: *Pendencia {hours_pending:.0f}h — Ticket #{ticket.number}*\n"
                f"Acao: {ticket.human_pending_action}\n"
                f"{mention} — preciso da sua acao neste ticket.\n"
                f"Categoria: {ticket.category} | Prioridade: {ticket.priority}"
            )
        elif hours_pending >= 24 and cobro_count < 4:
            # Urgent — escalate
            msg = (
                f":rotating_light: *URGENTE {hours_pending:.0f}h — Ticket #{ticket.number}*\n"
                f"Acao: {ticket.human_pending_action}\n"
                f"@victor @tauane — este ticket precisa de acao IMEDIATA.\n"
                f"Cliente aguardando ha mais de 24h por acao humana."
            )
            channel = SLACK_CHANNELS["pendencias"]
            result["escalados"] += 1

        if msg:
            sent = await send_slack_message(channel, msg)
            if sent:
                ticket.slack_cobro_count = cobro_count + 1
                ticket.slack_last_cobro_at = now
                result["cobrados"] += 1

    if result["cobrados"]:
        await db.commit()

    return result


async def mark_human_pending(ticket: Ticket, action: str, assigned_to: str = "victor"):
    """Mark a ticket as needing human action."""
    ticket.human_pending_action = action
    ticket.human_pending_since = datetime.now(timezone.utc)
    ticket.human_pending_assigned = assigned_to
    ticket.slack_cobro_count = 0


async def clear_human_pending(ticket: Ticket):
    """Clear human pending when action is taken."""
    ticket.human_pending_action = None
    ticket.human_pending_since = None
    ticket.human_pending_assigned = None
