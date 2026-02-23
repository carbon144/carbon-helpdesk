import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base, async_session
from app.api import auth, tickets, inboxes, dashboard, kb, slack, gmail, ai, reports, export, ws, tracking, shopify, media, ecommerce, catalog, gamification, rewards, meta
from app.services.seed import seed_database
from app.models.csat import CSATRating  # noqa: ensure table created
from app.models.social_comment import SocialComment  # noqa: ensure table created

escalation_logger = logging.getLogger("escalation")


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
            emails = await asyncio.to_thread(fetch_new_emails, max_results=20)
            if emails:
                async with async_session() as db:
                    created = 0
                    updated = 0
                    for email_data in emails:
                        gmail_thread_id = email_data.get("thread_id")
                        gmail_message_id = email_data.get("gmail_id")

                        # Check if already processed
                        existing_msg = await db.execute(
                            select(Message).where(Message.gmail_message_id == gmail_message_id)
                        )
                        if existing_msg.scalars().first():
                            continue

                        # Check existing ticket for this thread
                        existing_ticket = None
                        if gmail_thread_id:
                            result = await db.execute(
                                select(Ticket).join(Message).where(Message.gmail_thread_id == gmail_thread_id)
                            )
                            existing_ticket = result.scalars().first()

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
                            )
                            db.add(msg)
                            if existing_ticket.status == "resolved":
                                existing_ticket.status = "open"
                                existing_ticket.resolved_at = None
                            now = datetime.now(timezone.utc)
                            from app.core.sla_config import get_sla_for_ticket
                            sla = get_sla_for_ticket(existing_ticket.category, existing_ticket.priority)
                            existing_ticket.sla_deadline = now + timedelta(hours=sla["resolution_hours"])
                            existing_ticket.sla_response_deadline = now + timedelta(hours=sla["response_hours"])
                            existing_ticket.sla_breached = False
                            existing_ticket.first_response_at = None
                            existing_ticket.updated_at = now
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

                            max_num = await db.execute(select(func.max(Ticket.number)))
                            next_num = (max_num.scalar() or 1000) + 1
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
                                triage = ai_triage(
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
                            except Exception:
                                pass

                            created += 1

                        await asyncio.to_thread(mark_as_read, gmail_message_id)

                    await db.commit()
                    if created or updated:
                        logger.info(f"Email fetch: {created} created, {updated} updated")
        except Exception as e:
            logger.error(f"Email fetch loop error: {e}")
        await asyncio.sleep(60)  # 60 seconds


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
            # Seed tracking data on demo tickets that don't have tracking codes yet
            """UPDATE tickets SET tracking_code = 'NX123456789BR', tracking_status = 'Em trânsito - Saiu para entrega',
                tracking_data = '{"carrier":"Correios","code":"NX123456789BR","status":"Em trânsito - Saiu para entrega","main_status":10,"delivered":false,"days_in_transit":4,"location":"São Paulo/SP","last_update":"2026-02-20T14:30:00","events":[{"date":"2026-02-20T14:30:00","status":"Objeto saiu para entrega ao destinatário","location":"São Paulo/SP"},{"date":"2026-02-19T08:15:00","status":"Objeto em trânsito - por favor aguarde","location":"Curitiba/PR"},{"date":"2026-02-17T10:00:00","status":"Objeto postado","location":"Florianópolis/SC"}]}'::jsonb
                WHERE number = 1001 AND (tracking_code IS NULL OR tracking_code = '')""",
            """UPDATE tickets SET tracking_code = 'NX987654321BR', tracking_status = 'Entregue',
                tracking_data = '{"carrier":"Correios","code":"NX987654321BR","status":"Entregue","main_status":50,"delivered":true,"days_in_transit":6,"location":"Rio de Janeiro/RJ","last_update":"2026-02-18T16:45:00","events":[{"date":"2026-02-18T16:45:00","status":"Objeto entregue ao destinatário","location":"Rio de Janeiro/RJ"},{"date":"2026-02-17T09:00:00","status":"Objeto saiu para entrega","location":"Rio de Janeiro/RJ"},{"date":"2026-02-15T11:30:00","status":"Objeto em trânsito","location":"São Paulo/SP"},{"date":"2026-02-13T08:00:00","status":"Objeto postado","location":"Florianópolis/SC"}]}'::jsonb
                WHERE number = 1002 AND (tracking_code IS NULL OR tracking_code = '')""",
            """UPDATE tickets SET tracking_code = 'YT2312345678901', tracking_status = 'Em trânsito',
                tracking_data = '{"carrier":"Cainiao","code":"YT2312345678901","status":"Em trânsito","main_status":10,"delivered":false,"days_in_transit":12,"location":"Cajamar/SP","last_update":"2026-02-21T20:00:00","events":[{"date":"2026-02-21T20:00:00","status":"Pacote em trânsito para o destino","location":"Cajamar/SP"},{"date":"2026-02-18T05:00:00","status":"Pacote chegou no país de destino","location":"Curitiba/PR"},{"date":"2026-02-12T08:00:00","status":"Despachado do país de origem","location":"Shenzhen, China"}]}'::jsonb
                WHERE number = 1004 AND (tracking_code IS NULL OR tracking_code = '')""",
            """UPDATE tickets SET tracking_code = 'NX555888222BR', tracking_status = 'Objeto devolvido ao remetente',
                tracking_data = '{"carrier":"Correios","code":"NX555888222BR","status":"Objeto devolvido ao remetente","main_status":40,"delivered":false,"days_in_transit":8,"location":"Belo Horizonte/MG","last_update":"2026-02-22T10:00:00","events":[{"date":"2026-02-22T10:00:00","status":"Objeto devolvido ao remetente","location":"Belo Horizonte/MG"},{"date":"2026-02-21T14:00:00","status":"Destinatário ausente - 3ª tentativa","location":"Belo Horizonte/MG"},{"date":"2026-02-20T09:00:00","status":"Destinatário ausente - 2ª tentativa","location":"Belo Horizonte/MG"},{"date":"2026-02-19T10:30:00","status":"Destinatário ausente - 1ª tentativa","location":"Belo Horizonte/MG"}]}'::jsonb
                WHERE number = 1005 AND (tracking_code IS NULL OR tracking_code = '')""",
            """UPDATE tickets SET tracking_code = 'NX777333111BR', tracking_status = 'Aguardando postagem',
                tracking_data = '{"carrier":"Correios","code":"NX777333111BR","status":"Aguardando postagem","main_status":0,"delivered":false,"events":[]}'::jsonb
                WHERE number = 1008 AND (tracking_code IS NULL OR tracking_code = '')""",
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
        ]
        migration_logger = logging.getLogger("migrations")
        for sql in migration_sqls:
            try:
                await conn.execute(text(sql))
            except Exception as e:
                # Log but continue - column may already exist
                migration_logger.warning(f"Migration skipped: {str(e)[:200]}")

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

    # Start background tasks
    escalation_task = asyncio.create_task(_run_escalation_loop())
    email_fetch_task = asyncio.create_task(_run_email_fetch_loop())

    yield

    escalation_task.cancel()
    email_fetch_task.cancel()


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
app.include_router(ws.router)

# Public CSAT rating page (no auth required - customer clicks email link)
from app.api import csat as csat_public
app.include_router(csat_public.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Carbon Helpdesk"}
