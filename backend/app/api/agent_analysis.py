"""Agent deep analysis endpoints — super_admin only."""
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta, date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func, or_, and_, extract

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.agent_report import AgentReport
from app.services.agent_analysis_service import (
    calculate_quantitative_metrics, generate_ai_analysis, fetch_agent_messages,
    fetch_kb_context,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent-deep-analysis", tags=["agent-analysis"])


def _require_super_admin(user: User):
    if user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin only")


async def _ensure_settings_table(db: AsyncSession):
    """Create analysis_settings table if it doesn't exist."""
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS analysis_settings (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            updated_by VARCHAR(100)
        )
    """))
    await db.commit()


@router.get("/daily-activity")
async def daily_activity(
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to today"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get daily activity breakdown for all agents — messages per hour, first/last msg, gaps."""
    _require_super_admin(user)

    # BRT = UTC-3
    BRT = timezone(timedelta(hours=-3))

    if target_date:
        try:
            day = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    else:
        day = datetime.now(BRT).date()

    # Query range in UTC (BRT midnight = 03:00 UTC)
    day_start_brt = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=BRT)
    day_end_brt = day_start_brt + timedelta(days=1)
    day_start_utc = day_start_brt.astimezone(timezone.utc)
    day_end_utc = day_end_brt.astimezone(timezone.utc)

    # Get all active agents (not super_admin)
    agents_q = await db.execute(
        select(User).where(User.is_active == True, User.role.in_(["agent", "admin", "supervisor"]))
    )
    agents = agents_q.scalars().all()

    result = []
    for agent in agents:
        # Match outbound messages by sender_email or sender_name
        email_prefix = agent.email.split("@")[0] if agent.email else ""
        agent_filter = or_(
            func.coalesce(Message.sender_email, "").ilike(f"%{email_prefix}%"),
            func.coalesce(Message.sender_name, "").ilike(f"%{agent.name}%"),
        )

        # Get all outbound messages for this agent on this day
        msgs_q = await db.execute(
            select(Message.created_at).where(
                Message.type == "outbound",
                Message.created_at >= day_start_utc,
                Message.created_at < day_end_utc,
                agent_filter,
            ).order_by(Message.created_at)
        )
        timestamps_utc = [row[0] for row in msgs_q.all()]

        if not timestamps_utc:
            result.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "role": agent.role,
                "total_messages": 0,
                "first_message": None,
                "last_message": None,
                "active_hours": 0,
                "work_span_hours": 0,
                "hourly_breakdown": {},
                "gaps": [],
                "idle_pct": 100,
                "avg_gap_min": 0,
                "status": "ausente",
            })
            continue

        # Convert to BRT for display
        timestamps = []
        for ts in timestamps_utc:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            timestamps.append(ts.astimezone(BRT))

        # Hourly breakdown (in BRT)
        hourly = {}
        for ts in timestamps:
            h = ts.hour
            hourly[h] = hourly.get(h, 0) + 1

        first_msg = timestamps[0]
        last_msg = timestamps[-1]

        # Calculate active hours (hours with at least 1 message)
        active_hours = len(hourly)

        # Find gaps > 1 hour during work period
        gaps = []
        total_gap_min = 0
        if len(timestamps) > 1:
            for i in range(1, len(timestamps)):
                diff_min = (timestamps[i] - timestamps[i-1]).total_seconds() / 60
                if diff_min > 60:
                    gap_entry = {
                        "from": timestamps[i-1].strftime("%H:%M"),
                        "to": timestamps[i].strftime("%H:%M"),
                        "minutes": round(diff_min),
                    }
                    gaps.append(gap_entry)
                    total_gap_min += diff_min

        # Determine status
        total = len(timestamps)
        work_span_h = (last_msg - first_msg).total_seconds() / 3600 if total > 1 else 0
        work_span_min = work_span_h * 60

        # Idle percentage (gap time vs work span)
        idle_pct = round((total_gap_min / work_span_min) * 100) if work_span_min > 0 else 0
        avg_gap = round(total_gap_min / len(gaps)) if gaps else 0

        if total == 0:
            status = "ausente"
        elif total < 5:
            status = "baixa_atividade"
        elif active_hours < 4:
            status = "parcial"
        elif len(gaps) > 2 and any(g["minutes"] > 120 for g in gaps):
            status = "intermitente"
        else:
            status = "ativo"

        result.append({
            "agent_id": agent.id,
            "agent_name": agent.name,
            "role": agent.role,
            "total_messages": total,
            "first_message": first_msg.strftime("%H:%M"),
            "last_message": last_msg.strftime("%H:%M"),
            "active_hours": active_hours,
            "work_span_hours": round(work_span_h, 1),
            "hourly_breakdown": {str(k): v for k, v in sorted(hourly.items())},
            "gaps": gaps,
            "idle_pct": idle_pct,
            "avg_gap_min": avg_gap,
            "status": status,
        })

    # Sort: active first, then by total messages desc
    status_order = {"ativo": 0, "parcial": 1, "intermitente": 2, "baixa_atividade": 3, "ausente": 4}
    result.sort(key=lambda x: (status_order.get(x["status"], 5), -x["total_messages"]))

    # Summary stats
    active_agents = [a for a in result if a["total_messages"] > 0]
    total_msgs = sum(a["total_messages"] for a in result)
    avg_msgs = round(total_msgs / len(active_agents), 1) if active_agents else 0
    avg_span = round(sum(a["work_span_hours"] for a in active_agents) / len(active_agents), 1) if active_agents else 0

    return {
        "date": day.isoformat(),
        "agents": result,
        "summary": {
            "total_agents": len(result),
            "active_agents": len(active_agents),
            "total_messages": total_msgs,
            "avg_messages_per_agent": avg_msgs,
            "avg_work_span_hours": avg_span,
        },
    }


@router.get("/guidelines")
async def get_guidelines(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the analysis guidelines/playbook text."""
    _require_super_admin(user)
    await _ensure_settings_table(db)
    result = await db.execute(
        text("SELECT value FROM analysis_settings WHERE key = 'guidelines'")
    )
    row = result.first()
    return {"guidelines": row[0] if row else ""}


@router.post("/guidelines")
async def save_guidelines(
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Save analysis guidelines/playbook text."""
    _require_super_admin(user)
    await _ensure_settings_table(db)
    guidelines = data.get("guidelines", "")
    await db.execute(text("""
        INSERT INTO analysis_settings (key, value, updated_at, updated_by)
        VALUES ('guidelines', :val, NOW(), :user_id)
        ON CONFLICT (key) DO UPDATE SET value = :val, updated_at = NOW(), updated_by = :user_id
    """), {"val": guidelines, "user_id": user.id})
    await db.commit()
    return {"ok": True}


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

    agent = await db.get(User, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=days)

    try:
        metrics = await calculate_quantitative_metrics(db, agent_id, period_start, period_end)
    except Exception as e:
        logger.error(f"Metrics calculation failed for agent {agent_id}: {e}")
        metrics = {}
    messages = await fetch_agent_messages(db, agent_id, period_start, period_end, sample_size)

    # Fetch KB context (macros + articles) and custom guidelines
    kb_context = await fetch_kb_context(db)
    try:
        await _ensure_settings_table(db)
        r = await db.execute(text("SELECT value FROM analysis_settings WHERE key = 'guidelines'"))
        row = r.first()
        guidelines = row[0] if row else ""
    except Exception:
        guidelines = ""

    full_context = ""
    if guidelines:
        # Parse structured guidelines (JSON with sections) or plain text
        try:
            import json as _json
            sections = _json.loads(guidelines)
            if isinstance(sections, dict):
                section_labels = {
                    "tom_de_voz": "TOM DE VOZ E SAUDACAO",
                    "procedimentos": "PROCEDIMENTOS OBRIGATORIOS",
                    "politicas": "POLITICAS (TROCA, GARANTIA, REEMBOLSO)",
                    "escalacao": "REGRAS DE ESCALACAO",
                    "produtos": "CONHECIMENTO DE PRODUTOS",
                    "proibicoes": "PROIBICOES E ALERTAS",
                    "contexto_extra": "CONTEXTO EXTRA",
                }
                full_context += "DOCUMENTOS OFICIAIS DE INSTRUCAO DE ATENDIMENTO:\n"
                for key, label in section_labels.items():
                    val = sections.get(key, "").strip()
                    if val:
                        full_context += f"\n--- {label} ---\n{val}\n"
                full_context += "\n"
            else:
                full_context += f"DOCUMENTOS OFICIAIS DE INSTRUCAO DE ATENDIMENTO:\n{guidelines}\n\n"
        except Exception:
            full_context += f"DOCUMENTOS OFICIAIS DE INSTRUCAO DE ATENDIMENTO:\n{guidelines}\n\n"
    if kb_context:
        full_context += kb_context

    ai_result = {}
    if messages:
        try:
            ai_result = await generate_ai_analysis(agent.name, messages, metrics, kb_context=full_context)
            logger.info(f"AI analysis for {agent.name}: {len(ai_result)} keys, error={ai_result.get('error')}")
        except Exception as e:
            logger.error(f"AI analysis failed for {agent.name}: {e}", exc_info=True)
            ai_result = {"error": str(e)}
    else:
        logger.warning(f"No messages found for {agent.name} in period {period_start} - {period_end}")

    has_error = bool(ai_result.get("error"))

    # Build analysis metadata
    analysis_meta = {
        "messages_analyzed": len(messages),
        "sample_size_requested": sample_size,
        "tickets_in_period": metrics.get("tickets_total", 0),
        "period_days": days,
    }

    # ai_analysis is Text column (string), ai_scores is JSONB (dict)
    report = AgentReport(
        agent_id=agent_id,
        period_start=period_start,
        period_end=period_end,
        sample_size=sample_size,
        report_type="manual",
        quantitative_metrics={**metrics, "analysis_meta": analysis_meta},
        ai_analysis=ai_result.get("summary", "") if not has_error else "",
        ai_scores=ai_result if not has_error else {"error": ai_result.get("error", "unknown")},
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
        "quantitative_metrics": report.quantitative_metrics,
        "ai_scores": report.ai_scores,
        "ai_analysis": ai_result if not has_error else None,
        "analysis_meta": analysis_meta,
        "created_at": report.created_at.isoformat(),
    }


@router.get("/productivity")
async def productivity_metrics(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Agent productivity metrics: avg response time, resolution time, tickets/hour, daily breakdown."""
    _require_super_admin(user)

    BRT = timezone(timedelta(hours=-3))
    now_brt = datetime.now(BRT)

    if start_date:
        try:
            d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Invalid start_date. Use YYYY-MM-DD")
    else:
        d_start = (now_brt - timedelta(days=30)).date()

    if end_date:
        try:
            d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Invalid end_date. Use YYYY-MM-DD")
    else:
        d_end = now_brt.date()

    range_start_utc = datetime(d_start.year, d_start.month, d_start.day, 0, 0, 0, tzinfo=BRT).astimezone(timezone.utc)
    range_end_utc = datetime(d_end.year, d_end.month, d_end.day, 23, 59, 59, tzinfo=BRT).astimezone(timezone.utc)

    agents_q = await db.execute(
        select(User).where(User.is_active == True, User.role.in_(["agent", "admin", "supervisor"]))
    )
    agents = agents_q.scalars().all()

    result = []
    for agent in agents:
        email_prefix = agent.email.split("@")[0] if agent.email else ""
        agent_msg_filter = or_(
            func.coalesce(Message.sender_email, "").ilike(f"%{email_prefix}%"),
            func.coalesce(Message.sender_name, "").ilike(f"%{agent.name}%"),
        )

        ticket_ids_q = select(Ticket.id).where(
            Ticket.assigned_to == agent.id,
            or_(
                and_(Ticket.created_at >= range_start_utc, Ticket.created_at <= range_end_utc),
                and_(Ticket.updated_at >= range_start_utc, Ticket.updated_at <= range_end_utc),
            ),
        )

        msgs_q = await db.execute(
            select(Message.ticket_id, Message.type, Message.created_at, Message.sender_email, Message.sender_name)
            .where(
                Message.ticket_id.in_(ticket_ids_q),
                Message.type.in_(["inbound", "outbound"]),
                Message.created_at >= range_start_utc,
                Message.created_at <= range_end_utc,
            )
            .order_by(Message.ticket_id, Message.created_at)
        )
        all_msgs = msgs_q.all()

        ticket_msgs = defaultdict(list)
        for msg in all_msgs:
            ticket_msgs[msg[0]].append({
                "type": msg[1],
                "created_at": msg[2],
                "sender_email": msg[3] or "",
                "sender_name": msg[4] or "",
            })

        response_times = []
        daily_data = defaultdict(lambda: {
            "response_times": [],
            "resolution_times": [],
            "tickets_responded": set(),
            "outbound_timestamps": [],
        })

        for tid, msgs in ticket_msgs.items():
            pending_inbound = None
            for m in msgs:
                if m["type"] == "inbound":
                    pending_inbound = m["created_at"]
                elif m["type"] == "outbound" and pending_inbound:
                    is_agent = (
                        email_prefix and email_prefix.lower() in m["sender_email"].lower()
                    ) or (
                        agent.name and agent.name.lower() in m["sender_name"].lower()
                    )
                    if is_agent:
                        ts_inbound = pending_inbound
                        ts_outbound = m["created_at"]
                        if ts_inbound.tzinfo is None:
                            ts_inbound = ts_inbound.replace(tzinfo=timezone.utc)
                        if ts_outbound.tzinfo is None:
                            ts_outbound = ts_outbound.replace(tzinfo=timezone.utc)
                        diff_min = (ts_outbound - ts_inbound).total_seconds() / 60
                        if diff_min >= 0:
                            response_times.append(diff_min)
                            day_key = ts_outbound.astimezone(BRT).date().isoformat()
                            daily_data[day_key]["response_times"].append(diff_min)
                            daily_data[day_key]["tickets_responded"].add(tid)
                            daily_data[day_key]["outbound_timestamps"].append(ts_outbound)
                        pending_inbound = None

        resolved_q = await db.execute(
            select(Ticket.created_at, Ticket.resolved_at)
            .where(
                Ticket.assigned_to == agent.id,
                Ticket.resolved_at.isnot(None),
                Ticket.resolved_at >= range_start_utc,
                Ticket.resolved_at <= range_end_utc,
            )
        )
        resolution_times = []
        for row in resolved_q.all():
            t_created = row[0]
            t_resolved = row[1]
            if t_created.tzinfo is None:
                t_created = t_created.replace(tzinfo=timezone.utc)
            if t_resolved.tzinfo is None:
                t_resolved = t_resolved.replace(tzinfo=timezone.utc)
            diff_h = (t_resolved - t_created).total_seconds() / 3600
            if diff_h >= 0:
                resolution_times.append(diff_h)
                day_key = t_resolved.astimezone(BRT).date().isoformat()
                daily_data[day_key]["resolution_times"].append(diff_h)

        outbound_q = await db.execute(
            select(Message.created_at)
            .where(
                Message.type == "outbound",
                Message.created_at >= range_start_utc,
                Message.created_at <= range_end_utc,
                Message.ticket_id.in_(ticket_ids_q),
                agent_msg_filter,
            )
            .order_by(Message.created_at)
        )
        outbound_ts = []
        for row in outbound_q.all():
            ts = row[0]
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            outbound_ts.append(ts.astimezone(BRT))

        daily_outbound = defaultdict(list)
        for ts in outbound_ts:
            daily_outbound[ts.date().isoformat()].append(ts)

        total_hours_worked = 0
        total_tickets_responded = 0
        for day_key, timestamps in daily_outbound.items():
            if len(timestamps) >= 2:
                span_h = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
                total_hours_worked += max(span_h, 1)
            elif len(timestamps) == 1:
                total_hours_worked += 1
            total_tickets_responded += len(daily_data[day_key]["tickets_responded"]) if day_key in daily_data else 0

        all_days = set(daily_data.keys()) | set(daily_outbound.keys())
        daily_list = []
        for day_key in sorted(all_days):
            dd = daily_data.get(day_key, {"response_times": [], "resolution_times": [], "tickets_responded": set()})
            day_outbound = daily_outbound.get(day_key, [])

            day_hours = 0
            if len(day_outbound) >= 2:
                day_hours = max((day_outbound[-1] - day_outbound[0]).total_seconds() / 3600, 1)
            elif len(day_outbound) == 1:
                day_hours = 1

            day_tickets = len(dd["tickets_responded"])

            daily_list.append({
                "date": day_key,
                "avg_response_time_min": round(sum(dd["response_times"]) / len(dd["response_times"]), 1) if dd["response_times"] else 0,
                "avg_resolution_time_h": round(sum(dd["resolution_times"]) / len(dd["resolution_times"]), 1) if dd["resolution_times"] else 0,
                "tickets_responded": day_tickets,
                "hours_worked": round(day_hours, 1),
                "tickets_per_hour": round(day_tickets / day_hours, 1) if day_hours > 0 else 0,
            })

        avg_response = round(sum(response_times) / len(response_times), 1) if response_times else 0
        avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else 0
        tph = round(total_tickets_responded / total_hours_worked, 1) if total_hours_worked > 0 else 0

        result.append({
            "agent_id": agent.id,
            "agent_name": agent.name,
            "totals": {
                "avg_response_time_min": avg_response,
                "avg_resolution_time_h": avg_resolution,
                "tickets_per_hour": tph,
                "total_tickets": len(set(m[0] for m in all_msgs)),
                "total_resolved": len(resolution_times),
                "total_hours_worked": round(total_hours_worked, 1),
            },
            "daily": daily_list,
        })

    result.sort(key=lambda x: -x["totals"]["tickets_per_hour"])

    return {
        "period": {"start": d_start.isoformat(), "end": d_end.isoformat()},
        "agents": result,
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

    # ai_scores (JSONB) contains the full analysis dict from tool_use
    # ai_analysis (Text) contains just the summary string
    # For the frontend, return ai_scores as both ai_scores and ai_analysis (full structured data)
    ai_scores = report.ai_scores or {}
    return {
        "id": report.id,
        "agent_id": report.agent_id,
        "agent_name": report.agent.name if report.agent else "?",
        "period_start": report.period_start.isoformat(),
        "period_end": report.period_end.isoformat(),
        "sample_size": report.sample_size,
        "report_type": report.report_type,
        "quantitative_metrics": report.quantitative_metrics,
        "ai_analysis": ai_scores if not ai_scores.get("error") else report.ai_analysis,
        "ai_scores": ai_scores,
        "analysis_meta": (report.quantitative_metrics or {}).get("analysis_meta"),
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
        "technical_knowledge": "Conhecimento Tecnico",
        "conflict_management": "Gestao de Conflitos",
        "personalization": "Personalizacao",
        "urgency_awareness": "Senso de Urgencia",
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
