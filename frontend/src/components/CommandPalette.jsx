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
  { label: 'Biblioteca de Mídia', icon: 'fa-photo-video', path: '/media' },
  { label: 'Catálogo', icon: 'fa-box-open', path: '/catalog' },
  { label: 'Moderação Social', icon: 'fa-shield-alt', path: '/moderation' },
  { label: 'Performance', icon: 'fa-gamepad', path: '/leaderboard' },
  { label: 'Relatórios', icon: 'fa-chart-bar', path: '/reports' },
  { label: 'Integrações', icon: 'fa-plug', path: '/integrations' },
  { label: 'Configurações', icon: 'fa-cog', path: '/settings' },
]

const ACTIONS = [
  { label: 'Exportar CSV', icon: 'fa-file-csv', path: '/tickets?export=csv' },
  { label: 'Atribuição Automática', icon: 'fa-magic', path: '/tickets?auto_assign=true' },
]

const STATUS_LABELS = {
  open: 'Aberto', in_progress: 'Andamento', waiting: 'Aguardando',
  resolved: 'Resolvido', escalated: 'Escalado', closed: 'Fechado',
}

export default function CommandPalette() {
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
      navigate(item.data.path)
    }
  }, [navigate])

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
            placeholder="Buscar tickets, páginas, ações..."
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
              {q && <p className="px-5 py-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Páginas
              </p>}
              {!q && <p className="px-5 py-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Ir para
              </p>}
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
            <div className="mb-1">
              <p className="px-5 py-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Ações
              </p>
              {filteredActions.map((a, i) => {
                const idx = tickets.length + filteredPages.length + i
                return (
                  <button key={a.label} onClick={() => handleSelect({ type: 'action', data: a })}
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
