import asyncio
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text, select
from pathlib import Path

from app.core.config import settings
from app.core.database import engine, Base, async_session
from app.api import auth, tickets, inboxes, dashboard, kb, slack, gmail, ai, reports, export, ws, tracking, shopify, media, ecommerce, catalog, gamification, rewards, meta, customers, agent_analysis, chat, chatbot
from app.api.webhooks import whatsapp as wh_whatsapp, meta_dm as wh_meta_dm, tiktok as wh_tiktok
from app.services.seed import seed_database
from app.services.ticket_number import init_ticket_sequence
from app.models.csat import CSATRating  # noqa: ensure table created
from app.models.social_comment import SocialComment  # noqa: ensure table created
from app.models.reward import Reward, RewardClaim  # noqa: ensure table created
from app.models.agent_report import AgentReport  # noqa: ensure table created

escalation_logger = logging.getLogger("escalation")

# Email fetch health tracking
_email_health = {
    "last_success": None,        # timestamp of last successful fetch
    "last_check": None,          # timestamp of last check attempt
    "consecutive_failures": 0,   # number of consecutive failed cycles
    "total_processed": 0,        # total emails processed since startup
    "total_errors": 0,           # total individual email errors since startup
    "last_error": None,          # last error message
    "slack_alerted": False,      # whether we already sent a Slack alert for current failure streak
}


async def _run_escalation_loop():
    """Background task: check escalations every 5 minutes."""
    from app.services.escalation_service import check_and_escalate
    while True:
        try:
            async with async_session() as session:
                result = await check_and_escalate(session)
                if result["escalated"] or result["sla_breached"]:
                    escalation_logger.info(
                        f"Escalation check: {result['escalated']} escalated, {result['sla_breached']} SLA breached"
                    )
        except Exception as e:
            escalation_logger.error(f"Escalation check failed: {e}")
        await asyncio.sleep(300)  # 5 minutes


async def _run_scheduled_email_loop():
    """Background task: send scheduled emails every 30 seconds."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.ticket import Ticket
    from app.models.message import Message
    from app.services.gmail_service import send_email

    logger = logging.getLogger("scheduled_email")
    await asyncio.sleep(15)  # Wait for startup

    while True:
        try:
            async with async_session() as db:
                now = datetime.now(timezone.utc)
                result = await db.execute(
                    select(Message).where(
                        Message.is_scheduled == True,
                        Message.scheduled_at <= now,
                    )
                )
                scheduled_msgs = result.scalars().all()

                for msg in scheduled_msgs:
                    try:
                        # Get the ticket with customer eagerly loaded
                        ticket_result = await db.execute(
                            select(Ticket)
                            .where(Ticket.id == msg.ticket_id)
                            .options(joinedload(Ticket.customer))
                        )
                        ticket = ticket_result.scalar_one_or_none()
                        if not ticket:
                            msg.is_scheduled = False
                            continue

                        # Give up after 1 hour of retries
                        from datetime import timedelta as td
                        if msg.scheduled_at and (now - msg.scheduled_at) > td(hours=1):
                            msg.is_scheduled = False
                            logger.error(f"Scheduled email {msg.id} gave up after 1h of retries")
                            continue

                        sent = False
                        if ticket.source == "gmail" and ticket.customer:
                            # Find gmail thread info
                            thread_result = await db.execute(
                                select(Message).where(
                                    Message.ticket_id == ticket.id,
                                    Message.gmail_thread_id.isnot(None),
                                ).limit(1)
                            )
                            first_msg = thread_result.scalars().first()

                            cc_list = [e.strip() for e in msg.cc.split(",") if e.strip()] if msg.cc else None
                            bcc_list = [e.strip() for e in msg.bcc.split(",") if e.strip()] if msg.bcc else None

                            response = send_email(
                                to=ticket.customer.email,
                                subject=f"Re: {ticket.subject}",
                                body_text=msg.body_text or "",
                                thread_id=first_msg.gmail_thread_id if first_msg else None,
                                in_reply_to=first_msg.gmail_message_id if first_msg else None,
                                cc=cc_list,
                                bcc=bcc_list,
                                attachments=msg.attachments if msg.attachments else None,
                            )
                            if response:
                                msg.gmail_message_id = response.get("id")
                                msg.gmail_thread_id = response.get("threadId")
                                sent = True
                            else:
                                logger.warning(f"Scheduled email send failed for message {msg.id}, will retry")
                        else:
                            sent = True  # Non-Gmail tickets: just mark as sent

                        if sent:
                            msg.is_scheduled = False
                            logger.info(f"Scheduled email sent for message {msg.id} on ticket {ticket.id}")
                    except Exception as e:
                        logger.error(f"Failed to send scheduled message {msg.id}: {e}")

                await db.commit()
        except Exception as e:
            logger.error(f"Scheduled email loop error: {e}")
        await asyncio.sleep(30)  # Check every 30 seconds


async def _run_email_fetch_loop():
    """Background task: fetch new Gmail emails every 60 seconds."""
    from datetime import datetime, timezone, timedelta
    from email.utils import parsedate_to_datetime
    from sqlalchemy import select, func
    from app.models.ticket import Ticket
    from app.models.message import Message
    from app.models.customer import Customer
    from app.services.gmail_service import fetch_new_emails, mark_as_read
    from app.services.protocol_service import assign_protocol

    logger = logging.getLogger("email_fetch")

    # Wait 30s on startup for everything to initialize
    await asyncio.sleep(30)

    def _parse_email_date(date_str):
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            return None

    while True:
        try:
            _email_health["last_check"] = datetime.now(timezone.utc).isoformat()
            emails = await asyncio.to_thread(fetch_new_emails, max_results=20)
            if emails:
                created = 0
                updated = 0
                errors = 0
                for email_data in emails:
                    gmail_thread_id = email_data.get("thread_id")
                    gmail_message_id = email_data.get("gmail_id")
                    try:
                        async with async_session() as db:
                            # Check if already processed
                            existing_msg = await db.execute(
                                select(Message).where(Message.gmail_message_id == gmail_message_id)
                            )
                            if existing_msg.scalars().first():
                                # Already in DB, just ensure it's marked as read
                                await asyncio.to_thread(mark_as_read, gmail_message_id)
                                continue

                            # Check existing ticket for this thread
                            existing_ticket = None
                            if gmail_thread_id:
                                result = await db.execute(
                                    select(Ticket).join(Message).where(Message.gmail_thread_id == gmail_thread_id)
                                )
                                existing_ticket = result.scalars().first()

                            # Match by In-Reply-To header
                            if not existing_ticket:
                                in_reply_to = email_data.get("in_reply_to")
                                if in_reply_to:
                                    ref_result = await db.execute(
                                        select(Message).where(Message.email_message_id == in_reply_to)
                                    )
                                    ref_msg = ref_result.scalar_one_or_none()
                                    if ref_msg:
                                        ticket_result = await db.execute(
                                            select(Ticket).where(Ticket.id == ref_msg.ticket_id)
                                        )
                                        existing_ticket = ticket_result.scalar_one_or_none()

                            # Fallback: find open ticket from same customer
                            if not existing_ticket:
                                cust_result = await db.execute(
                                    select(Customer).where(Customer.email == email_data["from_email"])
                                )
                                cust = cust_result.scalars().first()
                                if cust:
                                    open_result = await db.execute(
                                        select(Ticket).where(
                                            Ticket.customer_id == cust.id,
                                            Ticket.status.notin_(["resolved", "closed", "archived", "merged"]),
                                        ).order_by(Ticket.updated_at.desc())
                                    )
                                    existing_ticket = open_result.scalars().first()

                            if existing_ticket:
                                msg = Message(
                                    ticket_id=existing_ticket.id,
                                    type="inbound",
                                    sender_name=email_data["from_name"],
                                    sender_email=email_data["from_email"],
                                    body_text=email_data["body_text"],
                                    body_html=email_data.get("body_html"),
                                    gmail_message_id=gmail_message_id,
                                    gmail_thread_id=gmail_thread_id,
                                    email_message_id=email_data.get("message_id"),
                                    email_references=email_data.get("references"),
                                )
                                db.add(msg)
                                was_resolved = existing_ticket.status == "resolved"
                                was_closed = existing_ticket.status == "closed"
                                if existing_ticket.status in ("resolved", "closed", "waiting", "waiting_supplier", "waiting_resend"):
                                    existing_ticket.status = "open"
                                if was_resolved or was_closed:
                                    existing_ticket.resolved_at = None
                                now = datetime.now(timezone.utc)
                                from app.core.sla_config import get_sla_for_ticket
                                sla = get_sla_for_ticket(existing_ticket.category, existing_ticket.priority)
                                existing_ticket.sla_deadline = now + timedelta(hours=sla["resolution_hours"])
                                existing_ticket.sla_response_deadline = now + timedelta(hours=sla["response_hours"])
                                existing_ticket.sla_breached = False
                                existing_ticket.first_response_at = None
                                existing_ticket.updated_at = now
                                await db.commit()
                                updated += 1
                            else:
                                # Find or create customer
                                cust_result = await db.execute(select(Customer).where(Customer.email == email_data["from_email"]))
                                customer = cust_result.scalars().first()
                                if not customer:
                                    customer = Customer(name=email_data["from_name"], email=email_data["from_email"])
                                    db.add(customer)
                                    await db.flush()
                                else:
                                    customer.total_tickets += 1
                                    if customer.total_tickets > 2:
                                        customer.is_repeat = True

                                from app.services.ticket_number import get_next_ticket_number
                                next_num = await get_next_ticket_number(db)
                                sla_deadline = datetime.now(timezone.utc) + timedelta(hours=settings.SLA_MEDIUM_HOURS)
                                email_date = _parse_email_date(email_data.get("date", ""))

                                ticket = Ticket(
                                    number=next_num,
                                    subject=email_data["subject"][:500],
                                    status="open",
                                    priority="medium",
                                    customer_id=customer.id,
                                    source="gmail",
                                    sla_deadline=sla_deadline,
                                    received_at=email_date or datetime.now(timezone.utc),
                                )
                                db.add(ticket)
                                await db.flush()

                                msg = Message(
                                    ticket_id=ticket.id,
                                    type="inbound",
                                    sender_name=email_data["from_name"],
                                    sender_email=email_data["from_email"],
                                    body_text=email_data["body_text"],
                                    body_html=email_data.get("body_html"),
                                    gmail_message_id=gmail_message_id,
                                    gmail_thread_id=gmail_thread_id,
                                )
                                db.add(msg)

                                # AI Triage
                                try:
                                    from app.services.ai_service import triage_ticket as ai_triage
                                    triage = await ai_triage(
                                        subject=email_data["subject"],
                                        body=email_data["body_text"][:2000],
                                        customer_name=email_data["from_name"],
                                        is_repeat=customer.is_repeat,
                                    )
                                    if triage:
                                        if triage.get("category"):
                                            ticket.ai_category = triage["category"]
                                            ticket.category = triage["category"]
                                        if triage.get("priority"):
                                            ticket.priority = triage["priority"]
                                            hours_map = {"urgent": settings.SLA_URGENT_HOURS, "high": settings.SLA_HIGH_HOURS, "medium": settings.SLA_MEDIUM_HOURS, "low": settings.SLA_LOW_HOURS}
                                            ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=hours_map.get(triage["priority"], 24))
                                        if triage.get("sentiment"):
                                            ticket.sentiment = triage["sentiment"]
                                        if triage.get("legal_risk") is not None:
                                            ticket.legal_risk = triage["legal_risk"]
                                        if triage.get("tags"):
                                            ticket.tags = triage["tags"]
                                        if triage.get("confidence"):
                                            ticket.ai_confidence = triage["confidence"]
                                except Exception as e:
                                    logger.warning(f"AI triage skipped: {e}")

                                try:
                                    await assign_protocol(ticket, db)
                                except Exception as e:
                                    logger.warning(f"Protocol assign warning: {e}")

                                await db.commit()
                                created += 1

                            # Only mark as read AFTER successful commit
                            await asyncio.to_thread(mark_as_read, gmail_message_id)

                    except Exception as e:
                        errors += 1
                        _email_health["total_errors"] += 1
                        _email_health["last_error"] = f"{email_data.get('from_email', '?')}: {str(e)[:200]}"
                        logger.error(f"Email fetch: failed to process {gmail_message_id} from {email_data.get('from_email', '?')}: {e}")
                        continue  # Continue processing remaining emails

                if created or updated:
                    logger.warning(f"Email fetch: {created} created, {updated} updated")
                    _email_health["total_processed"] += created + updated

                # Send Slack alert if individual emails failed
                if errors > 0:
                    try:
                        from app.services.slack_service import send_slack_message
                        channel = settings.SLACK_SUPPORT_CHANNEL
                        if channel:
                            await send_slack_message(
                                channel,
                                f":warning: *Email Fetch: {errors} email(s) falharam ao processar*\n"
                                f"Emails processados com sucesso: {created + updated}\n"
                                f"Ultimo erro: `{_email_health['last_error']}`"
                            )
                    except Exception as slack_err:
                        logger.warning(f"Slack alert for email errors failed: {slack_err}")

            # Cycle succeeded
            _email_health["last_success"] = datetime.now(timezone.utc).isoformat()
            _email_health["consecutive_failures"] = 0
            _email_health["slack_alerted"] = False

        except Exception as e:
            _email_health["consecutive_failures"] += 1
            _email_health["last_error"] = str(e)[:200]
            logger.error(f"Email fetch loop error: {e}")

            # Alert on 3+ consecutive failures
            if _email_health["consecutive_failures"] >= 3 and not _email_health["slack_alerted"]:
                _email_health["slack_alerted"] = True
                try:
                    from app.services.slack_service import send_slack_message
                    channel = settings.SLACK_SUPPORT_CHANNEL
                    if channel:
                        await send_slack_message(
                            channel,
                            f":rotating_light: *ALERTA: Email fetch falhou {_email_health['consecutive_failures']}x seguidas!*\n"
                            f"Emails NAO estao sendo recebidos no helpdesk.\n"
                            f"Erro: `{str(e)[:200]}`\n"
                            f"Ultima execucao OK: {_email_health['last_success'] or 'nunca'}"
                        )
                except Exception as slack_err:
                    logger.warning(f"Slack critical alert failed: {slack_err}")

        await asyncio.sleep(60)  # 60 seconds


async def _run_weekly_analysis():
    """Background task: generate weekly agent analysis reports every Sunday 23h UTC."""
    from datetime import datetime, timezone, timedelta
    from app.services.agent_analysis_service import (
        calculate_quantitative_metrics, generate_ai_analysis, fetch_agent_messages,
    )
    from app.models.user import User

    wlogger = logging.getLogger("weekly_analysis")
    await asyncio.sleep(60)

    last_run_week = None
    while True:
        try:
            now = datetime.now(timezone.utc)
            current_week = now.isocalendar()[1]
            if now.weekday() == 6 and now.hour == 23 and last_run_week != current_week:
                wlogger.info("Starting weekly agent analysis...")
                async with async_session() as db:
                    agents = await db.execute(select(User).where(User.is_active == True))
                    for agent in agents.scalars().all():
                        try:
                            period_end = now
                            period_start = now - timedelta(days=7)
                            metrics = await calculate_quantitative_metrics(db, agent.id, period_start, period_end)
                            messages = await fetch_agent_messages(db, agent.id, period_start, period_end, sample_size=50)
                            ai_result = {}
                            if messages:
                                ai_result = await generate_ai_analysis(agent.name, messages)
                            report = AgentReport(
                                agent_id=agent.id,
                                period_start=period_start,
                                period_end=period_end,
                                sample_size=50,
                                report_type="weekly_auto",
                                quantitative_metrics=metrics,
                                ai_analysis=ai_result.get("summary", ""),
                                ai_scores=ai_result if not ai_result.get("error") else {"error": ai_result["error"]},
                            )
                            db.add(report)
                            await db.commit()
                            wlogger.info(f"Weekly report generated for {agent.name}")
                        except Exception as e:
                            wlogger.error(f"Weekly analysis failed for {agent.name}: {e}")
                            await db.rollback()
                last_run_week = current_week
                wlogger.info("Weekly agent analysis complete")
        except Exception as e:
            wlogger.error(f"Weekly analysis loop error: {e}")
        await asyncio.sleep(3600)


async def _run_chat_inactivity_loop():
    """Background task: auto-close chat conversations inactive for 15+ minutes."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, and_
    from app.models.conversation import Conversation
    from app.models.chat_message import ChatMessage
    from app.models.channel_identity import ChannelIdentity
    from app.services.channels.dispatcher import dispatcher

    ilogger = logging.getLogger("chat_inactivity")
    await asyncio.sleep(60)  # Wait for startup

    while True:
        try:
            async with AsyncSessionLocal() as db:
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)

                # Find open conversations with last activity > 15min ago
                result = await db.execute(
                    select(Conversation).where(
                        and_(
                            Conversation.status == "open",
                            Conversation.channel.in_(["whatsapp", "instagram", "facebook"]),
                            Conversation.last_message_at < cutoff,
                            Conversation.last_message_at.isnot(None),
                        )
                    )
                )
                stale_convs = list(result.scalars().all())

                for conv in stale_convs:
                    try:
                        # Skip if pending observation (has its own timer)
                        meta = conv.metadata_ if isinstance(conv.metadata_, dict) else {}
                        if meta.get("pending_observation") or meta.get("pending_escalation"):
                            continue

                        msg = (
                            "Como não houve novas mensagens, vou encerrar este atendimento.\n\n"
                            "Se precisar de algo mais, é só mandar um *oi* a qualquer momento! "
                            "Estaremos aqui pra te ajudar."
                        )

                        bot_msg = ChatMessage(
                            conversation_id=conv.id,
                            sender_type="bot",
                            sender_id=None,
                            content_type="text",
                            content=msg,
                            created_at=datetime.now(timezone.utc),
                        )
                        db.add(bot_msg)
                        conv.status = "resolved"
                        conv.last_message_at = datetime.now(timezone.utc)

                        # Send via channel
                        ci_result = await db.execute(
                            select(ChannelIdentity).where(
                                ChannelIdentity.customer_id == conv.customer_id,
                                ChannelIdentity.channel == conv.channel,
                            )
                        )
                        ci = ci_result.scalar_one_or_none()
                        if ci:
                            kwargs = {}
                            phone_number_id = meta.get("phone_number_id")
                            if phone_number_id:
                                kwargs["phone_number_id"] = phone_number_id
                            try:
                                await dispatcher.send(conv.channel, ci.channel_id, msg, **kwargs)
                            except Exception as e:
                                ilogger.warning("Failed to send inactivity msg for conv %s: %s", conv.id, e)

                        ilogger.info("Auto-closed inactive conversation %s (%s)", conv.id, conv.channel)
                    except Exception as e:
                        ilogger.error("Error closing conv %s: %s", conv.id, e)

                if stale_convs:
                    await db.commit()
                    ilogger.info("Auto-closed %d inactive conversations", len(stale_convs))

        except Exception as e:
            ilogger.error("Chat inactivity loop error: %s", e)

        await asyncio.sleep(120)  # Check every 2 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Add new columns if they don't exist (schema migrations)
    async with engine.begin() as conn:
        migration_sqls = [
            # Slack fields
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS slack_channel_id VARCHAR(100)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS slack_thread_ts VARCHAR(50)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'web'",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS slack_ts VARCHAR(50)",
            "CREATE INDEX IF NOT EXISTS ix_tickets_slack_thread_ts ON tickets (slack_thread_ts)",
            # New status/SLA fields (convert enum to varchar if needed)
            "ALTER TABLE tickets ALTER COLUMN status TYPE VARCHAR(50) USING status::VARCHAR(50)",
            "ALTER TABLE tickets ALTER COLUMN priority TYPE VARCHAR(20) USING priority::VARCHAR(20)",
            "ALTER TABLE tickets ALTER COLUMN sentiment TYPE VARCHAR(20) USING sentiment::VARCHAR(20)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS sla_response_deadline TIMESTAMPTZ",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_summary TEXT",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS supplier_notes TEXT",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMPTZ",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS escalation_reason VARCHAR(255)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS last_agent_response_at TIMESTAMPTZ",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS tracking_code VARCHAR(100)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS tracking_status VARCHAR(100)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS tracking_data JSONB",
            # Customer blacklist fields
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS is_blacklisted BOOLEAN DEFAULT FALSE",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS blacklist_reason VARCHAR(500)",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS blacklisted_at TIMESTAMPTZ",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS chargeback_count INTEGER DEFAULT 0",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS resend_count INTEGER DEFAULT 0",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS abuse_flags TEXT[]",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS notes TEXT",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS tags TEXT[]",
            # User specialty/routing fields (RF-013)
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS specialty VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS max_tickets INTEGER DEFAULT 20",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_signature VARCHAR(2000)",
            # Email received_at
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ",
            "CREATE INDEX IF NOT EXISTS ix_tickets_received_at ON tickets (received_at)",
            # Protocol & internal notes
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS protocol VARCHAR(30)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS protocol_sent BOOLEAN DEFAULT FALSE",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS internal_notes TEXT",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_tickets_protocol ON tickets (protocol) WHERE protocol IS NOT NULL",
            # Macro actions field
            "ALTER TABLE macros ADD COLUMN IF NOT EXISTS actions JSONB",
            # Media items table
            """CREATE TABLE IF NOT EXISTS media_items (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                drive_file_id VARCHAR(255) NOT NULL,
                drive_url TEXT NOT NULL,
                thumbnail_url TEXT,
                mime_type VARCHAR(100),
                category VARCHAR(50),
                source_type VARCHAR(20) DEFAULT 'drive',
                is_active BOOLEAN DEFAULT TRUE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            # Add source_type column if missing
            "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'drive'",
            # Rewards system
            """CREATE TABLE IF NOT EXISTS rewards (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT DEFAULT '',
                icon VARCHAR(50) DEFAULT 'fa-gift',
                color VARCHAR(20) DEFAULT '#a855f7',
                points_required INTEGER DEFAULT 100,
                category VARCHAR(50) DEFAULT 'geral',
                is_active BOOLEAN DEFAULT TRUE,
                max_claims INTEGER DEFAULT 0,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            # (tracking seed data removed - was causing bind parameter errors in production)
            """CREATE TABLE IF NOT EXISTS reward_claims (
                id VARCHAR(36) PRIMARY KEY,
                reward_id VARCHAR(36) REFERENCES rewards(id) ON DELETE CASCADE,
                agent_id VARCHAR(36),
                agent_name VARCHAR(255),
                points_spent INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending',
                approved_by VARCHAR(36),
                approved_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            # Meta integration fields
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS meta_conversation_id VARCHAR(100)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS meta_platform VARCHAR(20)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_auto_mode BOOLEAN DEFAULT TRUE",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_paused_by VARCHAR(36)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_paused_at TIMESTAMPTZ",
            "CREATE INDEX IF NOT EXISTS ix_tickets_meta_conversation_id ON tickets (meta_conversation_id)",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS meta_message_id VARCHAR(100)",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS meta_platform VARCHAR(20)",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS meta_user_id VARCHAR(100)",
            "CREATE INDEX IF NOT EXISTS ix_customers_meta_user_id ON customers (meta_user_id)",
            # Social comments moderation table
            """CREATE TABLE IF NOT EXISTS social_comments (
                id VARCHAR(36) PRIMARY KEY,
                platform VARCHAR(20) NOT NULL,
                comment_id VARCHAR(100) UNIQUE NOT NULL,
                post_id VARCHAR(100),
                parent_comment_id VARCHAR(100),
                author_id VARCHAR(100) NOT NULL,
                author_name VARCHAR(255),
                text TEXT NOT NULL,
                post_caption TEXT,
                ai_action VARCHAR(30) NOT NULL,
                ai_reply TEXT,
                ai_sentiment VARCHAR(20),
                ai_category VARCHAR(50),
                ai_confidence FLOAT,
                reply_sent BOOLEAN DEFAULT FALSE,
                was_hidden BOOLEAN DEFAULT FALSE,
                manually_reviewed BOOLEAN DEFAULT FALSE,
                reviewed_by VARCHAR(255),
                commented_at TIMESTAMPTZ,
                moderated_at TIMESTAMPTZ DEFAULT NOW(),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            "CREATE INDEX IF NOT EXISTS ix_social_comments_platform ON social_comments (platform)",
            "CREATE INDEX IF NOT EXISTS ix_social_comments_comment_id ON social_comments (comment_id)",
            "CREATE INDEX IF NOT EXISTS ix_social_comments_ai_action ON social_comments (ai_action)",
            "CREATE INDEX IF NOT EXISTS ix_social_comments_post_id ON social_comments (post_id)",
            # Moderation settings (key/value for AI toggle, auto_reply, auto_hide)
            """CREATE TABLE IF NOT EXISTS moderation_settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                updated_by VARCHAR(255)
            )""",
            # Seed default moderation settings
            """INSERT INTO moderation_settings (key, value) VALUES
                ('ai_enabled', 'true'),
                ('auto_reply', 'true'),
                ('auto_hide', 'true')
            ON CONFLICT (key) DO NOTHING""",
            # Merge support migrations
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS merged_into_id UUID",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS alternate_emails VARCHAR[]",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS merged_into_id UUID",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS email_message_id VARCHAR(255)",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS email_message_id VARCHAR(255)",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS email_references TEXT",
            "CREATE INDEX IF NOT EXISTS ix_customers_merged_into_id ON customers(merged_into_id)",
            "CREATE INDEX IF NOT EXISTS ix_tickets_merged_into_id ON tickets(merged_into_id)",
            "CREATE INDEX IF NOT EXISTS ix_tickets_email_message_id ON tickets(email_message_id)",
            # CC/BCC and scheduled send on messages
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS cc TEXT",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS bcc TEXT",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_scheduled BOOLEAN DEFAULT FALSE",
            # Performance: composite indexes for common query patterns
            "CREATE INDEX IF NOT EXISTS idx_tickets_status_created ON tickets(status, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_agent_created ON tickets(assigned_to, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_source_created ON tickets(source, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_sla ON tickets(sla_deadline) WHERE sla_breached = FALSE",
            "CREATE INDEX IF NOT EXISTS idx_messages_type_created ON messages(type, created_at DESC)",
            # Chat integration — Customer fields
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS shopify_data JSONB",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS external_id VARCHAR(100)",
            "CREATE INDEX IF NOT EXISTS ix_customers_external_id ON customers(external_id)",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS total_conversations INTEGER DEFAULT 0",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS total_value FLOAT DEFAULT 0.0",
            "ALTER TABLE customers ALTER COLUMN email DROP NOT NULL",
            # Chat integration — User fields
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(10) DEFAULT 'offline'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS max_concurrent_chats INTEGER DEFAULT 10",
            # Chat integration — Conversations table
            """CREATE TABLE IF NOT EXISTS conversations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                number SERIAL,
                customer_id UUID NOT NULL REFERENCES customers(id),
                assigned_to UUID REFERENCES users(id),
                channel VARCHAR(20) NOT NULL,
                status VARCHAR(20) DEFAULT 'open',
                priority VARCHAR(10) DEFAULT 'normal',
                handler VARCHAR(10) DEFAULT 'chatbot',
                ai_enabled BOOLEAN DEFAULT TRUE,
                ai_attempts INTEGER DEFAULT 0,
                subject VARCHAR(500),
                tags JSONB,
                last_message_at TIMESTAMPTZ,
                metadata JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            "CREATE INDEX IF NOT EXISTS ix_conversations_customer_id ON conversations(customer_id)",
            "CREATE INDEX IF NOT EXISTS ix_conversations_assigned_to ON conversations(assigned_to)",
            "CREATE INDEX IF NOT EXISTS ix_conversations_channel ON conversations(channel)",
            "CREATE INDEX IF NOT EXISTS ix_conversations_status ON conversations(status)",
            # Chat integration — Chat messages table
            """CREATE TABLE IF NOT EXISTS chat_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                conversation_id UUID NOT NULL REFERENCES conversations(id),
                sender_type VARCHAR(10) NOT NULL,
                sender_id UUID,
                content_type VARCHAR(20) DEFAULT 'text',
                content TEXT NOT NULL,
                channel_message_id VARCHAR(255),
                delivered_at TIMESTAMPTZ,
                read_at TIMESTAMPTZ,
                metadata JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            "CREATE INDEX IF NOT EXISTS ix_chat_messages_conversation_id ON chat_messages(conversation_id)",
            # Chat integration — Channel identities table
            """CREATE TABLE IF NOT EXISTS channel_identities (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_id UUID NOT NULL REFERENCES customers(id),
                channel VARCHAR(20) NOT NULL,
                channel_id VARCHAR(255) NOT NULL,
                metadata JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            "CREATE INDEX IF NOT EXISTS ix_channel_identities_customer_id ON channel_identities(customer_id)",
            "CREATE INDEX IF NOT EXISTS ix_channel_identities_channel_id ON channel_identities(channel_id)",
            # Chat integration — Chatbot flows table
            """CREATE TABLE IF NOT EXISTS chatbot_flows (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                trigger_type VARCHAR(20) NOT NULL,
                trigger_config JSONB,
                steps JSONB,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS avatar_url TEXT",
        ]
        migration_logger = logging.getLogger("migrations")
        for sql in migration_sqls:
            try:
                await conn.execute(text(sql))
            except Exception as e:
                # Log but continue - column may already exist
                migration_logger.warning(f"Migration skipped: {str(e)[:200]}")

    # Initialize ticket number sequence (atomic generation)
    async with engine.begin() as conn:
        await init_ticket_sequence(conn)

    # Drop old enum types if they exist (after varchar conversion)
    async with engine.begin() as conn:
        for enum_name in ["ticket_status", "ticket_priority", "sentiment_type"]:
            try:
                await conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
            except Exception as e:
                migration_logger.warning(f"Enum drop skipped ({enum_name}): {e}")

    # Seed demo data (only in development)
    if settings.ENVIRONMENT != "production":
        async with async_session() as session:
            await seed_database(session)

    # Register channel adapters for chat dispatcher
    from app.services.channels.dispatcher import dispatcher
    from app.services.channels.whatsapp_adapter import WhatsAppAdapter
    from app.services.channels.instagram_adapter import InstagramAdapter
    from app.services.channels.facebook_adapter import FacebookAdapter
    from app.services.channels.tiktok_adapter import TikTokAdapter
    dispatcher.register(WhatsAppAdapter())
    dispatcher.register(InstagramAdapter())
    dispatcher.register(FacebookAdapter())
    dispatcher.register(TikTokAdapter())

    # Start background tasks
    escalation_task = asyncio.create_task(_run_escalation_loop())
    email_fetch_task = asyncio.create_task(_run_email_fetch_loop())
    scheduled_email_task = asyncio.create_task(_run_scheduled_email_loop())
    weekly_analysis_task = asyncio.create_task(_run_weekly_analysis())
    chat_inactivity_task = asyncio.create_task(_run_chat_inactivity_loop())

    yield

    escalation_task.cancel()
    email_fetch_task.cancel()
    scheduled_email_task.cancel()
    weekly_analysis_task.cancel()
    chat_inactivity_task.cancel()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(inboxes.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(kb.router, prefix="/api")
app.include_router(slack.router, prefix="/api")
app.include_router(gmail.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(shopify.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(ecommerce.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(gamification.router, prefix="/api")
app.include_router(rewards.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(agent_analysis.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")
app.include_router(wh_whatsapp.router)
app.include_router(wh_meta_dm.router)
app.include_router(wh_tiktok.router)
app.include_router(ws.router)

# Public CSAT rating page (no auth required - customer clicks email link)
from app.api import csat as csat_public
app.include_router(csat_public.router, prefix="/api")

# Serve uploaded attachments
_uploads_dir = Path("uploads")
_uploads_dir.mkdir(exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/api/public/invoice-pdf")
async def public_invoice_pdf(order_number: str, token: str = ""):
    """Public proxy for NF PDF — used by WhatsApp Cloud API to fetch document.
    Simple token check to prevent open access."""
    import httpx
    import os
    from fastapi.responses import Response

    expected_token = os.environ.get("NF_PDF_TOKEN", "carbon-nf-2026")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    nf_host = os.environ.get("CARBON_NF_URL", "http://172.17.0.1:8002")
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                f"{nf_host}/api/internal/invoice-pdf",
                params={"order_number": order_number},
                timeout=30,
            )
            if resp.status_code == 404:
                raise HTTPException(404, "NF não encontrada")
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "application/pdf")
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'inline; filename="NF_{order_number}.pdf"',
                    "Cache-Control": "public, max-age=86400",
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Erro ao buscar PDF: {e}")


@app.get("/api/health")
async def health():
    from app.services.ai_service import is_credits_exhausted
    return {
        "status": "ok",
        "service": "Carbon Expert Hub",
        "email_fetch": {
            "last_success": _email_health["last_success"],
            "last_check": _email_health["last_check"],
            "consecutive_failures": _email_health["consecutive_failures"],
            "total_processed": _email_health["total_processed"],
            "total_errors": _email_health["total_errors"],
            "healthy": _email_health["consecutive_failures"] < 3,
        },
        "ai": {
            "credits_exhausted": is_credits_exhausted(),
        },
    }
