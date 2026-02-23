"""Yampi e-commerce API integration service."""
import logging
from typing import Optional
from datetime import datetime

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _safe_float(value, default=0.0):
    """Safely convert a value to float."""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _get_yampi_credentials() -> tuple[Optional[str], Optional[str]]:
    """Get Yampi API credentials from settings or environment."""
    token = settings.YAMPI_TOKEN or ""
    alias = settings.YAMPI_ALIAS or ""
    
    if not token or not alias:
        logger.warning("Yampi credentials not configured (YAMPI_TOKEN and YAMPI_ALIAS)")
        return None, None
    
    return token, alias


def _yampi_base_url(alias: str) -> str:
    """Get Yampi base URL."""
    return f"https://api.dooki.com.br/v2/{alias}/"


def _yampi_headers(token: str) -> dict:
    """Get Yampi API headers."""
    return {
        "User-Token": token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def get_orders_by_email(email: str, limit: int = 50) -> dict:
    """Fetch orders from Yampi by customer email."""
    token, alias = _get_yampi_credentials()
    
    if not token or not alias:
        return {
            "configured": False,
            "orders": [],
            "error": "Yampi não configurado (YAMPI_TOKEN e YAMPI_ALIAS)",
        }

    try:
        base_url = _yampi_base_url(alias)
        url = f"{base_url}catalog/orders"
        params = {
            "search[customer_email]": email,
            "limit": limit,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                url,
                headers=_yampi_headers(token),
                params=params,
            )

        if resp.status_code == 401:
            return {
                "configured": False,
                "orders": [],
                "error": "Token Yampi inválido",
            }

        if resp.status_code == 404:
            return {
                "configured": False,
                "orders": [],
                "error": "Alias Yampi não encontrado",
            }

        resp.raise_for_status()
        data = resp.json()
        raw_orders = data.get("data", [])

        orders = []
        for order_data in raw_orders:
            order = _parse_yampi_order(order_data)
            orders.append(order)

        return {
            "configured": True,
            "orders": orders,
            "total": len(orders),
            "customer_email": email,
            "source": "yampi",
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Yampi HTTP error for {email}: {e}")
        return {
            "configured": True,
            "orders": [],
            "error": f"Erro HTTP: {e.response.status_code}",
        }
    except Exception as e:
        logger.error(f"Yampi error for {email}: {e}")
        return {
            "configured": True,
            "orders": [],
            "error": str(e),
        }


def _parse_yampi_order(order_data: dict) -> dict:
    """Parse Yampi order into unified format."""
    
    # Extract tracking codes from shipment
    tracking_codes = []
    shipment = order_data.get("shipment", {})
    if shipment:
        if isinstance(shipment, dict):
            tracking_code = shipment.get("tracking_code")
            if tracking_code:
                tracking_codes.append({
                    "code": tracking_code,
                    "status": shipment.get("status", "pendente"),
                    "url": shipment.get("tracking_url", None),
                })
        elif isinstance(shipment, list):
            for ship in shipment:
                tracking_code = ship.get("tracking_code")
                if tracking_code:
                    tracking_codes.append({
                        "code": tracking_code,
                        "status": ship.get("status", "pendente"),
                        "url": ship.get("tracking_url", None),
                    })
    
    # Extract items
    items = []
    for item in order_data.get("items", []):
        items.append({
            "name": item.get("product_name", ""),
            "quantity": item.get("quantity", 1),
            "price": _safe_float(item.get("price", 0)),
        })
    
    # Normalize status
    raw_status = order_data.get("status", {})
    if isinstance(raw_status, dict):
        status_name = raw_status.get("name", "pendente").lower()
    else:
        status_name = str(raw_status).lower()
    
    status_normalized = _normalize_yampi_status(status_name)
    status_label = _get_status_label(status_normalized)
    
    return {
        "source": "yampi",
        "order_number": str(order_data.get("number", order_data.get("id", ""))),
        "status": status_normalized,
        "status_label": status_label,
        "total": _safe_float(order_data.get("value_total", 0)),
        "payment_method": order_data.get("payment_method") or None,
        "created_at": order_data.get("created_at", ""),
        "tracking_codes": tracking_codes,
        "items": items,
        "raw": order_data,
    }


def _normalize_yampi_status(status: str) -> str:
    """Normalize Yampi status to standard format."""
    status = status.lower().strip()
    
    # Map Yampi statuses to standard ones
    status_map = {
        "pago": "pago",
        "nao_pago": "nao_pago",
        "pendente": "pendente",
        "cancelado": "cancelado",
        "recusado": "recusado",
        "abandonado": "abandonado",
        "reembolsado": "reembolsado",
        "enviado": "enviado",
        "entregue": "entregue",
        "processando": "processando",
    }
    
    return status_map.get(status, status)


def _get_status_label(status: str) -> str:
    """Get human-readable status label in Portuguese."""
    labels = {
        "pago": "Pago",
        "nao_pago": "Não Pago",
        "pendente": "Pendente",
        "cancelado": "Cancelado",
        "recusado": "Recusado",
        "abandonado": "Abandonado",
        "reembolsado": "Reembolsado",
        "enviado": "Enviado",
        "entregue": "Entregue",
        "processando": "Processando",
    }
    return labels.get(status, status.capitalize())


async def get_order_details(order_id: str) -> dict:
    """Fetch detailed information about a specific Yampi order."""
    token, alias = _get_yampi_credentials()
    
    if not token or not alias:
        return {"error": "Yampi não configurado"}

    try:
        base_url = _yampi_base_url(alias)
        url = f"{base_url}catalog/orders/{order_id}"

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                url,
                headers=_yampi_headers(token),
            )

        if resp.status_code == 404:
            return {"error": "Pedido não encontrado"}

        resp.raise_for_status()
        data = resp.json()
        order = data.get("data", {})

        return {
            "order": _parse_yampi_order(order),
            "raw": order,
        }

    except Exception as e:
        logger.error(f"Yampi order details error for {order_id}: {e}")
        return {"error": str(e)}


async def get_tracking_info(order_id: str) -> dict:
    """Fetch tracking information for a Yampi order."""
    token, alias = _get_yampi_credentials()

    if not token or not alias:
        return {"error": "Yampi não configurado"}

    try:
        base_url = _yampi_base_url(alias)
        url = f"{base_url}catalog/orders/{order_id}/tracking"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                url,
                headers=_yampi_headers(token),
            )

        if resp.status_code == 404:
            return {"error": "Rastreamento não encontrado"}

        resp.raise_for_status()
        data = resp.json()

        tracking_list = []
        for tracking in data.get("data", []):
            tracking_list.append({
                "code": tracking.get("tracking_code", ""),
                "status": tracking.get("status", "pendente"),
                "url": tracking.get("tracking_url", ""),
                "carrier": tracking.get("carrier", ""),
                "estimated_delivery": tracking.get("estimated_delivery", ""),
                "last_update": tracking.get("last_update", ""),
            })

        return {
            "order_id": order_id,
            "tracking_codes": tracking_list,
        }

    except Exception as e:
        logger.error(f"Yampi tracking error for {order_id}: {e}")
        return {"error": str(e)}
