import React, { useState, useEffect } from 'react'
import { useToast } from '../components/Toast'
import api, { getUsers } from '../services/api'

const CATEGORIES = [
  { value: 'meu_pedido', label: 'Meu Pedido', icon: 'fa-box', color: '#3B82F6', bg: 'rgba(59,130,246,0.15)' },
  { value: 'garantia', label: 'Garantia', icon: 'fa-shield-alt', color: '#F59E0B', bg: 'rgba(245,158,11,0.15)' },
  { value: 'reenvio', label: 'Reenvio', icon: 'fa-redo', color: '#8B5CF6', bg: 'rgba(139,92,246,0.15)' },
  { value: 'financeiro', label: 'Financeiro', icon: 'fa-dollar-sign', color: '#10B981', bg: 'rgba(16,185,129,0.15)' },
  { value: 'duvida', label: 'Duvida', icon: 'fa-question-circle', color: '#6366F1', bg: 'rgba(99,102,241,0.15)' },
  { value: 'reclamacao', label: 'Reclamacao', icon: 'fa-exclamation-triangle', color: '#EF4444', bg: 'rgba(239,68,68,0.15)' },
]

const PRIORITIES = [
  { value: 'low', label: 'Baixa', color: '#64748B', bg: 'rgba(100,116,139,0.15)' },
  { value: 'medium', label: 'Media', color: '#3B82F6', bg: 'rgba(59,130,246,0.15)' },
  { value: 'high', label: 'Alta', color: '#F97316', bg: 'rgba(249,115,22,0.15)' },
  { value: 'urgent', label: 'Urgente', color: '#EF4444', bg: 'rgba(239,68,68,0.15)' },
]

const EMPTY_FORM = { name: '', category: '', assign_to: '', set_priority: '', auto_reply: false, priority: 0 }

export default function TriagemPage({ user }) {
  const toast = useToast()
  const [rules, setRules] = useState([])
  const [agents, setAgents] = useState([])
  const [onlineAgents, setOnlineAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(null)

  useEffect(() => { loadAll() }, [])

  const loadAll = async () => {
    try {
      const [rulesRes, usersRes, onlineRes] = await Promise.all([
        api.get('/triage/rules'),
        getUsers(),
        api.get('/triage/online-agents'),
      ])
      setRules(rulesRes.data)
      setAgents(usersRes.data.filter(u => u.is_active && ['agent', 'supervisor', 'admin', 'super_admin'].includes(u.role)))
      setOnlineAgents(onlineRes.data)
    } catch { toast.error('Erro ao carregar dados') }
    finally { setLoading(false) }
  }

  const getCat = (val) => CATEGORIES.find(c => c.value === val)
  const getPrio = (val) => PRIORITIES.find(p => p.value === val)
  const getAgent = (id) => agents.find(a => a.id === id)

  const startNew = () => {
    setEditing('new')
    setForm({ ...EMPTY_FORM, priority: rules.length })
  }
  const startEdit = (rule) => {
    setEditing(rule)
    setForm({
      name: rule.name, category: rule.category || '', assign_to: rule.assign_to || '',
      set_priority: rule.set_priority || '', auto_reply: rule.auto_reply || false, priority: rule.priority || 0,
    })
  }
  const cancel = () => { setEditing(null); setForm(EMPTY_FORM) }

  const save = async () => {
    if (!form.name.trim()) { toast.error('Nome eh obrigatorio'); return }
    setSaving(true)
    const payload = {
      name: form.name, category: form.category || null, assign_to: form.assign_to || null,
      set_priority: form.set_priority || null, auto_reply: form.auto_reply, priority: form.priority,
    }
    try {
      if (editing === 'new') { await api.post('/triage/rules', payload); toast.success('Regra criada') }
      else { await api.put(`/triage/rules/${editing.id}`, payload); toast.success('Regra atualizada') }
      cancel(); await loadAll()
    } catch { toast.error('Erro ao salvar') }
    finally { setSaving(false) }
  }

  const handleDelete = async (id) => {
    try {
      await api.delete(`/triage/rules/${id}`)
      toast.success('Regra excluida'); setDeleteConfirm(null)
      if (editing?.id === id) cancel()
      await loadAll()
    } catch { toast.error('Erro ao excluir') }
  }

  const toggleActive = async (rule) => {
    try { await api.put(`/triage/rules/${rule.id}`, { is_active: !rule.is_active }); await loadAll() }
    catch { toast.error('Erro ao alterar status') }
  }

  if (loading) return (
    <div className="p-6 flex items-center justify-center h-full">
      <i className="fas fa-spinner animate-spin text-2xl" style={{ color: '#64748B' }} />
    </div>
  )

  const onlineIds = new Set(onlineAgents.map(a => a.id))

  return (
    <div className="p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Triagem</h1>
          <p className="text-sm mt-1" style={{ color: '#64748B' }}>
            Distribua tickets automaticamente para sua equipe
          </p>
        </div>
        <button onClick={startNew}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition cursor-pointer hover:opacity-90"
          style={{ background: '#E5A800', color: '#000' }}>
          <i className="fas fa-plus text-xs" /> Nova Regra
        </button>
      </div>

      {/* Rules */}
      <div className="space-y-2 mb-10">
        {rules.length === 0 ? (
          <div className="text-center py-20 rounded-2xl" style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
              style={{ background: 'rgba(229,168,0,0.1)' }}>
              <i className="fas fa-filter text-2xl" style={{ color: '#E5A800' }} />
            </div>
            <p className="font-semibold text-white mb-1">Sem regras de triagem</p>
            <p className="text-sm" style={{ color: '#64748B' }}>Clique em "Nova Regra" para comecar</p>
          </div>
        ) : (
          rules.map(rule => {
            const cat = getCat(rule.category)
            const prio = getPrio(rule.set_priority)
            const agent = getAgent(rule.assign_to) || (rule.agent_name ? { name: rule.agent_name } : null)

            return (
              <div key={rule.id}
                className="rounded-xl px-5 py-4 flex items-center gap-4 group transition cursor-pointer hover:border-white/10"
                style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.04)', opacity: rule.is_active ? 1 : 0.4 }}
                onClick={() => startEdit(rule)}>

                {/* Toggle */}
                <button onClick={e => { e.stopPropagation(); toggleActive(rule) }}
                  className="shrink-0 cursor-pointer" title={rule.is_active ? 'Desativar' : 'Ativar'}>
                  <div className="w-10 h-[22px] rounded-full transition-colors relative"
                    style={{ background: rule.is_active ? '#E5A800' : 'rgba(255,255,255,0.08)' }}>
                    <div className="w-4 h-4 rounded-full bg-white absolute top-[3px] transition-all"
                      style={{ left: rule.is_active ? '21px' : '3px' }} />
                  </div>
                </button>

                {/* Category icon */}
                {cat ? (
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                    style={{ background: cat.bg }}>
                    <i className={`fas ${cat.icon} text-sm`} style={{ color: cat.color }} />
                  </div>
                ) : (
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                    style={{ background: 'rgba(255,255,255,0.05)' }}>
                    <i className="fas fa-globe text-sm" style={{ color: '#64748B' }} />
                  </div>
                )}

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">{rule.name}</p>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className="text-[11px]" style={{ color: '#64748B' }}>
                      {cat?.label || 'Qualquer'} <i className="fas fa-long-arrow-alt-right mx-1 text-[9px]" /> {agent?.name || 'Round-robin'}
                    </span>
                    {prio && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                        style={{ background: prio.bg, color: prio.color }}>
                        {prio.label}
                      </span>
                    )}
                    {rule.auto_reply && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                        style={{ background: 'rgba(16,185,129,0.12)', color: '#10B981' }}>
                        Auto-reply
                      </span>
                    )}
                  </div>
                </div>

                {/* Delete */}
                <button onClick={e => { e.stopPropagation(); setDeleteConfirm(rule.id) }}
                  className="p-2 rounded-lg opacity-0 group-hover:opacity-100 transition hover:bg-red-500/10 cursor-pointer"
                  style={{ color: '#64748B' }} title="Excluir">
                  <i className="fas fa-trash text-xs" />
                </button>
              </div>
            )
          })
        )}

        {/* Fallback */}
        {rules.length > 0 && (
          <div className="rounded-xl px-5 py-4 flex items-center gap-4 border border-dashed"
            style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
            <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
              style={{ background: 'rgba(99,102,241,0.12)' }}>
              <i className="fas fa-random text-sm" style={{ color: '#6366F1' }} />
            </div>
            <div>
              <p className="text-sm font-medium text-white">Sem match → Round-Robin</p>
              <p className="text-[11px]" style={{ color: '#475569' }}>Distribui pro agente online com menos tickets</p>
            </div>
          </div>
        )}
      </div>

      {/* Online Agents */}
      <div className="mb-6">
        <div className="flex items-center gap-2.5 mb-4">
          <h2 className="text-lg font-bold text-white">Equipe</h2>
          <span className="text-[11px] font-bold px-2.5 py-1 rounded-full"
            style={{ background: onlineAgents.length > 0 ? 'rgba(16,185,129,0.12)' : 'rgba(100,116,139,0.12)',
                     color: onlineAgents.length > 0 ? '#10B981' : '#64748B' }}>
            {onlineAgents.length} online
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {agents.map(agent => {
            const isOnline = onlineIds.has(agent.id)
            return (
              <div key={agent.id} className="rounded-xl p-4 transition"
                style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.04)', opacity: isOnline ? 1 : 0.45 }}>
                <div className="flex items-center gap-3">
                  <div className="relative shrink-0">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold"
                      style={{ background: 'linear-gradient(135deg, #E5A800 0%, #CC9600 100%)', color: '#fff' }}>
                      {agent.name?.[0] || '?'}
                    </div>
                    <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2"
                      style={{ background: isOnline ? '#10B981' : '#475569', borderColor: 'var(--bg-secondary)' }} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-white truncate">{agent.name}</p>
                    <p className="text-[10px]" style={{ color: '#64748B' }}>{isOnline ? 'Online' : 'Offline'}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Modal */}
      {editing && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={cancel}>
          <div className="rounded-2xl p-6 w-full max-w-md" style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.08)' }}
            onClick={e => e.stopPropagation()}>
            <h2 className="text-white font-bold text-lg mb-5">
              {editing === 'new' ? 'Nova Regra' : 'Editar Regra'}
            </h2>

            {/* Name */}
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Nome da regra"
              className="w-full px-4 py-3 rounded-xl text-sm focus:outline-none mb-5"
              style={{ background: 'var(--bg-primary)', border: '1px solid rgba(255,255,255,0.08)', color: '#E2E8F0' }}
            />

            {/* Category chips */}
            <p className="text-[11px] font-bold uppercase tracking-wider mb-2.5" style={{ color: '#64748B' }}>Categoria</p>
            <div className="flex flex-wrap gap-2 mb-5">
              <button onClick={() => setForm(f => ({ ...f, category: '' }))}
                className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-xl transition cursor-pointer"
                style={{ background: !form.category ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.03)',
                         color: !form.category ? '#E2E8F0' : '#475569',
                         border: !form.category ? '1px solid rgba(255,255,255,0.15)' : '1px solid rgba(255,255,255,0.06)' }}>
                <i className="fas fa-globe text-[10px]" /> Qualquer
              </button>
              {CATEGORIES.map(c => (
                <button key={c.value} onClick={() => setForm(f => ({ ...f, category: c.value }))}
                  className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-xl transition cursor-pointer"
                  style={{ background: form.category === c.value ? c.bg : 'rgba(255,255,255,0.03)',
                           color: form.category === c.value ? c.color : '#475569',
                           border: form.category === c.value ? `1px solid ${c.color}30` : '1px solid rgba(255,255,255,0.06)' }}>
                  <i className={`fas ${c.icon} text-[10px]`} /> {c.label}
                </button>
              ))}
            </div>

            {/* Assign to */}
            <p className="text-[11px] font-bold uppercase tracking-wider mb-2.5" style={{ color: '#64748B' }}>Atribuir a</p>
            <select value={form.assign_to} onChange={e => setForm(f => ({ ...f, assign_to: e.target.value }))}
              className="w-full px-4 py-3 rounded-xl text-sm focus:outline-none mb-5 cursor-pointer"
              style={{ background: 'var(--bg-primary)', border: '1px solid rgba(255,255,255,0.08)', color: '#E2E8F0' }}>
              <option value="">Automatico (round-robin)</option>
              {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>

            {/* Priority buttons */}
            <p className="text-[11px] font-bold uppercase tracking-wider mb-2.5" style={{ color: '#64748B' }}>Prioridade</p>
            <div className="grid grid-cols-4 gap-2 mb-5">
              {PRIORITIES.map(p => (
                <button key={p.value} onClick={() => setForm(f => ({ ...f, set_priority: f.set_priority === p.value ? '' : p.value }))}
                  className="text-xs font-semibold py-2.5 rounded-xl transition cursor-pointer text-center"
                  style={{ background: form.set_priority === p.value ? p.bg : 'rgba(255,255,255,0.03)',
                           color: form.set_priority === p.value ? p.color : '#475569',
                           border: form.set_priority === p.value ? `1px solid ${p.color}30` : '1px solid rgba(255,255,255,0.06)' }}>
                  {p.label}
                </button>
              ))}
            </div>

            {/* Auto-reply */}
            <div className="flex items-center justify-between mb-6 rounded-xl px-4 py-3"
              style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <div className="flex items-center gap-2.5">
                <i className="fas fa-robot text-sm" style={{ color: form.auto_reply ? '#10B981' : '#475569' }} />
                <span className="text-sm" style={{ color: '#E2E8F0' }}>Auto-reply IA</span>
              </div>
              <button onClick={() => setForm(f => ({ ...f, auto_reply: !f.auto_reply }))} className="cursor-pointer">
                <div className="w-11 h-6 rounded-full transition-colors relative"
                  style={{ background: form.auto_reply ? '#10B981' : 'rgba(255,255,255,0.08)' }}>
                  <div className="w-[18px] h-[18px] rounded-full bg-white absolute top-[3px] transition-all shadow-sm"
                    style={{ left: form.auto_reply ? '23px' : '3px' }} />
                </div>
              </button>
            </div>

            {/* Buttons */}
            <div className="flex gap-3">
              <button onClick={cancel}
                className="flex-1 px-4 py-3 rounded-xl text-sm font-medium transition cursor-pointer hover:bg-white/10"
                style={{ background: 'rgba(255,255,255,0.05)', color: '#94A3B8' }}>
                Cancelar
              </button>
              <button onClick={save} disabled={saving}
                className="flex-1 px-4 py-3 rounded-xl text-sm font-bold transition disabled:opacity-50 cursor-pointer hover:opacity-90"
                style={{ background: '#E5A800', color: '#000' }}>
                {saving ? <i className="fas fa-spinner animate-spin" /> : editing === 'new' ? 'Criar' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setDeleteConfirm(null)}>
          <div className="rounded-2xl p-6 max-w-sm w-full" style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.08)' }}
            onClick={e => e.stopPropagation()}>
            <h3 className="text-white font-bold text-lg mb-2">Excluir regra?</h3>
            <p className="text-sm mb-5" style={{ color: '#94A3B8' }}>Essa acao nao pode ser desfeita.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteConfirm(null)}
                className="flex-1 px-4 py-2.5 rounded-xl text-sm cursor-pointer hover:bg-white/10 transition"
                style={{ background: 'rgba(255,255,255,0.05)', color: '#94A3B8' }}>
                Cancelar
              </button>
              <button onClick={() => handleDelete(deleteConfirm)}
                className="flex-1 px-4 py-2.5 rounded-xl text-sm font-bold bg-red-600 text-white cursor-pointer hover:bg-red-500 transition">
                Excluir
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
