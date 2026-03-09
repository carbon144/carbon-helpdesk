"""Voice Calls API — list, filter, and match calls to customers."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, decode_token
from app.models.voice_call import VoiceCall
from app.models.customer import Customer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice-calls", tags=["voice-calls"])


def _normalize_phone(phone: str) -> str:
    """Strip non-digits for phone matching."""
    return "".join(c for c in phone if c.isdigit()) if phone else ""


@router.get("")
async def list_voice_calls(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all voice calls with pagination, optional search, and customer matching."""

    # Base query
    query = select(VoiceCall).order_by(VoiceCall.created_at.desc())

    # Search by phone or summary
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                VoiceCall.caller_phone.ilike(search_term),
                VoiceCall.summary.ilike(search_term),
                VoiceCall.transcript.ilike(search_term),
            )
        )

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    pages = max(1, (total + per_page - 1) // per_page)

    # Paginate
    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    calls = result.scalars().all()

    # Batch match caller phones to customers
    phones = [c.caller_phone for c in calls if c.caller_phone]
    customer_map = {}
    if phones:
        # Normalize phones for matching
        normalized = {_normalize_phone(p): p for p in phones}
        # Try matching by phone field in customers
        cust_result = await db.execute(select(Customer))
        all_customers = cust_result.scalars().all()
        for cust in all_customers:
            cust_phone = _normalize_phone(cust.phone or "")
            if cust_phone and len(cust_phone) >= 8:
                # Match last 8+ digits
                for norm_p, orig_p in normalized.items():
                    if norm_p.endswith(cust_phone[-8:]) or cust_phone.endswith(norm_p[-8:]):
                        customer_map[orig_p] = {
                            "id": str(cust.id),
                            "name": cust.name,
                            "email": cust.email,
                        }

    items = []
    for c in calls:
        item = {
            "id": str(c.id),
            "vapi_call_id": c.vapi_call_id,
            "caller_phone": c.caller_phone,
            "duration_seconds": c.duration_seconds,
            "recording_url": c.recording_url,
            "transcript": c.transcript,
            "summary": c.summary,
            "ended_reason": c.ended_reason,
            "ticket_id": str(c.ticket_id) if c.ticket_id else None,
            "conversation_id": str(c.conversation_id) if c.conversation_id else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "customer": customer_map.get(c.caller_phone),
        }
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "per_page": per_page,
    }


@router.get("/active")
async def get_active_calls(user=Depends(get_current_user)):
    """Get currently active voice calls."""
    from app.services.voice_ws_manager import voice_manager
    return {"calls": list(voice_manager.active_calls.values())}


@router.get("/{call_id}")
async def get_voice_call(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get a single voice call by ID."""
    result = await db.execute(select(VoiceCall).where(VoiceCall.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Voice call not found")

    # Match customer
    customer = None
    if call.caller_phone:
        norm = _normalize_phone(call.caller_phone)
        if len(norm) >= 8:
            cust_result = await db.execute(select(Customer))
            for cust in cust_result.scalars().all():
                cust_phone = _normalize_phone(cust.phone or "")
                if cust_phone and len(cust_phone) >= 8:
                    if norm.endswith(cust_phone[-8:]) or cust_phone.endswith(norm[-8:]):
                        customer = {"id": str(cust.id), "name": cust.name, "email": cust.email}
                        break

    return {
        "id": str(call.id),
        "vapi_call_id": call.vapi_call_id,
        "caller_phone": call.caller_phone,
        "duration_seconds": call.duration_seconds,
        "recording_url": call.recording_url,
        "transcript": call.transcript,
        "summary": call.summary,
        "ended_reason": call.ended_reason,
        "ticket_id": str(call.ticket_id) if call.ticket_id else None,
        "conversation_id": str(call.conversation_id) if call.conversation_id else None,
        "created_at": call.created_at.isoformat() if call.created_at else None,
        "customer": customer,
    }


@router.websocket("/ws")
async def voice_calls_ws(ws: WebSocket, token: str = Query(None)):
    """WebSocket for live voice call monitoring."""
    from app.services.voice_ws_manager import voice_manager

    if not token:
        await ws.close(code=1008)
        return

    try:
        payload = decode_token(token)
        agent_id = payload.get("sub", "unknown")
    except Exception:
        await ws.close(code=1008)
        return

    await voice_manager.connect_agent(agent_id, ws)
    try:
        while True:
            await ws.receive_text()  # Keep alive
    except WebSocketDisconnect:
        await voice_manager.disconnect_agent(agent_id)
