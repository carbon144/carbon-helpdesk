import React, { useState, useEffect, useRef } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { getTicketCounts } from '../services/api'

const ROLE_LABELS = {
  super_admin: 'Super Admin', admin: 'Administrador', supervisor: 'Supervisor', agent: 'Agente',
}

const NAV_GROUPS = [
  {
    label: 'Atendimento',
    items: [
      { to: '/tickets', label: 'Caixa de Entrada', icon: 'fa-inbox', roles: ['super_admin', 'admin', 'supervisor', 'agent'], badge: 'tickets' },
      { to: '/chat', label: 'Chat ao Vivo', icon: 'fa-headset', roles: ['super_admin', 'admin', 'supervisor', 'agent'], badge: 'chat' },
      { to: '/tracking', label: 'Rastreamento', icon: 'fa-truck-fast', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/voice-calls', label: 'Ligacoes', icon: 'fa-phone', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
    ],
  },
  {
    label: 'Ferramentas',
    items: [
      { to: '/kb', label: 'Base de Conhecimento', icon: 'fa-book', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/macros', label: 'Respostas Rapidas', icon: 'fa-bolt', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/chatbot-flows', label: 'Chatbot Flows', icon: 'fa-robot', roles: ['super_admin', 'admin', 'supervisor'] },
      // { to: '/moderation', label: 'Moderacao Social', icon: 'fa-shield-alt', roles: ['super_admin', 'admin', 'supervisor'] },
    ],
  },
  {
    label: 'Gestao',
    items: [
      { to: '/metricas', label: 'Metricas', icon: 'fa-chart-line', roles: ['super_admin', 'admin', 'supervisor'] },
      { to: '/triagem', label: 'Triagem', icon: 'fa-filter', roles: ['super_admin', 'admin', 'supervisor'] },
      { to: '/settings', label: 'Configuracoes', icon: 'fa-cog', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
    ],
  },
]

const VIEW_OPTIONS = [
  { key: 'inbox', label: 'Caixa de Entrada', icon: 'fa-inbox' },
  { key: 'sent', label: 'Enviados', icon: 'fa-paper-plane' },
  { key: 'spam', label: 'Spam', icon: 'fa-shield-alt', color: 'text-red-400' },
]

const TAB_OPTIONS = [
  { key: 'mine', label: 'Privado', icon: 'fa-lock', countKey: 'mine', color: 'text-indigo-400' },
  { key: 'team', label: 'Equipe', icon: 'fa-users', countKey: 'team', color: 'text-teal-400' },
  { key: 'active', label: 'Novos', icon: 'fa-inbox', countKey: 'unassigned', color: 'text-orange-400', adminOnly: true },
  { key: 'escalated', label: 'Prioridade', icon: 'fa-exclamation-triangle', countKey: 'escalated', color: 'text-red-400' },
  { key: 'resolved', label: 'Resolvidos', icon: 'fa-check-circle', countKey: 'resolved', color: 'text-green-400' },
  { key: 'closed', label: 'Fechados', icon: 'fa-archive', countKey: 'closed', color: 'text-gray-400' },
  { key: 'all', label: 'Todos', icon: 'fa-list', countKey: 'total_open', color: 'text-blue-400' },
  { key: 'auto_reply', label: 'Auto-Reply IA', icon: 'fa-robot', countKey: 'auto_replied', color: 'text-purple-400' },
]

function TicketsFlyout({ open, onClose, userRole }) {
  const navigate = useNavigate()
  const location = useLocation()
  const flyoutRef = useRef(null)
  const [counts, setCounts] = useState({})
  const [loadingCounts, setLoadingCounts] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoadingCounts(true)
    getTicketCounts()
      .then(res => setCounts(res.data || res))
      .catch(() => {})
      .finally(() => setLoadingCounts(false))
  }, [open])

  useEffect(() => {
    if (!open) return
    const handleMouseDown = (e) => {
      if (flyoutRef.current && !flyoutRef.current.contains(e.target)) onClose()
    }
    const handleEscape = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('mousedown', handleMouseDown)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleMouseDown)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [open, onClose])

  if (!open) return null

  const currentParams = new URLSearchParams(location.search)
  const currentView = currentParams.get('view') || 'inbox'
  const currentTab = currentParams.get('tab') || ''

  const goTo = (view, tab) => {
    const params = new URLSearchParams()
    params.set('view', view)
    if (tab) params.set('tab', tab)
    navigate(`/tickets?${params.toString()}`)
    onClose()
  }

  const visibleTabs = TAB_OPTIONS.filter(t => !t.adminOnly || userRole !== 'agent')

  return (
    <div ref={flyoutRef}
      className="absolute left-full top-0 ml-2 w-56 rounded-xl shadow-2xl border z-50 overflow-hidden"
      style={{
        background: 'linear-gradient(180deg, #1A1D27 0%, #161921 100%)',
        borderColor: 'rgba(255,255,255,0.08)',
      }}>
      {/* Views */}
      <div className="p-2 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <p className="text-[10px] font-bold uppercase tracking-wider px-2 py-1" style={{ color: '#475569' }}>Visualizar</p>
        {VIEW_OPTIONS.map(v => (
          <button key={v.key}
            onClick={() => goTo(v.key, v.key === 'inbox' ? 'mine' : undefined)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors ${
              currentView === v.key && location.pathname === '/tickets'
                ? 'bg-white/[0.08] text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            }`}>
            <i className={`fas ${v.icon} w-4 text-center text-[11px] ${v.color || 'opacity-80'}`} />
            {v.label}
          </button>
        ))}
      </div>

      {/* Inbox Tabs */}
      <div className="p-2">
        <p className="text-[10px] font-bold uppercase tracking-wider px-2 py-1" style={{ color: '#475569' }}>Caixas</p>
        {visibleTabs.map(t => (
          <button key={t.key}
            onClick={() => goTo('inbox', t.key)}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-[13px] font-medium transition-colors ${
              currentView === 'inbox' && currentTab === t.key && location.pathname === '/tickets'
                ? 'bg-white/[0.08] text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            }`}>
            <span className="flex items-center gap-2.5">
              <i className={`fas ${t.icon} w-4 text-center text-[11px] ${t.color}`} />
              {t.label}
            </span>
            {t.countKey && counts[t.countKey] != null && (
              <span className="text-[11px] font-semibold tabular-nums" style={{ color: '#64748B' }}>
                {loadingCounts ? '...' : counts[t.countKey]}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function Sidebar({ user, onLogout, ticketCount, metaCount, chatCount }) {
  const userRole = user?.role || 'agent'
  const location = useLocation()
  const [flyoutOpen, setFlyoutOpen] = useState(false)
  const ticketBtnRef = useRef(null)

  const isTicketsActive = location.pathname.startsWith('/tickets')

  return (
    <div className="w-[248px] shrink-0 flex flex-col h-full"
      style={{
        background: 'linear-gradient(180deg, #0F1117 0%, #161921 50%, #1A1D27 100%)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
      }}>
      {/* Logo */}
      <div className="px-5 py-5 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <img src="/logo-white.png" alt="Carbon Expert Hub" className="h-8" />
        <p className="text-[10px] font-semibold tracking-[0.25em] mt-1 uppercase" style={{ color: 'rgba(255,255,255,0.45)' }}>ExpertHub</p>
      </div>

      {/* Navigation */}
      <nav className="px-3 py-4 flex-1 overflow-auto">
        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter(item => item.roles.includes(userRole))
          if (visibleItems.length === 0) return null
          return (
            <div key={group.label} className="mb-5">
              <p className="text-[10px] font-bold uppercase tracking-[0.08em] px-3 mb-2"
                style={{ color: '#475569' }}>
                {group.label}
              </p>
              <div className="space-y-0.5">
                {visibleItems.map(item => {
                  if (item.to === '/tickets') {
                    return (
                      <div key={item.to} className="relative" ref={ticketBtnRef}>
                        <button
                          onClick={() => setFlyoutOpen(prev => !prev)}
                          className={`sidebar-nav-item w-full flex items-center justify-between gap-2.5 px-3 py-[9px] rounded-lg text-[13px] font-medium ${isTicketsActive ? 'sidebar-nav-active' : ''}`}
                        >
                          <span className="flex items-center gap-3">
                            <i className={`fas ${item.icon} w-4 text-center text-[11px] opacity-80`} />
                            {item.label}
                          </span>
                          <span className="flex items-center gap-1.5">
                            {ticketCount > 0 && (
                              <span className="text-[10px] font-bold px-[7px] py-[2px] rounded-full min-w-[20px] text-center"
                                style={{ background: '#E5A800', color: '#FFFFFF' }}>
                                {ticketCount}
                              </span>
                            )}
                            <i className={`fas fa-chevron-right text-[9px] transition-transform ${flyoutOpen ? 'rotate-90' : ''}`} style={{ color: '#475569' }} />
                          </span>
                        </button>
                        <TicketsFlyout open={flyoutOpen} onClose={() => setFlyoutOpen(false)} userRole={userRole} />
                      </div>
                    )
                  }
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        `sidebar-nav-item w-full flex items-center justify-between gap-2.5 px-3 py-[9px] rounded-lg text-[13px] font-medium ${isActive ? 'sidebar-nav-active' : ''}`
                      }
                    >
                      <span className="flex items-center gap-3">
                        <i className={`fas ${item.icon} w-4 text-center text-[11px] opacity-80`} />
                        {item.label}
                      </span>
                      {item.badge === 'chat' && chatCount > 0 && (
                        <span className="text-[10px] font-bold px-[7px] py-[2px] rounded-full min-w-[20px] text-center"
                          style={{ background: '#3B82F6', color: '#FFFFFF' }}>
                          {chatCount}
                        </span>
                      )}
                      {item.badge === 'meta' && metaCount > 0 && (
                        <span className="text-[10px] font-bold px-[7px] py-[2px] rounded-full min-w-[20px] text-center"
                          style={{ background: '#25D366', color: '#FFFFFF' }}>
                          {metaCount}
                        </span>
                      )}
                    </NavLink>
                  )
                })}
              </div>
            </div>
          )
        })}
      </nav>

      {/* User profile */}
      <div className="px-3 py-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-white/[0.03] transition">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              style={{ background: 'linear-gradient(135deg, #E5A800 0%, #CC9600 100%)', color: '#FFFFFF' }}>
              {(user.name || '?')[0]}
            </div>
            <div className="min-w-0">
              <p className="text-[13px] font-semibold truncate" style={{ color: '#E2E8F0' }}>{user.name}</p>
              <p className="text-[10px] truncate" style={{ color: '#64748B' }}>{ROLE_LABELS[user.role] || user.role}</p>
            </div>
          </div>
          <button onClick={onLogout}
            className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors text-xs"
            style={{ color: '#64748B' }}
            onMouseEnter={e => e.currentTarget.style.color = '#EF4444'}
            onMouseLeave={e => e.currentTarget.style.color = '#64748B'}
            title="Sair">
            <i className="fas fa-sign-out-alt" />
          </button>
        </div>
      </div>
    </div>
  )
}
