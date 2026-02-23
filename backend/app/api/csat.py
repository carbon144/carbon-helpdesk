"""Public CSAT rating endpoint — no auth required (customer clicks email link)."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.ticket import Ticket
from app.models.csat import CSATRating
from app.services.csat_service import verify_csat_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["csat"])


@router.get("/csat/{ticket_id}")
async def csat_page(
    ticket_id: str,
    token: str = Query(...),
    score: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Public page for customer to rate their experience."""
    if not verify_csat_token(ticket_id, token):
        return HTMLResponse(_error_html("Link inválido ou expirado."), status_code=403)

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return HTMLResponse(_error_html("Ticket não encontrado."), status_code=404)

    # Check if already rated
    existing = await db.execute(select(CSATRating).where(CSATRating.ticket_id == ticket_id))
    if existing.scalar_one_or_none():
        return HTMLResponse(_thankyou_html(ticket, already=True))

    # If score provided via link, save directly
    if score and 1 <= score <= 5:
        rating = CSATRating(
            ticket_id=ticket_id,
            agent_id=ticket.assigned_to,
            score=score,
        )
        db.add(rating)
        await db.commit()
        return HTMLResponse(_thankyou_html(ticket, score=score))

    # Show rating form
    return HTMLResponse(_form_html(ticket, token))


@router.post("/csat/{ticket_id}/submit")
async def csat_submit(
    ticket_id: str,
    token: str = Query(...),
    score: int = Query(...),
    comment: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Submit CSAT rating with optional comment."""
    if not verify_csat_token(ticket_id, token):
        raise HTTPException(403, "Token inválido")

    existing = await db.execute(select(CSATRating).where(CSATRating.ticket_id == ticket_id))
    if existing.scalar_one_or_none():
        return HTMLResponse(_thankyou_html(None, already=True))

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")

    rating = CSATRating(
        ticket_id=ticket_id,
        agent_id=ticket.assigned_to,
        score=max(1, min(5, score)),
        comment=comment or None,
    )
    db.add(rating)
    await db.commit()
    return HTMLResponse(_thankyou_html(ticket, score=score))


def _base_style():
    return """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e4e4e7; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .card { background: #1a1b23; border: 1px solid #2a2b35; border-radius: 20px; padding: 40px; max-width: 480px; width: 90%; text-align: center; }
        .logo { font-size: 24px; font-weight: 800; color: #818cf8; margin-bottom: 8px; }
        .subtitle { color: #71717a; font-size: 14px; margin-bottom: 24px; }
        .stars { display: flex; justify-content: center; gap: 12px; margin: 24px 0; }
        .star-btn { width: 56px; height: 56px; border-radius: 14px; border: 2px solid #2a2b35; background: #1e1f2a; cursor: pointer; font-size: 28px; transition: all 0.2s; display: flex; align-items: center; justify-content: center; text-decoration: none; }
        .star-btn:hover { border-color: #818cf8; background: #818cf8/15; transform: scale(1.1); }
        .star-label { font-size: 11px; color: #71717a; margin-top: 4px; }
        .ticket-info { background: #15161e; border-radius: 12px; padding: 16px; margin: 16px 0; text-align: left; }
        .ticket-info p { font-size: 13px; color: #a1a1aa; margin: 4px 0; }
        .ticket-info span { color: #e4e4e7; font-weight: 600; }
        textarea { width: 100%; background: #15161e; border: 1px solid #2a2b35; border-radius: 12px; padding: 12px; color: #e4e4e7; font-size: 14px; resize: none; outline: none; margin: 12px 0; }
        textarea:focus { border-color: #818cf8; }
        .btn { background: #6366f1; color: white; border: none; border-radius: 12px; padding: 12px 32px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn:hover { background: #818cf8; }
        .success { color: #34d399; font-size: 48px; margin-bottom: 16px; }
    </style>
    """


def _form_html(ticket, token):
    customer_name = (ticket.customer.name or "Cliente").split()[0] if ticket.customer else "Cliente"
    category_labels = {
        "garantia": "garantia", "troca": "troca", "carregador": "carregador",
        "duvida": "dúvida", "reclamacao": "reclamação", "suporte_tecnico": "suporte técnico",
        "financeiro": "questão financeira", "defeito_garantia": "defeito em garantia",
        "reenvio": "reenvio", "rastreamento": "rastreamento",
    }
    problem = category_labels.get(ticket.category, "sua solicitação")
    emojis = ["😞", "😕", "😐", "😊", "🤩"]
    labels = ["Péssimo", "Ruim", "Regular", "Bom", "Excelente"]

    stars_html = ""
    for i in range(5):
        score = i + 1
        stars_html += f'''
        <div style="text-align:center">
            <a href="/api/csat/{ticket.id}?token={token}&score={score}" class="star-btn">{emojis[i]}</a>
            <div class="star-label">{labels[i]}</div>
        </div>'''

    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Avalie seu atendimento - Carbon</title>{_base_style()}</head><body>
    <div class="card">
        <div class="logo">Carbon Smartwatch</div>
        <h2 style="font-size:20px; margin-bottom:8px;">Olá {customer_name}!</h2>
        <p class="subtitle">Como foi seu atendimento sobre {problem}?</p>
        <div class="ticket-info">
            <p>Ticket: <span>#{ticket.number}</span></p>
            <p>Assunto: <span>{ticket.subject}</span></p>
            {f'<p>Protocolo: <span>{ticket.protocol}</span></p>' if ticket.protocol else ''}
        </div>
        <p style="color:#a1a1aa; font-size:14px; margin:16px 0 8px;">Toque na nota:</p>
        <div class="stars">{stars_html}</div>
    </div>
    </body></html>"""


def _thankyou_html(ticket, score=None, already=False):
    if already:
        msg = "Você já avaliou este atendimento. Obrigado!"
    else:
        labels = {1: "Sentimos muito", 2: "Vamos melhorar", 3: "Obrigado", 4: "Que bom!", 5: "Incrível!"}
        msg = f"{labels.get(score, 'Obrigado')} pela sua avaliação!"

    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Obrigado - Carbon</title>{_base_style()}</head><body>
    <div class="card">
        <div class="success">✓</div>
        <div class="logo">Carbon Smartwatch</div>
        <h2 style="font-size:20px; margin:12px 0;">{msg}</h2>
        <p class="subtitle">Sua opinião é muito importante para nós.</p>
    </div>
    </body></html>"""


def _error_html(msg):
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Erro - Carbon</title>{_base_style()}</head><body>
    <div class="card">
        <div style="font-size:48px; margin-bottom:16px; color:#f87171;">✕</div>
        <div class="logo">Carbon Smartwatch</div>
        <h2 style="font-size:20px; margin:12px 0;">{msg}</h2>
    </div>
    </body></html>"""
