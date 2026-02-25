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
      { to: '/media', label: 'Biblioteca de Mídia', icon: 'fa-photo-video', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/catalog', label: 'Catálogo', icon: 'fa-box-open', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/moderation', label: 'Moderação Social', icon: 'fa-shield-alt', roles: ['super_admin', 'admin', 'supervisor'] },
    ],
  },
  {
    label: 'Gestão',
    items: [
      { to: '/leaderboard', label: 'Performance', icon: 'fa-gamepad', roles: ['super_admin', 'admin', 'supervisor'] },
      { to: '/reports', label: 'Relatórios', icon: 'fa-chart-bar', roles: ['super_admin', 'admin', 'supervisor'] },
      { to: '/integrations', label: 'Integrações', icon: 'fa-plug', roles: ['super_admin'] },
      { to: '/settings', label: 'Configurações', icon: 'fa-cog', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
    ],
  },
]

export default function Sidebar({ user, onLogout, ticketCount, metaCount }) {
  const userRole = user?.role || 'agent'

  return (
    <div className="w-60 shrink-0 flex flex-col h-full"
      style={{ background: 'linear-gradient(180deg, #18181B 0%, #1F1F23 100%)', borderRight: '1px solid rgba(229,168,0,0.3)' }}>
      <div className="px-4 py-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <img src="/assets/carbon-logo.svg" alt="Carbon Expert Hub" className="h-8" />
      </div>

      <nav className="px-3 py-3 flex-1 overflow-auto">
        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter(item => item.roles.includes(userRole))
          if (visibleItems.length === 0) return null
          return (
            <div key={group.label} className="mb-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider px-3 mb-2" style={{ color: '#52525B' }}>
                {group.label}
              </p>
              <div className="space-y-0.5">
                {visibleItems.map(item => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `sidebar-nav-item w-full flex items-center justify-between gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium ${isActive ? 'sidebar-nav-active' : ''}`
                    }
                  >
                    <span className="flex items-center gap-2.5">
                      <i className={`fas ${item.icon} w-4 text-center text-xs`} />
                      {item.label}
                    </span>
                    {item.badge === 'tickets' && ticketCount > 0 && (
                      <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold"
                        style={{ background: '#E5A800', color: '#FFFFFF' }}>
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

      <div className="px-3 py-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              style={{ background: '#E5A800', color: '#FFFFFF' }}>
              {user.name[0]}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: '#E4E4E7' }}>{user.name}</p>
              <p className="text-[11px] truncate" style={{ color: '#71717A' }}>{ROLE_LABELS[user.role] || user.role}</p>
            </div>
          </div>
          <button onClick={onLogout}
            className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors text-xs"
            style={{ color: '#71717A' }}
            onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
            onMouseLeave={e => e.currentTarget.style.color = '#71717A'}
            title="Sair">
            <i className="fas fa-sign-out-alt" />
          </button>
        </div>
      </div>
    </div>
  )
}
