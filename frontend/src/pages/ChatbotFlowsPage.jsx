import { useState, useEffect, useCallback } from 'react'
import api from '../services/api'

const TRIGGER_TYPES = [
  { value: 'greeting', label: 'Saudacao', desc: 'Oi, ola, bom dia...' },
  { value: 'keyword', label: 'Palavra-chave', desc: 'Contem uma palavra especifica' },
  { value: 'exact', label: 'Texto exato', desc: 'Mensagem identica' },
  { value: 'any', label: 'Qualquer mensagem', desc: 'Responde a tudo' },
]

const STEP_TYPES = [
  { value: 'send_message', label: 'Enviar mensagem', icon: 'fa-comment' },
  { value: 'wait_response', label: 'Aguardar resposta', icon: 'fa-clock' },
  { value: 'lookup_order', label: 'Buscar pedido', icon: 'fa-search' },
  { value: 'suggest_article', label: 'Sugerir artigo KB', icon: 'fa-book' },
  { value: 'transfer_to_agent', label: 'Transferir p/ agente', icon: 'fa-user' },
]

function FlowCard({ flow, onEdit, onToggle, onDelete }) {
  const trigger = TRIGGER_TYPES.find(t => t.value === flow.trigger_type)
  const stepCount = (flow.steps || []).length

  return (
    <div className="rounded-xl p-4 border transition-all hover:border-[#E5A800]/40"
      style={{ background: '#1F1F23', borderColor: 'rgba(255,255,255,0.06)' }}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold truncate" style={{ color: '#E4E4E7' }}>{flow.name}</h3>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${flow.active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-zinc-700 text-zinc-400'}`}>
              {flow.active ? 'Ativo' : 'Inativo'}
            </span>
          </div>
          <div className="flex items-center gap-3 text-[11px]" style={{ color: '#71717A' }}>
            <span><i className="fas fa-bolt mr-1" />{trigger?.label || flow.trigger_type}</span>
            <span><i className="fas fa-list-ol mr-1" />{stepCount} {stepCount === 1 ? 'step' : 'steps'}</span>
          </div>
          {flow.trigger_type === 'keyword' && flow.trigger_config?.keywords?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {flow.trigger_config.keywords.map((kw, i) => (
                <span key={i} className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#27272A', color: '#A1A1AA' }}>
                  {kw}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={() => onToggle(flow)} className="w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-colors"
            style={{ color: '#71717A' }} title={flow.active ? 'Desativar' : 'Ativar'}>
            <i className={`fas ${flow.active ? 'fa-pause' : 'fa-play'}`} />
          </button>
          <button onClick={() => onEdit(flow)} className="w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-colors"
            style={{ color: '#71717A' }} title="Editar">
            <i className="fas fa-pen" />
          </button>
          <button onClick={() => onDelete(flow)} className="w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-colors"
            style={{ color: '#71717A' }} title="Excluir">
            <i className="fas fa-trash" />
          </button>
        </div>
      </div>
    </div>
  )
}

function StepEditor({ step, index, total, onChange, onRemove, onMove }) {
  const stepType = STEP_TYPES.find(s => s.value === step.type)

  return (
    <div className="rounded-lg border p-3 group" style={{ background: '#18181B', borderColor: 'rgba(255,255,255,0.06)' }}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold" style={{ background: '#E5A800', color: '#000' }}>
            {index + 1}
          </span>
          <select value={step.type} onChange={e => onChange({ ...step, type: e.target.value })}
            className="text-xs font-medium bg-transparent border-none outline-none cursor-pointer" style={{ color: '#E4E4E7' }}>
            {STEP_TYPES.map(s => <option key={s.value} value={s.value} style={{ background: '#27272A' }}>{s.label}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          {index > 0 && (
            <button onClick={() => onMove(index, index - 1)} className="w-6 h-6 rounded flex items-center justify-center text-[10px]" style={{ color: '#71717A' }}>
              <i className="fas fa-arrow-up" />
            </button>
          )}
          {index < total - 1 && (
            <button onClick={() => onMove(index, index + 1)} className="w-6 h-6 rounded flex items-center justify-center text-[10px]" style={{ color: '#71717A' }}>
              <i className="fas fa-arrow-down" />
            </button>
          )}
          <button onClick={() => onRemove(index)} className="w-6 h-6 rounded flex items-center justify-center text-[10px]" style={{ color: '#ef4444' }}>
            <i className="fas fa-times" />
          </button>
        </div>
      </div>

      {(step.type === 'send_message' || step.type === 'transfer_to_agent') && (
        <textarea value={step.content || step.message || ''} onChange={e => onChange({ ...step, content: e.target.value, message: e.target.value })}
          placeholder={step.type === 'transfer_to_agent' ? 'Mensagem ao transferir...' : 'Mensagem...'}
          rows={2} className="w-full text-xs rounded-lg px-3 py-2 resize-none outline-none"
          style={{ background: '#27272A', color: '#E4E4E7', border: '1px solid rgba(255,255,255,0.06)' }} />
      )}
      {step.type === 'wait_response' && (
        <input value={step.prompt || ''} onChange={e => onChange({ ...step, prompt: e.target.value })}
          placeholder="Prompt para o usuario..." className="w-full text-xs rounded-lg px-3 py-2 outline-none"
          style={{ background: '#27272A', color: '#E4E4E7', border: '1px solid rgba(255,255,255,0.06)' }} />
      )}
      {step.type === 'lookup_order' && (
        <input value={step.message || ''} onChange={e => onChange({ ...step, message: e.target.value })}
          placeholder="Mensagem enquanto busca..." className="w-full text-xs rounded-lg px-3 py-2 outline-none"
          style={{ background: '#27272A', color: '#E4E4E7', border: '1px solid rgba(255,255,255,0.06)' }} />
      )}
      {step.type === 'suggest_article' && (
        <input value={step.message || ''} onChange={e => onChange({ ...step, message: e.target.value })}
          placeholder="Mensagem ao sugerir artigo..." className="w-full text-xs rounded-lg px-3 py-2 outline-none"
          style={{ background: '#27272A', color: '#E4E4E7', border: '1px solid rgba(255,255,255,0.06)' }} />
      )}
    </div>
  )
}

function FlowEditor({ flow, onSave, onCancel }) {
  const [name, setName] = useState(flow?.name || '')
  const [triggerType, setTriggerType] = useState(flow?.trigger_type || 'greeting')
  const [keywords, setKeywords] = useState((flow?.trigger_config?.keywords || []).join(', '))
  const [exactText, setExactText] = useState(flow?.trigger_config?.text || '')
  const [steps, setSteps] = useState(flow?.steps || [])
  const [active, setActive] = useState(flow?.active ?? true)
  const [saving, setSaving] = useState(false)

  const addStep = (type) => {
    setSteps([...steps, { type, content: '', message: '', prompt: '' }])
  }

  const updateStep = (index, updated) => {
    const next = [...steps]
    next[index] = updated
    setSteps(next)
  }

  const removeStep = (index) => {
    setSteps(steps.filter((_, i) => i !== index))
  }

  const moveStep = (from, to) => {
    const next = [...steps]
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    setSteps(next)
  }

  const handleSave = async () => {
    if (!name.trim()) return
    setSaving(true)
    const triggerConfig = triggerType === 'keyword'
      ? { keywords: keywords.split(',').map(k => k.trim()).filter(Boolean) }
      : triggerType === 'exact'
        ? { text: exactText }
        : {}
    const payload = { name, trigger_type: triggerType, trigger_config: triggerConfig, steps, active }
    try {
      await onSave(payload)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-xl border p-5" style={{ background: '#1F1F23', borderColor: 'rgba(229,168,0,0.3)' }}>
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold" style={{ color: '#E4E4E7' }}>
          {flow?.id ? 'Editar Flow' : 'Novo Flow'}
        </h3>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 cursor-pointer text-xs" style={{ color: '#A1A1AA' }}>
            <span>{active ? 'Ativo' : 'Inativo'}</span>
            <button onClick={() => setActive(!active)}
              className={`w-8 h-4 rounded-full relative transition-colors ${active ? 'bg-emerald-500' : 'bg-zinc-600'}`}>
              <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${active ? 'left-4' : 'left-0.5'}`} />
            </button>
          </label>
        </div>
      </div>

      {/* Name */}
      <div className="mb-4">
        <label className="text-[11px] font-medium mb-1 block" style={{ color: '#71717A' }}>Nome do Flow</label>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="Ex: Boas-vindas, Rastreio de pedido..."
          className="w-full text-sm rounded-lg px-3 py-2 outline-none" style={{ background: '#27272A', color: '#E4E4E7', border: '1px solid rgba(255,255,255,0.06)' }} />
      </div>

      {/* Trigger */}
      <div className="mb-4">
        <label className="text-[11px] font-medium mb-1.5 block" style={{ color: '#71717A' }}>Gatilho</label>
        <div className="grid grid-cols-2 gap-2">
          {TRIGGER_TYPES.map(t => (
            <button key={t.value} onClick={() => setTriggerType(t.value)}
              className={`text-left rounded-lg px-3 py-2 border transition-all ${triggerType === t.value ? 'border-[#E5A800]/50' : ''}`}
              style={{ background: triggerType === t.value ? '#E5A800/10' : '#27272A', borderColor: triggerType === t.value ? '#E5A800' : 'rgba(255,255,255,0.06)' }}>
              <span className="text-xs font-medium block" style={{ color: triggerType === t.value ? '#E5A800' : '#E4E4E7' }}>{t.label}</span>
              <span className="text-[10px] block" style={{ color: '#71717A' }}>{t.desc}</span>
            </button>
          ))}
        </div>

        {triggerType === 'keyword' && (
          <input value={keywords} onChange={e => setKeywords(e.target.value)} placeholder="rastreio, pedido, entrega (separar por virgula)"
            className="w-full text-xs rounded-lg px-3 py-2 mt-2 outline-none" style={{ background: '#27272A', color: '#E4E4E7', border: '1px solid rgba(255,255,255,0.06)' }} />
        )}
        {triggerType === 'exact' && (
          <input value={exactText} onChange={e => setExactText(e.target.value)} placeholder="Texto exato que deve corresponder"
            className="w-full text-xs rounded-lg px-3 py-2 mt-2 outline-none" style={{ background: '#27272A', color: '#E4E4E7', border: '1px solid rgba(255,255,255,0.06)' }} />
        )}
      </div>

      {/* Steps */}
      <div className="mb-4">
        <label className="text-[11px] font-medium mb-1.5 block" style={{ color: '#71717A' }}>Steps</label>
        <div className="space-y-2 mb-3">
          {steps.map((step, i) => (
            <StepEditor key={i} step={step} index={i} total={steps.length}
              onChange={s => updateStep(i, s)} onRemove={removeStep} onMove={moveStep} />
          ))}
          {steps.length === 0 && (
            <p className="text-xs text-center py-4" style={{ color: '#52525B' }}>Nenhum step. Adicione abaixo.</p>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {STEP_TYPES.map(s => (
            <button key={s.value} onClick={() => addStep(s.value)}
              className="text-[11px] px-2.5 py-1.5 rounded-lg border transition-colors hover:border-[#E5A800]/40"
              style={{ background: '#27272A', color: '#A1A1AA', borderColor: 'rgba(255,255,255,0.06)' }}>
              <i className={`fas ${s.icon} mr-1`} />{s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Preview */}
      {steps.length > 0 && (
        <div className="mb-4">
          <label className="text-[11px] font-medium mb-1.5 block" style={{ color: '#71717A' }}>Preview</label>
          <div className="rounded-lg p-3 space-y-2" style={{ background: '#18181B', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="flex items-start gap-2">
              <span className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] shrink-0" style={{ background: '#3B82F6', color: '#fff' }}>U</span>
              <div className="rounded-lg px-3 py-1.5 text-xs" style={{ background: '#27272A', color: '#A1A1AA' }}>
                {triggerType === 'greeting' ? 'Oi, bom dia!' : triggerType === 'keyword' ? (keywords.split(',')[0]?.trim() || '...') : triggerType === 'exact' ? (exactText || '...') : 'Qualquer mensagem'}
              </div>
            </div>
            {steps.map((step, i) => {
              if (step.type === 'send_message' || step.type === 'transfer_to_agent') {
                return (
                  <div key={i} className="flex items-start gap-2 justify-end">
                    <div className="rounded-lg px-3 py-1.5 text-xs" style={{ background: '#E5A800', color: '#000' }}>
                      {step.content || step.message || (step.type === 'transfer_to_agent' ? 'Transferindo...' : '...')}
                    </div>
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] shrink-0" style={{ background: '#E5A800', color: '#000' }}>B</span>
                  </div>
                )
              }
              if (step.type === 'wait_response') {
                return (
                  <div key={i} className="text-center">
                    <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: '#27272A', color: '#71717A' }}>
                      <i className="fas fa-clock mr-1" />Aguarda resposta
                    </span>
                  </div>
                )
              }
              if (step.type === 'lookup_order') {
                return (
                  <div key={i} className="text-center">
                    <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: '#27272A', color: '#71717A' }}>
                      <i className="fas fa-search mr-1" />Busca pedido
                    </span>
                  </div>
                )
              }
              if (step.type === 'suggest_article') {
                return (
                  <div key={i} className="text-center">
                    <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: '#27272A', color: '#71717A' }}>
                      <i className="fas fa-book mr-1" />Sugere artigo
                    </span>
                  </div>
                )
              }
              return null
            })}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 pt-2 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <button onClick={onCancel} className="text-xs px-4 py-2 rounded-lg transition-colors" style={{ color: '#A1A1AA' }}>
          Cancelar
        </button>
        <button onClick={handleSave} disabled={!name.trim() || saving}
          className="text-xs px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
          style={{ background: '#E5A800', color: '#000' }}>
          {saving ? 'Salvando...' : flow?.id ? 'Salvar' : 'Criar Flow'}
        </button>
      </div>
    </div>
  )
}

export default function ChatbotFlowsPage() {
  const [flows, setFlows] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null) // null = list, 'new' = new, flow obj = editing
  const [importText, setImportText] = useState('')
  const [showImport, setShowImport] = useState(false)

  const loadFlows = useCallback(async () => {
    try {
      const res = await api.get('/chatbot/flows')
      setFlows(res.data)
    } catch (e) {
      console.error('Failed to load flows', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadFlows() }, [loadFlows])

  const handleSave = async (payload) => {
    if (editing && editing !== 'new' && editing.id) {
      await api.put(`/chatbot/flows/${editing.id}`, payload)
    } else {
      await api.post('/chatbot/flows', payload)
    }
    setEditing(null)
    loadFlows()
  }

  const handleToggle = async (flow) => {
    await api.put(`/chatbot/flows/${flow.id}`, { ...flow, active: !flow.active, trigger_config: flow.trigger_config || {}, steps: flow.steps || [] })
    loadFlows()
  }

  const handleDelete = async (flow) => {
    if (!confirm(`Excluir "${flow.name}"?`)) return
    await api.delete(`/chatbot/flows/${flow.id}`)
    loadFlows()
  }

  const handleImport = async () => {
    try {
      const data = JSON.parse(importText)
      const flowsToImport = Array.isArray(data) ? data : [data]
      for (const f of flowsToImport) {
        const payload = {
          name: f.name || 'Flow importado',
          trigger_type: f.trigger_type || 'any',
          trigger_config: f.trigger_config || {},
          steps: f.steps || [],
          active: f.active ?? true,
        }
        await api.post('/chatbot/flows', payload)
      }
      setImportText('')
      setShowImport(false)
      loadFlows()
    } catch {
      alert('JSON invalido. Cole um JSON valido de flow.')
    }
  }

  if (loading) {
    return (
      <div className="p-6 max-w-3xl mx-auto space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="rounded-xl h-20 animate-pulse" style={{ background: '#1F1F23' }} />
        ))}
      </div>
    )
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold" style={{ color: '#E4E4E7' }}>Chatbot Flows</h1>
          <p className="text-xs" style={{ color: '#71717A' }}>Configure respostas automaticas do chatbot</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowImport(!showImport)}
            className="text-xs px-3 py-2 rounded-lg border transition-colors hover:border-[#E5A800]/40"
            style={{ background: '#27272A', color: '#A1A1AA', borderColor: 'rgba(255,255,255,0.06)' }}>
            <i className="fas fa-file-import mr-1.5" />Importar
          </button>
          <button onClick={() => setEditing('new')}
            className="text-xs px-3 py-2 rounded-lg font-medium transition-colors"
            style={{ background: '#E5A800', color: '#000' }}>
            <i className="fas fa-plus mr-1.5" />Novo Flow
          </button>
        </div>
      </div>

      {showImport && (
        <div className="rounded-xl border p-4 mb-4" style={{ background: '#1F1F23', borderColor: 'rgba(255,255,255,0.06)' }}>
          <label className="text-[11px] font-medium mb-1.5 block" style={{ color: '#71717A' }}>Importar JSON (Reportana ou outro)</label>
          <textarea value={importText} onChange={e => setImportText(e.target.value)}
            placeholder='Cole o JSON do flow aqui... {"name": "...", "trigger_type": "...", "steps": [...]}'
            rows={5} className="w-full text-xs rounded-lg px-3 py-2 mb-2 resize-none outline-none font-mono"
            style={{ background: '#27272A', color: '#E4E4E7', border: '1px solid rgba(255,255,255,0.06)' }} />
          <div className="flex items-center gap-2 justify-end">
            <button onClick={() => { setShowImport(false); setImportText('') }} className="text-xs px-3 py-1.5 rounded-lg" style={{ color: '#A1A1AA' }}>
              Cancelar
            </button>
            <button onClick={handleImport} disabled={!importText.trim()}
              className="text-xs px-3 py-1.5 rounded-lg font-medium disabled:opacity-50"
              style={{ background: '#E5A800', color: '#000' }}>
              Importar
            </button>
          </div>
        </div>
      )}

      {editing ? (
        <FlowEditor flow={editing === 'new' ? null : editing} onSave={handleSave} onCancel={() => setEditing(null)} />
      ) : (
        <div className="space-y-2">
          {flows.length === 0 ? (
            <div className="text-center py-16">
              <i className="fas fa-robot text-3xl mb-3 block" style={{ color: '#27272A' }} />
              <p className="text-sm font-medium mb-1" style={{ color: '#52525B' }}>Nenhum flow configurado</p>
              <p className="text-xs mb-4" style={{ color: '#3F3F46' }}>Crie um flow para o chatbot responder automaticamente</p>
              <button onClick={() => setEditing('new')}
                className="text-xs px-4 py-2 rounded-lg font-medium"
                style={{ background: '#E5A800', color: '#000' }}>
                <i className="fas fa-plus mr-1.5" />Criar primeiro flow
              </button>
            </div>
          ) : (
            flows.map(f => <FlowCard key={f.id} flow={f} onEdit={setEditing} onToggle={handleToggle} onDelete={handleDelete} />)
          )}
        </div>
      )}
    </div>
  )
}
