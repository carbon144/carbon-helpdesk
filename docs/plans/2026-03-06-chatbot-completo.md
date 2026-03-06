# Chatbot Completo Carbon Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar chatbot completo em 3 camadas (chatbot flows -> IA Claude -> agente humano) nos canais WhatsApp, Instagram e Facebook, resolvendo automaticamente ~50% dos tickets (rastreio, duvidas, suporte tecnico).

**Architecture:** Engine multi-step com state tracking por conversa (metadata_ JSONB no Conversation). Flows executam steps sequenciais com capacidade de pausar (wait_response) e retomar. Shopify lookup real via shopify_service.py existente. Mensagens interativas (WA buttons/list, IG/FB quick replies) via metodos send_interactive nos adapters. Pipeline: chatbot match -> execute flow -> se nao resolver -> IA Claude com KB -> se nao resolver -> escala pra agente humano com dados coletados.

**Tech Stack:** Python/FastAPI (backend existente), PostgreSQL (JSONB para state), Shopify Admin API (existente), WhatsApp Cloud API interactive messages, Meta Send API quick replies, httpx.

---

## Task 1: Fix chatbot engine multi-step (state tracking)

**Files:**
- Modify: `backend/app/services/chatbot_engine.py`
- Modify: `backend/app/models/conversation.py` (usa metadata_ existente)

**Step 1: Rewrite chatbot_engine.py with state tracking**

O engine atual nao retoma flows apos wait_response. Reescrever para usar `conversation.metadata_["chatbot_state"]` como state store.

```python
# backend/app/services/chatbot_engine.py
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chatbot_flow import ChatbotFlow
import logging

logger = logging.getLogger(__name__)


class ChatbotEngine:
    """Engine that processes messages against chatbot flows with multi-step state."""

    async def process_message(
        self,
        db: AsyncSession,
        conversation: object,
        message_text: str,
        visitor_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Process message: resume active flow or match new one.
        Returns action result dict or None if no flow matched."""

        # Check for active flow state in conversation metadata
        meta = getattr(conversation, "metadata_", None) or {}
        chatbot_state = meta.get("chatbot_state")

        if chatbot_state and chatbot_state.get("flow_id"):
            return await self._resume_flow(db, conversation, message_text, chatbot_state)

        # No active flow — try to match a new one
        flow = await self.match_flow(db, message_text)
        if not flow:
            return None

        return await self._execute_flow(db, conversation, flow, message_text, start_step=0)

    async def _execute_flow(
        self,
        db: AsyncSession,
        conversation: object,
        flow: ChatbotFlow,
        message_text: str,
        start_step: int = 0,
        collected_data: Optional[dict] = None,
    ) -> dict:
        """Execute flow steps starting from start_step."""
        steps = flow.steps or []
        responses = []
        collected = collected_data or {}

        i = start_step
        while i < len(steps):
            step = steps[i]
            result = self.execute_step(step, {
                "conversation": conversation,
                "message_text": message_text,
                "collected_data": collected,
            })
            responses.append(result)

            if result.get("type") == "transfer_to_agent":
                self._clear_state(conversation)
                break

            if result.get("type") == "wait_response":
                # Save state — will resume on next message
                self._save_state(conversation, flow.id, i + 1, collected)
                break

            if result.get("type") == "collect_input":
                # Save state expecting input for this field
                collected_field = step.get("field", "input")
                self._save_state(conversation, flow.id, i + 1, collected, expecting_field=collected_field)
                break

            if result.get("type") == "lookup_order":
                # Mark that next step needs order data
                result["needs_async"] = True

            i += 1

        # If we finished all steps, clear state
        if i >= len(steps):
            self._clear_state(conversation)

        return {
            "flow_id": str(flow.id),
            "flow_name": flow.name,
            "responses": responses,
            "matched": True,
            "collected_data": collected,
        }

    async def _resume_flow(
        self,
        db: AsyncSession,
        conversation: object,
        message_text: str,
        state: dict,
    ) -> Optional[dict]:
        """Resume an active flow from saved state."""
        flow = await self._get_flow_by_id(db, state["flow_id"])
        if not flow:
            self._clear_state(conversation)
            return None

        step_index = state.get("step_index", 0)
        collected = state.get("collected_data", {})

        # If we were expecting a field, store the user's response
        expecting = state.get("expecting_field")
        if expecting:
            collected[expecting] = message_text

        return await self._execute_flow(db, conversation, flow, message_text, start_step=step_index, collected_data=collected)

    async def match_flow(
        self,
        db: AsyncSession,
        message_text: str,
        trigger_type: Optional[str] = None,
    ) -> Optional[ChatbotFlow]:
        """Find matching active flow by keyword/trigger. Priority: exact > keyword > greeting > any."""
        query = select(ChatbotFlow).where(ChatbotFlow.active.is_(True))
        if trigger_type:
            query = query.where(ChatbotFlow.trigger_type == trigger_type)

        result = await db.execute(query)
        flows = list(result.scalars().all())

        text_lower = message_text.lower().strip()

        # Sort by priority: exact first, then keyword, greeting, any last
        priority = {"exact": 0, "keyword": 1, "greeting": 2, "any": 3}
        flows.sort(key=lambda f: priority.get(f.trigger_type, 99))

        for flow in flows:
            if flow.trigger_type == "exact":
                exact = (flow.trigger_config or {}).get("text", "")
                if exact.lower() == text_lower:
                    return flow
            elif flow.trigger_type == "keyword":
                keywords = (flow.trigger_config or {}).get("keywords", [])
                for kw in keywords:
                    if kw.lower() in text_lower:
                        return flow
            elif flow.trigger_type == "greeting":
                greetings = ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
                             "hello", "hi", "hey", "e ai", "eai", "opa", "fala"]
                if text_lower in greetings:
                    return flow
            elif flow.trigger_type == "any":
                return flow

        return None

    def execute_step(self, step: dict, context: dict) -> dict:
        """Execute a single flow step and return result."""
        step_type = step.get("type", "send_message")

        if step_type == "send_message":
            content = step.get("content", "")
            # Template variable substitution
            collected = context.get("collected_data", {})
            for key, val in collected.items():
                content = content.replace(f"{{{{{key}}}}}", str(val))
            return {"type": "send_message", "content": content}

        elif step_type == "send_menu":
            return {
                "type": "send_menu",
                "content": step.get("content", ""),
                "options": step.get("options", []),
            }

        elif step_type == "collect_input":
            return {
                "type": "collect_input",
                "content": step.get("content", ""),
                "field": step.get("field", "input"),
            }

        elif step_type == "lookup_order":
            return {
                "type": "lookup_order",
                "field": step.get("field", "order_number"),
                "content": step.get("content", "Buscando seu pedido..."),
            }

        elif step_type == "transfer_to_agent":
            return {
                "type": "transfer_to_agent",
                "content": step.get("content", "Transferindo para um atendente..."),
                "collected_data": context.get("collected_data", {}),
            }

        elif step_type == "wait_response":
            return {
                "type": "wait_response",
                "content": step.get("content", ""),
            }

        elif step_type == "condition":
            return {
                "type": "condition",
                "field": step.get("field", ""),
                "branches": step.get("branches", {}),
            }

        return {"type": "unknown", "step": step}

    def _save_state(self, conversation, flow_id, step_index, collected_data, expecting_field=None):
        """Save chatbot state to conversation metadata."""
        meta = getattr(conversation, "metadata_", None) or {}
        meta["chatbot_state"] = {
            "flow_id": str(flow_id),
            "step_index": step_index,
            "collected_data": collected_data,
            "expecting_field": expecting_field,
        }
        conversation.metadata_ = meta

    def _clear_state(self, conversation):
        """Clear chatbot state from conversation metadata."""
        meta = getattr(conversation, "metadata_", None) or {}
        meta.pop("chatbot_state", None)
        conversation.metadata_ = meta

    async def _get_flow_by_id(self, db: AsyncSession, flow_id: str) -> Optional[ChatbotFlow]:
        result = await db.execute(select(ChatbotFlow).where(ChatbotFlow.id == flow_id))
        return result.scalar_one_or_none()


# CRUD helpers (unchanged)

async def list_flows(db: AsyncSession) -> list[ChatbotFlow]:
    result = await db.execute(select(ChatbotFlow).order_by(ChatbotFlow.created_at.desc()))
    return list(result.scalars().all())


async def get_flow(db: AsyncSession, flow_id: str) -> Optional[ChatbotFlow]:
    result = await db.execute(select(ChatbotFlow).where(ChatbotFlow.id == flow_id))
    return result.scalar_one_or_none()


async def create_flow(db: AsyncSession, data: dict) -> ChatbotFlow:
    flow = ChatbotFlow(**data)
    db.add(flow)
    await db.commit()
    await db.refresh(flow)
    return flow


async def update_flow(db: AsyncSession, flow_id: str, data: dict) -> Optional[ChatbotFlow]:
    flow = await get_flow(db, flow_id)
    if not flow:
        return None
    for key, value in data.items():
        setattr(flow, key, value)
    await db.commit()
    await db.refresh(flow)
    return flow


async def delete_flow(db: AsyncSession, flow_id: str) -> bool:
    flow = await get_flow(db, flow_id)
    if not flow:
        return False
    await db.delete(flow)
    await db.commit()
    return True
```

**Step 2: Verify no syntax errors**

Run: `cd /Users/pedrocastro/Desktop/carbon-helpdesk/backend && python -c "from app.services.chatbot_engine import ChatbotEngine; print('OK')"`

**Step 3: Commit**

```bash
git add backend/app/services/chatbot_engine.py
git commit -m "feat(chatbot): rewrite engine with multi-step state tracking

State persisted in conversation.metadata_ JSONB. Supports collect_input,
wait_response with resume, send_menu, template variables, flow priority."
```

---

## Task 2: Upgrade message_pipeline.py with Shopify lookup + interactive dispatch

**Files:**
- Modify: `backend/app/services/message_pipeline.py`

**Step 1: Rewrite pipeline to handle new step types**

```python
# backend/app/services/message_pipeline.py
"""Message pipeline orchestrator — Chatbot -> AI -> Human handoff."""

import logging
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.chat_message import ChatMessage
from app.models.kb_article import KBArticle
from app.services.chatbot_engine import ChatbotEngine
from app.services import ai_service
from app.services import chat_routing_service as routing_service

logger = logging.getLogger(__name__)

MAX_AI_ATTEMPTS = 3

_chatbot_engine = ChatbotEngine()


async def _search_kb(db: AsyncSession, query: str, limit: int = 3) -> list[KBArticle]:
    pattern = f"%{query}%"
    result = await db.execute(
        select(KBArticle)
        .where(
            KBArticle.is_published.is_(True),
            or_(KBArticle.title.ilike(pattern), KBArticle.content.ilike(pattern)),
        )
        .order_by(KBArticle.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def process_incoming_message(
    db: AsyncSession,
    conversation: Conversation,
    customer: Customer,
    message_text: str,
    visitor_id: str | None = None,
) -> dict:
    result = {"handler": conversation.handler or "chatbot", "bot_messages": [], "interactive_messages": [], "escalated": False}

    # Layer 0: If agent is in control and AI is off, skip everything
    if conversation.handler == "agent" and not conversation.ai_enabled:
        return result

    # Layer 1: Chatbot flows
    if conversation.handler in ("chatbot", None):
        chatbot_result = await _chatbot_engine.process_message(
            db, conversation, message_text, visitor_id=visitor_id,
        )

        if chatbot_result and chatbot_result.get("matched"):
            responses = chatbot_result.get("responses", [])
            collected = chatbot_result.get("collected_data", {})

            for resp in responses:
                resp_type = resp.get("type")

                if resp_type == "transfer_to_agent":
                    # Attach collected data to conversation for agent context
                    meta = conversation.metadata_ or {}
                    meta["collected_by_bot"] = resp.get("collected_data", collected)
                    conversation.metadata_ = meta
                    return await _escalate_to_agent(
                        db, conversation, result,
                        escalation_message=resp.get("content", "Transferindo para um atendente..."),
                    )

                elif resp_type == "send_message":
                    content = resp.get("content", "")
                    if content:
                        result["bot_messages"].append(content)
                        await _save_bot_message(db, conversation, content)

                elif resp_type == "send_menu":
                    content = resp.get("content", "")
                    options = resp.get("options", [])
                    result["interactive_messages"].append({
                        "type": "menu",
                        "content": content,
                        "options": options,
                    })
                    await _save_bot_message(db, conversation, content)

                elif resp_type == "collect_input":
                    content = resp.get("content", "")
                    if content:
                        result["bot_messages"].append(content)
                        await _save_bot_message(db, conversation, content)

                elif resp_type == "wait_response":
                    content = resp.get("content", "")
                    if content:
                        result["bot_messages"].append(content)
                        await _save_bot_message(db, conversation, content)

                elif resp_type == "lookup_order":
                    order_result = await _handle_order_lookup(
                        db, conversation, collected, resp.get("field", "order_number"),
                    )
                    if order_result:
                        for msg in order_result.get("messages", []):
                            result["bot_messages"].append(msg)
                            await _save_bot_message(db, conversation, msg)
                        if order_result.get("interactive"):
                            result["interactive_messages"].append(order_result["interactive"])

            if result["bot_messages"] or result["interactive_messages"]:
                result["handler"] = "chatbot"
                await db.commit()
                return result

        # No chatbot match — fall through to AI
        conversation.handler = "ai"

    # Layer 2: AI auto-reply
    if conversation.handler == "ai" and conversation.ai_enabled:
        kb_articles = []
        try:
            articles = await _search_kb(db, message_text, limit=3)
            kb_articles = [{"title": a.title, "content": a.content} for a in articles]
        except Exception:
            logger.warning("KB search failed, continuing without KB context")

        messages_history = await _build_history(db, conversation)
        messages_history.append({"role": "contact", "content": message_text})

        shopify_data = getattr(customer, "shopify_data", None)

        ai_result = await ai_service.chat_auto_reply(
            messages=messages_history,
            contact_shopify_data=shopify_data,
            kb_articles=kb_articles if kb_articles else None,
        )

        if ai_result["resolved"]:
            conversation.ai_attempts = 0
            result["handler"] = "ai"
            result["bot_messages"].append(ai_result["response"])
            await _save_bot_message(db, conversation, ai_result["response"])
            await db.commit()
            return result
        else:
            conversation.ai_attempts = (conversation.ai_attempts or 0) + 1
            await db.commit()

            if conversation.ai_attempts >= MAX_AI_ATTEMPTS:
                return await _escalate_to_agent(db, conversation, result)
            else:
                if ai_result["response"]:
                    result["handler"] = "ai"
                    result["bot_messages"].append(ai_result["response"])
                    await _save_bot_message(db, conversation, ai_result["response"])
                await db.commit()
                return result

    return result


async def _handle_order_lookup(
    db: AsyncSession,
    conversation: Conversation,
    collected_data: dict,
    field: str,
) -> dict | None:
    """Lookup order in Shopify and return formatted messages."""
    from app.services.shopify_service import get_order_by_number, get_orders_by_email

    order_input = collected_data.get(field, "").strip()
    if not order_input:
        return {"messages": ["Nao consegui identificar o numero do pedido. Pode informar novamente?"]}

    # Try by order number first
    order = await get_order_by_number(order_input)

    if order.get("error"):
        # Try as email
        if "@" in order_input:
            email_result = await get_orders_by_email(order_input, limit=3)
            if email_result.get("orders"):
                return _format_orders_list(email_result["orders"])
        return {"messages": [f"Nao encontrei o pedido '{order_input}'. Verifique o numero e tente novamente (ex: 129370)."]}

    return _format_order_detail(order)


def _format_order_detail(order: dict) -> dict:
    """Format a single order into chat messages."""
    status_map = {
        "pending": "Pendente",
        "shipped": "Enviado",
        "in_transit": "Em transito",
        "out_for_delivery": "Saiu para entrega",
        "delivered": "Entregue",
        "failed": "Falha na entrega",
    }
    financial_map = {
        "paid": "Pago",
        "pending": "Pendente",
        "refunded": "Reembolsado",
        "partially_refunded": "Parcialmente reembolsado",
        "voided": "Cancelado",
    }

    number = order.get("order_number", "?")
    delivery = status_map.get(order.get("delivery_status", ""), order.get("delivery_status", "Desconhecido"))
    financial = financial_map.get(order.get("financial_status", ""), order.get("financial_status", ""))
    tracking = order.get("tracking_code", "")
    carrier = order.get("carrier", "")
    items = order.get("items", [])
    total = order.get("total_price", "0")

    items_text = "\n".join(f"  - {it['title']} (x{it['quantity']})" for it in items[:5])

    msg = f"Pedido {number}\n"
    msg += f"Status: {delivery}\n"
    msg += f"Pagamento: {financial}\n"
    msg += f"Total: R$ {total}\n"
    if items_text:
        msg += f"Itens:\n{items_text}\n"
    if tracking:
        msg += f"Rastreio: {tracking}"
        if carrier:
            msg += f" ({carrier})"
        msg += "\n"

    messages = [msg.strip()]

    if order.get("delivery_status") in ("shipped", "in_transit", "out_for_delivery") and tracking:
        messages.append(f"Acompanhe seu envio: https://rastreamento.correios.com.br/app/index.php")

    return {"messages": messages}


def _format_orders_list(orders: list[dict]) -> dict:
    """Format multiple orders into a summary."""
    lines = ["Encontrei seus pedidos recentes:\n"]
    for o in orders[:5]:
        number = o.get("order_number", "?")
        status = o.get("delivery_status", "?")
        total = o.get("total_price", "0")
        lines.append(f"  {number} — R$ {total} — {status}")

    lines.append("\nInforme o numero do pedido para mais detalhes.")
    return {"messages": ["\n".join(lines)]}


async def _escalate_to_agent(
    db: AsyncSession,
    conversation: Conversation,
    result: dict,
    escalation_message: str = "Vou transferir voce para um de nossos atendentes. Um momento, por favor.",
) -> dict:
    conversation.handler = "agent"
    conversation.ai_enabled = False
    conversation.ai_attempts = 0

    await routing_service.auto_assign(db, conversation)

    system_msg = ChatMessage(
        conversation_id=conversation.id,
        sender_type="system",
        sender_id=None,
        content_type="text",
        content="Conversa transferida para atendimento humano.",
    )
    db.add(system_msg)

    result["bot_messages"].append(escalation_message)
    await _save_bot_message(db, conversation, escalation_message)

    await db.commit()

    result["handler"] = "agent"
    result["escalated"] = True
    return result


async def _save_bot_message(db: AsyncSession, conversation: Conversation, content: str):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    msg = ChatMessage(
        conversation_id=conversation.id,
        sender_type="bot",
        sender_id=None,
        content_type="text",
        content=content,
        created_at=now,
    )
    db.add(msg)
    conversation.last_message_at = now


async def _build_history(db: AsyncSession, conversation: Conversation) -> list[dict]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id, ChatMessage.content_type != "note")
        .order_by(ChatMessage.created_at.asc())
        .limit(20)
    )
    history = []
    for msg in result.scalars().all():
        role = "contact" if msg.sender_type == "contact" else "agent"
        history.append({"role": role, "content": msg.content})
    return history
```

**Step 2: Verify import**

Run: `cd /Users/pedrocastro/Desktop/carbon-helpdesk/backend && python -c "from app.services.message_pipeline import process_incoming_message; print('OK')"`

**Step 3: Commit**

```bash
git add backend/app/services/message_pipeline.py
git commit -m "feat(pipeline): add Shopify order lookup + interactive message support

Handles lookup_order with real Shopify API, send_menu for interactive
messages, collect_input for multi-step data collection, and passes
collected data to agent on escalation."
```

---

## Task 3: Add send_interactive to channel adapters

**Files:**
- Modify: `backend/app/services/channels/base.py`
- Modify: `backend/app/services/channels/whatsapp_adapter.py`
- Modify: `backend/app/services/channels/instagram_adapter.py`
- Modify: `backend/app/services/channels/facebook_adapter.py`
- Modify: `backend/app/services/channels/dispatcher.py`

**Step 1: Add send_interactive to base + dispatcher**

In `base.py`, add default method (not abstract, so existing adapters don't break):

```python
# Add to ChannelAdapter class in base.py after send_media:
    async def send_interactive(
        self,
        recipient_id: str,
        body_text: str,
        options: list[dict],
        header: str | None = None,
        footer: str | None = None,
    ) -> dict | None:
        """Send interactive message (buttons/quick replies). Default: fallback to text."""
        # Build text fallback with numbered options
        lines = [body_text, ""]
        for i, opt in enumerate(options, 1):
            lines.append(f"{i}. {opt.get('label', opt.get('title', ''))}")
        return await self.send_message(recipient_id, "\n".join(lines))
```

In `dispatcher.py`, add:

```python
# Add to ChannelDispatcher class:
    async def send_interactive(
        self,
        channel: str,
        recipient_id: str,
        body_text: str,
        options: list[dict],
        header: str | None = None,
        footer: str | None = None,
    ) -> dict | None:
        adapter = self.adapters.get(channel)
        if adapter:
            return await adapter.send_interactive(recipient_id, body_text, options, header, footer)
        logger.warning("No adapter registered for channel: %s", channel)
        return None
```

**Step 2: WhatsApp interactive buttons/list**

Add to `whatsapp_adapter.py`:

```python
    async def send_interactive(
        self,
        recipient_id: str,
        body_text: str,
        options: list[dict],
        header: str | None = None,
        footer: str | None = None,
    ) -> dict | None:
        """Send WhatsApp interactive message (buttons if <=3 options, list if more)."""
        url = f"{GRAPH_API_BASE}/{settings.META_WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        interactive: dict = {"body": {"text": body_text}}
        if header:
            interactive["header"] = {"type": "text", "text": header}
        if footer:
            interactive["footer"] = {"text": footer}

        if len(options) <= 3:
            # Reply buttons (max 3)
            interactive["type"] = "button"
            interactive["action"] = {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": opt.get("id", f"opt_{i}"),
                            "title": opt.get("label", opt.get("title", ""))[:20],
                        },
                    }
                    for i, opt in enumerate(options)
                ],
            }
        else:
            # List message (max 10)
            interactive["type"] = "list"
            interactive["action"] = {
                "button": "Ver opcoes",
                "sections": [
                    {
                        "title": "Opcoes",
                        "rows": [
                            {
                                "id": opt.get("id", f"opt_{i}"),
                                "title": opt.get("label", opt.get("title", ""))[:24],
                                "description": opt.get("description", "")[:72],
                            }
                            for i, opt in enumerate(options[:10])
                        ],
                    }
                ],
            }

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "interactive",
            "interactive": interactive,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("WhatsApp interactive sent to %s (%d options)", recipient_id, len(options))
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send WhatsApp interactive to %s: %s", recipient_id, e)
            # Fallback to text
            return await super().send_interactive(recipient_id, body_text, options, header, footer)
```

Also add to `_parse_message` in whatsapp_adapter.py to handle interactive replies:

```python
        # Add after the location elif block:
        elif msg_type == "interactive":
            interactive = msg.get("interactive", {})
            itype = interactive.get("type", "")
            if itype == "button_reply":
                reply = interactive.get("button_reply", {})
                return {
                    "sender_id": sender_id,
                    "content": reply.get("title", ""),
                    "content_type": "text",
                    "channel_message_id": channel_message_id,
                    "timestamp": timestamp,
                    "interactive_id": reply.get("id", ""),
                }
            elif itype == "list_reply":
                reply = interactive.get("list_reply", {})
                return {
                    "sender_id": sender_id,
                    "content": reply.get("title", ""),
                    "content_type": "text",
                    "channel_message_id": channel_message_id,
                    "timestamp": timestamp,
                    "interactive_id": reply.get("id", ""),
                }
```

**Step 3: Instagram/Facebook quick replies**

IG and FB use the same format. Add to both `instagram_adapter.py` and `facebook_adapter.py`:

```python
    async def send_interactive(
        self,
        recipient_id: str,
        body_text: str,
        options: list[dict],
        header: str | None = None,
        footer: str | None = None,
    ) -> dict | None:
        """Send quick replies (max 13 for FB, 13 for IG)."""
        url = f"{GRAPH_API_BASE}/{settings.META_PAGE_ID}/messages" if self.channel_name == "instagram" else f"{GRAPH_API_BASE}/me/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_PAGE_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        quick_replies = [
            {
                "content_type": "text",
                "title": opt.get("label", opt.get("title", ""))[:20],
                "payload": opt.get("id", f"opt_{i}"),
            }
            for i, opt in enumerate(options[:13])
        ]

        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {
                "text": body_text,
                "quick_replies": quick_replies,
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                logger.info("%s quick replies sent to %s", self.channel_name, recipient_id)
                return data
        except httpx.HTTPError as e:
            logger.error("Failed to send %s quick replies to %s: %s", self.channel_name, recipient_id, e)
            return await super().send_interactive(recipient_id, body_text, options, header, footer)
```

**Step 4: Commit**

```bash
git add backend/app/services/channels/
git commit -m "feat(channels): add send_interactive for WA buttons/list and IG/FB quick replies

WhatsApp: reply buttons (<=3) or list message (>3). IG/FB: quick replies.
All with text fallback. WA parser handles interactive replies."
```

---

## Task 4: Wire interactive messages in webhooks

**Files:**
- Modify: `backend/app/api/webhooks/meta_dm.py` (2 places where pipeline result is processed)
- Modify: `backend/app/api/webhooks/whatsapp.py` (1 place)
- Modify: `backend/app/api/ws.py` (widget websocket)

**Step 1: Add interactive dispatch after pipeline**

In all 3 webhook files, after the existing `for bot_msg in pr["bot_messages"]` loop, add:

```python
                    for im in pr.get("interactive_messages", []):
                        if im.get("type") == "menu":
                            await dispatcher.send_interactive(
                                channel, sender_id, im["content"], im["options"],
                            )
```

The pattern is the same in meta_dm.py (2 places: `_process_whatsapp_message` and `_process_meta_message`), whatsapp.py (1 place), and ws.py (visitor websocket handler).

**Step 2: Commit**

```bash
git add backend/app/api/webhooks/ backend/app/api/ws.py
git commit -m "feat(webhooks): dispatch interactive messages from pipeline results

All channels now send menu/button messages when chatbot returns send_menu steps."
```

---

## Task 5: Create the 7 chatbot flows (seed script)

**Files:**
- Create: `backend/seed_chatbot_flows.py`

**Step 1: Write seed script with all 7 flows**

```python
# backend/seed_chatbot_flows.py
"""Seed chatbot flows for Carbon helpdesk."""
import asyncio
import sys
sys.path.insert(0, ".")

from app.core.database import async_engine, AsyncSessionLocal
from app.models.chatbot_flow import ChatbotFlow


FLOWS = [
    {
        "name": "Saudacao + Menu Principal",
        "trigger_type": "greeting",
        "trigger_config": {},
        "active": True,
        "steps": [
            {
                "type": "send_message",
                "content": "Ola! Bem-vindo a Carbon, sua marca de smartwatches. Sou o assistente virtual e vou te ajudar!",
            },
            {
                "type": "send_menu",
                "content": "Como posso te ajudar?",
                "options": [
                    {"id": "rastreio", "label": "Rastrear pedido", "description": "Ver status e rastreio do seu pedido"},
                    {"id": "garantia", "label": "Garantia / Defeito", "description": "Problemas com seu relogio"},
                    {"id": "reenvio", "label": "Nao recebi meu pedido", "description": "Pedido atrasado ou extraviado"},
                    {"id": "financeiro", "label": "Financeiro", "description": "Pagamento, reembolso, cancelamento"},
                    {"id": "duvida", "label": "Duvida / Outro", "description": "Outras questoes"},
                ],
            },
        ],
    },
    {
        "name": "Rastreio de Pedido",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "rastreio", "rastrear", "rastreamento", "rastreiar",
                "meu pedido", "pedido", "entrega", "chegou", "chegar",
                "onde esta", "onde tá", "cadê", "cade",
                "tracking", "codigo de rastreio", "numero do pedido",
                "encomenda", "transportadora", "correios",
            ],
        },
        "active": True,
        "steps": [
            {
                "type": "collect_input",
                "content": "Claro! Para consultar seu pedido, me informe o numero do pedido (ex: 129370) ou o email usado na compra.",
                "field": "order_number",
            },
            {
                "type": "lookup_order",
                "field": "order_number",
                "content": "Buscando seu pedido...",
            },
            {
                "type": "send_message",
                "content": "Precisa de mais alguma coisa? Digite 'menu' para voltar ao menu principal.",
            },
        ],
    },
    {
        "name": "Garantia e Defeito",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "garantia", "defeito", "defeituoso", "quebrou", "quebrado",
                "nao funciona", "parou", "tela", "bateria", "carregador",
                "nao liga", "nao carrega", "travou", "travado", "apagou",
                "esquentando", "superaquecendo", "troca", "trocar",
                "assistencia", "assistência", "autorizada", "reparo", "consertar",
            ],
        },
        "active": True,
        "steps": [
            {
                "type": "send_message",
                "content": "Sentimos muito pelo inconveniente! Vou te ajudar com a garantia do seu Carbon.",
            },
            {
                "type": "collect_input",
                "content": "Qual o modelo do seu relogio? (Ex: Raptor, Atlas, One Max, Aurora, Rover, Explorer, Spark)",
                "field": "modelo",
            },
            {
                "type": "collect_input",
                "content": "Descreva o problema que esta acontecendo:",
                "field": "problema",
            },
            {
                "type": "collect_input",
                "content": "Informe o numero do pedido ou CPF para localizarmos sua compra:",
                "field": "order_number",
            },
            {
                "type": "send_message",
                "content": "Obrigado pelas informacoes! Vou transferir voce para nossa equipe de assistencia tecnica que vai analisar seu caso.",
            },
            {
                "type": "transfer_to_agent",
                "content": "Um momento, estou conectando voce com um especialista...",
            },
        ],
    },
    {
        "name": "Nao Recebi / Reenvio",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "nao recebi", "não recebi", "nao chegou", "não chegou",
                "atrasado", "atraso", "extraviado", "perdido",
                "reenvio", "reenviar", "devolvido", "devolveu",
                "alfandega", "alfândega", "taxado", "taxa",
                "mais de", "faz tempo", "demora",
            ],
        },
        "active": True,
        "steps": [
            {
                "type": "send_message",
                "content": "Entendo sua preocupacao! Vamos verificar o status do seu pedido.",
            },
            {
                "type": "collect_input",
                "content": "Informe o numero do pedido:",
                "field": "order_number",
            },
            {
                "type": "lookup_order",
                "field": "order_number",
                "content": "Consultando seu pedido...",
            },
            {
                "type": "send_message",
                "content": "Se o prazo de entrega ja passou ou o rastreio mostra problema, vou encaminhar para nossa equipe resolver.",
            },
            {
                "type": "transfer_to_agent",
                "content": "Transferindo para um atendente que vai analisar seu caso e providenciar a solucao...",
            },
        ],
    },
    {
        "name": "Financeiro",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "reembolso", "estorno", "dinheiro de volta", "cancelar",
                "cancelamento", "cancela", "pix", "boleto",
                "pagamento", "paguei", "cobrado", "cobranca",
                "nota fiscal", "nf", "comprovante", "recibo",
            ],
        },
        "active": True,
        "steps": [
            {
                "type": "collect_input",
                "content": "Entendi! Para resolver sua questao financeira, informe o numero do pedido:",
                "field": "order_number",
            },
            {
                "type": "lookup_order",
                "field": "order_number",
                "content": "Verificando...",
            },
            {
                "type": "collect_input",
                "content": "Descreva brevemente o que precisa (reembolso, cancelamento, segunda via, etc):",
                "field": "descricao_financeiro",
            },
            {
                "type": "transfer_to_agent",
                "content": "Vou encaminhar para nossa equipe financeira. Um momento...",
            },
        ],
    },
    {
        "name": "Duvida Geral (IA)",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "duvida", "dúvida", "pergunta", "informacao", "informação",
                "quero saber", "como funciona", "como usar", "funcionalidade",
                "preco", "preço", "valor", "parcela", "frete",
                "pulseira", "acessorio", "acessório", "compativel",
                "bluetooth", "app", "aplicativo", "conectar",
                "a prova dagua", "resistente", "mergulhar",
            ],
        },
        "active": True,
        "steps": [
            {
                "type": "send_message",
                "content": "Boa pergunta! Vou consultar nossa base de conhecimento para te responder da melhor forma.",
            },
        ],
        # After this single step, chatbot_engine returns and pipeline falls through to AI layer
    },
    {
        "name": "Fallback (Qualquer Mensagem)",
        "trigger_type": "any",
        "trigger_config": {},
        "active": True,
        "steps": [
            {
                "type": "send_menu",
                "content": "Ola! Sou o assistente virtual da Carbon. Selecione uma opcao ou descreva o que precisa:",
                "options": [
                    {"id": "rastreio", "label": "Rastrear pedido"},
                    {"id": "garantia", "label": "Garantia / Defeito"},
                    {"id": "reenvio", "label": "Nao recebi meu pedido"},
                    {"id": "financeiro", "label": "Financeiro"},
                    {"id": "duvida", "label": "Outra duvida"},
                ],
            },
        ],
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        # Check existing
        from sqlalchemy import select, func
        count = (await db.execute(select(func.count()).select_from(ChatbotFlow))).scalar()
        if count > 0:
            print(f"Ja existem {count} flows. Deletar e recriar? (s/n)")
            resp = input().strip().lower()
            if resp != "s":
                print("Abortado.")
                return
            await db.execute(ChatbotFlow.__table__.delete())
            await db.commit()

        for flow_data in FLOWS:
            flow = ChatbotFlow(**flow_data)
            db.add(flow)
            print(f"  + {flow_data['name']} ({flow_data['trigger_type']})")

        await db.commit()
        print(f"\n{len(FLOWS)} flows criados com sucesso!")


if __name__ == "__main__":
    asyncio.run(seed())
```

**Step 2: Run locally**

Run: `cd /Users/pedrocastro/Desktop/carbon-helpdesk/backend && python seed_chatbot_flows.py`

**Step 3: Commit**

```bash
git add backend/seed_chatbot_flows.py
git commit -m "feat(chatbot): add seed script with 7 flows

Saudacao+menu, Rastreio, Garantia/Defeito, Reenvio, Financeiro,
Duvida (IA fallthrough), Fallback (any). Covers 95% of ticket categories."
```

---

## Task 6: Update frontend ChatbotFlowsPage with new step types

**Files:**
- Modify: `frontend/src/pages/ChatbotFlowsPage.jsx`

**Step 1: Add collect_input and send_menu to STEP_TYPES and StepEditor**

Add to STEP_TYPES:

```javascript
const STEP_TYPES = [
  { value: 'send_message', label: 'Enviar mensagem', icon: 'fa-comment' },
  { value: 'send_menu', label: 'Menu interativo', icon: 'fa-list' },
  { value: 'collect_input', label: 'Coletar dado', icon: 'fa-keyboard' },
  { value: 'wait_response', label: 'Aguardar resposta', icon: 'fa-clock' },
  { value: 'lookup_order', label: 'Buscar pedido', icon: 'fa-search' },
  { value: 'suggest_article', label: 'Sugerir artigo KB', icon: 'fa-book' },
  { value: 'transfer_to_agent', label: 'Transferir p/ agente', icon: 'fa-user' },
]
```

In StepEditor, add cases for `send_menu` and `collect_input`:

- `send_menu`: textarea for content + dynamic options list (each with id, label, description fields)
- `collect_input`: textarea for content + input for field name

**Step 2: Commit**

```bash
git add frontend/src/pages/ChatbotFlowsPage.jsx
git commit -m "feat(frontend): add send_menu and collect_input step types to flow editor

Menu options editor with add/remove, collect_input with field name.
Preview updated for new step types."
```

---

## Task 7: Handle menu selection routing in chatbot engine

**Files:**
- Modify: `backend/app/services/chatbot_engine.py`

**Step 1: Add menu selection matching**

When a user responds to a menu with "rastreio", "1", or "Rastrear pedido", the engine should match the corresponding keyword flow instead of re-matching the fallback. Add to `process_message`:

```python
    # In process_message, before match_flow:
    # Check if this is a menu option selection (numbered or by id/label)
    menu_target = self._resolve_menu_selection(message_text, meta)
    if menu_target:
        # Try to match a flow whose keywords include the target
        flow = await self.match_flow(db, menu_target)
        if flow:
            return await self._execute_flow(db, conversation, flow, menu_target, start_step=0)
```

Add helper:

```python
    def _resolve_menu_selection(self, text: str, meta: dict) -> str | None:
        """Check if text matches a menu option and return the option id."""
        last_menu = (meta or {}).get("last_menu_options")
        if not last_menu:
            return None
        text_lower = text.lower().strip()
        for i, opt in enumerate(last_menu):
            opt_id = opt.get("id", "").lower()
            opt_label = opt.get("label", "").lower()
            # Match by id, label, or number
            if text_lower == opt_id or text_lower == opt_label or text_lower == str(i + 1):
                return opt_id
        return None
```

Also save menu options in metadata when `send_menu` is executed (in `_execute_flow`, after processing a send_menu step):

```python
        # In _execute_flow, inside the while loop after execute_step:
        if result.get("type") == "send_menu":
            meta = getattr(conversation, "metadata_", None) or {}
            meta["last_menu_options"] = result.get("options", [])
            conversation.metadata_ = meta
```

**Step 2: Commit**

```bash
git add backend/app/services/chatbot_engine.py
git commit -m "feat(chatbot): route menu selections to matching flows

Handles numbered replies (1,2,3), option ids (rastreio), and labels.
Saves last menu options in conversation metadata for matching."
```

---

## Task 8: Add 'menu' keyword to trigger menu flow

**Files:**
- Modify: `backend/app/services/chatbot_engine.py`

**Step 1: Handle 'menu' keyword to reset and show menu**

In `process_message`, before checking chatbot_state:

```python
        # Allow user to go back to menu anytime
        if message_text.lower().strip() in ("menu", "voltar", "inicio", "início"):
            self._clear_state(conversation)
            flow = await self.match_flow(db, "oi", trigger_type="greeting")
            if flow:
                return await self._execute_flow(db, conversation, flow, message_text, start_step=0)
```

**Step 2: Commit**

```bash
git add backend/app/services/chatbot_engine.py
git commit -m "feat(chatbot): add menu/voltar/inicio keywords to reset to main menu"
```

---

## Task 9: Deploy to production

**Step 1: Commit all, push, deploy**

```bash
cd /Users/pedrocastro/Desktop/carbon-helpdesk
git add -A
git status
# Verify nothing sensitive

# Rsync to server
sshpass -p 'OdysseY144.-a' rsync -avz --exclude='.git' --exclude='node_modules' --exclude='.venv' --exclude='__pycache__' . root@143.198.20.6:/opt/carbon-helpdesk/

# SSH and rebuild
sshpass -p 'OdysseY144.-a' ssh root@143.198.20.6 "cd /opt/carbon-helpdesk && docker compose -f docker-compose.prod.yml build --no-cache backend frontend && docker compose -f docker-compose.prod.yml up -d"

# Run seed script on prod
sshpass -p 'OdysseY144.-a' ssh root@143.198.20.6 "docker exec carbon-backend python seed_chatbot_flows.py"
```

**Step 2: Verify**

```bash
# Check flows exist
sshpass -p 'OdysseY144.-a' ssh root@143.198.20.6 "docker exec carbon-db psql -U carbon -d carbon_helpdesk -c \"SELECT name, trigger_type, active FROM chatbot_flows;\""

# Check backend logs
sshpass -p 'OdysseY144.-a' ssh root@143.198.20.6 "docker logs carbon-backend --tail 20"
```

**Step 3: Test by sending WhatsApp message "oi" to the Carbon number**

Expected: greeting flow fires, shows welcome + 5-option interactive menu.

---

## Summary of changes

| Task | What | Impact |
|------|------|--------|
| 1 | Engine multi-step rewrite | State persists in conversation.metadata_, supports resume |
| 2 | Pipeline + Shopify lookup | Real order lookup, interactive dispatch, collected data to agent |
| 3 | Channel interactive methods | WA buttons/list, IG/FB quick replies, text fallback |
| 4 | Webhook wiring | Interactive messages dispatched in all channels |
| 5 | 7 flows seed | Saudacao, Rastreio, Garantia, Reenvio, Financeiro, Duvida, Fallback |
| 6 | Frontend new step types | send_menu + collect_input in editor |
| 7 | Menu selection routing | Routes numbered/id/label replies to correct flow |
| 8 | Menu reset keyword | "menu"/"voltar" resets to main menu |
| 9 | Deploy + test | Prod deploy + seed + verify |
