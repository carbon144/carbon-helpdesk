"""AI Triage Service using Claude API."""
import json
import logging
from anthropic import Anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

client = None


def get_client() -> Anthropic:
    global client
    if client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY não configurada")
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return client


TRIAGE_SYSTEM_PROMPT = """Você é um assistente de triagem para o suporte da Carbon Smartwatch, uma empresa brasileira de smartwatches.

Analise a mensagem do cliente e retorne APENAS um JSON válido (sem markdown, sem texto extra) com:

{
  "category": "uma das categorias: garantia, troca, mau_uso, carregador, duvida, reclamacao, juridico, suporte_tecnico, financeiro",
  "priority": "uma das prioridades: low, medium, high, urgent",
  "sentiment": "um dos sentimentos: positive, neutral, negative, angry",
  "legal_risk": true ou false (se menciona PROCON, processo, advogado, Reclame Aqui, chargeback, danos morais),
  "tags": ["lista de tags relevantes entre: garantia, troca, carregador, mau_uso, procon, chargeback, duvida, reclamacao, juridico, suporte_tecnico"],
  "confidence": 0.0 a 1.0,
  "summary": "resumo em 1 frase do problema"
}

Regras de prioridade:
- urgent: risco jurídico, PROCON, chargeback, cliente muito irritado
- high: reclamação forte, produto com defeito grave, cliente reincidente
- medium: dúvidas gerais, trocas normais, problemas técnicos comuns
- low: elogios, dúvidas simples, feedback

Contexto do produto: smartwatches Carbon, carregadores magnéticos, pulseiras, garantia de 1 ano."""


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


def triage_ticket(subject: str, body: str, customer_name: str = "", is_repeat: bool = False) -> dict | None:
    """Classify a ticket using Claude AI."""
    try:
        ai = get_client()

        user_msg = f"Assunto: {subject}\n\nMensagem do cliente"
        if customer_name:
            user_msg += f" ({customer_name})"
        if is_repeat:
            user_msg += " [CLIENTE REINCIDENTE]"
        user_msg += f":\n{body[:2000]}"

        response = ai.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=500,
            system=TRIAGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        text = response.content[0].text.strip()
        # Try to parse JSON
        result = json.loads(text)
        logger.info(f"AI triage result: category={result.get('category')}, priority={result.get('priority')}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"AI returned invalid JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"AI triage failed: {e}")
        return None


def suggest_reply(subject: str, body: str, customer_name: str = "", category: str = "", kb_context: str = "", partial_text: str = "") -> str | None:
    """Generate a suggested reply using Claude AI. If partial_text is provided, complete it."""
    try:
        ai = get_client()

        user_msg = f"Ticket: {subject}\nCliente: {customer_name or 'N/A'}\nCategoria: {category or 'N/A'}\n\nMensagem:\n{body[:2000]}"

        if kb_context:
            user_msg += f"\n\n--- Base de Conhecimento relevante ---\n{kb_context[:1500]}"

        system_prompt = SUGGEST_SYSTEM_PROMPT
        if partial_text:
            user_msg += f"\n\n--- O agente já começou a escrever ---\n{partial_text}"
            system_prompt += "\n\nIMPORTANTE: O agente já começou a escrever uma resposta. Complete a resposta dele de forma natural, continuando de onde ele parou. Retorne APENAS a continuação, não repita o que ele já escreveu."

        response = ai.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=400 if partial_text else 800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )

        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"AI suggest reply failed: {e}")
        return None


SUMMARY_SYSTEM_PROMPT = """Você é um assistente de suporte da Carbon Smartwatch.
Analise o histórico de mensagens do ticket e gere um resumo executivo em português brasileiro.

O resumo deve ter no máximo 3 frases e incluir:
1. O problema principal do cliente
2. O que já foi feito/tentado
3. O status atual / próximo passo

Retorne APENAS o texto do resumo, sem JSON, sem markdown."""


def summarize_ticket(subject: str, messages: list[dict], category: str = "", customer_name: str = "") -> str | None:
    """RF-019: Generate AI summary from ticket conversation history."""
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

        response = ai.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=300,
            system=SUMMARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": conversation[:4000]}],
        )

        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"AI summary failed: {e}")
        return None


AUTO_REPLY_SYSTEM_PROMPT = """Você é a assistente virtual da Carbon Smartwatch nos canais de mensagem (WhatsApp, Instagram, Facebook).

Regras OBRIGATÓRIAS:
- Responda SEMPRE em português brasileiro
- Seja simpática, profissional e objetiva
- Respostas curtas (máximo 300 palavras) — é um chat, não e-mail
- Use emoji com moderação (1-2 por mensagem no máximo)
- NUNCA invente informações sobre produtos, políticas ou prazos
- NUNCA prometa algo que não esteja na base de conhecimento
- Sempre cumprimente o cliente pelo nome quando disponível
- Se for a primeira mensagem, apresente-se: "Olá! Sou a assistente virtual da Carbon"

Quando NÃO conseguir resolver:
- Risco jurídico (PROCON, advogado, processo, danos morais)
- Problema técnico complexo não coberto pela base de conhecimento
- Pedido de reembolso ou troca que precisa de aprovação humana
- Cliente claramente insatisfeito após 3+ trocas de mensagem
→ Nestes casos, responda normalmente mas sinalize should_escalate=true

Frase de escalação (quando should_escalate=true):
"Para que possamos resolver isso da melhor forma, por favor envie um e-mail detalhado para suporte@carbonsmartwatch.com.br. Nossa equipe vai te atender com prioridade! 📧"

Contexto dos produtos: smartwatches Carbon, carregadores magnéticos, pulseiras. Garantia de 1 ano.

Retorne APENAS um JSON válido (sem markdown):
{
  "response": "texto da resposta para o cliente",
  "should_escalate": true ou false,
  "escalation_reason": "motivo da escalação ou string vazia"
}"""


def ai_auto_reply(
    ticket_subject: str,
    conversation_history: list[dict],
    customer_name: str = "",
    category: str = "",
    kb_context: str = "",
    platform: str = "whatsapp",
) -> dict | None:
    """Generate an automatic AI reply for Meta channels (WhatsApp/Instagram/Facebook)."""
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

        response = ai.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=600,
            system=AUTO_REPLY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg[:6000]}],
        )

        text = response.content[0].text.strip()
        result = json.loads(text)
        logger.info(f"AI auto-reply: escalate={result.get('should_escalate', False)}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"AI auto-reply returned invalid JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"AI auto-reply failed: {e}")
        return None


def test_ai_connection() -> dict:
    """Test if Claude AI is reachable."""
    try:
        ai = get_client()
        response = ai.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": "Diga apenas 'ok'"}],
        )
        return {"ok": True, "model": settings.ANTHROPIC_MODEL}
    except Exception as e:
        return {"ok": False, "error": str(e)}
