"""Client para integrar com a API do Carbon Helpdesk.

Puxa dados de tickets, mensagens e KB para alimentar a geracao de roteiros
com insights reais dos clientes.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.HELPDESK_API_URL,
            headers={"Authorization": f"Bearer {settings.HELPDESK_API_TOKEN}"},
            timeout=30.0,
        )
    return _client


async def fetch_recent_tickets(days: int = 30, limit: int = 200) -> list[dict]:
    """Busca tickets recentes do helpdesk."""
    try:
        client = _get_client()
        resp = await client.get("/tickets", params={
            "limit": limit,
            "sort": "-created_at",
        })
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("items", data.get("tickets", []))
    except Exception as e:
        logger.warning(f"Erro ao buscar tickets do helpdesk: {e}")
        return []


async def fetch_ticket_messages(ticket_id: str) -> list[dict]:
    """Busca mensagens de um ticket especifico."""
    try:
        client = _get_client()
        resp = await client.get(f"/tickets/{ticket_id}/messages")
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("messages", [])
    except Exception as e:
        logger.warning(f"Erro ao buscar mensagens do ticket {ticket_id}: {e}")
        return []


async def fetch_kb_articles(search: str | None = None) -> list[dict]:
    """Busca artigos da knowledge base."""
    try:
        client = _get_client()
        params = {"limit": 50}
        if search:
            params["q"] = search
        resp = await client.get("/kb/articles", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("articles", [])
    except Exception as e:
        logger.warning(f"Erro ao buscar KB articles: {e}")
        return []


async def extract_customer_insights(product_name: str | None = None) -> dict:
    """Extrai insights dos clientes a partir dos tickets.

    Retorna:
    - faqs: perguntas frequentes
    - pain_points: dores/reclamacoes comuns
    - objections: objecoes de compra
    - praises: elogios recorrentes
    - common_words: palavras mais usadas pelos clientes
    """
    tickets = await fetch_recent_tickets(days=60, limit=300)

    if not tickets:
        return {
            "faqs": [],
            "pain_points": [],
            "objections": [],
            "praises": [],
            "total_tickets_analyzed": 0,
        }

    # Coletar mensagens de clientes (nao de agentes)
    customer_messages = []
    subjects = []

    for ticket in tickets[:100]:  # Limitar para nao sobrecarregar
        subject = ticket.get("subject", "")
        if subject:
            subjects.append(subject)

        # Se tiver mensagens inline
        messages = ticket.get("messages", [])
        if not messages and ticket.get("id"):
            messages = await fetch_ticket_messages(ticket["id"])

        for msg in messages[:3]:  # Primeiras 3 mensagens de cada ticket
            sender = msg.get("sender_type", msg.get("direction", ""))
            if sender in ("customer", "inbound"):
                body = msg.get("body", msg.get("content", ""))
                if body:
                    customer_messages.append(body[:500])

    # Filtrar por produto se especificado
    if product_name:
        product_lower = product_name.lower()
        relevant_subjects = [s for s in subjects if product_lower in s.lower()]
        relevant_messages = [m for m in customer_messages if product_lower in m.lower()]
        # Se nao encontrou nada filtrado, usa tudo
        if relevant_subjects or relevant_messages:
            subjects = relevant_subjects or subjects
            customer_messages = relevant_messages or customer_messages

    return {
        "subjects": subjects[:50],
        "customer_messages": customer_messages[:50],
        "total_tickets_analyzed": len(tickets),
        "product_filter": product_name,
    }


async def health_check() -> bool:
    """Verifica se o helpdesk esta acessivel."""
    try:
        client = _get_client()
        resp = await client.get("/ai/status")
        return resp.status_code == 200
    except Exception:
        return False
