import React, { useState, useEffect } from 'react'

const SHORTCUT_GROUPS = [
  {
    label: 'Navegação',
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
      { keys: ['J'], desc: 'Próximo ticket' },
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
      { keys: ['Alt', 'N'], desc: 'Próximo ticket' },
      { keys: ['Alt', 'S'], desc: 'Sugestão IA' },
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
