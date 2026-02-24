# Carbon Helpdesk "100%" Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement ticket/customer merge, fix all 68 diagnostics, and harden for production.

**Architecture:** Direct modifications to existing FastAPI backend + React frontend. New merge endpoints, regex extraction utility, and UI components.

**Tech Stack:** Python/FastAPI, React 18, SQLAlchemy, Tailwind CSS

---

## Phase 1: Backend — Models & Merge Feature

### Task 1: Add merge fields to models
**Files:** Modify: `backend/app/models/customer.py`, `backend/app/models/ticket.py`, `backend/app/models/message.py`

- Customer: add `merged_into_id` (FK self), `alternate_emails` (ARRAY String)
- Ticket: add `merged_into_id` (FK self), `email_message_id` (String)
- Message: add `email_message_id` (String), `email_references` (String)
- Add migration SQL to main.py lifespan

### Task 2: Create data extraction utility
**Files:** Create: `backend/app/services/data_extractor.py`

- `extract_customer_data(text)` → returns dict with cpf, phone, shopify_order_id, email
- Regex patterns for CPF, phone, Shopify order number, email
- Normalize CPF (remove dots/dashes), phone (remove parens/spaces)

### Task 3: Update AI triagem to extract customer data
**Files:** Modify: `backend/app/services/ai_service.py`

- Add customer data extraction fields to TRIAGE_SYSTEM_PROMPT
- Parse response to include cpf, phone, order_number if found

### Task 4: Update email fetch to handle thread matching
**Files:** Modify: `backend/app/api/gmail.py`

- Extract Message-ID, In-Reply-To, References headers from emails
- Before creating new ticket, check if In-Reply-To matches existing message
- If match found, add as message to existing ticket instead of creating new one

### Task 5: Create customer matching service
**Files:** Create: `backend/app/services/customer_matcher.py`

- `find_matching_customer(db, cpf, phone, email, shopify_order)` → Customer or None
- Search by CPF, phone, alternate emails, shopify order IDs
- Used during ticket creation to link to existing customer

### Task 6: Create merge API endpoints
**Files:** Modify: `backend/app/api/tickets.py`

- `POST /tickets/merge` — merge source ticket into target
- `POST /customers/merge` — merge source customer into target
- `GET /customers/{id}` — get customer details with all tickets
- `GET /customers/search` — search customers by name/email/cpf/phone

### Task 7: Update ticket creation to use customer matching
**Files:** Modify: `backend/app/api/tickets.py`, `backend/app/api/gmail.py`

- After extracting data from email body, call customer_matcher
- If match found, use existing customer instead of creating new one
- Add note to ticket suggesting merge if similar ticket exists

### Task 8: Frontend — Merge tickets UI
**Files:** Modify: `frontend/src/pages/TicketDetailPage.jsx`, `frontend/src/services/api.js`

- Add "Mesclar" button in ticket detail sidebar
- Modal to search and select target ticket
- API call to merge endpoint
- Show merged badge on merged tickets

### Task 9: Frontend — Merge customers UI
**Files:** Modify: `frontend/src/pages/TicketDetailPage.jsx`

- In customer info sidebar, add "Mesclar cliente" button
- Modal to search customers (by name, email, CPF)
- API call to customer merge endpoint

---

## Phase 2: Critical Diagnostic Fixes (Tasks 1-7)

### Task 10: Fix config security
**Files:** Modify: `backend/app/core/config.py`
- DATABASE_URL and JWT_SECRET already have empty defaults (already fixed)
- Verify they're required at startup

### Task 11: Fix missing imports
**Files:** Modify: `backend/app/api/slack.py`
- Move `from sqlalchemy import func` to top-level imports

### Task 12: Fix silent migration failures
**Files:** Modify: `backend/app/main.py`
- Replace `except Exception: pass` with proper logging in migration blocks

### Task 13: Fix background tasks blocking event loop
**Files:** Modify: `backend/app/main.py`
- Wrap synchronous service calls with asyncio.to_thread()

### Task 14: Fix frontend error handling
**Files:** Modify: `frontend/src/services/api.js`, `frontend/src/hooks/useWebSocket.js`
- Already mostly fixed based on code review (ErrorBoundary exists, token validation exists)
- Verify all error paths are handled

---

## Phase 3: High Severity Fixes (Tasks 8-19)

### Task 15: Fix SLA calculation
**Files:** Modify: `backend/app/api/ai.py:92`
- Use datetime.now(timezone.utc) instead of ticket.created_at for SLA

### Task 16: Fix SQLAlchemy != None comparisons
**Files:** Modify: `backend/app/api/tickets.py`
- Replace `!= None` with `.isnot(None)` everywhere

### Task 17: Fix pick_agent ignoring max_tickets
**Files:** Modify: `backend/app/api/tickets.py`
- Return None when all agents at capacity

### Task 18: Fix duplicate SLA recalculation
**Files:** Modify: `backend/app/api/tickets.py`
- Remove duplicate SLA calculation block in bulk_update

### Task 19: Fix RBAC on list_users
**Files:** Modify: `backend/app/api/auth.py`
- Already restricted to all roles based on code review (line 42)
- Verify agents can't list all users if needed

### Task 20: Fix CSAT O(n) query
**Files:** Modify: `backend/app/api/reports.py`
- Use single joined query instead of per-agent loop

### Task 21: Fix WebSocket broadcast failures
**Files:** Modify: `backend/app/api/ws.py`
- Log errors and remove dead connections

### Task 22: Fix frontend token validation
**Files:** Already implemented in App.jsx (getMe on startup)

### Task 23: Fix WebSocket security
**Files:** Already implemented (auto-detect wss/ws, crypto.randomUUID)

### Task 24: Fix NotificationBell event listener
**Files:** Modify: `frontend/src/components/NotificationBell.jsx`
- Already using mousedown handler correctly

### Task 25: Error Boundary
**Files:** Already implemented in App.jsx

---

## Phase 4: Medium & Low Severity Fixes

### Task 26: Add debounce to ticket search
**Files:** Modify: `frontend/src/pages/TicketsPage.jsx`
- Add debounce (300ms) to search input

### Task 27: Fix ThemeContext toggle
**Files:** Modify: `frontend/src/pages/LoginPage.jsx`
- Remove non-functional theme toggle if exists

### Task 28: Extract Claude model to config
**Files:** Already done — config.py has ANTHROPIC_MODEL

### Task 29: Replace magic numbers
**Files:** Multiple frontend files
- Extract timeout values, pagination sizes to constants

---

## Phase 5: Production Hardening

### Task 30: Update nginx for SSL-ready IP deployment
**Files:** Modify: `deploy/nginx.conf`, `docker-compose.prod.yml`
- Configure nginx with self-signed cert or HTTP for now
- Ensure CORS and WebSocket configs are correct for IP access
- Add proper health checks

### Task 31: Create PostgreSQL backup script
**Files:** Create: `deploy/backup.sh`
- pg_dump inside docker container
- Compress and store with timestamp
- Keep last 7 daily backups

### Task 32: Security hardening
**Files:** Modify: `backend/app/main.py`, `backend/app/core/config.py`
- Ensure seed data doesn't run in production
- Add startup validation for required env vars
- Log warnings for missing optional config
