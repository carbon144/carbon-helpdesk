"""E-commerce integration API endpoints (Shopify, Yampi, Appmax)."""
import json
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.core.config import settings
from app.models.user import User
from app.services.shopify_service import (
    get_orders_by_email as shopify_get_orders,
    get_order_by_number as shopify_get_order_by_number,
    get_customer_by_email as shopify_get_customer,
    refund_order as shopify_refund_order,
    cancel_order as shopify_cancel_order,
)
from app.services.yampi_service import (
    get_orders_by_email as yampi_get_orders,
    get_order_details as yampi_get_details,
    get_tracking_info as yampi_get_tracking,
)
from app.services.appmax_service import (
    get_orders_by_email as appmax_get_orders,
    get_sale_details as appmax_get_details,
    get_transaction_status as appmax_get_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ecommerce", tags=["ecommerce"])

# Path to ecommerce config file
CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "ecommerce.json"


def _ensure_config_dir():
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_settings_from_file() -> dict:
    """Load settings from JSON file."""
    _ensure_config_dir()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load ecommerce settings from file: {e}")
    return {}


def _save_settings_to_file(settings_data: dict):
    """Save settings to JSON file."""
    _ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save ecommerce settings to file: {e}")


def _get_settings() -> dict:
    """Get current settings from env vars or file."""
    return {
        "shopify": {
            "store": settings.SHOPIFY_STORE or "",
            "token": settings.SHOPIFY_ACCESS_TOKEN or "",
        },
        "yampi": {
            "token": settings.YAMPI_TOKEN or "",
            "alias": settings.YAMPI_ALIAS or "",
        },
        "appmax": {
            "api_key": settings.APPMAX_API_KEY or "",
        },
    }


def _mask_credentials(settings_data: dict) -> dict:
    """Mask sensitive credentials for display."""
    import copy
    masked = copy.deepcopy(settings_data)

    if "shopify" in masked:
        if masked["shopify"].get("token"):
            t = masked["shopify"]["token"]
            masked["shopify"]["token"] = f"{t[:8]}...{t[-4:]}" if len(t) > 12 else "***"

    if "yampi" in masked:
        if masked["yampi"].get("token"):
            t = masked["yampi"]["token"]
            masked["yampi"]["token"] = f"{t[:4]}...{t[-4:]}" if len(t) > 8 else "***"

    if "appmax" in masked:
        if masked["appmax"].get("api_key"):
            k = masked["appmax"]["api_key"]
            masked["appmax"]["api_key"] = f"{k[:4]}...{k[-4:]}" if len(k) > 8 else "***"

    return masked


async def _merge_ecommerce_orders(email: str, limit: int = 50) -> dict:
    """Fetch and merge orders from Shopify (principal), Yampi (abandonados) and Appmax (pagamentos)."""
    sources_status = {}
    shopify_orders = []
    yampi_orders = []
    appmax_orders = []

    # 1) Shopify — fonte principal de pedidos
    try:
        shopify_result = await shopify_get_orders(email, limit=limit)
        sources_status["shopify"] = {
            "configured": shopify_result.get("configured", False),
            "count": len(shopify_result.get("orders", [])),
            "error": shopify_result.get("error"),
        }
        shopify_orders = shopify_result.get("orders", [])
    except Exception as e:
        logger.error(f"Shopify fetch error: {e}")
        sources_status["shopify"] = {"configured": False, "count": 0, "error": str(e)}

    # 2) Yampi — carrinhos/checkouts abandonados
    try:
        yampi_result = await yampi_get_orders(email, limit=limit)
        sources_status["yampi"] = {
            "configured": yampi_result.get("configured", False),
            "count": len(yampi_result.get("orders", [])),
            "error": yampi_result.get("error"),
        }
        yampi_orders = yampi_result.get("orders", [])
    except Exception as e:
        logger.error(f"Yampi fetch error: {e}")
        sources_status["yampi"] = {"configured": False, "count": 0, "error": str(e)}

    # 3) Appmax — pagamentos, chargebacks
    try:
        appmax_result = await appmax_get_orders(email, limit=limit)
        sources_status["appmax"] = {
            "configured": appmax_result.get("configured", False),
            "count": len(appmax_result.get("orders", [])),
            "error": appmax_result.get("error"),
        }
        appmax_orders = appmax_result.get("orders", [])
    except Exception as e:
        logger.error(f"Appmax fetch error: {e}")
        sources_status["appmax"] = {"configured": False, "count": 0, "error": str(e)}

    return {
        "customer_email": email,
        "shopify_orders": shopify_orders,
        "yampi_orders": yampi_orders,
        "appmax_orders": appmax_orders,
        "sources": sources_status,
    }


@router.get("/orders")
async def get_unified_orders(
    email: str = Query(..., description="Email do cliente"),
    limit: int = Query(50, ge=1, le=100),
    _user: User = Depends(get_current_user),
):
    """
    Busca pedidos em Yampi e Appmax pelo email do cliente.
    Retorna lista unificada de pedidos ordenados por data.
    """
    return await _merge_ecommerce_orders(email, limit=limit)


@router.get("/shopify/orders")
async def get_shopify_orders(
    email: str = Query(..., description="Email do cliente"),
    limit: int = Query(50, ge=1, le=250),
    _user: User = Depends(get_current_user),
):
    """Busca pedidos no Shopify pelo email do cliente."""
    result = await shopify_get_orders(email, limit=limit)
    return {
        "customer_email": email,
        "orders": result.get("orders", []),
        "total": result.get("total", 0),
        "configured": result.get("configured", False),
        "error": result.get("error"),
        "source": "shopify",
    }


@router.get("/shopify/order-by-number")
async def get_shopify_order_by_num(
    number: str = Query(..., description="Número do pedido (ex: #1001)"),
    _user: User = Depends(get_current_user),
):
    """Busca pedido Shopify pelo número."""
    return await shopify_get_order_by_number(number)


@router.get("/yampi/orders")
async def get_yampi_orders(
    email: str = Query(..., description="Email do cliente"),
    limit: int = Query(50, ge=1, le=100),
    _user: User = Depends(get_current_user),
):
    """Busca pedidos apenas no Yampi pelo email do cliente."""
    result = await yampi_get_orders(email, limit=limit)
    
    return {
        "customer_email": email,
        "orders": result.get("orders", []),
        "total": result.get("total", 0),
        "configured": result.get("configured", False),
        "error": result.get("error"),
        "source": "yampi",
    }


@router.get("/appmax/orders")
async def get_appmax_orders(
    email: str = Query(..., description="Email do cliente"),
    limit: int = Query(50, ge=1, le=100),
    _user: User = Depends(get_current_user),
):
    """Busca pedidos/vendas apenas no Appmax pelo email do cliente."""
    result = await appmax_get_orders(email, limit=limit)
    
    return {
        "customer_email": email,
        "orders": result.get("orders", []),
        "total": result.get("total", 0),
        "configured": result.get("configured", False),
        "error": result.get("error"),
        "source": "appmax",
    }


@router.get("/settings")
async def get_ecommerce_settings(
    _user: User = Depends(get_current_user),
):
    """Get current API keys configuration (masked)."""
    current_settings = _get_settings()
    masked = _mask_credentials(current_settings)
    
    return {
        "settings": masked,
        "sources": {
            "shopify": {
                "configured": bool(current_settings["shopify"].get("store") and current_settings["shopify"].get("token")),
            },
            "yampi": {
                "configured": bool(current_settings["yampi"].get("token") and current_settings["yampi"].get("alias")),
            },
            "appmax": {
                "configured": bool(current_settings["appmax"].get("api_key")),
            },
        },
    }


class EcommerceSettingsBody(BaseModel):
    shopify_store: Optional[str] = None
    shopify_access_token: Optional[str] = None
    yampi_token: Optional[str] = None
    yampi_alias: Optional[str] = None
    appmax_api_key: Optional[str] = None


@router.post("/settings")
async def update_ecommerce_settings(
    body: EcommerceSettingsBody,
    _user: User = Depends(get_current_user),
):
    """
    Update API keys for Yampi and Appmax.
    Note: This updates environment variables, but changes persist only if saved to .env
    or passed at container startup.
    """

    # Update settings object (these won't persist after restart unless saved to .env)
    if body.shopify_store is not None:
        settings.SHOPIFY_STORE = body.shopify_store
    if body.shopify_access_token is not None:
        settings.SHOPIFY_ACCESS_TOKEN = body.shopify_access_token
    if body.yampi_token is not None:
        settings.YAMPI_TOKEN = body.yampi_token
    if body.yampi_alias is not None:
        settings.YAMPI_ALIAS = body.yampi_alias
    if body.appmax_api_key is not None:
        settings.APPMAX_API_KEY = body.appmax_api_key
    
    # Also try to save to file for reference
    file_settings = _load_settings_from_file()
    if body.shopify_store is not None:
        file_settings.setdefault("shopify", {})["store"] = body.shopify_store
    if body.shopify_access_token is not None:
        file_settings.setdefault("shopify", {})["token"] = body.shopify_access_token
    if body.yampi_token is not None:
        file_settings.setdefault("yampi", {})["token"] = body.yampi_token
    if body.yampi_alias is not None:
        file_settings.setdefault("yampi", {})["alias"] = body.yampi_alias
    if body.appmax_api_key is not None:
        file_settings.setdefault("appmax", {})["api_key"] = body.appmax_api_key
    
    _save_settings_to_file(file_settings)
    
    # Get updated settings
    current_settings = _get_settings()
    masked = _mask_credentials(current_settings)
    
    return {
        "success": True,
        "message": "Configurações atualizadas",
        "settings": masked,
        "sources": {
            "shopify": {
                "configured": bool(current_settings["shopify"].get("store") and current_settings["shopify"].get("token")),
            },
            "yampi": {
                "configured": bool(current_settings["yampi"].get("token") and current_settings["yampi"].get("alias")),
            },
            "appmax": {
                "configured": bool(current_settings["appmax"].get("api_key")),
            },
        },
    }


@router.get("/shopify/customer")
async def get_shopify_customer(
    email: str = Query(..., description="Email do cliente"),
    _user: User = Depends(get_current_user),
):
    """Busca perfil do cliente no Shopify (LTV, total pedidos, tags, endereço)."""
    result = await shopify_get_customer(email)

    # Classify customer based on data
    customer = result.get("customer")
    if customer:
        orders_count = customer.get("orders_count", 0)
        total_spent = customer.get("total_spent", 0)
        tags = (customer.get("tags", "") or "").lower()

        # VIP: 2+ paid orders or spent > R$500
        is_vip = orders_count >= 2 or total_spent >= 500

        # Bad customer flags
        has_chargeback = "chargeback" in tags or "fraude" in tags or "fraud" in tags
        has_many_returns = "troca" in tags and "recorrente" in tags

        customer["is_vip"] = is_vip
        customer["has_chargeback"] = has_chargeback
        customer["has_many_returns"] = has_many_returns

        # Customer tier
        if has_chargeback:
            customer["tier"] = "problematic"
            customer["tier_label"] = "Problemático"
            customer["tier_color"] = "red"
        elif has_many_returns:
            customer["tier"] = "attention"
            customer["tier_label"] = "Atenção"
            customer["tier_color"] = "orange"
        elif is_vip:
            customer["tier"] = "vip"
            customer["tier_label"] = "VIP"
            customer["tier_color"] = "gold"
        else:
            customer["tier"] = "regular"
            customer["tier_label"] = "Regular"
            customer["tier_color"] = "gray"

    return result


class RefundRequest(BaseModel):
    amount: Optional[float] = None
    reason: str = "customer"
    ticket_number: Optional[int] = None
    customer_name: str = ""
    customer_email: str = ""
    tracking_code: str = ""
    observacoes: str = ""


class CancelRequest(BaseModel):
    reason: str = "customer"
    email_customer: bool = True
    ticket_number: Optional[int] = None
    customer_name: str = ""
    customer_email: str = ""
    tracking_code: str = ""
    observacoes: str = ""


@router.post("/shopify/order/{order_id}/refund")
async def refund_shopify_order(
    order_id: str,
    body: RefundRequest,
    _user: User = Depends(get_current_user),
):
    """Processar reembolso de pedido Shopify e registrar no Notion."""
    result = await shopify_refund_order(order_id, amount=body.amount, reason=body.reason)

    # Log to Notion
    try:
        from app.services.notion_service import log_refund_or_cancel
        tipo = "Reembolso Parcial" if body.amount else "Reembolso"
        await log_refund_or_cancel(
            tipo=tipo,
            ticket_number=body.ticket_number,
            customer_name=body.customer_name,
            customer_email=body.customer_email,
            order_id=order_id,
            valor=body.amount,
            motivo=body.reason,
            agente=_user.name or _user.email,
            tracking_code=body.tracking_code,
            observacoes=body.observacoes,
        )
    except Exception as e:
        logger.warning(f"Notion log failed for refund: {e}")

    return result


@router.post("/shopify/order/{order_id}/cancel")
async def cancel_shopify_order(
    order_id: str,
    body: CancelRequest,
    _user: User = Depends(get_current_user),
):
    """Cancelar pedido Shopify e registrar no Notion."""
    result = await shopify_cancel_order(order_id, reason=body.reason, email_customer=body.email_customer)

    # Log to Notion
    try:
        from app.services.notion_service import log_refund_or_cancel
        await log_refund_or_cancel(
            tipo="Cancelamento",
            ticket_number=body.ticket_number,
            customer_name=body.customer_name,
            customer_email=body.customer_email,
            order_id=order_id,
            motivo=body.reason,
            agente=_user.name or _user.email,
            tracking_code=body.tracking_code,
            observacoes=body.observacoes,
        )
    except Exception as e:
        logger.warning(f"Notion log failed for cancel: {e}")

    return result


@router.get("/yampi/order/{order_id}")
async def get_yampi_order_details(
    order_id: str,
    _user: User = Depends(get_current_user),
):
    """Get detailed information about a specific Yampi order."""
    return await yampi_get_details(order_id)


@router.get("/yampi/order/{order_id}/tracking")
async def get_yampi_order_tracking(
    order_id: str,
    _user: User = Depends(get_current_user),
):
    """Get tracking information for a Yampi order."""
    return await yampi_get_tracking(order_id)


@router.get("/appmax/sale/{sale_id}")
async def get_appmax_sale_details(
    sale_id: str,
    _user: User = Depends(get_current_user),
):
    """Get detailed information about a specific Appmax sale."""
    return await appmax_get_details(sale_id)


@router.get("/appmax/transaction/{transaction_id}/status")
async def get_appmax_transaction_status(
    transaction_id: str,
    _user: User = Depends(get_current_user),
):
    """Get status of a specific Appmax transaction."""
    return await appmax_get_status(transaction_id)
