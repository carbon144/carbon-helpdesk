"""Chat routing — auto-assign conversations to available agents."""

import logging
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage

logger = logging.getLogger(__name__)


async def get_available_agents(db: AsyncSession) -> list[User]:
    """Return online agents that are below their max_concurrent_chats limit."""
    active_count_sub = (
        select(
            Conversation.assigned_to.label("agent_id"),
            func.count().label("active_count"),
        )
        .where(Conversation.status.in_(["open", "pending"]))
        .where(Conversation.assigned_to.is_not(None))
        .group_by(Conversation.assigned_to)
        .subquery()
    )

    query = (
        select(User)
        .outerjoin(active_count_sub, User.id == active_count_sub.c.agent_id)
        .where(User.status == "online")
        .where(User.is_active.is_(True))
        .where(User.role.in_(["agent", "supervisor", "admin", "super_admin"]))
        .where(
            func.coalesce(active_count_sub.c.active_count, 0) < User.max_concurrent_chats
        )
        .order_by(func.coalesce(active_count_sub.c.active_count, 0).asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def auto_assign(
    db: AsyncSession, conversation: Conversation
) -> Optional[User]:
    """Pick the online agent with fewest active conversations (round-robin).
    Assigns agent to conversation, returns agent or None if nobody available.
    Uses FOR UPDATE to prevent race conditions."""
    # Lock the conversation row to prevent concurrent assignment
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation.id)
        .with_for_update()
    )
    conv = result.scalar_one_or_none()
    if not conv or conv.assigned_to:
        # Already assigned by another request
        return None

    agents = await get_available_agents(db)
    if not agents:
        return None

    agent = agents[0]  # least loaded
    conv.assigned_to = agent.id
    await db.commit()
    await db.refresh(conv)
    # Update the original reference too
    conversation.assigned_to = conv.assigned_to
    return agent


async def transfer(
    db: AsyncSession,
    conversation_id: str,
    from_agent_id: str,
    to_agent_id: str,
) -> Optional[Conversation]:
    """Transfer conversation from one agent to another with a system message."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        return None

    from_result = await db.execute(select(User).where(User.id == from_agent_id))
    from_agent = from_result.scalar_one_or_none()

    to_result = await db.execute(select(User).where(User.id == to_agent_id))
    to_agent = to_result.scalar_one_or_none()

    if not from_agent or not to_agent:
        return None

    conv.assigned_to = to_agent_id
    await db.flush()

    system_msg = ChatMessage(
        conversation_id=conversation_id,
        sender_type="system",
        sender_id=None,
        content_type="text",
        content=f"Conversa transferida de {from_agent.name} para {to_agent.name}",
    )
    db.add(system_msg)
    await db.commit()
    await db.refresh(conv)
    return conv
