# Integracao Carbon Chat no Helpdesk — Design Doc

**Data:** 2026-03-05
**Status:** Aprovado

## Objetivo

Integrar o projeto Carbon Chat dentro do Helpdesk como uma secao separada. Chat ao vivo (widget, WhatsApp, Instagram DM, Facebook Messenger, TikTok) coexiste com Tickets (email), compartilhando a mesma base de clientes, agentes e knowledge base.

## Decisoes de Design

1. **Customer como entidade central** — Customer eh pai de tudo (tickets + conversations + channel_identities). Email passa a ser nullable (contatos de WhatsApp podem nao ter)
2. **User expandido** — Adicionar status online/offline e max_concurrent_chats ao User existente. Nao criar modelo Agent separado
3. **Tabelas separadas** — `tickets` + `messages` (email) e `conversations` + `chat_messages` (chat) coexistem no mesmo banco. Schemas muito diferentes pra unificar
4. **KB unificada** — Usar KBArticle do helpdesk. Pipeline de IA do chat busca artigos na mesma tabela
5. **Pipeline AI so no chat** — Tickets de email continuam manuais. Auto-reply so roda em conversations de chat
6. **Todos os canais** — Widget, WhatsApp, Instagram DM, Facebook Messenger, TikTok. Codigo ja existe
7. **Sidebar** — "Chat ao Vivo" no grupo Atendimento, abaixo de "Caixa de Entrada"

## Arquitetura

```
Helpdesk (projeto unificado)
|-- Tickets (email) -- intocado
|-- Chat (nova secao)
|   |-- conversations + chat_messages (tabelas novas)
|   |-- chatbot_flows (tabela nova)
|   |-- channel_identities (tabela nova)
|   |-- WebSocket visitor + agent real-time
|   |-- AI Auto-Loop Pipeline (chatbot -> IA -> handoff)
|   |-- Channel adapters (WhatsApp, IG, FB, TikTok, widget)
|-- Customer unificado (pai de tudo)
|   |-- tickets (email)
|   |-- conversations (chat)
|   |-- channel_identities
|-- User expandido (+ status, max_concurrent_chats)
|-- KB unificada (KBArticle existente)
|-- Frontend: sidebar com "Chat ao Vivo" abaixo de "Caixa de Entrada"
```

## Modelo de Dados

### Expandir `customers`

Novos campos:
- `shopify_data` (JSONB, nullable)
- `external_id` (varchar 100, nullable, index)
- `avatar_url` (varchar 500, nullable)
- `total_conversations` (int, default 0)
- `total_value` (float, default 0.0)
- `email` torna-se nullable

### Expandir `users`

Novos campos:
- `status` (varchar 10, default "offline")
- `max_concurrent_chats` (int, default 10)

### Tabelas Novas

**`conversations`**
- id (uuid PK)
- number (int, unique, index)
- customer_id (FK customers)
- assigned_to (FK users, nullable)
- channel (varchar 20, index) — chat, whatsapp, instagram, facebook, tiktok
- status (varchar 20, default "open", index)
- priority (varchar 10, default "normal")
- handler (varchar 10, default "chatbot") — chatbot, ai, agent
- ai_enabled (bool, default true)
- ai_attempts (int, default 0)
- subject (varchar 500, nullable)
- tags (JSONB, nullable)
- last_message_at (timestamptz, nullable)
- metadata (JSONB, nullable)
- created_at, updated_at (timestamptz)

**`chat_messages`**
- id (uuid PK)
- conversation_id (FK conversations)
- sender_type (varchar 10) — contact, agent, bot, system
- sender_id (uuid, nullable)
- content_type (varchar 20, default "text")
- content (text)
- channel_message_id (varchar 255, nullable)
- delivered_at (timestamptz, nullable)
- read_at (timestamptz, nullable)
- metadata (JSONB, nullable)
- created_at (timestamptz)

**`channel_identities`**
- id (uuid PK)
- customer_id (FK customers)
- channel (varchar 20)
- channel_id (varchar 255, index)
- metadata (JSONB, nullable)
- created_at (timestamptz)

**`chatbot_flows`**
- id (uuid PK)
- name (varchar 255)
- trigger_type (varchar 20)
- trigger_config (JSONB, nullable)
- steps (JSONB, nullable)
- active (bool, default true)
- created_at, updated_at (timestamptz)

## Backend

### Services Novos (do chat, adaptados)
- `message_pipeline.py` — orquestrador chatbot -> IA -> handoff
- `chatbot_engine.py` — engine de flows
- `chat_service.py` — CRUD conversations + chat_messages
- `chat_ws_manager.py` — gerenciador WebSocket visitor + agent chat
- `chat_routing_service.py` — auto-assign round-robin pra chat
- `channels/` — dispatcher + 5 adapters (WhatsApp, IG, FB, TikTok, chat widget)

### Services Modificados
- `ai_service.py` — adicionar `auto_reply()` com confidence assessment

### API Novos
- `api/chat.py` — CRUD conversations, messages, toggle-ai
- `api/chatbot.py` — CRUD chatbot flows
- `api/ws.py` — expandir com WebSocket visitor (/ws/chat/{visitor_id})
- `api/webhooks/whatsapp.py` — webhook WhatsApp
- `api/webhooks/meta_dm.py` — webhook Instagram/Facebook DMs
- `api/webhooks/tiktok.py` — webhook TikTok

### Adaptacao de Referencias
- Agent -> User (id, name, email, role, status)
- Contact -> Customer (id, name, email, phone)
- KnowledgeArticle -> KBArticle (id, title, content, category)
- conversation.contact_id -> conversation.customer_id
- conversation.assigned_agent_id -> conversation.assigned_to

## Frontend

### Pagina Nova
- `ChatPage.jsx` — split panel: lista de conversations (esquerda) + chat view (direita)

### Componentes Novos (adaptados ao design system Carbon dark)
- ChatList — lista de conversations com filtros por canal/status
- ChatView — header + messages + input (com botao toggle IA)
- ChatInput — input com tabs mensagem/nota
- ChatMessageBubble — bolha de mensagem (contact/agent/bot/system)
- TypingIndicator — indicador de digitacao
- ChannelIcon — icone por canal (WhatsApp, IG, etc)

### Sidebar
- Novo item: "Chat ao Vivo", icone fa-headset, badge com contagem
- Posicao: grupo Atendimento, abaixo de "Caixa de Entrada"

## O Que NAO Muda
- Tickets (email) — intocados
- Messages (email) — intocadas
- Gmail service — intocado
- Frontend de tickets — intocado
- Auth — mesma, User existente
- Dashboard — intocado (pode adicionar metricas de chat depois)
