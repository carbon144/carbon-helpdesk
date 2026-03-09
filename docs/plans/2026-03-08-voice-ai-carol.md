# Voice AI Carol — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add phone-based Voice AI (Carol) to Carbon Helpdesk using Twilio + Vapi.ai, with call recording/transcription visible in the helpdesk panel.

**Architecture:** Twilio provides a fixed SP phone number that forwards calls to Vapi.ai. Vapi orchestrates STT (Deepgram) → LLM (Claude) → TTS (ElevenLabs). When the AI needs data (order lookup, tracking, Troque status), Vapi calls custom tools via webhook to our FastAPI backend. End-of-call reports with recording + transcript are saved to a new `voice_calls` table and displayed in the frontend.

**Tech Stack:** FastAPI (backend), React (frontend), Vapi.ai, Twilio, ElevenLabs, PostgreSQL

---

## Task 1: Add Vapi config to Settings

**Files:**
- Modify: `backend/app/core/config.py`

**Step 1: Add Vapi settings to config**

Add after the WONCA/Notion settings block (line ~62):

```python
# Vapi Voice AI
VAPI_API_KEY: str = ""
VAPI_SERVER_SECRET: str = ""  # shared secret to verify webhook requests
```

**Step 2: Add to .env on server**

```bash
VAPI_API_KEY=<will be set after creating Vapi account>
VAPI_SERVER_SECRET=<generate random 32-char string>
```

**Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat(voice): add Vapi config settings"
```

---

## Task 2: Create voice_calls DB model + migration

**Files:**
- Create: `backend/app/models/voice_call.py`
- Modify: `backend/app/models/__init__.py` (if it imports models)

**Step 1: Create VoiceCall model**

```python
"""Voice call records from Vapi."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class VoiceCall(Base):
    __tablename__ = "voice_calls"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    vapi_call_id = Column(String(255), unique=True, index=True)
    caller_phone = Column(String(50))
    duration_seconds = Column(Float, default=0)
    recording_url = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    ended_reason = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    ticket = relationship("Ticket", backref="voice_calls")
    conversation = relationship("Conversation", backref="voice_calls")
```

**Step 2: Create Alembic migration**

```bash
cd backend
alembic revision --autogenerate -m "add voice_calls table"
alembic upgrade head
```

**Step 3: Commit**

```bash
git add backend/app/models/voice_call.py backend/alembic/versions/
git commit -m "feat(voice): add voice_calls model and migration"
```

---

## Task 3: Create voice_service.py — tool handlers

**Files:**
- Create: `backend/app/services/voice_service.py`

**Step 1: Create voice service with tool functions**

This service exposes the same logic the chatbot uses (Shopify, tracking, Troque) but formatted for Vapi tool responses.

```python
"""Voice AI service — tool handlers for Vapi webhooks."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.shopify_service import search_order
from app.services.tracking_service import get_tracking_info
from app.services.troque_service import search_by_order_number, search_by_phone, format_status_message
from app.models.voice_call import VoiceCall
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)


async def handle_lookup_order(db: AsyncSession, args: dict) -> str:
    """Lookup Shopify order by number. Returns formatted string for TTS."""
    order_number = args.get("order_number", "").strip()
    if not order_number:
        return "Nao consegui identificar o numero do pedido. Pode repetir?"

    order = await search_order(db, order_number)
    if not order:
        return f"Nao encontrei nenhum pedido com o numero {order_number}. Confere se o numero ta certo?"

    status_map = {
        "fulfilled": "enviado",
        "unfulfilled": "em preparacao",
        "partially_fulfilled": "parcialmente enviado",
        "cancelled": "cancelado",
        "refunded": "reembolsado",
    }
    status = status_map.get(order.get("fulfillment_status", ""), order.get("fulfillment_status", "desconhecido"))
    name = order.get("customer", {}).get("first_name", "")

    msg = f"Achei o pedido {order_number}"
    if name:
        msg += f" do {name}"
    msg += f". O status atual eh: {status}."

    tracking = order.get("tracking_number")
    if tracking:
        msg += f" O codigo de rastreio eh {tracking}."

    return msg


async def handle_lookup_tracking(db: AsyncSession, args: dict) -> str:
    """Lookup tracking info by code or order number."""
    code = args.get("tracking_code", "").strip()
    if not code:
        return "Nao consegui identificar o codigo de rastreio. Pode repetir?"

    info = await get_tracking_info(code)
    if not info or not info.get("events"):
        return f"Nao encontrei informacoes pro rastreio {code}. As vezes demora um pouco pra atualizar no sistema."

    latest = info["events"][0]
    return f"Ultimo status do rastreio: {latest.get('description', 'sem descricao')}, em {latest.get('date', '')}."


async def handle_lookup_troque(db: AsyncSession, args: dict) -> str:
    """Lookup Troque status by order number or phone."""
    order_number = args.get("order_number", "").strip()
    phone = args.get("phone", "").strip()

    result = None
    if order_number:
        result = await search_by_order_number(order_number)
    elif phone:
        result = await search_by_phone(phone)

    if not result:
        return "Nao encontrei nenhuma solicitacao no Troque. Voce ja abriu uma solicitacao pelo site carbonsmartwatch.troque.app.br?"

    return format_status_message(result)


async def handle_create_ticket(db: AsyncSession, args: dict) -> str:
    """Create a helpdesk ticket from voice call."""
    subject = args.get("subject", "Ligacao telefonica")
    description = args.get("description", "")
    caller_phone = args.get("caller_phone", "")
    customer_name = args.get("customer_name", "")

    ticket = Ticket(
        subject=f"[Ligacao] {subject}",
        body=f"Cliente: {customer_name or 'nao identificado'}\nTelefone: {caller_phone}\n\n{description}",
        source="phone",
        status="open",
        priority="medium",
        channel="phone",
    )
    db.add(ticket)
    await db.flush()

    return f"Pronto, abri um chamado pra voce, numero {ticket.number}. Nossa equipe vai retornar por email."


async def save_call_record(db: AsyncSession, data: dict) -> VoiceCall:
    """Save end-of-call report from Vapi."""
    call = data.get("call", {})
    artifact = data.get("artifact", {})

    voice_call = VoiceCall(
        vapi_call_id=call.get("id", ""),
        caller_phone=call.get("customer", {}).get("number", ""),
        duration_seconds=call.get("duration", 0),
        recording_url=artifact.get("recordingUrl", ""),
        transcript=artifact.get("transcript", ""),
        summary=artifact.get("summary", ""),
        ended_reason=data.get("endedReason", ""),
    )
    db.add(voice_call)
    await db.flush()

    return voice_call


# Map Vapi tool names to handler functions
TOOL_HANDLERS = {
    "lookup_order": handle_lookup_order,
    "lookup_tracking": handle_lookup_tracking,
    "lookup_troque": handle_lookup_troque,
    "create_ticket": handle_create_ticket,
}
```

**Step 2: Commit**

```bash
git add backend/app/services/voice_service.py
git commit -m "feat(voice): add voice_service with tool handlers"
```

---

## Task 4: Create Vapi webhook endpoint

**Files:**
- Create: `backend/app/api/webhooks/vapi.py`
- Modify: `backend/app/main.py` (register router)

**Step 1: Create Vapi webhook router**

```python
"""Vapi Voice AI webhook endpoint."""
import logging
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.voice_service import TOOL_HANDLERS, save_call_record

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks/vapi", tags=["vapi"])


@router.post("")
async def vapi_webhook(request: Request):
    """Handle all Vapi server URL events: tool-calls, end-of-call-report, etc."""
    body = await request.json()
    message = body.get("message", {})
    event_type = message.get("type", "")

    logger.info(f"Vapi webhook: {event_type}")

    # Verify shared secret if configured
    secret = request.headers.get("x-vapi-secret", "")
    if settings.VAPI_SERVER_SECRET and secret != settings.VAPI_SERVER_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret")

    if event_type == "tool-calls":
        return await _handle_tool_calls(message)

    elif event_type == "end-of-call-report":
        return await _handle_end_of_call(message)

    elif event_type == "assistant-request":
        # Return assistant config dynamically if needed
        return {"assistant": None}  # Use default Vapi assistant

    # Acknowledge other events
    return {"ok": True}


async def _handle_tool_calls(message: dict):
    """Process tool calls from Vapi and return results."""
    from app.core.database import async_session_factory

    tool_call_list = message.get("toolCallList", [])
    # Also check toolWithToolCallList format
    tool_with_list = message.get("toolWithToolCallList", [])
    if tool_with_list and not tool_call_list:
        tool_call_list = [
            {
                "id": item.get("toolCall", {}).get("id", ""),
                "name": item.get("name", ""),
                "arguments": item.get("toolCall", {}).get("parameters", {}),
            }
            for item in tool_with_list
        ]

    results = []
    async with async_session_factory() as db:
        for tc in tool_call_list:
            tool_name = tc.get("name", "")
            tool_call_id = tc.get("id", "")
            args = tc.get("arguments", {})

            handler = TOOL_HANDLERS.get(tool_name)
            if handler:
                try:
                    result = await handler(db, args)
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}")
                    result = "Desculpa, tive um probleminha aqui. Pode repetir?"
            else:
                logger.warning(f"Unknown tool: {tool_name}")
                result = "Desculpa, nao consigo fazer isso agora."

            results.append({
                "toolCallId": tool_call_id,
                "result": result,
            })

        await db.commit()

    return {"results": results}


async def _handle_end_of_call(message: dict):
    """Save call recording and transcript."""
    from app.core.database import async_session_factory

    async with async_session_factory() as db:
        voice_call = await save_call_record(db, message)
        await db.commit()
        logger.info(f"Saved voice call {voice_call.vapi_call_id}, duration={voice_call.duration_seconds}s")

    return {"ok": True}
```

**Step 2: Register router in main.py**

In `backend/app/main.py`, add with the other webhook imports:

```python
from app.api.webhooks.vapi import router as vapi_webhook_router
app.include_router(vapi_webhook_router)
```

**Step 3: Commit**

```bash
git add backend/app/api/webhooks/vapi.py backend/app/main.py
git commit -m "feat(voice): add Vapi webhook endpoint with tool-calls and end-of-call handling"
```

---

## Task 5: Create Vapi assistant configuration script

**Files:**
- Create: `backend/scripts/setup_vapi_assistant.py`

**Step 1: Write setup script that creates the Vapi assistant via API**

This script configures the Vapi assistant with:
- ElevenLabs voice (Carol persona)
- Claude as LLM with the Carbon system prompt
- Custom tools (lookup_order, lookup_tracking, lookup_troque, create_ticket)
- Server URL pointing to our webhook

```python
"""Setup Vapi assistant for Carbon Voice AI (Carol).

Usage: python -m scripts.setup_vapi_assistant
Requires VAPI_API_KEY in .env
"""
import os
import sys
import json
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.core.config import settings

VAPI_BASE = "https://api.vapi.ai"

SYSTEM_PROMPT = """Voce eh a Carol, assistente virtual da Carbon por telefone.
A Carbon eh uma marca brasileira de smartwatches e acessorios.

REGRAS:
- Fale de forma casual e direta, como amiga ajudando. Use "voce", nao "senhor/senhora".
- Respostas curtas e objetivas (maximo 3 frases por vez). Lembre: eh voz, nao texto.
- NUNCA invente informacoes. Se nao sabe, diga que vai abrir um chamado.
- NUNCA mencione importacao, China, alfandega.
- NUNCA sugira Procon, Reclame Aqui, advogado.
- Sempre diga apenas "Carbon", nunca "Carbon Smartwatch".

REGRAS DE NEGOCIO:
- Modelos: Carbon Raptor, Atlas, One Max, Aurora, Quartz
- Garantia: legal 90 dias + contratual 12 meses. Carbon Care estende pra 24 meses.
- NAO temos assistencia tecnica. Dentro da garantia: troca por novo. Fora: cupom de desconto.
- Portal trocas: carbonsmartwatch.troque.app.br
- Apps: Raptor/Atlas = GloryFitPro. One Max/Aurora = DaFit.
- Cancelamento antes de enviar: ok. Depois: recusar entrega ou devolver em 7 dias.
- Estorno: ate 10 dias uteis. Pix direto. Cartao ate 3 faturas.

PRAZOS DE ENTREGA:
- Sudeste: 7 a 12 dias uteis
- Sul: 7 a 14 dias uteis
- Centro-Oeste: 8 a 16 dias uteis
- Nordeste: 10 a 20 dias uteis
- Norte: 12 a 25 dias uteis

FLUXO DA LIGACAO:
1. Cumprimente: "Fala! Bem-vindo a Carbon, aqui eh a Carol. Como posso te ajudar?"
2. Identifique o que o cliente precisa
3. Use as ferramentas disponiveis pra consultar pedido, rastreio ou Troque
4. Se nao conseguir resolver, abra um chamado com create_ticket e informe que retornam por email

ESCALAR (usar create_ticket) quando:
- Procon, advogado, processo, Reclame Aqui, chargeback
- Reembolso/cancelamento
- Problema tecnico que reset nao resolveu
- Cliente irritado
- Qualquer coisa que nao sabe"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Consulta um pedido no Shopify pelo numero do pedido. Use quando o cliente quer saber status do pedido.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {
                        "type": "string",
                        "description": "Numero do pedido (ex: 126338)"
                    }
                },
                "required": ["order_number"]
            }
        },
        "server": {"url": "WILL_BE_SET"}
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_tracking",
            "description": "Consulta rastreio de envio pelo codigo de rastreamento. Use quando o cliente tem um codigo de rastreio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_code": {
                        "type": "string",
                        "description": "Codigo de rastreio (ex: NL247033946BR)"
                    }
                },
                "required": ["tracking_code"]
            }
        },
        "server": {"url": "WILL_BE_SET"}
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_troque",
            "description": "Consulta status de troca/devolucao no TroqueCommerce. Use quando o cliente pergunta sobre garantia, troca ou devolucao.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {
                        "type": "string",
                        "description": "Numero do pedido original"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Telefone do cliente se nao souber o pedido"
                    }
                },
                "required": []
            }
        },
        "server": {"url": "WILL_BE_SET"}
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Cria um chamado no helpdesk quando nao conseguir resolver o problema do cliente. Informe que retornarao por email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Resumo do problema em poucas palavras"
                    },
                    "description": {
                        "type": "string",
                        "description": "Descricao detalhada do que o cliente relatou"
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Nome do cliente se informado"
                    },
                    "caller_phone": {
                        "type": "string",
                        "description": "Telefone de quem ligou"
                    }
                },
                "required": ["subject", "description"]
            }
        },
        "server": {"url": "WILL_BE_SET"}
    }
]


def create_assistant():
    """Create or update Vapi assistant."""
    if not settings.VAPI_API_KEY:
        print("ERROR: VAPI_API_KEY not set in .env")
        sys.exit(1)

    server_url = input("Enter your server webhook URL (e.g. https://helpdesk.brutodeverdade.com.br/api/webhooks/vapi): ").strip()

    # Set server URL on all tools
    for tool in TOOLS:
        tool["server"]["url"] = server_url

    headers = {
        "Authorization": f"Bearer {settings.VAPI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "name": "Carol - Carbon Voice AI",
        "model": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "XB0fDUnXU5powFXDhCwa",  # Charlotte - natural female
            "stability": 0.6,
            "similarityBoost": 0.8,
        },
        "firstMessage": "Fala! Bem-vindo a Carbon, aqui eh a Carol. Como posso te ajudar?",
        "serverUrl": server_url,
        "serverUrlSecret": settings.VAPI_SERVER_SECRET,
        "endCallMessage": "Foi bom falar com voce! Se precisar de mais alguma coisa, eh so ligar de novo. Tchau!",
        "tools": TOOLS,
        "silenceTimeoutSeconds": 30,
        "maxDurationSeconds": 600,  # 10 min max
        "backgroundSound": "off",
        "language": "pt-BR",
    }

    resp = requests.post(f"{VAPI_BASE}/assistant", headers=headers, json=payload)
    if resp.status_code in (200, 201):
        assistant = resp.json()
        print(f"\nAssistant created! ID: {assistant['id']}")
        print(f"Name: {assistant['name']}")
        print(f"\nNext steps:")
        print(f"1. Go to Vapi dashboard and buy a Twilio phone number")
        print(f"2. Link the phone number to this assistant")
        print(f"3. Add VAPI_ASSISTANT_ID={assistant['id']} to your .env")
        return assistant
    else:
        print(f"ERROR: {resp.status_code} - {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    create_assistant()
```

**Step 2: Commit**

```bash
git add backend/scripts/setup_vapi_assistant.py
git commit -m "feat(voice): add Vapi assistant setup script with Carol persona"
```

---

## Task 6: Frontend — VoiceCallPlayer component

**Files:**
- Create: `frontend/src/components/tickets/VoiceCallPlayer.jsx`

**Step 1: Create the component**

```jsx
import { useState } from 'react';

export default function VoiceCallPlayer({ voiceCall }) {
  const [showTranscript, setShowTranscript] = useState(false);

  if (!voiceCall) return null;

  const duration = voiceCall.duration_seconds
    ? `${Math.floor(voiceCall.duration_seconds / 60)}:${String(Math.floor(voiceCall.duration_seconds % 60)).padStart(2, '0')}`
    : '--:--';

  return (
    <div style={{
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      padding: '12px',
      marginBottom: '12px',
      backgroundColor: '#f8fafc',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span style={{ fontSize: '18px' }}>📞</span>
        <strong>Ligacao telefonica</strong>
        <span style={{ color: '#64748b', fontSize: '13px' }}>
          {duration} &middot; {new Date(voiceCall.created_at).toLocaleString('pt-BR')}
        </span>
      </div>

      {voiceCall.recording_url && (
        <audio controls style={{ width: '100%', marginBottom: '8px' }}>
          <source src={voiceCall.recording_url} />
        </audio>
      )}

      {voiceCall.summary && (
        <p style={{ margin: '4px 0 8px', color: '#475569', fontSize: '14px' }}>
          <strong>Resumo:</strong> {voiceCall.summary}
        </p>
      )}

      {voiceCall.transcript && (
        <>
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            style={{
              background: 'none',
              border: '1px solid #cbd5e1',
              borderRadius: '4px',
              padding: '4px 12px',
              cursor: 'pointer',
              fontSize: '13px',
              color: '#475569',
            }}
          >
            {showTranscript ? 'Ocultar transcricao' : 'Ver transcricao'}
          </button>
          {showTranscript && (
            <pre style={{
              marginTop: '8px',
              padding: '10px',
              backgroundColor: '#fff',
              border: '1px solid #e2e8f0',
              borderRadius: '4px',
              fontSize: '13px',
              whiteSpace: 'pre-wrap',
              maxHeight: '300px',
              overflow: 'auto',
            }}>
              {voiceCall.transcript}
            </pre>
          )}
        </>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/tickets/VoiceCallPlayer.jsx
git commit -m "feat(voice): add VoiceCallPlayer component with audio + transcript"
```

---

## Task 7: Frontend — Integrate VoiceCallPlayer in ticket view

**Files:**
- Modify: `frontend/src/components/chat/ChatView.jsx` (or equivalent ticket detail view)

**Step 1: Add API call to fetch voice calls for a ticket**

Add a fetch for voice calls when viewing a ticket. The backend endpoint needs to be created too.

**Step 2: Add API endpoint for voice calls**

Add to `backend/app/api/tickets.py`:

```python
@router.get("/{ticket_id}/voice-calls")
async def get_voice_calls(ticket_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.voice_call import VoiceCall
    result = await db.execute(
        select(VoiceCall).where(VoiceCall.ticket_id == ticket_id).order_by(VoiceCall.created_at.desc())
    )
    calls = result.scalars().all()
    return [
        {
            "id": c.id,
            "vapi_call_id": c.vapi_call_id,
            "caller_phone": c.caller_phone,
            "duration_seconds": c.duration_seconds,
            "recording_url": c.recording_url,
            "transcript": c.transcript,
            "summary": c.summary,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in calls
    ]
```

**Step 3: Render VoiceCallPlayer in ticket/chat view**

In the ticket detail component, fetch and render:

```jsx
import VoiceCallPlayer from '../tickets/VoiceCallPlayer';

// In the component, after loading ticket:
const [voiceCalls, setVoiceCalls] = useState([]);
useEffect(() => {
  if (ticket?.id) {
    fetch(`/api/tickets/${ticket.id}/voice-calls`, { headers: authHeaders })
      .then(r => r.json())
      .then(setVoiceCalls)
      .catch(() => {});
  }
}, [ticket?.id]);

// In the render, above the message thread:
{voiceCalls.map(vc => <VoiceCallPlayer key={vc.id} voiceCall={vc} />)}
```

**Step 4: Commit**

```bash
git add backend/app/api/tickets.py frontend/src/components/chat/ChatView.jsx frontend/src/components/tickets/VoiceCallPlayer.jsx
git commit -m "feat(voice): integrate voice calls in ticket view with player + transcript"
```

---

## Task 8: Add "phone" source indicator in ticket list

**Files:**
- Modify: `frontend/src/components/chat/ChatList.jsx` (or ticket list component)

**Step 1: Add phone icon for tickets with source="phone"**

Wherever the source icon is rendered (WhatsApp, Instagram, etc.), add:

```jsx
{ticket.source === 'phone' && <span title="Ligacao">📞</span>}
```

**Step 2: Commit**

```bash
git add frontend/src/components/chat/ChatList.jsx
git commit -m "feat(voice): add phone icon in ticket list for voice call tickets"
```

---

## Task 9: Setup external services (manual)

These steps are done manually, not coded:

**Step 1: Create Vapi account**
- Go to vapi.ai, create account
- Get API key from dashboard
- Add to .env: `VAPI_API_KEY=...`

**Step 2: Run setup script**
```bash
cd backend
python -m scripts.setup_vapi_assistant
```
- Enter server URL: `https://helpdesk.brutodeverdade.com.br/api/webhooks/vapi`

**Step 3: Buy Twilio phone number through Vapi**
- In Vapi dashboard, go to Phone Numbers
- Buy a fixed SP (11) number
- Link to the Carol assistant

**Step 4: Configure ElevenLabs**
- In Vapi dashboard, add ElevenLabs API key
- Select voice (Charlotte or clone a custom voice)

**Step 5: Test**
- Call the number
- Verify Carol answers
- Test: "Quero rastrear meu pedido 126338"
- Check that end-of-call recording appears in helpdesk

---

## Task 10: Deploy

**Step 1: Deploy backend**
```bash
sshpass -p 'OdysseY144.-a' rsync -avz --exclude='__pycache__' --exclude='.env' backend/ root@143.198.20.6:/root/carbon-helpdesk/backend/
ssh root@143.198.20.6 "cd /root/carbon-helpdesk && docker compose -f docker-compose.prod.yml build --no-cache backend && docker compose -f docker-compose.prod.yml up -d"
```

**Step 2: Run migration on server**
```bash
ssh root@143.198.20.6 "cd /root/carbon-helpdesk && docker compose exec backend alembic upgrade head"
```

**Step 3: Deploy frontend (build on server)**
```bash
sshpass -p 'OdysseY144.-a' rsync -avz --exclude='node_modules' frontend/src/ root@143.198.20.6:/root/carbon-helpdesk/frontend/src/
ssh root@143.198.20.6 "cd /root/carbon-helpdesk && docker compose -f docker-compose.prod.yml build --no-cache frontend && docker compose -f docker-compose.prod.yml up -d"
```

**Step 4: Add .env vars on server**
```bash
ssh root@143.198.20.6 "cd /root/carbon-helpdesk/backend && echo 'VAPI_API_KEY=...' >> .env && echo 'VAPI_SERVER_SECRET=...' >> .env"
```

**Step 5: Commit all remaining changes**
```bash
git add -A
git commit -m "feat(voice): Carbon Voice AI Carol — complete implementation"
```
