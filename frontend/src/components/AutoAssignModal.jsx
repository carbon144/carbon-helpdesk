import React, { useState } from 'react'

export default function AutoAssignModal({ open, onClose, agents, onAssign }) {
  const [selectedIds, setSelectedIds] = useState([])
  if (!open) return null
  const activeAgents = agents.filter(a => a.is_active)
  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[var(--bg-secondary)] rounded-2xl w-full max-w-md border border-[var(--border-color)] shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-[var(--border-color)] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-green-600/20 flex items-center justify-center">
              <i className="fas fa-magic text-green-400" />
            </div>
            <div>
              <h3 className="text-[var(--text-primary)] font-semibold">Auto-Atribuir</h3>
              <p className="text-xs text-[var(--text-tertiary)]">Selecione os agentes que receberão tickets</p>
            </div>
          </div>
          <button onClick={onClose} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors">
            <i className="fas fa-times" />
          </button>
        </div>

        <div className="px-6 py-3 border-b border-[var(--border-color)] flex items-center justify-between">
          <span className="text-xs text-[var(--text-tertiary)]">{selectedIds.length} de {activeAgents.length} selecionados</span>
          <div className="flex gap-2">
            <button onClick={() => setSelectedIds(activeAgents.map(a => a.id))} className="text-xs text-[var(--accent)] hover:underline">Selecionar todos</button>
            <span className="text-[var(--text-tertiary)]">|</span>
            <button onClick={() => setSelectedIds([])} className="text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">Limpar</button>
          </div>
        </div>

        <div className="px-6 py-3 max-h-80 overflow-y-auto space-y-1">
          {activeAgents.map(agent => (
            <label key={agent.id} className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors hover:bg-[var(--bg-hover)]">
              <input type="checkbox" checked={selectedIds.includes(agent.id)}
                onChange={e => {
                  if (e.target.checked) setSelectedIds(prev => [...prev, agent.id])
                  else setSelectedIds(prev => prev.filter(id => id !== agent.id))
                }}
                className="w-4 h-4 rounded border-[var(--border-color)] accent-green-500" />
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                {agent.name?.[0] || '?'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[var(--text-primary)] font-medium truncate">{agent.name}</p>
                <p className="text-xs text-[var(--text-tertiary)]">
                  {agent.specialty && agent.specialty !== 'geral' ? agent.specialty : 'Geral'}
                  {agent.role === 'admin' ? ' · Admin' : agent.role === 'supervisor' ? ' · Supervisor' : ''}
                </p>
              </div>
            </label>
          ))}
        </div>

        <div className="px-6 py-4 border-t border-[var(--border-color)] flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">Cancelar</button>
          <button onClick={() => { onAssign(selectedIds); setSelectedIds([]) }} disabled={selectedIds.length === 0}
            className="px-5 py-2 rounded-lg text-sm font-medium bg-green-600 hover:bg-green-700 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
            <i className="fas fa-magic mr-2" />Distribuir para {selectedIds.length} agente(s)
          </button>
        </div>
      </div>
    </div>
  )
}
