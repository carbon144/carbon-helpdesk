"""RF-021-024: Tracking service for package tracking via 17track + Correios.
Supports Correios (Brazil), Cainiao/AliExpress, and any carrier via 17track.
"""
from __future__ import annotations
import logging
import re
from datetime import datetime, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Correios tracking code pattern: AA123456789BR
CORREIOS_PATTERN = re.compile(r'^[A-Z]{2}\d{9}[A-Z]{2}$')

# 17track main status mapping
STATUS_MAP = {
    0: "Sem informação",
    10: "Em trânsito",
    20: "Expirado",
    30: "Coleta realizada",
    35: "Sem informação",
    40: "Devolvido",
    50: "Entregue",
    60: "Alerta",
    70: "Falha na entrega",
}

# 17track sub-status mapping (most common)
SUB_STATUS_MAP = {
    0: "",
    1: "Informação recebida",
    2: "Em trânsito",
    3: "Saiu para entrega",
    4: "Falha na entrega",
    5: "Entregue",
    6: "Alerta",
    7: "Devolvido",
    8: "Retido na alfândega",
    9: "Exceção",
    10: "Aguardando retirada",
}

# Tradução automática de status comuns (inglês/espanhol → português)
TRANSLATIONS = {
    # English common
    "delivered": "Entregue",
    "in transit": "Em trânsito",
    "out for delivery": "Saiu para entrega",
    "shipped": "Enviado",
    "picked up": "Coletado",
    "arrived at destination country": "Chegou no país de destino",
    "arrived at destination": "Chegou no destino",
    "departed origin country": "Saiu do país de origem",
    "customs clearance": "Desembaraço aduaneiro",
    "held at customs": "Retido na alfândega",
    "customs": "Alfândega",
    "accepted by carrier": "Aceito pela transportadora",
    "shipment information received": "Informação de envio recebida",
    "package received": "Pacote recebido",
    "returned to sender": "Devolvido ao remetente",
    "delivery attempt": "Tentativa de entrega",
    "delivery failed": "Falha na entrega",
    "exception": "Exceção",
    "expired": "Expirado",
    "available for pickup": "Disponível para retirada",
    "waiting for pickup": "Aguardando retirada",
    "package departed": "Pacote despachado",
    "package arrived": "Pacote chegou",
    "sorting center": "Centro de distribuição",
    "in customs": "Na alfândega",
    "released from customs": "Liberado da alfândega",
    "return to sender": "Devolver ao remetente",
    "no tracking information": "Sem informação de rastreio",
    "not found": "Não encontrado",
    "shipment picked up": "Envio coletado",
    "item dispatched": "Item despachado",
    "item received": "Item recebido",
    "clearance completed": "Desembaraço concluído",
    "clearance processing": "Processando desembaraço",
    "arrived at hub": "Chegou no centro de distribuição",
    "departed from hub": "Saiu do centro de distribuição",
    "departed from origin": "Saiu da origem",
    "arrived at facility": "Chegou na unidade",
    "departed from facility": "Saiu da unidade",
    "handover to airline": "Entregue à companhia aérea",
    "received by airline": "Recebido pela companhia aérea",
    "flight departure": "Partida do voo",
    "flight arrival": "Chegada do voo",
    # Cainiao common
    "the logistics order has been created": "Pedido logístico criado",
    "parcel is out for delivery": "Pacote saiu para entrega",
    "parcel has been delivered": "Pacote entregue",
    "accepted by logistics company": "Aceito pela empresa de logística",
    "hand over to airline": "Entregue à companhia aérea",
    "arrive at destination country": "Chegou ao país de destino",
    "depart from origin country": "Saiu do país de origem",
    # Spanish
    "entregado": "Entregue",
    "en tránsito": "Em trânsito",
    "en camino": "A caminho",
    "enviado": "Enviado",
}


def translate_status(text: str) -> str:
    """Traduz status de rastreio para português."""
    if not text:
        return text

    lower = text.lower().strip()

    # Exact match first
    if lower in TRANSLATIONS:
        return TRANSLATIONS[lower]

    # Partial match - find longest matching key
    best_match = ""
    best_translation = ""
    for en, pt in TRANSLATIONS.items():
        if en in lower and len(en) > len(best_match):
            best_match = en
            best_translation = pt

    if best_translation:
        # Replace the English part with Portuguese
        result = re.sub(re.escape(best_match), best_translation, text, flags=re.IGNORECASE, count=1)
        return result

    return text


def detect_carrier(code: str) -> str:
    """Detect carrier from tracking code format."""
    code = code.strip().upper()
    if CORREIOS_PATTERN.match(code):
        # CNBR codes look like Correios format but are actually Cainiao
        if code.startswith("CNBR"):
            return "cainiao"
        return "correios"
    if code.startswith(("YT", "LP", "LB", "CNAQV", "CNBR", "CN")):
        return "cainiao"
    return "international"


def _get_carrier_code_for_register(code: str) -> int | None:
    """Return 17track carrier code to force carrier detection on register."""
    carrier = detect_carrier(code)
    if carrier == "cainiao":
        return 100003  # Cainiao carrier code in 17track
    if carrier == "correios":
        return 190271  # Correios carrier code
    return None


async def track_17track(code: str) -> dict:
    """Track via 17track API v2.2 — register + gettrackinfo."""
    api_key = getattr(settings, 'TRACK17_API_KEY', '') or ''
    if not api_key:
        return {
            "carrier": detect_carrier(code),
            "code": code,
            "status": "Configure TRACK17_API_KEY no .env",
            "events": [],
            "delivered": False,
        }

    headers = {"17token": api_key, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            # Step 1: Register tracking number (with carrier hint for Cainiao)
            register_payload = {"number": code}
            carrier_hint = _get_carrier_code_for_register(code)
            if carrier_hint:
                register_payload["carrier"] = carrier_hint

            reg_resp = await client.post(
                "https://api.17track.net/track/v2.2/register",
                headers=headers,
                json=[register_payload],
            )
            logger.info(f"17track register {code} (carrier={carrier_hint}): {reg_resp.status_code}")

            # Step 2: Wait for 17track to process (Cainiao needs more time)
            import asyncio
            wait_time = 8 if detect_carrier(code) == "cainiao" else 3
            await asyncio.sleep(wait_time)

            # Step 3: Get tracking info (with carrier hint)
            get_payload = {"number": code}
            if carrier_hint:
                get_payload["carrier"] = carrier_hint

            resp = await client.post(
                "https://api.17track.net/track/v2.2/gettrackinfo",
                headers=headers,
                json=[get_payload],
            )

            if resp.status_code != 200:
                return {
                    "carrier": detect_carrier(code),
                    "code": code,
                    "status": f"Erro API: HTTP {resp.status_code}",
                    "events": [],
                    "delivered": False,
                }

            data = resp.json()
            logger.info(f"17track response for {code}: code={data.get('code')}")

            if data.get("code") != 0:
                return {
                    "carrier": detect_carrier(code),
                    "code": code,
                    "status": f"Erro: {data.get('data', {}).get('errors', 'desconhecido')}",
                    "events": [],
                    "delivered": False,
                }

            # Parse accepted results
            accepted = data.get("data", {}).get("accepted", [])
            if not accepted:
                # Check rejected
                rejected = data.get("data", {}).get("rejected", [])
                if rejected:
                    err_msg = rejected[0].get("error", {}).get("message", "Código não encontrado")
                    # If "not register" or "register first", try re-registering
                    if "register" in err_msg.lower():
                        return {
                            "carrier": detect_carrier(code),
                            "code": code,
                            "status": "Registrado - aguardando processamento do 17track (tente novamente em 5 min)",
                            "main_status": 0,
                            "events": [],
                            "delivered": False,
                        }
                    return {
                        "carrier": detect_carrier(code),
                        "code": code,
                        "status": translate_status(err_msg),
                        "events": [],
                        "delivered": False,
                    }
                return {
                    "carrier": detect_carrier(code),
                    "code": code,
                    "status": "Registrado - aguardando dados",
                    "main_status": 0,
                    "events": [],
                    "delivered": False,
                }

            track_data = accepted[0]
            track_info = track_data.get("track", {})
            carrier_code = track_data.get("carrier", 0)

            # Get status
            main_status = track_info.get("e", 0)  # main status code
            sub_status = track_info.get("f", 0)   # sub-status code
            status_text = STATUS_MAP.get(main_status, "Desconhecido")
            sub_text = SUB_STATUS_MAP.get(sub_status, "")
            if sub_text:
                status_text = f"{status_text} - {sub_text}"

            is_delivered = main_status == 50

            # Parse events from z1 (origin) and z2 (destination)
            events = []
            for z_key in ["z2", "z1"]:  # z2 = destination first
                z_events = track_info.get(z_key, [])
                for ev in z_events:
                    raw_status = ev.get("z", "")
                    events.append({
                        "date": ev.get("a", ""),       # datetime
                        "status": translate_status(raw_status),  # traduzido
                        "status_original": raw_status,  # original
                        "location": ev.get("c", ""),    # location
                    })

            # Sort events by date descending (newest first)
            events.sort(key=lambda x: x.get("date", ""), reverse=True)

            # Detect carrier name
            carrier_name = _get_carrier_name(carrier_code)

            return {
                "carrier": carrier_name,
                "carrier_code": carrier_code,
                "code": code,
                "status": status_text,
                "main_status": main_status,
                "sub_status": sub_status,
                "last_update": events[0]["date"] if events else "",
                "location": events[0].get("location", "") if events else "",
                "events": events[:20],
                "delivered": is_delivered,
                "days_in_transit": track_info.get("g1", None),
            }

    except Exception as e:
        logger.error(f"17track error for {code}: {e}")
        return {
            "carrier": detect_carrier(code),
            "code": code,
            "status": f"Erro: {str(e)[:100]}",
            "events": [],
            "delivered": False,
        }


def _get_carrier_name(carrier_code: int) -> str:
    """Map common 17track carrier codes to names."""
    carrier_names = {
        0: "desconhecido",
        3011: "China Post",
        100003: "Cainiao",
        100048: "YunExpress",
        190271: "Correios",
        100072: "Yanwen",
        100001: "DHL",
        100002: "UPS",
        100004: "FedEx",
        21051: "Correios",
        100030: "4PX",
        100149: "SunYou",
        100188: "J&T Express",
        100173: "Shopee Express",
    }
    return carrier_names.get(carrier_code, f"carrier_{carrier_code}")


async def track_correios(code: str) -> dict:
    """Track via Correios — uses 17track as it covers Correios too."""
    return await track_17track(code)


async def track_package(code: str) -> dict:
    """Main entry point: track any package via 17track."""
    code = code.strip()
    if not code:
        return {"carrier": "unknown", "code": code, "status": "Código vazio", "events": [], "delivered": False}

    # Use 17track for everything (it supports Correios, Cainiao, and 1000+ carriers)
    return await track_17track(code)


async def track_and_update_ticket(db, ticket) -> dict:
    """Track a package and update the ticket with results."""
    if not ticket.tracking_code:
        return {"error": "Sem código de rastreio"}

    result = await track_package(ticket.tracking_code)

    ticket.tracking_status = result.get("status", "")
    ticket.tracking_data = result
    ticket.updated_at = datetime.now(timezone.utc)

    # Auto-update ticket status if delivered
    if result.get("delivered") and ticket.status not in ("resolved", "closed"):
        ticket.status = "resolved"
        ticket.resolved_at = datetime.now(timezone.utc)
        if not ticket.tags:
            ticket.tags = []
        if "ENTREGUE" not in ticket.tags:
            ticket.tags = list(ticket.tags) + ["ENTREGUE"]

    await db.commit()
    return result
