"""Chat API endpoints — conversations, messages, assignment."""
from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage
from app.schemas.chat import (
    ConversationResponse, ConversationCreate,
    ChatMessageResponse, ChatMessageCreate,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations/counts")
async def conversation_counts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    counts = {}
    for status in ("open", "pending", "resolved", "closed"):
        result = await db.execute(
            select(func.count(Conversation.id)).where(Conversation.status == status)
        )
        counts[status] = result.scalar() or 0
    counts["total"] = sum(counts.values())
    # Mine
    result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.assigned_to == user.id,
            Conversation.status.in_(["open", "pending"]),
        )
    )
    counts["mine"] = result.scalar() or 0
    return counts


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    status: str | None = None,
    channel: str | None = None,
    assigned_to: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Conversation).order_by(Conversation.last_message_at.desc().nullslast())
    if status:
        query = query.where(Conversation.status == status)
    if channel:
        query = query.where(Conversation.channel == channel)
    if assigned_to:
        query = query.where(Conversation.assigned_to == assigned_to)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(
    conv_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify customer exists
    cust = await db.execute(select(Customer).where(Customer.id == data.customer_id))
    if not cust.scalar_one_or_none():
        raise HTTPException(404, "Customer not found")

    conv = Conversation(
        customer_id=data.customer_id,
        channel=data.channel,
        subject=data.subject,
        status="open",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/conversations/{conv_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    conv_id: str,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conv_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(offset).limit(limit)
    )
    return list(result.scalars().all())


@router.post("/conversations/{conv_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    conv_id: str,
    data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify conversation
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "Conversation not found")

    now = datetime.now(timezone.utc)
    msg = ChatMessage(
        conversation_id=conv_id,
        sender_type="agent",
        sender_id=user.id,
        content_type=data.content_type,
        content=data.content,
        created_at=now,
    )
    db.add(msg)
    conv.last_message_at = now
    await db.commit()
    await db.refresh(msg)

    # Notify visitor via WS
    from app.services.chat_ws_manager import chat_manager
    customer_result = await db.execute(select(Customer).where(Customer.id == conv.customer_id))
    customer = customer_result.scalar_one_or_none()
    visitor_id = None
    if customer and customer.external_id:
        visitor_id = customer.external_id
    if visitor_id:
        await chat_manager.send_to_visitor(visitor_id, {
            "event": "new_message",
            "conversation_id": conv_id,
            "content": data.content,
            "sender_type": "agent",
            "sender_id": user.id,
        })

    # Also send via channel adapter if not chat
    if conv.channel != "chat" and visitor_id:
        from app.services.channels.dispatcher import dispatcher
        from app.models.channel_identity import ChannelIdentity
        ci_result = await db.execute(
            select(ChannelIdentity).where(
                ChannelIdentity.customer_id == conv.customer_id,
                ChannelIdentity.channel == conv.channel,
            )
        )
        ci = ci_result.scalar_one_or_none()
        if ci:
            await dispatcher.send(conv.channel, ci.channel_id, data.content)

    return msg


@router.post("/conversations/{conv_id}/toggle-ai")
async def toggle_ai(
    conv_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "Conversation not found")

    conv.ai_enabled = not conv.ai_enabled
    if conv.ai_enabled:
        conv.handler = "ai"
        conv.ai_attempts = 0
    else:
        conv.handler = "agent"
    await db.commit()
    return {"ai_enabled": conv.ai_enabled, "handler": conv.handler}


@router.put("/conversations/{conv_id}/assign")
async def assign_conversation(
    conv_id: str,
    agent_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "Conversation not found")

    agent = await db.execute(select(User).where(User.id == agent_id))
    if not agent.scalar_one_or_none():
        raise HTTPException(404, "Agent not found")

    conv.assigned_to = agent_id
    conv.handler = "agent"
    await db.commit()
    return {"assigned_to": agent_id}


@router.put("/conversations/{conv_id}/resolve")
async def resolve_conversation(
    conv_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "Conversation not found")

    conv.status = "resolved"
    now = datetime.now(timezone.utc)
    system_msg = ChatMessage(
        conversation_id=conv_id,
        sender_type="system",
        content="Conversa resolvida.",
        created_at=now,
    )
    db.add(system_msg)
    conv.last_message_at = now
    await db.commit()
    return {"status": "resolved"}
