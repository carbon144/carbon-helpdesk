"""Vapi Voice AI webhook endpoint."""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db, async_session
from app.services.voice_service import TOOL_HANDLERS, save_call_record

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
        return {}

    return {"ok": True}


async def _handle_tool_calls(message: dict):
    # Support both formats Vapi uses
    tool_call_list = message.get("toolCallList", [])
    tool_with_list = message.get("toolWithToolCallList", [])
    if tool_with_list and not tool_call_list:
        tool_call_list = [
            {
                "id": item.get("toolCall", {}).get("id", ""),
                "name": item.get("name", ""),
                "arguments": item.get("toolCall", {}).get("parameters", {}),
            }
            for item in tool_with_list
        ]

    results = []
    async with async_session() as db:
        for tc in tool_call_list:
            tool_name = tc.get("name", "")
            tool_call_id = tc.get("id", "")
            args = tc.get("arguments", {})

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
    async with async_session() as db:
        voice_call = await save_call_record(db, message)
        await db.commit()
        logger.info(f"Saved voice call {voice_call.vapi_call_id}")
    return {"ok": True}
