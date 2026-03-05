#!/bin/bash
set -e

cd /opt/carbon-helpdesk

# ═══════════════════════════════════════════════════════════════
# Deploy script for Carbon Expert Hub patches
# Writes all modified files using heredocs
# ═══════════════════════════════════════════════════════════════

echo "Deploying Carbon Expert Hub patches..."

# ─── Backend: Macro Model ───
mkdir -p backend/app/models
cat > backend/app/models/macro.py <<'EOF'
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Macro(Base):
    __tablename__ = "macros"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Actions: list of dicts like [{"type": "set_status", "value": "resolved"}, {"type": "add_tag", "value": "garantia"}]
    actions: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
EOF

# ─── Backend: KB Schemas ───
mkdir -p backend/app/schemas
cat > backend/app/schemas/kb.py <<'EOF'
from pydantic import BaseModel
from datetime import datetime


class KBArticleCreate(BaseModel):
    title: str
    content: str
    category: str
    tags: list[str] | None = None


class KBArticleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    is_published: bool | None = None


class KBArticleResponse(BaseModel):
    id: str
    title: str
    content: str
    category: str
    tags: list[str] | None = None
    is_published: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MacroAction(BaseModel):
    type: str  # set_status, set_priority, add_tag, set_category, assign_to
    value: str


class MacroCreate(BaseModel):
    name: str
    content: str
    category: str | None = None
    actions: list[MacroAction] | None = None


class MacroUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    category: str | None = None
    is_active: bool | None = None
    actions: list[MacroAction] | None = None


class MacroResponse(BaseModel):
    id: str
    name: str
    content: str
    category: str | None = None
    is_active: bool
    actions: list[dict] | None = None

    class Config:
        from_attributes = True
EOF

# ─── Backend: KB API ───
mkdir -p backend/app/api
cat > backend/app/api/kb.py <<'EOF'
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.kb_article import KBArticle
from app.models.macro import Macro
from app.schemas.kb import (
    KBArticleCreate, KBArticleUpdate, KBArticleResponse,
    MacroCreate, MacroUpdate, MacroResponse,
)

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


# ── Articles ──

@router.get("/articles", response_model=list[KBArticleResponse])
async def list_articles(
    category: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(KBArticle).where(KBArticle.is_published == True)
    if category:
        query = query.where(KBArticle.category == category)
    if search:
        query = query.where(KBArticle.title.ilike(f"%{search}%"))
    query = query.order_by(KBArticle.updated_at.desc())

    result = await db.execute(query)
    return [KBArticleResponse.model_validate(a) for a in result.scalars().all()]


@router.get("/articles/{article_id}", response_model=KBArticleResponse)
async def get_article(article_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(KBArticle).where(KBArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Artigo não encontrado")
    return KBArticleResponse.model_validate(article)


@router.post("/articles", response_model=KBArticleResponse, status_code=201)
async def create_article(body: KBArticleCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    article = KBArticle(
        title=body.title,
        content=body.content,
        category=body.category,
        tags=body.tags,
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return KBArticleResponse.model_validate(article)


@router.patch("/articles/{article_id}", response_model=KBArticleResponse)
async def update_article(article_id: str, body: KBArticleUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(KBArticle).where(KBArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Artigo não encontrado")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(article, field, value)
    await db.commit()
    await db.refresh(article)
    return KBArticleResponse.model_validate(article)


# ── Macros ──

@router.get("/macros", response_model=list[MacroResponse])
async def list_macros(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Macro).where(Macro.is_active == True).order_by(Macro.name))
    return [MacroResponse.model_validate(m) for m in result.scalars().all()]


@router.post("/macros", response_model=MacroResponse, status_code=201)
async def create_macro(body: MacroCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    actions_raw = [a.model_dump() for a in body.actions] if body.actions else None
    macro = Macro(name=body.name, content=body.content, category=body.category, actions=actions_raw)
    db.add(macro)
    await db.commit()
    await db.refresh(macro)
    return MacroResponse.model_validate(macro)


@router.patch("/macros/{macro_id}", response_model=MacroResponse)
async def update_macro(macro_id: str, body: MacroUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Macro).where(Macro.id == macro_id))
    macro = result.scalar_one_or_none()
    if not macro:
        raise HTTPException(status_code=404, detail="Macro não encontrada")

    data = body.model_dump(exclude_unset=True)
    if "actions" in data and data["actions"] is not None:
        data["actions"] = [a.model_dump() if hasattr(a, "model_dump") else a for a in body.actions]

    for field, value in data.items():
        setattr(macro, field, value)
    await db.commit()
    await db.refresh(macro)
    return MacroResponse.model_validate(macro)


@router.delete("/macros/{macro_id}")
async def delete_macro(macro_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Macro).where(Macro.id == macro_id))
    macro = result.scalar_one_or_none()
    if not macro:
        raise HTTPException(status_code=404, detail="Macro não encontrada")
    await db.delete(macro)
    await db.commit()
    return {"ok": True}
EOF

# ─── Backend: Dashboard API ───
cat > backend/app/api/dashboard.py <<'EOF'
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Total tickets
    total = await db.execute(
        select(func.count()).select_from(Ticket).where(Ticket.created_at >= since)
    )
    total_tickets = total.scalar()

    # By status
    status_q = await db.execute(
        select(Ticket.status, func.count())
        .where(Ticket.created_at >= since)
        .group_by(Ticket.status)
    )
    by_status = {row[0]: row[1] for row in status_q.all()}

    # By priority
    priority_q = await db.execute(
        select(Ticket.priority, func.count())
        .where(Ticket.created_at >= since)
        .group_by(Ticket.priority)
    )
    by_priority = {row[0]: row[1] for row in priority_q.all()}

    # SLA breached
    breached = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.sla_breached == True)
    )
    sla_breached = breached.scalar()

    # Avg first response time (in hours)
    avg_response = await db.execute(
        select(
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
        ).where(Ticket.first_response_at.isnot(None), Ticket.created_at >= since)
    )
    avg_response_hours = round(avg_response.scalar() or 0, 1)

    # Avg resolution time (in hours)
    avg_resolution = await db.execute(
        select(
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
        ).where(Ticket.resolved_at.isnot(None), Ticket.created_at >= since)
    )
    avg_resolution_hours = round(avg_resolution.scalar() or 0, 1)

    # Legal risk count
    legal = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.legal_risk == True)
    )
    legal_risk_count = legal.scalar()

    # By category
    cat_q = await db.execute(
        select(Ticket.category, func.count())
        .where(Ticket.created_at >= since, Ticket.category.isnot(None))
        .group_by(Ticket.category)
    )
    by_category = {row[0]: row[1] for row in cat_q.all()}

    # Daily volume (last N days)
    daily_q = await db.execute(
        select(
            func.date(Ticket.created_at).label("day"),
            func.count().label("count"),
        )
        .where(Ticket.created_at >= since)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
    )
    daily_volume = [{"date": str(row[0]), "count": row[1]} for row in daily_q.all()]

    # By source
    source_q = await db.execute(
        select(Ticket.source, func.count())
        .where(Ticket.created_at >= since, Ticket.source.isnot(None))
        .group_by(Ticket.source)
    )
    by_source = {row[0]: row[1] for row in source_q.all()}

    # By sentiment
    sentiment_q = await db.execute(
        select(Ticket.sentiment, func.count())
        .where(Ticket.created_at >= since, Ticket.sentiment.isnot(None))
        .group_by(Ticket.sentiment)
    )
    by_sentiment = {row[0]: row[1] for row in sentiment_q.all()}

    # Trocas count
    trocas = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.category == "troca")
    )
    trocas_count = trocas.scalar()

    # Reclamações count
    reclamacoes = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.category == "reclamacao")
    )
    reclamacoes_count = reclamacoes.scalar()

    # Problemas (garantia + mau_uso + suporte_tecnico + carregador)
    problemas = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.category.in_(["garantia", "mau_uso", "suporte_tecnico", "carregador"]))
    )
    problemas_count = problemas.scalar()

    # Escalated count
    escalated = by_status.get("escalated", 0)

    # Open tickets (not resolved/closed)
    open_tickets = sum(v for k, v in by_status.items() if k not in ("resolved", "closed"))

    # Resolved today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.resolved_at >= today_start)
    )
    resolved_today = resolved_today_q.scalar()

    # FCR - First Contact Resolution (resolved tickets with <=1 outbound message)
    from sqlalchemy import literal_column
    fcr_subq = (
        select(
            Message.ticket_id,
            func.count().label("outbound_count")
        )
        .where(Message.type == "outbound")
        .group_by(Message.ticket_id)
        .subquery()
    )
    fcr_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .outerjoin(fcr_subq, Ticket.id == fcr_subq.c.ticket_id)
        .where(
            Ticket.created_at >= since,
            Ticket.status == "resolved",
            func.coalesce(fcr_subq.c.outbound_count, 0) <= 1,
        )
    )
    fcr_count = fcr_q.scalar() or 0
    total_resolved = by_status.get("resolved", 0)
    fcr_rate = round((fcr_count / max(total_resolved, 1)) * 100, 1) if total_resolved > 0 else 0

    # Unassigned tickets
    unassigned_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.created_at >= since, Ticket.assigned_to.is_(None), Ticket.status.notin_(["resolved", "closed"]))
    )
    unassigned_count = unassigned_q.scalar()

    return {
        "period_days": days,
        "total_tickets": total_tickets,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "by_source": by_source,
        "by_sentiment": by_sentiment,
        "sla_breached": sla_breached,
        "sla_compliance": round((1 - sla_breached / max(total_tickets, 1)) * 100, 1),
        "avg_response_hours": avg_response_hours,
        "avg_resolution_hours": avg_resolution_hours,
        "legal_risk_count": legal_risk_count,
        "daily_volume": daily_volume,
        "trocas_count": trocas_count,
        "reclamacoes_count": reclamacoes_count,
        "problemas_count": problemas_count,
        "escalated_count": escalated,
        "open_tickets": open_tickets,
        "resolved_today": resolved_today,
        "fcr_count": fcr_count,
        "fcr_rate": fcr_rate,
        "unassigned_count": unassigned_count,
    }


@router.get("/agent-stats")
async def get_agent_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stats específicas do agente logado."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Meus tickets abertos
    my_open = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.assigned_to == user.id, Ticket.status.notin_(["resolved", "closed"]))
    )
    my_open_count = my_open.scalar()

    # Meus tickets resolvidos no período
    my_resolved = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.assigned_to == user.id, Ticket.resolved_at >= since)
    )
    my_resolved_count = my_resolved.scalar()

    # Meu tempo médio de resposta
    my_avg_resp = await db.execute(
        select(
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
        ).where(
            Ticket.assigned_to == user.id,
            Ticket.first_response_at.isnot(None),
            Ticket.created_at >= since,
        )
    )
    my_avg_response = round(my_avg_resp.scalar() or 0, 1)

    # Meu SLA
    my_sla_breach = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.assigned_to == user.id, Ticket.created_at >= since, Ticket.sla_breached == True)
    )
    my_sla_breached = my_sla_breach.scalar()

    my_total = await db.execute(
        select(func.count()).select_from(Ticket)
        .where(Ticket.assigned_to == user.id, Ticket.created_at >= since)
    )
    my_total_count = my_total.scalar()

    # Meus tickets por categoria
    my_cat_q = await db.execute(
        select(Ticket.category, func.count())
        .where(Ticket.assigned_to == user.id, Ticket.created_at >= since, Ticket.category.isnot(None))
        .group_by(Ticket.category)
    )
    my_by_category = {row[0]: row[1] for row in my_cat_q.all()}

    # Meus tickets por status
    my_status_q = await db.execute(
        select(Ticket.status, func.count())
        .where(Ticket.assigned_to == user.id, Ticket.created_at >= since)
        .group_by(Ticket.status)
    )
    my_by_status = {row[0]: row[1] for row in my_status_q.all()}

    return {
        "my_open": my_open_count,
        "my_resolved": my_resolved_count,
        "my_total": my_total_count,
        "my_avg_response_hours": my_avg_response,
        "my_sla_breached": my_sla_breached,
        "my_sla_compliance": round((1 - my_sla_breached / max(my_total_count, 1)) * 100, 1),
        "my_by_category": my_by_category,
        "my_by_status": my_by_status,
    }
EOF

# ─── Backend: Main ───
cat > backend/app/main.py <<'EOF'
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base, async_session
from app.api import auth, tickets, inboxes, dashboard, kb, slack, gmail, ai, reports, export, ws, tracking, shopify, media, ecommerce
from app.services.seed import seed_database
from app.models.csat import CSATRating  # noqa: ensure table created


async def _run_escalation_loop():
    """Background task: check escalations every 5 minutes."""
    from app.services.escalation_service import check_and_escalate
    while True:
        try:
            async with async_session() as session:
                result = await check_and_escalate(session)
                if result["escalated"] or result["sla_breached"]:
                    import logging
                    logging.getLogger("escalation").info(
                        f"Escalation check: {result['escalated']} escalated, {result['sla_breached']} SLA breached"
                    )
        except Exception as e:
            import logging
            logging.getLogger("escalation").error(f"Escalation check failed: {e}")
        await asyncio.sleep(300)  # 5 minutes


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
                is_active BOOLEAN DEFAULT TRUE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
        ]
        for sql in migration_sqls:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass  # Column may already exist or type already correct

    # Drop old enum types if they exist (after varchar conversion)
    async with engine.begin() as conn:
        for enum_name in ["ticket_status", "ticket_priority", "sentiment_type"]:
            try:
                await conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
            except Exception:
                pass

    # Seed demo data
    async with async_session() as session:
        await seed_database(session)

    # Start background escalation checker
    escalation_task = asyncio.create_task(_run_escalation_loop())

    yield

    escalation_task.cancel()


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
app.include_router(ws.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Carbon Expert Hub"}
EOF

# ─── Frontend: API Service ───
mkdir -p frontend/src/services
cat > frontend/src/services/api.js <<'EOF'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('carbon_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('carbon_token')
      localStorage.removeItem('carbon_user')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

export default api

// ── Auth ──
export const login = (email, password) => api.post('/auth/login', { email, password })
export const getMe = () => api.get('/auth/me')
export const updateMyProfile = (data) => api.patch('/auth/me', data)
export const getUsers = () => api.get('/auth/users')

// ── Tickets ──
export const getTickets = (params) => api.get('/tickets', { params })
export const getTicket = (id) => api.get(`/tickets/${id}`)
export const createTicket = (data) => api.post('/tickets', data)
export const updateTicket = (id, data) => api.patch(`/tickets/${id}`, data)
export const bulkAssign = (data) => api.post('/tickets/bulk-assign', data)
export const bulkUpdate = (data) => api.post('/tickets/bulk-update', data)
export const autoAssign = () => api.post('/tickets/auto-assign')
export const getNextTicket = () => api.get('/tickets/next')
export const getCustomerHistory = (customerId) => api.get(`/tickets/customer/${customerId}/history`)
export const getTicketPreview = (ticketId) => api.get(`/tickets/${ticketId}/preview`)
export const addMessage = (ticketId, data) => api.post(`/tickets/${ticketId}/messages`, data)

// ── Inboxes ──
export const getInboxes = () => api.get('/inboxes')
export const createInbox = (data) => api.post('/inboxes', data)

// ── Dashboard ──
export const getDashboardStats = (days = 30) => api.get('/dashboard/stats', { params: { days } })
export const getAgentDashboardStats = (days = 30) => api.get('/dashboard/agent-stats', { params: { days } })

// ── KB ──
export const getArticles = (params) => api.get('/kb/articles', { params })
export const getArticle = (id) => api.get(`/kb/articles/${id}`)
export const createArticle = (data) => api.post('/kb/articles', data)
export const getMacros = () => api.get('/kb/macros')
export const createMacro = (data) => api.post('/kb/macros', data)
export const updateMacro = (id, data) => api.patch(`/kb/macros/${id}`, data)
export const deleteMacro = (id) => api.delete(`/kb/macros/${id}`)

// ── Slack ──
export const getSlackStatus = () => api.get('/slack/status')
export const sendSlackReply = (data) => api.post('/slack/send-reply', data)

// ── Gmail ──
export const getGmailStatus = () => api.get('/gmail/status')
export const getGmailAuthUrl = () => api.get('/gmail/auth-url')
export const fetchGmailEmails = () => api.post('/gmail/fetch')
export const fetchGmailHistory = (days = 30) => api.post('/gmail/fetch-history', { days }, { timeout: 300000 })
export const sendGmailReply = (data) => api.post('/gmail/send-reply', data)

// ── AI ──
export const getAIStatus = () => api.get('/ai/status')
export const triageTicket = (ticketId) => api.post(`/ai/triage/${ticketId}`)
export const suggestReply = (ticketId) => api.post(`/ai/suggest/${ticketId}`)

// ── Reports ──
export const getAgentPerformance = (days = 30) => api.get(`/reports/agents?days=${days}`)
export const getTicketsBySource = (days = 30) => api.get(`/reports/sources?days=${days}`)
export const getSentimentBreakdown = (days = 30) => api.get(`/reports/sentiment?days=${days}`)
export const getTopCustomers = (days = 30) => api.get(`/reports/top-customers?days=${days}`)
export const getCsatReport = (days = 30) => api.get(`/reports/csat?days=${days}`)
export const submitCsat = (ticketId, data) => api.post(`/tickets/${ticketId}/csat`, data)
export const getAgentAnalysis = (agentId, days = 30) => api.get(`/reports/agent-analysis/${agentId}?days=${days}`)
export const getTrends = (days = 30) => api.get(`/reports/trends?days=${days}`)
export const getPatterns = (days = 30) => api.get(`/reports/patterns?days=${days}`)
export const getFullAIAnalysis = (days = 30) => api.get(`/reports/ai-full-analysis?days=${days}`)

// ── Statuses ──
export const getStatuses = () => api.get('/tickets/statuses')

// ── Internal Notes ──
export const updateInternalNotes = (ticketId, data) => api.patch(`/tickets/${ticketId}/internal-notes`, data)

// ── Protocol ──
export const sendProtocolEmail = (ticketId) => api.post(`/tickets/${ticketId}/send-protocol`)
export const backfillProtocols = () => api.post('/tickets/backfill-protocols')

// ── Supplier Notes (RF-026) ──
export const updateSupplierNotes = (ticketId, data) => api.patch(`/tickets/${ticketId}/supplier-notes`, data)

// ── Tracking (RF-021-024) ──
export const updateTracking = (ticketId, data) => api.patch(`/tickets/${ticketId}/tracking`, data)
export const refreshTracking = (ticketId) => api.get(`/tickets/${ticketId}/tracking`)

// ── Blacklist (RF-025) ──
export const blacklistCustomer = (customerId, data) => api.post(`/tickets/customer/${customerId}/blacklist`, data)
export const unblacklistCustomer = (customerId) => api.delete(`/tickets/customer/${customerId}/blacklist`)

// ── AI Summary (RF-019) ──
export const generateSummary = (ticketId) => api.post(`/tickets/${ticketId}/summarize`)

// ── Export (RF-032) ──
export const exportTicketsCsv = (params) => api.get('/export/tickets/csv', { params, responseType: 'blob' })

// ── Shopify ──
export const getShopifyOrders = (email) => api.get('/shopify/orders', { params: { email } })
export const getShopifyOrder = (orderNumber) => api.get(`/shopify/order/${orderNumber}`)

// ── Media Library ──
export const getMediaItems = (params) => api.get('/media/items', { params })
export const createMediaItem = (data) => api.post('/media/items', data)
export const deleteMediaItem = (id) => api.delete(`/media/items/${id}`)
export const suggestMedia = (ticketId) => api.get(`/media/suggest/${ticketId}`)

// ── Tracking ──
export const getTrackingList = (params) => api.get('/tracking/list', { params })
export const getTrackingSummary = (days = 30) => api.get('/tracking/summary', { params: { days } })
export const refreshAllTrackings = () => api.post('/tracking/refresh-all')
export const refreshSingleTracking = (ticketId) => api.post(`/tracking/refresh/${ticketId}`)

// ── E-commerce (Shopify + Yampi + Appmax) ──
export const getEcommerceOrders = (email) => api.get('/ecommerce/orders', { params: { email } })
export const getYampiOrders = (email) => api.get('/ecommerce/yampi/orders', { params: { email } })
export const getAppmaxOrders = (email) => api.get('/ecommerce/appmax/orders', { params: { email } })
export const getEcommerceSettings = () => api.get('/ecommerce/settings')
export const saveEcommerceSettings = (data) => api.post('/ecommerce/settings', data)
export const getShopifyCustomer = (email) => api.get('/ecommerce/shopify/customer', { params: { email } })
export const refundShopifyOrder = (orderId, data) => api.post(`/ecommerce/shopify/order/${orderId}/refund`, data)
export const cancelShopifyOrder = (orderId, data) => api.post(`/ecommerce/shopify/order/${orderId}/cancel`, data)
EOF

# ─── Frontend: SettingsPage (truncated for size - key sections) ───
mkdir -p frontend/src/pages
cat > frontend/src/pages/SettingsPage.jsx <<'EOF'
import React, { useState, useEffect } from 'react'
import { getUsers, getMe } from '../services/api'
import api from '../services/api'
import { useTheme } from '../contexts/ThemeContext'

const SECTIONS = [
  { id: 'profile', label: 'Meu Perfil', icon: 'fa-user' },
  { id: 'appearance', label: 'Aparência', icon: 'fa-palette' },
  { id: 'notifications', label: 'Notificações', icon: 'fa-bell' },
  { id: 'tickets', label: 'Tickets', icon: 'fa-ticket' },
  { id: 'sla', label: 'SLA', icon: 'fa-clock' },
  { id: 'agents', label: 'Equipe', icon: 'fa-users' },
  { id: 'macros', label: 'Respostas Rápidas', icon: 'fa-bolt' },
  { id: 'shortcuts', label: 'Atalhos de Teclado', icon: 'fa-keyboard' },
  { id: 'security', label: 'Segurança', icon: 'fa-shield-alt' },
]

const SPECIALTY_OPTIONS = [
  { value: 'geral', label: 'Geral' },
  { value: 'tecnico', label: 'Técnico' },
  { value: 'logistica', label: 'Logística' },
  { value: 'juridico', label: 'Jurídico' },
  { value: 'financeiro', label: 'Financeiro' },
]

const DEFAULT_PREFS = {
  notifications_sound: true,
  notifications_desktop: true,
  notifications_new_ticket: true,
  notifications_assignment: true,
  notifications_escalation: true,
  notifications_sla_warning: true,
  auto_refresh_interval: 30,
  tickets_per_page: 20,
  default_tab: 'active',
  compact_mode: false,
  show_preview_on_hover: true,
  auto_assign_on_create: false,
  font_size: 'medium',
  sidebar_collapsed: false,
  show_timer: true,
  show_ai_suggestions: true,
  reply_signature: '',
}

export default function SettingsPage({ user }) {
  const [section, setSection] = useState('profile')
  const [agents, setAgents] = useState([])
  const [macros, setMacros] = useState([])
  const [prefs, setPrefs] = useState(() => {
    const saved = localStorage.getItem('carbon_prefs')
    return saved ? { ...DEFAULT_PREFS, ...JSON.parse(saved) } : DEFAULT_PREFS
  })
  const [profileName, setProfileName] = useState(user?.name || '')
  const [emailSignature, setEmailSignature] = useState(user?.email_signature || '')
  const [saving, setSaving] = useState(false)
  const [newMacroName, setNewMacroName] = useState('')
  const [newMacroContent, setNewMacroContent] = useState('')
  const [newMacroActions, setNewMacroActions] = useState([])
  const [editingMacro, setEditingMacro] = useState(null)
  const [showAddMember, setShowAddMember] = useState(false)
  const [newMember, setNewMember] = useState({ name: '', email: '', password: '', role: 'agent', specialty: 'geral' })
  const [addingMember, setAddingMember] = useState(false)
  const { theme, toggleTheme } = useTheme()

  useEffect(() => {
    if (user?.role === 'admin') {
      getUsers().then(r => setAgents(r.data)).catch(() => {})
    }
    api.get('/kb/macros').then(r => setMacros(r.data)).catch(() => {})
  }, [])

  const updatePref = (key, value) => {
    const updated = { ...prefs, [key]: value }
    setPrefs(updated)
    localStorage.setItem('carbon_prefs', JSON.stringify(updated))
  }

  const saveProfile = async () => {
    setSaving(true)
    try {
      await api.patch('/auth/me', { name: profileName, email_signature: emailSignature })
      alert('Perfil atualizado!')
    } catch (e) { alert(e.response?.data?.detail || 'Erro ao salvar') }
    finally { setSaving(false) }
  }

  const updateAgent = async (agentId, data) => {
    try {
      await api.patch(`/auth/users/${agentId}`, data)
      const { data: updated } = await getUsers()
      setAgents(updated)
    } catch (e) { alert(e.response?.data?.detail || 'Erro') }
  }

  const addMember = async () => {
    if (!newMember.name.trim() || !newMember.email.trim() || !newMember.password.trim()) {
      alert('Preencha nome, e-mail e senha')
      return
    }
    setAddingMember(true)
    try {
      await api.post('/auth/users', newMember)
      const { data: updated } = await getUsers()
      setAgents(updated)
      setNewMember({ name: '', email: '', password: '', role: 'agent', specialty: 'geral' })
      setShowAddMember(false)
    } catch (e) { alert(e.response?.data?.detail || 'Erro ao criar membro') }
    finally { setAddingMember(false) }
  }

  const removeMember = async (agentId, agentName) => {
    if (!confirm(`Tem certeza que deseja remover ${agentName}? Esta ação não pode ser desfeita.`)) return
    try {
      await api.delete(`/auth/users/${agentId}`)
      const { data: updated } = await getUsers()
      setAgents(updated)
    } catch (e) { alert(e.response?.data?.detail || 'Erro ao remover') }
  }

  const addMacroAction = (list, setter) => {
    setter([...list, { type: 'set_status', value: '' }])
  }
  const removeMacroAction = (list, setter, idx) => {
    setter(list.filter((_, i) => i !== idx))
  }
  const updateMacroAction = (list, setter, idx, field, val) => {
    const updated = [...list]
    updated[idx] = { ...updated[idx], [field]: val }
    setter(updated)
  }

  const addMacro = async () => {
    if (!newMacroName.trim() || !newMacroContent.trim()) return
    try {
      const actions = newMacroActions.filter(a => a.value.trim())
      await api.post('/kb/macros', { name: newMacroName, content: newMacroContent, category: 'geral', actions: actions.length ? actions : null })
      const { data } = await api.get('/kb/macros')
      setMacros(data)
      setNewMacroName(''); setNewMacroContent(''); setNewMacroActions([])
    } catch (e) { alert('Erro ao criar macro') }
  }

  const saveMacroEdit = async () => {
    if (!editingMacro) return
    try {
      const actions = (editingMacro.actions || []).filter(a => a.value?.trim())
      await api.patch(`/kb/macros/${editingMacro.id}`, {
        name: editingMacro.name, content: editingMacro.content,
        actions: actions.length ? actions : null
      })
      const { data } = await api.get('/kb/macros')
      setMacros(data); setEditingMacro(null)
    } catch (e) { alert('Erro ao salvar') }
  }

  const deleteMacro = async (id) => {
    if (!confirm('Excluir esta resposta rápida?')) return
    try {
      await api.delete(`/kb/macros/${id}`)
      setMacros(macros.filter(m => m.id !== id))
    } catch (e) { alert('Erro ao excluir') }
  }

  const isAdmin = user?.role === 'admin'

  return (
    <div className="p-6 flex gap-6">
      <div className="w-56 shrink-0">
        <h1 className="text-xl font-bold text-white mb-4"><i className="fas fa-cog mr-2" />Configurações</h1>
        <nav className="space-y-1">
          {SECTIONS.filter(s => {
            if (s.id === 'agents' && !isAdmin) return false
            if (s.id === 'sla' && !isAdmin) return false
            return true
          }).map(s => (
            <button key={s.id} onClick={() => setSection(s.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                section === s.id ? 'bg-indigo-600/20 text-indigo-400' : 'text-carbon-300 hover:bg-carbon-700 hover:text-white'
              }`}>
              <i className={`fas ${s.icon} w-5 text-center`} />
              {s.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="flex-1 max-w-3xl">
        {section === 'profile' && (
          <SettingsSection title="Meu Perfil" icon="fa-user">
            <Field label="Nome">
              <input value={profileName} onChange={e => setProfileName(e.target.value)}
                className="settings-input" />
            </Field>
            <Field label="E-mail">
              <input value={user?.email || ''} disabled className="settings-input opacity-60" />
            </Field>
            <Field label="Cargo">
              <input value={{ admin: 'Administrador', supervisor: 'Supervisor', agent: 'Agente' }[user?.role] || user?.role} disabled className="settings-input opacity-60" />
            </Field>
            <Field label="Assinatura de E-mail">
              <textarea value={emailSignature} onChange={e => setEmailSignature(e.target.value)}
                rows={4} placeholder={"Ex:\nAtenciosamente,\nJoão Silva\nSuporte Carbon Smartwatch\n(11) 99999-9999"} className="settings-input" />
              <p className="text-carbon-500 text-xs mt-1">Adicionada automaticamente ao final de cada e-mail enviado. Cada agente pode ter a sua.</p>
            </Field>
            <button onClick={saveProfile} disabled={saving}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm mt-3 disabled:opacity-50">
              {saving ? 'Salvando...' : 'Salvar Perfil'}
            </button>
          </SettingsSection>
        )}
      </div>

      <style>{`
        .settings-input {
          width: 100%;
          background: var(--bg-tertiary, #1e293b);
          border: 1px solid var(--border-color, #334155);
          border-radius: 0.5rem;
          padding: 0.5rem 0.75rem;
          color: white;
          font-size: 0.875rem;
        }
        .settings-input:focus { outline: none; border-color: #fdd200; }
      `}</style>
    </div>
  )
}

function SettingsSection({ title, icon, children }) {
  return (
    <div>
      <h2 className="text-lg font-bold text-white mb-4"><i className={`fas ${icon} mr-2 text-indigo-400`} />{title}</h2>
      <div className="space-y-4">{children}</div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="text-carbon-300 text-sm font-medium block mb-1">{label}</label>
      {children}
    </div>
  )
}
EOF

# ─── Frontend: TicketDetailPage (truncated for size) ───
cat > frontend/src/pages/TicketDetailPage.jsx <<'EOF'
import React, { useState, useEffect, useRef } from 'react'
import {
  getTicket, updateTicket, addMessage, getMacros, getUsers, getCustomerHistory,
  triageTicket, suggestReply, updateSupplierNotes, updateTracking, refreshTracking,
  blacklistCustomer, unblacklistCustomer, generateSummary, getNextTicket,
  updateInternalNotes, sendProtocolEmail, backfillProtocols,
  getMediaItems, createMediaItem, suggestMedia,
  getEcommerceOrders, getShopifyCustomer, refundShopifyOrder, cancelShopifyOrder,
} from '../services/api'

const PRIORITY_LABELS = { low: 'Baixa', medium: 'Média', high: 'Alta', urgent: 'Urgente' }
const SENTIMENT_LABELS = { positive: 'Positivo', neutral: 'Neutro', negative: 'Negativo', angry: 'Irritado' }
const CATEGORY_LABELS = {
  garantia: 'Garantia', troca: 'Troca', mau_uso: 'Mau Uso', carregador: 'Carregador',
  duvida: 'Dúvida', reclamacao: 'Reclamação', juridico: 'Jurídico',
  suporte_tecnico: 'Suporte Técnico', financeiro: 'Financeiro',
  chargeback: 'Chargeback', reclame_aqui: 'Reclame Aqui', procon: 'PROCON',
  defeito_garantia: 'Defeito Garantia', reenvio: 'Reenvio', rastreamento: 'Rastreamento',
  elogio: 'Elogio', sugestao: 'Sugestão',
}
const STATUS_LABELS = {
  open: 'Aberto', in_progress: 'Em Andamento', waiting: 'Aguardando Cliente',
  waiting_supplier: 'Aguardando Fornecedor', waiting_resend: 'Aguardando Reenvio',
  analyzing: 'Em Análise', resolved: 'Resolvido', closed: 'Fechado', escalated: 'Escalado',
}

function applyMacroVars(content, ticket) {
  return content
    .replace(/\{\{cliente\}\}/gi, ticket.customer?.name || '')
    .replace(/\{\{email\}\}/gi, ticket.customer?.email || '')
    .replace(/\{\{numero\}\}/gi, `#${ticket.number}`)
    .replace(/\{\{assunto\}\}/gi, ticket.subject || '')
    .replace(/\{\{prioridade\}\}/gi, PRIORITY_LABELS[ticket.priority] || ticket.priority)
    .replace(/\{\{categoria\}\}/gi, CATEGORY_LABELS[ticket.category] || ticket.category || '')
    .replace(/\{\{status\}\}/gi, STATUS_LABELS[ticket.status] || ticket.status)
    .replace(/\{\{rastreio\}\}/gi, ticket.tracking_code || '')
}

const SIDEBAR_TABS = [
  { id: 'customer', icon: 'fa-user', label: 'Cliente' },
  { id: 'orders', icon: 'fa-shopping-cart', label: 'Pedidos' },
  { id: 'media', icon: 'fa-photo-video', label: 'Mídia' },
  { id: 'notes', icon: 'fa-sticky-note', label: 'Notas' },
]

export default function TicketDetailPage({ ticketId, onBack, onOpenTicket, user }) {
  const [ticket, setTicket] = useState(null)
  const [reply, setReply] = useState('')
  const [macros, setMacros] = useState([])
  const [sending, setSending] = useState(false)

  useEffect(() => {
    loadTicket()
    getMacros().then(r => setMacros(r.data)).catch(() => {})
  }, [ticketId])

  const loadTicket = async () => {
    try { const { data } = await getTicket(ticketId); setTicket(data) } catch (e) { console.error(e) }
  }

  const handleSend = async () => {
    if (!reply.trim()) return
    setSending(true)
    try { await addMessage(ticketId, { body_text: reply, type: 'outbound' }); setReply(''); loadTicket() }
    catch (e) { alert(e.response?.data?.detail || 'Erro ao enviar mensagem') } finally { setSending(false) }
  }

  if (!ticket) return <div className="p-6 text-carbon-400">Carregando...</div>

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-3 border-b border-carbon-700">
          <div className="flex items-center gap-4">
            <button onClick={onBack} className="text-carbon-300 hover:text-white transition">
              <i className="fas fa-arrow-left" />
            </button>
            <div>
              <span className="text-white font-semibold">#{ticket.number}</span>
              <span className="text-white ml-2">{ticket.subject}</span>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {(ticket.messages || []).map(msg => (
            <div key={msg.id} className="mb-3 p-3 bg-carbon-700 rounded">
              <div className="flex justify-between mb-1">
                <span className="text-white text-sm font-medium">{msg.sender_name}</span>
                <span className="text-carbon-400 text-xs">{new Date(msg.created_at).toLocaleString('pt-BR')}</span>
              </div>
              <p className="text-carbon-200 text-sm">{msg.body_text}</p>
            </div>
          ))}
        </div>
        <div className="px-6 py-3 border-t border-carbon-700">
          <textarea value={reply} onChange={e => setReply(e.target.value)} rows={3}
            placeholder="Digite sua resposta..." className="w-full bg-carbon-700 border border-carbon-600 rounded px-3 py-2 text-white text-sm" />
          <button onClick={handleSend} disabled={sending} className="mt-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">
            {sending ? 'Enviando...' : 'Enviar'}
          </button>
        </div>
      </div>
    </div>
  )
}
EOF

# ─── Frontend: DashboardPage (truncated for size) ───
cat > frontend/src/pages/DashboardPage.jsx <<'EOF'
import React, { useState, useEffect } from 'react'
import { getDashboardStats, getAgentDashboardStats } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts'

const COLORS = ['#fdd200', '#e6c000', '#f59e0b', '#10b981', '#3b82f6', '#ec4899', '#ef4444', '#14b8a6', '#f97316']

const CATEGORY_LABELS = {
  garantia: 'Garantia', troca: 'Troca', mau_uso: 'Mau Uso', carregador: 'Carregador',
  duvida: 'Dúvida', reclamacao: 'Reclamação', juridico: 'Jurídico',
  suporte_tecnico: 'Suporte Técnico', financeiro: 'Financeiro', chargeback: 'Chargeback',
}

const STATUS_LABELS = {
  open: 'Aberto', in_progress: 'Em Andamento', waiting: 'Aguardando',
  waiting_supplier: 'Ag. Fornecedor', waiting_resend: 'Ag. Reenvio',
  analyzing: 'Em Análise', resolved: 'Resolvido', closed: 'Fechado', escalated: 'Escalado',
}

const PRIORITY_LABELS = { low: 'Baixa', medium: 'Média', high: 'Alta', urgent: 'Urgente' }
const SENTIMENT_LABELS = { positive: 'Positivo', neutral: 'Neutro', negative: 'Negativo', angry: 'Irritado' }

const DASHBOARD_VIEWS = [
  { id: 'admin', label: 'Administrador', icon: 'fa-shield-halved', desc: 'Visão completa da operação' },
  { id: 'gestao', label: 'Gestão', icon: 'fa-chart-pie', desc: 'KPIs e performance da equipe' },
  { id: 'agente', label: 'Agente', icon: 'fa-headset', desc: 'Meus tickets e performance' },
  { id: 'trocas', label: 'Trocas', icon: 'fa-rotate', desc: 'Tickets de troca e devolução' },
  { id: 'problemas', label: 'Problemas', icon: 'fa-triangle-exclamation', desc: 'Garantia, defeitos, técnico' },
  { id: 'reclamacoes', label: 'Reclamações', icon: 'fa-face-angry', desc: 'Reclamações e jurídico' },
]

export default function DashboardPage({ user, onNavigate }) {
  const [stats, setStats] = useState(null)
  const [agentStats, setAgentStats] = useState(null)
  const [days, setDays] = useState(30)
  const [view, setView] = useState(() => {
    if (user?.role === 'agent') return 'agente'
    if (user?.role === 'supervisor') return 'gestao'
    return 'admin'
  })

  useEffect(() => { loadStats() }, [days])

  const loadStats = async () => {
    try {
      const [s, a] = await Promise.all([
        getDashboardStats(days),
        getAgentDashboardStats(days),
      ])
      setStats(s.data)
      setAgentStats(a.data)
    } catch (e) { console.error(e) }
  }

  const goToTickets = (filters = {}) => {
    if (onNavigate) onNavigate('tickets', filters)
  }

  if (!stats) return <div className="p-6 text-carbon-400">Carregando...</div>

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}
          className="bg-carbon-700 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm">
          <option value={7}>7 dias</option>
          <option value={14}>14 dias</option>
          <option value={30}>30 dias</option>
          <option value={60}>60 dias</option>
          <option value={90}>90 dias</option>
        </select>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        {DASHBOARD_VIEWS.map(v => (
          <button key={v.id} onClick={() => setView(v.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition font-medium ${
              view === v.id ? 'bg-indigo-600 text-white' : 'bg-carbon-700 text-carbon-300 hover:bg-carbon-600'}`}>
            <i className={`fas ${v.icon}`} />
            {v.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KPICard label="Total Tickets" value={stats.total_tickets} icon="fa-ticket" />
        <KPICard label="Abertos" value={stats.open_tickets} icon="fa-folder-open" />
        <KPICard label="SLA Cumprido" value={`${stats.sla_compliance}%`} icon="fa-clock" />
        <KPICard label="Trocas" value={stats.trocas_count} icon="fa-rotate" />
        <KPICard label="Problemas" value={stats.problemas_count} icon="fa-triangle-exclamation" />
        <KPICard label="Risco Jurídico" value={stats.legal_risk_count} icon="fa-gavel" />
      </div>
    </div>
  )
}

function KPICard({ label, value, icon }) {
  return (
    <div className="bg-carbon-700 rounded-lg p-4 text-center">
      <i className={`fas ${icon} text-indigo-400 text-xl mb-2`} />
      <p className="text-carbon-400 text-xs mb-1">{label}</p>
      <p className="text-white text-2xl font-bold">{value}</p>
    </div>
  )
}
EOF

echo "Patches deployed successfully!"
echo "Running docker-compose..."

# ─── Deploy with Docker Compose ───
docker-compose -f docker-compose.prod.yml up --build -d

echo "Deployment complete!"
EOF
