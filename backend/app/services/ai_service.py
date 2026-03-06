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
    credit_keywords = ["credit", "balance", "billing", "insufficient", "exceeded", "quota", "rate_limit"]
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

    # ── Priority override by keywords ──
    _text = f"{getattr(ticket, 'subject', '')} {triage.get('summary', '')}".lower()
    HIGH_KEYWORDS = ["reclame aqui", "reclameaqui", "reembolso", "procon", "advogado", "juridico", "processo"]
    if any(kw in _text for kw in HIGH_KEYWORDS):
        ticket.priority = "high"
    elif ticket.priority == "medium":
        MEDIUM_KEYWORDS = ["rastreio", "rastreamento", "status", "prazo", "entrega"]
        if any(kw in _text for kw in MEDIUM_KEYWORDS):
            ticket.priority = "medium"  # keep medium explicitly

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


TRIAGE_SYSTEM_PROMPT = """Você é um assistente de triagem para o suporte da Carbon Smartwatch, uma empresa brasileira de smartwatches.

Analise a mensagem do cliente e retorne APENAS um JSON válido (sem markdown, sem texto extra) com:

{
  "category": "UMA das categorias abaixo",
  "priority": "low | medium | high | urgent",
  "sentiment": "positive | neutral | negative | angry",
  "legal_risk": true ou false,
  "tags": ["tags relevantes da lista abaixo"],
  "confidence": 0.0 a 1.0,
  "summary": "resumo em 1 frase do problema",
  "customer_data": {
    "cpf": "CPF se encontrado (apenas dígitos, 11 chars)",
    "phone": "telefone se encontrado (apenas dígitos)",
    "order_number": "número do pedido se encontrado (apenas dígitos)",
    "full_name": "nome completo se identificado"
  }
}

CATEGORIAS (use exatamente estes valores):
- defeito_garantia: produto com defeito dentro da garantia de 1 ano
- troca: solicitação de troca (tamanho, cor, modelo)
- reenvio: produto não chegou, extraviado, precisa reenviar
- rastreamento: dúvida sobre status de entrega, código de rastreio
- mau_uso: produto danificado por mau uso (tela quebrada, molhou além do IP, etc)
- carregador: problema específico com carregador magnético
- suporte_tecnico: problemas de software, app, bluetooth, configuração
- chargeback: cliente abriu disputa no cartão
- procon: mencionou PROCON, processo, advogado, danos morais
- reclame_aqui: mencionou Reclame Aqui
- financeiro: reembolso, estorno, pagamento, nota fiscal
- duvida: dúvida geral sobre produto, funcionalidades, compra
- reclamacao: reclamação genérica que não se encaixa nas acima
- elogio: feedback positivo, elogio

TAGS possíveis: garantia, troca, carregador, mau_uso, procon, chargeback, reclame_aqui, reenvio, rastreamento, defeito, reembolso, duvida, elogio

Regras de prioridade:
- urgent: risco jurídico (PROCON, chargeback, advogado, Reclame Aqui), cliente muito irritado
- high: reclamação forte, defeito grave, cliente reincidente, produto não chegou
- medium: trocas normais, problemas técnicos comuns, dúvidas sobre entrega
- low: dúvidas simples, elogios, feedback positivo

legal_risk = true se menciona: PROCON, processo, advogado, Reclame Aqui, chargeback, danos morais, juizado

Se não encontrar dados do cliente, retorne customer_data como null.

Contexto: smartwatches Carbon, carregadores magnéticos, pulseiras, garantia de 1 ano."""


SUGGEST_SYSTEM_PROMPT = """Você é um agente de suporte da Carbon Smartwatch. Sugira uma resposta profissional e empática para o ticket abaixo.

Regras:
- Sempre cumprimente o cliente pelo nome
- Seja empático e profissional
- Use português brasileiro
- Não invente informações sobre políticas que não conhece
- Se for garantia: mencione que o prazo é de 1 ano
- Se for mau uso: explique com delicadeza que não é coberto pela garantia
- Se houver risco jurídico: seja extra cuidadoso e sugira escalar para supervisor
- Mantenha a resposta concisa (máximo 5 parágrafhs)
- NÃO use markdown, use texto simples

Retorne APENAS o texto da resposta sugerida, sem JSON, sem explicações."""


async def triage_ticket(subject: str, body: str, customer_name: str = "", is_repeat: bool = False) -> dict | None:
    """Classify a ticket using Claude AI."""
    if is_credits_exhausted():
        logger.warning("AI triage skipped: credits exhausted")
        return None
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


AUTO_REPLY_SYSTEM_PROMPT = """Voce e a assistente virtual da Carbon nos canais de mensagem (WhatsApp, Instagram, Facebook).
A Carbon e uma marca brasileira de smartwatches e acessorios.

REGRAS ABSOLUTAS:
- NUNCA inventar informacoes. Se nao sabe, sinalize should_escalate=true.
- NUNCA sugerir Procon, Reclame Aqui, advogado ou qualquer orgao ao cliente.
- NUNCA dizer "Carbon Smartwatch". Sempre apenas "Carbon".
- NUNCA mencionar importacao, China, alfandega.
- Respostas curtas (maximo 3 paragrafos) em portugues brasileiro.
- Sem emojis exagerados (maximo 1 por mensagem).

REGRAS DE NEGOCIO:
- Modelos: Carbon Raptor, Atlas, One Max, Aurora, Quartz
- Garantia: 1 ano. NAO temos assistencia tecnica. Troca por novo se na garantia.
- Portal trocas: carbonsmartwatch.troque.app.br
- Cancelamento antes de enviar: ok. Depois: recusar entrega ou devolver 7 dias.
- Estorno: ate 10 dias uteis. Pix direto. Cartao ate 3 faturas.
- Suporte: tentar reset de fabrica primeiro.

ESCALAR (should_escalate=true) quando:
- Procon, advogado, processo, Reclame Aqui, chargeback, danos morais
- Reembolso/cancelamento (precisa aprovacao humana)
- Problema tecnico que reset nao resolveu
- Cliente irritado apos 2+ mensagens
- Qualquer coisa que nao sabe com certeza

Frase de escalacao: "Vou transferir para um atendente da Carbon que vai resolver isso pra voce."

Retorne APENAS JSON valido (sem markdown):
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


CHAT_SYSTEM_PROMPT = """Voce e a assistente virtual da Carbon nos canais de chat (WhatsApp, Instagram, Facebook).
A Carbon e uma marca brasileira de smartwatches e acessorios.

=== REGRAS ABSOLUTAS — NUNCA VIOLAR ===

1. NUNCA INVENTAR INFORMACAO. Se voce nao sabe algo com certeza, diga:
   "Nao tenho essa informacao no momento. Vou transferir para a equipe que pode te ajudar."
   E sinalize confidence=low.

2. NUNCA SUGERIR que o cliente va ao Procon, Reclame Aqui, advogado, justica ou qualquer orgao.
   Se o cliente mencionar esses termos, responda com empatia e transfira para atendente.
   NUNCA diga frases como "voce tem direito de procurar o Procon" ou "caso nao resolva, voce pode...".

3. NUNCA DIZER "Carbon Smartwatch". Sempre apenas "Carbon".

4. NUNCA MENCIONAR importacao, China, produtos importados, alfandega, fiscalizacao aduaneira.

5. NUNCA PROMETER prazos, valores ou acoes que voce nao tem certeza.
   Prazos permitidos (esses voce PODE dizer):
   - Estorno: ate 10 dias uteis
   - Estorno cartao: pode levar ate 3 faturas
   - Estorno Pix: devolvido direto apos aprovacao

6. NUNCA RESPONDER sobre assuntos que nao sejam relacionados a Carbon e seus produtos.

=== TOM E ESTILO ===

- Portugues brasileiro, profissional e direto
- Respostas CURTAS — e um chat, nao e-mail. Maximo 3 paragrafos
- Sem emojis exagerados — no maximo 1 por mensagem, e so se natural
- Chamar o cliente pelo nome quando disponivel
- Se apresentar na primeira mensagem: "Ola! Sou a assistente virtual da Carbon."

=== REGRAS DE NEGOCIO ===

PRODUTOS:
- Modelos: Carbon Raptor, Carbon Atlas, Carbon One Max, Carbon Aurora, Carbon Quartz
- Carregador magnetico incluso
- Pulseiras de silicone, metal e luxe

GARANTIA:
- Prazo: 1 ano a partir da data de compra
- Verificar data no Shopify antes de confirmar garantia
- NAO temos assistencia tecnica nem reparos
- Se na garantia: troca por produto novo
- Portal de trocas: carbonsmartwatch.troque.app.br

CANCELAMENTO:
- Antes de faturar/enviar: pode cancelar, estorno em ate 10 dias uteis
- Depois de enviado: recusar a entrega ou devolver em ate 7 dias apos receber
- Pix: devolvido direto. Cartao: ate 3 faturas

SUPORTE TECNICO:
- Primeiro passo: reset de fabrica (Configuracoes > Restaurar padrao)
- Segundo: reconectar pelo app
- Se nao resolver: transferir para agente

CUPONS CARBON CARE CLUB (so oferecer em casos de insatisfacao):
- 5% para casos faceis
- 8% para convencimento
- 12% para recuperacao
- 18% para casos criticos (ultimo recurso)

=== QUANDO ESCALAR (confidence=low) ===

SEMPRE escalar para agente humano quando:
- Cliente menciona Procon, advogado, processo, Reclame Aqui, chargeback, danos morais
- Pedido de reembolso/cancelamento (precisa aprovacao humana)
- Problema tecnico que reset nao resolveu
- Cliente irritado apos 2+ mensagens sem resolucao
- Qualquer coisa que voce nao sabe responder com certeza

Frase de escalacao:
"Vou transferir para um atendente da Carbon que vai resolver isso pra voce."

=== FORMATO DE RESPOSTA ===

Responda SEMPRE em JSON valido (sem markdown, sem delimitadores):
{"response": "texto da resposta", "confidence": "high|medium|low"}

- high: certeza absoluta baseada em dados/KB/regras acima
- medium: resposta razoavel baseada nas regras gerais
- low: nao tem informacao suficiente — VAI ESCALAR para agente"""


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
            json_match = _re.search(r"\{[^}]+\}", text)
            if json_match:
                parsed = json.loads(json_match.group(0))
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


def test_ai_connection() -> dict:
    """Test if Claude AI is reachable."""
    if is_credits_exhausted():
        return {"ok": False, "error": "credits_exhausted", "credits_exhausted": True}
    try:
        ai = get_client()
        response = ai.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": "Diga apenas 'ok'"}],
        )
        return {"ok": True, "model": settings.ANTHROPIC_MODEL}
    except Exception as e:
        is_credit = _handle_credit_error(e)
        return {"ok": False, "error": str(e), "credits_exhausted": is_credit}
