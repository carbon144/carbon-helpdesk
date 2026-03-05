"""Appmax payment gateway API integration service."""
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


def _get_appmax_credentials() -> Optional[str]:
    """Get Appmax API credentials from settings or environment."""
    api_key = settings.APPMAX_API_KEY or ""
    
    if not api_key:
        logger.warning("Appmax API key not configured (APPMAX_API_KEY)")
        return None
    
    return api_key


def _appmax_base_url() -> str:
    """Get Appmax base URL."""
    return "https://admin.appmax.com.br/api/v3/"


def _appmax_params(api_key: str) -> dict:
    """Get Appmax API query parameters."""
    return {
        "access-token": api_key,
    }


async def get_orders_by_email(email: str, limit: int = 50) -> dict:
    """Fetch sales/transactions from Appmax by customer email."""
    api_key = _get_appmax_credentials()
    
    if not api_key:
        return {
            "configured": False,
            "orders": [],
            "error": "Appmax não configurado (APPMAX_API_KEY)",
        }

    try:
        base_url = _appmax_base_url()
        url = f"{base_url}sale"
        params = _appmax_params(api_key)
        params["customer_email"] = email
        params["limit"] = limit

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)

        if resp.status_code == 401:
            return {
                "configured": False,
                "orders": [],
                "error": "Chave API Appmax inválida",
            }

        if resp.status_code == 403:
            return {
                "configured": False,
                "orders": [],
                "error": "Acesso negado à API Appmax",
            }

        if resp.status_code == 404:
            return {
                "configured": True,
                "orders": [],
                "total": 0,
                "customer_email": email,
                "source": "appmax",
            }

        resp.raise_for_status()
        data = resp.json()
        
        # Handle different possible response formats
        if isinstance(data, dict):
            raw_sales = data.get("data", data.get("sales", []))
        else:
            raw_sales = data if isinstance(data, list) else []

        orders = []
        for sale_data in raw_sales:
            order = _parse_appmax_sale(sale_data)
            orders.append(order)

        return {
            "configured": True,
            "orders": orders,
            "total": len(orders),
            "customer_email": email,
            "source": "appmax",
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Appmax HTTP error for {email}: {e}")
        return {
            "configured": True,
            "orders": [],
            "error": f"Erro HTTP: {e.response.status_code}",
        }
    except Exception as e:
        logger.error(f"Appmax error for {email}: {e}")
        return {
            "configured": True,
            "orders": [],
            "error": str(e),
        }


def _parse_appmax_sale(sale_data: dict) -> dict:
    """Parse Appmax sale into unified format."""
    
    # Extract tracking codes
    tracking_codes = []
    tracking_code = sale_data.get("tracking_code")
    if tracking_code:
        tracking_codes.append({
            "code": tracking_code,
            "status": sale_data.get("tracking_status", "pendente"),
            "url": sale_data.get("tracking_url", None),
        })
    
    # Extract items - Appmax may have different structure
    items = []
    if "items" in sale_data:
        for item in sale_data.get("items", []):
            items.append({
                "name": item.get("name") or item.get("product_name", ""),
                "quantity": item.get("quantity", 1),
                "price": _safe_float(item.get("price", 0)),
            })
    
    # Normalize status
    raw_status = sale_data.get("status", "pendente")
    status_normalized = _normalize_appmax_status(str(raw_status).lower())
    status_label = _get_status_label(status_normalized)
    
    return {
        "source": "appmax",
        "order_number": str(sale_data.get("order_id") or sale_data.get("id", "")),
        "status": status_normalized,
        "status_label": status_label,
        "total": _safe_float(sale_data.get("total", 0)),
        "payment_method": sale_data.get("payment_method") or None,
        "created_at": sale_data.get("created_at", ""),
        "tracking_codes": tracking_codes,
        "items": items,
        "raw": sale_data,
    }


def _normalize_appmax_status(status: str) -> str:
    """Normalize Appmax status to standard format."""
    status = status.lower().strip()
    
    # Map Appmax statuses to standard ones
    status_map = {
        "approved": "pago",
        "paid": "pago",
        "pago": "pago",
        "pending": "pendente",
        "pendente": "pendente",
        "declined": "recusado",
        "recusado": "recusado",
        "canceled": "cancelado",
        "cancelado": "cancelado",
        "refunded": "reembolsado",
        "reembolsado": "reembolsado",
        "shipped": "enviado",
        "enviado": "enviado",
        "delivered": "entregue",
        "entregue": "entregue",
        "abandoned": "abandonado",
        "abandonado": "abandonado",
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


async def get_sale_details(sale_id: str) -> dict:
    """Fetch detailed information about a specific Appmax sale."""
    api_key = _get_appmax_credentials()

    if not api_key:
        return {"error": "Appmax não configurado"}

    try:
        base_url = _appmax_base_url()
        url = f"{base_url}sale/{sale_id}"
        params = _appmax_params(api_key)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)

        if resp.status_code == 404:
            return {"error": "Venda não encontrada"}

        resp.raise_for_status()
        data = resp.json()
        
        # Handle response format
        sale = data.get("data", data) if isinstance(data, dict) else data

        return {
            "sale": _parse_appmax_sale(sale),
            "raw": sale,
        }

    except Exception as e:
        logger.error(f"Appmax sale details error for {sale_id}: {e}")
        return {"error": str(e)}


async def get_transaction_status(transaction_id: str) -> dict:
    """Fetch transaction status from Appmax."""
    api_key = _get_appmax_credentials()

    if not api_key:
        return {"error": "Appmax não configurado"}

    try:
        base_url = _appmax_base_url()
        url = f"{base_url}transaction/{transaction_id}"
        params = _appmax_params(api_key)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)

        if resp.status_code == 404:
            return {"error": "Transação não encontrada"}

        resp.raise_for_status()
        data = resp.json()

        transaction = data.get("data", data) if isinstance(data, dict) else data

        return {
            "transaction_id": transaction_id,
            "status": transaction.get("status", "pendente"),
            "status_label": _get_status_label(_normalize_appmax_status(transaction.get("status", "pendente"))),
            "amount": transaction.get("amount", 0),
            "authorization_code": transaction.get("authorization_code", ""),
            "created_at": transaction.get("created_at", ""),
            "updated_at": transaction.get("updated_at", ""),
            "raw": transaction,
        }

    except Exception as e:
        logger.error(f"Appmax transaction status error for {transaction_id}: {e}")
        return {"error": str(e)}
