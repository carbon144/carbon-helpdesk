"""Meta Platform webhook — handles WhatsApp, Instagram, and Facebook Messenger."""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, HTTPException, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.customer import Customer
from app.services.meta_service import (
    verify_signature, parse_webhook_entry, parse_comment_events,
    send_message, get_user_profile, reply_to_comment, hide_comment,
    unhide_comment, fetch_page_posts, fetch_instagram_media,
    fetch_comments_for_post,
)
from app.services.ai_service import triage_ticket as ai_triage, ai_auto_reply, moderate_comment
from app.services.protocol_service import assign_protocol
from app.models.social_comment import SocialComment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meta", tags=["meta"])


# ── Webhook verification (GET) — Meta sends this during app setup ──

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Handle Meta webhook verification challenge."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
        logger.info("Meta webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(403, "Verification failed")


# ── Webhook events (POST) — receives all messages ──

@router.post("/webhook")
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle incoming Meta webhook events (WhatsApp, Instagram, Facebook)."""
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(body, signature):
        raise HTTPException(401, "Invalid signature")

    data = await request.json()
    webhook_object = data.get("object", "")

    # Parse entries — Meta sends batched events
    for entry in data.get("entry", []):
        # Process DMs (WhatsApp, Instagram, Facebook Messenger)
        normalized_messages = parse_webhook_entry(entry, webhook_object)
        for msg_data in normalized_messages:
            try:
                await _process_inbound_message(db, msg_data)
            except Exception as e:
                logger.error(f"Error processing Meta message: {e}")

        # Process comments (Instagram, Facebook)
        comment_events = parse_comment_events(entry, webhook_object)
        for comment_data in comment_events:
            try:
                await _process_comment(db, comment_data)
            except Exception as e:
                logger.error(f"Error processing Meta comment: {e}")

    return {"status": "ok"}


async def _process_inbound_message(db: AsyncSession, msg_data: dict):
    """Process a single inbound message from any Meta platform."""
    platform = msg_data["platform"]
    sender_id = msg_data["sender_id"]
    sender_name = msg_data.get("sender_name") or ""
    text = msg_data["text"]
    message_id = msg_data["message_id"]

    # 1. Check if message already processed
    existing = await db.execute(
        select(Message).where(Message.meta_message_id == message_id)
    )
    if existing.scalars().first():
        return

    # 2. Find or create customer
    customer = await _find_or_create_customer(db, platform, sender_id, sender_name)

    # 3. Find open ticket or create new one
    ticket, is_new_ticket = await _find_or_create_ticket(db, customer, platform, text)

    # 4. Create inbound message
    message = Message(
        ticket_id=ticket.id,
        type="inbound",
        sender_name=customer.name,
        sender_email=customer.email,
        body_text=text,
        meta_message_id=message_id,
        meta_platform=platform,
    )
    db.add(message)
    await db.flush()

    # 5. AI triage on first message
    if is_new_ticket:
        try:
            triage = await ai_triage(
                subject=ticket.subject,
                body=text[:2000],
                customer_name=customer.name,
                is_repeat=customer.is_repeat,
            )
            if triage:
                if triage.get("category"):
                    ticket.ai_category = triage["category"]
                    ticket.category = triage["category"]
                if triage.get("priority"):
                    ticket.priority = triage["priority"]
                    hours_map = {
                        "urgent": settings.SLA_URGENT_HOURS,
                        "high": settings.SLA_HIGH_HOURS,
                        "medium": settings.SLA_MEDIUM_HOURS,
                        "low": settings.SLA_LOW_HOURS,
                    }
                    ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(
                        hours=hours_map.get(triage["priority"], 24)
                    )
                if triage.get("sentiment"):
                    ticket.sentiment = triage["sentiment"]
                if triage.get("legal_risk") is not None:
                    ticket.legal_risk = triage["legal_risk"]
                if triage.get("tags"):
                    ticket.tags = triage["tags"]
                if triage.get("confidence"):
                    ticket.ai_confidence = triage["confidence"]
        except Exception as e:
            logger.warning(f"AI triage skipped for Meta ticket: {e}")

    # 6. AI auto-reply (if enabled)
    if ticket.ai_auto_mode:
        await _send_ai_reply(db, ticket, customer, platform, sender_id)

    await db.commit()
    logger.info(f"Processed Meta {platform} message for ticket #{ticket.number}")


async def _find_or_create_customer(
    db: AsyncSession, platform: str, sender_id: str, sender_name: str
) -> Customer:
    """Find customer by meta_user_id or create a new one, following merge chain."""
    from app.services.customer_matcher import _follow_merge_chain

    result = await db.execute(
        select(Customer).where(Customer.meta_user_id == sender_id)
    )
    customer = result.scalars().first()

    if customer:
        # Follow merge chain — if customer was merged, use the target customer
        return await _follow_merge_chain(db, customer)

    # Fetch profile name from Meta if not provided
    if not sender_name:
        profile = await get_user_profile(platform, sender_id)
        if profile:
            sender_name = profile.get("name", "")

    name = sender_name or f"{platform.capitalize()} User"
    email = f"{sender_id}@{platform}.meta.local"

    customer = Customer(
        name=name,
        email=email,
        meta_user_id=sender_id,
    )
    db.add(customer)
    await db.flush()
    return customer


async def _find_or_create_ticket(
    db: AsyncSession, customer: Customer, platform: str, text: str
) -> tuple[Ticket, bool]:
    """Find an open ticket for this customer+platform, or create a new one.
    Returns (ticket, is_new)."""
    result = await db.execute(
        select(Ticket).where(
            Ticket.customer_id == customer.id,
            Ticket.meta_platform == platform,
            Ticket.status.notin_(["resolved", "closed", "archived"]),
        ).order_by(Ticket.created_at.desc())
    )
    ticket = result.scalars().first()

    if ticket:
        if ticket.status == "escalated":
            ticket.status = "open"
        ticket.updated_at = datetime.now(timezone.utc)
        return ticket, False

    # Create new ticket
    from app.services.ticket_number import get_next_ticket_number
    next_num = await get_next_ticket_number(db)

    subject = text.split("\n")[0][:100] if text else f"Mensagem via {platform.capitalize()}"
    sla_deadline = datetime.now(timezone.utc) + timedelta(hours=settings.SLA_MEDIUM_HOURS)

    ticket = Ticket(
        number=next_num,
        subject=subject,
        status="open",
        priority="medium",
        customer_id=customer.id,
        source=platform,
        meta_platform=platform,
        meta_conversation_id=f"{customer.meta_user_id}_{platform}",
        ai_auto_mode=True,
        sla_deadline=sla_deadline,
    )
    db.add(ticket)
    await db.flush()

    try:
        await assign_protocol(ticket, db)
    except Exception:
        pass

    return ticket, True


async def _send_ai_reply(
    db: AsyncSession, ticket: Ticket, customer: Customer, platform: str, recipient_id: str
):
    """Generate and send AI auto-reply."""
    msgs = await db.execute(
        select(Message)
        .where(Message.ticket_id == ticket.id)
        .order_by(Message.created_at)
    )
    all_messages = msgs.scalars().all()

    conversation_history = []
    for m in all_messages:
        role = "customer" if m.type == "inbound" else "assistant"
        conversation_history.append({"role": role, "content": m.body_text or ""})

    # Gather KB context
    kb_context = await _get_kb_context(db, ticket.category)

    result = await ai_auto_reply(
        ticket_subject=ticket.subject,
        conversation_history=conversation_history,
        customer_name=customer.name,
        category=ticket.category or "",
        kb_context=kb_context,
        platform=platform,
    )

    if not result or not result.get("response"):
        logger.warning(f"AI auto-reply returned empty for ticket #{ticket.number}")
        return

    response_text = result["response"]

    # Send via Meta API
    sent = await send_message(platform, recipient_id, response_text)
    if not sent:
        logger.error(f"Failed to send AI reply via {platform} for ticket #{ticket.number}")
        return

    # Extract message ID from response
    if platform == "whatsapp":
        sent_id = sent.get("messages", [{}])[0].get("id", "")
    else:
        sent_id = sent.get("message_id", "")

    outbound = Message(
        ticket_id=ticket.id,
        type="outbound",
        sender_name="Carbon IA",
        body_text=response_text,
        meta_message_id=sent_id,
        meta_platform=platform,
    )
    db.add(outbound)

    # Handle escalation
    if result.get("should_escalate"):
        ticket.status = "escalated"
        ticket.escalated_at = datetime.now(timezone.utc)
        ticket.escalation_reason = result.get("escalation_reason", "AI escalation from social channel")

    if not ticket.first_response_at:
        ticket.first_response_at = datetime.now(timezone.utc)


async def _get_kb_context(db: AsyncSession, category: str | None) -> str:
    """Fetch relevant KB articles for the given category."""
    from app.models.kb_article import KBArticle
    try:
        query = select(KBArticle).where(KBArticle.is_published.is_(True))
        if category:
            query = query.where(KBArticle.category == category)
        query = query.limit(3)
        result = await db.execute(query)
        articles = result.scalars().all()
        if not articles:
            result = await db.execute(
                select(KBArticle).where(KBArticle.is_published.is_(True)).limit(2)
            )
            articles = result.scalars().all()
        return "\n\n".join(f"## {a.title}\n{a.content[:800]}" for a in articles)
    except Exception as e:
        logger.warning(f"KB context fetch failed: {e}")
        return ""


# ── Comment moderation ──

async def _get_moderation_setting(db: AsyncSession, key: str, default: str = "true") -> str:
    """Get a moderation setting value from the database."""
    result = await db.execute(text(f"SELECT value FROM moderation_settings WHERE key = :key"), {"key": key})
    row = result.first()
    return row[0] if row else default


async def _process_comment(db: AsyncSession, comment_data: dict):
    """Process and moderate a single comment from Instagram or Facebook."""
    platform = comment_data["platform"]
    comment_id = comment_data["comment_id"]
    comment_text = comment_data["text"]
    author_name = comment_data.get("author_name", "")

    # Check if already processed
    existing = await db.execute(
        select(SocialComment).where(SocialComment.comment_id == comment_id)
    )
    if existing.scalars().first():
        return

    # Check if AI moderation is enabled
    ai_enabled = (await _get_moderation_setting(db, "ai_enabled")) == "true"

    result = None
    action = "ignore"
    reply_text = ""
    stored_action = "pending"
    reply_sent = False
    was_hidden = False

    if ai_enabled:
        result = await moderate_comment(
            comment_text=comment_text,
            author_name=author_name,
            post_caption=comment_data.get("post_caption", ""),
            platform=platform,
        )

        if result:
            action = result.get("action", "ignore")
            reply_text = result.get("reply", "")

            # Check auto_reply and auto_hide settings before executing
            auto_reply = (await _get_moderation_setting(db, "auto_reply")) == "true"
            auto_hide = (await _get_moderation_setting(db, "auto_hide")) == "true"

            if action in ("hide", "hide_reply") and auto_hide:
                was_hidden = await hide_comment(platform, comment_id)

            if action in ("reply", "hide_reply") and reply_text and auto_reply:
                sent = await reply_to_comment(platform, comment_id, reply_text)
                reply_sent = sent is not None

            # Map action to stored value
            if action == "hide_reply":
                stored_action = "hidden_replied"
            elif action == "hide":
                stored_action = "hidden"
            elif action == "reply":
                stored_action = "replied"
            else:
                stored_action = "ignored"
        else:
            logger.warning(f"AI moderation returned empty for comment {comment_id}")
            stored_action = "pending"
    else:
        stored_action = "pending"

    # Parse comment timestamp from Meta API
    commented_at = None
    raw_ts = comment_data.get("timestamp")
    if raw_ts:
        from datetime import datetime as dt
        try:
            if isinstance(raw_ts, (int, float)):
                commented_at = dt.fromtimestamp(raw_ts)
            elif isinstance(raw_ts, str):
                # Meta API returns ISO 8601 format like "2025-01-15T10:30:00+0000"
                commented_at = dt.fromisoformat(raw_ts.replace("+0000", "+00:00"))
        except Exception:
            pass

    # Save to database
    record = SocialComment(
        platform=platform,
        comment_id=comment_id,
        post_id=comment_data.get("post_id", ""),
        parent_comment_id=comment_data.get("parent_comment_id"),
        author_id=comment_data.get("author_id", ""),
        author_name=author_name,
        text=comment_text,
        post_caption=comment_data.get("post_caption") or None,
        ai_action=stored_action,
        ai_reply=reply_text if reply_text else None,
        ai_sentiment=result.get("sentiment") if result else None,
        ai_category=result.get("category") if result else None,
        ai_confidence=result.get("confidence") if result else None,
        reply_sent=reply_sent,
        was_hidden=was_hidden,
        commented_at=commented_at,
    )
    db.add(record)
    await db.commit()

    logger.info(f"Moderated {platform} comment {comment_id}: action={stored_action}, sentiment={result.get('sentiment') if result else 'N/A'}")


# ── Agent-facing API endpoints ──

@router.get("/status")
async def meta_status(user: User = Depends(get_current_user)):
    """Check if Meta integration is configured."""
    whatsapp_configured = bool(settings.META_WHATSAPP_TOKEN and settings.META_WHATSAPP_PHONE_ID)
    fb_ig_configured = bool(settings.META_PAGE_ACCESS_TOKEN)

    return {
        "whatsapp": {"configured": whatsapp_configured},
        "instagram": {"configured": fb_ig_configured},
        "facebook": {"configured": fb_ig_configured},
        "webhook_configured": bool(settings.META_APP_SECRET and settings.META_VERIFY_TOKEN),
    }


@router.post("/tickets/{ticket_id}/pause-ai")
async def pause_ai(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Pause AI auto-reply on a Meta ticket (agent takes over)."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    if not ticket.meta_platform:
        raise HTTPException(400, "Este ticket não é de um canal Meta")

    ticket.ai_auto_mode = False
    ticket.ai_paused_by = user.id
    ticket.ai_paused_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"AI paused on ticket #{ticket.number} by {user.name}")
    return {"ok": True, "ai_auto_mode": False}


@router.post("/tickets/{ticket_id}/resume-ai")
async def resume_ai(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Resume AI auto-reply on a Meta ticket."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    if not ticket.meta_platform:
        raise HTTPException(400, "Este ticket não é de um canal Meta")

    ticket.ai_auto_mode = True
    ticket.ai_paused_by = None
    ticket.ai_paused_at = None
    await db.commit()

    logger.info(f"AI resumed on ticket #{ticket.number} by {user.name}")
    return {"ok": True, "ai_auto_mode": True}


@router.post("/send-reply")
async def send_manual_reply(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a manual agent reply to a Meta channel (when AI is paused)."""
    data = await request.json()
    ticket_id = data.get("ticket_id")
    message_text = data.get("message")

    if not ticket_id or not message_text:
        raise HTTPException(400, "ticket_id e message são obrigatórios")

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    if not ticket.meta_platform:
        raise HTTPException(400, "Este ticket não é de um canal Meta")

    cust_result = await db.execute(select(Customer).where(Customer.id == ticket.customer_id))
    customer = cust_result.scalars().first()
    if not customer or not customer.meta_user_id:
        raise HTTPException(400, "Cliente não tem ID Meta")

    sent = await send_message(ticket.meta_platform, customer.meta_user_id, message_text)
    if not sent:
        raise HTTPException(500, "Falha ao enviar mensagem")

    msg = Message(
        ticket_id=ticket.id,
        type="outbound",
        sender_name=user.name,
        sender_email=user.email,
        body_text=message_text,
        meta_platform=ticket.meta_platform,
    )
    db.add(msg)

    ticket.last_agent_response_at = datetime.now(timezone.utc)
    if not ticket.first_response_at:
        ticket.first_response_at = datetime.now(timezone.utc)

    await db.commit()
    return {"ok": True}


# ── Social moderation endpoints ──

@router.get("/moderation")
async def get_moderation_log(
    platform: str | None = None,
    action: str | None = None,
    sentiment: str | None = None,
    search: str | None = None,
    days: int | None = None,
    post_id: str | None = None,
    page: int = 1,
    per_page: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the social media moderation log with filters."""
    from datetime import datetime, timedelta, timezone

    # Order by comment timestamp (when user commented), fallback to created_at
    query = select(SocialComment).order_by(
        SocialComment.commented_at.desc().nullslast(),
        SocialComment.created_at.desc(),
    )

    # Filter by period (days)
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.where(
            (SocialComment.commented_at >= cutoff) | (
                SocialComment.commented_at.is_(None) & (SocialComment.created_at >= cutoff)
            )
        )

    if platform:
        query = query.where(SocialComment.platform == platform)
    if post_id:
        query = query.where(SocialComment.post_id == post_id)
    if action:
        query = query.where(SocialComment.ai_action == action)
    if sentiment:
        query = query.where(SocialComment.ai_sentiment == sentiment)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            SocialComment.text.ilike(search_filter) | SocialComment.author_name.ilike(search_filter)
        )

    # Count total
    from sqlalchemy import func as sql_func
    count_query = select(sql_func.count()).select_from(SocialComment)
    if days:
        count_query = count_query.where(
            (SocialComment.commented_at >= cutoff) | (
                SocialComment.commented_at.is_(None) & (SocialComment.created_at >= cutoff)
            )
        )
    if platform:
        count_query = count_query.where(SocialComment.platform == platform)
    if post_id:
        count_query = count_query.where(SocialComment.post_id == post_id)
    if action:
        count_query = count_query.where(SocialComment.ai_action == action)
    if sentiment:
        count_query = count_query.where(SocialComment.ai_sentiment == sentiment)
    if search:
        search_filter = f"%{search}%"
        count_query = count_query.where(
            SocialComment.text.ilike(search_filter) | SocialComment.author_name.ilike(search_filter)
        )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    comments = result.scalars().all()

    return {
        "comments": [
            {
                "id": c.id,
                "platform": c.platform,
                "comment_id": c.comment_id,
                "post_id": c.post_id,
                "author_name": c.author_name,
                "text": c.text,
                "ai_action": c.ai_action,
                "ai_reply": c.ai_reply,
                "ai_sentiment": c.ai_sentiment,
                "ai_category": c.ai_category,
                "ai_confidence": c.ai_confidence,
                "reply_sent": c.reply_sent,
                "was_hidden": c.was_hidden,
                "manually_reviewed": c.manually_reviewed,
                "reviewed_by": c.reviewed_by,
                "commented_at": c.commented_at.isoformat() if c.commented_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "post_caption": c.post_caption,
            }
            for c in comments
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/moderation/stats")
async def get_moderation_stats(
    days: int = 7,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get moderation statistics for the dashboard."""
    from sqlalchemy import func as sql_func
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    base = select(SocialComment).where(SocialComment.created_at >= cutoff)

    # Total comments
    total = await db.execute(select(sql_func.count()).select_from(SocialComment).where(SocialComment.created_at >= cutoff))
    total_count = total.scalar() or 0

    # By action
    action_result = await db.execute(
        select(SocialComment.ai_action, sql_func.count())
        .where(SocialComment.created_at >= cutoff)
        .group_by(SocialComment.ai_action)
    )
    by_action = {row[0]: row[1] for row in action_result.all()}

    # By sentiment
    sentiment_result = await db.execute(
        select(SocialComment.ai_sentiment, sql_func.count())
        .where(SocialComment.created_at >= cutoff)
        .group_by(SocialComment.ai_sentiment)
    )
    by_sentiment = {row[0]: row[1] for row in sentiment_result.all()}

    # By platform
    platform_result = await db.execute(
        select(SocialComment.platform, sql_func.count())
        .where(SocialComment.created_at >= cutoff)
        .group_by(SocialComment.platform)
    )
    by_platform = {row[0]: row[1] for row in platform_result.all()}

    # By category
    category_result = await db.execute(
        select(SocialComment.ai_category, sql_func.count())
        .where(SocialComment.created_at >= cutoff)
        .group_by(SocialComment.ai_category)
    )
    by_category = {row[0]: row[1] for row in category_result.all()}

    return {
        "total": total_count,
        "by_action": by_action,
        "by_sentiment": by_sentiment,
        "by_platform": by_platform,
        "by_category": by_category,
        "days": days,
    }


@router.post("/moderation/{comment_db_id}/review")
async def review_comment(
    comment_db_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark a moderated comment as manually reviewed."""
    result = await db.execute(select(SocialComment).where(SocialComment.id == comment_db_id))
    comment = result.scalars().first()
    if not comment:
        raise HTTPException(404, "Comentário não encontrado")

    comment.manually_reviewed = True
    comment.reviewed_by = user.name
    await db.commit()

    return {"ok": True}


@router.get("/moderation/posts-grouped")
async def get_posts_grouped(
    platform: str | None = None,
    days: int = 7,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get posts grouped from social_comments with aggregate data."""
    from sqlalchemy import func as sql_func

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Build time filter
    time_filter = (
        (SocialComment.commented_at >= cutoff) | (
            SocialComment.commented_at.is_(None) & (SocialComment.created_at >= cutoff)
        )
    )

    # Group by post_id to get counts and latest comment
    query = (
        select(
            SocialComment.post_id,
            SocialComment.platform,
            sql_func.max(SocialComment.post_caption).label("post_caption"),
            sql_func.count().label("comment_count"),
            sql_func.count().filter(SocialComment.ai_action == "pending").label("pending_count"),
            sql_func.max(SocialComment.commented_at).label("latest_commented_at"),
        )
        .where(time_filter)
        .where(SocialComment.post_id.isnot(None))
        .where(SocialComment.post_id != "")
        .group_by(SocialComment.post_id, SocialComment.platform)
        .order_by(sql_func.max(SocialComment.commented_at).desc().nullslast())
    )

    if platform:
        query = query.where(SocialComment.platform == platform)

    result = await db.execute(query)
    grouped = result.all()

    posts = []
    for row in grouped:
        # Get the latest comment for this post
        latest_q = (
            select(SocialComment)
            .where(SocialComment.post_id == row.post_id)
            .where(time_filter)
            .order_by(SocialComment.commented_at.desc().nullslast())
            .limit(1)
        )
        latest_result = await db.execute(latest_q)
        latest = latest_result.scalars().first()

        posts.append({
            "post_id": row.post_id,
            "platform": row.platform,
            "post_caption": row.post_caption,
            "comment_count": row.comment_count,
            "pending_count": row.pending_count,
            "latest_commented_at": row.latest_commented_at.isoformat() if row.latest_commented_at else None,
            "latest_comment": {
                "author_name": latest.author_name if latest else None,
                "text": latest.text if latest else None,
                "commented_at": latest.commented_at.isoformat() if latest and latest.commented_at else None,
            } if latest else None,
        })

    return {"posts": posts}


# ── New moderation action endpoints ──

@router.get("/posts")
async def get_posts(
    user: User = Depends(get_current_user),
):
    """Fetch recent posts from Facebook and Instagram."""
    posts = []

    if settings.META_PAGE_ID:
        fb_posts = await fetch_page_posts(settings.META_PAGE_ID)
        posts.extend(fb_posts)

    if settings.META_INSTAGRAM_ACCOUNT_ID:
        ig_posts = await fetch_instagram_media(settings.META_INSTAGRAM_ACCOUNT_ID)
        posts.extend(ig_posts)

    # Sort by created_at descending
    posts.sort(key=lambda p: p.get("created_at", ""), reverse=True)

    return {"posts": posts}


@router.post("/comments/sync")
async def sync_comments(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sync comments from Facebook/Instagram posts and process them with AI."""
    from datetime import datetime as dt, timedelta, timezone

    data = await request.json()
    sync_all = data.get("sync_all", False)
    post_ids = data.get("post_ids", [])
    platform_filter = data.get("platform")
    sync_days = data.get("days", 7)  # Only sync comments from last N days

    cutoff = dt.now(timezone.utc) - timedelta(days=sync_days)

    # Gather posts to sync (id, platform, caption)
    posts_to_sync = []

    if sync_all:
        if settings.META_PAGE_ID:
            fb_posts = await fetch_page_posts(settings.META_PAGE_ID)
            posts_to_sync.extend([
                (p["id"], "facebook", p.get("text", ""))
                for p in fb_posts
            ])
        if settings.META_INSTAGRAM_ACCOUNT_ID:
            ig_posts = await fetch_instagram_media(settings.META_INSTAGRAM_ACCOUNT_ID)
            posts_to_sync.extend([
                (p["id"], "instagram", p.get("text", ""))
                for p in ig_posts
            ])
    else:
        for pid in post_ids:
            posts_to_sync.append((pid, platform_filter or "instagram", ""))

    synced = 0
    skipped_old = 0
    errors = 0

    for post_id, platform, post_caption in posts_to_sync:
        try:
            comments = await fetch_comments_for_post(platform, post_id)
            for comment_data in comments:
                try:
                    # Filter out old comments
                    raw_ts = comment_data.get("timestamp")
                    if raw_ts:
                        try:
                            if isinstance(raw_ts, (int, float)):
                                comment_time = dt.fromtimestamp(raw_ts, tz=timezone.utc)
                            elif isinstance(raw_ts, str):
                                comment_time = dt.fromisoformat(raw_ts.replace("+0000", "+00:00"))
                            else:
                                comment_time = None
                            if comment_time and comment_time < cutoff:
                                skipped_old += 1
                                continue
                        except Exception:
                            pass

                    # Inject post_caption into comment_data
                    comment_data["post_caption"] = post_caption

                    await _process_comment(db, comment_data)
                    synced += 1
                except Exception as e:
                    logger.error(f"Error processing synced comment: {e}")
                    errors += 1
        except Exception as e:
            logger.error(f"Error fetching comments for post {post_id}: {e}")
            errors += 1

    return {
        "synced": synced,
        "skipped_old": skipped_old,
        "errors": errors,
        "total_posts": len(posts_to_sync),
        "days_filter": sync_days,
    }


@router.post("/moderation/{comment_db_id}/reply")
async def reply_to_moderation_comment(
    comment_db_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a manual reply to a moderated comment."""
    data = await request.json()
    reply_text = data.get("reply", "").strip()
    if not reply_text:
        raise HTTPException(400, "reply é obrigatório")

    result = await db.execute(select(SocialComment).where(SocialComment.id == comment_db_id))
    comment = result.scalars().first()
    if not comment:
        raise HTTPException(404, "Comentário não encontrado")

    sent = await reply_to_comment(comment.platform, comment.comment_id, reply_text)
    if not sent:
        raise HTTPException(500, "Falha ao enviar resposta via Meta API")

    comment.ai_reply = reply_text
    comment.reply_sent = True
    if comment.ai_action == "pending":
        comment.ai_action = "replied"
    await db.commit()

    return {"ok": True, "reply_sent": True}


@router.post("/moderation/{comment_db_id}/hide")
async def hide_moderation_comment(
    comment_db_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Hide or unhide a moderated comment."""
    data = await request.json()
    should_hide = data.get("hide", True)

    result = await db.execute(select(SocialComment).where(SocialComment.id == comment_db_id))
    comment = result.scalars().first()
    if not comment:
        raise HTTPException(404, "Comentário não encontrado")

    if should_hide:
        success = await hide_comment(comment.platform, comment.comment_id)
    else:
        success = await unhide_comment(comment.platform, comment.comment_id)

    if not success:
        action_label = "ocultar" if should_hide else "mostrar"
        raise HTTPException(500, f"Falha ao {action_label} comentário via Meta API")

    comment.was_hidden = should_hide
    await db.commit()

    return {"ok": True, "was_hidden": should_hide}


@router.post("/moderation/{comment_db_id}/reprocess")
async def reprocess_comment(
    comment_db_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Re-run AI moderation on a comment and optionally execute actions."""
    data = await request.json()
    execute_actions = data.get("execute_actions", False)

    result_row = await db.execute(select(SocialComment).where(SocialComment.id == comment_db_id))
    comment = result_row.scalars().first()
    if not comment:
        raise HTTPException(404, "Comentário não encontrado")

    # Re-run AI moderation
    ai_result = await moderate_comment(
        comment_text=comment.text,
        author_name=comment.author_name or "",
        post_caption=comment.post_caption or "",
        platform=comment.platform,
    )

    if not ai_result:
        raise HTTPException(500, "IA não retornou resultado")

    action = ai_result.get("action", "ignore")
    reply_text = ai_result.get("reply", "")

    # Update AI fields
    comment.ai_sentiment = ai_result.get("sentiment")
    comment.ai_category = ai_result.get("category")
    comment.ai_confidence = ai_result.get("confidence")
    comment.ai_reply = reply_text if reply_text else comment.ai_reply

    # Map action
    if action == "hide_reply":
        comment.ai_action = "hidden_replied"
    elif action == "hide":
        comment.ai_action = "hidden"
    elif action == "reply":
        comment.ai_action = "replied"
    else:
        comment.ai_action = "ignored"

    # Execute actions if requested
    if execute_actions:
        if action in ("hide", "hide_reply"):
            comment.was_hidden = await hide_comment(comment.platform, comment.comment_id)
        if action in ("reply", "hide_reply") and reply_text:
            sent = await reply_to_comment(comment.platform, comment.comment_id, reply_text)
            comment.reply_sent = sent is not None

    await db.commit()

    return {
        "ok": True,
        "ai_action": comment.ai_action,
        "ai_sentiment": comment.ai_sentiment,
        "ai_category": comment.ai_category,
        "ai_confidence": comment.ai_confidence,
        "ai_reply": comment.ai_reply,
    }


@router.get("/moderation/settings")
async def get_moderation_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current moderation settings."""
    result = await db.execute(text("SELECT key, value FROM moderation_settings"))
    rows = result.all()
    settings_dict = {row[0]: row[1] for row in rows}
    return {
        "ai_enabled": settings_dict.get("ai_enabled", "true") == "true",
        "auto_reply": settings_dict.get("auto_reply", "true") == "true",
        "auto_hide": settings_dict.get("auto_hide", "true") == "true",
    }


@router.post("/moderation/settings")
async def update_moderation_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update moderation settings (ai_enabled, auto_reply, auto_hide)."""
    data = await request.json()
    allowed_keys = {"ai_enabled", "auto_reply", "auto_hide"}
    now = datetime.now(timezone.utc).isoformat()

    for key, value in data.items():
        if key not in allowed_keys:
            continue
        str_value = "true" if value else "false"
        await db.execute(
            text(
                "INSERT INTO moderation_settings (key, value, updated_at, updated_by) "
                "VALUES (:key, :value, :updated_at, :updated_by) "
                "ON CONFLICT (key) DO UPDATE SET value = :value, updated_at = :updated_at, updated_by = :updated_by"
            ),
            {"key": key, "value": str_value, "updated_at": now, "updated_by": user.name},
        )

    await db.commit()

    return await get_moderation_settings(user=user, db=db)
