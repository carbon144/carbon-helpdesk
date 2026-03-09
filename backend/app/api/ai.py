"""AI triage and suggestion endpoints."""
from __future__ import annotations
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.kb_article import KBArticle
from app.services.ai_service import triage_ticket, suggest_reply, test_ai_connection, is_credits_exhausted, CreditExhaustedError, apply_triage_results

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
async def ai_status(user: User = Depends(get_current_user)):
    """Check AI integration status."""
    from app.core.config import settings
    if not settings.ANTHROPIC_API_KEY:
        return {"configured": False, "connected": False, "credits_exhausted": False}

    credits_out = is_credits_exhausted()
    if credits_out:
        return {
            "configured": True,
            "connected": False,
            "credits_exhausted": True,
            "error": "Creditos IA esgotados. Recarregue em console.anthropic.com",
        }

    result = test_ai_connection()
    return {
        "configured": True,
        "connected": result["ok"],
        "credits_exhausted": result.get("credits_exhausted", False),
        "model": result.get("model"),
        "error": result.get("error"),
    }


@router.post("/triage/{ticket_id}")
async def triage_single_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run AI triage on a single ticket."""
    if is_credits_exhausted():
        raise HTTPException(402, detail={"error": "credits_exhausted", "message": "Creditos IA esgotados. Recarregue em console.anthropic.com"})

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")

    # Get first inbound message
    msg_result = await db.execute(
        select(Message).where(
            Message.ticket_id == ticket_id,
            Message.type == "inbound",
        ).order_by(Message.created_at.asc()).limit(1)
    )
    first_msg = msg_result.scalar_one_or_none()
    body = first_msg.body_text if first_msg else ticket.subject

    is_repeat = ticket.customer.is_repeat if ticket.customer else False
    customer_name = ticket.customer.name if ticket.customer else ""

    try:
        triage = await triage_ticket(
            subject=ticket.subject,
            body=body,
            customer_name=customer_name,
            is_repeat=is_repeat,
        )
    except CreditExhaustedError:
        raise HTTPException(402, detail={"error": "credits_exhausted", "message": "Creditos IA esgotados. Recarregue em console.anthropic.com"})

    if not triage:
        raise HTTPException(500, "Falha na triagem IA")

    apply_triage_results(ticket, triage, customer=ticket.customer)

    # Recalc SLA based on new priority
    from datetime import datetime, timezone, timedelta
    from app.core.config import settings as cfg
    hours_map = {"urgent": cfg.SLA_URGENT_HOURS, "high": cfg.SLA_HIGH_HOURS, "medium": cfg.SLA_MEDIUM_HOURS, "low": cfg.SLA_LOW_HOURS}
    hours = hours_map.get(triage.get("priority", "medium"), 24)
    ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=hours)

    await db.commit()
    await db.refresh(ticket)

    return {
        "ok": True,
        "triage": triage,
        "ticket_id": ticket_id,
    }


class SuggestBody(BaseModel):
    partial_text: str | None = None

@router.post("/suggest/{ticket_id}")
async def suggest_ticket_reply(
    ticket_id: str,
    body_in: SuggestBody | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate AI suggested reply for a ticket."""
    if is_credits_exhausted():
        raise HTTPException(402, detail={"error": "credits_exhausted", "message": "Creditos IA esgotados. Recarregue em console.anthropic.com"})

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")

    # Get messages
    msg_result = await db.execute(
        select(Message).where(Message.ticket_id == ticket_id)
        .order_by(Message.created_at.desc()).limit(3)
    )
    messages = msg_result.scalars().all()
    body = "\n---\n".join([
        f"[{m.type}] {m.sender_name}: {m.body_text[:500]}" for m in reversed(messages) if m.body_text
    ])

    # Search KB for relevant articles
    kb_context = ""
    if ticket.category or ticket.ai_category:
        cat = ticket.category or ticket.ai_category
        kb_result = await db.execute(
            select(KBArticle).where(
                KBArticle.is_published == True,
                KBArticle.category == cat,
            ).limit(2)
        )
        articles = kb_result.scalars().all()
        if articles:
            kb_context = "\n\n".join([f"[{a.title}]\n{a.content[:500]}" for a in articles])

    customer_name = ticket.customer.name if ticket.customer else ""

    partial_text = body_in.partial_text if body_in and body_in.partial_text else ""

    try:
        suggestion = await suggest_reply(
            subject=ticket.subject,
            body=body,
            customer_name=customer_name,
            category=ticket.category or ticket.ai_category or "",
            kb_context=kb_context,
            partial_text=partial_text,
        )
    except CreditExhaustedError:
        raise HTTPException(402, detail={"error": "credits_exhausted", "message": "Creditos IA esgotados. Recarregue em console.anthropic.com"})

    if not suggestion:
        raise HTTPException(500, "Falha ao gerar sugestão")

    return {
        "ok": True,
        "suggestion": suggestion,
        "ticket_id": ticket_id,
    }


class CopilotRequest(BaseModel):
    ticket_id: str
    last_message: str | None = None


@router.post("/copilot")
async def copilot_analysis(
    body: CopilotRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI Copilot: real-time analysis of ticket to suggest KB articles, actions, and tips."""
    from app.core.config import settings as cfg
    if not cfg.ANTHROPIC_API_KEY:
        return {"tips": [], "kb_articles": [], "actions": [], "warning": "IA não configurada"}
    if is_credits_exhausted():
        return {"tips": [], "kb_articles": [], "actions": [], "warning": "credits_exhausted", "credits_exhausted": True}

    result = await db.execute(select(Ticket).where(Ticket.id == body.ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")

    # Get recent messages
    msg_result = await db.execute(
        select(Message).where(Message.ticket_id == body.ticket_id)
        .order_by(Message.created_at.desc()).limit(5)
    )
    messages = msg_result.scalars().all()
    conversation = "\n".join([
        f"[{m.type}] {m.sender_name}: {m.body_text[:300]}" for m in reversed(messages) if m.body_text
    ])

    # Get all KB articles
    kb_result = await db.execute(
        select(KBArticle).where(KBArticle.is_published == True)
    )
    all_articles = kb_result.scalars().all()
    kb_list = "\n".join([f"ID:{a.id}|{a.title}|Cat:{a.category}" for a in all_articles])

    try:
        from app.services.ai_service import get_client
        ai_client = get_client()

        prompt = f"""Analise este ticket de suporte e forneça insights para o atendente.

TICKET:
- Assunto: {ticket.subject}
- Categoria: {ticket.category or 'N/A'}
- Prioridade: {ticket.priority}
- Status: {ticket.status}
- Sentimento: {ticket.sentiment or 'N/A'}
- Tags: {', '.join(ticket.tags) if ticket.tags else 'N/A'}
- Risco jurídico: {'SIM' if ticket.legal_risk else 'NÃO'}

CONVERSA:
{conversation}

{f'ÚLTIMA MENSAGEM DO AGENTE: {body.last_message}' if body.last_message else ''}

ARTIGOS KB DISPONÍVEIS:
{kb_list}

Responda EXATAMENTE neste formato JSON:
{{
  "tips": ["dica1", "dica2"],
  "kb_article_ids": ["id1", "id2"],
  "actions": ["acao1", "acao2"],
  "sentiment_alert": "texto se cliente irritado/jurídico, ou null",
  "next_step": "próximo passo recomendado"
}}

Regras:
- tips: 1-3 dicas curtas de como lidar com este caso específico
- kb_article_ids: IDs dos artigos KB mais relevantes (max 3)
- actions: ações sugeridas (ex: "Escalar para supervisor", "Solicitar fotos do produto", "Verificar rastreio")
- sentiment_alert: alerta se tom do cliente precisa atenção especial
- next_step: 1 frase com o próximo passo ideal"""

        response = ai_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        text = response.content[0].text.strip()
        # Extract JSON from response
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        data = json.loads(text)

        # Map KB IDs to full article info
        kb_ids = data.get("kb_article_ids", [])
        kb_articles = [
            {"id": a.id, "title": a.title, "category": a.category, "content_preview": a.content[:200]}
            for a in all_articles if a.id in kb_ids
        ]

        return {
            "tips": data.get("tips", []),
            "kb_articles": kb_articles,
            "actions": data.get("actions", []),
            "sentiment_alert": data.get("sentiment_alert"),
            "next_step": data.get("next_step"),
        }

    except Exception as e:
        logger.warning(f"Copilot error: {e}")
        # Fallback: simple category-based suggestions
        tips = []
        actions = []
        if ticket.legal_risk:
            tips.append("⚠️ Risco jurídico detectado. Tome cuidado extra com palavras.")
            actions.append("Escalar para supervisor/jurídico")
        if ticket.sentiment in ("angry", "negative"):
            tips.append("Cliente insatisfeito. Use tom empático e proativo.")
        if ticket.category == "garantia":
            tips.append("Verificar se está dentro do prazo de 12 meses (ou 24 com Carbon Care) e se não é mau uso.")
        if ticket.category == "reenvio":
            tips.append("Confirmar se houve extravio, produto errado ou item faltante. Pedir evidências.")
        if ticket.category == "financeiro":
            tips.append("Arrependimento: 7 dias CDC. Estorno cartão até 3 faturas, Pix imediato.")
        if ticket.category == "meu_pedido":
            tips.append("Verificar status no Shopify e código de rastreamento antes de responder.")
        return {"tips": tips, "kb_articles": [], "actions": actions, "sentiment_alert": None, "next_step": None}


class AssistantRequest(BaseModel):
    message: str
    history: list[dict] = []


ASSISTANT_SYSTEM_PROMPT = """Você é o Assistente Carbon, uma IA interna da Carbon Relógios Inteligentes (www.carbonsmartwatch.com.br).

Seu papel é ajudar os funcionários do suporte com:
- Processos e playbooks de atendimento
- Políticas de garantia, troca, devolução
- Procedimentos para PROCON, Reclame Aqui, chargeback
- Identificação de mau uso vs defeito de fábrica
- Informações sobre produtos Carbon
- Dicas de atendimento ao cliente
- Processos de escalação e SLA
- Qualquer dúvida operacional da empresa

Regras:
- Responda SEMPRE em português brasileiro
- Seja direto e objetivo
- Quando não souber, diga que não tem a informação e sugira consultar a base de conhecimento ou um supervisor
- Não invente processos - baseie-se no conhecimento que tem
- Formate respostas de forma clara com tópicos quando necessário

Conhecimento base da Carbon:
- Garantia: 1 ano para defeitos de fabricação, não cobre mau uso (tela quebrada, entrada de água por uso incorreto, danos físicos)
- Troca: cliente tem 7 dias para troca por arrependimento (CDC). Após isso, somente por defeito.
- PROCON: prioridade máxima, prazo de 10 dias para resposta. Escalar para jurídico imediatamente.
- Chargeback: coletar evidências de entrega, prints, conversas. Escalar para financeiro.
- Carregadores: problema mais comum. Verificar se é o carregador original, testar com outro cabo. Garantia cobre carregador original.
- Reenvio: confirmar endereço, gerar novo código de rastreio, prazo de 7 a 15 dias úteis.
- SLA padrão: urgente 4h, alto 8h, médio 24h, baixo 48h (horas úteis).
- Escalação: tickets com risco jurídico, cliente muito insatisfeito, ou reincidente com 3+ tickets devem ser escalados ao supervisor.
"""


@router.post("/assistant")
async def assistant_chat(
    body: AssistantRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Internal AI assistant for staff - answers questions about processes, policies, etc."""
    from app.core.config import settings as cfg
    if not cfg.ANTHROPIC_API_KEY:
        raise HTTPException(500, "IA não configurada")
    if is_credits_exhausted():
        raise HTTPException(402, detail={"error": "credits_exhausted", "message": "Creditos IA esgotados. Recarregue em console.anthropic.com"})

    try:
        # Fetch KB articles for context
        kb_result = await db.execute(
            select(KBArticle).where(KBArticle.is_published == True).limit(10)
        )
        articles = kb_result.scalars().all()
        kb_context = ""
        if articles:
            kb_context = "\n\nBase de Conhecimento disponível:\n" + "\n".join(
                [f"- [{a.title}] {a.content[:300]}" for a in articles]
            )

        system_prompt = ASSISTANT_SYSTEM_PROMPT + kb_context

        from app.services.ai_service import get_client
        ai_client = get_client()
        messages = [{"role": m["role"], "content": m["content"]} for m in body.history[-8:]]
        messages.append({"role": "user", "content": body.message})

        response = ai_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )

        return {"response": response.content[0].text}
    except Exception as e:
        logger.error(f"Assistant error: {e}")
        raise HTTPException(500, f"Erro no assistente: {str(e)}")
