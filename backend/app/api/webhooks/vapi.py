"""Vapi Voice AI webhook endpoint."""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db, async_session
from app.services.voice_service import TOOL_HANDLERS, save_call_record
from app.services.voice_ws_manager import voice_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks/vapi", tags=["vapi"])


@router.post("")
async def vapi_webhook(request: Request):
    body = await request.json()
    message = body.get("message", {})
    event_type = message.get("type", "")

    logger.info(f"Vapi webhook event: {event_type}")

    # Verify shared secret
    secret = request.headers.get("x-vapi-secret", "")
    if settings.VAPI_SERVER_SECRET and secret != settings.VAPI_SERVER_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret")

    if event_type == "tool-calls":
        return await _handle_tool_calls(message)
    elif event_type == "end-of-call-report":
        return await _handle_end_of_call(message)
    elif event_type == "assistant-request":
        return _dynamic_greeting()
    elif event_type == "transcript":
        call_id = message.get("call", {}).get("id") or message.get("callId", "")
        role = message.get("role", "unknown")
        text = message.get("transcript", "")
        if text and call_id:
            voice_manager.add_transcript(call_id, role, text)
            await voice_manager.broadcast({
                "type": "transcript",
                "call_id": call_id,
                "role": role,
                "text": text,
            })
    elif event_type == "speech-update":
        call_id = message.get("call", {}).get("id") or message.get("callId", "")
        status = message.get("status", "")
        role = message.get("role", "")
        if status == "stopped" and call_id:
            # Speech ended, could track
            pass
    elif event_type == "status-update":
        call_id = message.get("call", {}).get("id") or message.get("callId", "")
        status = message.get("status", "")
        caller_phone = message.get("call", {}).get("customer", {}).get("number")
        logger.info(f"Vapi status-update: status={status}, call_id={call_id}, phone={caller_phone}, keys={list(message.keys())}")
        if status == "in-progress" and call_id:
            voice_manager.start_call(call_id, caller_phone)
            await voice_manager.broadcast({
                "type": "call_started",
                "call": voice_manager.active_calls.get(call_id),
            })
        elif status == "ended" and call_id:
            voice_manager.end_call(call_id)
            await voice_manager.broadcast({
                "type": "call_ended",
                "call_id": call_id,
            })
    elif event_type == "conversation-update":
        call_id = message.get("call", {}).get("id") or ""
        conversation = message.get("conversation", [])
        if call_id and conversation:
            last = conversation[-1] if conversation else {}
            role = last.get("role", "")
            content = last.get("content", "")
            if content:
                voice_manager.add_transcript(call_id, role, content)
                await voice_manager.broadcast({
                    "type": "transcript",
                    "call_id": call_id,
                    "role": role,
                    "text": content,
                })

    return {"ok": True}


async def _handle_tool_calls(message: dict):
    logger.info(f"Vapi tool-calls raw keys: {list(message.keys())}")

    # Support ALL formats Vapi uses
    tool_call_list = message.get("toolCallList", [])
    tool_with_list = message.get("toolWithToolCallList", [])

    # Format 1: toolWithToolCallList (newer Vapi)
    if tool_with_list:
        tool_call_list = []
        for item in tool_with_list:
            tc = item.get("toolCall", {})
            tool_call_list.append({
                "id": tc.get("id", ""),
                "name": item.get("function", {}).get("name", "") or item.get("name", "") or tc.get("function", {}).get("name", ""),
                "arguments": tc.get("function", {}).get("arguments", {}) or tc.get("parameters", {}),
            })

    # Format 2: toolCallList directly
    if not tool_call_list:
        # Maybe it's in message.toolCalls or message.tool_calls
        tool_call_list = message.get("toolCalls", []) or message.get("tool_calls", [])

    logger.info(f"Vapi parsed {len(tool_call_list)} tool calls: {[tc.get('name','?') for tc in tool_call_list]}")

    results = []
    async with async_session() as db:
        for tc in tool_call_list:
            tool_name = tc.get("name", "") or tc.get("function", {}).get("name", "")
            tool_call_id = tc.get("id", "")
            args = tc.get("arguments", {}) or tc.get("function", {}).get("arguments", {})

            handler = TOOL_HANDLERS.get(tool_name)
            if handler:
                try:
                    # create_ticket needs db, others don't
                    import inspect
                    sig = inspect.signature(handler)
                    if "db" in sig.parameters:
                        result = await handler(db, args)
                    else:
                        result = await handler(args)
                except Exception as e:
                    logger.error(f"Voice tool {tool_name} error: {e}")
                    result = "Desculpa, tive um probleminha. Pode repetir?"
            else:
                logger.warning(f"Unknown voice tool: {tool_name}")
                result = "Nao consigo fazer isso agora."

            results.append({"toolCallId": tool_call_id, "result": result})

        await db.commit()

    return {"results": results}


async def _handle_end_of_call(message: dict):
    call_id = message.get("call", {}).get("id") or message.get("callId") or message.get("call_id", "")
    voice_manager.end_call(call_id)
    await voice_manager.broadcast({"type": "call_ended", "call_id": call_id})

    logger.info(f"Vapi end-of-call payload keys: {list(message.keys())}")

    # Extract fields from Vapi's end-of-call-report format
    call_data = {
        "call_id": message.get("call", {}).get("id") or message.get("callId") or message.get("call_id"),
        "caller_phone": (
            message.get("call", {}).get("customer", {}).get("number")
            or (message.get("customer", {}).get("number") if isinstance(message.get("customer"), dict) else None)
        ),
        "duration_seconds": message.get("durationSeconds") or message.get("duration_seconds", 0),
        "recording_url": message.get("recordingUrl") or message.get("recording_url"),
        "transcript": message.get("transcript"),
        "summary": message.get("summary"),
        "ended_reason": message.get("endedReason") or message.get("ended_reason"),
    }

    logger.info(f"Vapi call data parsed: phone={call_data['caller_phone']}, duration={call_data['duration_seconds']}")

    async with async_session() as db:
        voice_call = await save_call_record(db, call_data)
        await db.commit()
        logger.info(f"Saved voice call {voice_call.vapi_call_id}")
    return {"ok": True}


def _dynamic_greeting() -> dict:
    """Return assistant override with time-based greeting (BRT UTC-3)."""
    brt = datetime.now(timezone(timedelta(hours=-3)))
    hour = brt.hour

    if hour < 12:
        saudacao = "Bom dia"
    elif hour < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"

    return {
        "assistant": {
            "firstMessage": f"{saudacao}! Bem-vindo a Carbon, aqui quem fala eh o Carlos. Como posso te ajudar?",
        }
    }
