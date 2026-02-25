# Performance Optimization - Carbon Helpdesk

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Otimizar performance do helpdesk em todas as camadas: DB indexes, cache Redis, consolidacao de queries, e frontend code splitting.

**Architecture:** Adicionar indexes compostos no PostgreSQL para queries frequentes, implementar cache Redis com TTL para endpoints pesados (dashboard, leaderboard), consolidar 15+ queries do dashboard em 2-3 queries com CASE statements, e configurar Vite manualChunks para separar recharts do bundle principal.

**Tech Stack:** PostgreSQL (indexes, sequences), Redis (aioredis cache), SQLAlchemy async, FastAPI, Vite (rollupOptions), React.lazy

---

### Task 1: Database - Indexes Compostos e pool_pre_ping

**Files:**
- Modify: `backend/app/core/database.py`
- Modify: `backend/app/main.py` (migration_sqls)

**Step 1: Adicionar pool_pre_ping ao engine**

Em `backend/app/core/database.py`, alterar linha 6:
```python
engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=20, max_overflow=10, pool_pre_ping=True)
```

**Step 2: Adicionar indexes compostos nas migrations**

Em `backend/app/main.py`, adicionar ao final da lista `migration_sqls` (antes do fechamento `]`):
```python
            # Performance: composite indexes for common query patterns
            "CREATE INDEX IF NOT EXISTS idx_tickets_status_created ON tickets(status, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_agent_created ON tickets(assigned_to, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_source_created ON tickets(source, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_sla ON tickets(sla_deadline) WHERE sla_breached = FALSE",
            "CREATE INDEX IF NOT EXISTS idx_messages_type_created ON messages(type, created_at DESC)",
```

**Step 3: Verificar que o backend inicia sem erros**

Run: Deploy ao servidor e checar logs.
Expected: Backend inicia sem erros de migration, indexes criados.

**Step 4: Commit**
```bash
git add backend/app/core/database.py backend/app/main.py
git commit -m "perf: add composite indexes and pool_pre_ping"
```

---

### Task 2: Redis Cache Service

**Files:**
- Create: `backend/app/services/cache.py`

**Step 1: Criar servico de cache Redis**

```python
"""Redis cache service for expensive queries."""
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis = None


async def get_redis():
    """Get or create Redis connection."""
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await _redis.ping()
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")
            _redis = None
    return _redis


async def cache_get(key: str) -> Any | None:
    """Get value from cache. Returns None on miss or error."""
    r = await get_redis()
    if not r:
        return None
    try:
        val = await r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    """Set value in cache with TTL. Fails silently."""
    r = await get_redis()
    if not r:
        return
    try:
        await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception:
        pass


async def cache_delete_pattern(pattern: str):
    """Delete all keys matching pattern. Fails silently."""
    r = await get_redis()
    if not r:
        return
    try:
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await r.delete(*keys)
    except Exception:
        pass
```

**Step 2: Verificar que redis.asyncio (aioredis) esta no requirements.txt**

Checar `backend/requirements.txt` para ver se `redis` ja esta listado. Se nao, adicionar `redis>=5.0.0`.

**Step 3: Commit**
```bash
git add backend/app/services/cache.py backend/requirements.txt
git commit -m "feat: add Redis cache service"
```

---

### Task 3: Dashboard Stats - Consolidar Queries + Cache

**Files:**
- Modify: `backend/app/api/dashboard.py`

**Step 1: Reescrever get_stats consolidando 15 queries em 3**

Substituir todo o endpoint `get_stats` por versao otimizada. A ideia:
- **Query 1**: Todas as contagens/agrupamentos de tickets num unico SELECT com CASE
- **Query 2**: Medias de tempo (response/resolution)
- **Query 3**: Volume diario + FCR
- Envolver tudo com cache Redis de 5 minutos

```python
@router.get("/stats")
async def get_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.cache import cache_get, cache_set

    cache_key = f"dashboard:stats:{days}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Query 1: All ticket counts in one pass
    q1 = await db.execute(
        select(
            func.count().label("total"),
            # By status
            func.count(case((Ticket.status == "open", 1))).label("s_open"),
            func.count(case((Ticket.status == "in_progress", 1))).label("s_in_progress"),
            func.count(case((Ticket.status == "waiting", 1))).label("s_waiting"),
            func.count(case((Ticket.status == "waiting_supplier", 1))).label("s_waiting_supplier"),
            func.count(case((Ticket.status == "waiting_resend", 1))).label("s_waiting_resend"),
            func.count(case((Ticket.status == "analyzing", 1))).label("s_analyzing"),
            func.count(case((Ticket.status == "resolved", 1))).label("s_resolved"),
            func.count(case((Ticket.status == "closed", 1))).label("s_closed"),
            func.count(case((Ticket.status == "escalated", 1))).label("s_escalated"),
            # By priority
            func.count(case((Ticket.priority == "low", 1))).label("p_low"),
            func.count(case((Ticket.priority == "medium", 1))).label("p_medium"),
            func.count(case((Ticket.priority == "high", 1))).label("p_high"),
            func.count(case((Ticket.priority == "urgent", 1))).label("p_urgent"),
            # Flags
            func.count(case((Ticket.sla_breached == True, 1))).label("sla_breached"),
            func.count(case((Ticket.legal_risk == True, 1))).label("legal_risk"),
            # Categories
            func.count(case((Ticket.category == "troca", 1))).label("c_troca"),
            func.count(case((Ticket.category == "reclamacao", 1))).label("c_reclamacao"),
            func.count(case((Ticket.category.in_(["garantia", "mau_uso", "suporte_tecnico", "carregador"]), 1))).label("c_problemas"),
            # Resolved today
            func.count(case((Ticket.resolved_at >= today_start, 1))).label("resolved_today"),
            # Unassigned open
            func.count(case((and_(Ticket.assigned_to.is_(None), Ticket.status.notin_(["resolved", "closed"])), 1))).label("unassigned"),
        )
        .select_from(Ticket)
        .where(Ticket.created_at >= since)
    )
    r = q1.one()

    by_status = {}
    for s in ["open", "in_progress", "waiting", "waiting_supplier", "waiting_resend", "analyzing", "resolved", "closed", "escalated"]:
        val = getattr(r, f"s_{s}")
        if val:
            by_status[s] = val

    by_priority = {}
    for p in ["low", "medium", "high", "urgent"]:
        val = getattr(r, f"p_{p}")
        if val:
            by_priority[p] = val

    total_tickets = r.total

    # By category (dynamic - need separate small query)
    cat_q = await db.execute(
        select(Ticket.category, func.count())
        .where(Ticket.created_at >= since, Ticket.category.isnot(None))
        .group_by(Ticket.category)
    )
    by_category = {row[0]: row[1] for row in cat_q.all()}

    # By source
    source_q = await db.execute(
        select(Ticket.source, func.count())
        .where(Ticket.created_at >= since, Ticket.source.isnot(None))
        .group_by(Ticket.source)
    )
    by_source = {row[0]: row[1] for row in source_q.all()}

    # By sentiment
    sentiment_q = await db.execute(
        select(Ticket.sentiment, func.count())
        .where(Ticket.created_at >= since, Ticket.sentiment.isnot(None))
        .group_by(Ticket.sentiment)
    )
    by_sentiment = {row[0]: row[1] for row in sentiment_q.all()}

    # Query 2: Time averages
    q2 = await db.execute(
        select(
            func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
            .filter(Ticket.first_response_at.isnot(None)).label("avg_resp"),
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600)
            .filter(Ticket.resolved_at.isnot(None)).label("avg_res"),
        )
        .where(Ticket.created_at >= since)
    )
    times = q2.one()
    avg_response_hours = round(times.avg_resp or 0, 1)
    avg_resolution_hours = round(times.avg_res or 0, 1)

    # Query 3: Daily volume
    daily_q = await db.execute(
        select(func.date(Ticket.created_at).label("day"), func.count().label("count"))
        .where(Ticket.created_at >= since)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
    )
    daily_volume = [{"date": str(row[0]), "count": row[1]} for row in daily_q.all()]

    # Query 4: Responded today + FCR (messages)
    responded_result = await db.execute(
        select(func.count(func.distinct(Message.ticket_id)))
        .where(Message.type == "outbound", Message.created_at >= today_start)
    )
    responded_today = responded_result.scalar() or 0

    # FCR - with date filter fix
    from sqlalchemy import literal_column
    fcr_subq = (
        select(Message.ticket_id, func.count().label("outbound_count"))
        .where(Message.type == "outbound", Message.created_at >= since)
        .group_by(Message.ticket_id)
        .subquery()
    )
    fcr_q = await db.execute(
        select(func.count()).select_from(Ticket)
        .outerjoin(fcr_subq, Ticket.id == fcr_subq.c.ticket_id)
        .where(
            Ticket.created_at >= since,
            Ticket.status == "resolved",
            func.coalesce(fcr_subq.c.outbound_count, 0) <= 1,
        )
    )
    fcr_count = fcr_q.scalar() or 0
    total_resolved = by_status.get("resolved", 0)
    fcr_rate = round((fcr_count / max(total_resolved, 1)) * 100, 1) if total_resolved > 0 else 0

    open_tickets = sum(v for k, v in by_status.items() if k not in ("resolved", "closed"))

    result = {
        "period_days": days,
        "total_tickets": total_tickets,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "by_source": by_source,
        "by_sentiment": by_sentiment,
        "sla_breached": r.sla_breached,
        "sla_compliance": round((1 - r.sla_breached / max(total_tickets, 1)) * 100, 1),
        "avg_response_hours": avg_response_hours,
        "avg_resolution_hours": avg_resolution_hours,
        "legal_risk_count": r.legal_risk,
        "daily_volume": daily_volume,
        "trocas_count": r.c_troca,
        "reclamacoes_count": r.c_reclamacao,
        "problemas_count": r.c_problemas,
        "escalated_count": by_status.get("escalated", 0),
        "open_tickets": open_tickets,
        "resolved_today": r.resolved_today,
        "responded_today": responded_today,
        "fcr_count": fcr_count,
        "fcr_rate": fcr_rate,
        "unassigned_count": r.unassigned,
    }

    await cache_set(cache_key, result, ttl_seconds=300)
    return result
```

**Step 2: Adicionar cache ao agent-stats**

Envolver o endpoint `get_agent_stats` com cache de 2 minutos, usando key `dashboard:agent:{user.id}:{days}`.

Adicionar no inicio do handler:
```python
    from app.services.cache import cache_get, cache_set
    cache_key = f"dashboard:agent:{user.id}:{days}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
```

E no final, antes do return:
```python
    result = { ... }  # o dict existente
    await cache_set(cache_key, result, ttl_seconds=120)
    return result
```

**Step 3: Commit**
```bash
git add backend/app/api/dashboard.py
git commit -m "perf: consolidate dashboard to 4 queries + Redis cache 5min"
```

---

### Task 4: Cache no Leaderboard

**Files:**
- Modify: `backend/app/api/gamification.py`

**Step 1: Adicionar cache de 2 minutos ao leaderboard**

No inicio do handler `get_leaderboard`:
```python
    from app.services.cache import cache_get, cache_set
    cache_key = f"gamification:leaderboard:{days}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
```

No final, antes do return:
```python
    await cache_set(cache_key, leaderboard, ttl_seconds=120)
    return leaderboard
```

**Step 2: Commit**
```bash
git add backend/app/api/gamification.py
git commit -m "perf: add Redis cache to leaderboard (2min TTL)"
```

---

### Task 5: Invalidar Cache ao Modificar Tickets

**Files:**
- Modify: `backend/app/api/tickets.py`

**Step 1: Invalidar cache do dashboard quando tickets mudam**

Adicionar invalidacao nos pontos criticos de `tickets.py`:
- Apos `create_ticket` (commit)
- Apos `update_ticket` (commit)
- Apos `bulk_update` (commit)

Em cada um desses pontos, apos o `await db.commit()`:
```python
    from app.services.cache import cache_delete_pattern
    await cache_delete_pattern("dashboard:*")
    await cache_delete_pattern("gamification:*")
```

Tambem adicionar no `gmail.py` apos criar ticket via compose/fetch, e no `main.py` email fetch loop (apos commit).

Pontos exatos:
- `tickets.py`: apos commit em `create_ticket` (~linha 460), `update_ticket` (~linha 565), `bulk_update` (~linha 640)
- `gmail.py`: apos commit em `compose_email` (~linha 821), `fetch_emails` (~linha 642)

**Step 2: Commit**
```bash
git add backend/app/api/tickets.py backend/app/api/gmail.py
git commit -m "perf: invalidate dashboard cache on ticket changes"
```

---

### Task 6: Frontend - Vite Code Splitting

**Files:**
- Modify: `frontend/vite.config.js`

**Step 1: Configurar manualChunks para separar recharts**

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'es2020',
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-charts': ['recharts'],
        },
      },
    },
  },
})
```

**Step 2: Commit**
```bash
git add frontend/vite.config.js
git commit -m "perf: split recharts into separate chunk via manualChunks"
```

---

### Task 7: Frontend - Lazy Load DashboardPage

**Files:**
- Modify: `frontend/src/components/Layout.jsx`

**Step 1: Mover DashboardPage para lazy load**

Na linha 5, remover o import direto:
```javascript
// REMOVER: import DashboardPage from '../pages/DashboardPage'
```

Adicionar junto com os outros lazy imports (apos linha 19):
```javascript
const DashboardPage = lazy(() => import('../pages/DashboardPage'))
```

NOTA: O DashboardPage ja esta dentro de `<Suspense>` no JSX? Verificar o render. Se nao estiver, envolver com `<Suspense fallback={<div>...</div>}>`.

**Step 2: Commit**
```bash
git add frontend/src/components/Layout.jsx
git commit -m "perf: lazy-load DashboardPage (recharts loaded on demand)"
```

---

### Task 8: Frontend - Rebuild e Deploy

**Files:**
- Nenhum arquivo novo

**Step 1: Rebuild frontend no servidor**

O deploy.sh ja faz rsync + docker build. Executar:
```bash
bash deploy.sh
```

Ou manualmente:
```bash
sshpass -p 'OdysseY144.-a' rsync -avz \
  --exclude node_modules --exclude .git --exclude __pycache__ \
  --exclude .env --exclude venv --exclude .venv --exclude dist \
  --exclude backups --exclude .claude \
  ~/Desktop/carbon-helpdesk/ root@143.198.20.6:/opt/carbon-helpdesk/

sshpass -p 'OdysseY144.-a' ssh root@143.198.20.6 \
  "cd /opt/carbon-helpdesk && docker compose -f docker-compose.prod.yml up -d --build"
```

**Step 2: Rodar testes de performance**

```bash
# Comparar tempos antes/depois
TOKEN=<gerar token>
curl -sL -o /dev/null -w "%{time_total}s size:%{size_download}B\n" \
  -H "Accept-Encoding: gzip" -H "Authorization: Bearer $TOKEN" \
  "http://143.198.20.6/api/dashboard/stats"

# Segundo request (deve vir do cache)
curl -sL -o /dev/null -w "%{time_total}s size:%{size_download}B\n" \
  -H "Accept-Encoding: gzip" -H "Authorization: Bearer $TOKEN" \
  "http://143.198.20.6/api/dashboard/stats"

# Frontend JS (deve ter chunks separados)
curl -s -o /dev/null -w "%{time_total}s size:%{size_download}B\n" \
  -H "Accept-Encoding: gzip" \
  "http://143.198.20.6/assets/index-*.js"
```

Expected:
- Dashboard stats: 1o request ~300ms, 2o request ~270ms (cache hit)
- Frontend JS principal: ~150-200KB (sem recharts)
- Chunk recharts: ~200KB (carregado sob demanda)

**Step 3: Commit final**
```bash
git add -A
git commit -m "perf: deploy performance optimizations"
```

---

## Resumo de Impacto Esperado

| Otimizacao | Antes | Depois | Ganho |
|-----------|-------|--------|-------|
| Dashboard stats (1o req) | 15 queries, ~400ms | 4 queries, ~300ms | -25% |
| Dashboard stats (2o+ req) | 15 queries, ~400ms | Cache hit, ~270ms | -33% |
| Leaderboard (2o+ req) | Aggregation, ~370ms | Cache hit, ~270ms | -27% |
| Frontend JS inicial | 803KB | ~350KB | -56% |
| Queries com filtro status+date | Full scan | Index seek | -50%+ |
| Conexoes DB mortas | Erro esporadico | pool_pre_ping auto-reconecta | Eliminado |
