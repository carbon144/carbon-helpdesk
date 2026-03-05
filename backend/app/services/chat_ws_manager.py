"""WebSocket connection manager for real-time chat (agent + visitor connections)."""

import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ChatConnectionManager:
    """Manages WebSocket connections for chat agents and visitors (widget users)."""

    def __init__(self):
        self.agent_connections: dict[str, WebSocket] = {}
        self.visitor_connections: dict[str, WebSocket] = {}

    async def connect_agent(self, agent_id: str, ws: WebSocket):
        await ws.accept()
        self.agent_connections[agent_id] = ws
        logger.info("Chat agent %s connected via WebSocket", agent_id)

    async def connect_visitor(self, visitor_id: str, ws: WebSocket):
        await ws.accept()
        self.visitor_connections[visitor_id] = ws
        logger.info("Chat visitor %s connected via WebSocket", visitor_id)

    async def disconnect_agent(self, agent_id: str):
        self.agent_connections.pop(agent_id, None)
        logger.info("Chat agent %s disconnected from WebSocket", agent_id)

    async def disconnect_visitor(self, visitor_id: str):
        self.visitor_connections.pop(visitor_id, None)
        logger.info("Chat visitor %s disconnected from WebSocket", visitor_id)

    async def send_to_agent(self, agent_id: str, data: dict):
        ws = self.agent_connections.get(agent_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                logger.warning("Failed to send to chat agent %s, removing connection", agent_id)
                await self.disconnect_agent(agent_id)

    async def send_to_visitor(self, visitor_id: str, data: dict):
        ws = self.visitor_connections.get(visitor_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                logger.warning("Failed to send to chat visitor %s, removing connection", visitor_id)
                await self.disconnect_visitor(visitor_id)

    async def broadcast_to_agents(self, data: dict):
        disconnected: list[str] = []
        for agent_id, ws in self.agent_connections.items():
            try:
                await ws.send_json(data)
            except Exception:
                logger.warning("Failed to broadcast to chat agent %s", agent_id)
                disconnected.append(agent_id)
        for agent_id in disconnected:
            await self.disconnect_agent(agent_id)


# Singleton instance used across the app
chat_manager = ChatConnectionManager()
