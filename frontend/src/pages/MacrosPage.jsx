import React, { useState, useEffect } from 'react'
import { getMacros, createMacro, updateMacro, deleteMacro } from '../services/api'
import { useToast } from '../components/Toast'

const MACRO_CATEGORIES = [
  { value: 'meu_pedido', label: 'Meu Pedido' },
  { value: 'garantia', label: 'Garantia' },
  { value: 'reenvio', label: 'Reenvio' },
  { value: 'financeiro', label: 'Financeiro' },
  { value: 'duvida', label: 'Duvida' },
  { value: 'reclamacao', label: 'Reclamacao' },
]

const VARIABLES = [
  { tag: '{{cliente}}', desc: 'Nome do cliente' },
  { tag: '{{agente}}', desc: 'Nome do agente logado' },
  { tag: '{{email}}', desc: 'Email do cliente' },
  { tag: '{{numero}}', desc: 'Numero do ticket' },
  { tag: '{{assunto}}', desc: 'Assunto do ticket' },
  { tag: '{{rastreio}}', desc: 'Codigo de rastreio' },
  { tag: '{{categoria}}', desc: 'Categoria do ticket' },
  { tag: '{{prioridade}}', desc: 'Prioridade' },
  { tag: '{{status}}', desc: 'Status atual' },
]

const ACTION_TYPES = [
  { value: 'set_status', label: 'Mudar status', options: ['open', 'waiting', 'resolved', 'escalated', 'closed'] },
  { value: 'set_priority', label: 'Mudar prioridade', options: ['low', 'medium', 'high', 'urgent'] },
  { value: 'set_category', label: 'Mudar categoria', options: ['meu_pedido', 'garantia', 'reenvio', 'financeiro', 'duvida', 'reclamacao'] },
  { value: 'add_tag', label: 'Adicionar tag', options: null },
]

const EMPTY_FORM = { name: '', content: '', category: 'meu_pedido', actions: [] }

export default function MacrosPage() {
  const toast = useToast()
  const [macros, setMacros] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterCat, setFilterCat] = useState('')
  const [editing, setEditing] = useState(null) // macro object or 'new'
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(null)

  useEffect(() => { load() }, [])

  const load = async () => {
    try {
      const { data } = await getMacros()
      setMacros(data)
    } catch { toast.error('Erro ao carregar macros') }
    finally { setLoading(false) }
  }

  const filtered = macros.filter(m => {
    if (filterCat && m.category !== filterCat) return false
    if (search && !m.name.toLowerCase().includes(search.toLowerCase()) && !m.content.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const grouped = MACRO_CATEGORIES.reduce((acc, cat) => {
    const items = filtered.filter(m => m.category === cat.value)
    if (items.length > 0) acc.push({ ...cat, items })
    return acc
  }, [])
  // Uncategorized
  const uncategorized = filtered.filter(m => !MACRO_CATEGORIES.some(c => c.value === m.category))
  if (uncategorized.length > 0) grouped.push({ value: 'outros', label: 'Outros', items: uncategorized })

  const startEdit = (macro) => {
    setEditing(macro)
    setForm({ name: macro.name, content: macro.content, category: macro.category || 'meu_pedido', actions: macro.actions || [] })
  }

  const startNew = () => {
    setEditing('new')
    setForm(EMPTY_FORM)
  }

  const cancel = () => { setEditing(null); setForm(EMPTY_FORM) }

  const save = async () => {
    if (!form.name.trim() || !form.content.trim()) {
      toast.error('Nome e conteudo sao obrigatorios')
      return
    }
    setSaving(true)
    const payload = {
      name: form.name,
      content: form.content,
      category: form.category,
      actions: (form.actions || []).filter(a => a.type && a.value) || null,
    }
    if (payload.actions.length === 0) payload.actions = null
    try {
      if (editing === 'new') {
        await createMacro(payload)
        toast.success('Macro criada')
      } else {
        await updateMacro(editing.id, payload)
        toast.success('Macro atualizada')
      }
      setEditing(null)
      setForm(EMPTY_FORM)
      await load()
    } catch { toast.error('Erro ao salvar') }
    finally { setSaving(false) }
  }

  const handleDelete = async (id) => {
    try {
      await deleteMacro(id)
      toast.success('Macro excluida')
      setDeleteConfirm(null)
      if (editing?.id === id) cancel()
      await load()
    } catch { toast.error('Erro ao excluir') }
  }

  const insertVar = (tag) => {
    setForm(prev => ({ ...prev, content: prev.content + tag }))
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <i className="fas fa-spinner animate-spin text-2xl" style={{ color: '#64748B' }} />
      </div>
    )
  }

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Respostas Rapidas</h1>
          <p className="text-sm mt-1" style={{ color: '#64748B' }}>
            {macros.length} macro{macros.length !== 1 ? 's' : ''} · Use <code className="bg-white/5 px-1.5 py-0.5 rounded text-xs">/</code> no reply box pra inserir
          </p>
        </div>
        <button onClick={startNew}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition"
          style={{ background: '#E5A800', color: '#000' }}>
          <i className="fas fa-plus" /> Nova Macro
        </button>
      </div>

      {/* Search + Filter */}
      <div className="flex gap-3 mb-5">
        <div className="relative flex-1">
          <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-xs" style={{ color: '#64748B' }} />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Buscar macros..."
            className="w-full pl-9 pr-3 py-2 rounded-lg text-sm focus:outline-none"
            style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.08)', color: '#E2E8F0' }}
          />
        </div>
        <select value={filterCat} onChange={e => setFilterCat(e.target.value)}
          className="px-3 py-2 rounded-lg text-sm focus:outline-none"
          style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.08)', color: '#E2E8F0' }}>
          <option value="">Todas categorias</option>
          {MACRO_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
      </div>

      {/* Content: list + editor side by side */}
      <div className="flex gap-5 flex-1 min-h-0">
        {/* Macros list */}
        <div className="flex-1 overflow-auto pr-1">
          {grouped.length === 0 ? (
            <div className="text-center py-16">
              <i className="fas fa-bolt text-4xl mb-3" style={{ color: '#475569' }} />
              <p style={{ color: '#64748B' }}>Nenhuma macro encontrada</p>
            </div>
          ) : (
            grouped.map(group => (
              <div key={group.value} className="mb-5">
                <p className="text-[10px] font-bold uppercase tracking-wider px-1 mb-2" style={{ color: '#475569' }}>
                  {group.label} ({group.items.length})
                </p>
                <div className="space-y-2">
                  {group.items.map(m => (
                    <div key={m.id}
                      onClick={() => startEdit(m)}
                      className={`rounded-xl p-4 cursor-pointer transition border ${editing?.id === m.id ? 'border-yellow-500/50' : 'border-transparent hover:border-white/10'}`}
                      style={{ background: 'var(--bg-secondary)' }}>
                      <div className="flex items-start justify-between mb-1.5">
                        <h3 className="text-white font-medium text-sm">{m.name}</h3>
                        <div className="flex items-center gap-1.5 ml-2 shrink-0">
                          <button onClick={(e) => { e.stopPropagation(); startEdit(m) }}
                            className="p-1 rounded hover:bg-white/5 transition" style={{ color: '#64748B' }} title="Editar">
                            <i className="fas fa-pen text-xs" />
                          </button>
                          <button onClick={(e) => { e.stopPropagation(); setDeleteConfirm(m.id) }}
                            className="p-1 rounded hover:bg-red-500/10 transition" style={{ color: '#64748B' }} title="Excluir">
                            <i className="fas fa-trash text-xs" />
                          </button>
                        </div>
                      </div>
                      <p className="text-sm line-clamp-2" style={{ color: '#94A3B8' }}>{m.content}</p>
                      <div className="flex items-center gap-3 mt-2">
                        {m.use_count > 0 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(255,255,255,0.05)', color: '#64748B' }}>
                            <i className="fas fa-chart-bar mr-1" />{m.use_count}x usada
                          </span>
                        )}
                        {m.actions?.length > 0 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(234,179,8,0.1)', color: '#EAB308' }}>
                            <i className="fas fa-cog mr-1" />{m.actions.length} {m.actions.length === 1 ? 'acao' : 'acoes'}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Editor panel */}
        {editing && (
          <div className="w-[420px] shrink-0 rounded-xl p-5 flex flex-col"
            style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-white font-bold text-sm">
                <i className={`fas ${editing === 'new' ? 'fa-plus' : 'fa-pen'} mr-2 text-xs`} style={{ color: '#E5A800' }} />
                {editing === 'new' ? 'Nova Macro' : 'Editar Macro'}
              </h2>
              <button onClick={cancel} className="p-1 rounded hover:bg-white/5 transition" style={{ color: '#64748B' }}>
                <i className="fas fa-times" />
              </button>
            </div>

            <label className="text-xs font-semibold mb-1.5" style={{ color: '#94A3B8' }}>Nome</label>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Ex: Saudacao Inicial"
              className="w-full px-3 py-2 rounded-lg text-sm mb-3 focus:outline-none"
              style={{ background: 'var(--bg-primary)', border: '1px solid rgba(255,255,255,0.08)', color: '#E2E8F0' }}
            />

            <label className="text-xs font-semibold mb-1.5" style={{ color: '#94A3B8' }}>Categoria</label>
            <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg text-sm mb-3 focus:outline-none"
              style={{ background: 'var(--bg-primary)', border: '1px solid rgba(255,255,255,0.08)', color: '#E2E8F0' }}>
              {MACRO_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>

            <label className="text-xs font-semibold mb-1.5" style={{ color: '#94A3B8' }}>Conteudo</label>
            <textarea value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
              placeholder="Escreva o texto da resposta..."
              rows={8}
              className="w-full px-3 py-2 rounded-lg text-sm mb-2 focus:outline-none resize-none"
              style={{ background: 'var(--bg-primary)', border: '1px solid rgba(255,255,255,0.08)', color: '#E2E8F0' }}
            />

            {/* Variables */}
            <div className="mb-4">
              <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: '#475569' }}>
                Variaveis (clique pra inserir)
              </p>
              <div className="flex flex-wrap gap-1.5">
                {VARIABLES.map(v => (
                  <button key={v.tag} onClick={() => insertVar(v.tag)}
                    className="text-[11px] px-2 py-1 rounded-md transition hover:bg-yellow-500/10"
                    style={{ background: 'rgba(255,255,255,0.04)', color: '#94A3B8', border: '1px solid rgba(255,255,255,0.06)' }}
                    title={v.desc}>
                    {v.tag}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions automáticas */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: '#475569' }}>
                  Acoes automaticas
                </p>
                <button onClick={() => setForm(f => ({ ...f, actions: [...(f.actions || []), { type: 'set_status', value: '' }] }))}
                  className="text-[10px] px-2 py-0.5 rounded transition hover:bg-yellow-500/10"
                  style={{ color: '#E5A800' }}>
                  <i className="fas fa-plus mr-1" />Adicionar
                </button>
              </div>
              {(form.actions || []).length === 0 ? (
                <p className="text-[11px]" style={{ color: '#475569' }}>Nenhuma acao. A macro so insere texto.</p>
              ) : (
                <div className="space-y-2">
                  {form.actions.map((action, idx) => {
                    const actionType = ACTION_TYPES.find(a => a.value === action.type)
                    return (
                      <div key={idx} className="flex items-center gap-2">
                        <select value={action.type}
                          onChange={e => {
                            const newActions = [...form.actions]
                            newActions[idx] = { type: e.target.value, value: '' }
                            setForm(f => ({ ...f, actions: newActions }))
                          }}
                          className="flex-1 px-2 py-1.5 rounded-lg text-[11px] focus:outline-none"
                          style={{ background: 'var(--bg-primary)', border: '1px solid rgba(255,255,255,0.08)', color: '#E2E8F0' }}>
                          {ACTION_TYPES.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                        </select>
                        {actionType?.options ? (
                          <select value={action.value}
                            onChange={e => {
                              const newActions = [...form.actions]
                              newActions[idx] = { ...action, value: e.target.value }
                              setForm(f => ({ ...f, actions: newActions }))
                            }}
                            className="flex-1 px-2 py-1.5 rounded-lg text-[11px] focus:outline-none"
                            style={{ background: 'var(--bg-primary)', border: '1px solid rgba(255,255,255,0.08)', color: '#E2E8F0' }}>
                            <option value="">Selecione...</option>
                            {actionType.options.map(o => <option key={o} value={o}>{o}</option>)}
                          </select>
                        ) : (
                          <input value={action.value}
                            onChange={e => {
                              const newActions = [...form.actions]
                              newActions[idx] = { ...action, value: e.target.value }
                              setForm(f => ({ ...f, actions: newActions }))
                            }}
                            placeholder="ex: garantia_aprovada"
                            className="flex-1 px-2 py-1.5 rounded-lg text-[11px] focus:outline-none"
                            style={{ background: 'var(--bg-primary)', border: '1px solid rgba(255,255,255,0.08)', color: '#E2E8F0' }}
                          />
                        )}
                        <button onClick={() => {
                          const newActions = form.actions.filter((_, i) => i !== idx)
                          setForm(f => ({ ...f, actions: newActions }))
                        }}
                          className="p-1 rounded hover:bg-red-500/10 transition" style={{ color: '#64748B' }}>
                          <i className="fas fa-times text-xs" />
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Preview */}
            {form.content && (
              <div className="mb-4">
                <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: '#475569' }}>Pre-visualizacao</p>
                <div className="rounded-lg p-3 text-sm whitespace-pre-wrap"
                  style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', color: '#CBD5E1' }}>
                  {form.content
                    .replace(/\{\{cliente\}\}/gi, 'Joao Silva')
                    .replace(/\{\{agente\}\}/gi, 'Ana Silva')
                    .replace(/\{\{email\}\}/gi, 'joao@email.com')
                    .replace(/\{\{numero\}\}/gi, '#1234')
                    .replace(/\{\{assunto\}\}/gi, 'Meu pedido nao chegou')
                    .replace(/\{\{rastreio\}\}/gi, 'BR123456789')
                    .replace(/\{\{categoria\}\}/gi, 'Meu Pedido')
                    .replace(/\{\{prioridade\}\}/gi, 'Media')
                    .replace(/\{\{status\}\}/gi, 'Aberto')}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 mt-auto">
              <button onClick={cancel}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-medium transition"
                style={{ background: 'rgba(255,255,255,0.05)', color: '#94A3B8' }}>
                Cancelar
              </button>
              <button onClick={save} disabled={saving}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-semibold transition disabled:opacity-50"
                style={{ background: '#E5A800', color: '#000' }}>
                {saving ? <i className="fas fa-spinner animate-spin" /> : editing === 'new' ? 'Criar' : 'Salvar'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setDeleteConfirm(null)}>
          <div className="rounded-xl p-6 max-w-sm w-full" style={{ background: 'var(--bg-secondary)' }} onClick={e => e.stopPropagation()}>
            <h3 className="text-white font-bold mb-2">Excluir macro?</h3>
            <p className="text-sm mb-4" style={{ color: '#94A3B8' }}>Essa acao nao pode ser desfeita.</p>
            <div className="flex gap-2">
              <button onClick={() => setDeleteConfirm(null)}
                className="flex-1 px-4 py-2 rounded-lg text-sm" style={{ background: 'rgba(255,255,255,0.05)', color: '#94A3B8' }}>
                Cancelar
              </button>
              <button onClick={() => handleDelete(deleteConfirm)}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 text-white">
                Excluir
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
