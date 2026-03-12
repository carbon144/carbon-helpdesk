"""AI Triage Service using Claude API."""
from __future__ import annotations
import asyncio as _asyncio
import json
import logging
import random as _random
import time
from anthropic import Anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _call_with_retry(func, max_retries=3):
    """Call a sync anthropic function with retry on 429/529."""
    for attempt in range(max_retries + 1):
        try:
            return await _asyncio.to_thread(func)
        except Exception as e:
            err_str = str(e)
            is_retryable = any(code in err_str for code in ["429", "500", "529", "overloaded", "rate_limit", "api_error", "Internal server error"])
            if not is_retryable or attempt == max_retries:
                raise
            delay = (2 ** attempt) + _random.uniform(0, 1)
            logger.warning(f"Anthropic retry {attempt+1}/{max_retries} after {delay:.1f}s: {err_str[:80]}")
            await _asyncio.sleep(delay)

client = None

# Credit exhaustion tracking
_credits_exhausted = False
_credits_exhausted_at: float = 0.0
_CREDITS_RETRY_INTERVAL = 300  # Retry every 5 minutes


def is_credits_exhausted() -> bool:
    """Check if AI credits are currently exhausted."""
    global _credits_exhausted, _credits_exhausted_at
    if not _credits_exhausted:
        return False
    # Auto-retry after interval
    if time.time() - _credits_exhausted_at > _CREDITS_RETRY_INTERVAL:
        _credits_exhausted = False
        return False
    return True


def _handle_credit_error(error: Exception) -> bool:
    """Check if error is credit-related. Returns True if it is."""
    global _credits_exhausted, _credits_exhausted_at
    error_str = str(error).lower()
    credit_keywords = ["credit", "balance", "billing", "insufficient", "exceeded", "quota"]
    if any(kw in error_str for kw in credit_keywords):
        if not _credits_exhausted:
            _credits_exhausted = True
            _credits_exhausted_at = time.time()
            logger.error(f"AI CREDITS EXHAUSTED: {error}")
            # Send Slack alert asynchronously
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(_send_credit_alert(str(error)))
            except Exception:
                pass
        return True
    return False


async def _send_credit_alert(error_msg: str):
    """Send Slack alert about credit exhaustion."""
    try:
        from app.services.slack_service import send_slack_message
        channel = settings.SLACK_SUPPORT_CHANNEL
        if channel:
            await send_slack_message(
                channel,
                f":rotating_light: *ALERTA: Creditos IA esgotados!*\n"
                f"Todas as funcoes de IA (triagem, sugestao, copilot, assistente) estao desativadas.\n"
                f"Erro: `{error_msg[:200]}`\n"
                f"Acao necessaria: recarregar creditos em console.anthropic.com"
            )
    except Exception as e:
        logger.error(f"Failed to send credit alert to Slack: {e}")


def get_client() -> Anthropic:
    global client
    if client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY não configurada")
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return client


def _clean_json(text: str) -> dict:
    """Parse JSON from Claude response, stripping markdown wrappers if present."""
    text = text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        lines = [l for l in lines if not l.strip().startswith('```')]
        text = '\n'.join(lines).strip()
    return json.loads(text)


def apply_triage_results(ticket, triage: dict, customer=None):
    """Apply AI triage results to a ticket (and optionally enrich customer).
    Centralizes the repeated triage-application logic.
    """
    if not triage:
        return
    if triage.get("category"):
        ticket.ai_category = triage["category"]
        ticket.category = triage["category"]
    if triage.get("priority"):
        ticket.priority = triage["priority"]
    if triage.get("sentiment"):
        ticket.sentiment = triage["sentiment"]
    if triage.get("legal_risk") is not None:
        ticket.legal_risk = triage["legal_risk"]
    if triage.get("tags"):
        existing = list(ticket.tags or [])
        ticket.tags = list(set(existing + triage["tags"]))
    if triage.get("confidence"):
        ticket.ai_confidence = triage["confidence"]
        # Low confidence → flag for human review
        if triage["confidence"] < 0.5:
            existing = list(ticket.tags or [])
            ticket.tags = list(set(existing + ["revisao_manual"]))

    # ── Priority override by keywords (only UPGRADE, never downgrade) ──
    PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2, "urgent": 3}
    current_rank = PRIORITY_RANK.get(ticket.priority, 1)
    _text = f"{getattr(ticket, 'subject', '')} {triage.get('summary', '')}".lower()
    URGENT_KEYWORDS = ["procon", "advogado", "processo", "juizado", "danos morais"]
    HIGH_KEYWORDS = ["reclame aqui", "reclameaqui", "chargeback", "reembolso"]
    if any(kw in _text for kw in URGENT_KEYWORDS) and current_rank < 3:
        ticket.priority = "urgent"
    elif any(kw in _text for kw in HIGH_KEYWORDS) and current_rank < 2:
        ticket.priority = "high"

    # Enrich customer data if available
    if customer:
        ai_data = triage.get("customer_data")
        if ai_data and isinstance(ai_data, dict):
            if ai_data.get("cpf") and not getattr(customer, 'cpf', None):
                customer.cpf = ai_data["cpf"]
            if ai_data.get("phone") and not getattr(customer, 'phone', None):
                customer.phone = ai_data["phone"]
            if ai_data.get("full_name") and getattr(customer, 'name', '') == getattr(customer, 'email', ''):
                customer.name = ai_data["full_name"]


TRIAGE_SYSTEM_PROMPT = """Você é o triador do suporte da Carbon Smartwatch (empresa brasileira de smartwatches).

Analise a mensagem e retorne APENAS JSON válido (sem markdown):

{
  "category": "UMA das categorias abaixo",
  "priority": "low | medium | high | urgent",
  "sentiment": "positive | neutral | negative | angry",
  "legal_risk": true ou false,
  "tags": ["tags da lista abaixo"],
  "confidence": 0.0 a 1.0,
  "summary": "problema → próximo passo pro agente",
  "customer_data": {
    "cpf": "apenas dígitos, 11 chars",
    "phone": "apenas dígitos",
    "order_number": "apenas dígitos",
    "full_name": "nome completo"
  }
}

CATEGORIAS (exatamente estes valores):
- meu_pedido: quer saber onde está o pedido, rastreio, nota fiscal, cancelar, pedido incompleto
- garantia: defeito, troca, devolução, produto errado, carregador quebrado, assistência, mau uso
- reenvio: produto extraviado, não chegou E quer que envie de novo
- financeiro: estorno, reembolso, chargeback, dúvida de pagamento
- duvida: pré-venda, como usar, funcionalidades, elogio, sugestão, feedback positivo
- reclamacao: insatisfação, reclamação genérica, acha que é golpe, menciona GUACU

REGRA meu_pedido vs reenvio:
- "Cadê meu pedido?" / "Quero rastreio" → meu_pedido (quer SABER onde está)
- "Não chegou, quero que enviem de novo" → reenvio (quer NOVO ENVIO)

CONTEXTO IMPORTANTE:
- GUACU NEGOCIOS DIGITAIS LTDA = Carbon Smartwatch. Mesma empresa. Cliente que menciona GUACU/golpe/fraude → reclamacao + tag guacu
- Garantia: 12 meses contra defeitos de fabricação
- Não tem assistência técnica — troca direta na garantia
- Houve atrasos em pedidos jan-fev 2026 por problema de importação. Já corrigido.

TAGS (detalham o que a categoria não diz):
guacu, procon, advogado, reclame_aqui, chargeback, mau_uso, carregador, defeito, troca, nf, reembolso, reincidente

PRIORIDADE:
- urgent: PROCON, chargeback, advogado, Reclame Aqui, juizado, danos morais
- high: defeito grave, cliente reincidente, produto não chegou, reclamação forte
- medium: trocas, problemas técnicos, dúvidas sobre entrega
- low: dúvidas simples, elogios, feedback positivo

legal_risk = true se menciona: PROCON, processo, advogado, Reclame Aqui, chargeback, danos morais, juizado

SUMMARY — escreva como BRIEFING pro agente (problema → o que fazer):
- BOM: "Pedido #54321 não entregue há 15 dias → buscar rastreio no Shopify"
- BOM: "Relógio não liga após 3 meses → garantia ativa, iniciar troca via Troque"
- BOM: "Acha que Carbon é golpe (GUACU) → explicar que é mesma empresa"
- RUIM: "Cliente reclama que pedido não chegou" (não diz o que fazer)

Se não encontrar dados do cliente, retorne customer_data como null."""


SUGGEST_SYSTEM_PROMPT = """Você é um agente de suporte da Carbon Smartwatch. Sugira uma resposta empática e direta para o ticket abaixo.

Regras:
- Cumprimente o cliente pelo nome
- Tom casual e empático, direto ao ponto
- Português brasileiro
- Não invente informações que não conhece
- Categorias do ticket: meu_pedido, garantia, reenvio, financeiro, duvida, reclamacao
- Garantia: 12 meses contra defeitos de fabricação. Troca direta (sem assistência técnica)
- Mau uso: não é coberto pela garantia. Explique com delicadeza
- GUACU NEGOCIOS DIGITAIS = Carbon (mesma empresa, mesmo CNPJ). Não é golpe
- Risco jurídico: seja extra cuidadoso, sugira escalar para supervisor
- Máximo 4 parágrafos. Texto simples, sem markdown

Resistência à água por modelo (NUNCA inventar IP68/IP67):
- Raptor: 5ATM, Atlas: 3ATM, One Max/Aurora/Quartz: 1ATM
- NENHUM modelo é IP68/IP67. NENHUM tem NFC.
- Raptor e Atlas servem para natação. Os demais NÃO.

Apps: Raptor/Atlas = GloryFitPro. One Max/Aurora = DaFit.

Retorne APENAS o texto da resposta sugerida."""


# ── Keyword fallback when AI is unavailable ──
_KEYWORD_FALLBACK = {
    "reclamacao": ["procon", "advogado", "processo", "juizado", "danos morais", "reclame aqui", "reclameaqui", "golpe", "guacu", "fraude", "enganosa"],
    "financeiro": ["estorno", "reembolso", "cancelar", "cancelamento", "dinheiro de volta", "chargeback", "pagamento"],
    "reenvio": ["extraviado", "não recebi", "nao recebi", "reenvio", "reenviar", "enviar de novo", "enviem novamente"],
    "garantia": ["defeito", "garantia", "quebrou", "não liga", "nao liga", "não funciona", "nao funciona", "carregador", "troca", "trocar", "devolver", "devolução"],
    "meu_pedido": ["rastreio", "rastreamento", "entrega", "pedido", "nota fiscal", "onde está", "onde esta", "cadê", "cade", "status"],
    "duvida": ["dúvida", "duvida", "como funciona", "pergunta", "informação", "informacao"],
}

_LEGAL_KEYWORDS = ["procon", "advogado", "processo", "juizado", "danos morais", "reclame aqui", "reclameaqui", "chargeback"]


def _fallback_triage(subject: str, body: str) -> dict:
    """Keyword-based fallback when AI credits are exhausted."""
    text = f"{subject} {body[:1000]}".lower()
    category = "duvida"
    priority = "medium"
    legal_risk = False
    tags = []

    # Check legal risk first
    if any(kw in text for kw in _LEGAL_KEYWORDS):
        legal_risk = True
        priority = "urgent"

    # Match category (order matters: more specific first)
    for cat, keywords in _KEYWORD_FALLBACK.items():
        if any(kw in text for kw in keywords):
            category = cat
            break

    if "guacu" in text or "golpe" in text:
        tags.append("guacu")
    if "reincidente" in text or "de novo" in text:
        tags.append("reincidente")

    return {
        "category": category,
        "priority": priority,
        "sentiment": "neutral",
        "legal_risk": legal_risk,
        "tags": tags,
        "confidence": 0.3,
        "summary": f"{subject[:100]}",
        "customer_data": None,
    }


async def triage_ticket(subject: str, body: str, customer_name: str = "", is_repeat: bool = False) -> dict | None:
    """Classify a ticket using Claude AI. Falls back to keywords if AI unavailable."""
    if is_credits_exhausted():
        logger.warning("AI triage unavailable, using keyword fallback")
        return _fallback_triage(subject, body)
    try:
        ai = get_client()

        user_msg = f"Assunto: {subject}\n\nMensagem do cliente"
        if customer_name:
            user_msg += f" ({customer_name})"
        if is_repeat:
            user_msg += " [CLIENTE REINCIDENTE]"
        user_msg += f":\n{body[:2000]}"

        triage_model = getattr(settings, 'ANTHROPIC_TRIAGE_MODEL', None) or "claude-haiku-4-5-20251001"
        response = await _call_with_retry(
            lambda: ai.messages.create(
                model=triage_model,
                max_tokens=500,
                system=TRIAGE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
        )

        text = response.content[0].text.strip()
        # Try to parse JSON
        result = _clean_json(text)
        logger.info(f"AI triage result: category={result.get('category')}, priority={result.get('priority')}")

        # Extract customer_data if present (backward compatible)
        customer_data = result.get("customer_data")
        if customer_data and isinstance(customer_data, dict):
            # Clean up empty/null values
            customer_data = {k: v for k, v in customer_data.items() if v}
            result["customer_data"] = customer_data if customer_data else None
        else:
            result["customer_data"] = None

        return result
    except json.JSONDecodeError as e:
        logger.error(f"AI returned invalid JSON: {e}")
        return None
    except Exception as e:
        _handle_credit_error(e)
        logger.error(f"AI triage failed: {e}")
        return None


async def suggest_reply(subject: str, body: str, customer_name: str = "", category: str = "", kb_context: str = "", partial_text: str = "") -> str | None:
    """Generate a suggested reply using Claude AI. If partial_text is provided, complete it."""
    if is_credits_exhausted():
        raise CreditExhaustedError("Creditos IA esgotados")
    try:
        ai = get_client()

        user_msg = f"Ticket: {subject}\nCliente: {customer_name or 'N/A'}\nCategoria: {category or 'N/A'}\n\nMensagem:\n{body[:2000]}"

        if kb_context:
            user_msg += f"\n\n--- Base de Conhecimento relevante ---\n{kb_context[:1500]}"

        system_prompt = SUGGEST_SYSTEM_PROMPT
        if partial_text:
            user_msg += f"\n\n--- O agente já começou a escrever ---\n{partial_text}"
            system_prompt += "\n\nIMPORTANTE: O agente já começou a escrever uma resposta. Complete a resposta dele de forma natural, continuando de onde ele parou. Retorne APENAS a continuação, não repita o que ele já escreveu."

        response = await _call_with_retry(
            lambda: ai.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=400 if partial_text else 800,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
        )

        return response.content[0].text.strip()
    except Exception as e:
        if _handle_credit_error(e):
            raise CreditExhaustedError("Creditos IA esgotados")
        logger.error(f"AI suggest reply failed: {e}")
        return None


SUMMARY_SYSTEM_PROMPT = """Você é um assistente de suporte da Carbon Smartwatch.
Analise o histórico de mensagens do ticket e gere um resumo executivo em português brasileiro.

O resumo deve ter no máximo 3 frases e incluir:
1. O problema principal do cliente
2. O que já foi feito/tentado
3. O status atual / próximo passo

Retorne APENAS o texto do resumo, sem JSON, sem markdown."""


async def summarize_ticket(subject: str, messages: list[dict], category: str = "", customer_name: str = "") -> str | None:
    """RF-019: Generate AI summary from ticket conversation history."""
    if is_credits_exhausted():
        raise CreditExhaustedError("Creditos IA esgotados")
    try:
        ai = get_client()

        # Build conversation context
        conversation = f"Assunto: {subject}\nCliente: {customer_name or 'N/A'}\nCategoria: {category or 'N/A'}\n\n"
        conversation += "--- Histórico de mensagens ---\n"
        for msg in messages[-15:]:  # Last 15 messages max
            sender = msg.get("sender_name", "Desconhecido")
            mtype = msg.get("type", "inbound")
            prefix = "CLIENTE" if mtype == "inbound" else "AGENTE"
            body = (msg.get("body_text", "") or "")[:500]
            conversation += f"[{prefix} - {sender}]: {body}\n\n"

        response = await _call_with_retry(
            lambda: ai.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=300,
                system=SUMMARY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": conversation[:4000]}],
            )
        )

        return response.content[0].text.strip()
    except Exception as e:
        if _handle_credit_error(e):
            raise CreditExhaustedError("Creditos IA esgotados")
        logger.error(f"AI summary failed: {e}")
        return None


AUTO_REPLY_SYSTEM_PROMPT = """Você é a assistente virtual da Carbon nos canais de mensagem (WhatsApp, Instagram, Facebook).
A Carbon é uma marca brasileira de smartwatches e acessórios.

REGRAS ABSOLUTAS:
- NUNCA inventar informações. Se não sabe, sinalize should_escalate=true.
- NUNCA sugerir Procon, Reclame Aqui, advogado ou qualquer órgão ao cliente.
- NUNCA dizer "Carbon Smartwatch". Sempre apenas "Carbon".
- NUNCA mencionar importação, China, alfândega.
- NUNCA mencionar espontaneamente que a NF é de serviço ou intermediação. SÓ explique se o cliente perguntar.
- Respostas curtas (máximo 3 parágrafos) em português brasileiro.
- Sem emojis exagerados (máximo 1 por mensagem).

REGRAS DE NEGÓCIO:
- Modelos atuais: Carbon Raptor, Atlas, One Max, Aurora, Quartz
- Carbon One (DESCONTINUADO): modelo antigo, pulseira 24mm. Carbon One Max é a evolução do Carbon One, pulseira 22mm. NÃO são compatíveis entre si (pulseiras diferentes).
- Garantia: legal 90 dias + contratual 12 meses. Carbon Care estende pra 24 meses (upsell).
- NÃO temos assistência técnica. Dentro da garantia: troca por novo. Fora: cupom de desconto.
- Portal trocas/devoluções: carbonsmartwatch.troque.app.br (sempre direcionar pra lá)
- Cancelamento antes de enviar: ok. Depois: recusar entrega ou devolver em 7 dias.
- Estorno: até 10 dias úteis. Pix direto. Cartão até 3 faturas.
- Suporte: tentar reset de fábrica primeiro.
- Apps: Raptor/Atlas = GloryFitPro. One Max/Aurora = DaFit.
- NF (SÓ se perguntar): Carbon atua como intermediadora comercial, NF emitida nessa modalidade (legal e correta). Valor integral registrado, validade fiscal normal, serve como comprovante pra tudo incluindo garantia.

RESISTÊNCIA À ÁGUA (NUNCA inventar IP68, IP67 ou qualquer classificação IP):
- Raptor: 5ATM (respingos, chuva, banho, piscina, natação)
- Atlas: 3ATM (respingos, chuva, banho, piscina, natação)
- One Max: 1ATM (respingos leves, suor — NÃO molhar)
- Aurora: 1ATM (respingos leves, suor — NÃO molhar)
- Quartz: 1ATM (respingos leves, suor — NÃO molhar)
- NENHUM modelo é IP68 ou IP67.
- Raptor e Atlas servem para natação. One Max, Aurora e Quartz NÃO.
- NFC: NENHUM modelo possui NFC.

PRAZOS DE ENTREGA POR REGIÃO:
- Sudeste: 7 a 12 dias úteis
- Sul: 7 a 14 dias úteis
- Centro-Oeste: 8 a 16 dias úteis
- Nordeste: 10 a 20 dias úteis
- Norte: 12 a 25 dias úteis

TOM: casual e direto, como se fosse um amigo ajudando. Use "você", não "senhor/senhora". Máximo 1 emoji por mensagem.

ESCALAR (should_escalate=true) quando:
- Procon, advogado, processo, Reclame Aqui, chargeback, danos morais
- Reembolso/cancelamento (precisa aprovação humana)
- Problema técnico que reset não resolveu
- Cliente irritado após 2+ mensagens
- Qualquer coisa que não sabe com certeza

Frase de escalação: "Vou transferir para um atendente da Carbon que vai resolver isso pra você."

Retorne APENAS JSON válido (sem markdown):
{"response": "texto", "should_escalate": true/false, "escalation_reason": "motivo ou vazio"}"""


async def ai_auto_reply(
    ticket_subject: str,
    conversation_history: list[dict],
    customer_name: str = "",
    category: str = "",
    kb_context: str = "",
    platform: str = "whatsapp",
) -> dict | None:
    """Generate an automatic AI reply for Meta channels (WhatsApp/Instagram/Facebook)."""
    if is_credits_exhausted():
        logger.warning("AI auto-reply skipped: credits exhausted")
        return None
    try:
        ai = get_client()

        user_msg = f"Canal: {platform}\nCliente: {customer_name or 'N/A'}\nCategoria: {category or 'N/A'}\n"
        user_msg += f"Assunto original: {ticket_subject}\n\n"

        if kb_context:
            user_msg += f"--- Base de Conhecimento ---\n{kb_context[:2000]}\n\n"

        user_msg += "--- Conversa ---\n"
        for msg in conversation_history[-20:]:
            role_label = "CLIENTE" if msg["role"] == "customer" else "CARBON IA"
            user_msg += f"[{role_label}]: {msg['content']}\n\n"

        response = await _call_with_retry(
            lambda: ai.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=600,
                system=AUTO_REPLY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg[:6000]}],
            )
        )

        text = response.content[0].text.strip()
        result = _clean_json(text)
        logger.info(f"AI auto-reply: escalate={result.get('should_escalate', False)}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"AI auto-reply returned invalid JSON: {e}")
        return None
    except Exception as e:
        _handle_credit_error(e)
        logger.error(f"AI auto-reply failed: {e}")
        return None


MODERATE_COMMENT_PROMPT = """Você é o moderador de redes sociais da Carbon Smartwatch (Instagram e Facebook).

Analise o comentário abaixo e decida a ação. Retorne APENAS um JSON válido (sem markdown):

{
  "action": "reply" | "hide_reply" | "hide" | "ignore",
  "reply": "texto da resposta (ou string vazia se action=hide/ignore)",
  "sentiment": "positive" | "neutral" | "negative" | "offensive",
  "category": "elogio" | "duvida" | "reclamacao" | "ofensivo" | "spam" | "mencao" | "outro",
  "confidence": 0.0 a 1.0
}

Regras de AÇÃO:
- "reply": responde publicamente ao comentário (elogios, dúvidas, reclamações moderadas)
- "hide_reply": OCULTA o comentário E responde em privado/publicamente (ofensivo mas merece resposta)
- "hide": apenas oculta sem responder (spam, palavrões sem contexto, conteúdo impróprio)
- "ignore": não faz nada (emojis solo como 🔥❤️, tags de amigos como "@fulano", risadas "kkkk", "kkk" sem contexto)

Regras de RESPOSTA:
- Respostas CURTAS (máximo 2 frases) — é comentário de rede social, não e-mail
- Tom amigável e leve, pode usar 1-2 emojis
- Português brasileiro
- Para elogios: agradeça com entusiasmo
- Para dúvidas: responda objetivamente ou direcione ao DM/link da bio
- Para reclamações: peça para enviar DM com detalhes
- Para ofensivos: responda com educação e firmeza se for hide_reply
- NUNCA responda com agressividade ou sarcasmo
- NUNCA invente informações sobre produtos

Contexto: Carbon Smartwatch — smartwatches, carregadores magnéticos, pulseiras. Garantia 1 ano."""


async def moderate_comment(
    comment_text: str,
    author_name: str = "",
    post_caption: str = "",
    platform: str = "instagram",
) -> dict | None:
    """Analyze a social media comment and decide moderation action.

    Returns: {"action": str, "reply": str, "sentiment": str, "category": str, "confidence": float}
    """
    if is_credits_exhausted():
        logger.warning("Comment moderation skipped: credits exhausted")
        return None
    try:
        ai = get_client()

        user_msg = f"Plataforma: {platform}\n"
        if author_name:
            user_msg += f"Autor: {author_name}\n"
        if post_caption:
            user_msg += f"Legenda do post: {post_caption[:300]}\n"
        user_msg += f"\nComentário:\n{comment_text}"

        response = await _call_with_retry(
            lambda: ai.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=400,
                system=MODERATE_COMMENT_PROMPT,
                messages=[{"role": "user", "content": user_msg[:3000]}],
            )
        )

        text = response.content[0].text.strip()
        result = _clean_json(text)
        logger.info(f"Comment moderation: action={result.get('action')}, sentiment={result.get('sentiment')}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Comment moderation returned invalid JSON: {e}")
        return None
    except Exception as e:
        _handle_credit_error(e)
        logger.error(f"Comment moderation failed: {e}")
        return None


import re as _re


CHAT_SYSTEM_PROMPT = """Você é a assistente virtual da Carbon nos canais de chat (WhatsApp, Instagram, Facebook).
A Carbon é uma marca brasileira de smartwatches e acessórios.

=== REGRAS ABSOLUTAS — NUNCA VIOLAR ===

1. NUNCA INVENTAR INFORMAÇÃO. Se você não sabe algo com certeza, diga:
   "Não tenho essa informação no momento. Vou transferir para a equipe que pode te ajudar."
   E sinalize confidence=low.

2. NUNCA SUGERIR que o cliente vá ao Procon, Reclame Aqui, advogado, justiça ou qualquer órgão.
   Se o cliente mencionar esses termos, responda com empatia e transfira para atendente.
   NUNCA diga frases como "você tem direito de procurar o Procon" ou "caso não resolva, você pode...".

3. NUNCA DIZER "Carbon Smartwatch". Sempre apenas "Carbon".

4. NUNCA MENCIONAR importação, China, produtos importados, alfândega, fiscalização aduaneira.

5. NUNCA PROMETER prazos, valores ou ações que você não tem certeza.
   Prazos permitidos (esses você PODE dizer):
   - Estorno: até 10 dias úteis
   - Estorno cartão: pode levar até 3 faturas
   - Estorno Pix: devolvido direto após aprovação

6. NUNCA RESPONDER sobre assuntos que não sejam relacionados à Carbon e seus produtos.

7. NUNCA mencionar espontaneamente que a NF é de serviço ou de intermediação.
   SÓ explique sobre o modelo da NF se o cliente PERGUNTAR ou QUESTIONAR diretamente.

=== TOM E ESTILO ===

- Português brasileiro, profissional e direto
- Respostas CURTAS — é um chat, não e-mail. Máximo 3 parágrafos
- Sem emojis exagerados — no máximo 1 por mensagem, e só se natural
- Chamar o cliente pelo nome quando disponível
- Se apresentar na primeira mensagem: "Olá! Sou a assistente virtual da Carbon."

=== REGRAS DE NEGÓCIO ===

PRODUTOS:
- Modelos atuais: Carbon Raptor, Carbon Atlas, Carbon One Max, Carbon Aurora, Carbon Quartz
- Carbon One (DESCONTINUADO): modelo antigo, pulseira 24mm. Carbon One Max é a evolução, pulseira 22mm. Pulseiras NÃO são compatíveis entre si.
- Carregador magnético incluso
- Pulseiras de silicone, metal e luxe

GARANTIA:
- Prazo: 1 ano a partir da data de compra
- Verificar data no Shopify antes de confirmar garantia
- NÃO temos assistência técnica nem reparos
- Se na garantia: troca por produto novo
- Portal de trocas: carbonsmartwatch.troque.app.br

CANCELAMENTO:
- Antes de faturar/enviar: pode cancelar, estorno em até 10 dias úteis
- Depois de enviado: recusar a entrega ou devolver em até 7 dias após receber
- Pix: devolvido direto. Cartão: até 3 faturas

NOTA FISCAL (SÓ responder se o cliente perguntar/questionar):
- A NF é enviada automaticamente por e-mail após faturamento
- A Carbon atua como intermediadora comercial — CNPJ enquadrado como intermediação de negócios
- A NF é emitida nessa modalidade, que é o formato correto e legal
- Não conseguimos emitir de outra forma porque o CNPJ não permite
- O valor integral da compra está registrado na nota
- Tem a mesma validade fiscal e serve como comprovante para todos os fins, incluindo garantia
- NUNCA mencionar "nota de serviço" espontaneamente — só se o cliente perguntar

RESISTÊNCIA À ÁGUA (NUNCA inventar IP68, IP67 ou qualquer classificação IP):
- Raptor: 5ATM (respingos, chuva, banho, piscina, natação)
- Atlas: 3ATM (respingos, chuva, banho, piscina, natação)
- One Max: 1ATM (respingos leves, suor — NÃO molhar)
- Aurora: 1ATM (respingos leves, suor — NÃO molhar)
- Quartz: 1ATM (respingos leves, suor — NÃO molhar)
- NENHUM modelo é IP68 ou IP67. Nunca usar classificação IP.
- Raptor e Atlas servem para natação. One Max, Aurora e Quartz NÃO.
- NFC: NENHUM modelo possui NFC.

APPS:
- Raptor/Atlas = GloryFitPro
- One Max/Aurora = DaFit

SUPORTE TÉCNICO:
- Primeiro passo: reset de fábrica (Configurações > Restaurar padrão)
- Segundo: reconectar pelo app
- Se não resolver: transferir para agente

CUPONS CARBON CARE CLUB (só oferecer em casos de insatisfação):
- 5% para casos fáceis
- 8% para convencimento
- 12% para recuperação
- 18% para casos críticos (último recurso)

=== QUANDO ESCALAR (confidence=low) ===

SEMPRE escalar para agente humano quando:
- Cliente menciona Procon, advogado, processo, Reclame Aqui, chargeback, danos morais
- Pedido de reembolso/cancelamento (precisa aprovação humana)
- Problema técnico que reset não resolveu
- Cliente irritado após 2+ mensagens sem resolução
- Qualquer coisa que você não sabe responder com certeza

Frase de escalação:
"Vou transferir para um atendente da Carbon que vai resolver isso pra você."

=== FORMATO DE RESPOSTA ===

Responda SEMPRE em JSON válido (sem markdown, sem delimitadores):
{"response": "texto da resposta", "confidence": "high|medium|low"}

- high: certeza absoluta baseada em dados/KB/regras acima
- medium: resposta razoável baseada nas regras gerais
- low: não tem informação suficiente — VAI ESCALAR para agente"""


async def chat_auto_reply(
    messages: list[dict],
    contact_shopify_data: dict | None = None,
    kb_articles: list[dict] | None = None,
) -> dict:
    """Generate an automatic reply for chat conversations with confidence assessment.

    Used by the chat message pipeline.
    Returns dict with keys: response (str), confidence (str), resolved (bool).
    """
    if is_credits_exhausted() or not settings.ANTHROPIC_API_KEY:
        return {"response": "", "confidence": "none", "resolved": False}

    system_prompt = CHAT_SYSTEM_PROMPT

    context_parts = []
    if contact_shopify_data:
        context_parts.append(f"Dados Shopify do cliente:\n{json.dumps(contact_shopify_data, ensure_ascii=False, indent=2)}")
    if kb_articles:
        articles_text = "\n\n".join(
            f"Artigo: {a.get('title', '')}\n{a.get('content', '')}" for a in kb_articles
        )
        context_parts.append(f"Artigos da base de conhecimento:\n{articles_text}")

    if context_parts:
        system_prompt += "\nContexto:\n" + "\n\n".join(context_parts)

    claude_messages = []
    for msg in messages:
        role = "user" if msg.get("role") == "contact" else "assistant"
        claude_messages.append({"role": role, "content": msg["content"]})

    if not claude_messages or claude_messages[-1]["role"] != "user":
        claude_messages.append({"role": "user", "content": "Responda ao cliente."})

    try:
        ai = get_client()
        response = await _call_with_retry(
            lambda: ai.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=1024,
                system=system_prompt,
                messages=claude_messages,
            )
        )

        text = response.content[0].text.strip()

        # Try to parse JSON response
        try:
            # Try parsing the full text as JSON first
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                # Find JSON by matching balanced braces
                start = text.find("{")
                if start >= 0:
                    depth = 0
                    for i, ch in enumerate(text[start:], start):
                        if ch == "{": depth += 1
                        elif ch == "}": depth -= 1
                        if depth == 0:
                            parsed = json.loads(text[start:i+1])
                            break
                    else:
                        parsed = None
                else:
                    parsed = None
            if parsed:
                confidence = parsed.get("confidence", "medium")
                if confidence not in ("high", "medium", "low"):
                    confidence = "medium"
                return {
                    "response": parsed.get("response", text),
                    "confidence": confidence,
                    "resolved": confidence in ("high", "medium"),
                }
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: treat plain text as medium confidence
        return {
            "response": text,
            "confidence": "medium",
            "resolved": True,
        }
    except Exception as e:
        _handle_credit_error(e)
        logger.error(f"Chat auto-reply failed: {e}")
        return {"response": "", "confidence": "none", "resolved": False}


class CreditExhaustedError(Exception):
    """Raised when AI credits are exhausted."""
    pass


async def test_ai_connection() -> dict:
    """Test if Claude AI is reachable (async to avoid blocking event loop)."""
    if is_credits_exhausted():
        return {"ok": False, "error": "credits_exhausted", "credits_exhausted": True}
    try:
        import asyncio
        ai = get_client()
        response = await asyncio.to_thread(
            ai.messages.create,
            model=settings.ANTHROPIC_MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": "Diga apenas 'ok'"}],
        )
        return {"ok": True, "model": settings.ANTHROPIC_MODEL}
    except Exception as e:
        is_credit = _handle_credit_error(e)
        return {"ok": False, "error": str(e), "credits_exhausted": is_credit}
