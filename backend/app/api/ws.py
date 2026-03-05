"""WebSocket endpoint for real-time notifications."""
from __future__ import annotations
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}  # user_id -> [ws, ...]
        self.ticket_viewers: dict[str, dict[str, str]] = {}  # ticket_id -> {user_id: user_name}
        self.user_names: dict[str, str] = {}  # user_id -> name (cache)

    async def connect(self, ws: WebSocket, user_id: str):
        await ws.accept()
        self.active.setdefault(user_id, []).append(ws)
        logger.info(f"WS connected: user={user_id} (total={sum(len(v) for v in self.active.values())})")

    def disconnect(self, ws: WebSocket, user_id: str):
        conns = self.active.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns and user_id in self.active:
            del self.active[user_id]
        # Remove from all ticket viewers
        for tid in list(self.ticket_viewers.keys()):
            if user_id in self.ticket_viewers[tid]:
                del self.ticket_viewers[tid][user_id]
            if not self.ticket_viewers[tid]:
                del self.ticket_viewers[tid]

    async def add_ticket_viewer(self, ticket_id: str, user_id: str, user_name: str):
        """Track user viewing a ticket and notify others."""
        # Remove from previous tickets
        for tid in list(self.ticket_viewers.keys()):
            if tid != ticket_id and user_id in self.ticket_viewers[tid]:
                del self.ticket_viewers[tid][user_id]
                if not self.ticket_viewers[tid]:
                    del self.ticket_viewers[tid]
                else:
                    await self._broadcast_viewers(tid)

        self.ticket_viewers.setdefault(ticket_id, {})[user_id] = user_name
        self.user_names[user_id] = user_name
        await self._broadcast_viewers(ticket_id)

    async def remove_ticket_viewer(self, ticket_id: str, user_id: str):
        """Remove user from ticket viewers."""
        viewers = self.ticket_viewers.get(ticket_id, {})
        if user_id in viewers:
            del viewers[user_id]
            if not viewers and ticket_id in self.ticket_viewers:
                del self.ticket_viewers[ticket_id]
            else:
                await self._broadcast_viewers(ticket_id)

    async def _broadcast_viewers(self, ticket_id: str):
        """Broadcast current viewers list to everyone viewing this ticket."""
        viewers = self.ticket_viewers.get(ticket_id, {})
        viewer_list = [{"user_id": uid, "name": name} for uid, name in viewers.items()]
        for uid in viewers:
            await self.send_to_user(uid, {
                "type": "ticket_viewers",
                "ticket_id": ticket_id,
                "viewers": viewer_list,
            })

    async def send_to_user(self, user_id: str, data: dict):
        dead = []
        for ws in self.active.get(user_id, []):
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.debug(f"WS send failed for user={user_id}: {e}")
                dead.append(ws)
        # Clean up dead connections
        for ws in dead:
            self.disconnect(ws, user_id)

    async def broadcast(self, data: dict, exclude_user: str | None = None):
        dead_pairs = []
        for uid, connections in self.active.items():
            if uid == exclude_user:
                continue
            for ws in connections:
                try:
                    await ws.send_json(data)
                except Exception as e:
                    logger.debug(f"WS broadcast failed for user={uid}: {e}")
                    dead_pairs.append((ws, uid))
        for ws, uid in dead_pairs:
            self.disconnect(ws, uid)


manager = ConnectionManager()


@router.websocket("/ws/{token}")
async def websocket_endpoint(ws: WebSocket, token: str):
    """WebSocket connection authenticated via JWT token in URL."""
    from app.core.security import decode_token

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await ws.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await ws.close(code=4001, reason="Invalid token")
        return

    # Get user name for collision detection
    user_name = "Agente"
    try:
        from sqlalchemy import select as sa_select
        from app.core.database import async_session
        from app.models.user import User
        async with async_session() as db:
            result = await db.execute(sa_select(User).where(User.id == user_id))
            u = result.scalar_one_or_none()
            if u:
                user_name = u.name or u.email
    except Exception:
        pass

    await manager.connect(ws, user_id)
    try:
        while True:
            raw = await ws.receive_text()
            if raw == "ping":
                await ws.send_text("pong")
                continue
            try:
                data = json.loads(raw)
                msg_type = data.get("type")
                if msg_type == "viewing_ticket":
                    ticket_id = data.get("ticket_id")
                    if ticket_id:
                        await manager.add_ticket_viewer(ticket_id, user_id, user_name)
                elif msg_type == "leave_ticket":
                    ticket_id = data.get("ticket_id")
                    if ticket_id:
                        await manager.remove_ticket_viewer(ticket_id, user_id)
            except (json.JSONDecodeError, KeyError):
                pass
    except WebSocketDisconnect:
        manager.disconnect(ws, user_id)
    except Exception:
        manager.disconnect(ws, user_id)


async def notify_ticket_update(ticket_id: str, ticket_number: int, action: str, actor_name: str, details: str = "", exclude_user: str | None = None):
    """Broadcast a ticket update notification to all connected users."""
    await manager.broadcast({
        "type": "ticket_update",
        "ticket_id": ticket_id,
        "ticket_number": ticket_number,
        "action": action,
        "actor": actor_name,
        "details": details,
    }, exclude_user=exclude_user)


async def notify_new_ticket(ticket_id: str, ticket_number: int, subject: str, customer_name: str):
    """Notify all users about a new ticket."""
    await manager.broadcast({
        "type": "new_ticket",
        "ticket_id": ticket_id,
        "ticket_number": ticket_number,
        "subject": subject,
        "customer": customer_name,
    })


async def notify_assignment(ticket_id: str, ticket_number: int, agent_id: str, agent_name: str):
    """Notify specific agent about ticket assignment."""
    await manager.send_to_user(agent_id, {
        "type": "assignment",
        "ticket_id": ticket_id,
        "ticket_number": ticket_number,
        "message": f"Ticket #{ticket_number} foi atribuído a você",
    })


async def notify_escalation(ticket_id: str, ticket_number: int, reason: str):
    """Notify all users about an escalated ticket."""
    await manager.broadcast({
        "type": "escalation",
        "ticket_id": ticket_id,
        "ticket_number": ticket_number,
        "reason": reason,
    })


# ── Chat visitor WebSocket ──

from app.services.chat_ws_manager import chat_manager


@router.websocket("/ws/chat/{visitor_id}")
async def ws_chat(ws: WebSocket, visitor_id: str):
    """WebSocket for chat widget visitors. No auth — visitor_id is a session identifier."""
    await chat_manager.connect_visitor(visitor_id, ws)
    try:
        while True:
            data = await ws.receive_json()
            event = data.get("event")

            if event == "new_message":
                conversation_id = data.get("conversation_id")
                content = data.get("content", "")

                await chat_manager.broadcast_to_agents({
                    "event": "new_message",
                    "conversation_id": conversation_id,
                    "content": content,
                    "sender_type": "contact",
                    "sender_id": visitor_id,
                })

                if conversation_id and content:
                    from app.core.database import async_session
                    from app.services.message_pipeline import process_incoming_message
                    from sqlalchemy import select as sa_select
                    from app.models.conversation import Conversation
                    from app.models.customer import Customer

                    async with async_session() as db:
                        conv = (await db.execute(
                            sa_select(Conversation).where(Conversation.id == conversation_id)
                        )).scalar_one_or_none()
                        if conv:
                            customer = (await db.execute(
                                sa_select(Customer).where(Customer.id == conv.customer_id)
                            )).scalar_one_or_none()
                            if customer:
                                pipeline_result = await process_incoming_message(
                                    db, conv, customer, content, visitor_id=visitor_id,
                                )
                                for bot_msg in pipeline_result.get("bot_messages", []):
                                    await chat_manager.send_to_visitor(visitor_id, {
                                        "event": "new_message",
                                        "conversation_id": conversation_id,
                                        "content": bot_msg,
                                        "sender_type": "bot",
                                    })
                                    await chat_manager.broadcast_to_agents({
                                        "event": "new_message",
                                        "conversation_id": conversation_id,
                                        "content": bot_msg,
                                        "sender_type": "bot",
                                    })
                                if pipeline_result.get("escalated"):
                                    await chat_manager.broadcast_to_agents({
                                        "event": "escalation",
                                        "conversation_id": conversation_id,
                                    })

            elif event == "typing":
                conversation_id = data.get("conversation_id")
                await chat_manager.broadcast_to_agents({
                    "event": "typing",
                    "conversation_id": conversation_id,
                    "sender_type": "contact",
                    "sender_id": visitor_id,
                })

    except WebSocketDisconnect:
        await chat_manager.disconnect_visitor(visitor_id)
    except Exception as e:
        logger.error("Chat visitor WS error for %s: %s", visitor_id, e)
        await chat_manager.disconnect_visitor(visitor_id)
