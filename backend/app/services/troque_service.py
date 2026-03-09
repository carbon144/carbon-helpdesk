"""TroqueCommerce API integration — consulta status de reversas."""

import logging
import httpx

logger = logging.getLogger(__name__)

TROQUE_BASE_URL = "https://www.troquecommerce.com.br/api/public"
TROQUE_TOKEN = "0c95de77-d552-4813-96d4-42447f6ce9b7"

STATUS_MAP = {
    "Em Análise": "Em análise pelo nosso time",
    "Aprovado": "Aprovada! Aguardando envio do produto",
    "Aguardando Envio": "Aguardando você enviar o produto",
    "Enviado": "Produto enviado, aguardando recebimento",
    "Recebido": "Produto recebido, processando troca/reembolso",
    "Finalizado": "Finalizada com sucesso",
    "Cancelado": "Cancelada",
    "Reprovado": "Reprovada",
}


async def search_by_order_number(order_number: str) -> list[dict]:
    """Search TroqueCommerce reversals by Shopify order number."""
    clean = order_number.strip().lstrip("#")
    results = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # Search recent pages (max 5 pages to avoid slow responses)
            for page in range(1, 6):
                resp = await client.get(
                    f"{TROQUE_BASE_URL}/order/list",
                    params={"page": str(page)},
                    headers={"token": TROQUE_TOKEN},
                )
                if resp.status_code != 200:
                    logger.error("TroqueCommerce API error: %s %s", resp.status_code, resp.text[:200])
                    break
                data = resp.json()
                for item in data.get("list", []):
                    if str(item.get("ecommerce_number", "")) == clean:
                        results.append(item)
                # If found or no more pages, stop
                if results or page >= data.get("total_pages", 1):
                    break
    except Exception as e:
        logger.error("TroqueCommerce search error: %s", e)
    return results


async def search_by_phone(phone: str) -> list[dict]:
    """Search TroqueCommerce reversals by customer phone number."""
    # Normalize: keep only digits, last 11
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) > 11:
        digits = digits[-11:]
    results = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for page in range(1, 4):
                resp = await client.get(
                    f"{TROQUE_BASE_URL}/order/list",
                    params={"page": str(page)},
                    headers={"token": TROQUE_TOKEN},
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                for item in data.get("list", []):
                    client_phone = "".join(c for c in (item.get("client", {}).get("phone", "")) if c.isdigit())
                    if len(client_phone) > 11:
                        client_phone = client_phone[-11:]
                    if client_phone and client_phone == digits:
                        results.append(item)
                if results or page >= data.get("total_pages", 1):
                    break
    except Exception as e:
        logger.error("TroqueCommerce phone search error: %s", e)
    return results


def format_status_message(reversals: list[dict]) -> str:
    """Format reversal data into a WhatsApp-friendly message."""
    if not reversals:
        return (
            "Não encontrei nenhuma solicitação no Troque pra esse pedido.\n\n"
            "Se você ainda não abriu, acesse:\n"
            "👉 *carbonsmartwatch.troque.app.br*"
        )

    msgs = []
    for r in reversals[:3]:  # Max 3 results
        status_raw = r.get("status", "Desconhecido")
        status_friendly = STATUS_MAP.get(status_raw, status_raw)
        tracking = r.get("tracking", {}) or {}
        tracking_code = tracking.get("courier_tracking_code")
        tracking_status = tracking.get("status")

        msg = (
            f"📋 *Solicitação — Pedido #{r.get('ecommerce_number', 'N/A')}*\n"
            f"Tipo: {r.get('reverse_type', 'N/A')}\n"
            f"Status: *{status_friendly}*\n"
            f"Aberta em: {r.get('created_at', '')[:10]}"
        )

        if tracking_code:
            msg += f"\nRastreio reversa: {tracking_code}"
        if tracking_status:
            msg += f"\nStatus envio: {tracking_status}"

        msgs.append(msg)

    return "\n\n".join(msgs)
