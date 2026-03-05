import React, { useState, useEffect } from 'react'
import { useToast } from '../components/Toast'
import { getUsers, getMe, changePassword } from '../services/api'
import api from '../services/api'
const SECTIONS = [
  { id: 'profile', label: 'Meu Perfil', icon: 'fa-user' },
  { id: 'tickets', label: 'Tickets', icon: 'fa-ticket' },
  { id: 'sla', label: 'SLA', icon: 'fa-clock' },
  { id: 'business_hours', label: 'Horário de Atendimento', icon: 'fa-business-time' },
  { id: 'agents', label: 'Equipe', icon: 'fa-users' },
  { id: 'macros', label: 'Respostas Rápidas', icon: 'fa-bolt' },
  { id: 'shortcuts', label: 'Atalhos de Teclado', icon: 'fa-keyboard' },
  { id: 'security', label: 'Segurança', icon: 'fa-shield-alt' },
  { id: 'changelog', label: 'Changelog', icon: 'fa-code-branch' },
]

const CHANGELOG = [
  {
    date: '26/02/2026',
    title: 'Permissões e Roles',
    items: [
      { type: 'fix', text: 'Agentes agora têm acesso a todos os tickets (antes só viam os atribuídos)' },
      { type: 'change', text: 'Pedro e Lyvia como Super Admin; Victor e Tauane como Supervisor' },
    ],
  },
  {
    date: '25/02/2026',
    title: 'Análise de Equipe + Overhaul Visual',
    items: [
      { type: 'new', text: 'Página Análise de Equipe — métricas quantitativas e análise qualitativa com IA por agente' },
      { type: 'new', text: 'Relatórios semanais automáticos de performance (todo domingo)' },
      { type: 'new', text: 'Design system completo: dark theme + paleta dourada Carbon' },
      { type: 'new', text: 'Command Palette (Ctrl+K) para busca rápida' },
      { type: 'new', text: 'Notificações real-time com sino e toast' },
      { type: 'new', text: 'Skeleton loading em todas as páginas' },
      { type: 'new', text: 'Leaderboard com gamificação: pontos, ranking, streaks' },
      { type: 'new', text: 'Sistema de recompensas com resgate por pontos' },
    ],
  },
  {
    date: '24/02/2026',
    title: 'Helpdesk 100% + Performance',
    items: [
      { type: 'new', text: 'Protocolo automático por ticket (CARBON-YYYYMMDD-XXXX)' },
      { type: 'new', text: 'Notas internas (sticky) e notas do fornecedor' },
      { type: 'new', text: 'Merge de tickets duplicados do mesmo cliente' },
      { type: 'new', text: 'CC/BCC em emails e agendamento de envio' },
      { type: 'new', text: 'Busca ampla: assunto, número, nome, email, tracking, conteúdo' },
      { type: 'new', text: 'Blacklist de clientes com motivo e tags' },
      { type: 'new', text: 'Rastreamento integrado (LinkeTrack + 17Track)' },
      { type: 'perf', text: 'Índices compostos para queries frequentes no banco' },
      { type: 'perf', text: 'Ordenação por data real do email (received_at)' },
    ],
  },
  {
    date: '23/02/2026',
    title: 'Canais Meta + Correções',
    items: [
      { type: 'new', text: 'WhatsApp Business — receber e responder mensagens via API' },
      { type: 'new', text: 'Instagram DM — receber e responder mensagens diretas' },
      { type: 'new', text: 'Facebook Messenger — receber e responder mensagens' },
      { type: 'new', text: 'Moderação de comentários sociais com IA (auto-reply, auto-hide)' },
      { type: 'new', text: 'Auto-resposta por IA nos canais Meta com toggle on/off por ticket' },
      { type: 'fix', text: 'Correções de CSS, configurações e estabilidade geral' },
    ],
  },
  {
    date: '22/02/2026',
    title: 'E-Commerce + Deploy',
    items: [
      { type: 'new', text: 'Integração Yampi — pedidos, detalhes e rastreio' },
      { type: 'new', text: 'Integração Appmax — vendas, detalhes e transações' },
      { type: 'new', text: 'Integração Shopify' },
      { type: 'new', text: 'API unificada de e-commerce com normalização de status' },
      { type: 'new', text: 'Deploy automatizado: Docker + Nginx + DigitalOcean' },
      { type: 'new', text: 'Health check com monitoramento de email e créditos IA' },
    ],
  },
  {
    date: 'Base',
    title: 'Sistema Core',
    items: [
      { type: 'new', text: 'Tickets com 11 status, 4 prioridades, SLA automático e escalação' },
      { type: 'new', text: 'Gmail bidirecional — fetch automático a cada 60s' },
      { type: 'new', text: 'IA (Claude) — triagem, categorização, sentimento, risco jurídico, resumo' },
      { type: 'new', text: 'Dashboard em tempo real com contadores e métricas' },
      { type: 'new', text: 'Base de Conhecimento, Biblioteca de Mídia e Catálogo' },
      { type: 'new', text: 'Assistente IA para consultas da equipe' },
      { type: 'new', text: 'CSAT — pesquisa de satisfação por email' },
      { type: 'new', text: 'WebSocket para notificações real-time' },
      { type: 'new', text: 'Roles: Super Admin, Admin, Supervisor, Agente' },
      { type: 'new', text: 'Slack — notificações e alertas' },
    ],
  },
]

const SPECIALTY_OPTIONS = [
  { value: 'geral', label: 'Geral' },
  { value: 'tecnico', label: 'Técnico' },
  { value: 'logistica', label: 'Logística' },
  { value: 'juridico', label: 'Jurídico' },
  { value: 'financeiro', label: 'Financeiro' },
]

const DEFAULT_PREFS = {
  notifications_sound: true,
  notifications_desktop: true,
  notifications_new_ticket: true,
  notifications_assignment: true,
  notifications_escalation: true,
  notifications_sla_warning: true,
  auto_refresh_interval: 30,
  tickets_per_page: 20,
  default_tab: 'active',
  compact_mode: false,
  show_preview_on_hover: true,
  auto_assign_on_create: false,
  font_size: 'medium',
  sidebar_collapsed: false,
  show_timer: true,
  show_ai_suggestions: true,
  reply_signature: '',
}

export default function SettingsPage({ user }) {
  const toast = useToast()
  const [section, setSection] = useState('profile')
  const [agents, setAgents] = useState([])
  const [macros, setMacros] = useState([])
  const [prefs, setPrefs] = useState(() => {
    const saved = localStorage.getItem('carbon_prefs')
    return saved ? { ...DEFAULT_PREFS, ...JSON.parse(saved) } : DEFAULT_PREFS
  })
  const [profileName, setProfileName] = useState(user?.name || '')
  const [emailSignature, setEmailSignature] = useState(user?.email_signature || '')
  const [saving, setSaving] = useState(false)
  const [newMacroName, setNewMacroName] = useState('')
  const [newMacroContent, setNewMacroContent] = useState('')
  const [newMacroActions, setNewMacroActions] = useState([])
  const [editingMacro, setEditingMacro] = useState(null)
  const [showAddMember, setShowAddMember] = useState(false)
  const [newMember, setNewMember] = useState({ name: '', email: '', password: '', role: 'agent', specialty: 'geral' })
  const [addingMember, setAddingMember] = useState(false)
  const [pwCurrent, setPwCurrent] = useState('')
  const [pwNew, setPwNew] = useState('')
  const [pwConfirm, setPwConfirm] = useState('')
  const [changingPw, setChangingPw] = useState(false)
  const [resetPwAgent, setResetPwAgent] = useState(null)
  const [resetPwValue, setResetPwValue] = useState('')
  const [resettingPw, setResettingPw] = useState(false)

  const DEFAULT_BH = {
    timezone: 'America/Sao_Paulo',
    auto_reply_enabled: true,
    auto_reply_message: 'Olá! Nosso horário de atendimento humanizado é de segunda a sexta, das 09:00 às 18:00. Recebemos sua mensagem e responderemos assim que possível no próximo dia útil. Obrigado pela compreensão!',
    days: {
      seg: { active: true, start: '09:00', end: '18:00' },
      ter: { active: true, start: '09:00', end: '18:00' },
      qua: { active: true, start: '09:00', end: '18:00' },
      qui: { active: true, start: '09:00', end: '18:00' },
      sex: { active: true, start: '09:00', end: '18:00' },
      sab: { active: false, start: '09:00', end: '13:00' },
      dom: { active: false, start: '', end: '' },
    },
  }
  const [businessHours, setBusinessHours] = useState(() => {
    const saved = localStorage.getItem('carbon_business_hours')
    return saved ? { ...DEFAULT_BH, ...JSON.parse(saved) } : DEFAULT_BH
  })
  const [bhSaving, setBhSaving] = useState(false)

  const updateBH = (update) => {
    const updated = { ...businessHours, ...update }
    setBusinessHours(updated)
  }
  const updateBHDay = (day, field, value) => {
    const updated = { ...businessHours, days: { ...businessHours.days, [day]: { ...businessHours.days[day], [field]: value } } }
    setBusinessHours(updated)
  }
  const saveBH = async () => {
    setBhSaving(true)
    try {
      await api.post('/settings/business-hours', businessHours)
      localStorage.setItem('carbon_business_hours', JSON.stringify(businessHours))
      toast.success('Horário de atendimento salvo!')
    } catch {
      // Backend endpoint may not exist yet, save locally
      localStorage.setItem('carbon_business_hours', JSON.stringify(businessHours))
      toast.success('Salvo localmente!')
    }
    setBhSaving(false)
  }

  useEffect(() => {
    if (isAdmin) {
      getUsers().then(r => setAgents(r.data)).catch(() => {})
    }
    api.get('/kb/macros').then(r => setMacros(r.data)).catch(() => {})
  }, [])

  const updatePref = (key, value) => {
    const updated = { ...prefs, [key]: value }
    setPrefs(updated)
    localStorage.setItem('carbon_prefs', JSON.stringify(updated))
  }

  const saveProfile = async () => {
    setSaving(true)
    try {
      await api.patch('/auth/me', { name: profileName, email_signature: emailSignature })
      toast.success('Perfil atualizado!')
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao salvar') }
    finally { setSaving(false) }
  }

  const updateAgent = async (agentId, data) => {
    try {
      await api.patch(`/auth/users/${agentId}`, data)
      const { data: updated } = await getUsers()
      setAgents(updated)
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro') }
  }

  const addMember = async () => {
    if (!newMember.name.trim() || !newMember.email.trim() || !newMember.password.trim()) {
      toast.warning('Preencha nome, e-mail e senha')
      return
    }
    setAddingMember(true)
    try {
      await api.post('/auth/users', newMember)
      const { data: updated } = await getUsers()
      setAgents(updated)
      setNewMember({ name: '', email: '', password: '', role: 'agent', specialty: 'geral' })
      setShowAddMember(false)
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao criar membro') }
    finally { setAddingMember(false) }
  }

  const resetPassword = async () => {
    if (!resetPwValue.trim() || resetPwValue.length < 6) {
      toast.warning('A senha deve ter pelo menos 6 caracteres')
      return
    }
    setResettingPw(true)
    try {
      const res = await api.post(`/auth/users/${resetPwAgent.id}/reset-password`, { new_password: resetPwValue })
      toast.success(res.data.message || 'Senha resetada!')
      setResetPwAgent(null)
      setResetPwValue('')
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao resetar senha') }
    finally { setResettingPw(false) }
  }

  const removeMember = async (agentId, agentName) => {
    if (!confirm(`Tem certeza que deseja remover ${agentName}? Esta ação não pode ser desfeita.`)) return
    try {
      await api.delete(`/auth/users/${agentId}`)
      const { data: updated } = await getUsers()
      setAgents(updated)
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao remover') }
  }

  const addMacroAction = (list, setter) => {
    setter([...list, { type: 'set_status', value: '' }])
  }
  const removeMacroAction = (list, setter, idx) => {
    setter(list.filter((_, i) => i !== idx))
  }
  const updateMacroAction = (list, setter, idx, field, val) => {
    const updated = [...list]
    updated[idx] = { ...updated[idx], [field]: val }
    setter(updated)
  }

  const addMacro = async () => {
    if (!newMacroName.trim() || !newMacroContent.trim()) return
    try {
      const actions = newMacroActions.filter(a => a.value.trim())
      await api.post('/kb/macros', { name: newMacroName, content: newMacroContent, category: 'geral', actions: actions.length ? actions : null })
      const { data } = await api.get('/kb/macros')
      setMacros(data)
      setNewMacroName(''); setNewMacroContent(''); setNewMacroActions([])
    } catch (e) { toast.error('Erro ao criar macro') }
  }

  const saveMacroEdit = async () => {
    if (!editingMacro) return
    try {
      const actions = (editingMacro.actions || []).filter(a => a.value?.trim())
      await api.patch(`/kb/macros/${editingMacro.id}`, {
        name: editingMacro.name, content: editingMacro.content,
        actions: actions.length ? actions : null
      })
      const { data } = await api.get('/kb/macros')
      setMacros(data); setEditingMacro(null)
    } catch (e) { toast.error('Erro ao salvar') }
  }

  const deleteMacro = async (id) => {
    if (!confirm('Excluir esta resposta rápida?')) return
    try {
      await api.delete(`/kb/macros/${id}`)
      setMacros(macros.filter(m => m.id !== id))
    } catch (e) { toast.error('Erro ao excluir') }
  }

  const handleChangePassword = async () => {
    if (!pwCurrent || !pwNew) return toast.error('Preencha todos os campos')
    if (pwNew !== pwConfirm) return toast.error('As senhas não coincidem')
    if (pwNew.length < 6) return toast.error('Nova senha deve ter pelo menos 6 caracteres')
    setChangingPw(true)
    try {
      await changePassword(pwCurrent, pwNew)
      toast.success('Senha alterada com sucesso')
      setPwCurrent(''); setPwNew(''); setPwConfirm('')
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao alterar senha')
    } finally { setChangingPw(false) }
  }

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'
  const isSuperAdmin = user?.role === 'super_admin'

  return (
    <div className="p-6 flex gap-6">
      {/* Nav lateral */}
      <div className="w-56 shrink-0">
        <h1 className="text-xl font-bold text-white mb-4"><i className="fas fa-cog mr-2" />Configurações</h1>
        <nav className="space-y-1">
          {SECTIONS.filter(s => {
            if (s.id === 'agents' && !isSuperAdmin) return false
            if (s.id === 'sla' && !isAdmin) return false
            if (s.id === 'business_hours' && !isAdmin) return false
            return true
          }).map(s => (
            <button key={s.id} onClick={() => setSection(s.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                section === s.id ? 'bg-indigo-600/20 text-indigo-400' : 'text-carbon-300 hover:bg-carbon-700 hover:text-white'
              }`}>
              <i className={`fas ${s.icon} w-5 text-center`} />
              {s.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Conteúdo */}
      <div className="flex-1 max-w-3xl">

        {/* ── Meu Perfil ── */}
        {section === 'profile' && (
          <SettingsSection title="Meu Perfil" icon="fa-user">
            <Field label="Nome">
              <input value={profileName} onChange={e => setProfileName(e.target.value)}
                className="settings-input" />
            </Field>
            <Field label="E-mail">
              <input value={user?.email || ''} disabled className="settings-input opacity-60" />
            </Field>
            <Field label="Cargo">
              <input value={{ super_admin: 'Super Admin', admin: 'Administrador', supervisor: 'Supervisor', agent: 'Agente' }[user?.role] || user?.role} disabled className="settings-input opacity-60" />
            </Field>
            <Field label="Assinatura de E-mail">
              <textarea value={emailSignature} onChange={e => setEmailSignature(e.target.value)}
                rows={4} placeholder={"Ex:\nAtenciosamente,\nJoão Silva\nSuporte Carbon Smartwatch\n(11) 99999-9999"} className="settings-input" />
              <p className="text-carbon-500 text-xs mt-1">Adicionada automaticamente ao final de cada e-mail enviado. Cada agente pode ter a sua.</p>
            </Field>
            <button onClick={saveProfile} disabled={saving}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm mt-3 disabled:opacity-50">
              {saving ? 'Salvando...' : 'Salvar Perfil'}
            </button>
          </SettingsSection>
        )}


        {/* ── Tickets ── */}
        {section === 'tickets' && (
          <SettingsSection title="Tickets" icon="fa-ticket">
            <Field label="Tickets por Página">
              <select value={prefs.tickets_per_page} onChange={e => updatePref('tickets_per_page', Number(e.target.value))} className="settings-input">
                {[10, 20, 30, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </Field>
            <Field label="Aba Padrão">
              <select value={prefs.default_tab} onChange={e => updatePref('default_tab', e.target.value)} className="settings-input">
                <option value="active">Abertos</option>
                <option value="escalated">Escalados</option>
                <option value="resolved">Resolvidos</option>
                <option value="all">Todos</option>
              </select>
            </Field>
            <Field label="Atualização Automática (segundos)">
              <select value={prefs.auto_refresh_interval} onChange={e => updatePref('auto_refresh_interval', Number(e.target.value))} className="settings-input">
                <option value={0}>Desativado</option>
                <option value={15}>15 segundos</option>
                <option value={30}>30 segundos</option>
                <option value={60}>1 minuto</option>
                <option value={120}>2 minutos</option>
              </select>
            </Field>
            <Toggle label="Preview ao Passar o Mouse" description="Mostra prévia do ticket ao passar o mouse" value={prefs.show_preview_on_hover} onChange={v => updatePref('show_preview_on_hover', v)} />
            <Toggle label="Mostrar Timer de Atendimento" description="Cronômetro mostrando tempo no ticket" value={prefs.show_timer} onChange={v => updatePref('show_timer', v)} />
            <Toggle label="Sugestões de IA" description="Mostrar sugestões automáticas da IA" value={prefs.show_ai_suggestions} onChange={v => updatePref('show_ai_suggestions', v)} />
            {isAdmin && (
              <Toggle label="Auto-Atribuir ao Criar" description="Atribuir automaticamente tickets novos" value={prefs.auto_assign_on_create} onChange={v => updatePref('auto_assign_on_create', v)} />
            )}
          </SettingsSection>
        )}

        {/* ── SLA (admin) ── */}
        {section === 'sla' && isAdmin && (
          <SettingsSection title="Configurações de SLA" icon="fa-clock">
            <p className="text-carbon-400 text-sm mb-4">Defina os prazos de SLA por prioridade. Os valores são em horas.</p>
            {[
              { key: 'urgent', label: 'Urgente', color: 'text-red-400' },
              { key: 'high', label: 'Alta', color: 'text-orange-400' },
              { key: 'medium', label: 'Média', color: 'text-blue-400' },
              { key: 'low', label: 'Baixa', color: 'text-gray-400' },
            ].map(p => (
              <Field key={p.key} label={<span className={p.color}>{p.label}</span>}>
                <div className="flex gap-3 items-center">
                  <div>
                    <label className="text-carbon-500 text-xs">Resposta (h)</label>
                    <input type="number" defaultValue={{ urgent: 1, high: 2, medium: 4, low: 8 }[p.key]}
                      className="settings-input w-24" />
                  </div>
                  <div>
                    <label className="text-carbon-500 text-xs">Resolução (h)</label>
                    <input type="number" defaultValue={{ urgent: 4, high: 8, medium: 24, low: 48 }[p.key]}
                      className="settings-input w-24" />
                  </div>
                </div>
              </Field>
            ))}
            <p className="text-carbon-500 text-xs mt-2">Para aplicar, edite o arquivo .env ou reinicie o backend.</p>
          </SettingsSection>
        )}

        {/* ── Horário de Atendimento (admin) ── */}
        {section === 'business_hours' && isAdmin && (
          <SettingsSection title="Horário de Atendimento" icon="fa-business-time">
            <p className="text-carbon-400 text-sm mb-4">
              Configure os dias e horários em que sua equipe atende. Fora desse horário, uma resposta automática será enviada aos clientes.
            </p>

            {/* Dias da semana */}
            <div className="space-y-2 mb-6">
              {[
                { key: 'seg', label: 'Segunda-feira' },
                { key: 'ter', label: 'Terça-feira' },
                { key: 'qua', label: 'Quarta-feira' },
                { key: 'qui', label: 'Quinta-feira' },
                { key: 'sex', label: 'Sexta-feira' },
                { key: 'sab', label: 'Sábado' },
                { key: 'dom', label: 'Domingo' },
              ].map(d => {
                const day = businessHours.days[d.key]
                return (
                  <div key={d.key} className="bg-carbon-700 rounded-lg px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-[160px]">
                      <button onClick={() => updateBHDay(d.key, 'active', !day.active)}
                        className={`w-9 h-5 rounded-full transition relative ${day.active ? 'bg-indigo-600' : 'bg-carbon-600'}`}>
                        <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${day.active ? 'left-4' : 'left-0.5'}`} />
                      </button>
                      <span className={`text-sm ${day.active ? 'text-white' : 'text-carbon-500'}`}>{d.label}</span>
                    </div>
                    {day.active ? (
                      <div className="flex items-center gap-2">
                        <input type="time" value={day.start} onChange={e => updateBHDay(d.key, 'start', e.target.value)}
                          className="settings-input-sm w-28 text-center" />
                        <span className="text-carbon-500 text-xs">até</span>
                        <input type="time" value={day.end} onChange={e => updateBHDay(d.key, 'end', e.target.value)}
                          className="settings-input-sm w-28 text-center" />
                      </div>
                    ) : (
                      <span className="text-carbon-500 text-xs italic">Fechado</span>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Fuso horário */}
            <Field label="Fuso Horário">
              <select value={businessHours.timezone} onChange={e => updateBH({ timezone: e.target.value })}
                className="settings-input">
                <option value="America/Sao_Paulo">Brasília (GMT-3)</option>
                <option value="America/Manaus">Manaus (GMT-4)</option>
                <option value="America/Cuiaba">Cuiabá (GMT-4)</option>
                <option value="America/Belem">Belém (GMT-3)</option>
                <option value="America/Fortaleza">Fortaleza (GMT-3)</option>
                <option value="America/Recife">Recife (GMT-3)</option>
                <option value="America/Noronha">Fernando de Noronha (GMT-2)</option>
                <option value="America/Rio_Branco">Rio Branco (GMT-5)</option>
              </select>
            </Field>

            {/* Auto-reply */}
            <div className="border-t border-carbon-700 pt-4 mt-4">
              <Toggle label="Resposta Automática Fora do Horário"
                description="Enviar mensagem automática quando cliente entrar em contato fora do expediente"
                value={businessHours.auto_reply_enabled}
                onChange={v => updateBH({ auto_reply_enabled: v })} />

              {businessHours.auto_reply_enabled && (
                <Field label="Mensagem Automática">
                  <textarea value={businessHours.auto_reply_message}
                    onChange={e => updateBH({ auto_reply_message: e.target.value })}
                    rows={4} className="settings-input"
                    placeholder="Mensagem enviada automaticamente fora do horário..." />
                  <p className="text-carbon-500 text-xs mt-1">
                    Variáveis disponíveis: <code className="text-indigo-400">{'{{cliente}}'}</code>, <code className="text-indigo-400">{'{{horario_abertura}}'}</code>, <code className="text-indigo-400">{'{{proximo_dia}}'}</code>
                  </p>
                </Field>
              )}
            </div>

            <button onClick={saveBH} disabled={bhSaving}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm mt-4 disabled:opacity-50">
              <i className="fas fa-save mr-2" />{bhSaving ? 'Salvando...' : 'Salvar Horário'}
            </button>
          </SettingsSection>
        )}

        {/* ── Equipe (admin) ── */}
        {section === 'agents' && isSuperAdmin && (
          <SettingsSection title="Gerenciar Equipe" icon="fa-users">
            {/* Botão Adicionar */}
            <button onClick={() => setShowAddMember(!showAddMember)}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm mb-4">
              <i className={`fas ${showAddMember ? 'fa-times' : 'fa-plus'} mr-2`} />
              {showAddMember ? 'Cancelar' : 'Adicionar Membro'}
            </button>

            {/* Formulário Novo Membro */}
            {showAddMember && (
              <div className="bg-carbon-700 rounded-lg p-4 mb-4 space-y-3">
                <p className="text-white text-sm font-medium"><i className="fas fa-user-plus mr-2 text-green-400" />Novo Membro</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-carbon-500 text-xs">Nome</label>
                    <input value={newMember.name} onChange={e => setNewMember({...newMember, name: e.target.value})}
                      placeholder="Nome completo" className="settings-input" />
                  </div>
                  <div>
                    <label className="text-carbon-500 text-xs">E-mail</label>
                    <input value={newMember.email} onChange={e => setNewMember({...newMember, email: e.target.value})}
                      placeholder="email@empresa.com" className="settings-input" />
                  </div>
                  <div>
                    <label className="text-carbon-500 text-xs">Senha</label>
                    <input type="password" value={newMember.password} onChange={e => setNewMember({...newMember, password: e.target.value})}
                      placeholder="Senha inicial" className="settings-input" />
                  </div>
                  <div>
                    <label className="text-carbon-500 text-xs">Cargo</label>
                    <select value={newMember.role} onChange={e => setNewMember({...newMember, role: e.target.value})}
                      className="settings-input">
                      <option value="agent">Agente</option>
                      <option value="supervisor">Supervisor</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                </div>
                <button onClick={addMember} disabled={addingMember}
                  className="bg-green-600 hover:bg-green-500 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">
                  {addingMember ? 'Criando...' : 'Criar Membro'}
                </button>
              </div>
            )}

            {/* Lista de Membros */}
            <div className="space-y-3">
              {agents.map(agent => (
                <div key={agent.id} className="bg-carbon-700 rounded-lg p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold">
                      {agent.name[0]}
                    </div>
                    <div>
                      <p className="text-white text-sm font-medium">{agent.name}</p>
                      <p className="text-carbon-400 text-xs">{agent.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {agent.role === 'super_admin' ? (
                      <span className="px-2 py-1 rounded text-xs bg-yellow-600/20 text-yellow-400 font-medium">Super Admin</span>
                    ) : (
                      <select value={agent.role || 'agent'} onChange={e => updateAgent(agent.id, { role: e.target.value })}
                        className="settings-input-sm">
                        <option value="agent">Agente</option>
                        <option value="supervisor">Supervisor</option>
                        <option value="admin">Admin</option>
                      </select>
                    )}
                    <select value={agent.specialty || 'geral'} onChange={e => updateAgent(agent.id, { specialty: e.target.value })}
                      className="settings-input-sm">
                      {SPECIALTY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                    <div className="flex items-center gap-1">
                      <label className="text-carbon-500 text-xs">Max:</label>
                      <input type="number" value={agent.max_tickets || 20} min={1} max={100}
                        onChange={e => updateAgent(agent.id, { max_tickets: Number(e.target.value) })}
                        className="settings-input-sm w-16" />
                    </div>
                    <button onClick={() => updateAgent(agent.id, { is_active: !agent.is_active })}
                      className={`px-2 py-1 rounded text-xs ${agent.is_active ? 'bg-green-600/20 text-green-400' : 'bg-red-600/20 text-red-400'}`}>
                      {agent.is_active ? 'Ativo' : 'Inativo'}
                    </button>
                    {agent.id !== user?.id && (
                      <>
                        <button onClick={() => { setResetPwAgent(agent); setResetPwValue('') }}
                          className="text-yellow-400 hover:text-yellow-300 ml-1" title="Resetar senha">
                          <i className="fas fa-key text-xs" />
                        </button>
                        <button onClick={() => removeMember(agent.id, agent.name)}
                          className="text-red-400 hover:text-red-300 ml-1" title="Remover membro">
                          <i className="fas fa-trash text-xs" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </SettingsSection>
        )}

        {/* Modal Resetar Senha */}
        {resetPwAgent && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setResetPwAgent(null)}>
            <div className="bg-carbon-800 rounded-xl p-6 w-full max-w-sm shadow-xl" onClick={e => e.stopPropagation()}>
              <p className="text-white text-sm font-medium mb-1">
                <i className="fas fa-key mr-2 text-yellow-400" />Resetar Senha
              </p>
              <p className="text-carbon-400 text-xs mb-4">{resetPwAgent.name} ({resetPwAgent.email})</p>
              <input type="password" value={resetPwValue} onChange={e => setResetPwValue(e.target.value)}
                placeholder="Nova senha (mín. 6 caracteres)" className="settings-input mb-4 w-full"
                onKeyDown={e => e.key === 'Enter' && resetPassword()} autoFocus />
              <div className="flex gap-2 justify-end">
                <button onClick={() => setResetPwAgent(null)}
                  className="px-4 py-2 rounded-lg text-sm text-carbon-400 hover:text-white">
                  Cancelar
                </button>
                <button onClick={resetPassword} disabled={resettingPw}
                  className="bg-yellow-600 hover:bg-yellow-500 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">
                  {resettingPw ? 'Resetando...' : 'Resetar Senha'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Respostas Rápidas ── */}
        {section === 'macros' && (
          <SettingsSection title="Respostas Rápidas (Macros)" icon="fa-bolt">
            <p className="text-carbon-400 text-sm mb-4">
              Use variáveis: <code className="text-indigo-400">{'{{cliente}}'}</code>, <code className="text-indigo-400">{'{{numero}}'}</code>, <code className="text-indigo-400">{'{{rastreio}}'}</code>, <code className="text-indigo-400">{'{{categoria}}'}</code>.
              Adicione ações automáticas para mudar status, prioridade ou tags ao usar a macro.
            </p>

            {/* Nova macro */}
            <div className="bg-carbon-700 rounded-lg p-4 mb-4">
              <p className="text-white text-sm font-medium mb-3"><i className="fas fa-plus mr-2 text-green-400" />Nova Resposta Rápida</p>
              <input value={newMacroName} onChange={e => setNewMacroName(e.target.value)} placeholder="Nome (ex: Boas-vindas)"
                className="settings-input mb-2" />
              <textarea value={newMacroContent} onChange={e => setNewMacroContent(e.target.value)} rows={3}
                placeholder="Conteúdo (ex: Olá {{cliente}}, recebemos seu ticket #{{numero}}...)" className="settings-input" />

              {/* Actions */}
              <div className="mt-3">
                <p className="text-carbon-300 text-xs font-medium mb-2"><i className="fas fa-cog mr-1" />Ações automáticas (opcional)</p>
                {newMacroActions.map((action, idx) => (
                  <div key={idx} className="flex gap-2 mb-2 items-center">
                    <select value={action.type} onChange={e => updateMacroAction(newMacroActions, setNewMacroActions, idx, 'type', e.target.value)}
                      className="settings-input w-40 text-xs">
                      <option value="set_status">Mudar status</option>
                      <option value="set_priority">Mudar prioridade</option>
                      <option value="add_tag">Adicionar tag</option>
                      <option value="set_category">Mudar categoria</option>
                    </select>
                    {action.type === 'set_status' && (
                      <select value={action.value} onChange={e => updateMacroAction(newMacroActions, setNewMacroActions, idx, 'value', e.target.value)}
                        className="settings-input flex-1 text-xs">
                        <option value="">Selecione...</option>
                        <option value="open">Aberto</option>
                        <option value="waiting_customer">Aguardando cliente</option>
                        <option value="resolved">Resolvido</option>
                        <option value="escalated">Escalado</option>
                      </select>
                    )}
                    {action.type === 'set_priority' && (
                      <select value={action.value} onChange={e => updateMacroAction(newMacroActions, setNewMacroActions, idx, 'value', e.target.value)}
                        className="settings-input flex-1 text-xs">
                        <option value="">Selecione...</option>
                        <option value="low">Baixa</option>
                        <option value="medium">Média</option>
                        <option value="high">Alta</option>
                        <option value="urgent">Urgente</option>
                      </select>
                    )}
                    {(action.type === 'add_tag' || action.type === 'set_category') && (
                      <input value={action.value} onChange={e => updateMacroAction(newMacroActions, setNewMacroActions, idx, 'value', e.target.value)}
                        placeholder={action.type === 'add_tag' ? 'Nome da tag' : 'Categoria'}
                        className="settings-input flex-1 text-xs" />
                    )}
                    <button onClick={() => removeMacroAction(newMacroActions, setNewMacroActions, idx)}
                      className="text-red-400 hover:text-red-300 px-2"><i className="fas fa-times text-xs" /></button>
                  </div>
                ))}
                <button onClick={() => addMacroAction(newMacroActions, setNewMacroActions)}
                  className="text-indigo-400 hover:text-indigo-300 text-xs"><i className="fas fa-plus mr-1" />Adicionar ação</button>
              </div>

              <button onClick={addMacro} className="bg-green-600 hover:bg-green-500 text-white px-4 py-2 rounded-lg text-sm mt-3">
                <i className="fas fa-plus mr-1" />Criar
              </button>
            </div>

            {/* Lista */}
            <div className="space-y-2">
              {macros.map(m => (
                <div key={m.id} className="bg-carbon-700 rounded-lg p-3">
                  {editingMacro?.id === m.id ? (
                    <div>
                      <input value={editingMacro.name} onChange={e => setEditingMacro({...editingMacro, name: e.target.value})}
                        className="settings-input mb-2 text-sm" />
                      <textarea value={editingMacro.content} onChange={e => setEditingMacro({...editingMacro, content: e.target.value})}
                        rows={3} className="settings-input text-xs" />
                      <div className="mt-2">
                        <p className="text-carbon-300 text-xs font-medium mb-2"><i className="fas fa-cog mr-1" />Ações</p>
                        {(editingMacro.actions || []).map((action, idx) => (
                          <div key={idx} className="flex gap-2 mb-2 items-center">
                            <select value={action.type} onChange={e => {
                              const acts = [...(editingMacro.actions || [])]; acts[idx] = {...acts[idx], type: e.target.value}
                              setEditingMacro({...editingMacro, actions: acts})
                            }} className="settings-input w-40 text-xs">
                              <option value="set_status">Mudar status</option>
                              <option value="set_priority">Mudar prioridade</option>
                              <option value="add_tag">Adicionar tag</option>
                              <option value="set_category">Mudar categoria</option>
                            </select>
                            {action.type === 'set_status' && (
                              <select value={action.value || ''} onChange={e => {
                                const acts = [...(editingMacro.actions || [])]; acts[idx] = {...acts[idx], value: e.target.value}
                                setEditingMacro({...editingMacro, actions: acts})
                              }} className="settings-input flex-1 text-xs">
                                <option value="">Selecione...</option>
                                <option value="open">Aberto</option>
                                <option value="waiting_customer">Aguardando cliente</option>
                                <option value="resolved">Resolvido</option>
                                <option value="escalated">Escalado</option>
                              </select>
                            )}
                            {action.type === 'set_priority' && (
                              <select value={action.value || ''} onChange={e => {
                                const acts = [...(editingMacro.actions || [])]; acts[idx] = {...acts[idx], value: e.target.value}
                                setEditingMacro({...editingMacro, actions: acts})
                              }} className="settings-input flex-1 text-xs">
                                <option value="">Selecione...</option>
                                <option value="low">Baixa</option><option value="medium">Média</option>
                                <option value="high">Alta</option><option value="urgent">Urgente</option>
                              </select>
                            )}
                            {(action.type === 'add_tag' || action.type === 'set_category') && (
                              <input value={action.value || ''} onChange={e => {
                                const acts = [...(editingMacro.actions || [])]; acts[idx] = {...acts[idx], value: e.target.value}
                                setEditingMacro({...editingMacro, actions: acts})
                              }} className="settings-input flex-1 text-xs" />
                            )}
                            <button onClick={() => {
                              const acts = (editingMacro.actions || []).filter((_, i) => i !== idx)
                              setEditingMacro({...editingMacro, actions: acts})
                            }} className="text-red-400 hover:text-red-300 px-2"><i className="fas fa-times text-xs" /></button>
                          </div>
                        ))}
                        <button onClick={() => setEditingMacro({...editingMacro, actions: [...(editingMacro.actions || []), {type: 'set_status', value: ''}]})}
                          className="text-indigo-400 hover:text-indigo-300 text-xs"><i className="fas fa-plus mr-1" />Ação</button>
                      </div>
                      <div className="flex gap-2 mt-3">
                        <button onClick={saveMacroEdit} className="bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded text-xs">
                          <i className="fas fa-check mr-1" />Salvar</button>
                        <button onClick={() => setEditingMacro(null)} className="text-carbon-400 hover:text-carbon-300 text-xs px-3">Cancelar</button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-white text-sm font-medium">{m.name}</p>
                        <p className="text-carbon-400 text-xs mt-1 line-clamp-2">{m.content}</p>
                        {m.actions?.length > 0 && (
                          <div className="flex gap-1.5 mt-2 flex-wrap">
                            {m.actions.map((a, i) => (
                              <span key={i} className="bg-carbon-600 text-carbon-300 text-[10px] px-2 py-0.5 rounded-full">
                                <i className="fas fa-cog mr-1" />
                                {a.type === 'set_status' ? `Status → ${a.value}` :
                                 a.type === 'set_priority' ? `Prioridade → ${a.value}` :
                                 a.type === 'add_tag' ? `+Tag: ${a.value}` :
                                 a.type === 'set_category' ? `Categoria → ${a.value}` : a.type}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex gap-2 ml-3">
                        <button onClick={() => setEditingMacro({...m, actions: m.actions || []})} className="text-indigo-400 hover:text-indigo-300">
                          <i className="fas fa-edit text-xs" />
                        </button>
                        <button onClick={() => deleteMacro(m.id)} className="text-red-400 hover:text-red-300">
                          <i className="fas fa-trash text-xs" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {macros.length === 0 && (
                <p className="text-carbon-500 text-sm text-center py-6">Nenhuma resposta rápida cadastrada.</p>
              )}
            </div>
          </SettingsSection>
        )}

        {/* ── Atalhos ── */}
        {section === 'shortcuts' && (
          <SettingsSection title="Atalhos de Teclado" icon="fa-keyboard">
            <p className="text-carbon-400 text-sm mb-4">Atalhos disponíveis dentro de um ticket (funcionam quando não estiver digitando):</p>
            <div className="space-y-2">
              {[
                { keys: 'Alt + R', action: 'Resolver ticket' },
                { keys: 'Alt + E', action: 'Escalar ticket' },
                { keys: 'Alt + W', action: 'Aguardar cliente' },
                { keys: 'Alt + N', action: 'Próximo ticket da fila' },
                { keys: 'Alt + S', action: 'Sugerir resposta com IA' },
                { keys: 'Alt + F', action: 'Focar no campo de resposta' },
                { keys: 'Ctrl + Enter', action: 'Enviar resposta' },
              ].map(s => (
                <div key={s.keys} className="bg-carbon-700 rounded-lg px-4 py-3 flex items-center justify-between">
                  <span className="text-white text-sm">{s.action}</span>
                  <kbd className="bg-carbon-800 border border-carbon-600 text-indigo-400 px-3 py-1 rounded text-xs font-mono">{s.keys}</kbd>
                </div>
              ))}
            </div>
          </SettingsSection>
        )}

        {/* ── Segurança ── */}
        {section === 'security' && (
          <SettingsSection title="Segurança" icon="fa-shield-alt">
            <Field label="Alterar Senha">
              <input type="password" placeholder="Senha atual" value={pwCurrent} onChange={e => setPwCurrent(e.target.value)} className="settings-input mb-2" />
              <input type="password" placeholder="Nova senha" value={pwNew} onChange={e => setPwNew(e.target.value)} className="settings-input mb-2" />
              <input type="password" placeholder="Confirmar nova senha" value={pwConfirm} onChange={e => setPwConfirm(e.target.value)} className="settings-input" />
            </Field>
            <button onClick={handleChangePassword} disabled={changingPw}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm mt-3">
              {changingPw ? 'Alterando...' : 'Alterar Senha'}
            </button>
            {isSuperAdmin && (
              <div className="border-t border-carbon-700 pt-4 mt-6">
                <p className="text-red-400 text-sm font-semibold mb-2"><i className="fas fa-exclamation-triangle mr-1" />Zona de Perigo</p>
                <button onClick={() => {
                  if (!confirm('ATENÇÃO: Isso apagará todos os dados do sistema. Deseja continuar?')) return
                  if (!confirm('Tem CERTEZA ABSOLUTA? Esta ação é IRREVERSÍVEL.')) return
                  toast.error('Funcionalidade desabilitada por segurança. Contate o administrador do servidor.')
                }} className="bg-red-600/20 text-red-400 hover:bg-red-600/40 px-4 py-2 rounded-lg text-sm">
                  Resetar Banco de Dados
                </button>
              </div>
            )}
          </SettingsSection>
        )}

        {/* ── Changelog ── */}
        {section === 'changelog' && (
          <SettingsSection title="Changelog" icon="fa-code-branch">
            <p className="text-carbon-400 text-sm mb-6">Histórico de atualizações e melhorias do Carbon Expert Hub.</p>
            <div className="space-y-6">
              {CHANGELOG.map((release, idx) => (
                <div key={idx} className="relative">
                  {/* Timeline line */}
                  {idx < CHANGELOG.length - 1 && (
                    <div className="absolute left-[7px] top-8 bottom-0 w-px" style={{ background: 'rgba(229,168,0,0.2)' }} />
                  )}
                  <div className="flex items-start gap-4">
                    <div className="w-4 h-4 rounded-full mt-1 shrink-0 border-2" style={{ borderColor: '#E5A800', background: idx === 0 ? '#E5A800' : 'transparent' }} />
                    <div className="flex-1">
                      <div className="flex items-baseline gap-3 mb-2">
                        <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(229,168,0,0.15)', color: '#E5A800' }}>
                          {release.date}
                        </span>
                        <h3 className="text-white font-semibold text-sm">{release.title}</h3>
                      </div>
                      <div className="space-y-1.5">
                        {release.items.map((item, i) => {
                          const badge = {
                            new: { label: 'NOVO', bg: 'rgba(34,197,94,0.15)', color: '#22c55e' },
                            fix: { label: 'FIX', bg: 'rgba(239,68,68,0.15)', color: '#ef4444' },
                            change: { label: 'ALTERADO', bg: 'rgba(59,130,246,0.15)', color: '#3b82f6' },
                            perf: { label: 'PERF', bg: 'rgba(168,85,247,0.15)', color: '#a855f7' },
                          }[item.type] || { label: item.type, bg: 'rgba(113,113,122,0.15)', color: '#71717a' }
                          return (
                            <div key={i} className="flex items-start gap-2">
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 mt-0.5"
                                style={{ background: badge.bg, color: badge.color }}>
                                {badge.label}
                              </span>
                              <span className="text-carbon-300 text-sm">{item.text}</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </SettingsSection>
        )}
      </div>

      <style>{`
        .settings-input {
          width: 100%;
          background: var(--bg-tertiary, #1e293b);
          border: 1px solid var(--border-color, #334155);
          border-radius: 0.5rem;
          padding: 0.5rem 0.75rem;
          color: white;
          font-size: 0.875rem;
        }
        .settings-input:focus { outline: none; border-color: #E5A800; }
        .settings-input-sm {
          background: var(--bg-tertiary, #1e293b);
          border: 1px solid var(--border-color, #334155);
          border-radius: 0.375rem;
          padding: 0.25rem 0.5rem;
          color: white;
          font-size: 0.75rem;
        }
        .settings-input-sm:focus { outline: none; border-color: #E5A800; }
      `}</style>
    </div>
  )
}

function SettingsSection({ title, icon, children }) {
  return (
    <div>
      <h2 className="text-lg font-bold text-white mb-4"><i className={`fas ${icon} mr-2 text-indigo-400`} />{title}</h2>
      <div className="space-y-4">{children}</div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="text-carbon-300 text-sm font-medium block mb-1">{label}</label>
      {children}
    </div>
  )
}

function Toggle({ label, description, value, onChange }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="text-white text-sm">{label}</p>
        {description && <p className="text-carbon-500 text-xs">{description}</p>}
      </div>
      <button onClick={() => onChange(!value)}
        className={`w-11 h-6 rounded-full transition relative ${value ? 'bg-indigo-600' : 'bg-carbon-600'}`}>
        <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${value ? 'left-5' : 'left-0.5'}`} />
      </button>
    </div>
  )
}

