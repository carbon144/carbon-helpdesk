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
      { to: '/chat', label: 'Chat ao Vivo', icon: 'fa-headset', roles: ['super_admin', 'admin', 'supervisor', 'agent'], badge: 'chat' },
      { to: '/tracking', label: 'Rastreamento', icon: 'fa-truck-fast', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/voice-calls', label: 'Ligacoes', icon: 'fa-phone', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
    ],
  },
  {
    label: 'Ferramentas',
    items: [
      { to: '/assistant', label: 'Assistente IA', icon: 'fa-robot', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/kb', label: 'Base de Conhecimento', icon: 'fa-book', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/media', label: 'Biblioteca de Midia', icon: 'fa-photo-video', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/catalog', label: 'Catalogo', icon: 'fa-box-open', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/macros', label: 'Respostas Rapidas', icon: 'fa-bolt', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
      { to: '/chatbot-flows', label: 'Chatbot Flows', icon: 'fa-robot', roles: ['super_admin', 'admin', 'supervisor'] },
      // { to: '/moderation', label: 'Moderacao Social', icon: 'fa-shield-alt', roles: ['super_admin', 'admin', 'supervisor'] },
    ],
  },
  {
    label: 'Gestao',
    items: [
      { to: '/leaderboard', label: 'Performance', icon: 'fa-gamepad', roles: ['super_admin', 'admin', 'supervisor'] },
      { to: '/agent-analysis', label: 'Analise de Equipe', icon: 'fa-microscope', roles: ['super_admin'] },
      { to: '/reports', label: 'Relatorios', icon: 'fa-chart-bar', roles: ['super_admin', 'admin', 'supervisor'] },
      { to: '/integrations', label: 'Integracoes', icon: 'fa-plug', roles: ['super_admin'] },
      { to: '/settings', label: 'Configuracoes', icon: 'fa-cog', roles: ['super_admin', 'admin', 'supervisor', 'agent'] },
    ],
  },
]

export default function Sidebar({ user, onLogout, ticketCount, metaCount, chatCount }) {
  const userRole = user?.role || 'agent'

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
                {visibleItems.map(item => (
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
                    {item.badge === 'tickets' && ticketCount > 0 && (
                      <span className="text-[10px] font-bold px-[7px] py-[2px] rounded-full min-w-[20px] text-center"
                        style={{ background: '#E5A800', color: '#FFFFFF' }}>
                        {ticketCount}
                      </span>
                    )}
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
                ))}
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
              {user.name[0]}
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
