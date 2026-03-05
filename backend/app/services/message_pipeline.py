"""Message pipeline orchestrator — Chatbot -> AI -> Human handoff."""

import logging
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.chat_message import ChatMessage
from app.models.kb_article import KBArticle
from app.services.chatbot_engine import ChatbotEngine
from app.services import ai_service
from app.services import chat_routing_service as routing_service

logger = logging.getLogger(__name__)

MAX_AI_ATTEMPTS = 3

_chatbot_engine = ChatbotEngine()


async def _search_kb(db: AsyncSession, query: str, limit: int = 3) -> list[KBArticle]:
    pattern = f"%{query}%"
    result = await db.execute(
        select(KBArticle)
        .where(
            KBArticle.is_published.is_(True),
            or_(KBArticle.title.ilike(pattern), KBArticle.content.ilike(pattern)),
        )
        .order_by(KBArticle.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def process_incoming_message(
    db: AsyncSession,
    conversation: Conversation,
    customer: Customer,
    message_text: str,
    visitor_id: str | None = None,
) -> dict:
    result = {"handler": conversation.handler or "chatbot", "bot_messages": [], "escalated": False}

    # Layer 0: If agent is in control and AI is off, skip everything
    if conversation.handler == "agent" and not conversation.ai_enabled:
        return result

    # Layer 1: Chatbot flows
    if conversation.handler in ("chatbot", None):
        chatbot_result = await _chatbot_engine.process_message(
            db, conversation, message_text, visitor_id=visitor_id,
        )

        if chatbot_result and chatbot_result.get("matched"):
            responses = chatbot_result.get("responses", [])
            for resp in responses:
                if resp.get("type") == "transfer_to_agent":
                    return await _escalate_to_agent(
                        db, conversation, result,
                        escalation_message=resp.get("message", "Transferindo para um atendente..."),
                    )
                if resp.get("type") == "send_message":
                    content = resp.get("content", "")
                    if content:
                        result["bot_messages"].append(content)
                        await _save_bot_message(db, conversation, content)

            if result["bot_messages"]:
                result["handler"] = "chatbot"
                await db.commit()
                return result

        # No chatbot match — fall through to AI
        conversation.handler = "ai"

    # Layer 2: AI auto-reply
    if conversation.handler == "ai" and conversation.ai_enabled:
        kb_articles = []
        try:
            articles = await _search_kb(db, message_text, limit=3)
            kb_articles = [{"title": a.title, "content": a.content} for a in articles]
        except Exception:
            logger.warning("KB search failed, continuing without KB context")

        messages_history = _build_history(conversation)
        messages_history.append({"role": "contact", "content": message_text})

        shopify_data = getattr(customer, "shopify_data", None)

        ai_result = await ai_service.chat_auto_reply(
            messages=messages_history,
            contact_shopify_data=shopify_data,
            kb_articles=kb_articles if kb_articles else None,
        )

        if ai_result["resolved"]:
            conversation.ai_attempts = 0
            result["handler"] = "ai"
            result["bot_messages"].append(ai_result["response"])
            await _save_bot_message(db, conversation, ai_result["response"])
            await db.commit()
            return result
        else:
            conversation.ai_attempts = (conversation.ai_attempts or 0) + 1
            await db.commit()

            if conversation.ai_attempts >= MAX_AI_ATTEMPTS:
                return await _escalate_to_agent(db, conversation, result)
            else:
                if ai_result["response"]:
                    result["handler"] = "ai"
                    result["bot_messages"].append(ai_result["response"])
                    await _save_bot_message(db, conversation, ai_result["response"])
                await db.commit()
                return result

    return result


async def _escalate_to_agent(
    db: AsyncSession,
    conversation: Conversation,
    result: dict,
    escalation_message: str = "Vou transferir voce para um de nossos atendentes. Um momento, por favor.",
) -> dict:
    conversation.handler = "agent"
    conversation.ai_enabled = False
    conversation.ai_attempts = 0

    await routing_service.auto_assign(db, conversation)

    system_msg = ChatMessage(
        conversation_id=conversation.id,
        sender_type="system",
        sender_id=None,
        content_type="text",
        content="Conversa transferida para atendimento humano.",
    )
    db.add(system_msg)

    result["bot_messages"].append(escalation_message)
    await _save_bot_message(db, conversation, escalation_message)

    await db.commit()

    result["handler"] = "agent"
    result["escalated"] = True
    return result


async def _save_bot_message(db: AsyncSession, conversation: Conversation, content: str):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    msg = ChatMessage(
        conversation_id=conversation.id,
        sender_type="bot",
        sender_id=None,
        content_type="text",
        content=content,
        created_at=now,
    )
    db.add(msg)
    conversation.last_message_at = now


def _build_history(conversation: Conversation) -> list[dict]:
    history = []
    for msg in (conversation.chat_messages or []):
        if msg.content_type == "note":
            continue
        role = "contact" if msg.sender_type == "contact" else "agent"
        history.append({"role": role, "content": msg.content})
    return history
