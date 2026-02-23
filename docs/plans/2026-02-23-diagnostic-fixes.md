# Carbon Expert Hub - Diagnostic Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 68 diagnosed issues across 4 phases (critical, high, medium, low).

**Architecture:** Direct fixes to existing FastAPI backend and React frontend. No new dependencies except where explicitly needed (e.g., Alembic). All changes are backwards-compatible.

**Tech Stack:** Python/FastAPI, React 18, SQLAlchemy, Tailwind CSS

---

## Phase 1: Critical Fixes (Security + Crashes)

### Task 1: Remove hardcoded credentials from backend config
**Files:** Modify: `backend/app/core/config.py:8,11`
- Remove default values from DATABASE_URL and JWT_SECRET
- Make them required (no default = must be set via env)

### Task 2: Remove hardcoded demo credentials from LoginPage
**Files:** Modify: `frontend/src/pages/LoginPage.jsx:6-7,140`
- Clear default email/password state
- Remove visible demo credentials text

### Task 3: Fix missing imports causing NameError
**Files:**
- Modify: `backend/app/api/slack.py` - Move `from sqlalchemy import func` to top
- Verify: `backend/app/api/tickets.py` - Confirm AuditLog import exists at line 19

### Task 4: Fix silent migration failures
**Files:** Modify: `backend/app/main.py:309-310,317-318`
- Replace `except Exception: pass` with proper logging

### Task 5: Guard seed data from running in production
**Files:** Modify: `backend/app/main.py:321-322`
- Add ENVIRONMENT check, only seed if ENVIRONMENT != "production"

### Task 6: Fix background tasks blocking event loop
**Files:** Modify: `backend/app/main.py:15-193`
- Wrap synchronous service calls with asyncio.to_thread()

### Task 7: Fix frontend error handling
**Files:**
- Modify: `frontend/src/services/api.js:20-23` - Proper logout flow
- Modify: `frontend/src/hooks/useWebSocket.js:36,51` - Log errors
- Modify: `frontend/src/components/Toast.jsx:69` - Log errors
- Modify: `frontend/src/App.jsx:15` - Add try/catch to JSON.parse
- Modify: `frontend/src/App.jsx:32` - Add loading spinner

---

## Phase 2: High Severity Fixes

### Task 8: Fix SLA calculation in AI triage
**Files:** Modify: `backend/app/api/ai.py:92`
- Use datetime.now(timezone.utc) instead of ticket.created_at

### Task 9: Fix SQLAlchemy != None comparisons
**Files:** Modify: `backend/app/api/tickets.py:109,124,215`
- Replace `!= None` with `.isnot(None)`

### Task 10: Fix pick_agent ignoring max_tickets
**Files:** Modify: `backend/app/api/tickets.py:605-613`
- Return None when all agents are at capacity instead of fallback

### Task 11: Fix duplicate SLA recalculation in bulk_update
**Files:** Modify: `backend/app/api/tickets.py:558-561`
- Remove duplicate SLA calculation block

### Task 12: Add RBAC to list_users endpoint
**Files:** Modify: `backend/app/api/auth.py:42-46`
- Restrict to admin/supervisor/super_admin roles

### Task 13: Fix CSAT O(n) query in reports
**Files:** Modify: `backend/app/api/reports.py:51-76`
- Use a single joined query instead of per-agent loop

### Task 14: Fix WebSocket broadcast silent failures
**Files:** Modify: `backend/app/api/ws.py:74-77,84-87`
- Log errors and remove dead connections

### Task 15: Fix ecommerce settings persistence
**Files:** Modify: `backend/app/api/ecommerce.py:284-293`
- Add warning comment that settings are runtime-only

### Task 16: Fix frontend token validation on load
**Files:** Modify: `frontend/src/App.jsx:11-18`
- Validate token with /auth/me API call on startup

### Task 17: Fix WebSocket security
**Files:** Modify: `frontend/src/hooks/useWebSocket.js:3,15,29-30,43`
- Auto-detect wss:// vs ws://
- Fix race condition in reconnect
- Use crypto.randomUUID() for IDs

### Task 18: Fix NotificationBell event listener
**Files:** Modify: `frontend/src/components/NotificationBell.jsx:23-25`
- Only add listener when dropdown is open

### Task 19: Add Error Boundary to React app
**Files:**
- Modify: `frontend/src/App.jsx` - Wrap with ErrorBoundary
- Add ErrorBoundary component inline

---

## Phase 3: Medium Severity Fixes

### Task 20: Change ticket relationships to lazy loading
**Files:** Modify: `backend/app/models/ticket.py:93-95`
- Change lazy="selectin" to lazy="select"

### Task 21: Add visibility API to frontend auto-refresh
**Files:**
- Modify: `frontend/src/components/Layout.jsx:27-32`
- Modify: `frontend/src/pages/TicketsPage.jsx:165-170`

### Task 22: Add debounce to ticket search
**Files:** Modify: `frontend/src/pages/TicketsPage.jsx:220-224`

### Task 23: Fix CSV export to use streaming
**Files:** Modify: `backend/app/api/export.py:50-85`

### Task 24: Fix ticket duplicate detection
**Files:** Modify: `backend/app/api/tickets.py` - duplicate detection logic

### Task 25: Extract Claude model to config
**Files:**
- Modify: `backend/app/core/config.py` - Add ANTHROPIC_MODEL setting
- Modify: `backend/app/services/ai_service.py` - Use config

### Task 26: Fix ThemeContext to be functional or remove toggle
**Files:**
- Modify: `frontend/src/pages/LoginPage.jsx` - Remove non-functional toggle

---

## Phase 4: Low Severity Fixes

### Task 27: Replace magic numbers with named constants
**Files:** Multiple frontend files

### Task 28: Add proper error logging instead of console.error
**Files:** Multiple frontend files

### Task 29: Fix inline style mutations
**Files:** `frontend/src/components/Sidebar.jsx` and others
