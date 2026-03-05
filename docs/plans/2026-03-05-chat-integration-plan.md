# Chat Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate the Carbon Chat project into the Helpdesk as a separate "Chat ao Vivo" section, sharing Customer, User, and KB.

**Architecture:** New models (Conversation, ChatMessage, ChannelIdentity, ChatbotFlow) added to helpdesk DB alongside existing Ticket/Message. Customer expanded as central entity. Chat services (pipeline, chatbot engine, channel adapters, WS manager) ported from carbon-chat with references adapted (Agent→User, Contact→Customer, KnowledgeArticle→KBArticle). Frontend gets new ChatPage with split panel, added to sidebar.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL, Anthropic Claude SDK, React, Tailwind CSS, WebSocket.

**Source project:** `/Users/pedrocastro/Desktop/carbon-chat`
**Target project:** `/Users/pedrocastro/Desktop/carbon-helpdesk`

---

### Task 1: Expand Customer and User models + migration

**Files:**
- Modify: `backend/app/models/customer.py`
- Modify: `backend/app/models/user.py`
- Create: `backend/alembic/versions/xxx_add_chat_fields.py` (via alembic)

**Step 1: Add fields to Customer model**

In `backend/app/models/customer.py`, add after existing fields:

```python
shopify_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
total_conversations: Mapped[int] = mapped_column(Integer, default=0)
total_value: Mapped[float] = mapped_column(Float, default=0.0)
```

Make `email` nullable: change `email: Mapped[str]` to `email: Mapped[Optional[str]]` and add `nullable=True` to its mapped_column. Keep the unique constraint but make it nullable.

**Step 2: Add fields to User model**

In `backend/app/models/user.py`, add after existing fields:

```python
status: Mapped[str] = mapped_column(String(10), default="offline")
max_concurrent_chats: Mapped[int] = mapped_column(Integer, default=10)
```

**Step 3: Generate Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "add chat fields to customer and user"`

If Alembic is not configured, create migration manually. Check `backend/alembic.ini` and `backend/alembic/env.py`.

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: all existing tests pass

**Step 5: Commit**

```bash
git add backend/app/models/customer.py backend/app/models/user.py backend/alembic/
git commit -m "feat: expand Customer and User models for chat integration"
```

---

### Task 2: Create chat models (Conversation, ChatMessage, ChannelIdentity, ChatbotFlow)

**Files:**
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/chat_message.py`
- Create: `backend/app/models/channel_identity.py`
- Create: `backend/app/models/chatbot_flow.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Create Conversation model**

Create `backend/app/models/conversation.py`:

```python
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    number: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True, nullable=True)
    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("customers.id"), index=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    handler: Mapped[str] = mapped_column(String(10), default="chatbot")
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_attempts: Mapped[int] = mapped_column(Integer, default=0)
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", backref="conversations")
    assigned_agent = relationship("User", foreign_keys=[assigned_to])
    chat_messages = relationship("ChatMessage", back_populates="conversation", lazy="selectin", order_by="ChatMessage.created_at")
```

**Step 2: Create ChatMessage model**

Create `backend/app/models/chat_message.py`:

```python
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id"), index=True)
    sender_type: Mapped[str] = mapped_column(String(10))  # contact, agent, bot, system
    sender_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    content_type: Mapped[str] = mapped_column(String(20), default="text")
    content: Mapped[str] = mapped_column(Text)
    channel_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="chat_messages")
```

**Step 3: Create ChannelIdentity model**

Create `backend/app/models/channel_identity.py`:

```python
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ChannelIdentity(Base):
    __tablename__ = "channel_identities"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("customers.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    channel_id: Mapped[str] = mapped_column(String(255), index=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", backref="channel_identities")
```

**Step 4: Create ChatbotFlow model**

Create `backend/app/models/chatbot_flow.py`:

```python
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ChatbotFlow(Base):
    __tablename__ = "chatbot_flows"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    trigger_type: Mapped[str] = mapped_column(String(20))
    trigger_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    steps: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
```

**Step 5: Register models in __init__.py**

Add imports to `backend/app/models/__init__.py`:

```python
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage
from app.models.channel_identity import ChannelIdentity
from app.models.chatbot_flow import ChatbotFlow
```

**Step 6: Generate Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "add chat models"`

**Step 7: Run tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: all pass

**Step 8: Commit**

```bash
git add backend/app/models/
git commit -m "feat: add Conversation, ChatMessage, ChannelIdentity, ChatbotFlow models"
```

---

### Task 3: Create chat schemas

**Files:**
- Create: `backend/app/schemas/chat.py`

**Step 1: Create schemas**

Create `backend/app/schemas/chat.py`:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ConversationResponse(BaseModel):
    id: str
    number: Optional[int] = None
    customer_id: str
    assigned_to: Optional[str] = None
    channel: str
    status: str
    priority: str
    handler: str = "chatbot"
    ai_enabled: bool = True
    ai_attempts: int = 0
    subject: Optional[str] = None
    tags: Optional[list] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    customer_id: str
    channel: str = "chat"
    subject: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_type: str
    sender_id: Optional[str] = None
    content_type: str
    content: str
    channel_message_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    content: str
    content_type: str = "text"


class ChatbotFlowResponse(BaseModel):
    id: str
    name: str
    trigger_type: str
    trigger_config: Optional[dict] = None
    steps: Optional[dict] = None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatbotFlowCreate(BaseModel):
    name: str
    trigger_type: str
    trigger_config: Optional[dict] = None
    steps: Optional[dict] = None
    active: bool = True
```

**Step 2: Commit**

```bash
git add backend/app/schemas/chat.py
git commit -m "feat: add chat schemas (Conversation, ChatMessage, ChatbotFlow)"
```

---

### Task 4: Port chat services (chatbot_engine, chat_routing, chat_ws_manager)

**Files:**
- Create: `backend/app/services/chatbot_engine.py` (copy from carbon-chat, adapt)
- Create: `backend/app/services/chat_routing_service.py`
- Create: `backend/app/services/chat_ws_manager.py`

**Step 1: Copy and adapt chatbot_engine.py**

Copy from `/Users/pedrocastro/Desktop/carbon-chat/backend/app/services/chatbot_engine.py`.
Change model import: `from app.models.chatbot_flow import ChatbotFlow` (was `from app.models.chatbot import ChatbotFlow`).
No other changes needed — it uses generic `conversation: object`.

**Step 2: Create chat_routing_service.py**

Adapt from carbon-chat's `routing_service.py`. Change:
- `Agent` → `User` (from `app.models.user import User`)
- Filter by `User.is_active == True` and `User.status == "online"`
- Assign via `conversation.assigned_to = user.id`

```python
"""Chat routing — auto-assign conversations to available agents."""

import logging
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)


async def get_available_agents(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(User).where(
            User.is_active.is_(True),
            User.status == "online",
            User.role.in_(["agent", "supervisor", "admin", "super_admin"]),
        )
    )
    return list(result.scalars().all())


async def auto_assign(db: AsyncSession, conversation: Conversation) -> Optional[User]:
    agents = await get_available_agents(db)
    if not agents:
        return None

    # Round-robin: pick agent with fewest active conversations
    best = None
    best_count = float("inf")
    for agent in agents:
        count_result = await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.assigned_to == agent.id,
                Conversation.status == "open",
            )
        )
        count = count_result.scalar() or 0
        if count < agent.max_concurrent_chats and count < best_count:
            best = agent
            best_count = count

    if best:
        conversation.assigned_to = best.id
        return best
    return None
```

**Step 3: Create chat_ws_manager.py**

Copy from carbon-chat's `ws_manager.py`. This manages visitor + agent WebSocket connections for chat. No model changes needed — it only deals with WebSocket objects and string IDs.

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: all pass

**Step 5: Commit**

```bash
git add backend/app/services/chatbot_engine.py backend/app/services/chat_routing_service.py backend/app/services/chat_ws_manager.py
git commit -m "feat: add chatbot engine, chat routing, and chat WS manager"
```

---

### Task 5: Port channel adapters and dispatcher

**Files:**
- Create: `backend/app/services/channels/` directory
- Copy from carbon-chat: `base.py`, `dispatcher.py`, `whatsapp_adapter.py`, `instagram_adapter.py`, `facebook_adapter.py`, `tiktok_adapter.py`, `chat_adapter.py`

**Step 1: Copy entire channels directory**

```bash
cp -r /Users/pedrocastro/Desktop/carbon-chat/backend/app/services/channels/ backend/app/services/channels/
```

No adaptations needed — adapters use HTTP clients and don't reference internal models.

**Step 2: Add channel config to settings**

Check `backend/app/core/config.py` for existing Meta/WhatsApp settings. Add any missing:

```python
# Chat channel settings (add if not present)
META_VERIFY_TOKEN: str = ""
META_APP_SECRET: str = ""
WHATSAPP_PHONE_ID: str = ""
WHATSAPP_ACCESS_TOKEN: str = ""
TIKTOK_CLIENT_SECRET: str = ""
```

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: all pass

**Step 4: Commit**

```bash
git add backend/app/services/channels/ backend/app/core/config.py
git commit -m "feat: add channel adapters (WhatsApp, IG, FB, TikTok, chat)"
```

---

### Task 6: Port AI auto_reply and message_pipeline

**Files:**
- Modify: `backend/app/services/ai_service.py`
- Create: `backend/app/services/message_pipeline.py`
- Create: `backend/tests/test_chat_pipeline.py`

**Step 1: Add auto_reply to ai_service.py**

The helpdesk already has `ai_service.py`. Add the `auto_reply` function from carbon-chat at the end. No conflicts — it's a new function. Ensure `json` and `re` are imported at top.

**Step 2: Create message_pipeline.py**

Copy from carbon-chat's `message_pipeline.py`. Adapt references:
- `from app.models.conversation import Conversation` (same)
- `from app.models.customer import Customer` (was Contact)
- `from app.models.chat_message import ChatMessage` (was Message)
- `from app.services.chatbot_engine import ChatbotEngine` (same)
- `from app.services import ai_service` (same)
- KB search: use helpdesk's KB search function. Check how `backend/app/services/ai_service.py` or `backend/app/api/kb.py` searches articles. Adapt the import.
- `from app.services import chat_routing_service as routing_service` (was routing_service)
- `contact.shopify_data` → `customer.shopify_data`
- `Message(...)` → `ChatMessage(...)`

**Step 3: Write tests**

Create `backend/tests/test_chat_pipeline.py` with the same test structure from carbon-chat's `test_pipeline.py`, adapted for helpdesk models (Customer instead of Contact, User instead of Agent, ChatMessage instead of Message, KBArticle instead of KnowledgeArticle).

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_chat_pipeline.py -v`
Expected: all pass

**Step 5: Run full suite**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: all pass

**Step 6: Commit**

```bash
git add backend/app/services/ai_service.py backend/app/services/message_pipeline.py backend/tests/test_chat_pipeline.py
git commit -m "feat: add auto_reply and message pipeline for chat"
```

---

### Task 7: Create chat API endpoints

**Files:**
- Create: `backend/app/api/chat.py`
- Create: `backend/app/api/chatbot.py`
- Modify: `backend/app/main.py` (register routers)

**Step 1: Create chat.py API**

Endpoints:
- `GET /api/chat/conversations` — list conversations (filterable by status, channel, assigned_to)
- `GET /api/chat/conversations/{id}` — get single conversation
- `POST /api/chat/conversations` — create conversation
- `GET /api/chat/conversations/{id}/messages` — list messages
- `POST /api/chat/conversations/{id}/messages` — send message (agent)
- `POST /api/chat/conversations/{id}/toggle-ai` — toggle AI
- `PUT /api/chat/conversations/{id}/assign` — assign agent
- `PUT /api/chat/conversations/{id}/resolve` — resolve conversation
- `GET /api/chat/conversations/counts` — counts by status

All endpoints require auth (`get_current_user` dependency).

**Step 2: Create chatbot.py API**

Endpoints:
- `GET /api/chatbot/flows` — list flows
- `POST /api/chatbot/flows` — create flow
- `PUT /api/chatbot/flows/{id}` — update flow
- `DELETE /api/chatbot/flows/{id}` — delete flow

**Step 3: Register routers in main.py**

Add to `backend/app/main.py`:

```python
from app.api.chat import router as chat_router
from app.api.chatbot import router as chatbot_router
app.include_router(chat_router)
app.include_router(chatbot_router)
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: all pass

**Step 5: Commit**

```bash
git add backend/app/api/chat.py backend/app/api/chatbot.py backend/app/main.py
git commit -m "feat: add chat and chatbot API endpoints"
```

---

### Task 8: Create chat webhook endpoints

**Files:**
- Create: `backend/app/api/webhooks/` directory (if not exists)
- Create: `backend/app/api/webhooks/whatsapp.py`
- Create: `backend/app/api/webhooks/meta_dm.py`
- Create: `backend/app/api/webhooks/tiktok.py`
- Modify: `backend/app/main.py` (register routers)

**Step 1: Port webhook handlers**

Copy from carbon-chat's webhook handlers. Adapt:
- `Contact` → `Customer`
- `Conversation` (same model name, different import path)
- `Message` → `ChatMessage`
- `ChannelIdentity` from new model path
- Add pipeline call after message save (already wired in carbon-chat)
- Dispatcher import from new path

**Step 2: Register webhook routers in main.py**

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: all pass

**Step 4: Commit**

```bash
git add backend/app/api/webhooks/ backend/app/main.py
git commit -m "feat: add chat webhook endpoints (WhatsApp, Meta DM, TikTok)"
```

---

### Task 9: Expand WebSocket for chat visitors

**Files:**
- Modify: `backend/app/api/ws.py`

**Step 1: Add visitor WebSocket endpoint**

Add to existing `backend/app/api/ws.py` a new endpoint `/ws/chat/{visitor_id}` for chat widget visitors. This uses `chat_ws_manager` (not the existing ticket ConnectionManager).

Also add pipeline integration to the visitor message handler (same pattern as carbon-chat's ws.py).

Add agent chat WebSocket events: when agent sends message via existing WS, check if it's a chat conversation and forward to visitor.

**Step 2: Run tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: all pass

**Step 3: Commit**

```bash
git add backend/app/api/ws.py
git commit -m "feat: add chat visitor WebSocket endpoint with pipeline integration"
```

---

### Task 10: Frontend — ChatPage and components

**Files:**
- Create: `frontend/src/pages/ChatPage.jsx`
- Create: `frontend/src/components/chat/ChatList.jsx`
- Create: `frontend/src/components/chat/ChatView.jsx`
- Create: `frontend/src/components/chat/ChatInput.jsx`
- Create: `frontend/src/components/chat/ChatMessageBubble.jsx`
- Create: `frontend/src/components/chat/TypingIndicator.jsx`
- Create: `frontend/src/components/chat/ChannelIcon.jsx`

**Step 1: Create components**

Port from carbon-chat's frontend components, adapting:
- Design system: dark background (#18181B), yellow accent (#E5A800/#FDD200), matching helpdesk's existing style
- API paths: `/api/chat/conversations/...` instead of `/api/conversations/...`
- Auth context: use helpdesk's existing auth context (user instead of agent)
- lucide-react icons: check if helpdesk uses lucide-react or font-awesome. Helpdesk uses font-awesome — adapt icons or add lucide-react dep.

**Step 2: Create ChatPage.jsx**

Split panel layout:
- Left: ChatList (conversations list with channel/status filters)
- Right: ChatView (messages + input)
- Mobile: toggle between list and view

**Step 3: Build frontend**

Run: `cd frontend && npm run build`
Expected: build succeeds

**Step 4: Commit**

```bash
git add frontend/src/pages/ChatPage.jsx frontend/src/components/chat/
git commit -m "feat: add ChatPage and chat components"
```

---

### Task 11: Frontend — Add Chat to sidebar and routing

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/App.jsx` (or wherever routes are defined)

**Step 1: Add sidebar item**

In `Sidebar.jsx`, add to the Atendimento group after "Caixa de Entrada":

```javascript
{ to: '/chat', label: 'Chat ao Vivo', icon: 'fa-headset', roles: ['super_admin', 'admin', 'supervisor', 'agent'], badge: 'chat' },
```

Add `chatCount` prop to Sidebar and wire badge display.

**Step 2: Add route**

In App.jsx (or router config), add:

```javascript
<Route path="/chat" element={<ChatPage />} />
```

Import ChatPage.

**Step 3: Wire chat count**

In the Layout component, fetch chat conversation count from `/api/chat/conversations/counts` and pass as `chatCount` prop to Sidebar.

**Step 4: Build frontend**

Run: `cd frontend && npm run build`
Expected: build succeeds

**Step 5: Commit**

```bash
git add frontend/src/components/Sidebar.jsx frontend/src/App.jsx
git commit -m "feat: add Chat ao Vivo to sidebar and routing"
```

---

### Task 12: Full integration test

**Step 1: Run full backend test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all pass (original + new chat tests)

**Step 2: Build frontend**

Run: `cd frontend && npm run build`
Expected: build succeeds

**Step 3: Commit any remaining changes**

```bash
git add -A
git commit -m "feat: chat integration complete — chat ao vivo in helpdesk"
```
