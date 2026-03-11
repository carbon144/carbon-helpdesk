"""WebSocket manager for live voice call monitoring."""
import logging
import json
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class VoiceCallManager:
    """Tracks active voice calls and broadcasts live transcript to connected agents."""

    def __init__(self):
        self.agent_connections: dict[str, WebSocket] = {}
        # Active calls: {call_id: {caller_phone, started_at, transcript_lines, status}}
        self.active_calls: dict[str, dict] = {}

    async def connect_agent(self, agent_id: str, ws: WebSocket):
        await ws.accept()
        self.agent_connections[agent_id] = ws
        logger.info("Voice monitor agent %s connected", agent_id)
        # Send current active calls on connect
        await ws.send_json({"type": "active_calls", "calls": list(self.active_calls.values())})

    async def disconnect_agent(self, agent_id: str):
        self.agent_connections.pop(agent_id, None)
        logger.info("Voice monitor agent %s disconnected", agent_id)

    def start_call(self, call_id: str, caller_phone: str = None):
        from datetime import datetime, timezone
        self.active_calls[call_id] = {
            "call_id": call_id,
            "caller_phone": caller_phone,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "transcript_lines": [],
            "status": "active",
        }

    def end_call(self, call_id: str):
        self.active_calls.pop(call_id, None)

    def add_transcript(self, call_id: str, role: str, text: str):
        call = self.active_calls.get(call_id)
        if call:
            lines = call["transcript_lines"]
            lines.append({"role": role, "text": text})
            # Cap at 500 lines to prevent unbounded memory growth
            if len(lines) > 500:
                call["transcript_lines"] = lines[-500:]

    async def broadcast(self, data: dict):
        disconnected = []
        for agent_id, ws in self.agent_connections.items():
            try:
                await ws.send_json(data)
            except Exception:
                logger.warning("Failed to send to voice monitor agent %s", agent_id)
                disconnected.append(agent_id)
        for agent_id in disconnected:
            await self.disconnect_agent(agent_id)


voice_manager = VoiceCallManager()
