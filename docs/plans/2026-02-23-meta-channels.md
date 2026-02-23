# Meta Channels (WhatsApp, Instagram, Facebook) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate WhatsApp, Instagram, and Facebook Messenger via Meta APIs with AI auto-response — human agents get read-only access with emergency intervention.

**Architecture:** Single webhook endpoint receives events from all 3 Meta platforms. A unified `meta_service.py` handles outbound messaging. Each inbound message triggers AI auto-reply via a new `ai_auto_reply()` function that uses the existing KB. Agents see conversations read-only with a "Pause AI / Resume AI" toggle for emergencies.

**Tech Stack:** FastAPI, SQLAlchemy (PostgreSQL), Meta Graph API v21.0, Anthropic Claude, React + Tailwind CSS

**Design Doc:** `docs/plans/2026-02-23-meta-channels-design.md`

---

## Task 1: Add Meta environment variables to config

**Files:**
- Modify: `backend/app/core/config.py:28-48`

**Step 1: Add Meta settings to the Settings class**

Add these fields after the existing Slack settings block (after line 30):

```python
    # Meta (WhatsApp, Instagram, Facebook)
    META_APP_SECRET: str = ""
    META_VERIFY_TOKEN: str = ""
    META_PAGE_ACCESS_TOKEN: str = ""
    META_WHATSAPP_TOKEN: str = ""
    META_WHATSAPP_PHONE_ID: str = ""
```

**Step 2: Verify the app still starts**

Run: `cd /Users/pedrocastro/Desktop/carbon-helpdesk/backend && python -c "from app.core.config import settings; print(settings.META_APP_SECRET)"`
Expected: Empty string (no crash)

**Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat(meta): add Meta platform environment variables to config"
```

---

## Task 2: Add Meta fields to database models

**Files:**
- Modify: `backend/app/models/ticket.py:60-64`
- Modify: `backend/app/models/message.py:27`
- Modify: `backend/app/models/customer.py:36`

**Step 1: Add Meta fields to Ticket model**

In `backend/app/models/ticket.py`, after the Slack integration block (after line 64, `source` field), add:

```python
    # Meta integration (WhatsApp, Instagram, Facebook)
    meta_conversation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    meta_platform: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_auto_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_paused_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    ai_paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

**Step 2: Add Meta fields to Message model**

In `backend/app/models/message.py`, after the `slack_ts` field (line 27), add:

```python
    meta_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meta_platform: Mapped[str | None] = mapped_column(String(20), nullable=True)
```

**Step 3: Add meta_user_id to Customer model**

In `backend/app/models/customer.py`, after the `metadata_` field (line 36), add:

```python
    meta_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
```

**Step 4: Add migration SQLs to main.py lifespan**

In `backend/app/main.py`, inside the `migration_sqls` list (before the closing `]`), add:

```python
            # Meta integration fields
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS meta_conversation_id VARCHAR(100)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS meta_platform VARCHAR(20)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_auto_mode BOOLEAN DEFAULT TRUE",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_paused_by VARCHAR(36)",
            "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_paused_at TIMESTAMPTZ",
            "CREATE INDEX IF NOT EXISTS ix_tickets_meta_conversation_id ON tickets (meta_conversation_id)",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS meta_message_id VARCHAR(100)",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS meta_platform VARCHAR(20)",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS meta_user_id VARCHAR(100)",
            "CREATE INDEX IF NOT EXISTS ix_customers_meta_user_id ON customers (meta_user_id)",
```

**Step 5: Update TicketResponse schema**

In `backend/app/schemas/ticket.py`, inside `TicketResponse` class (after `slack_thread_ts` field, ~line 102), add:

```python
    meta_conversation_id: str | None = None
    meta_platform: str | None = None
    ai_auto_mode: bool = True
    ai_paused_by: str | None = None
    ai_paused_at: datetime | None = None
```

**Step 6: Commit**

```bash
git add backend/app/models/ticket.py backend/app/models/message.py backend/app/models/customer.py backend/app/main.py backend/app/schemas/ticket.py
git commit -m "feat(meta): add Meta fields to Ticket, Message, and Customer models"
```

---

## Task 3: Create Meta message service

**Files:**
- Create: `backend/app/services/meta_service.py`

**Step 1: Create the service file**

```python
"""Meta Platform messaging service — WhatsApp, Instagram, Facebook Messenger."""
import hashlib
import hmac
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify X-Hub-Signature-256 from Meta webhook."""
    if not settings.META_APP_SECRET:
        return True  # Skip in dev if not configured
    expected = "sha256=" + hmac.new(
        settings.META_APP_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def send_message(platform: str, recipient_id: str, text: str) -> dict | None:
    """Send a text message via the appropriate Meta platform API.

    Args:
        platform: "whatsapp", "instagram", or "facebook"
        recipient_id: The recipient's platform-specific ID (phone for WA, PSID/IGSID for FB/IG)
        text: Message text to send

    Returns:
        API response dict or None on failure
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if platform == "whatsapp":
                url = f"{GRAPH_API_BASE}/{settings.META_WHATSAPP_PHONE_ID}/messages"
                payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient_id,
                    "type": "text",
                    "text": {"body": text},
                }
                token = settings.META_WHATSAPP_TOKEN
            else:
                # Instagram and Facebook Messenger use the same Send API
                url = f"{GRAPH_API_BASE}/me/messages"
                payload = {
                    "recipient": {"id": recipient_id},
                    "message": {"text": text},
                }
                token = settings.META_PAGE_ACCESS_TOKEN

            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"Meta message sent via {platform} to {recipient_id}")
            return result
    except Exception as e:
        logger.error(f"Failed to send Meta message ({platform}): {e}")
        return None


async def get_user_profile(platform: str, user_id: str) -> dict | None:
    """Fetch basic profile (name) for a Meta user.

    WhatsApp: profile name comes in the webhook payload, so this is primarily for FB/IG.
    """
    try:
        if platform == "whatsapp":
            return None  # WhatsApp profile comes in webhook payload

        token = settings.META_PAGE_ACCESS_TOKEN
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/{user_id}",
                params={"fields": "name", "access_token": token},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch Meta profile ({platform}, {user_id}): {e}")
        return None


def parse_webhook_entry(entry: dict) -> list[dict]:
    """Parse a single Meta webhook entry into normalized message dicts.

    Returns list of:
        {
            "platform": "whatsapp" | "instagram" | "facebook",
            "sender_id": str,
            "sender_name": str | None,
            "text": str,
            "message_id": str,
            "timestamp": str,
        }
    """
    messages = []

    # ── WhatsApp Cloud API format ──
    if "changes" in entry:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if value.get("messaging_product") == "whatsapp":
                contacts = {c["wa_id"]: c.get("profile", {}).get("name", "") for c in value.get("contacts", [])}
                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        continue  # Skip media/reactions for now
                    messages.append({
                        "platform": "whatsapp",
                        "sender_id": msg["from"],
                        "sender_name": contacts.get(msg["from"], ""),
                        "text": msg.get("text", {}).get("body", ""),
                        "message_id": msg["id"],
                        "timestamp": msg.get("timestamp", ""),
                    })

    # ── Instagram & Facebook Messenger format ──
    if "messaging" in entry:
        page_id = entry.get("id", "")
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id", "")
            # Ignore messages sent by the page itself
            if sender_id == page_id:
                continue
            msg = event.get("message", {})
            if not msg or msg.get("is_echo"):
                continue
            text = msg.get("text", "")
            if not text:
                continue  # Skip attachments-only for now
            # Determine platform by presence of instagram-specific fields
            # Instagram webhooks come on the "instagram" object; FB on "page"
            platform = "instagram" if entry.get("id") and "instagram" in str(entry.get("messaging_type", "")) else "facebook"
            messages.append({
                "platform": platform,
                "sender_id": sender_id,
                "sender_name": None,  # Fetched separately via profile API
                "text": text,
                "message_id": msg.get("mid", ""),
                "timestamp": str(event.get("timestamp", "")),
            })

    return messages
```

**Step 2: Commit**

```bash
git add backend/app/services/meta_service.py
git commit -m "feat(meta): create Meta message service for WhatsApp/Instagram/Facebook"
```

---

## Task 4: Add `ai_auto_reply()` to AI service

**Files:**
- Modify: `backend/app/services/ai_service.py`

**Step 1: Add the system prompt constant**

After the existing `SUMMARY_SYSTEM_PROMPT` (around line 121), add:

```python
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
```

**Step 2: Add the `ai_auto_reply()` function**

After the existing `summarize_ticket()` function (after line 157), add:

```python
def ai_auto_reply(
    ticket_subject: str,
    conversation_history: list[dict],
    customer_name: str = "",
    category: str = "",
    kb_context: str = "",
    platform: str = "whatsapp",
) -> dict | None:
    """Generate an automatic AI reply for Meta channels (WhatsApp/Instagram/Facebook).

    Args:
        ticket_subject: Ticket subject/first message
        conversation_history: List of {"role": "customer"|"assistant", "content": str}
        customer_name: Customer's name
        category: Ticket category from triage
        kb_context: Relevant KB article text
        platform: "whatsapp", "instagram", or "facebook"

    Returns:
        {"response": str, "should_escalate": bool, "escalation_reason": str} or None
    """
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
```

**Step 3: Commit**

```bash
git add backend/app/services/ai_service.py
git commit -m "feat(meta): add ai_auto_reply() for social channel auto-responses"
```

---

## Task 5: Create Meta webhook API endpoint

**Files:**
- Create: `backend/app/api/meta.py`

**Step 1: Create the webhook endpoint with full message processing**

```python
"""Meta Platform webhook — handles WhatsApp, Instagram, and Facebook Messenger."""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, HTTPException, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.config import settings
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.customer import Customer
from app.services.meta_service import verify_signature, parse_webhook_entry, send_message, get_user_profile
from app.services.ai_service import triage_ticket as ai_triage, ai_auto_reply
from app.services.protocol_service import assign_protocol

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meta", tags=["meta"])


# ── Webhook verification (GET) — Meta sends this during app setup ──

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Handle Meta webhook verification challenge."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
        logger.info("Meta webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(403, "Verification failed")


# ── Webhook events (POST) — receives all messages ──

@router.post("/webhook")
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle incoming Meta webhook events (WhatsApp, Instagram, Facebook)."""
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(body, signature):
        raise HTTPException(401, "Invalid signature")

    data = await request.json()

    # Parse entries — Meta sends batched events
    for entry in data.get("entry", []):
        normalized_messages = parse_webhook_entry(entry)
        for msg_data in normalized_messages:
            try:
                await _process_inbound_message(db, msg_data)
            except Exception as e:
                logger.error(f"Error processing Meta message: {e}")

    return {"status": "ok"}


async def _process_inbound_message(db: AsyncSession, msg_data: dict):
    """Process a single inbound message from any Meta platform."""
    platform = msg_data["platform"]
    sender_id = msg_data["sender_id"]
    sender_name = msg_data.get("sender_name") or ""
    text = msg_data["text"]
    message_id = msg_data["message_id"]

    # ── 1. Check if message already processed ──
    existing = await db.execute(
        select(Message).where(Message.meta_message_id == message_id)
    )
    if existing.scalars().first():
        return

    # ── 2. Find or create customer ──
    customer = await _find_or_create_customer(db, platform, sender_id, sender_name)

    # ── 3. Find open ticket or create new one ──
    ticket = await _find_or_create_ticket(db, customer, platform, text)
    is_new_ticket = ticket.id is None or len(ticket.messages) == 0

    # ── 4. Create inbound message ──
    message = Message(
        ticket_id=ticket.id,
        type="inbound",
        sender_name=customer.name,
        sender_email=customer.email,
        body_text=text,
        meta_message_id=message_id,
        meta_platform=platform,
    )
    db.add(message)
    await db.flush()

    # ── 5. AI triage on first message ──
    if is_new_ticket:
        try:
            triage = ai_triage(
                subject=ticket.subject,
                body=text[:2000],
                customer_name=customer.name,
                is_repeat=customer.is_repeat,
            )
            if triage:
                if triage.get("category"):
                    ticket.ai_category = triage["category"]
                    ticket.category = triage["category"]
                if triage.get("priority"):
                    ticket.priority = triage["priority"]
                    hours_map = {
                        "urgent": settings.SLA_URGENT_HOURS,
                        "high": settings.SLA_HIGH_HOURS,
                        "medium": settings.SLA_MEDIUM_HOURS,
                        "low": settings.SLA_LOW_HOURS,
                    }
                    ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(
                        hours=hours_map.get(triage["priority"], 24)
                    )
                if triage.get("sentiment"):
                    ticket.sentiment = triage["sentiment"]
                if triage.get("legal_risk") is not None:
                    ticket.legal_risk = triage["legal_risk"]
                if triage.get("tags"):
                    ticket.tags = triage["tags"]
                if triage.get("confidence"):
                    ticket.ai_confidence = triage["confidence"]
        except Exception as e:
            logger.warning(f"AI triage skipped for Meta ticket: {e}")

    # ── 6. AI auto-reply (if enabled) ──
    if ticket.ai_auto_mode:
        await _send_ai_reply(db, ticket, customer, platform, sender_id)

    await db.commit()
    logger.info(f"Processed Meta {platform} message for ticket #{ticket.number}")


async def _find_or_create_customer(
    db: AsyncSession, platform: str, sender_id: str, sender_name: str
) -> Customer:
    """Find customer by meta_user_id or create a new one."""
    result = await db.execute(
        select(Customer).where(Customer.meta_user_id == sender_id)
    )
    customer = result.scalars().first()

    if customer:
        return customer

    # Fetch profile name from Meta if not provided
    if not sender_name:
        profile = await get_user_profile(platform, sender_id)
        if profile:
            sender_name = profile.get("name", "")

    name = sender_name or f"{platform.capitalize()} User"
    # Create with a placeholder email — Meta doesn't expose emails
    email = f"{sender_id}@{platform}.meta.local"

    customer = Customer(
        name=name,
        email=email,
        meta_user_id=sender_id,
    )
    db.add(customer)
    await db.flush()
    return customer


async def _find_or_create_ticket(
    db: AsyncSession, customer: Customer, platform: str, text: str
) -> Ticket:
    """Find an open ticket for this customer+platform, or create a new one."""
    # Look for an existing open ticket from the same customer on the same platform
    result = await db.execute(
        select(Ticket).where(
            Ticket.customer_id == customer.id,
            Ticket.meta_platform == platform,
            Ticket.status.notin_(["resolved", "closed", "archived"]),
        ).order_by(Ticket.created_at.desc())
    )
    ticket = result.scalars().first()

    if ticket:
        # Reopen if escalated but customer came back
        if ticket.status == "escalated":
            ticket.status = "open"
        ticket.updated_at = datetime.now(timezone.utc)
        return ticket

    # Create new ticket
    max_num = await db.execute(select(func.max(Ticket.number)))
    next_num = (max_num.scalar() or 1000) + 1

    subject = text.split("\n")[0][:100] if text else f"Mensagem via {platform.capitalize()}"

    sla_deadline = datetime.now(timezone.utc) + timedelta(hours=settings.SLA_MEDIUM_HOURS)

    ticket = Ticket(
        number=next_num,
        subject=subject,
        status="open",
        priority="medium",
        customer_id=customer.id,
        source=platform,
        meta_platform=platform,
        meta_conversation_id=f"{customer.meta_user_id}_{platform}",
        ai_auto_mode=True,
        sla_deadline=sla_deadline,
    )
    db.add(ticket)
    await db.flush()

    try:
        await assign_protocol(ticket, db)
    except Exception:
        pass

    return ticket


async def _send_ai_reply(
    db: AsyncSession, ticket: Ticket, customer: Customer, platform: str, recipient_id: str
):
    """Generate and send AI auto-reply."""
    # Build conversation history from ticket messages
    msgs = await db.execute(
        select(Message)
        .where(Message.ticket_id == ticket.id)
        .order_by(Message.created_at)
    )
    all_messages = msgs.scalars().all()

    conversation_history = []
    for m in all_messages:
        role = "customer" if m.type == "inbound" else "assistant"
        conversation_history.append({"role": role, "content": m.body_text or ""})

    # Gather KB context
    kb_context = await _get_kb_context(db, ticket.category)

    # Call AI
    result = ai_auto_reply(
        ticket_subject=ticket.subject,
        conversation_history=conversation_history,
        customer_name=customer.name,
        category=ticket.category or "",
        kb_context=kb_context,
        platform=platform,
    )

    if not result or not result.get("response"):
        logger.warning(f"AI auto-reply returned empty for ticket #{ticket.number}")
        return

    response_text = result["response"]

    # Send via Meta API
    sent = await send_message(platform, recipient_id, response_text)
    if not sent:
        logger.error(f"Failed to send AI reply via {platform} for ticket #{ticket.number}")
        return

    # Save outbound message
    outbound = Message(
        ticket_id=ticket.id,
        type="outbound",
        sender_name="Carbon IA",
        body_text=response_text,
        meta_message_id=sent.get("messages", [{}])[0].get("id", "") if platform == "whatsapp" else sent.get("message_id", ""),
        meta_platform=platform,
    )
    db.add(outbound)

    # Handle escalation
    if result.get("should_escalate"):
        ticket.status = "escalated"
        ticket.escalated_at = datetime.now(timezone.utc)
        ticket.escalation_reason = result.get("escalation_reason", "AI escalation from social channel")

    # Mark first response
    if not ticket.first_response_at:
        ticket.first_response_at = datetime.now(timezone.utc)


async def _get_kb_context(db: AsyncSession, category: str | None) -> str:
    """Fetch relevant KB articles for the given category."""
    from app.models.kb_article import KBArticle
    try:
        query = select(KBArticle).where(KBArticle.is_published.is_(True))
        if category:
            query = query.where(KBArticle.category == category)
        query = query.limit(3)
        result = await db.execute(query)
        articles = result.scalars().all()
        if not articles:
            # Fallback: get any 2 published articles
            result = await db.execute(
                select(KBArticle).where(KBArticle.is_published.is_(True)).limit(2)
            )
            articles = result.scalars().all()
        return "\n\n".join(f"## {a.title}\n{a.content[:800]}" for a in articles)
    except Exception as e:
        logger.warning(f"KB context fetch failed: {e}")
        return ""
```

**Step 2: Commit**

```bash
git add backend/app/api/meta.py
git commit -m "feat(meta): create webhook endpoint with message processing and AI auto-reply"
```

---

## Task 6: Register Meta router and API endpoints

**Files:**
- Modify: `backend/app/main.py:11-12, 354-371`
- Modify: `backend/app/services/api.js:74-77`

**Step 1: Import and register the meta router in main.py**

In `backend/app/main.py`, line 11, add `meta` to the import:

```python
from app.api import auth, tickets, inboxes, dashboard, kb, slack, gmail, ai, reports, export, ws, tracking, shopify, media, ecommerce, catalog, gamification, rewards, meta
```

After line 370 (the rewards router), add:

```python
app.include_router(meta.router, prefix="/api")
```

**Step 2: Add frontend API functions**

In `frontend/src/services/api.js`, after the Slack section (~line 76), add:

```javascript
// ── Meta (WhatsApp, Instagram, Facebook) ──
export const getMetaStatus = () => api.get('/meta/status')
export const pauseTicketAI = (ticketId) => api.post(`/meta/tickets/${ticketId}/pause-ai`)
export const resumeTicketAI = (ticketId) => api.post(`/meta/tickets/${ticketId}/resume-ai`)
export const sendMetaReply = (data) => api.post('/meta/send-reply', data)
```

**Step 3: Commit**

```bash
git add backend/app/main.py frontend/src/services/api.js
git commit -m "feat(meta): register Meta router and add frontend API functions"
```

---

## Task 7: Add Meta agent endpoints (status, pause/resume AI, manual reply)

**Files:**
- Modify: `backend/app/api/meta.py` (append to end of file)

**Step 1: Add agent-facing endpoints**

Append to the end of `backend/app/api/meta.py`:

```python
# ── Agent-facing API endpoints ──

from app.core.security import get_current_user
from app.models.user import User


@router.get("/status")
async def meta_status(user: User = Depends(get_current_user)):
    """Check if Meta integration is configured."""
    whatsapp_configured = bool(settings.META_WHATSAPP_TOKEN and settings.META_WHATSAPP_PHONE_ID)
    fb_ig_configured = bool(settings.META_PAGE_ACCESS_TOKEN)

    return {
        "whatsapp": {"configured": whatsapp_configured},
        "instagram": {"configured": fb_ig_configured},
        "facebook": {"configured": fb_ig_configured},
        "webhook_configured": bool(settings.META_APP_SECRET and settings.META_VERIFY_TOKEN),
    }


@router.post("/tickets/{ticket_id}/pause-ai")
async def pause_ai(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Pause AI auto-reply on a Meta ticket (agent takes over)."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    if not ticket.meta_platform:
        raise HTTPException(400, "Este ticket não é de um canal Meta")

    ticket.ai_auto_mode = False
    ticket.ai_paused_by = user.id
    ticket.ai_paused_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"AI paused on ticket #{ticket.number} by {user.name}")
    return {"ok": True, "ai_auto_mode": False}


@router.post("/tickets/{ticket_id}/resume-ai")
async def resume_ai(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Resume AI auto-reply on a Meta ticket."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    if not ticket.meta_platform:
        raise HTTPException(400, "Este ticket não é de um canal Meta")

    ticket.ai_auto_mode = True
    ticket.ai_paused_by = None
    ticket.ai_paused_at = None
    await db.commit()

    logger.info(f"AI resumed on ticket #{ticket.number} by {user.name}")
    return {"ok": True, "ai_auto_mode": True}


@router.post("/send-reply")
async def send_manual_reply(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a manual agent reply to a Meta channel (when AI is paused)."""
    data = await request.json()
    ticket_id = data.get("ticket_id")
    message_text = data.get("message")

    if not ticket_id or not message_text:
        raise HTTPException(400, "ticket_id e message são obrigatórios")

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    if not ticket.meta_platform:
        raise HTTPException(400, "Este ticket não é de um canal Meta")

    # Get customer to find recipient ID
    cust_result = await db.execute(select(Customer).where(Customer.id == ticket.customer_id))
    customer = cust_result.scalars().first()
    if not customer or not customer.meta_user_id:
        raise HTTPException(400, "Cliente não tem ID Meta")

    # Send via Meta API
    sent = await send_message(ticket.meta_platform, customer.meta_user_id, message_text)
    if not sent:
        raise HTTPException(500, "Falha ao enviar mensagem")

    # Save message
    msg = Message(
        ticket_id=ticket.id,
        type="outbound",
        sender_name=user.name,
        sender_email=user.email,
        body_text=message_text,
        meta_platform=ticket.meta_platform,
    )
    db.add(msg)

    ticket.last_agent_response_at = datetime.now(timezone.utc)
    if not ticket.first_response_at:
        ticket.first_response_at = datetime.now(timezone.utc)

    await db.commit()
    return {"ok": True}
```

**Step 2: Commit**

```bash
git add backend/app/api/meta.py
git commit -m "feat(meta): add agent endpoints — status, pause/resume AI, manual reply"
```

---

## Task 8: Frontend — Add channel badges to TicketsPage

**Files:**
- Create: `frontend/src/components/MetaBadge.jsx`
- Modify: `frontend/src/pages/TicketsPage.jsx`

**Step 1: Create the MetaBadge component**

```jsx
import React from 'react'

const CHANNEL_CONFIG = {
  whatsapp: { icon: 'fab fa-whatsapp', label: 'WhatsApp', color: 'text-green-400', bg: 'bg-green-500/10' },
  instagram: { icon: 'fab fa-instagram', label: 'Instagram', color: 'text-pink-400', bg: 'bg-pink-500/10' },
  facebook: { icon: 'fab fa-facebook-messenger', label: 'Facebook', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  gmail: { icon: 'fas fa-envelope', label: 'Email', color: 'text-red-400', bg: 'bg-red-500/10' },
  slack: { icon: 'fab fa-slack', label: 'Slack', color: 'text-purple-400', bg: 'bg-purple-500/10' },
  web: { icon: 'fas fa-globe', label: 'Web', color: 'text-gray-400', bg: 'bg-gray-500/10' },
}

export default function MetaBadge({ source, size = 'sm', showLabel = false, aiAutoMode, className = '' }) {
  const config = CHANNEL_CONFIG[source] || CHANNEL_CONFIG.web
  const sizeClass = size === 'lg' ? 'text-base px-2.5 py-1' : 'text-xs px-1.5 py-0.5'

  return (
    <span className={`inline-flex items-center gap-1 rounded ${config.bg} ${config.color} ${sizeClass} ${className}`}>
      <i className={config.icon} />
      {showLabel && <span>{config.label}</span>}
      {aiAutoMode === false && source && ['whatsapp', 'instagram', 'facebook'].includes(source) && (
        <span className="ml-0.5 text-yellow-400" title="IA Pausada">
          <i className="fas fa-pause-circle text-[10px]" />
        </span>
      )}
      {aiAutoMode === true && source && ['whatsapp', 'instagram', 'facebook'].includes(source) && (
        <span className="ml-0.5 text-emerald-400" title="IA Ativa">
          <i className="fas fa-robot text-[10px]" />
        </span>
      )}
    </span>
  )
}

export { CHANNEL_CONFIG }
```

**Step 2: Add MetaBadge to TicketsPage ticket list**

In `frontend/src/pages/TicketsPage.jsx`, add the import at the top:

```javascript
import MetaBadge from '../components/MetaBadge'
```

Find the ticket row rendering section where `ticket.source` or ticket subject is displayed. In the ticket row, near the ticket number/subject area, add the badge:

```jsx
<MetaBadge source={ticket.source} aiAutoMode={ticket.ai_auto_mode} />
```

Also add source filter options. In the filter/toolbar area, add "whatsapp", "instagram", "facebook" to any existing source filter dropdown (alongside "gmail", "slack", "web").

**Step 3: Commit**

```bash
git add frontend/src/components/MetaBadge.jsx frontend/src/pages/TicketsPage.jsx
git commit -m "feat(meta): add channel badges and source filters to ticket list"
```

---

## Task 9: Frontend — Add AI controls to TicketDetailPage

**Files:**
- Modify: `frontend/src/pages/TicketDetailPage.jsx`

**Step 1: Import new API functions and MetaBadge**

At the top of the file, add to existing imports:

```javascript
import { pauseTicketAI, resumeTicketAI, sendMetaReply } from '../services/api'
import MetaBadge from '../components/MetaBadge'
```

**Step 2: Add AI control state**

Inside the component function, add state:

```javascript
const [aiPausing, setAiPausing] = useState(false)
```

**Step 3: Add AI control handler functions**

```javascript
const isMetaChannel = ticket && ['whatsapp', 'instagram', 'facebook'].includes(ticket.source)

const handlePauseAI = async () => {
  setAiPausing(true)
  try {
    await pauseTicketAI(ticket.id)
    setTicket(prev => ({ ...prev, ai_auto_mode: false }))
    toast.success('IA pausada — você pode responder manualmente')
  } catch (e) {
    toast.error('Erro ao pausar IA')
  } finally {
    setAiPausing(false)
  }
}

const handleResumeAI = async () => {
  setAiPausing(true)
  try {
    await resumeTicketAI(ticket.id)
    setTicket(prev => ({ ...prev, ai_auto_mode: true }))
    toast.success('IA retomada — respostas automáticas ativadas')
  } catch (e) {
    toast.error('Erro ao retomar IA')
  } finally {
    setAiPausing(false)
  }
}
```

**Step 4: Add the AI banner and controls to the ticket detail UI**

Above the message timeline (right after the ticket header area), add:

```jsx
{isMetaChannel && (
  <div className={`flex items-center justify-between px-4 py-2.5 rounded-lg mb-3 ${
    ticket.ai_auto_mode
      ? 'bg-emerald-500/10 border border-emerald-500/20'
      : 'bg-yellow-500/10 border border-yellow-500/20'
  }`}>
    <div className="flex items-center gap-2 text-sm">
      <MetaBadge source={ticket.source} size="lg" showLabel />
      {ticket.ai_auto_mode ? (
        <span className="text-emerald-400">
          <i className="fas fa-robot mr-1" />
          IA respondendo automaticamente
        </span>
      ) : (
        <span className="text-yellow-400">
          <i className="fas fa-pause-circle mr-1" />
          IA pausada — modo manual
        </span>
      )}
    </div>
    <button
      onClick={ticket.ai_auto_mode ? handlePauseAI : handleResumeAI}
      disabled={aiPausing}
      className={`px-3 py-1.5 rounded text-xs font-medium transition ${
        ticket.ai_auto_mode
          ? 'bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30'
          : 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30'
      }`}
    >
      {aiPausing ? (
        <i className="fas fa-spinner fa-spin" />
      ) : ticket.ai_auto_mode ? (
        <><i className="fas fa-pause mr-1" />Pausar IA</>
      ) : (
        <><i className="fas fa-play mr-1" />Retomar IA</>
      )}
    </button>
  </div>
)}
```

**Step 5: Mark AI messages in the timeline**

In the message rendering loop, add a badge for AI-generated messages:

```jsx
{msg.sender_name === 'Carbon IA' && (
  <span className="ml-2 text-[10px] bg-emerald-500/15 text-emerald-400 px-1.5 py-0.5 rounded">
    <i className="fas fa-robot mr-0.5" />IA
  </span>
)}
```

**Step 6: Modify reply area for Meta channels**

When `isMetaChannel && ticket.ai_auto_mode`, hide or disable the reply text area (since AI is responding). When `isMetaChannel && !ticket.ai_auto_mode`, show a simplified reply area that calls `sendMetaReply` instead of `addMessage`:

In the send handler, add a check at the top:

```javascript
// If Meta channel with AI paused, send via Meta API
if (isMetaChannel && !ticket.ai_auto_mode) {
  await sendMetaReply({ ticket_id: ticket.id, message: reply })
  // Refresh ticket to see the new message
  const { data } = await getTicket(ticketId)
  setTicket(data)
  setReply('')
  setSending(false)
  return
}
```

**Step 7: Commit**

```bash
git add frontend/src/pages/TicketDetailPage.jsx
git commit -m "feat(meta): add AI controls (pause/resume) and channel banner to ticket detail"
```

---

## Task 10: Add source filter to TicketsPage

**Files:**
- Modify: `frontend/src/pages/TicketsPage.jsx`

**Step 1: Add source filter state**

Inside the component, add:

```javascript
const [sourceFilter, setSourceFilter] = useState('')
```

**Step 2: Pass source to API call**

In the `loadTickets` function, add `source` to the params:

```javascript
const params = {
  // ... existing params
  source: sourceFilter || undefined,
}
```

**Step 3: Add source filter dropdown to the toolbar**

Near the existing status/priority filters, add:

```jsx
<select
  value={sourceFilter}
  onChange={e => { setSourceFilter(e.target.value); setPage(1) }}
  className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200"
>
  <option value="">Todos os canais</option>
  <option value="web">Web</option>
  <option value="gmail">Email</option>
  <option value="slack">Slack</option>
  <option value="whatsapp">WhatsApp</option>
  <option value="instagram">Instagram</option>
  <option value="facebook">Facebook</option>
</select>
```

**Step 4: Add source param support to backend tickets API**

In `backend/app/api/tickets.py`, in the `list_tickets` endpoint, add `source` to the query parameters and filter:

```python
source: str | None = None,
```

And in the query building:

```python
if source:
    query = query.where(Ticket.source == source)
```

**Step 5: Commit**

```bash
git add frontend/src/pages/TicketsPage.jsx backend/app/api/tickets.py
git commit -m "feat(meta): add source/channel filter to ticket list"
```

---

## Task 11: Add Meta status to IntegrationsPage

**Files:**
- Modify: `frontend/src/pages/IntegrationsPage.jsx`

**Step 1: Import getMetaStatus**

```javascript
import { getMetaStatus } from '../services/api'
```

**Step 2: Add Meta status state and fetch**

```javascript
const [metaStatus, setMetaStatus] = useState(null)

useEffect(() => {
  // ... existing fetches
  getMetaStatus().then(r => setMetaStatus(r.data)).catch(() => {})
}, [])
```

**Step 3: Add Meta cards to the integrations page**

After the existing Slack/Gmail cards, add:

```jsx
{/* Meta Channels */}
<div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700/50">
  <div className="flex items-center gap-3 mb-4">
    <div className="w-10 h-10 rounded-lg bg-green-500/15 flex items-center justify-center">
      <i className="fab fa-whatsapp text-green-400 text-xl" />
    </div>
    <div>
      <h3 className="font-medium text-white">WhatsApp Business</h3>
      <p className="text-xs text-gray-400">Atendimento automático por IA</p>
    </div>
    <span className={`ml-auto px-2 py-1 rounded text-xs ${
      metaStatus?.whatsapp?.configured
        ? 'bg-green-500/15 text-green-400'
        : 'bg-gray-600/20 text-gray-500'
    }`}>
      {metaStatus?.whatsapp?.configured ? 'Configurado' : 'Não configurado'}
    </span>
  </div>
</div>

<div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700/50">
  <div className="flex items-center gap-3 mb-4">
    <div className="w-10 h-10 rounded-lg bg-pink-500/15 flex items-center justify-center">
      <i className="fab fa-instagram text-pink-400 text-xl" />
    </div>
    <div>
      <h3 className="font-medium text-white">Instagram</h3>
      <p className="text-xs text-gray-400">Mensagens Direct com IA</p>
    </div>
    <span className={`ml-auto px-2 py-1 rounded text-xs ${
      metaStatus?.instagram?.configured
        ? 'bg-green-500/15 text-green-400'
        : 'bg-gray-600/20 text-gray-500'
    }`}>
      {metaStatus?.instagram?.configured ? 'Configurado' : 'Não configurado'}
    </span>
  </div>
</div>

<div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700/50">
  <div className="flex items-center gap-3 mb-4">
    <div className="w-10 h-10 rounded-lg bg-blue-500/15 flex items-center justify-center">
      <i className="fab fa-facebook-messenger text-blue-400 text-xl" />
    </div>
    <div>
      <h3 className="font-medium text-white">Facebook Messenger</h3>
      <p className="text-xs text-gray-400">Mensagens do Messenger com IA</p>
    </div>
    <span className={`ml-auto px-2 py-1 rounded text-xs ${
      metaStatus?.facebook?.configured
        ? 'bg-green-500/15 text-green-400'
        : 'bg-gray-600/20 text-gray-500'
    }`}>
      {metaStatus?.facebook?.configured ? 'Configurado' : 'Não configurado'}
    </span>
  </div>
</div>
```

**Step 4: Commit**

```bash
git add frontend/src/pages/IntegrationsPage.jsx
git commit -m "feat(meta): add WhatsApp/Instagram/Facebook status cards to integrations page"
```

---

## Task 12: Fix Instagram platform detection in webhook parser

**Files:**
- Modify: `backend/app/services/meta_service.py`

**Step 1: Improve platform detection**

The initial implementation uses a heuristic for distinguishing Instagram from Facebook in the webhook parser. Meta sends different webhook objects for each:
- **Instagram**: The webhook subscription object is `"instagram"` and entries come under `"messaging"` with the Instagram-scoped user ID (IGSID)
- **Facebook Page**: The webhook subscription object is `"page"` and entries also come under `"messaging"` with the Page-scoped user ID (PSID)

Update the `parse_webhook_entry` function and the `receive_webhook` endpoint to pass the `object` field from the top-level webhook payload:

In `meta.py`, change the receive_webhook call:

```python
# In receive_webhook, pass the object type
webhook_object = data.get("object", "")
for entry in data.get("entry", []):
    normalized_messages = parse_webhook_entry(entry, webhook_object)
```

In `meta_service.py`, update the function signature and detection:

```python
def parse_webhook_entry(entry: dict, webhook_object: str = "") -> list[dict]:
```

And replace the Instagram/Facebook detection logic:

```python
            platform = "instagram" if webhook_object == "instagram" else "facebook"
```

**Step 2: Commit**

```bash
git add backend/app/services/meta_service.py backend/app/api/meta.py
git commit -m "fix(meta): improve Instagram vs Facebook platform detection using webhook object type"
```

---

## Task 13: Update dashboard stats to include Meta channels

**Files:**
- Modify: `backend/app/api/dashboard.py` (if it filters by source)
- Modify: `frontend/src/pages/DashboardPage.jsx` (if it shows source breakdown)

**Step 1: Verify dashboard includes all sources**

Check that the dashboard stats query does NOT filter by source — it should already count all tickets regardless of source. If it does filter, add the new sources.

In the frontend dashboard, if there's a source breakdown chart, add the 3 new channels with their colors:

```javascript
const SOURCE_COLORS = {
  web: '#6B7280',
  gmail: '#EF4444',
  slack: '#8B5CF6',
  whatsapp: '#22C55E',
  instagram: '#EC4899',
  facebook: '#3B82F6',
}
```

**Step 2: Commit**

```bash
git add backend/app/api/dashboard.py frontend/src/pages/DashboardPage.jsx
git commit -m "feat(meta): include Meta channels in dashboard source breakdown"
```

---

## Task 14: Final integration test and cleanup

**Step 1: Verify all imports are correct**

Run: `cd /Users/pedrocastro/Desktop/carbon-helpdesk/backend && python -c "from app.api.meta import router; print('Meta router OK')"`
Expected: "Meta router OK"

Run: `cd /Users/pedrocastro/Desktop/carbon-helpdesk/backend && python -c "from app.services.meta_service import verify_signature, send_message, parse_webhook_entry; print('Meta service OK')"`
Expected: "Meta service OK"

Run: `cd /Users/pedrocastro/Desktop/carbon-helpdesk/backend && python -c "from app.services.ai_service import ai_auto_reply; print('AI auto-reply OK')"`
Expected: "AI auto-reply OK"

**Step 2: Verify the full app starts**

Run: `cd /Users/pedrocastro/Desktop/carbon-helpdesk/backend && timeout 10 python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 || true`
Expected: Server starts without import errors (will timeout after 10s, that's fine)

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(meta): complete WhatsApp, Instagram, and Facebook integration

- Meta webhook endpoint (single endpoint for all 3 platforms)
- AI auto-reply pipeline with KB context
- Agent UI: channel badges, AI pause/resume, manual reply
- Source filter on ticket list
- Integration status cards
- Database schema migrations"
```

---

## Summary of all new/modified files

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/core/config.py` | Modify | Add META_* env vars |
| `backend/app/models/ticket.py` | Modify | Add meta_*, ai_auto_mode fields |
| `backend/app/models/message.py` | Modify | Add meta_message_id, meta_platform |
| `backend/app/models/customer.py` | Modify | Add meta_user_id |
| `backend/app/schemas/ticket.py` | Modify | Add new fields to response schema |
| `backend/app/main.py` | Modify | Migrations + register meta router |
| `backend/app/services/meta_service.py` | Create | Meta API messaging + webhook parser |
| `backend/app/services/ai_service.py` | Modify | Add ai_auto_reply() |
| `backend/app/api/meta.py` | Create | Webhook + agent endpoints |
| `backend/app/api/tickets.py` | Modify | Add source filter param |
| `frontend/src/services/api.js` | Modify | Add Meta API functions |
| `frontend/src/components/MetaBadge.jsx` | Create | Channel badge component |
| `frontend/src/pages/TicketsPage.jsx` | Modify | Badges + source filter |
| `frontend/src/pages/TicketDetailPage.jsx` | Modify | AI controls + banner |
| `frontend/src/pages/IntegrationsPage.jsx` | Modify | Meta status cards |
| `frontend/src/pages/DashboardPage.jsx` | Modify | Source colors |
