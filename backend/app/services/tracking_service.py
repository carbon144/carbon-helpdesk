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
            wait_time = 5 if detect_carrier(code) == "cainiao" else 2
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


async def track_wonca(code: str) -> dict:
    """Track via Wonca Labs API (Correios + Cainiao). $0.0021/req, 1000 free/month."""
    api_key = getattr(settings, 'WONCA_API_KEY', '') or ''
    if not api_key:
        return {"carrier": detect_carrier(code), "code": code, "status": "", "events": [], "delivered": False}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api-labs.wonca.com.br/wonca.labs.v1.LabsService/Track",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Apikey {api_key}",
                },
                json={"code": code},
            )

            if resp.status_code != 200:
                logger.warning(f"Wonca API error for {code}: HTTP {resp.status_code} {resp.text[:200]}")
                return {"carrier": detect_carrier(code), "code": code, "status": "", "events": [], "delivered": False}

            data = resp.json()

            # Parse the inner JSON string
            import json
            inner = json.loads(data.get("json", "{}"))
            carrier_raw = data.get("carrier", "")

            eventos = inner.get("eventos", [])
            if not eventos:
                return {"carrier": detect_carrier(code), "code": code, "status": "Sem informação", "events": [], "delivered": False}

            # Parse events
            events = []
            for ev in eventos:
                dt_info = ev.get("dtHrCriado", {})
                dt_str = dt_info.get("date", "")[:19] if isinstance(dt_info, dict) else ""
                descricao = ev.get("descricao", "")
                detalhe = ev.get("detalhe", "")
                # Location from unidade
                unidade = ev.get("unidade", {}) or {}
                endereco = unidade.get("endereco", {}) or {}
                cidade = endereco.get("cidade", "") or ""
                uf = endereco.get("uf", "") or ""
                location = f"{cidade}/{uf}" if cidade and uf else cidade or uf or ""
                # Destination
                destino = ev.get("unidadeDestino")
                if destino:
                    dest_end = (destino.get("endereco") or {})
                    dest_cidade = dest_end.get("cidade", "") or ""
                    dest_uf = dest_end.get("uf", "") or ""
                    if dest_cidade:
                        location += f" → {dest_cidade}/{dest_uf}" if dest_uf else f" → {dest_cidade}"

                status_text = descricao
                if detalhe:
                    status_text += f" ({detalhe})"

                events.append({
                    "date": dt_str,
                    "status": descricao,
                    "detail": detalhe,
                    "location": location,
                })

            # Most recent event first (API returns newest first already)
            last = eventos[0]
            last_descricao = last.get("descricao", "")
            is_delivered = last.get("codigo") == "BDE" or "entregue" in last_descricao.lower()

            # Carrier name
            carrier_map = {
                "CARRIER_CORREIOS": "Correios",
                "CARRIER_CAINIAO": "Cainiao",
            }
            carrier_name = carrier_map.get(carrier_raw, carrier_raw or detect_carrier(code))

            # Predicted delivery date
            dt_prevista = inner.get("dtPrevista", "")

            return {
                "carrier": carrier_name,
                "code": code,
                "status": last_descricao,
                "last_update": events[0]["date"] if events else "",
                "location": events[0].get("location", "") if events else "",
                "events": events[:20],
                "delivered": is_delivered,
                "estimated_delivery": dt_prevista,
            }

    except Exception as e:
        logger.error(f"Wonca error for {code}: {e}")
        return {"carrier": detect_carrier(code), "code": code, "status": "", "events": [], "delivered": False}


async def track_correios(code: str) -> dict:
    """Track via Correios — uses Wonca first, then 17track."""
    return await track_wonca(code)


async def track_linketrack(code: str) -> dict:
    """Track via Linketrack API (free, Correios-only)."""
    user = getattr(settings, 'LINKETRACK_USER', '') or ''
    token = getattr(settings, 'LINKETRACK_TOKEN', '') or ''
    if not user or not token:
        return {"carrier": "correios", "code": code, "status": "Configure LINKETRACK_USER/TOKEN no .env", "events": [], "delivered": False}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://api.linketrack.com/track/json?user={user}&token={token}&codigo={code}",
            )
            if resp.status_code != 200:
                return {"carrier": "correios", "code": code, "status": f"Erro API: HTTP {resp.status_code}", "events": [], "delivered": False}

            data = resp.json()
            eventos = data.get("eventos", [])
            if not eventos:
                return {"carrier": "correios", "code": code, "status": "Sem informação", "events": [], "delivered": False}

            events = []
            for ev in eventos:
                events.append({
                    "date": ev.get("data", "") + " " + ev.get("hora", ""),
                    "status": ev.get("status", ""),
                    "location": ev.get("local", ""),
                    "detail": ev.get("subStatus", [None])[0] if ev.get("subStatus") else "",
                })

            last = eventos[0]
            status_text = last.get("status", "Sem informação")
            is_delivered = "entregue" in status_text.lower()

            return {
                "carrier": "correios",
                "code": code,
                "status": status_text,
                "location": last.get("local", ""),
                "last_update": last.get("data", "") + " " + last.get("hora", ""),
                "events": events[:20],
                "delivered": is_delivered,
            }
    except Exception as e:
        logger.error(f"Linketrack error for {code}: {e}")
        return {"carrier": "correios", "code": code, "status": f"Erro: {str(e)[:100]}", "events": [], "delivered": False}


async def track_package(code: str) -> dict:
    """Main entry point: track any package.
    Priority: Wonca (Correios+Cainiao, cheap) → 17track (international fallback)."""
    code = code.strip()
    if not code:
        return {"carrier": "unknown", "code": code, "status": "Código vazio", "events": [], "delivered": False}

    carrier = detect_carrier(code.upper())

    # 1. Wonca Labs — covers Correios + Cainiao ($0.0021/req, 1000 free/month)
    wonca_key = getattr(settings, 'WONCA_API_KEY', '') or ''
    if wonca_key:
        result = await track_wonca(code)
        if result.get("events"):
            return result

    # 2. 17track fallback (international codes or if Wonca had no data)
    api_key = getattr(settings, 'TRACK17_API_KEY', '') or ''
    if api_key:
        return await track_17track(code)

    # No API configured
    return {"carrier": carrier, "code": code, "status": "Nenhuma API de rastreio configurada", "events": [], "delivered": False}


async def track_and_update_ticket(db, ticket) -> dict:
    """Track a package and update the ticket with results."""
    if not ticket.tracking_code:
        return {"error": "Sem código de rastreio"}

    # Handle multiple tracking codes separated by comma
    codes = [c.strip() for c in ticket.tracking_code.split(",") if c.strip()]
    if len(codes) > 1:
        # Track each code and pick the one with most info
        best = None
        for code in codes:
            r = await track_package(code)
            if best is None or r.get("main_status", 0) > best.get("main_status", 0) or r.get("events"):
                best = r
        result = best or await track_package(codes[0])
    else:
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
