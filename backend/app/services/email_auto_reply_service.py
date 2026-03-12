"""Email Auto-Reply Service — IA responds to simple email tickets automatically."""

import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.services import ai_service
from app.services.gmail_service import send_email
from app.services.kb_real_data import KB_ARTICLES

logger = logging.getLogger(__name__)

# Categories that IA can auto-resolve
AUTO_RESOLVE_CATEGORIES = {"meu_pedido", "duvida", "reenvio"}

# Categories that get ACK only (agent handles)
ACK_CATEGORIES = {"garantia", "financeiro", "reclamacao"}

EMAIL_AUTO_REPLY_PROMPT = """Você é a assistente de suporte da Carbon por email.
A Carbon é uma marca brasileira de smartwatches.

Você está respondendo a um email de cliente automaticamente. O email já foi classificado pela triagem.

=== REGRAS ABSOLUTAS ===
1. NUNCA INVENTAR NADA. Nenhuma informação, nenhuma URL, nenhum prazo, nenhum status de pedido, nenhum código de rastreio. Se você não tem a informação CONCRETA no contexto, diga que a equipe vai verificar e retornar. Inventar é o pior erro possível.
2. NUNCA sugerir Procon, Reclame Aqui, advogado ou qualquer órgão.
3. NUNCA dizer "Carbon Smartwatch". Sempre apenas "Carbon".
4. NUNCA mencionar importação, China, alfândega.
5. NUNCA mencionar espontaneamente que a NF é de serviço/intermediação.
6. NUNCA prometer ações que você não pode executar (abrir ocorrência, investigar, acionar transportadora, verificar no sistema). Diga que a EQUIPE vai analisar/verificar.
7. NUNCA usar frases como "vou abrir", "vou solicitar", "vou verificar". Use "nossa equipe vai analisar" ou "nosso time vai verificar".
8. NUNCA inventar URLs. O site oficial é carbonsmartwatch.com.br — NÃO use "carbonoficial", "carbonstores" ou qualquer outra variação.

=== TOM ===
- Email profissional mas amigável. Mais completo que chat, mas sem enrolação.
- Português brasileiro. Chamar pelo nome.
- Máximo 4 parágrafos.
- Sem emojis.

=== REGRAS DE NEGÓCIO ===
- Modelos atuais: Carbon Raptor, Atlas, One Max, Aurora, Quartz
- Carbon One (DESCONTINUADO): modelo antigo, pulseira 24mm. One Max é a evolução, pulseira 22mm. Pulseiras NÃO compatíveis.
- Garantia: 12 meses contra defeitos. Troca direta (sem assistência técnica).
- Portal trocas: carbonsmartwatch.troque.app.br
- Cancelamento antes de envio: ok. Depois: recusar entrega ou devolver em 7 dias.
- Estorno: até 10 dias úteis. Pix direto. Cartão até 3 faturas.
- Apps: Raptor/Atlas = GloryFitPro. One Max/Aurora = DaFit.

RESISTÊNCIA À ÁGUA (specs oficiais — NUNCA inventar IP68 ou qualquer outra classificação):
- Raptor: 5ATM (respingos, chuva, banho, piscina, natação)
- Atlas: 3ATM (respingos, chuva, banho, piscina, natação)
- One Max: 1ATM (respingos leves, suor — NÃO molhar)
- Aurora: 1ATM (respingos leves, suor — NÃO molhar)
- Quartz: 1ATM (respingos leves, suor — NÃO molhar)
- NENHUM modelo é IP68 ou IP67. NUNCA usar essas classificações.
- Raptor e Atlas servem para natação. One Max, Aurora e Quartz NÃO.
- Se o cliente perguntar sobre natação: Raptor e Atlas sim, os demais não.

PRAZOS DE ENTREGA:
- Sudeste: 7 a 12 dias úteis
- Sul: 7 a 14 dias úteis
- Centro-Oeste: 8 a 16 dias úteis
- Nordeste: 10 a 20 dias úteis
- Norte: 12 a 25 dias úteis

=== FORMATO ===
Responda APENAS com o texto do email. Sem JSON, sem markdown.
Comece com "Olá, [nome]!" e termine com:

Qualquer dúvida, é só responder este email.

Atenciosamente,
Equipe Carbon"""

ACK_TEMPLATE = """Olá, {name}!

Recebemos sua mensagem e nosso time já está analisando.{extra_info}

Retornaremos em até 24 horas úteis com uma resposta completa.

Enquanto isso, algumas informações que podem ajudar:
• Rastreio do seu pedido: https://carbonsmartwatch.com.br/rastreio
• Portal de trocas/devoluções: carbonsmartwatch.troque.app.br
• Garantia: 12 meses a partir da compra

Qualquer dúvida, é só responder este email.

Atenciosamente,
Equipe Carbon"""


def _get_kb_context(category: str) -> str:
    """Get relevant KB articles for the category."""
    relevant = [a for a in KB_ARTICLES if a.get("category") == category]
    if not relevant:
        relevant = KB_ARTICLES[:3]
    texts = []
    for a in relevant[:3]:
        texts.append(f"Artigo: {a['title']}\n{a['content'][:500]}")
    return "\n\n".join(texts)


async def generate_auto_reply(
    subject: str,
    body: str,
    customer_name: str,
    category: str,
    triage: dict | None = None,
    protocol: str | None = None,
) -> dict:
    """Generate an automatic email reply.

    Returns:
        {
            "type": "auto_reply" | "ack" | "skip",
            "body": str (email text),
            "reason": str,
        }
    """
    if not settings.EMAIL_AUTO_REPLY_ENABLED:
        return {"type": "skip", "body": "", "reason": "disabled"}

    # NEVER auto-reply to legal risk or urgent
    if triage and (triage.get("legal_risk") or triage.get("priority") == "urgent"):
        return {"type": "skip", "body": "", "reason": "legal_risk_or_urgent"}

    confidence = triage.get("confidence", 0) if triage else 0

    # Detect complex topics that should NOT be auto-resolved, even if category is "simple"
    _text = f"{subject} {body}".lower()
    ESCALATE_KEYWORDS = [
        "garantia", "carbon care", "carboncare", "defeito", "quebrou", "parou de funcionar",
        "nao funciona", "não funciona", "tela apagou", "nao liga", "não liga",
        "reembolso", "estorno", "dinheiro de volta", "cancelar compra",
        "procon", "reclame aqui", "advogado", "juridico", "jurídico",
        "troca", "devolu", "arrependimento", "produto errado",
        "nota fiscal", "termo de garantia", "certificado",
        # Perguntas sobre água/natação — depende do modelo, melhor humano verificar
        "natação", "natacao", "nadar", "mergulh", "piscina", "prova d'água",
        "prova d'agua", "prova dagua", "ip68", "ip67", "ip66",
        "a prova de agua", "à prova de água", "resistente a agua", "resistente à água",
    ]
    if any(kw in _text for kw in ESCALATE_KEYWORDS):
        name = customer_name.split()[0] if customer_name else "Cliente"
        extra_info = ""
        if protocol:
            extra_info = f"\nSeu protocolo de atendimento: {protocol}"
        ack_body = ACK_TEMPLATE.format(name=name, extra_info=extra_info)
        return {"type": "ack", "body": ack_body, "reason": f"escalate_keyword_detected"}

    # Auto-resolve: simple categories with high confidence
    if category in AUTO_RESOLVE_CATEGORIES and confidence >= 0.5:
        try:
            reply_text = await _generate_ai_reply(
                subject, body, customer_name, category, protocol
            )
            if reply_text:
                return {
                    "type": "auto_reply",
                    "body": reply_text,
                    "reason": f"auto_resolve_{category}",
                }
        except Exception as e:
            logger.error(f"AI auto-reply generation failed: {e}")

    # ACK: everything else that's not skipped
    name = customer_name.split()[0] if customer_name else "Cliente"
    extra_info = ""
    if protocol:
        extra_info = f"\nSeu protocolo de atendimento: {protocol}"

    ack_body = ACK_TEMPLATE.format(name=name, extra_info=extra_info)
    return {"type": "ack", "body": ack_body, "reason": f"ack_{category}"}


async def _generate_ai_reply(
    subject: str,
    body: str,
    customer_name: str,
    category: str,
    protocol: str | None = None,
) -> str | None:
    """Use Claude to generate a full auto-reply for simple tickets."""
    if ai_service.is_credits_exhausted():
        return None

    kb_context = _get_kb_context(category)

    user_msg = f"Assunto: {subject}\nCliente: {customer_name}\nCategoria: {category}\n"
    if protocol:
        user_msg += f"Protocolo: {protocol}\n"
    user_msg += f"\nEmail do cliente:\n{body[:2000]}"
    if kb_context:
        user_msg += f"\n\n--- Base de Conhecimento ---\n{kb_context}"

    try:
        ai = ai_service.get_client()
        response = await ai_service._call_with_retry(
            lambda: ai.messages.create(
                model=settings.ANTHROPIC_AUTO_REPLY_MODEL or settings.ANTHROPIC_MODEL,
                max_tokens=800,
                system=EMAIL_AUTO_REPLY_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
        )
        return response.content[0].text.strip()
    except Exception as e:
        ai_service._handle_credit_error(e)
        logger.error(f"Email auto-reply AI failed: {e}")
        return None


async def send_auto_reply(
    to_email: str,
    subject: str,
    body_text: str,
    gmail_thread_id: str | None = None,
    gmail_message_id: str | None = None,
) -> dict | None:
    """Send the auto-reply email via Gmail in the same thread."""
    reply_subject = subject if subject.startswith("Re:") else f"Re: {subject}"

    import asyncio
    result = await asyncio.to_thread(
        send_email,
        to=to_email,
        subject=reply_subject,
        body_text=body_text,
        thread_id=gmail_thread_id,
        in_reply_to=gmail_message_id,
    )
    if result:
        logger.info(f"Auto-reply sent to {to_email}, gmail_id={result.get('id')}")
    return result
