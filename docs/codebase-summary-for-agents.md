# Carbon Helpdesk - Technical Codebase Summary

Generated: 2026-03-12. Purpose: reference for AI agents implementation planning.

---

## 1. Application Startup (`main.py`)

### Lifespan Sequence
1. **Create tables**: `Base.metadata.create_all` via async SQLAlchemy engine
2. **Run migrations**: ~60+ `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements executed sequentially with try/except (failures logged but not fatal)
3. **Init ticket sequence**: atomic ticket number generation via `init_ticket_sequence(conn)`
4. **Drop old enum types**: removes `ticket_status`, `ticket_priority`, `sentiment_type` enums (system uses VARCHAR now)
5. **Seed demo data**: only in non-production environments via `seed_database(session)`
6. **Register channel adapters**: WhatsApp, Instagram, Facebook, TikTok adapters registered with a `dispatcher`
7. **Start 6 background tasks** (all infinite loops with `asyncio.create_task`):
   - `_run_escalation_loop()` - every 5 min, checks SLA breaches and escalations
   - `_run_email_fetch_loop()` - every 60s, fetches Gmail, creates/updates tickets, runs AI triage + auto-reply
   - `_run_scheduled_email_loop()` - every 30s, sends scheduled emails
   - `_run_weekly_analysis()` - every Sunday 23h UTC, generates agent performance reports
   - `_run_chat_inactivity_loop()` - every 2 min, auto-closes inactive chat conversations (25min threshold, differentiated timeout messages)
   - `_run_auto_close_loop()` - every 6h, closes tickets inactive >5 days

### CORS
Configured from `settings.CORS_ORIGINS` (comma-separated string).

### Routers (30+ routers)
All mounted under `/api` prefix except webhooks (`wh_whatsapp`, `wh_meta_dm`, `wh_tiktok`, `wh_vapi`) and WebSocket (`ws`).

Key routers: `auth`, `tickets`, `dashboard`, `kb`, `slack`, `gmail`, `ai`, `tracking`, `shopify`, `meta`, `chat`, `chatbot`, `triage`, `ra_monitor`, `voice_calls`, `csat`.

### Static Files
- `/api/uploads` serves uploaded attachments from `./uploads` directory
- `/api/public/invoice-pdf` - public proxy endpoint for NF PDFs (token-protected)

### Email Fetch Health Tracking
Global `_email_health` dict tracks: `last_success`, `last_check`, `consecutive_failures`, `total_processed`, `total_errors`, `last_error`. Sends Slack alert after 3+ consecutive failures.

---

## 2. Database Layer (`core/database.py`)

### Engine Configuration
- **Async engine**: `create_async_engine` with `pool_size=20`, `max_overflow=10`, `pool_pre_ping=True`
- **Session factory**: `async_sessionmaker` with `expire_on_commit=False`
- **Base class**: `DeclarativeBase` (SQLAlchemy 2.0 style)

### Session Dependency
```python
async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```
Used as FastAPI `Depends(get_db)` in all API routes.

### Migration Strategy
NOT using Alembic. Migrations are raw SQL strings in `main.py` lifespan, executed with `ADD COLUMN IF NOT EXISTS`. Separate migration files exist in `migrations/` for more complex changes (e.g., `004_triage_rules.sql`). **Important rule**: always run migration SQL BEFORE deploying model changes to production.

---

## 3. Database Models

### Ticket (`models/ticket.py`)
Table: `tickets`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (str) | PK, auto-generated |
| number | Integer | unique, auto-increment |
| subject | String(500) | |
| status | String(50) | default="open", indexed. Valid: open, in_progress, waiting, waiting_supplier, waiting_resend, analyzing, resolved, closed, escalated, archived, merged |
| priority | String(20) | default="medium", indexed. Valid: low, medium, high, urgent |
| category | String(100) | nullable. Values: meu_pedido, garantia, reenvio, financeiro, duvida, reclamacao |
| customer_id | UUID FK→customers | indexed |
| assigned_to | UUID FK→users | nullable, indexed |
| inbox_id | UUID FK→inboxes | nullable |
| sla_deadline | DateTime(tz) | nullable |
| sla_response_deadline | DateTime(tz) | nullable |
| sla_breached | Boolean | default=False |
| sentiment | String(20) | nullable. Values: positive, neutral, negative, angry |
| ai_category | String(100) | nullable, AI-assigned category |
| ai_confidence | Float | nullable |
| ai_summary | Text | nullable |
| legal_risk | Boolean | default=False |
| is_locked | Boolean | default=False |
| locked_by | UUID FK→users | nullable |
| tags | ARRAY(String) | nullable. e.g., ["guacu", "reclame_aqui", "auto_reply", "ack"] |
| slack_channel_id | String(100) | nullable |
| slack_thread_ts | String(50) | nullable, indexed |
| source | String(50) | default="web". Values: web, gmail, slack, whatsapp, instagram, facebook |
| meta_conversation_id | String(100) | nullable, indexed |
| meta_platform | String(20) | nullable |
| ai_auto_mode | Boolean | default=True |
| ai_paused_by | UUID FK→users | nullable |
| ai_paused_at | DateTime(tz) | nullable |
| protocol | String(30) | nullable, unique, indexed |
| protocol_sent | Boolean | default=False |
| internal_notes | Text | nullable |
| merged_into_id | UUID | nullable, indexed |
| email_message_id | String(255) | nullable, indexed |
| supplier_notes | Text | nullable |
| escalated_at | DateTime(tz) | nullable |
| escalation_reason | String(255) | nullable |
| last_agent_response_at | DateTime(tz) | nullable |
| tracking_code | String(100) | nullable |
| tracking_status | String(100) | nullable |
| tracking_data | JSONB | nullable |
| received_at | DateTime(tz) | nullable, indexed |
| created_at | DateTime(tz) | auto-set, indexed |
| updated_at | DateTime(tz) | auto-set, auto-updated |
| resolved_at | DateTime(tz) | nullable |
| csat_sent | Boolean | default=False |
| first_response_at | DateTime(tz) | nullable |
| auto_replied | Boolean | default=False |
| auto_reply_at | DateTime(tz) | nullable |

**Relationships:**
- `customer` → Customer (selectin, via customer_id)
- `agent` → User (selectin, via assigned_to)
- `messages` → Message[] (select, ordered by created_at)

### Message (`models/message.py`)
Table: `messages`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (str) | PK |
| ticket_id | UUID FK→tickets | indexed |
| type | Enum | "inbound", "outbound", "internal_note" (DB enum `message_type`) |
| sender_email | String(255) | nullable |
| sender_name | String(255) | nullable |
| body_html | Text | nullable |
| body_text | Text | nullable |
| gmail_message_id | String(255) | nullable |
| gmail_thread_id | String(255) | nullable, indexed |
| attachments | JSONB | nullable |
| ai_suggestion | Text | nullable |
| slack_ts | String(50) | nullable |
| meta_message_id | String(100) | nullable |
| meta_platform | String(20) | nullable |
| original_ticket_id | UUID | nullable (merge tracking) |
| email_message_id | String(255) | nullable |
| email_references | Text | nullable |
| cc | Text | nullable |
| bcc | Text | nullable |
| scheduled_at | DateTime(tz) | nullable |
| is_scheduled | Boolean | default=False |
| created_at | DateTime(tz) | auto-set |

**Relationships:**
- `ticket` → Ticket (back_populates="messages")

### User (`models/user.py`)
Table: `users`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (str) | PK |
| name | String(255) | |
| email | String(255) | unique, indexed |
| password_hash | String(255) | |
| role | Enum | "super_admin", "admin", "supervisor", "agent" (DB enum `user_role`) |
| is_active | Boolean | default=True |
| avatar_url | String(500) | nullable |
| specialty | String(50) | nullable. Values: juridico, tecnico, logistica, geral |
| max_tickets | Integer | default=20 |
| email_signature | String(2000) | nullable, HTML |
| status | String(10) | default="offline" |
| max_concurrent_chats | Integer | default=10 |
| created_at | DateTime(tz) | auto-set |
| last_login | DateTime(tz) | nullable |
| last_activity_at | DateTime(tz) | nullable |

### KBArticle (`models/kb_article.py`)
Table: `kb_articles`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (str) | PK |
| title | String(500) | |
| content | Text | |
| category | String(100) | indexed |
| tags | ARRAY(String) | nullable |
| is_published | Boolean | default=True |
| created_at | DateTime(tz) | auto-set |
| updated_at | DateTime(tz) | auto-set |

No relationships defined. Queried by category to provide context to AI prompts. The actual KB data is stored both in this table AND in a hardcoded Python module `kb_real_data.py` (the `KB_ARTICLES` list). The `seed_kb.py` service syncs the latter into the DB.

### TriageRule (`models/triage_rule.py`)
Table: `triage_rules`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (str) | PK |
| name | String(255) | |
| is_active | Boolean | default=True |
| priority | Integer | default=0. Higher = checked first |
| category | String(100) | nullable. Condition field for matching |
| assign_to | UUID FK→users | nullable. Action: assign ticket to this agent |
| set_priority | String(20) | nullable. Action: set ticket priority |
| auto_reply | Boolean | default=False. Action: enable auto-reply for this rule |
| created_by | UUID FK→users | |
| created_at | DateTime(tz) | auto-set |
| updated_at | DateTime(tz) | auto-set, auto-updated |

**Relationships:**
- `agent` → User (selectin, via assign_to)

---

## 4. AI Service (`services/ai_service.py`)

Central AI service wrapping the Anthropic Claude API. All functions are async.

### Global State
- `client`: singleton `Anthropic` instance, lazy-initialized
- `_credits_exhausted` / `_credits_exhausted_at`: credit exhaustion tracking with 5-min auto-retry

### Key Functions

**`get_client() -> Anthropic`**
Lazy init of Anthropic client using `settings.ANTHROPIC_API_KEY`. Raises RuntimeError if key missing.

**`is_credits_exhausted() -> bool`**
Checks if credits are exhausted. Auto-resets after 300s for retry.

**`_handle_credit_error(error) -> bool`**
Checks error message for credit-related keywords. If found, sets exhaustion flag and fires async Slack alert. Returns True if credit error.

**`_call_with_retry(func, max_retries=3)`**
Wraps sync Anthropic calls via `asyncio.to_thread(func)`. Retries on 429/500/529/overloaded errors with exponential backoff + jitter.

**`_clean_json(text) -> dict`**
Strips markdown code fences and parses JSON from Claude responses.

**`apply_triage_results(ticket, triage, customer=None)`**
Applies triage dict to ticket model: sets category, priority, sentiment, legal_risk, tags, ai_confidence. Adds "revisao_manual" tag if confidence < 0.5. Upgrades priority (never downgrades) based on keywords (Procon/advogado = urgent, Reclame Aqui/chargeback = high). Enriches customer data (cpf, phone, full_name) if available.

**`triage_ticket(subject, body, customer_name="", is_repeat=False) -> dict | None`**
AI-powered ticket classification. Uses `TRIAGE_SYSTEM_PROMPT` to return JSON with: category, priority, sentiment, legal_risk, tags, confidence, summary, customer_data. Falls back to `_fallback_triage()` (keyword matching) when credits exhausted. Model: `settings.ANTHROPIC_TRIAGE_MODEL` or `claude-haiku-4-5-20251001`. Max tokens: 500.

**`suggest_reply(subject, body, customer_name, category, kb_context, partial_text) -> str | None`**
Generates reply suggestions for agents. Supports autocomplete (partial_text parameter). Model: `settings.ANTHROPIC_MODEL`. Max tokens: 400 (partial) or 800 (full). Raises `CreditExhaustedError` on credit issues.

**`summarize_ticket(subject, messages, category, customer_name) -> str | None`**
Generates executive summary from last 15 messages. Max tokens: 300. Raises `CreditExhaustedError`.

**`ai_auto_reply(ticket_subject, conversation_history, customer_name, category, kb_context, platform) -> dict | None`**
Auto-reply for Meta channels (WhatsApp/Instagram/Facebook). Returns `{"response": str, "should_escalate": bool, "escalation_reason": str}`. Max tokens: 600.

**`chat_auto_reply(messages, contact_shopify_data, kb_articles) -> dict`**
Main chatbot reply function. Injects Shopify data and KB articles into system prompt. Parses JSON response with confidence (high/medium/low). Returns `{"response": str, "confidence": str, "resolved": bool}`. Falls back to plain text as medium confidence. Max tokens: 1024.

**`moderate_comment(comment_text, author_name, post_caption, platform) -> dict | None`**
Social media comment moderation. Returns `{"action": "reply"|"hide_reply"|"hide"|"ignore", "reply": str, "sentiment": str, "category": str, "confidence": float}`.

**`test_ai_connection() -> dict`**
Health check. Sends minimal request to Claude.

### Keyword Fallback (`_fallback_triage`)
When AI credits exhausted, uses `_KEYWORD_FALLBACK` dict mapping categories to keyword lists. Checks legal keywords for urgent priority. Returns confidence=0.3.

### CreditExhaustedError
Custom exception raised by `suggest_reply` and `summarize_ticket` when credits are exhausted.

---

## 5. Email Auto-Reply Service (`services/email_auto_reply_service.py`)

### Flow (triggered from `_run_email_fetch_loop` in main.py)

1. New email arrives → Gmail fetch loop creates ticket + runs AI triage
2. `generate_auto_reply()` called with subject, body, customer_name, category, triage dict, protocol, from_email
3. **Decision tree:**
   - If `EMAIL_AUTO_REPLY_ENABLED` is False → `skip`
   - If legal_risk or urgent priority → `skip`
   - If HARD_ESCALATE keywords detected (garantia, defeito, Procon, IP68, natacao, etc.) → `ack` (template response)
   - Enriches with Shopify order data + live tracking (via `_enrich_with_order_data`)
   - If SOFT_ESCALATE keywords (cancelar, estorno, nota fiscal) AND no order data → `ack`
   - If category in AUTO_RESOLVE_CATEGORIES (meu_pedido, duvida, reenvio) with confidence >= 0.5, OR order data available → generates AI reply via `_generate_ai_reply()` → `auto_reply`
   - Otherwise → `ack` (template)

4. **Return value:** `{"type": "auto_reply"|"ack"|"skip", "body": str, "reason": str}`

5. Back in main.py: if type is auto_reply or ack, sends via `send_email()`, creates outbound Message, marks ticket as `auto_replied=True`, sets `first_response_at`, changes status to "waiting" if auto_reply, adds type as tag.

### Order Data Enrichment (`_enrich_with_order_data`)
- Strategy 1: extract order number from subject/body via `data_extractor.extract_customer_data()`
- Strategy 2: look up by customer email in Shopify (most recent of 3 orders)
- If order found, fetches live tracking via `track_package()`
- Returns formatted dict with: order_number, items, total, financial_status, delivery_status, tracking info, region

### AI Reply Generation (`_generate_ai_reply`)
- Checks credit exhaustion
- Builds prompt with KB context (by category), order data context, email body (first 2000 chars)
- Uses `EMAIL_AUTO_REPLY_PROMPT` system prompt with strict rules (never invent, never mention import/China, max 4 paragraphs)
- Model: `settings.ANTHROPIC_AUTO_REPLY_MODEL` or `settings.ANTHROPIC_MODEL`. Max tokens: 800.

### ACK Template
Static template with customer name, protocol number, useful links (rastreio, troque.app.br, garantia info). Promises response within 24 business hours.

### `send_auto_reply()`
Sends reply via `gmail_service.send_email()` in the same Gmail thread (using thread_id and in_reply_to). Runs sync function via `asyncio.to_thread`.

---

## 6. Slack Integration

### Service Layer (`services/slack_service.py`)

Uses `slack_sdk.web.async_client.AsyncWebClient`.

**`get_slack_client() -> AsyncWebClient | None`**
Returns client if `SLACK_BOT_TOKEN` configured, else None.

**`send_slack_message(channel, text, thread_ts=None) -> dict | None`**
Posts message to channel, optionally as thread reply. Returns `{"ok": True, "ts": ..., "channel": ...}`.

**`send_ticket_created_notification(channel, thread_ts, ticket_number, subject)`**
Posts ticket creation confirmation as thread reply.

**`send_agent_reply_to_slack(channel, thread_ts, agent_name, message_text)`**
Posts agent reply to Slack thread.

**`get_slack_user_info(user_id) -> dict | None`**
Gets user profile (name, email) from Slack.

**`test_slack_connection() -> dict`**
Tests auth via `auth_test()`.

### API Layer (`api/slack.py`)

**`POST /api/slack/events`** - Slack Events API webhook
- Handles `url_verification` challenge
- Verifies request signature via HMAC-SHA256 (5-min replay window)
- Processes `message` events:
  - Ignores bot messages and subtypes
  - Only processes messages in `SLACK_SUPPORT_CHANNEL`
  - Top-level message → `handle_new_slack_ticket()`: looks up/creates Customer, creates Ticket (source="slack"), creates Message, sends confirmation back to Slack
  - Thread reply → `handle_slack_thread_reply()`: finds ticket by `slack_thread_ts`, adds Message, reopens if resolved

**`GET /api/slack/status`** - Check Slack integration status (auth required)

**`POST /api/slack/send-reply`** - Send agent reply to Slack thread (auth required)
- Requires ticket_id and message. Validates ticket has Slack fields.

### Slack is also used for alerts:
- Credit exhaustion alerts (from ai_service)
- Email fetch failure alerts (from main.py)
- Individual email processing error alerts (from main.py)

---

## 7. Triage System (`services/triage_service.py`)

Two-layer triage: AI classification (ai_service) + rule-based routing (triage_service).

### AI Classification (Layer 1, in ai_service.py)
Called in `_run_email_fetch_loop` after ticket creation. Returns structured JSON with category, priority, sentiment, legal_risk, tags, confidence, summary, customer_data.

### Rule-Based Routing (Layer 2, in triage_service.py)

**`apply_triage_rules(ticket, db) -> dict`**
1. Loads all active `TriageRule` records, ordered by priority DESC
2. For each rule, checks if `rule.category` matches `ticket.category` (or rule has no category = matches all)
3. First matching rule applies:
   - Sets priority (only upgrades, never downgrades)
   - Assigns ticket to `rule.assign_to` agent
   - Returns `auto_reply` flag
4. If no rule matches → fallback round-robin

**`_fallback_round_robin(ticket, db) -> dict`**
Assigns to online agent with fewest open tickets.

**`_pick_online_agent(db) -> User | None`**
- "Online" = `last_activity_at` within 15 minutes AND `is_active=True` AND role in (agent, supervisor)
- Counts open tickets per agent (statuses: open, in_progress, waiting, analyzing, waiting_supplier, waiting_resend)
- Skips agents at `max_tickets` capacity
- Returns agent with minimum ticket count

**`get_online_agents(db) -> list[User]`**
Returns list of online agents based on 15-min activity threshold.

### Pre-configured Rules (6 rules from session 24)
1. Reclamacao → Victor (urgent)
2. Garantia → Tauane (high)
3. Financeiro → Victor (high)
4. Reenvio → Luana (medium, auto_reply)
5. Meu Pedido → round-robin (medium, auto_reply)
6. Duvida → round-robin (low, auto_reply)

---

## 8. KB Articles

### Storage
- **Database**: `kb_articles` table (KBArticle model) with title, content (full text), category, tags, is_published
- **Python module**: `kb_real_data.py` contains `KB_ARTICLES` list (hardcoded, authoritative source)

### Seeding (`services/seed_kb.py`)
`reseed_kb(db)` deletes ALL existing KB articles and re-inserts from `KB_ARTICLES` list. Returns count.

### Usage in AI
- `email_auto_reply_service._get_kb_context(category)`: filters KB_ARTICLES by category, takes first 3, truncates content to 500 chars each
- `ai_service.suggest_reply()`: accepts `kb_context` parameter (pre-formatted string, up to 1500 chars)
- `ai_service.chat_auto_reply()`: accepts `kb_articles` list, formats into system prompt

### Querying
KB articles are queried by category (exact match on the `category` column). No full-text search is implemented at the DB level -- the AI handles semantic matching via the context injected into prompts.

---

## 9. Patterns and Conventions

### Async Pattern
- All services are async. Sync operations (Gmail API, Anthropic SDK) are wrapped in `asyncio.to_thread()`.
- Background tasks use infinite `while True` loops with `asyncio.sleep()` intervals.
- Database sessions are async via `sqlalchemy.ext.asyncio`.

### Error Handling
- Try/except with logging at every level. Errors are caught and logged, rarely re-raised (graceful degradation).
- AI services have special credit exhaustion handling that disables AI features and alerts via Slack.
- Email fetch loop continues processing remaining emails if one fails (`continue` after error).
- Triage and auto-reply failures are caught and logged as warnings, not blocking ticket creation.

### ID Generation
All models use `uuid.uuid4()` as string UUIDs for primary keys. Ticket numbers are sequential integers managed by a separate sequence service.

### Logging
Standard Python `logging` module. Named loggers per module/concern: `email_fetch`, `escalation`, `scheduled_email`, `weekly_analysis`, `auto_close`, `chat_inactivity`, `migrations`. Format: `%(asctime)s %(name)s %(levelname)s %(message)s`.

### Configuration
Via `app.core.config.settings` (likely Pydantic BaseSettings). Key settings referenced:
- `DATABASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_AUTO_REPLY_MODEL`, `ANTHROPIC_TRIAGE_MODEL`
- `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_SUPPORT_CHANNEL`
- `EMAIL_AUTO_REPLY_ENABLED`, `GMAIL_SUPPORT_EMAIL`
- `SLA_URGENT_HOURS`, `SLA_HIGH_HOURS`, `SLA_MEDIUM_HOURS`, `SLA_LOW_HOURS`
- `CORS_ORIGINS`, `PROJECT_NAME`, `VERSION`, `ENVIRONMENT`
- `NF_PDF_TOKEN`

### Relationships Pattern
Models use SQLAlchemy `relationship()` with `lazy="selectin"` for eager-loaded FKs (customer, agent) and `lazy="select"` for collections (messages). This avoids N+1 queries for the common case.

### Tag System
Tags are stored as `ARRAY(String)` in PostgreSQL. Tags are accumulated (set union) rather than replaced. Special tags: `auto_reply`, `ack`, `revisao_manual`, `reclame_aqui`, `guacu`, `reincidente`, `ra:{id}`.

### Priority System
4 levels: low < medium < high < urgent. Priority can only be UPGRADED by triage rules (never downgraded). Keyword-based override in `apply_triage_results()` can upgrade to urgent/high regardless of AI classification.

### SLA System
SLA deadlines set on ticket creation based on priority. Recalculated when ticket is reopened (new email on resolved/closed ticket). Separate `sla_deadline` (resolution) and `sla_response_deadline` (first response).

### Email Thread Matching
3-level strategy to match incoming emails to existing tickets:
1. Gmail thread_id match
2. In-Reply-To header match against stored email_message_id
3. Fallback: most recent open ticket from same customer email

---

## 10. Additional Tables (created via migrations in main.py)

These tables are created inline in the lifespan function, not via separate model files:

- **conversations**: chat conversations (id, customer_id, assigned_to, channel, status, handler, ai_enabled, ai_attempts, subject, tags, metadata, last_message_at)
- **chat_messages**: individual chat messages (conversation_id, sender_type, sender_id, content_type, content, channel_message_id)
- **channel_identities**: maps customers to channel IDs (customer_id, channel, channel_id)
- **chatbot_flows**: chatbot flow definitions (name, trigger_type, trigger_config, steps, active)
- **social_comments**: social media comment moderation (platform, comment_id, author, text, ai_action, ai_reply, ai_sentiment)
- **moderation_settings**: key/value settings for moderation (ai_enabled, auto_reply, auto_hide)
- **media_items**: media library items linked to Google Drive
- **rewards / reward_claims**: gamification system for agents

---

## 11. External Integrations Summary

| Integration | Module | Purpose |
|-------------|--------|---------|
| Anthropic Claude | ai_service.py | Triage, reply suggestions, auto-reply, chat, comment moderation |
| Gmail API | gmail_service.py | Fetch emails, send replies, mark as read |
| Slack SDK | slack_service.py | Receive tickets, send notifications, alerts |
| Shopify API | shopify_service.py | Order lookup by number/email |
| Tracking (Wonca) | tracking_service.py | Package tracking (Correios/Cainiao) |
| Meta (WhatsApp/IG/FB) | channels/, webhooks/ | Receive/send messages via Graph API |
| TroqueCommerce | troque_service.py | Returns/exchanges portal API |
| Vapi | webhooks/vapi.py | Voice AI integration |
| Google Drive | gdrive (separate project) | Media library |
