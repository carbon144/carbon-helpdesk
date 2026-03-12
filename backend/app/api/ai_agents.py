"""AI Agents CRUD API."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_agent import AIAgent
from app.models.ticket import Ticket
from app.models.message import Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai-agents", tags=["ai-agents"])


@router.get("")
async def list_agents(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """List all AI agents with stats."""
    result = await db.execute(select(AIAgent).order_by(AIAgent.level, AIAgent.name))
    agents = result.scalars().all()

    agents_list = []
    for a in agents:
        # Count pending drafts
        draft_count = await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.ai_agent_id == a.id,
                Ticket.ai_draft_text.isnot(None),
            )
        )

        agents_list.append({
            "id": a.id,
            "name": a.name,
            "human_name": a.human_name,
            "role": a.role,
            "level": a.level,
            "categories": a.categories or [],
            "tools_enabled": a.tools_enabled or [],
            "confidence_threshold": a.confidence_threshold,
            "auto_send": a.auto_send,
            "is_active": a.is_active,
            "total_replies": a.total_replies,
            "total_approved": a.total_approved,
            "total_escalated": a.total_escalated,
            "pending_drafts": draft_count.scalar() or 0,
            "approval_rate": round(a.total_approved / a.total_replies * 100, 1) if a.total_replies > 0 else 0,
        })

    return {"agents": agents_list}


@router.get("/{agent_id}")
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get agent detail with prompt and examples."""
    result = await db.execute(select(AIAgent).where(AIAgent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    return {
        "id": agent.id,
        "name": agent.name,
        "human_name": agent.human_name,
        "role": agent.role,
        "level": agent.level,
        "categories": agent.categories or [],
        "tools_enabled": agent.tools_enabled or [],
        "system_prompt": agent.system_prompt,
        "few_shot_examples": agent.few_shot_examples or [],
        "escalation_keywords": agent.escalation_keywords or [],
        "confidence_threshold": agent.confidence_threshold,
        "auto_send": agent.auto_send,
        "is_active": agent.is_active,
        "total_replies": agent.total_replies,
        "total_approved": agent.total_approved,
        "total_escalated": agent.total_escalated,
    }


@router.put("/{agent_id}")
async def update_agent(agent_id: str, body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Update agent config (prompt, threshold, examples, etc)."""
    result = await db.execute(select(AIAgent).where(AIAgent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    ALLOWED_FIELDS = [
        "system_prompt", "few_shot_examples", "escalation_keywords",
        "confidence_threshold", "categories", "tools_enabled", "is_active",
    ]
    for field in ALLOWED_FIELDS:
        if field in body:
            setattr(agent, field, body[field])

    await db.commit()
    return {"status": "updated", "agent": agent.name}


@router.post("/{agent_id}/toggle")
async def toggle_auto_send(agent_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Toggle auto_send on/off."""
    result = await db.execute(select(AIAgent).where(AIAgent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    agent.auto_send = not agent.auto_send
    await db.commit()
    return {"agent": agent.name, "auto_send": agent.auto_send}


@router.get("/{agent_id}/drafts")
async def get_agent_drafts(agent_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get pending drafts for this agent."""
    result = await db.execute(
        select(Ticket)
        .where(
            Ticket.ai_agent_id == agent_id,
            Ticket.ai_draft_text.isnot(None),
        )
        .options(joinedload(Ticket.customer))
        .order_by(Ticket.created_at.desc())
        .limit(50)
    )
    tickets = result.scalars().all()

    drafts = []
    for t in tickets:
        drafts.append({
            "ticket_id": t.id,
            "ticket_number": t.number,
            "subject": t.subject,
            "category": t.category,
            "priority": t.priority,
            "customer_name": t.customer.name if t.customer else "?",
            "customer_email": t.customer.email if t.customer else "?",
            "draft_text": t.ai_draft_text,
            "draft_confidence": t.ai_draft_confidence,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    return {"drafts": drafts, "total": len(drafts)}


@router.post("/{agent_id}/drafts/{ticket_id}/approve")
async def approve_draft(agent_id: str, ticket_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Approve and send a draft reply."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id, Ticket.ai_agent_id == agent_id))
    ticket = result.scalar_one_or_none()
    if not ticket or not ticket.ai_draft_text:
        raise HTTPException(404, "Draft not found")

    # Send the email
    from app.services.email_auto_reply_service import send_auto_reply

    customer = ticket.customer
    if not customer or not customer.email:
        raise HTTPException(400, "No customer email")

    # Find gmail thread
    msg_result = await db.execute(
        select(Message).where(
            Message.ticket_id == ticket.id,
            Message.gmail_thread_id.isnot(None),
        ).limit(1)
    )
    first_msg = msg_result.scalars().first()

    sent = await send_auto_reply(
        to_email=customer.email,
        subject=ticket.subject or "",
        body_text=ticket.ai_draft_text,
        gmail_thread_id=first_msg.gmail_thread_id if first_msg else None,
        gmail_message_id=first_msg.gmail_message_id if first_msg else None,
    )

    if sent:
        # Save as message
        agent_name = "Carbon IA"
        if ticket.ai_agent:
            agent_name = ticket.ai_agent.name

        auto_msg = Message(
            ticket_id=ticket.id,
            type="outbound",
            sender_name=agent_name,
            sender_email=settings.GMAIL_SUPPORT_EMAIL or "suporte@carbonsmartwatch.com.br",
            body_text=ticket.ai_draft_text,
            gmail_message_id=sent.get("id"),
            gmail_thread_id=sent.get("threadId"),
        )
        db.add(auto_msg)

        # Update agent stats
        agent_result = await db.execute(select(AIAgent).where(AIAgent.id == agent_id))
        agent = agent_result.scalar_one_or_none()
        if agent:
            agent.total_approved += 1

        # Clear draft, update ticket
        draft_text = ticket.ai_draft_text  # save before clearing
        ticket.ai_draft_text = None
        ticket.ai_draft_confidence = None
        ticket.auto_replied = True
        ticket.auto_reply_at = datetime.now(timezone.utc)
        ticket.first_response_at = ticket.first_response_at or datetime.now(timezone.utc)
        ticket.status = "waiting"
        existing_tags = list(ticket.tags or [])
        existing_tags.append("agent_approved")
        ticket.tags = list(set(existing_tags))

        # === ESTORNO / REENVIO DETECTION (after approved draft) ===
        try:
            from app.services.estorno_service import detect_estorno, notify_estorno_slack, log_estorno_to_sheet
            from app.services.reenvio_service import detect_reenvio, create_reenvio_draft_order, notify_reenvio_slack, check_reenvio_limit

            # Fetch order data for context
            _order_data = None
            if ticket.customer and ticket.customer.email:
                from app.services.shopify_service import get_orders_by_email
                orders_result = await get_orders_by_email(ticket.customer.email, limit=1)
                if orders_result.get("orders"):
                    _order_data = orders_result["orders"][0]

            if detect_estorno(draft_text, ticket.category):
                await notify_estorno_slack(ticket, _order_data, agent_name, draft_text)
                await log_estorno_to_sheet(ticket, _order_data)
                logger.info(f"Estorno detected in approved draft for ticket #{ticket.number}")

            if detect_reenvio(draft_text, ticket.category):
                limit_info = await check_reenvio_limit(db)
                if limit_info["allowed"] and _order_data:
                    draft_order = await create_reenvio_draft_order(_order_data)
                    if draft_order.get("success"):
                        await notify_reenvio_slack(ticket, _order_data, draft_order, limit_info)
                        existing_tags = list(ticket.tags or [])
                        existing_tags.append("reenvio-ia")
                        ticket.tags = list(set(existing_tags))
                        logger.info(f"Reenvio draft created for approved ticket #{ticket.number}")
        except Exception as e:
            logger.warning(f"Estorno/reenvio detection skipped in approve_draft: {e}")

        await db.commit()
        return {"status": "sent", "ticket_number": ticket.number}

    raise HTTPException(500, "Failed to send email")


@router.post("/{agent_id}/drafts/{ticket_id}/reject")
async def reject_draft(agent_id: str, ticket_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Reject a draft (human will handle)."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id, Ticket.ai_agent_id == agent_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    ticket.ai_draft_text = None
    ticket.ai_draft_confidence = None

    await db.commit()
    return {"status": "rejected", "ticket_number": ticket.number}
