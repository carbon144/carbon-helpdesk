"""Shopify integration service — busca pedidos por email do cliente."""
import logging
from datetime import datetime

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _shopify_headers():
    return {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def _format_order_from_shopify(o: dict) -> dict:
    """Quick format a raw Shopify order dict into our standard order shape."""
    fulfillments = o.get("fulfillments", [])
    tracking_code = ""
    delivery_status = "pending"
    carrier = ""

    if fulfillments:
        last_f = fulfillments[0]
        tracking_code = (last_f.get("tracking_numbers") or [""])[0]
        carrier = last_f.get("tracking_company", "")
        shipment_status = last_f.get("shipment_status") or ""
        if shipment_status == "delivered" or o.get("fulfillment_status") == "fulfilled":
            delivery_status = "delivered"
        elif shipment_status in ("in_transit", "out_for_delivery"):
            delivery_status = shipment_status
        elif shipment_status == "confirmed" or last_f.get("status") == "success":
            delivery_status = "shipped"

    shipping_lines = o.get("shipping_lines", [])
    if not carrier and shipping_lines:
        carrier = shipping_lines[0].get("title", "")

    items = [{"title": li.get("title"), "variant_title": li.get("variant_title"),
              "quantity": li.get("quantity"), "price": li.get("price")}
             for li in o.get("line_items", [])]

    return {
        "order_id": o.get("id"),
        "order_number": o.get("name"),
        "email": o.get("email"),
        "financial_status": o.get("financial_status"),
        "total_price": o.get("total_price"),
        "delivery_status": delivery_status,
        "tracking_code": tracking_code,
        "carrier": carrier,
        "items": items,
        "created_at": o.get("created_at"),
    }


def _shopify_base():
    store = settings.SHOPIFY_STORE.rstrip("/")
    if not store:
        return None
    # Ensure it's just the domain
    if not store.startswith("http"):
        store = f"https://{store}"
    return f"{store}/admin/api/2024-01"


async def get_orders_by_email(email: str, limit: int = 10) -> dict:
    """Busca pedidos no Shopify pelo email do cliente."""
    base = _shopify_base()
    if not base or not settings.SHOPIFY_ACCESS_TOKEN:
        return {"configured": False, "orders": [], "error": "Shopify não configurado (SHOPIFY_STORE e SHOPIFY_ACCESS_TOKEN)"}

    try:
        url = f"{base}/orders.json"
        params = {
            "email": email,
            "status": "any",
            "limit": limit,
            "fields": "id,name,email,created_at,updated_at,financial_status,fulfillment_status,"
                       "total_price,currency,line_items,shipping_address,fulfillments,"
                       "shipping_lines,note,tags,cancelled_at,closed_at,confirmed",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_shopify_headers(), params=params)

        if resp.status_code == 401:
            return {"configured": False, "orders": [], "error": "Token Shopify inválido"}
        if resp.status_code == 404:
            return {"configured": False, "orders": [], "error": "Loja Shopify não encontrada"}

        resp.raise_for_status()
        data = resp.json()
        raw_orders = data.get("orders", [])

        orders = []
        for o in raw_orders:
            # Extrair fulfillments/tracking
            fulfillments = []
            for f in o.get("fulfillments", []):
                tracking_numbers = f.get("tracking_numbers", [])
                tracking_urls = f.get("tracking_urls", [])
                tracking_company = f.get("tracking_company", "")
                fulfillments.append({
                    "id": f.get("id"),
                    "status": f.get("status"),  # success, pending, open, failure, error
                    "tracking_company": tracking_company,
                    "tracking_numbers": tracking_numbers,
                    "tracking_urls": tracking_urls,
                    "created_at": f.get("created_at"),
                    "updated_at": f.get("updated_at"),
                    "shipment_status": f.get("shipment_status"),  # confirmed, in_transit, out_for_delivery, delivered, failure
                    "estimated_delivery_at": f.get("estimated_delivery_at"),
                })

            # Itens do pedido
            items = []
            for li in o.get("line_items", []):
                items.append({
                    "title": li.get("title"),
                    "variant_title": li.get("variant_title"),
                    "quantity": li.get("quantity"),
                    "price": li.get("price"),
                    "sku": li.get("sku"),
                })

            # Endereço de envio
            shipping = o.get("shipping_address") or {}
            shipping_info = {
                "name": shipping.get("name", ""),
                "city": shipping.get("city", ""),
                "province": shipping.get("province", ""),
                "zip": shipping.get("zip", ""),
                "country": shipping.get("country", "BR"),
            } if shipping else None

            # Transportadora
            shipping_lines = o.get("shipping_lines", [])
            carrier = shipping_lines[0].get("title", "") if shipping_lines else ""

            # Status de entrega consolidado
            delivery_status = "pending"
            tracking_code = ""
            tracking_url = ""
            estimated_delivery = None
            last_tracking_update = None

            if fulfillments:
                last_f = fulfillments[0]  # Mais recente
                if last_f["tracking_numbers"]:
                    tracking_code = last_f["tracking_numbers"][0]
                if last_f["tracking_urls"]:
                    tracking_url = last_f["tracking_urls"][0]
                estimated_delivery = last_f.get("estimated_delivery_at")
                last_tracking_update = last_f.get("updated_at")

                shipment_status = last_f.get("shipment_status") or ""
                fulfillment_status = last_f.get("status") or ""

                if shipment_status == "delivered" or o.get("fulfillment_status") == "fulfilled":
                    delivery_status = "delivered"
                elif shipment_status in ("in_transit", "out_for_delivery"):
                    delivery_status = shipment_status
                elif shipment_status == "confirmed":
                    delivery_status = "shipped"
                elif fulfillment_status == "success":
                    delivery_status = "shipped"
                elif shipment_status == "failure":
                    delivery_status = "failed"

            orders.append({
                "order_id": o.get("id"),
                "order_number": o.get("name"),  # ex: #1001
                "created_at": o.get("created_at"),
                "updated_at": o.get("updated_at"),
                "financial_status": o.get("financial_status"),  # paid, pending, refunded, etc.
                "fulfillment_status": o.get("fulfillment_status"),  # fulfilled, partial, null
                "total_price": o.get("total_price"),
                "currency": o.get("currency"),
                "items": items,
                "shipping_address": shipping_info,
                "carrier": carrier,
                "tracking_code": tracking_code,
                "tracking_url": tracking_url,
                "delivery_status": delivery_status,
                "estimated_delivery": estimated_delivery,
                "last_tracking_update": last_tracking_update,
                "fulfillments": fulfillments,
                "cancelled_at": o.get("cancelled_at"),
                "note": o.get("note"),
                "tags": o.get("tags", ""),
            })

        return {
            "configured": True,
            "orders": orders,
            "total": len(orders),
            "customer_email": email,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Shopify HTTP error for {email}: {e}")
        return {"configured": True, "orders": [], "error": f"Erro HTTP: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Shopify error for {email}: {e}")
        return {"configured": True, "orders": [], "error": str(e)}


async def get_order_by_number(order_number: str) -> dict:
    """Busca um pedido específico pelo número (ex: #1001 ou 1001)."""
    base = _shopify_base()
    if not base or not settings.SHOPIFY_ACCESS_TOKEN:
        return {"error": "Shopify não configurado"}

    # Remove # se tiver
    number = order_number.strip().lstrip("#")

    try:
        url = f"{base}/orders.json"
        params = {"name": number, "status": "any", "limit": 1}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_shopify_headers(), params=params)

        resp.raise_for_status()
        data = resp.json()
        orders = data.get("orders", [])

        if not orders:
            return {"error": "Pedido não encontrado"}

        # Reusa a lógica do get_orders_by_email para o primeiro resultado
        result = await get_orders_by_email(orders[0].get("email", ""), limit=1)
        if result.get("orders"):
            return result["orders"][0]
        return {"error": "Erro ao processar pedido"}

    except Exception as e:
        logger.error(f"Shopify order lookup error for {order_number}: {e}")
        return {"error": str(e)}


async def get_orders_by_phone(phone: str, limit: int = 5) -> dict:
    """Busca pedidos no Shopify pelo telefone do cliente.
    Shopify aceita busca por phone no endpoint de orders."""
    base = _shopify_base()
    if not base or not settings.SHOPIFY_ACCESS_TOKEN:
        return {"configured": False, "orders": []}

    # Normalize: keep only digits
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return {"configured": True, "orders": []}

    try:
        # Build phone variants to try (Shopify stores phones in various formats)
        phone_variants = [f"+{digits}", digits]
        if digits.startswith("55") and len(digits) >= 12:
            # +55 11 961720761
            phone_variants.append(f"+{digits[:2]} {digits[2:4]} {digits[4:]}")
            # Without country code: 11961720761
            phone_variants.append(digits[2:])
            # +55 (11) 96172-0761
            local = digits[4:]
            if len(local) >= 8:
                phone_variants.append(f"+{digits[:2]} ({digits[2:4]}) {local[:-4]}-{local[-4:]}")

        # Strategy 1: Search customers by phone
        url = f"{base}/customers/search.json"
        for phone_query in phone_variants:
            params = {"query": f"phone:{phone_query}", "limit": 1}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers=_shopify_headers(), params=params)
            if resp.status_code != 200:
                continue
            customers = resp.json().get("customers", [])
            if customers:
                email = customers[0].get("email")
                if email:
                    return await get_orders_by_email(email, limit=limit)

        # Strategy 2: Search orders directly by phone
        orders_url = f"{base}/orders.json"
        for phone_query in phone_variants:
            params = {"phone": phone_query, "limit": limit, "status": "any",
                      "fields": "id,name,order_number,email,phone,financial_status,fulfillment_status,total_price,created_at,fulfillments,line_items,customer"}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(orders_url, headers=_shopify_headers(), params=params)
            if resp.status_code != 200:
                continue
            orders = resp.json().get("orders", [])
            if orders:
                # Found via orders — also try to get email for future lookups
                email = orders[0].get("email") or (orders[0].get("customer") or {}).get("email")
                if email:
                    return await get_orders_by_email(email, limit=limit)
                # No email but we have orders — format them directly
                return {"configured": True, "orders": [_format_order_from_shopify(o) for o in orders]}

        return {"configured": True, "orders": []}
    except Exception as e:
        logger.error(f"Shopify phone lookup error for {phone}: {e}")
        return {"configured": True, "orders": []}


def _safe_float(value) -> float:
    """Convert value to float safely."""
    try:
        return float(value) if value else 0.0
    except (ValueError, TypeError):
        return 0.0


async def get_customer_by_email(email: str) -> dict:
    """Fetch customer profile data from Shopify by email - LTV, total orders, tags, addresses, etc."""
    base = _shopify_base()
    if not base or not settings.SHOPIFY_ACCESS_TOKEN:
        return {"error": "Shopify não configurado"}

    try:
        # Search customers by email
        url = f"{base}/customers/search.json"
        params = {"query": f"email:{email}", "fields": "id,email,first_name,last_name,phone,orders_count,total_spent,currency,tags,note,created_at,updated_at,addresses,default_address,verified_email,state,last_order_id,last_order_name"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=_shopify_headers(), params=params)

        if resp.status_code != 200:
            return {"error": f"Erro HTTP: {resp.status_code}"}

        data = resp.json()
        customers = data.get("customers", [])

        if not customers:
            return {"found": False, "customer": None}

        c = customers[0]
        default_addr = c.get("default_address") or {}

        return {
            "found": True,
            "customer": {
                "shopify_id": c.get("id"),
                "name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                "email": c.get("email", ""),
                "phone": c.get("phone", ""),
                "orders_count": c.get("orders_count", 0),
                "total_spent": _safe_float(c.get("total_spent", 0)),
                "currency": c.get("currency", "BRL"),
                "tags": c.get("tags", ""),
                "note": c.get("note", ""),
                "verified_email": c.get("verified_email", False),
                "state": c.get("state", ""),
                "created_at": c.get("created_at", ""),
                "last_order_name": c.get("last_order_name", ""),
                "default_address": {
                    "address1": default_addr.get("address1", ""),
                    "address2": default_addr.get("address2", ""),
                    "city": default_addr.get("city", ""),
                    "province": default_addr.get("province", ""),
                    "zip": default_addr.get("zip", ""),
                    "country": default_addr.get("country", "BR"),
                    "phone": default_addr.get("phone", ""),
                } if default_addr else None,
                "addresses_count": len(c.get("addresses", [])),
            },
        }

    except Exception as e:
        logger.error(f"Shopify customer lookup error for {email}: {e}")
        return {"error": str(e)}


async def refund_order(order_id: str, amount: float = None, reason: str = "customer") -> dict:
    """Process a refund for a Shopify order. If amount is None, full refund."""
    base = _shopify_base()
    if not base or not settings.SHOPIFY_ACCESS_TOKEN:
        return {"error": "Shopify não configurado"}

    try:
        # First get the order to know the total
        order_url = f"{base}/orders/{order_id}.json"
        async with httpx.AsyncClient(timeout=30) as client:
            order_resp = await client.get(order_url, headers=_shopify_headers())

        if order_resp.status_code != 200:
            return {"error": f"Pedido não encontrado: {order_resp.status_code}"}

        order_data = order_resp.json().get("order", {})

        # Build refund payload
        refund_url = f"{base}/orders/{order_id}/refunds/calculate.json"
        
        # Calculate refund
        calc_payload = {"refund": {"shipping": {"full_refund": True}}}
        
        async with httpx.AsyncClient(timeout=30) as client:
            calc_resp = await client.post(refund_url, headers=_shopify_headers(), json=calc_payload)

        if calc_resp.status_code != 200:
            return {"error": f"Erro ao calcular reembolso: {calc_resp.status_code}"}

        calculated = calc_resp.json().get("refund", {})

        # Now create the actual refund
        refund_create_url = f"{base}/orders/{order_id}/refunds.json"
        refund_payload = {
            "refund": {
                "note": reason or "Reembolso via helpdesk",
                "shipping": {"full_refund": True},
                "refund_line_items": calculated.get("refund_line_items", []),
                "transactions": calculated.get("transactions", []),
            }
        }

        async with httpx.AsyncClient(timeout=30) as client:
            refund_resp = await client.post(refund_create_url, headers=_shopify_headers(), json=refund_payload)

        if refund_resp.status_code in (200, 201):
            return {"success": True, "refund": refund_resp.json().get("refund", {})}
        else:
            error_body = refund_resp.json() if refund_resp.headers.get("content-type", "").startswith("application/json") else {}
            return {"error": f"Erro ao criar reembolso: {refund_resp.status_code}", "details": error_body}

    except Exception as e:
        logger.error(f"Shopify refund error for order {order_id}: {e}")
        return {"error": str(e)}


async def cancel_order(order_id: str, reason: str = "customer", email_customer: bool = True) -> dict:
    """Cancel a Shopify order."""
    base = _shopify_base()
    if not base or not settings.SHOPIFY_ACCESS_TOKEN:
        return {"error": "Shopify não configurado"}

    try:
        url = f"{base}/orders/{order_id}/cancel.json"
        payload = {
            "reason": reason,
            "email": email_customer,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=_shopify_headers(), json=payload)

        if resp.status_code in (200, 201):
            return {"success": True, "order": resp.json().get("order", {})}
        elif resp.status_code == 422:
            return {"error": "Pedido não pode ser cancelado (já enviado ou cancelado)"}
        else:
            return {"error": f"Erro ao cancelar: {resp.status_code}"}

    except Exception as e:
        logger.error(f"Shopify cancel error for order {order_id}: {e}")
        return {"error": str(e)}
