"""Shopify API endpoints — consulta pedidos por email do cliente."""
from fastapi import APIRouter, Depends, Query

from app.api.auth import get_current_user
from app.models.user import User
from app.services.shopify_service import get_orders_by_email, get_order_by_number

router = APIRouter(prefix="/shopify", tags=["shopify"])


@router.get("/orders")
async def shopify_orders(
    email: str = Query(..., description="Email do cliente"),
    limit: int = Query(10, ge=1, le=50),
    _user: User = Depends(get_current_user),
):
    """Busca pedidos Shopify pelo email do cliente."""
    return await get_orders_by_email(email, limit=limit)


@router.get("/order/{order_number}")
async def shopify_order(
    order_number: str,
    _user: User = Depends(get_current_user),
):
    """Busca pedido Shopify pelo número."""
    return await get_order_by_number(order_number)
