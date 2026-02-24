import React from 'react'

const ROLE_LABELS = {
  super_admin: 'Super Admin', admin: 'Administrador', supervisor: 'Supervisor', agent: 'Agente',
}

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'fa-chart-line', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
  { id: 'tickets', label: 'Caixa de Entrada', icon: 'fa-inbox', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
  { id: 'kb', label: 'Base de Conhecimento', icon: 'fa-book', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
  { id: 'media', label: 'Biblioteca de Mídia', icon: 'fa-photo-video', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
  { id: 'catalog', label: 'Catálogo', icon: 'fa-box-open', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
  { id: 'assistant', label: 'Assistente IA', icon: 'fa-robot', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
  { id: 'leaderboard', label: 'Performance', icon: 'fa-gamepad', roles: ['super_admin', 'admin', 'supervisor'] },
  { id: 'tracking', label: 'Rastreamento', icon: 'fa-truck-fast', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
  { id: 'canais-ia', label: 'Canais IA', icon: 'fa-comments', roles: ['super_admin', 'admin', 'supervisor'] },
  { id: 'moderation', label: 'Moderação Social', icon: 'fa-shield-alt', roles: ['super_admin', 'admin', 'supervisor'] },
  { id: 'reports', label: 'Relatórios', icon: 'fa-chart-bar', roles: ['super_admin', 'admin', 'supervisor'] },
  { id: 'integrations', label: 'Integrações', icon: 'fa-plug', roles: ['super_admin'] },
  { id: 'settings', label: 'Configurações', icon: 'fa-cog', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
]

export default function Sidebar({ user, onLogout, page, setPage, ticketCount, metaCount }) {
  const userRole = user?.role || 'agent'

  return (
    <div className="w-60 shrink-0 flex flex-col h-full"
      style={{ background: '#1d1d1f', borderRight: '1px solid rgba(255,255,255,0.06)' }}>
      {/* Logo */}
      <div className="px-4 py-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <img src="/assets/carbon-logo.svg" alt="Carbon Expert Hub" className="h-8" />
      </div>

      {/* Nav */}
      <nav className="px-3 py-3 space-y-0.5 flex-1 overflow-auto">
        <p className="text-[10px] font-semibold uppercase tracking-wider px-3 mb-2" style={{ color: '#636366' }}>Menu</p>
        {NAV_ITEMS.filter(item => item.roles.includes(userRole)).map(item => {
          const active = page === item.id
          return (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className="w-full flex items-center justify-between gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all"
              style={{
                background: active ? 'rgba(253,210,0,0.12)' : 'transparent',
                color: active ? '#fdd200' : '#8e8e93',
              }}
              onMouseEnter={e => { if (!active) { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = '#f5f5f7' }}}
              onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#8e8e93' }}}
            >
              <span className="flex items-center gap-2.5">
                <i className={`fas ${item.icon} w-4 text-center text-xs`} />
                {item.label}
              </span>
              {item.id === 'tickets' && ticketCount > 0 && (
                <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold"
                  style={{ background: '#fdd200', color: '#1d1d1f' }}>
                  {ticketCount}
                </span>
              )}
              {item.id === 'canais-ia' && metaCount > 0 && (
                <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold"
                  style={{ background: '#25D366', color: '#fff' }}>
                  {metaCount}
                </span>
              )}
            </button>
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
