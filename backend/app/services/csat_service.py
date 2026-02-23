"""CSAT satisfaction survey email service."""
import logging
import hashlib
import hmac

from app.core.config import settings
from app.models.ticket import Ticket
from app.services.gmail_service import send_email

logger = logging.getLogger(__name__)

CSAT_SECRET = settings.JWT_SECRET  # reuse for HMAC token


def generate_csat_token(ticket_id: str) -> str:
    """Generate a secure HMAC token for CSAT rating link."""
    return hmac.new(
        CSAT_SECRET.encode(), ticket_id.encode(), hashlib.sha256
    ).hexdigest()[:32]


def verify_csat_token(ticket_id: str, token: str) -> bool:
    """Verify the CSAT token is valid."""
    expected = generate_csat_token(ticket_id)
    return hmac.compare_digest(expected, token)


def send_csat_email(ticket: Ticket, base_url: str | None = None) -> bool:
    """Send a personalized CSAT satisfaction email to the customer."""
    if not ticket.customer or not ticket.customer.email:
        return False

    customer_name = ticket.customer.name or "Cliente"
    first_name = customer_name.split()[0] if customer_name else "Cliente"

    # Build CSAT rating URL
    token = generate_csat_token(ticket.id)
    if not base_url:
        base_url = "https://helpdesk.carbonsmartwatch.com.br"
    csat_url = f"{base_url}/api/csat/{ticket.id}?token={token}"

    # Build rating links (1-5 stars)
    rating_links = ""
    star_emojis = ["😞", "😕", "😐", "😊", "🤩"]
    star_labels = ["Péssimo", "Ruim", "Regular", "Bom", "Excelente"]
    for score in range(1, 6):
        link = f"{csat_url}&score={score}"
        rating_links += f"  {star_emojis[score-1]} {star_labels[score-1]}: {link}\n"

    # Personalized subject
    subject = f"Como foi seu atendimento? - Ticket #{ticket.number}"

    # Build personalized body
    category_labels = {
        "garantia": "garantia", "troca": "troca", "mau_uso": "mau uso",
        "carregador": "carregador", "duvida": "dúvida", "reclamacao": "reclamação",
        "juridico": "questão jurídica", "suporte_tecnico": "suporte técnico",
        "financeiro": "questão financeira", "chargeback": "chargeback",
        "reclame_aqui": "Reclame Aqui", "procon": "PROCON",
        "defeito_garantia": "defeito em garantia", "reenvio": "reenvio",
        "rastreamento": "rastreamento", "elogio": "elogio", "sugestao": "sugestão",
    }
    problem_desc = category_labels.get(ticket.category, ticket.category or "sua solicitação")

    body = f"""Olá {first_name},

Seu atendimento sobre {problem_desc} (Ticket #{ticket.number}) foi finalizado.

Queremos saber: como foi sua experiência com nosso suporte?

Clique na nota que melhor representa seu atendimento:

{rating_links}
Sua avaliação nos ajuda a melhorar cada vez mais o atendimento da Carbon Smartwatch.

{f'Resumo do atendimento: {ticket.ai_summary}' if ticket.ai_summary else ''}

Protocolo: {ticket.protocol or 'N/A'}

Obrigado pela confiança!
Equipe Carbon Smartwatch
atendimento@carbonsmartwatch.com.br"""

    try:
        result = send_email(
            to=ticket.customer.email,
            subject=subject,
            body_text=body,
        )
        if result:
            logger.info(f"CSAT email sent for ticket #{ticket.number} to {ticket.customer.email}")
            return True
        else:
            logger.warning(f"Failed to send CSAT email for ticket #{ticket.number}")
            return False
    except Exception as e:
        logger.error(f"Error sending CSAT email: {e}")
        return False
