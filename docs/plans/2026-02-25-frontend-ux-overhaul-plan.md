# Frontend UX Overhaul — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve Carbon Helpdesk frontend UX for a team of 4-10 agents handling high volume — URL routing, command palette, sidebar grouping, dashboard simplification, skeleton loading, ticket preview, sticky headers, typography, keyboard shortcuts overlay.

**Architecture:** Incremental improvements on existing React 18 + Vite + Tailwind codebase. Each task is independent and testable. No rewrites — surgical changes to existing components.

**Tech Stack:** React 18, react-router-dom 6, Tailwind CSS 3.4, Vite 5, DM Sans + JetBrains Mono (Google Fonts), lucide-react

---

### Task 1: Typography & Google Fonts

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/index.css`

**Step 1: Add Google Fonts to index.html**

Add before the Font Awesome link:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

**Step 2: Update body font-family in index.css**

Replace the existing `body` rule's font-family:

```css
body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

**Step 3: Add monospace utility class in index.css**

Add at the end of index.css:

```css
/* ═══ Monospace for numbers/codes ═══ */
.font-mono-carbon {
  font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
  font-weight: 500;
}
```

**Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

**Step 5: Commit**

```bash
git add frontend/index.html frontend/src/index.css
git commit -m "feat: switch typography to DM Sans + JetBrains Mono"
```

---

### Task 2: Skeleton Loading Component

**Files:**
- Create: `frontend/src/components/Skeleton.jsx`
- Modify: `frontend/src/index.css` (add keyframes)

**Step 1: Add skeleton keyframes to index.css**

Add at the end of index.css:

```css
/* ═══ Skeleton Loading ═══ */
@keyframes shimmer {
  0% { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}

.skeleton {
  background: linear-gradient(90deg, var(--bg-tertiary) 25%, rgba(255,255,255,0.15) 50%, var(--bg-tertiary) 75%);
  background-size: 800px 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
}
```

**Step 2: Create Skeleton component**

Create `frontend/src/components/Skeleton.jsx`:

```jsx
import React from 'react'

export function SkeletonLine({ width = '100%', height = '14px', className = '' }) {
  return <div className={`skeleton ${className}`} style={{ width, height }} />
}

export function SkeletonCircle({ size = '32px', className = '' }) {
  return <div className={`skeleton ${className}`} style={{ width: size, height: size, borderRadius: '50%' }} />
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`rounded-xl p-4 border ${className}`} style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
      <div className="flex items-center justify-between mb-3">
        <SkeletonLine width="60%" height="10px" />
        <SkeletonCircle size="32px" />
      </div>
      <SkeletonLine width="40%" height="28px" />
    </div>
  )
}

export function SkeletonTicketRow() {
  return (
    <div className="flex items-center gap-4 px-6 py-4 border-b" style={{ borderColor: 'var(--border-color)' }}>
      <SkeletonCircle size="16px" />
      <SkeletonLine width="50px" height="12px" />
      <div className="flex-1 space-y-1.5">
        <SkeletonLine width="60%" height="13px" />
        <SkeletonLine width="40%" height="10px" />
      </div>
      <SkeletonLine width="70px" height="22px" />
      <SkeletonLine width="50px" height="22px" />
      <SkeletonLine width="60px" height="12px" />
      <SkeletonLine width="80px" height="12px" />
    </div>
  )
}

export function SkeletonTicketList({ rows = 8 }) {
  return (
    <div>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonTicketRow key={i} />
      ))}
    </div>
  )
}

export function SkeletonDashboard() {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <SkeletonLine width="160px" height="28px" />
        <SkeletonLine width="120px" height="36px" />
      </div>
      <div className="flex gap-2 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonLine key={i} width="120px" height="36px" />
        ))}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl p-4 border" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
          <SkeletonLine width="140px" height="14px" className="mb-4" />
          <SkeletonLine width="100%" height="200px" />
        </div>
        <div className="rounded-xl p-4 border" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
          <SkeletonLine width="140px" height="14px" className="mb-4" />
          <SkeletonLine width="100%" height="200px" />
        </div>
      </div>
    </div>
  )
}
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 4: Commit**

```bash
git add frontend/src/components/Skeleton.jsx frontend/src/index.css
git commit -m "feat: add skeleton loading components"
```

---

### Task 3: URL Routing with React Router

**Files:**
- Modify: `frontend/src/main.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Layout.jsx`
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/pages/TicketsPage.jsx` (navigate instead of onOpenTicket prop)
- Modify: `frontend/src/pages/TicketDetailPage.jsx` (useParams, useNavigate)
- Modify: `frontend/src/pages/DashboardPage.jsx` (useNavigate instead of onNavigate prop)
- Modify: `frontend/src/pages/TrackingPage.jsx` (useNavigate)
- Modify: `frontend/src/pages/CanaisIAPage.jsx` (useNavigate)
- Modify: `frontend/src/services/api.js` (update 401 redirect)

**Step 1: Update main.jsx to wrap with BrowserRouter**

Replace `frontend/src/main.jsx` entirely:

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
```

**Step 2: Update App.jsx — remove page state, keep auth only**

Replace `frontend/src/App.jsx` entirely:

```jsx
import React, { useState, useEffect, Component } from 'react'
import { ThemeProvider } from './contexts/ThemeContext'
import { ToastProvider } from './components/Toast'
import LoginPage from './pages/LoginPage'
import Layout from './components/Layout'
import { getMe } from './services/api'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-primary, #f2f2f7)' }}>
          <div className="text-center p-8 rounded-2xl" style={{ background: 'var(--bg-secondary, #fff)', maxWidth: 400 }}>
            <div className="w-14 h-14 rounded-xl flex items-center justify-center font-black text-xl mx-auto mb-4"
              style={{ background: '#fdd200', color: '#1d1d1f' }}>!</div>
            <h2 className="text-lg font-bold mb-2" style={{ color: 'var(--text-primary, #1d1d1f)' }}>Algo deu errado</h2>
            <p className="text-sm mb-4" style={{ color: 'var(--text-secondary, #636366)' }}>
              Ocorreu um erro inesperado. Tente recarregar a pagina.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 rounded-lg font-semibold text-sm"
              style={{ background: '#fdd200', color: '#1d1d1f' }}>
              Recarregar
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const validateSession = async () => {
      const token = localStorage.getItem('carbon_token')
      const saved = localStorage.getItem('carbon_user')
      if (token && saved) {
        try {
          const { data } = await getMe()
          setUser(data)
          localStorage.setItem('carbon_user', JSON.stringify(data))
        } catch {
          localStorage.removeItem('carbon_token')
          localStorage.removeItem('carbon_user')
        }
      }
      setLoading(false)
    }
    validateSession()
  }, [])

  const handleLogin = (userData, token) => {
    localStorage.setItem('carbon_token', token)
    localStorage.setItem('carbon_user', JSON.stringify(userData))
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('carbon_token')
    localStorage.removeItem('carbon_user')
    setUser(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-primary, #f2f2f7)' }}>
        <div className="text-center">
          <div className="w-14 h-14 rounded-xl flex items-center justify-center font-black text-xl mx-auto mb-4 animate-pulse"
            style={{ background: '#fdd200', color: '#1d1d1f' }}>C</div>
          <p className="text-sm" style={{ color: 'var(--text-tertiary, #8e8e93)' }}>Carregando...</p>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <ToastProvider>
          {!user ? <LoginPage onLogin={handleLogin} /> : <Layout user={user} onLogout={handleLogout} />}
        </ToastProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}
```

**Step 3: Rewrite Layout.jsx with React Router**

Replace `frontend/src/components/Layout.jsx` entirely:

```jsx
import React, { useState, useEffect, Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import TicketsPage from '../pages/TicketsPage'
import TicketDetailPage from '../pages/TicketDetailPage'
import { getTicketCounts } from '../services/api'
import { SkeletonDashboard } from './Skeleton'

const KBPage = lazy(() => import('../pages/KBPage'))
const IntegrationsPage = lazy(() => import('../pages/IntegrationsPage'))
const ReportsPage = lazy(() => import('../pages/ReportsPage'))
const SettingsPage = lazy(() => import('../pages/SettingsPage'))
const TrackingPage = lazy(() => import('../pages/TrackingPage'))
const AssistantPage = lazy(() => import('../pages/AssistantPage'))
const MediaPage = lazy(() => import('../pages/MediaPage'))
const CatalogPage = lazy(() => import('../pages/CatalogPage'))
const LeaderboardPage = lazy(() => import('../pages/LeaderboardPage'))
const ModerationPage = lazy(() => import('../pages/ModerationPage'))
const CanaisIAPage = lazy(() => import('../pages/CanaisIAPage'))
const DashboardPage = lazy(() => import('../pages/DashboardPage'))

const AUTO_REFRESH_MS = 30_000

export default function Layout({ user, onLogout }) {
  const [ticketCount, setTicketCount] = useState(0)
  const [metaCount, setMetaCount] = useState(0)

  useEffect(() => {
    loadTicketCounts()
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        loadTicketCounts()
      }
    }, AUTO_REFRESH_MS)
    return () => clearInterval(interval)
  }, [])

  const loadTicketCounts = async () => {
    try {
      const { data } = await getTicketCounts()
      setTicketCount(data.mine)
      setMetaCount(data.meta_channels || 0)
    } catch (e) {
      console.error('Failed to load ticket counts', e)
    }
  }

  return (
    <div className="flex h-screen" style={{ background: 'var(--bg-primary)' }}>
      <Sidebar
        user={user}
        onLogout={onLogout}
        ticketCount={ticketCount}
        metaCount={metaCount}
      />
      <main className="flex-1 overflow-auto" style={{ background: 'var(--bg-primary)' }}>
        <Suspense fallback={<SkeletonDashboard />}>
          <Routes>
            <Route path="/dashboard" element={<DashboardPage user={user} />} />
            <Route path="/tickets" element={<TicketsPage user={user} />} />
            <Route path="/tickets/:id" element={<TicketDetailPage user={user} />} />
            <Route path="/kb" element={<KBPage />} />
            <Route path="/assistant" element={<AssistantPage user={user} />} />
            <Route path="/media" element={<MediaPage />} />
            <Route path="/catalog" element={<CatalogPage />} />
            <Route path="/leaderboard" element={<LeaderboardPage user={user} />} />
            <Route path="/tracking" element={<TrackingPage />} />
            <Route path="/canais-ia" element={<CanaisIAPage user={user} />} />
            <Route path="/moderation" element={<ModerationPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/integrations" element={<IntegrationsPage />} />
            <Route path="/settings" element={<SettingsPage user={user} />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
```

**Step 4: Rewrite Sidebar.jsx with NavLink**

Replace `frontend/src/components/Sidebar.jsx` entirely:

```jsx
import React from 'react'
import { NavLink } from 'react-router-dom'

const ROLE_LABELS = {
  super_admin: 'Super Admin', admin: 'Administrador', supervisor: 'Supervisor', agent: 'Agente',
}

const NAV_GROUPS = [
  {
    label: 'Atendimento',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: 'fa-chart-line', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/tickets', label: 'Caixa de Entrada', icon: 'fa-inbox', roles: ['super_admin', 'admin', 'supervisor', 'agent'], badge: 'tickets' },
      { to: '/canais-ia', label: 'Canais IA', icon: 'fa-comments', roles: ['super_admin', 'admin', 'supervisor'], badge: 'meta' },
      { to: '/tracking', label: 'Rastreamento', icon: 'fa-truck-fast', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
    ],
  },
  {
    label: 'Ferramentas',
    items: [
      { to: '/assistant', label: 'Assistente IA', icon: 'fa-robot', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/kb', label: 'Base de Conhecimento', icon: 'fa-book', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/media', label: 'Biblioteca de Midia', icon: 'fa-photo-video', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/catalog', label: 'Catalogo', icon: 'fa-box-open', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/moderation', label: 'Moderacao Social', icon: 'fa-shield-alt', roles: ['super_admin', 'admin', 'supervisor'] },
    ],
  },
  {
    label: 'Gestao',
    items: [
      { to: '/leaderboard', label: 'Performance', icon: 'fa-gamepad', roles: ['super_admin', 'admin', 'supervisor'] },
      { to: '/reports', label: 'Relatorios', icon: 'fa-chart-bar', roles: ['super_admin', 'admin', 'supervisor'] },
      { to: '/integrations', label: 'Integracoes', icon: 'fa-plug', roles: ['super_admin'] },
      { to: '/settings', label: 'Configuracoes', icon: 'fa-cog', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
    ],
  },
]

export default function Sidebar({ user, onLogout, ticketCount, metaCount }) {
  const userRole = user?.role || 'agent'

  return (
    <div className="w-60 shrink-0 flex flex-col h-full"
      style={{ background: '#1d1d1f', borderRight: '1px solid rgba(255,255,255,0.06)' }}>
      {/* Logo */}
      <div className="px-4 py-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <img src="/assets/carbon-logo.svg" alt="Carbon Expert Hub" className="h-8" />
      </div>

      {/* Nav */}
      <nav className="px-3 py-3 flex-1 overflow-auto">
        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter(item => item.roles.includes(userRole))
          if (visibleItems.length === 0) return null
          return (
            <div key={group.label} className="mb-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider px-3 mb-2" style={{ color: '#636366' }}>
                {group.label}
              </p>
              <div className="space-y-0.5">
                {visibleItems.map(item => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className="w-full flex items-center justify-between gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all"
                    style={({ isActive }) => ({
                      background: isActive ? 'rgba(253,210,0,0.12)' : 'transparent',
                      color: isActive ? '#fdd200' : '#8e8e93',
                    })}
                    onMouseEnter={e => {
                      if (!e.currentTarget.classList.contains('active')) {
                        e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
                        e.currentTarget.style.color = '#f5f5f7'
                      }
                    }}
                    onMouseLeave={e => {
                      if (!e.currentTarget.classList.contains('active')) {
                        // Let NavLink re-render handle the style
                        const isActive = e.currentTarget.getAttribute('aria-current') === 'page'
                        e.currentTarget.style.background = isActive ? 'rgba(253,210,0,0.12)' : 'transparent'
                        e.currentTarget.style.color = isActive ? '#fdd200' : '#8e8e93'
                      }
                    }}
                  >
                    <span className="flex items-center gap-2.5">
                      <i className={`fas ${item.icon} w-4 text-center text-xs`} />
                      {item.label}
                    </span>
                    {item.badge === 'tickets' && ticketCount > 0 && (
                      <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold"
                        style={{ background: '#fdd200', color: '#1d1d1f' }}>
                        {ticketCount}
                      </span>
                    )}
                    {item.badge === 'meta' && metaCount > 0 && (
                      <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold"
                        style={{ background: '#25D366', color: '#fff' }}>
                        {metaCount}
                      </span>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          )
        })}
      </nav>

      {/* User */}
      <div className="px-3 py-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              style={{ background: '#fdd200', color: '#1d1d1f' }}>
              {user.name[0]}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: '#f5f5f7' }}>{user.name}</p>
              <p className="text-[11px] truncate" style={{ color: '#636366' }}>{ROLE_LABELS[user.role] || user.role}</p>
            </div>
          </div>
          <button onClick={onLogout}
            className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors text-xs"
            style={{ color: '#636366' }}
            onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
            onMouseLeave={e => e.currentTarget.style.color = '#636366'}
            title="Sair">
            <i className="fas fa-sign-out-alt" />
          </button>
        </div>
      </div>
    </div>
  )
}
```

**Step 5: Update DashboardPage.jsx — use useNavigate**

At the top of DashboardPage.jsx, add:
```jsx
import { useNavigate } from 'react-router-dom'
```

Inside the component, replace:
```jsx
const goToTickets = (filters = {}) => {
    if (onNavigate) onNavigate('tickets', filters)
  }
```
With:
```jsx
const navigate = useNavigate()
const goToTickets = (filters = {}) => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v) })
    navigate(`/tickets${params.toString() ? '?' + params.toString() : ''}`)
  }
```

Remove `onNavigate` from the props destructuring — change `{ user, onNavigate }` to `{ user }`.

**Step 6: Update TicketsPage.jsx — use useNavigate, useSearchParams**

At the top, add:
```jsx
import { useNavigate, useSearchParams } from 'react-router-dom'
```

Inside the component:
- Remove `filters` and `onOpenTicket` from props — change `{ filters, onOpenTicket, user }` to `{ user }`
- Add after `const toast = useToast()`:
```jsx
const navigate = useNavigate()
const [searchParams] = useSearchParams()
const filters = Object.fromEntries(searchParams.entries())
const onOpenTicket = (id) => navigate(`/tickets/${id}`)
```

**Step 7: Update TicketDetailPage.jsx — use useParams, useNavigate**

At the top, add:
```jsx
import { useParams, useNavigate } from 'react-router-dom'
```

Inside the component:
- Remove `ticketId`, `onBack`, `onOpenTicket` from props — change `{ ticketId, onBack, onOpenTicket, user }` to `{ user }`
- Add after `const toast = useToast()`:
```jsx
const { id } = useParams()
const ticketId = parseInt(id)
const navigate = useNavigate()
const onBack = () => navigate('/tickets')
const onOpenTicket = (id) => navigate(`/tickets/${id}`)
```

**Step 8: Update TrackingPage.jsx and CanaisIAPage.jsx**

In both files, replace `onOpenTicket` prop usage:

Add at top:
```jsx
import { useNavigate } from 'react-router-dom'
```

Inside the component, add:
```jsx
const navigate = useNavigate()
const onOpenTicket = (id) => navigate(`/tickets/${id}`)
```

Remove `onOpenTicket` from props destructuring.

**Step 9: Update api.js 401 redirect**

In `frontend/src/services/api.js`, the 401 handler already redirects to `/`. This works fine since react-router will redirect `/` to `/dashboard`. No change needed.

**Step 10: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 11: Commit**

```bash
git add frontend/src/
git commit -m "feat: add URL routing with react-router-dom

Routes: /dashboard, /tickets, /tickets/:id, /kb, /assistant, /media,
/catalog, /leaderboard, /tracking, /canais-ia, /moderation, /reports,
/integrations, /settings. Browser back/forward works. Links shareable."
```

---

### Task 4: Sidebar Hover Fix (CSS-based)

The Sidebar uses inline onMouseEnter/onMouseLeave which conflicts with NavLink's isActive styling. Fix by using CSS classes instead.

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/index.css`

**Step 1: Add sidebar nav styles to index.css**

Add at end of index.css:

```css
/* ═══ Sidebar Nav Items ═══ */
.sidebar-nav-item {
  transition: background 0.15s ease, color 0.15s ease;
}
.sidebar-nav-item:not(.sidebar-nav-active):hover {
  background: rgba(255,255,255,0.06);
  color: #f5f5f7;
}
.sidebar-nav-active {
  background: rgba(253,210,0,0.12);
  color: #fdd200;
}
```

**Step 2: Simplify Sidebar NavLink**

In Sidebar.jsx, replace the NavLink element (remove onMouseEnter/onMouseLeave) with:

```jsx
<NavLink
  key={item.to}
  to={item.to}
  className={({ isActive }) =>
    `sidebar-nav-item w-full flex items-center justify-between gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium ${isActive ? 'sidebar-nav-active' : ''}`
  }
  style={{ color: undefined }}
>
```

Remove the `style` prop and the `onMouseEnter`/`onMouseLeave` handlers entirely. The default color for non-active items:

Add to index.css:
```css
.sidebar-nav-item {
  color: #8e8e93;
  transition: background 0.15s ease, color 0.15s ease;
}
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`

**Step 4: Commit**

```bash
git add frontend/src/components/Sidebar.jsx frontend/src/index.css
git commit -m "fix: use CSS classes for sidebar hover instead of inline handlers"
```

---

### Task 5: Command Palette (Cmd+K)

**Files:**
- Create: `frontend/src/components/CommandPalette.jsx`
- Modify: `frontend/src/components/Layout.jsx`

**Step 1: Create CommandPalette component**

Create `frontend/src/components/CommandPalette.jsx`:

```jsx
import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTickets } from '../services/api'

const PAGES = [
  { label: 'Dashboard', icon: 'fa-chart-line', path: '/dashboard' },
  { label: 'Caixa de Entrada', icon: 'fa-inbox', path: '/tickets' },
  { label: 'Canais IA', icon: 'fa-comments', path: '/canais-ia' },
  { label: 'Rastreamento', icon: 'fa-truck-fast', path: '/tracking' },
  { label: 'Assistente IA', icon: 'fa-robot', path: '/assistant' },
  { label: 'Base de Conhecimento', icon: 'fa-book', path: '/kb' },
  { label: 'Biblioteca de Midia', icon: 'fa-photo-video', path: '/media' },
  { label: 'Catalogo', icon: 'fa-box-open', path: '/catalog' },
  { label: 'Moderacao Social', icon: 'fa-shield-alt', path: '/moderation' },
  { label: 'Performance', icon: 'fa-gamepad', path: '/leaderboard' },
  { label: 'Relatorios', icon: 'fa-chart-bar', path: '/reports' },
  { label: 'Integracoes', icon: 'fa-plug', path: '/integrations' },
  { label: 'Configuracoes', icon: 'fa-cog', path: '/settings' },
]

const ACTIONS = [
  { label: 'Novo E-mail', icon: 'fa-pen-to-square', action: 'compose' },
  { label: 'Exportar CSV', icon: 'fa-file-csv', action: 'export' },
  { label: 'Atribuicao automatica', icon: 'fa-magic', action: 'auto-assign' },
]

const STATUS_LABELS = {
  open: 'Aberto', in_progress: 'Andamento', waiting: 'Aguardando',
  resolved: 'Resolvido', escalated: 'Escalado', closed: 'Fechado',
}

export default function CommandPalette({ onAction }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [tickets, setTickets] = useState([])
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef(null)
  const debounceRef = useRef(null)
  const navigate = useNavigate()

  // Listen for Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen(prev => !prev)
      }
      if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open])

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery('')
      setTickets([])
      setSelectedIdx(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  // Search tickets with debounce
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!query || query.length < 2) { setTickets([]); return }

    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const { data } = await getTickets({ search: query, limit: 5 })
        setTickets(data.tickets || [])
      } catch { setTickets([]) }
      finally { setLoading(false) }
    }, 200)

    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [query])

  // Build results
  const q = query.toLowerCase()
  const filteredPages = q ? PAGES.filter(p => p.label.toLowerCase().includes(q)) : []
  const filteredActions = q ? ACTIONS.filter(a => a.label.toLowerCase().includes(q)) : []

  const allResults = [
    ...tickets.map(t => ({ type: 'ticket', data: t })),
    ...filteredPages.map(p => ({ type: 'page', data: p })),
    ...filteredActions.map(a => ({ type: 'action', data: a })),
  ]

  // Show pages when empty query
  const displayResults = q ? allResults : PAGES.map(p => ({ type: 'page', data: p }))

  // Reset selection when results change
  useEffect(() => { setSelectedIdx(0) }, [query, tickets.length])

  const handleSelect = useCallback((item) => {
    setOpen(false)
    if (item.type === 'ticket') {
      navigate(`/tickets/${item.data.id}`)
    } else if (item.type === 'page') {
      navigate(item.data.path)
    } else if (item.type === 'action') {
      onAction?.(item.data.action)
    }
  }, [navigate, onAction])

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIdx(i => Math.min(i + 1, displayResults.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIdx(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && displayResults.length > 0) {
      e.preventDefault()
      handleSelect(displayResults[selectedIdx])
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[9998] flex items-start justify-center pt-[15vh]"
      onClick={() => setOpen(false)}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 rounded-2xl overflow-hidden"
        style={{
          background: 'rgba(255,255,255,0.92)',
          backdropFilter: 'blur(20px) saturate(180%)',
          border: '1px solid rgba(0,0,0,0.08)',
          boxShadow: '0 25px 60px rgba(0,0,0,0.15), 0 8px 20px rgba(0,0,0,0.08)',
        }}
        onClick={e => e.stopPropagation()}>

        {/* Search input */}
        <div className="flex items-center gap-3 px-5 py-4 border-b" style={{ borderColor: 'rgba(0,0,0,0.06)' }}>
          <i className="fas fa-search text-sm" style={{ color: 'var(--text-tertiary)' }} />
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar tickets, paginas, acoes..."
            className="flex-1 bg-transparent text-[15px] outline-none placeholder:text-[var(--text-tertiary)]"
            style={{ color: 'var(--text-primary)' }}
          />
          {loading && <i className="fas fa-spinner fa-spin text-xs" style={{ color: 'var(--text-tertiary)' }} />}
          <kbd className="text-[10px] px-1.5 py-0.5 rounded font-medium"
            style={{ background: 'rgba(0,0,0,0.05)', color: 'var(--text-tertiary)' }}>
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[360px] overflow-y-auto py-2">
          {displayResults.length === 0 && query && !loading && (
            <div className="px-5 py-8 text-center">
              <i className="fas fa-search text-2xl mb-2" style={{ color: 'var(--text-tertiary)', opacity: 0.4 }} />
              <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Nenhum resultado para "{query}"</p>
            </div>
          )}

          {/* Tickets section */}
          {tickets.length > 0 && (
            <div className="mb-1">
              <p className="px-5 py-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Tickets
              </p>
              {tickets.map((t, i) => {
                const idx = i
                return (
                  <button key={t.id} onClick={() => handleSelect({ type: 'ticket', data: t })}
                    className="w-full flex items-center gap-3 px-5 py-2.5 transition-colors"
                    style={{
                      background: selectedIdx === idx ? 'rgba(253,210,0,0.08)' : 'transparent',
                    }}
                    onMouseEnter={() => setSelectedIdx(idx)}>
                    <i className="fas fa-ticket text-xs" style={{ color: 'var(--accent-muted)' }} />
                    <div className="flex-1 min-w-0 text-left">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono-carbon" style={{ color: 'var(--text-tertiary)' }}>#{t.number}</span>
                        <span className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>{t.subject}</span>
                      </div>
                      <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{t.customer?.name}</span>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                      style={{ background: 'rgba(0,0,0,0.04)', color: 'var(--text-secondary)' }}>
                      {STATUS_LABELS[t.status] || t.status}
                    </span>
                  </button>
                )
              })}
            </div>
          )}

          {/* Pages section */}
          {(q ? filteredPages : PAGES).length > 0 && (
            <div className="mb-1">
              <p className="px-5 py-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Paginas
              </p>
              {(q ? filteredPages : PAGES).map((p, i) => {
                const idx = tickets.length + i
                return (
                  <button key={p.path} onClick={() => handleSelect({ type: 'page', data: p })}
                    className="w-full flex items-center gap-3 px-5 py-2.5 transition-colors"
                    style={{
                      background: selectedIdx === idx ? 'rgba(253,210,0,0.08)' : 'transparent',
                    }}
                    onMouseEnter={() => setSelectedIdx(idx)}>
                    <i className={`fas ${p.icon} text-xs w-4 text-center`} style={{ color: 'var(--text-tertiary)' }} />
                    <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{p.label}</span>
                  </button>
                )
              })}
            </div>
          )}

          {/* Actions section */}
          {filteredActions.length > 0 && (
            <div>
              <p className="px-5 py-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Acoes
              </p>
              {filteredActions.map((a, i) => {
                const idx = tickets.length + filteredPages.length + i
                return (
                  <button key={a.action} onClick={() => handleSelect({ type: 'action', data: a })}
                    className="w-full flex items-center gap-3 px-5 py-2.5 transition-colors"
                    style={{
                      background: selectedIdx === idx ? 'rgba(253,210,0,0.08)' : 'transparent',
                    }}
                    onMouseEnter={() => setSelectedIdx(idx)}>
                    <i className={`fas ${a.icon} text-xs w-4 text-center`} style={{ color: 'var(--accent-muted)' }} />
                    <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{a.label}</span>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer hint */}
        <div className="flex items-center gap-4 px-5 py-2.5 border-t" style={{ borderColor: 'rgba(0,0,0,0.06)' }}>
          <span className="text-[10px] flex items-center gap-1" style={{ color: 'var(--text-tertiary)' }}>
            <kbd className="px-1 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.05)' }}>↑↓</kbd> navegar
          </span>
          <span className="text-[10px] flex items-center gap-1" style={{ color: 'var(--text-tertiary)' }}>
            <kbd className="px-1 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.05)' }}>Enter</kbd> selecionar
          </span>
          <span className="text-[10px] flex items-center gap-1" style={{ color: 'var(--text-tertiary)' }}>
            <kbd className="px-1 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.05)' }}>Esc</kbd> fechar
          </span>
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Mount CommandPalette in Layout.jsx**

In `frontend/src/components/Layout.jsx`, add import at top:
```jsx
import CommandPalette from './CommandPalette'
```

Add `<CommandPalette />` right after the opening `<div className="flex h-screen" ...>`:
```jsx
<CommandPalette />
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`

**Step 4: Commit**

```bash
git add frontend/src/components/CommandPalette.jsx frontend/src/components/Layout.jsx
git commit -m "feat: add Cmd+K command palette for global search and navigation"
```

---

### Task 6: Dashboard Simplification

**Files:**
- Modify: `frontend/src/pages/DashboardPage.jsx`

**Step 1: Add collapsible section state and hero row to AdminDashboard**

In the AdminDashboard function, add at the top:
```jsx
const [showSecondaryKPIs, setShowSecondaryKPIs] = useState(false)
const [showSecondaryCharts, setShowSecondaryCharts] = useState(false)
```

Replace the existing 3 KPI grids (lines ~164-187 in current file) with:

**Hero Row** (4 cards, larger):
```jsx
{/* Hero KPIs */}
<div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
  <KPICard label="Abertos" value={stats.open_tickets} icon="fa-folder-open" color="blue" size="hero" onClick={() => goToTickets({ status: 'open' })} />
  <KPICard label="SLA Cumprido" value={`${stats.sla_compliance}%`} icon="fa-clock" color="green" size="hero" />
  <KPICard label="Tempo Resposta" value={`${stats.avg_response_hours}h`} icon="fa-reply" color="blue" size="hero" />
  <KPICard label="Risco Juridico" value={stats.legal_risk_count} icon="fa-gavel" color="red" size="hero" onClick={() => goToTickets({ legal_risk: 'true' })} />
</div>
```

**Secondary KPIs** (collapsible):
```jsx
{/* Secondary KPIs */}
<div className="mb-6">
  <button onClick={() => setShowSecondaryKPIs(!showSecondaryKPIs)}
    className="flex items-center gap-2 text-xs font-medium mb-3 transition"
    style={{ color: 'var(--text-tertiary)' }}>
    <i className={`fas fa-chevron-${showSecondaryKPIs ? 'up' : 'down'} text-[10px]`} />
    {showSecondaryKPIs ? 'Menos metricas' : 'Mais metricas'}
  </button>
  {showSecondaryKPIs && (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <KPICard label="Total Tickets" value={stats.total_tickets} icon="fa-ticket" color="accent" onClick={() => goToTickets({})} />
      <KPICard label="Trocas" value={stats.trocas_count} icon="fa-rotate" color="yellow" onClick={() => goToTickets({ category: 'troca' })} />
      <KPICard label="Reclamacoes" value={stats.reclamacoes_count} icon="fa-face-angry" color="red" onClick={() => goToTickets({ category: 'reclamacao' })} />
      <KPICard label="Escalados" value={stats.escalated_count} icon="fa-arrow-up" color="red" onClick={() => goToTickets({ status: 'escalated' })} />
      <KPICard label="FCR" value={`${stats.fcr_rate || 0}%`} icon="fa-bullseye" color="green" />
      <KPICard label="Nao Atribuidos" value={stats.unassigned_count || 0} icon="fa-user-slash" color="orange" onClick={() => goToTickets({ assigned_to: 'none' })} />
      <KPICard label="Resolvidos Hoje" value={stats.resolved_today} icon="fa-check-circle" color="green" onClick={() => goToTickets({ status: 'resolved' })} />
      <KPICard label="Respondidos Hoje" value={stats.responded_today || 0} icon="fa-paper-plane" color="blue" />
      <KPICard label="Tempo Resolucao" value={`${stats.avg_resolution_hours}h`} icon="fa-check-double" color="purple" />
      <KPICard label="SLA Quebrados" value={stats.sla_breached} icon="fa-exclamation-triangle" color="red" onClick={() => goToTickets({ sla_breached: 'true' })} />
      <KPICard label="Problemas" value={stats.problemas_count} icon="fa-triangle-exclamation" color="orange" onClick={() => goToTickets({ category: 'garantia' })} />
      <KPICard label="Resolv. 1a Resp" value={stats.fcr_count || 0} icon="fa-bullseye" color="green" />
    </div>
  )}
</div>
```

Keep the first 2 charts (Volume + Categoria). Wrap the remaining 4 in collapsible:
```jsx
{/* Secondary Charts */}
<div className="mb-6">
  <button onClick={() => setShowSecondaryCharts(!showSecondaryCharts)}
    className="flex items-center gap-2 text-xs font-medium mb-3 transition"
    style={{ color: 'var(--text-tertiary)' }}>
    <i className={`fas fa-chevron-${showSecondaryCharts ? 'up' : 'down'} text-[10px]`} />
    {showSecondaryCharts ? 'Menos graficos' : 'Mais graficos'}
  </button>
  {showSecondaryCharts && (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Status, Priority, Channel, Sentiment charts here */}
    </div>
  )}
</div>
```

**Step 2: Update KPICard to support hero size**

Add `size` prop to KPICard:
```jsx
function KPICard({ label, value, icon, color, onClick, size }) {
  const c = KPI_COLORS[color] || KPI_COLORS.accent
  const Wrapper = onClick ? 'button' : 'div'
  const isHero = size === 'hero'

  return (
    <Wrapper
      onClick={onClick}
      className={`rounded-xl text-left transition border ${isHero ? 'p-5' : 'p-4'}`}
      style={{
        background: 'var(--bg-secondary)',
        borderColor: 'var(--border-color)',
      }}
      onMouseEnter={e => { if (onClick) { e.currentTarget.style.borderColor = 'var(--border-hover)'; e.currentTarget.style.boxShadow = 'var(--shadow-sm)' }}}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.boxShadow = 'none' }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</span>
        <div className={`${isHero ? 'w-10 h-10' : 'w-8 h-8'} rounded-lg flex items-center justify-center`}
          style={{ background: c.bg, color: c.text }}>
          <i className={`fas ${icon} ${isHero ? 'text-base' : 'text-sm'}`} />
        </div>
      </div>
      <p className={`${isHero ? 'text-3xl' : 'text-2xl'} font-bold`} style={{ color: 'var(--text-primary)' }}>{value}</p>
      {onClick && <p className="text-[10px] mt-1" style={{ color: 'var(--text-tertiary)' }}>clique para ver <i className="fas fa-arrow-right" /></p>}
    </Wrapper>
  )
}
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`

**Step 4: Commit**

```bash
git add frontend/src/pages/DashboardPage.jsx
git commit -m "feat: simplify dashboard with hero KPIs and collapsible sections"
```

---

### Task 7: Ticket List Preview + Sticky Headers

**Files:**
- Modify: `frontend/src/pages/TicketsPage.jsx`
- Modify: `frontend/src/index.css`

**Step 1: Add sticky header CSS to index.css**

```css
/* ═══ Sticky Table Headers ═══ */
.sticky-header th {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg-secondary);
  box-shadow: 0 1px 0 var(--border-color);
}
```

**Step 2: Add last message preview to ticket rows**

In TicketsPage.jsx, find the ticket table row where the subject is rendered. Below the subject `<td>`, add a snippet of the last message. The ticket object from API includes `last_message_preview` or `messages`. We'll use `last_message_at` and add a computed preview.

In the ticket row, after the subject text, add:
```jsx
{t.last_message_preview && (
  <p className="text-xs mt-0.5 truncate max-w-[400px]" style={{ color: 'var(--text-tertiary)' }}>
    {t.last_message_preview.substring(0, 80)}
  </p>
)}
```

**Step 3: Add "needs action" indicator**

After the SLA column, add a small dot indicator if the last message type is 'inbound' (client responded):
```jsx
{t.last_message_type === 'inbound' && (
  <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" title="Cliente respondeu" />
)}
```

**Step 4: Add time since last response**

Add a helper function at the top of the file:
```jsx
function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  return `${days}d`
}
```

Use it in the row near the SLA column:
```jsx
<span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
  {timeAgo(t.last_message_at)}
</span>
```

**Step 5: Add `sticky-header` class to the table thead**

Find the `<thead>` in the ticket table and add the class:
```jsx
<thead className="sticky-header">
```

**Step 6: Integrate SkeletonTicketList**

At the top of TicketsPage.jsx, add:
```jsx
import { SkeletonTicketList } from '../components/Skeleton'
```

Replace the existing loading spinner in the inbox view with:
```jsx
{loading ? <SkeletonTicketList /> : (
  // existing ticket table
)}
```

Note: You'll need to add a `loading` state — the current code doesn't have one for the main ticket list. Add `const [loading, setLoading] = useState(true)` and set it in `loadTickets`:
```jsx
const loadTickets = async () => {
  setLoading(true)
  try {
    // existing code
  } catch (e) {
    toast.error('Falha ao carregar tickets')
  } finally {
    setLoading(false)
  }
}
```

**Step 7: Verify build**

Run: `cd frontend && npm run build`

**Step 8: Commit**

```bash
git add frontend/src/pages/TicketsPage.jsx frontend/src/index.css
git commit -m "feat: add ticket preview, needs-action indicator, sticky headers, skeleton loading"
```

---

### Task 8: Keyboard Shortcuts Overlay

**Files:**
- Create: `frontend/src/components/KeyboardShortcutsModal.jsx`
- Modify: `frontend/src/components/Layout.jsx`

**Step 1: Create KeyboardShortcutsModal component**

Create `frontend/src/components/KeyboardShortcutsModal.jsx`:

```jsx
import React, { useState, useEffect } from 'react'

const SHORTCUT_GROUPS = [
  {
    label: 'Navegacao',
    shortcuts: [
      { keys: ['⌘', 'K'], desc: 'Command palette' },
      { keys: ['?'], desc: 'Este painel' },
      { keys: ['G', 'D'], desc: 'Ir pro Dashboard' },
      { keys: ['G', 'T'], desc: 'Ir pros Tickets' },
      { keys: ['G', 'K'], desc: 'Ir pra Base de Conhecimento' },
    ],
  },
  {
    label: 'Lista de Tickets',
    shortcuts: [
      { keys: ['J'], desc: 'Proximo ticket' },
      { keys: ['K'], desc: 'Ticket anterior' },
      { keys: ['X'], desc: 'Selecionar ticket' },
      { keys: ['Enter'], desc: 'Abrir ticket' },
    ],
  },
  {
    label: 'Dentro do Ticket',
    shortcuts: [
      { keys: ['Alt', 'R'], desc: 'Resolver' },
      { keys: ['Alt', 'E'], desc: 'Escalar' },
      { keys: ['Alt', 'W'], desc: 'Aguardando' },
      { keys: ['Alt', 'N'], desc: 'Proximo ticket' },
      { keys: ['Alt', 'S'], desc: 'Sugestao IA' },
      { keys: ['Alt', 'F'], desc: 'Focar resposta' },
      { keys: ['⌘', 'Enter'], desc: 'Enviar mensagem' },
      { keys: ['/'], desc: 'Buscar macros' },
    ],
  },
  {
    label: 'Geral',
    shortcuts: [
      { keys: ['Esc'], desc: 'Fechar modal' },
    ],
  },
]

export default function KeyboardShortcutsModal() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
      if (e.key === '?' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault()
        setOpen(prev => !prev)
      }
      if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[9997] flex items-center justify-center"
      onClick={() => setOpen(false)}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative w-full max-w-2xl mx-4 rounded-2xl overflow-hidden"
        style={{
          background: 'rgba(255,255,255,0.95)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(0,0,0,0.08)',
          boxShadow: '0 25px 60px rgba(0,0,0,0.15)',
        }}
        onClick={e => e.stopPropagation()}>

        <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'rgba(0,0,0,0.06)' }}>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            <i className="fas fa-keyboard mr-2" style={{ color: 'var(--accent)' }} />
            Atalhos de Teclado
          </h2>
          <button onClick={() => setOpen(false)} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition">
            <i className="fas fa-times" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-6 p-6">
          {SHORTCUT_GROUPS.map(group => (
            <div key={group.label}>
              <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>
                {group.label}
              </h3>
              <div className="space-y-2">
                {group.shortcuts.map((s, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{s.desc}</span>
                    <div className="flex items-center gap-1">
                      {s.keys.map((key, j) => (
                        <React.Fragment key={j}>
                          {j > 0 && <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>+</span>}
                          <kbd className="text-[11px] px-1.5 py-0.5 rounded font-medium min-w-[24px] text-center"
                            style={{
                              background: 'rgba(0,0,0,0.06)',
                              color: 'var(--text-primary)',
                              border: '1px solid rgba(0,0,0,0.08)',
                            }}>
                            {key}
                          </kbd>
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="px-6 py-3 border-t text-center" style={{ borderColor: 'rgba(0,0,0,0.06)' }}>
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            Pressione <kbd className="px-1 py-0.5 rounded text-[10px]" style={{ background: 'rgba(0,0,0,0.05)' }}>?</kbd> para abrir/fechar
          </p>
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Mount in Layout.jsx**

Add import:
```jsx
import KeyboardShortcutsModal from './KeyboardShortcutsModal'
```

Add `<KeyboardShortcutsModal />` next to `<CommandPalette />` in the Layout return.

**Step 3: Add G-key navigation shortcuts in Layout.jsx**

Add a useEffect in Layout for "go to" shortcuts:

```jsx
import { useNavigate } from 'react-router-dom'

// Inside the Layout component:
const navigate = useNavigate()

useEffect(() => {
  let gPending = false
  let gTimer = null

  const handleKeyDown = (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
    if (e.metaKey || e.ctrlKey || e.altKey) return

    if (gPending) {
      gPending = false
      clearTimeout(gTimer)
      if (e.key === 'd') { e.preventDefault(); navigate('/dashboard') }
      else if (e.key === 't') { e.preventDefault(); navigate('/tickets') }
      else if (e.key === 'k') { e.preventDefault(); navigate('/kb') }
      return
    }

    if (e.key === 'g') {
      gPending = true
      gTimer = setTimeout(() => { gPending = false }, 500)
    }
  }

  window.addEventListener('keydown', handleKeyDown)
  return () => {
    window.removeEventListener('keydown', handleKeyDown)
    if (gTimer) clearTimeout(gTimer)
  }
}, [navigate])
```

**Step 4: Verify build**

Run: `cd frontend && npm run build`

**Step 5: Commit**

```bash
git add frontend/src/components/KeyboardShortcutsModal.jsx frontend/src/components/Layout.jsx
git commit -m "feat: add keyboard shortcuts overlay (?) and G-key navigation"
```

---

### Task 9: Final Polish — Vite SPA Fallback + Build Verification

**Files:**
- Modify: `frontend/vite.config.js` (dev SPA fallback for react-router)

**Step 1: Verify vite handles SPA routing in dev**

Vite's dev server already handles SPA fallback by default when using `appType: 'spa'` (the default). For production (nginx), a catch-all rule is needed. Check the nginx config:

If `frontend/vite.config.js` doesn't have explicit SPA handling, it should work in dev. For production nginx, add to the nginx config (not frontend code):

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

This is already standard for SPA deploys. If the existing nginx config at `nginx/` doesn't have this, add it.

**Step 2: Full build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds with all chunks.

**Step 3: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: final build verification for frontend UX overhaul"
```

---

## Summary of Changes

| Task | What | Files |
|------|------|-------|
| 1 | DM Sans + JetBrains Mono typography | index.html, index.css |
| 2 | Skeleton loading components | Skeleton.jsx, index.css |
| 3 | URL routing with react-router-dom | main.jsx, App.jsx, Layout.jsx, Sidebar.jsx, TicketsPage, TicketDetailPage, DashboardPage, TrackingPage, CanaisIAPage |
| 4 | Sidebar CSS hover fix | Sidebar.jsx, index.css |
| 5 | Cmd+K command palette | CommandPalette.jsx, Layout.jsx |
| 6 | Dashboard hero KPIs + collapsibles | DashboardPage.jsx |
| 7 | Ticket preview + sticky headers + skeleton | TicketsPage.jsx, index.css |
| 8 | Keyboard shortcuts overlay + G-nav | KeyboardShortcutsModal.jsx, Layout.jsx |
| 9 | SPA fallback + final build | vite.config.js, nginx |
