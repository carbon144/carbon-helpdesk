# Agent Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a deep agent performance analysis system combining SQL metrics with AI qualitative analysis, accessible only to super_admin users.

**Architecture:** New `AgentReport` model stores reports. New endpoints under `/api/reports/agent-analysis/` handle generation, listing, detail, and PDF export. A weekly cron generates automatic reports. New frontend page `/agent-analysis` with overview cards, detail view, and export. Also adds retry with backoff to AI service for 429/529 errors.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL JSONB, Anthropic Claude API, React, Recharts, html-to-pdf via backend HTML template.

---

### Task 1: AI Service Retry (fix 529 errors)

**Files:**
- Modify: `backend/app/services/ai_service.py`

**What to do:**

Add a retry wrapper with exponential backoff for Anthropic API calls. This fixes the 529 Overloaded errors seen in production.

Add this helper near the top of the file (after imports):

```python
import asyncio as _asyncio
import random as _random

async def _call_with_retry(func, *args, max_retries=3, **kwargs):
    """Call an async/sync anthropic function with retry on 429/529."""
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        except Exception as e:
            err_str = str(e)
            is_retryable = any(code in err_str for code in ["429", "529", "overloaded", "rate_limit"])
            if not is_retryable or attempt == max_retries:
                raise
            delay = (2 ** attempt) + _random.uniform(0, 1)
            logging.getLogger(__name__).warning(f"Anthropic retry {attempt+1}/{max_retries} after {delay:.1f}s: {err_str[:80]}")
            await _asyncio.sleep(delay)
```

Then wrap the `client.messages.create()` calls in `triage_ticket`, `suggest_reply`, `summarize_ticket`, `ai_auto_reply`, and any other function that calls Anthropic. Replace direct `client.messages.create(...)` with:

```python
response = await _call_with_retry(client.messages.create, model=..., max_tokens=..., messages=...)
```

Note: `client.messages.create` is synchronous in the anthropic SDK v0.18. So wrap it:

```python
response = await _call_with_retry(lambda: client.messages.create(model=..., max_tokens=..., messages=...))
```

**Commit:** `fix: add retry with backoff for Anthropic 429/529 errors`

---

### Task 2: AgentReport Model + Migration

**Files:**
- Create: `backend/app/models/agent_report.py`
- Modify: `backend/app/main.py` (import model so table is created)

**What to do:**

Create the model:

```python
import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class AgentReport(Base):
    __tablename__ = "agent_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # null = all
    report_type: Mapped[str] = mapped_column(String(20), default="manual")  # manual | weekly_auto
    quantitative_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ai_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    generated_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    agent = relationship("User", foreign_keys=[agent_id], lazy="selectin")
```

In `backend/app/main.py`, add import near line 17:
```python
from app.models.agent_report import AgentReport  # noqa: ensure table created
```

**Commit:** `feat: add AgentReport model`

---

### Task 3: Agent Analysis Service

**Files:**
- Create: `backend/app/services/agent_analysis_service.py`

**What to do:**

Service with two main functions:

1. `calculate_quantitative_metrics(db, agent_id, period_start, period_end)` — runs SQL queries and returns a dict with all quantitative metrics.

2. `generate_ai_analysis(agent_name, messages, kb_context=None)` — sends messages to Claude and returns parsed JSON with scores + text analysis.

```python
"""Agent deep analysis service."""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, extract

from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.csat import CSATRating

logger = logging.getLogger(__name__)


async def calculate_quantitative_metrics(
    db: AsyncSession, agent_id: str, period_start: datetime, period_end: datetime
) -> dict:
    """Calculate all quantitative metrics for an agent in a period."""

    # Base filters
    period_filter = and_(Ticket.created_at >= period_start, Ticket.created_at <= period_end)
    agent_filter = Ticket.assigned_to == agent_id

    # Main ticket stats
    stats = await db.execute(
        select(
            func.count(Ticket.id).label("total"),
            func.count().filter(Ticket.status.in_(["resolved", "closed"])).label("resolved"),
            func.count().filter(Ticket.sla_breached == False, Ticket.status.in_(["resolved", "closed"])).label("sla_ok"),
            func.count().filter(Ticket.status == "escalated").label("escalated"),
            func.avg(extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
                .filter(Ticket.first_response_at.isnot(None)).label("avg_first_response_h"),
            func.avg(extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
                .filter(Ticket.resolved_at.isnot(None)).label("avg_resolution_h"),
        ).where(agent_filter, period_filter)
    )
    row = stats.one()
    total = row[0] or 0
    resolved = row[1] or 0
    sla_ok = row[2] or 0
    escalated = row[3] or 0
    avg_first_response_h = round(row[4] or 0, 1)
    avg_resolution_h = round(row[5] or 0, 1)
    sla_pct = round((sla_ok / resolved * 100) if resolved > 0 else 100, 1)

    # FCR - tickets resolved with only 1 outbound message
    fcr_q = await db.execute(
        select(func.count(Ticket.id)).where(
            agent_filter, period_filter,
            Ticket.status.in_(["resolved", "closed"]),
            Ticket.first_response_at.isnot(None),
            Ticket.resolved_at.isnot(None),
            extract("epoch", Ticket.resolved_at - Ticket.first_response_at) < 300,  # resolved within 5min of first response
        )
    )
    fcr_count = fcr_q.scalar() or 0
    fcr_rate = round((fcr_count / resolved * 100) if resolved > 0 else 0, 1)

    # CSAT
    csat = await db.execute(
        select(
            func.avg(CSATRating.score),
            func.count(CSATRating.id),
        ).where(CSATRating.agent_id == agent_id, CSATRating.created_at >= period_start, CSATRating.created_at <= period_end)
    )
    csat_row = csat.one()
    csat_avg = round(csat_row[0] or 0, 1)
    csat_count = csat_row[1] or 0

    # Messages per ticket avg
    msg_q = await db.execute(
        select(func.count(Message.id)).where(
            Message.type == "outbound",
            Message.ticket_id.in_(
                select(Ticket.id).where(agent_filter, period_filter)
            ),
        )
    )
    total_outbound = msg_q.scalar() or 0
    msgs_per_ticket = round(total_outbound / total, 1) if total > 0 else 0

    # Tickets by category
    cat_q = await db.execute(
        select(Ticket.category, func.count(Ticket.id))
        .where(agent_filter, period_filter)
        .group_by(Ticket.category)
    )
    by_category = {(r[0] or "sem_categoria"): r[1] for r in cat_q.all()}

    # Hourly distribution (based on outbound messages)
    hour_q = await db.execute(
        select(
            extract("hour", Message.created_at).label("h"),
            func.count(Message.id),
        ).where(
            Message.type == "outbound",
            Message.sender_email.isnot(None),
            Message.created_at >= period_start,
            Message.created_at <= period_end,
            Message.ticket_id.in_(select(Ticket.id).where(agent_filter)),
        ).group_by("h").order_by("h")
    )
    hourly = {int(r[0]): r[1] for r in hour_q.all()}

    # Daily volume
    daily_q = await db.execute(
        select(
            func.date_trunc("day", Ticket.created_at).label("day"),
            func.count(Ticket.id),
        ).where(agent_filter, period_filter)
        .group_by("day").order_by("day")
    )
    daily = [{"date": r[0].isoformat()[:10], "count": r[1]} for r in daily_q.all()]

    return {
        "tickets_total": total,
        "tickets_resolved": resolved,
        "tickets_escalated": escalated,
        "avg_first_response_h": avg_first_response_h,
        "avg_resolution_h": avg_resolution_h,
        "sla_compliance_pct": sla_pct,
        "csat_avg": csat_avg,
        "csat_count": csat_count,
        "fcr_rate": fcr_rate,
        "messages_per_ticket_avg": msgs_per_ticket,
        "tickets_by_category": by_category,
        "hourly_distribution": hourly,
        "daily_volume": daily,
    }


async def generate_ai_analysis(agent_name: str, messages: list[str]) -> dict:
    """Send agent messages to Claude for qualitative analysis."""
    from app.services.ai_service import client, is_credits_exhausted, _handle_credit_error, _call_with_retry

    if not client:
        return {"error": "AI not configured"}
    if is_credits_exhausted():
        return {"error": "credits_exhausted"}

    messages_text = "\n---\n".join(messages[:200])  # safety cap

    prompt = f"""Voce e um supervisor de atendimento ao cliente da Carbon (marca brasileira de smartwatches).
Analise as mensagens abaixo enviadas pelo atendente "{agent_name}".

Avalie cada criterio de 1 a 10:
1. Tom e empatia - Acolhimento, cordialidade, nao robotico
2. Clareza e objetividade - Explicacoes sem ambiguidade
3. Aderencia aos procedimentos - Seguiu playbook, pediu dados corretos
4. Proatividade - Antecipou duvidas, ofereceu solucoes extras
5. Qualidade do portugues - Gramatica, ortografia, formalidade adequada
6. Resolucao efetiva - Resolveu de fato ou enrolou o cliente

Retorne SOMENTE um JSON valido (sem markdown, sem ```):
{{
  "scores": {{
    "tone_empathy": N,
    "clarity": N,
    "playbook_adherence": N,
    "proactivity": N,
    "grammar": N,
    "resolution_quality": N,
    "overall": N
  }},
  "summary": "parecer geral em 3-5 paragrafos sobre o perfil deste atendente",
  "strengths": ["ponto forte 1", "ponto forte 2"],
  "improvements": ["melhoria 1 com exemplo real das mensagens", "melhoria 2"],
  "recommendations": ["recomendacao concreta 1", "recomendacao concreta 2"]
}}

MENSAGENS DO ATENDENTE:
{messages_text}"""

    try:
        response = await _call_with_retry(
            lambda: client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
        )
        text = response.content[0].text.strip()
        # Try to parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group())
            return {"error": "Failed to parse AI response", "raw": text[:500]}
    except Exception as e:
        _handle_credit_error(e)
        logger.error(f"Agent analysis AI failed: {e}")
        return {"error": str(e)[:200]}


async def fetch_agent_messages(
    db: AsyncSession, agent_id: str, period_start: datetime, period_end: datetime,
    sample_size: Optional[int] = 50,
) -> list[str]:
    """Fetch outbound messages from an agent for AI analysis."""
    q = (
        select(Message.body_text)
        .join(Ticket, Message.ticket_id == Ticket.id)
        .where(
            Ticket.assigned_to == agent_id,
            Message.type == "outbound",
            Message.body_text.isnot(None),
            Message.body_text != "",
            Message.created_at >= period_start,
            Message.created_at <= period_end,
        )
        .order_by(Message.created_at.desc())
    )
    if sample_size:
        q = q.limit(sample_size)

    result = await db.execute(q)
    return [row[0] for row in result.all() if row[0] and len(row[0].strip()) > 10]
```

**Commit:** `feat: add agent analysis service (quantitative + AI)`

---

### Task 4: Agent Analysis API Endpoints

**Files:**
- Create: `backend/app/api/agent_analysis.py`
- Modify: `backend/app/main.py` (register router)

**What to do:**

Create the API file with these endpoints:

1. `POST /api/reports/agent-analysis/{agent_id}` — generate report on demand
2. `GET /api/reports/agent-analysis` — list reports (with filters)
3. `GET /api/reports/agent-analysis/{report_id}` — get single report
4. `GET /api/reports/agent-analysis/overview` — all agents summary
5. `GET /api/reports/agent-analysis/{report_id}/export` — export PDF

All endpoints check `user.role == "super_admin"`, return 403 otherwise.

```python
"""Agent deep analysis endpoints — super_admin only."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.agent_report import AgentReport
from app.services.agent_analysis_service import (
    calculate_quantitative_metrics, generate_ai_analysis, fetch_agent_messages,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports/agent-analysis", tags=["agent-analysis"])


def _require_super_admin(user: User):
    if user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin only")


@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Summary cards for all agents with their latest report scores."""
    _require_super_admin(user)

    agents = await db.execute(select(User).where(User.is_active == True))
    agents_list = agents.scalars().all()

    result = []
    for agent in agents_list:
        # Get latest report
        latest = await db.execute(
            select(AgentReport)
            .where(AgentReport.agent_id == agent.id)
            .order_by(AgentReport.created_at.desc())
            .limit(1)
        )
        report = latest.scalars().first()

        result.append({
            "agent_id": agent.id,
            "agent_name": agent.name,
            "role": agent.role,
            "latest_report": {
                "id": report.id,
                "created_at": report.created_at.isoformat(),
                "ai_scores": report.ai_scores,
                "report_type": report.report_type,
                "quantitative_metrics": report.quantitative_metrics,
            } if report else None,
        })

    return result


@router.post("/{agent_id}")
async def generate_report(
    agent_id: str,
    days: int = Query(30, ge=1, le=365),
    sample_size: Optional[int] = Query(50, description="20, 50, 100, or null for all"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a new analysis report for an agent."""
    _require_super_admin(user)

    # Validate agent exists
    agent = await db.get(User, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=days)

    # 1. Quantitative metrics
    metrics = await calculate_quantitative_metrics(db, agent_id, period_start, period_end)

    # 2. Fetch messages for AI
    messages = await fetch_agent_messages(db, agent_id, period_start, period_end, sample_size)

    # 3. AI analysis
    ai_result = {}
    ai_scores = {}
    if messages:
        ai_result = await generate_ai_analysis(agent.name, messages)
        ai_scores = ai_result.get("scores", {})

    # 4. Save report
    report = AgentReport(
        agent_id=agent_id,
        period_start=period_start,
        period_end=period_end,
        sample_size=sample_size,
        report_type="manual",
        quantitative_metrics=metrics,
        ai_analysis=ai_result.get("summary", ""),
        ai_scores=ai_result if not ai_result.get("error") else {"error": ai_result["error"]},
        generated_by=user.id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return {
        "id": report.id,
        "agent_id": agent_id,
        "agent_name": agent.name,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "sample_size": sample_size,
        "quantitative_metrics": metrics,
        "ai_scores": ai_scores,
        "ai_analysis": ai_result,
        "created_at": report.created_at.isoformat(),
    }


@router.get("")
async def list_reports(
    agent_id: Optional[str] = None,
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List saved reports."""
    _require_super_admin(user)

    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = select(AgentReport).where(AgentReport.created_at >= since)
    if agent_id:
        q = q.where(AgentReport.agent_id == agent_id)
    q = q.order_by(AgentReport.created_at.desc())

    result = await db.execute(q)
    reports = result.scalars().all()

    return [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "agent_name": r.agent.name if r.agent else "?",
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "sample_size": r.sample_size,
            "report_type": r.report_type,
            "ai_scores": r.ai_scores,
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single report detail."""
    _require_super_admin(user)

    report = await db.get(AgentReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report.id,
        "agent_id": report.agent_id,
        "agent_name": report.agent.name if report.agent else "?",
        "period_start": report.period_start.isoformat(),
        "period_end": report.period_end.isoformat(),
        "sample_size": report.sample_size,
        "report_type": report.report_type,
        "quantitative_metrics": report.quantitative_metrics,
        "ai_analysis": report.ai_analysis,
        "ai_scores": report.ai_scores,
        "generated_by": report.generated_by,
        "created_at": report.created_at.isoformat(),
    }


@router.get("/{report_id}/export")
async def export_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export report as HTML (printable/saveable as PDF via browser)."""
    _require_super_admin(user)

    report = await db.get(AgentReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    agent_name = report.agent.name if report.agent else "Agente"
    metrics = report.quantitative_metrics or {}
    scores = report.ai_scores or {}
    ai_scores = scores.get("scores", scores)

    def score_bar(val):
        val = val or 0
        color = "#22c55e" if val >= 7 else "#eab308" if val >= 5 else "#ef4444"
        return f'<div style="background:#e5e7eb;border-radius:4px;height:20px;width:200px;display:inline-block;vertical-align:middle"><div style="background:{color};height:20px;border-radius:4px;width:{val*20}px"></div></div> <b>{val}/10</b>'

    score_rows = ""
    labels = {
        "tone_empathy": "Tom e Empatia",
        "clarity": "Clareza",
        "playbook_adherence": "Aderencia ao Playbook",
        "proactivity": "Proatividade",
        "grammar": "Portugues",
        "resolution_quality": "Resolucao Efetiva",
        "overall": "Nota Geral",
    }
    for key, label in labels.items():
        val = ai_scores.get(key, 0)
        score_rows += f"<tr><td>{label}</td><td>{score_bar(val)}</td></tr>\n"

    strengths = "".join(f"<li>{s}</li>" for s in scores.get("strengths", []))
    improvements = "".join(f"<li>{s}</li>" for s in scores.get("improvements", []))
    recommendations = "".join(f"<li>{s}</li>" for s in scores.get("recommendations", []))

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Analise - {agent_name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 40px auto; color: #1a1a1a; line-height: 1.6; }}
h1 {{ color: #111; border-bottom: 2px solid #111; padding-bottom: 8px; }}
h2 {{ color: #333; margin-top: 32px; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
td, th {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #e5e7eb; }}
.metric-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 16px 0; }}
.metric {{ background: #f9fafb; border-radius: 8px; padding: 16px; text-align: center; }}
.metric .value {{ font-size: 28px; font-weight: 700; color: #111; }}
.metric .label {{ font-size: 13px; color: #666; }}
ul {{ padding-left: 20px; }}
li {{ margin-bottom: 6px; }}
@media print {{ body {{ margin: 20px; }} }}
</style></head><body>
<h1>Analise de Atendente: {agent_name}</h1>
<p>Periodo: {report.period_start.strftime("%d/%m/%Y")} a {report.period_end.strftime("%d/%m/%Y")} | Amostra: {report.sample_size or "todas"} mensagens | Gerado em: {report.created_at.strftime("%d/%m/%Y %H:%M")}</p>

<h2>Metricas Quantitativas</h2>
<div class="metric-grid">
<div class="metric"><div class="value">{metrics.get("tickets_resolved", 0)}</div><div class="label">Tickets Resolvidos</div></div>
<div class="metric"><div class="value">{metrics.get("sla_compliance_pct", 0)}%</div><div class="label">SLA Cumprido</div></div>
<div class="metric"><div class="value">{metrics.get("avg_first_response_h", 0)}h</div><div class="label">Tempo Med. 1a Resposta</div></div>
<div class="metric"><div class="value">{metrics.get("avg_resolution_h", 0)}h</div><div class="label">Tempo Med. Resolucao</div></div>
<div class="metric"><div class="value">{metrics.get("csat_avg", 0)}</div><div class="label">CSAT Medio</div></div>
<div class="metric"><div class="value">{metrics.get("fcr_rate", 0)}%</div><div class="label">FCR</div></div>
</div>

<h2>Analise Qualitativa IA</h2>
<table>{score_rows}</table>

<h2>Parecer</h2>
<p>{report.ai_analysis or "Sem analise disponivel"}</p>

<h2>Pontos Fortes</h2>
<ul>{strengths or "<li>-</li>"}</ul>

<h2>Pontos de Melhoria</h2>
<ul>{improvements or "<li>-</li>"}</ul>

<h2>Recomendacoes</h2>
<ul>{recommendations or "<li>-</li>"}</ul>

</body></html>"""

    return HTMLResponse(content=html)
```

In `backend/app/main.py`, add import and register router:
```python
from app.api import agent_analysis
# ... after other include_router lines:
app.include_router(agent_analysis.router, prefix="/api")
```

**Commit:** `feat: add agent analysis API endpoints`

---

### Task 5: Weekly Cron Job

**Files:**
- Modify: `backend/app/main.py`

**What to do:**

Add a new background loop `_run_weekly_analysis()` that runs every hour, checks if it's Sunday 23:00 UTC, and generates reports for all active agents.

```python
async def _run_weekly_analysis():
    """Background task: generate weekly agent analysis reports every Sunday 23h UTC."""
    from app.services.agent_analysis_service import (
        calculate_quantitative_metrics, generate_ai_analysis, fetch_agent_messages,
    )
    logger = logging.getLogger("weekly_analysis")
    await asyncio.sleep(60)  # wait for startup

    last_run_week = None
    while True:
        try:
            now = datetime.now(timezone.utc)
            current_week = now.isocalendar()[1]
            # Run on Sunday (weekday 6) at hour 23, once per week
            if now.weekday() == 6 and now.hour == 23 and last_run_week != current_week:
                logger.info("Starting weekly agent analysis...")
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
                            logger.info(f"Weekly report generated for {agent.name}")
                        except Exception as e:
                            logger.error(f"Weekly analysis failed for {agent.name}: {e}")
                            await db.rollback()
                last_run_week = current_week
                logger.info("Weekly agent analysis complete")
        except Exception as e:
            logger.error(f"Weekly analysis loop error: {e}")
        await asyncio.sleep(3600)  # check every hour
```

Add to lifespan (near line 546):
```python
weekly_analysis_task = asyncio.create_task(_run_weekly_analysis())
```

Import needed at top of the cron function:
```python
from app.models.agent_report import AgentReport
```

**Commit:** `feat: add weekly automatic agent analysis cron`

---

### Task 6: Frontend — AgentAnalysisPage

**Files:**
- Create: `frontend/src/pages/AgentAnalysisPage.jsx`
- Modify: `frontend/src/components/Layout.jsx` (add route + nav link for super_admin)
- Modify: `frontend/src/services/api.js` (add API functions)

**What to do:**

Add API functions to `api.js`:
```javascript
// Agent Analysis (super_admin only)
export const getAgentAnalysisOverview = () => api.get('/reports/agent-analysis/overview')
export const generateAgentAnalysis = (agentId, params) => api.post(`/reports/agent-analysis/${agentId}`, null, { params })
export const getAgentAnalysisHistory = (params) => api.get('/reports/agent-analysis', { params })
export const getAgentAnalysisReport = (reportId) => api.get(`/reports/agent-analysis/${reportId}`)
```

Add route in `Layout.jsx` (inside Routes, before the catch-all):
```jsx
<Route path="/agent-analysis" element={<AgentAnalysisPage user={user} />} />
```

Add nav link in Layout.jsx sidebar, in the "Gestao" section, conditionally rendered:
```jsx
{user?.role === 'super_admin' && (
  <Link to="/agent-analysis">
    <span><i className="fa-solid fa-microscope"></i></span>
    <span>Analise de Equipe</span>
  </Link>
)}
```

Create `AgentAnalysisPage.jsx` with:
- Overview mode: grid of agent cards with scores radar/bars
- Detail mode: when clicking an agent, shows full report with:
  - Period selector (7/14/30/60/90 days)
  - Sample size selector (20/50/100/Todas)
  - "Gerar Nova Analise" button
  - Quantitative metrics section with recharts (daily volume, hourly dist, by category)
  - AI scores as horizontal bars (colored green/yellow/red)
  - Full AI text (summary, strengths, improvements, recommendations)
  - "Exportar PDF" button (opens export endpoint in new tab)
  - History tab with previous reports list

The page should be dark-themed consistent with the rest of the app.

**Commit:** `feat: add agent analysis frontend page`

---

### Task 7: Super Admin Role Migration

**Files:**
- Modify: `backend/app/models/user.py` (add super_admin to role enum if not present)
- Run SQL to set Pedro and Lyvia as super_admin

**What to do:**

Check if `super_admin` is already in the user_role enum. The model shows:
```python
role: Mapped[str] = mapped_column(SAEnum("super_admin", "admin", "supervisor", "agent", name="user_role"), default="agent")
```

Good — `super_admin` is already in the enum. Just need to update the two users via SQL on the server:

```sql
UPDATE users SET role = 'super_admin' WHERE email IN ('pedro@carbonsmartwatch.com.br', 'lyvia@carbonsmartwatch.com.br');
```

Also update the frontend auth check — in Layout.jsx, the sidebar may need to recognize `super_admin` as having admin-level access everywhere. Check that the frontend doesn't restrict admin-only features from super_admin.

**Commit:** `feat: set super_admin role for Pedro and Lyvia`

---

### Task 8: Deploy & Test

**What to do:**

1. Sync files to server via rsync
2. Rebuild backend + frontend containers
3. Run SQL to update Pedro and Lyvia roles
4. Test via browser:
   - Login as Pedro/Lyvia
   - Navigate to /agent-analysis
   - See overview with all agents
   - Click on an agent, generate analysis
   - Verify scores and text appear
   - Export PDF
   - Verify other users (non-super_admin) cannot see the page or call the API

**Commit:** N/A (deploy only)
