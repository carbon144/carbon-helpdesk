# Email Auto-Reply + Helpdesk Jobs Overhaul

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the helpdesk IA respond automatically to 45%+ of email tickets (rastreio, duvida, status) and send ACKs inteligentes for the rest — reducing first response time from 58.7h to <5min.

**Architecture:** New `email_auto_reply_service.py` plugged into existing `gmail.py:fetch_emails` flow. Reuses existing `ai_service.py` prompts/KB, `shopify_service.py` for order lookup, `troque_service.py` for warranty lookup, and `gmail_service.send_email()` for sending. Auto-assign fallback ensures zero tickets without owner.

**Tech Stack:** Python/FastAPI, Anthropic Claude API (existing), Gmail API (existing), SQLAlchemy async

---

## Task 1: Add auto_replied fields to Ticket model

**Files:**
- Modify: `backend/app/models/ticket.py:103` (before relationships)

**Step 1: Add fields to model**

In `backend/app/models/ticket.py`, add after line 103 (`first_response_at`):

```python
    # Email auto-reply tracking
    auto_replied: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

**Step 2: Add EMAIL_AUTO_REPLY_ENABLED to config**

In `backend/app/core/config.py`, add before `SLA_URGENT_HOURS`:

```python
    # Email auto-reply
    EMAIL_AUTO_REPLY_ENABLED: bool = True
    ANTHROPIC_TRIAGE_MODEL: str = "claude-haiku-4-5-20251001"
```

**Step 3: Verify**

Schema auto-creates via `create_all` on restart. No migration needed.

**Step 4: Commit**

```bash
git add backend/app/models/ticket.py backend/app/core/config.py
git commit -m "feat: add auto_replied fields to Ticket model + config flag"
```

---

## Task 2: Create email_auto_reply_service.py

**Files:**
- Create: `backend/app/services/email_auto_reply_service.py`

**Step 1: Create the service**

```python
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
1. NUNCA inventar informações. Se não tem certeza, diga que a equipe vai analisar.
2. NUNCA sugerir Procon, Reclame Aqui, advogado ou qualquer órgão.
3. NUNCA dizer "Carbon Smartwatch". Sempre apenas "Carbon".
4. NUNCA mencionar importação, China, alfândega.
5. NUNCA mencionar espontaneamente que a NF é de serviço/intermediação.

=== TOM ===
- Email profissional mas amigável. Mais completo que chat, mas sem enrolação.
- Português brasileiro. Chamar pelo nome.
- Máximo 4 parágrafos.
- Sem emojis.

=== REGRAS DE NEGÓCIO ===
- Modelos: Carbon Raptor, Atlas, One Max, Aurora, Quartz
- Garantia: 12 meses contra defeitos. Troca direta (sem assistência técnica).
- Portal trocas: carbonsmartwatch.troque.app.br
- Cancelamento antes de envio: ok. Depois: recusar entrega ou devolver em 7 dias.
- Estorno: até 10 dias úteis. Pix direto. Cartão até 3 faturas.
- Apps: Raptor/Atlas = GloryFitPro. One Max/Aurora = DaFit.

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
    triage: dict,
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

    # Auto-resolve: simple categories with high confidence
    if category in AUTO_RESOLVE_CATEGORIES and confidence >= 0.7:
        try:
            reply_text = await _generate_ai_reply(subject, body, customer_name, category, protocol)
            if reply_text:
                return {"type": "auto_reply", "body": reply_text, "reason": f"auto_resolve_{category}"}
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
                model=settings.ANTHROPIC_MODEL,
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

    result = send_email(
        to=to_email,
        subject=reply_subject,
        body_text=body_text,
        thread_id=gmail_thread_id,
        in_reply_to=gmail_message_id,
    )
    if result:
        logger.info(f"Auto-reply sent to {to_email}, gmail_id={result.get('id')}")
    return result
```

**Step 2: Commit**

```bash
git add backend/app/services/email_auto_reply_service.py
git commit -m "feat: create email auto-reply service with AI + ACK templates"
```

---

## Task 3: Plug auto-reply into gmail.py fetch flow

**Files:**
- Modify: `backend/app/api/gmail.py:336-367` (inside fetch_emails, after triage + protocol, before `created += 1`)

**Step 1: Add auto-reply call after ticket creation**

In `backend/app/api/gmail.py`, replace the block from line 359 (`# Auto-assign to available agent`) to line 364 with:

```python
            # === EMAIL AUTO-REPLY ===
            auto_reply_result = None
            try:
                from app.services.email_auto_reply_service import generate_auto_reply, send_auto_reply
                auto_reply_result = await generate_auto_reply(
                    subject=email_data["subject"],
                    body=email_data["body_text"][:2000],
                    customer_name=email_data["from_name"],
                    category=ticket.category or "duvida",
                    triage=triage if 'triage' in dir() else None,
                    protocol=ticket.protocol,
                )
                if auto_reply_result and auto_reply_result["type"] in ("auto_reply", "ack"):
                    sent = await send_auto_reply(
                        to_email=email_data["from_email"],
                        subject=email_data["subject"],
                        body_text=auto_reply_result["body"],
                        gmail_thread_id=gmail_thread_id,
                        gmail_message_id=gmail_message_id,
                    )
                    if sent:
                        # Save outbound message
                        auto_msg = Message(
                            ticket_id=ticket.id,
                            type="outbound",
                            sender_name="Carbon IA",
                            sender_email=settings.GMAIL_SUPPORT_EMAIL or "suporte@carbonsmartwatch.com.br",
                            body_text=auto_reply_result["body"],
                            gmail_message_id=sent.get("id"),
                            gmail_thread_id=sent.get("threadId") or gmail_thread_id,
                        )
                        db.add(auto_msg)
                        ticket.auto_replied = True
                        ticket.auto_reply_at = datetime.now(timezone.utc)
                        ticket.first_response_at = datetime.now(timezone.utc)
                        if auto_reply_result["type"] == "auto_reply":
                            ticket.status = "waiting"
                        existing_tags = list(ticket.tags or [])
                        existing_tags.append(auto_reply_result["type"])
                        ticket.tags = list(set(existing_tags))
                        logger.info(f"Auto-reply ({auto_reply_result['type']}) sent for ticket #{ticket.number}")
            except Exception as e:
                logger.warning(f"Email auto-reply skipped: {e}")

            # Auto-assign to available agent
            try:
                from app.api.tickets import _auto_assign_single
                await _auto_assign_single(ticket, db, user)
            except Exception as e:
                logger.warning(f"Auto-assign skipped for gmail ticket: {e}")
```

**Step 2: Commit**

```bash
git add backend/app/api/gmail.py
git commit -m "feat: plug email auto-reply into gmail fetch flow"
```

---

## Task 4: Fix auto-assign to ALWAYS assign (fallback to active agents)

**Files:**
- Modify: `backend/app/api/tickets.py:754-817` (`_auto_assign_single`)

**Step 1: Add fallback when no online agents**

In `_auto_assign_single`, after the existing `if not agents: return` on line 761, change to:

```python
    if not agents:
        # Fallback: get ANY active agent (even if not online)
        fallback_result = await db.execute(
            select(User).where(User.is_active == True, User.role.in_(["agent", "supervisor", "admin"]))
        )
        agents = fallback_result.scalars().all()
        if not agents:
            return
```

This ensures zero tickets without an owner — even on weekends/off-hours.

**Step 2: Commit**

```bash
git add backend/app/api/tickets.py
git commit -m "fix: auto-assign fallback to active agents when none online"
```

---

## Task 5: Create CHANGELOG-EQUIPE.md (manual para equipe)

**Files:**
- Create: `docs/CHANGELOG-EQUIPE.md`

**Step 1: Write the manual**

```markdown
# Changelog & Manual — Equipe Carbon Helpdesk
## Atualização: IA Auto-Reply por Email (Março 2026)

---

### O QUE MUDOU

A partir de agora, quando um cliente envia um email para o suporte, a IA da Carbon responde automaticamente:

**1. Tickets Simples (rastreio, dúvida, status do pedido)**
- A IA lê o email, entende o problema e responde direto
- O ticket fica como "Aguardando Cliente" (amarelo)
- Se o cliente responder, o ticket volta pra fila normalmente
- Tag no ticket: `auto_reply`

**2. Tickets que precisam de análise (garantia, financeiro, reclamação)**
- A IA envia um ACK automático: "Recebemos sua mensagem, retornaremos em até 24h"
- O email inclui links úteis (rastreio, portal trocas, FAQ)
- O ticket fica "Aberto" na fila do agente — vocês resolvem normalmente
- Tag no ticket: `ack`

**3. Tickets urgentes (Procon, advogado, chargeback)**
- A IA NÃO responde nada. Esses vão direto pro agente com prioridade URGENTE
- Slack é notificado automaticamente

---

### O QUE MUDA PRA VOCÊS

| Antes | Agora |
|-------|-------|
| Cliente esperava 58h por resposta | Cliente recebe resposta em <5 min |
| 393 tickets sem agente | Todo ticket tem dono automaticamente |
| Segunda: avalanche de 205 tickets | IA resolve FDS, segunda chega filtrada |
| 73% tickets = 1 msg simples | IA resolve esses automaticamente |
| "Peço desculpas pela demora" em toda msg | Não precisa mais — IA respondeu na hora |

---

### COMO IDENTIFICAR TICKETS DA IA

Na inbox, os tickets da IA têm tags visíveis:
- **`auto_reply`** — IA respondeu completamente. Só revisar se o cliente responder.
- **`ack`** — IA enviou confirmação. Vocês precisam resolver.
- Tickets sem tag = nunca passaram pela IA.

---

### REGRAS IMPORTANTES

1. **NÃO desabilitar a IA** sem falar com Pedro. Se algo parecer errado, reportem.
2. **Revisem tickets `auto_reply`** se o cliente responder — a IA pode ter errado.
3. **Foco nos tickets `ack`** — esses são os que precisam de vocês de verdade.
4. **Tickets urgentes** (Procon, advogado, etc) continuam chegando direto pra vocês. A IA não toca neles.

---

### PRIORIDADE DE ATENDIMENTO

1. **URGENTE** (vermelho) — Procon, advogado, chargeback. SLA: 1h resposta.
2. **ALTA** (laranja) — Defeito grave, reincidente, reclamação forte. SLA: 4h.
3. **MÉDIA** (amarelo) — Trocas, problemas técnicos, entrega. SLA: 8h.
4. **BAIXA** (verde) — Dúvidas simples, elogios, feedback. SLA: 24h.

---

### CATEGORIAS DOS TICKETS

| Categoria | O que é | Exemplo |
|-----------|---------|---------|
| meu_pedido | Quer saber onde está o pedido | "Cadê meu rastreio?" |
| garantia | Defeito, troca, devolução | "Meu relógio não liga" |
| reenvio | Não chegou, quer novo envio | "Extraviou, enviem de novo" |
| financeiro | Estorno, reembolso, chargeback | "Quero meu dinheiro de volta" |
| duvida | Pré-venda, como usar, elogio | "Qual app uso pro Raptor?" |
| reclamacao | Insatisfação, golpe, GUACU | "Isso é golpe?" |

---

### ESCALA E COBERTURA

- **Todo ticket agora tem um agente atribuído automaticamente** (round-robin por carga)
- Se nenhum agente tá online, o sistema distribui entre todos os ativos
- **Daniele e Tauane** = modelo de efetividade. Menos mensagens, mais resoluções.
- **Foco em FECHAR tickets**, não em responder. Uma resposta completa > 5 respostas parciais.

---

### DÚVIDAS FREQUENTES

**P: A IA pode responder errado?**
R: Ela foi programada pra NUNCA inventar informação. Se não sabe, manda o ACK genérico. Mas revisem se algo parecer estranho.

**P: O cliente vai saber que é IA?**
R: O email vem de "Equipe Carbon", não de "IA" ou "Bot". O tom é profissional e natural.

**P: E se a IA responder e o cliente não gostar?**
R: O ticket continua na fila. Quando o cliente responde, volta pra "Aberto" e o agente assume.

**P: Funciona no final de semana?**
R: SIM. A IA responde 24/7, inclusive feriados. É o principal benefício.
```

**Step 2: Commit**

```bash
git add docs/CHANGELOG-EQUIPE.md
git commit -m "docs: changelog e manual da IA auto-reply para equipe"
```

---

## Task 6: Add SQL migration script for production

**Files:**
- Create: `backend/migrations/003_auto_reply_fields.sql`

Even though `create_all` handles dev, production needs explicit migration.

**Step 1: Create migration**

```sql
-- Migration: Add auto-reply fields to tickets table
-- Date: 2026-03-09
-- Feature: Email Auto-Reply

ALTER TABLE tickets ADD COLUMN IF NOT EXISTS auto_replied BOOLEAN DEFAULT FALSE;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS auto_reply_at TIMESTAMPTZ;
```

**Step 2: Commit**

```bash
git add backend/migrations/003_auto_reply_fields.sql
git commit -m "db: migration for auto_replied fields in production"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Model + config fields | `ticket.py`, `config.py` |
| 2 | Auto-reply service | `email_auto_reply_service.py` (new) |
| 3 | Plug into gmail fetch | `gmail.py` |
| 4 | Fix auto-assign fallback | `tickets.py` |
| 5 | Changelog/manual equipe | `CHANGELOG-EQUIPE.md` (new) |
| 6 | Production migration | `003_auto_reply_fields.sql` (new) |

**Deploy order:** Run migration SQL on prod → deploy backend → restart.
