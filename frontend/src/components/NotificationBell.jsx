import React, { useState, useRef, useEffect } from 'react'

const TYPE_CONFIG = {
  new_ticket: { icon: 'fa-ticket-alt', color: 'text-blue-400', label: 'Novo ticket' },
  ticket_update: { icon: 'fa-edit', color: 'text-yellow-400', label: 'Atualização' },
  assignment: { icon: 'fa-user-tag', color: 'text-green-400', label: 'Atribuição' },
  escalation: { icon: 'fa-exclamation-triangle', color: 'text-red-400', label: 'Escalação' },
}

function timeAgo(date) {
  const s = Math.floor((Date.now() - date.getTime()) / 1000)
  if (s < 60) return 'agora'
  if (s < 3600) return `${Math.floor(s / 60)}min`
  if (s < 86400) return `${Math.floor(s / 3600)}h`
  return `${Math.floor(s / 86400)}d`
}

export default function NotificationBell({ notifications, unreadCount, connected, markRead, clearAll, onOpenTicket }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleClick = (notif) => {
    markRead(notif.id)
    if (notif.ticket_id && onOpenTicket) {
      onOpenTicket(notif.ticket_id)
      setOpen(false)
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition"
      >
        <i className="fas fa-bell text-lg" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
        <span className={`absolute bottom-0.5 right-0.5 w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-12 w-80 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl shadow-2xl z-50 overflow-hidden">
          <div className="flex items-center justify-between p-3 border-b border-[var(--border-color)]">
            <span className="text-[var(--text-primary)] text-sm font-medium">
              Notificações {unreadCount > 0 && <span className="text-indigo-400">({unreadCount})</span>}
            </span>
            {notifications.length > 0 && (
              <button onClick={clearAll} className="text-[var(--text-secondary)] text-xs hover:text-red-400">
                Limpar
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-auto">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-[var(--text-secondary)] text-sm">
                <i className="fas fa-bell-slash text-2xl mb-2 block" />
                Sem notificações
              </div>
            ) : (
              notifications.map(notif => {
                const cfg = TYPE_CONFIG[notif.type] || TYPE_CONFIG.ticket_update
                return (
                  <div
                    key={notif.id}
                    onClick={() => handleClick(notif)}
                    className={`p-3 border-b border-[var(--border-color)]/50 cursor-pointer hover:bg-[var(--bg-tertiary)] transition ${
                      !notif.read ? 'bg-indigo-500/5' : ''
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <i className={`fas ${cfg.icon} ${cfg.color} mt-0.5`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
                          {!notif.read && <span className="w-2 h-2 bg-indigo-500 rounded-full" />}
                          <span className="text-[var(--text-tertiary)] text-xs ml-auto">{timeAgo(notif.timestamp)}</span>
                        </div>
                        <p className="text-[var(--text-primary)] text-sm mt-0.5 truncate">
                          {notif.type === 'new_ticket' && `#${notif.ticket_number} - ${notif.subject}`}
                          {notif.type === 'ticket_update' && `#${notif.ticket_number} atualizado por ${notif.actor}`}
                          {notif.type === 'assignment' && notif.message}
                          {notif.type === 'escalation' && `#${notif.ticket_number} escalado`}
                        </p>
                        {notif.details && (
                          <p className="text-[var(--text-secondary)] text-xs mt-0.5 truncate">{notif.details}</p>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
