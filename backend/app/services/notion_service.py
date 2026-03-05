"""Notion integration: log refunds & cancellations to Notion database."""
from __future__ import annotations
import logging
import httpx
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# Will be set on first call (created automatically if needed)
_database_id: str | None = None


def _headers():
    return {
        "Authorization": f"Bearer {settings.NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


async def _get_or_create_database() -> str | None:
    """Get existing database ID from config or find/create one."""
    global _database_id

    if _database_id:
        return _database_id

    token = getattr(settings, "NOTION_TOKEN", "") or ""
    if not token:
        logger.warning("NOTION_TOKEN not configured")
        return None

    # Check if database ID is configured
    db_id = getattr(settings, "NOTION_DATABASE_ID", "") or ""
    if db_id:
        _database_id = db_id
        return _database_id

    # Search for existing database by title
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{NOTION_API}/search",
                headers=_headers(),
                json={
                    "query": "Reembolsos",
                    "filter": {"property": "object", "value": "database"},
                },
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for r in results:
                    title_parts = r.get("title", [])
                    title = "".join(t.get("plain_text", "") for t in title_parts)
                    if "Reembolsos" in title or "Cancelamentos" in title:
                        _database_id = r["id"]
                        logger.info(f"Found Notion database: {_database_id}")
                        return _database_id

            # Create new database as top-level page
            # First create a page, then a database inside it
            page_resp = await client.post(
                f"{NOTION_API}/pages",
                headers=_headers(),
                json={
                    "parent": {"type": "workspace", "workspace": True},
                    "properties": {
                        "title": [{"type": "text", "text": {"content": "Carbon Expert Hub"}}]
                    },
                },
            )

            if page_resp.status_code not in (200, 201):
                # Try searching for existing Carbon Expert Hub page
                search_resp = await client.post(
                    f"{NOTION_API}/search",
                    headers=_headers(),
                    json={"query": "Carbon Expert Hub", "filter": {"property": "object", "value": "page"}},
                )
                pages = search_resp.json().get("results", [])
                parent_id = pages[0]["id"] if pages else None
                if not parent_id:
                    logger.error("Cannot create Notion page")
                    return None
            else:
                parent_id = page_resp.json()["id"]

            # Create database inside the page
            db_resp = await client.post(
                f"{NOTION_API}/databases",
                headers=_headers(),
                json={
                    "parent": {"type": "page_id", "page_id": parent_id},
                    "title": [{"type": "text", "text": {"content": "Reembolsos & Cancelamentos"}}],
                    "properties": {
                        "Ticket": {"title": {}},
                        "Tipo": {
                            "select": {
                                "options": [
                                    {"name": "Reembolso", "color": "orange"},
                                    {"name": "Cancelamento", "color": "red"},
                                    {"name": "Reembolso Parcial", "color": "yellow"},
                                ]
                            }
                        },
                        "Status": {
                            "select": {
                                "options": [
                                    {"name": "Solicitado", "color": "yellow"},
                                    {"name": "Aprovado", "color": "green"},
                                    {"name": "Processado", "color": "blue"},
                                    {"name": "Recusado", "color": "red"},
                                ]
                            }
                        },
                        "Cliente": {"rich_text": {}},
                        "Email": {"email": {}},
                        "Pedido Shopify": {"rich_text": {}},
                        "Valor": {"number": {"format": "real"}},
                        "Motivo": {"rich_text": {}},
                        "Agente": {"rich_text": {}},
                        "Data": {"date": {}},
                        "Código Rastreio": {"rich_text": {}},
                        "Observações": {"rich_text": {}},
                    },
                },
            )

            if db_resp.status_code in (200, 201):
                _database_id = db_resp.json()["id"]
                logger.info(f"Created Notion database: {_database_id}")
                return _database_id
            else:
                logger.error(f"Failed to create Notion DB: {db_resp.text}")
                return None

    except Exception as e:
        logger.error(f"Notion database setup error: {e}")
        return None


async def log_refund_or_cancel(
    tipo: str,  # "Reembolso", "Cancelamento", "Reembolso Parcial"
    ticket_number: int | None = None,
    customer_name: str = "",
    customer_email: str = "",
    order_id: str = "",
    valor: float | None = None,
    motivo: str = "",
    agente: str = "",
    tracking_code: str = "",
    observacoes: str = "",
) -> dict:
    """Log a refund or cancellation to Notion database."""
    db_id = await _get_or_create_database()
    if not db_id:
        return {"ok": False, "error": "Notion não configurado"}

    # Build properties
    properties = {
        "Ticket": {"title": [{"text": {"content": f"#{ticket_number}" if ticket_number else "N/A"}}]},
        "Tipo": {"select": {"name": tipo}},
        "Status": {"select": {"name": "Processado"}},
        "Cliente": {"rich_text": [{"text": {"content": customer_name[:200]}}]} if customer_name else {"rich_text": []},
        "Email": {"email": customer_email} if customer_email else {"email": None},
        "Pedido Shopify": {"rich_text": [{"text": {"content": str(order_id)[:100]}}]} if order_id else {"rich_text": []},
        "Motivo": {"rich_text": [{"text": {"content": motivo[:500]}}]} if motivo else {"rich_text": []},
        "Agente": {"rich_text": [{"text": {"content": agente[:100]}}]} if agente else {"rich_text": []},
        "Data": {"date": {"start": datetime.now(timezone.utc).strftime("%Y-%m-%d")}},
        "Código Rastreio": {"rich_text": [{"text": {"content": tracking_code[:100]}}]} if tracking_code else {"rich_text": []},
        "Observações": {"rich_text": [{"text": {"content": observacoes[:500]}}]} if observacoes else {"rich_text": []},
    }

    if valor is not None:
        properties["Valor"] = {"number": valor}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{NOTION_API}/pages",
                headers=_headers(),
                json={
                    "parent": {"type": "database_id", "database_id": db_id},
                    "properties": properties,
                },
            )

            if resp.status_code in (200, 201):
                page_id = resp.json()["id"]
                logger.info(f"Logged {tipo} to Notion: {page_id}")
                return {"ok": True, "notion_page_id": page_id}
            else:
                logger.error(f"Notion create page error: {resp.text}")
                return {"ok": False, "error": resp.text[:200]}

    except Exception as e:
        logger.error(f"Notion log error: {e}")
        return {"ok": False, "error": str(e)[:200]}
