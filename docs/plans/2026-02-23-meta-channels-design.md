# Meta Channels Integration — Design Document

**Date:** 2026-02-23
**Status:** Approved
**Author:** Claude (brainstorming session)

## Goal

Integrate WhatsApp, Instagram, and Facebook Messenger into Carbon Expert Hub using Meta's APIs directly. All 3 channels are AI-only — Claude responds automatically to every message. Human agents have read-only access with emergency intervention capability (pause AI, take over manually).

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API approach | Meta API Direct | Already have Meta Business; no middleware cost |
| AI model | 100% AI auto-response | Reduces agent workload on social channels |
| Escalation | AI directs customer to email | Keeps complex cases in existing email workflow |
| Agent access | Read + emergency intervention | Agents can pause AI and respond manually |
| Knowledge base | Same helpdesk KB | Single source of truth |
| Data model | Extend existing Ticket/Message | No new models, minimal schema changes |

## Architecture

```
                    ┌─────────────────────────┐
                    │   Meta Webhook Gateway   │
                    │  POST /api/meta/webhook  │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │   HMAC-SHA256 Verify    │
                    └────────┬────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───┐  ┌──────▼─────┐  ┌────▼────────┐
     │  WhatsApp  │  │ Instagram  │  │  Facebook   │
     │  handler   │  │  handler   │  │  handler    │
     └────────┬───┘  └──────┬─────┘  └────┬────────┘
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  Meta Message Service   │
                    └────────┬────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───┐  ┌──────▼─────┐  ┌────▼────────┐
     │ Ticket     │  │ AI Auto-   │  │ Send reply  │
     │ create/    │  │ Reply      │  │ via Meta    │
     │ update     │  │            │  │ Graph API   │
     └────────────┘  └────────────┘  └─────────────┘
```

## Data Model Changes

### Ticket (new fields)

- `meta_conversation_id` — String(100), nullable, indexed. Meta conversation/thread ID.
- `meta_platform` — String(20), nullable. "whatsapp" | "instagram" | "facebook".
- `ai_auto_mode` — Boolean, default True. When True, AI responds automatically.
- `ai_paused_by` — UUID FK to users, nullable. Agent who paused AI.
- `ai_paused_at` — DateTime, nullable.
- `source` — Extend existing values: add "whatsapp", "instagram", "facebook".

### Message (new fields)

- `meta_message_id` — String(100), nullable. Meta's message ID.
- `meta_platform` — String(20), nullable.

### Customer (new field)

- `meta_user_id` — String(100), nullable, indexed. Meta's sender ID (PSID/IGID/phone).

## Webhook Flow

### Inbound (customer → helpdesk)

1. Meta POST → `/api/meta/webhook`
2. Verify HMAC-SHA256 signature (X-Hub-Signature-256 header)
3. Parse payload → identify platform (whatsapp/instagram/messenger)
4. Extract sender ID, name, text content
5. Find/create Customer by meta_user_id
6. Find open Ticket for customer+platform → or create new
7. Create Message (type=inbound)
8. If `ai_auto_mode=True` → trigger AI auto-reply pipeline

### Outbound (AI/agent → customer)

1. AI generates response (or agent types manually)
2. `meta_service.send_message(platform, recipient_id, text)`
3. Create Message (type=outbound)
4. Platform-specific API calls:
   - WhatsApp: `POST /v21.0/{phone_number_id}/messages`
   - Instagram: `POST /v21.0/me/messages`
   - Facebook: `POST /v21.0/me/messages`

## AI Auto-Reply Pipeline

New function: `ai_auto_reply()` in ai_service.py

**Input:** ticket subject, conversation history, customer name, category, KB context, platform
**Output:** `{response: str, should_escalate: bool, escalation_reason: str}`

**Behavior:**
- Short, conversational responses (max 300 words)
- Friendly tone, moderate emoji usage
- Brazilian Portuguese
- Uses KB articles as knowledge base
- When unable to resolve → escalation (directs to email)
- Never fabricates information or makes promises outside policy

**Triage:** Reuses existing `triage_ticket()` on first message only.

## Escalation Flow

When AI detects it cannot resolve:

1. AI responds: "Para resolver da melhor forma, envie um e-mail para suporte@carbonsmartwatch.com.br com o assunto '[protocolo]'."
2. Ticket status → "escalated", escalation_reason filled
3. AI stays active (repeats email guidance if customer insists)
4. Dashboard notification for agents

**Escalation triggers:**
- Legal keywords (PROCON, advogado, processo)
- Complex technical issues outside KB
- Customer unsatisfied after 3+ messages
- Refund/exchange requiring human approval

## Agent UI

**Ticket list:**
- Channel badges (WhatsApp/Instagram/Facebook icons)
- AI status indicator (Active/Paused)
- Source filter

**Ticket detail (Meta channels):**
- Normal message timeline
- Top banner: "Este canal é atendido por IA automaticamente"
- "Pausar IA" button → disables auto-reply, shows text input for agent
- "Retomar IA" button → re-enables auto-reply
- AI messages marked with "IA" badge vs agent name badge

## Configuration

**Environment variables:**
```
META_APP_SECRET=xxx
META_VERIFY_TOKEN=xxx
META_PAGE_ACCESS_TOKEN=xxx
META_WHATSAPP_TOKEN=xxx
META_WHATSAPP_PHONE_ID=xxx
```

## Files

**New:**
- `backend/app/api/meta.py` — Webhook endpoint + handlers
- `backend/app/services/meta_service.py` — Send messages via Graph API
- `frontend/src/components/MetaBadge.jsx` — Channel badge component

**Modified:**
- `backend/app/models/ticket.py` — New fields
- `backend/app/models/message.py` — New fields
- `backend/app/models/customer.py` — meta_user_id
- `backend/app/services/ai_service.py` — ai_auto_reply()
- `backend/app/main.py` — Register meta router
- `backend/app/core/config.py` — Meta env vars
- `frontend/src/pages/TicketsPage.jsx` — Badges, filters
- `frontend/src/pages/TicketDetailPage.jsx` — Pause/Resume AI
- `frontend/src/services/api.js` — New endpoints
