import React, { useState, useEffect, useRef } from 'react'
import { useToast } from '../components/Toast'
import {
  getAgentAnalysisOverview, generateAgentAnalysis,
  getAgentAnalysisHistory, getAgentAnalysisReport,
  getAnalysisGuidelines, saveAnalysisGuidelines,
  getDailyActivity,
} from '../services/api'

/* ═══════════════════════════════════════
   SCORE CONFIG
   ═══════════════════════════════════════ */
const SCORE_META = {
  tone_empathy:        { label: 'Tom e Empatia',          icon: 'fa-heart' },
  clarity:             { label: 'Clareza',                 icon: 'fa-bullseye' },
  playbook_adherence:  { label: 'Aderencia ao Playbook',   icon: 'fa-book' },
  proactivity:         { label: 'Proatividade',            icon: 'fa-bolt' },
  grammar:             { label: 'Portugues',               icon: 'fa-spell-check' },
  resolution_quality:  { label: 'Resolucao Efetiva',       icon: 'fa-check-double' },
  technical_knowledge: { label: 'Conhecimento Tecnico',    icon: 'fa-microchip' },
  conflict_management: { label: 'Gestao de Conflitos',     icon: 'fa-shield-halved' },
  personalization:     { label: 'Personalizacao',          icon: 'fa-user-pen' },
  urgency_awareness:   { label: 'Senso de Urgencia',       icon: 'fa-clock' },
  overall:             { label: 'Nota Geral',              icon: 'fa-star' },
}

const scoreColor = v => v >= 7 ? '#16a34a' : v >= 5 ? '#ca8a04' : v > 0 ? '#dc2626' : '#9CA3AF'

/* ═══════════════════════════════════════
   CIRCULAR GAUGE (SVG)
   ═══════════════════════════════════════ */
function CircularGauge({ value, size = 96, stroke = 7 }) {
  const v = value || 0
  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const pct = v / 10
  const offset = circ * (1 - pct)
  const color = scoreColor(v)

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#F3F4F6" strokeWidth={stroke} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s cubic-bezier(0.4,0,0.2,1)' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono-carbon text-2xl font-bold" style={{ color }}>{v || '-'}</span>
        <span className="text-xs uppercase tracking-wider font-semibold" style={{ color: '#4B5563' }}>score</span>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════
   SCORE BAR
   ═══════════════════════════════════════ */
function ScoreBar({ value, label, icon, delay = 0 }) {
  const v = value || 0
  const color = scoreColor(v)
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay)
    return () => clearTimeout(t)
  }, [delay])

  return (
    <div className="flex items-center gap-3 py-2.5 group">
      <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: `${color}18` }}>
        <i className={`fas ${icon} text-xs`} style={{ color }} />
      </div>
      <span className="text-sm w-44 shrink-0 font-medium" style={{ color: '#374151' }}>{label}</span>
      <div className="flex-1 h-2.5 rounded-full overflow-hidden" style={{ background: '#F3F4F6' }}>
        <div ref={ref} className="h-2.5 rounded-full"
          style={{
            width: visible ? `${v * 10}%` : '0%',
            background: `linear-gradient(90deg, ${color}99, ${color})`,
            transition: 'width 0.7s cubic-bezier(0.4,0,0.2,1)',
          }} />
      </div>
      <span className="font-mono-carbon text-sm font-bold w-8 text-right" style={{ color }}>
        {v || '-'}
      </span>
    </div>
  )
}

/* ═══════════════════════════════════════
   METRIC CARD
   ═══════════════════════════════════════ */
function MetricCard({ value, label, accent }) {
  return (
    <div className="glass-card p-5 text-center group hover:border-amber-300 transition-all">
      <div className="font-mono-carbon text-2xl font-bold" style={{ color: accent ? '#B8860B' : '#111827' }}>
        {value}
      </div>
      <div className="text-xs mt-1 font-semibold" style={{ color: '#4B5563' }}>{label}</div>
    </div>
  )
}

/* ═══════════════════════════════════════
   SECTION HEADER
   ═══════════════════════════════════════ */
function SectionHeader({ icon, children }) {
  return (
    <div className="flex items-center gap-2.5 mb-5">
      <div className="w-1 h-5 rounded-full" style={{ background: '#E5A800' }} />
      <i className={`fas ${icon} text-sm`} style={{ color: '#B8860B' }} />
      <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: '#374151' }}>{children}</h2>
    </div>
  )
}

/* ═══════════════════════════════════════
   SEVERITY / FREQUENCY HELPERS
   ═══════════════════════════════════════ */
const SEVERITY_CONFIG = {
  critico:  { label: 'Crítico',  color: '#dc2626', bg: 'rgba(220,38,38,0.08)' },
  moderado: { label: 'Moderado', color: '#ca8a04', bg: 'rgba(202,138,4,0.08)' },
  leve:     { label: 'Leve',     color: '#16a34a', bg: 'rgba(22,163,74,0.08)' },
}

const FREQ_CONFIG = {
  frequente:  { label: 'Frequente',  color: '#dc2626' },
  ocasional:  { label: 'Ocasional',  color: '#ca8a04' },
  raro:       { label: 'Raro',       color: '#16a34a' },
}

const PT_CATEGORY_META = {
  ortografia_acentuacao:  { label: 'Ortografia e Acentuação', icon: 'fa-spell-check' },
  informalidade:          { label: 'Informalidade',            icon: 'fa-comment-dots' },
  gramatica_concordancia: { label: 'Gramática e Concordância', icon: 'fa-language' },
  pontuacao_estrutura:    { label: 'Pontuação e Estrutura',    icon: 'fa-align-left' },
  formalidade:            { label: 'Formalidade',              icon: 'fa-user-tie' },
}

const LEVEL_CONFIG = {
  basico:        { label: 'Básico',        color: '#dc2626', bg: 'rgba(220,38,38,0.08)' },
  intermediario: { label: 'Intermediário', color: '#ca8a04', bg: 'rgba(202,138,4,0.08)' },
  avancado:      { label: 'Avançado',      color: '#16a34a', bg: 'rgba(22,163,74,0.08)' },
}

/* ═══════════════════════════════════════
   PORTUGUESE DIAGNOSIS COMPONENT
   ═══════════════════════════════════════ */
function PortugueseDiagnosis({ data }) {
  const [expandedCat, setExpandedCat] = useState(null)
  const level = LEVEL_CONFIG[data.level] || LEVEL_CONFIG.basico
  const categories = data.categories || {}

  return (
    <div className="glass-card p-6" style={{ borderLeft: '3px solid #6366f1' }}>
      <SectionHeader icon="fa-spell-check">Diagnóstico de Português</SectionHeader>

      {/* Level badge + overall score */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold" style={{ color: '#374151' }}>Nível:</span>
          <span className="px-3 py-1 rounded-full text-sm font-bold"
            style={{ background: level.bg, color: level.color }}>
            {level.label}
          </span>
        </div>
        {data.overall_score != null && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold" style={{ color: '#374151' }}>Nota geral:</span>
            <span className="font-mono-carbon text-lg font-bold" style={{ color: scoreColor(data.overall_score) }}>
              {data.overall_score}/10
            </span>
          </div>
        )}
      </div>

      {/* Category cards */}
      <div className="space-y-3 mb-6">
        {Object.entries(PT_CATEGORY_META).map(([key, meta]) => {
          const cat = categories[key]
          if (!cat) return null
          const sev = SEVERITY_CONFIG[cat.severity] || SEVERITY_CONFIG.leve
          const freq = FREQ_CONFIG[cat.frequency] || FREQ_CONFIG.raro
          const isExpanded = expandedCat === key
          const errors = cat.errors || []

          return (
            <div key={key} className="rounded-xl overflow-hidden" style={{ border: '1px solid #E5E7EB' }}>
              <div className="flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors"
                onClick={() => setExpandedCat(isExpanded ? null : key)}
                style={{ background: isExpanded ? '#F9FAFB' : '#fff' }}>
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: `${scoreColor(cat.score)}18` }}>
                  <i className={`fas ${meta.icon} text-sm`} style={{ color: scoreColor(cat.score) }} />
                </div>
                <span className="text-sm font-semibold flex-1" style={{ color: '#374151' }}>{meta.label}</span>
                <span className="font-mono-carbon text-sm font-bold" style={{ color: scoreColor(cat.score) }}>
                  {cat.score}/10
                </span>
                <span className="px-2 py-0.5 rounded text-xs font-semibold" style={{ background: sev.bg, color: sev.color }}>
                  {sev.label}
                </span>
                <span className="text-xs font-medium" style={{ color: freq.color }}>
                  {freq.label}
                </span>
                <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'} text-xs`} style={{ color: '#9CA3AF' }} />
              </div>

              {isExpanded && errors.length > 0 && (
                <div className="px-4 pb-4 pt-1 space-y-2" style={{ background: '#F9FAFB' }}>
                  {errors.map((err, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: '#fff', border: '1px solid #F3F4F6' }}>
                      <div className="shrink-0 mt-0.5">
                        <i className="fas fa-arrow-right text-xs" style={{ color: '#6366f1' }} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <span className="text-sm line-through" style={{ color: '#dc2626' }}>{err.wrote}</span>
                          <i className="fas fa-arrow-right text-xs" style={{ color: '#9CA3AF' }} />
                          <span className="text-sm font-semibold" style={{ color: '#16a34a' }}>{err.correct}</span>
                        </div>
                        {err.context && (
                          <p className="text-xs mt-1" style={{ color: '#6B7280' }}>
                            <i className="fas fa-quote-left text-xs mr-1" style={{ color: '#D1D5DB' }} />
                            {err.context}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Top corrections */}
      {data.top_corrections?.length > 0 && (
        <div className="mb-5">
          <h3 className="text-sm font-bold mb-3" style={{ color: '#374151' }}>
            <i className="fas fa-bullseye mr-2" style={{ color: '#6366f1' }} />
            Correções Prioritárias
          </h3>
          <ul className="space-y-2">
            {data.top_corrections.map((c, i) => (
              <li key={i} className="flex items-start gap-3 text-sm" style={{ color: '#374151' }}>
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold shrink-0 mt-0.5"
                  style={{ background: 'rgba(99,102,241,0.1)', color: '#6366f1' }}>{i + 1}</span>
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Training suggestion */}
      {data.training_suggestion && (
        <div className="p-4 rounded-lg" style={{ background: 'rgba(99,102,241,0.04)', border: '1px solid rgba(99,102,241,0.15)' }}>
          <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: '#6366f1' }}>
            <i className="fas fa-chalkboard-teacher mr-1.5" />
            Plano de Treinamento
          </p>
          <p className="text-sm leading-relaxed" style={{ color: '#374151' }}>{data.training_suggestion}</p>
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════ */
export default function AgentAnalysisPage({ user }) {
  const toast = useToast()
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [report, setReport] = useState(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [days, setDays] = useState(30)
  const [sampleSize, setSampleSize] = useState(50)
  const [view, setView] = useState('overview')
  const GUIDELINE_SECTIONS = [
    { key: 'tom_de_voz', label: 'Tom de Voz e Saudacao', icon: 'fa-comment-dots', color: '#6366f1',
      placeholder: 'Como o atendente deve se comunicar? Formalidade, cordialidade, uso de emojis, saudacao padrao, despedida...\n\nEx: "Sempre cumprimentar pelo nome. Tom amigavel mas profissional. Nunca usar girias. Pedir desculpas quando houver erro nosso."' },
    { key: 'procedimentos', label: 'Procedimentos Obrigatorios', icon: 'fa-list-check', color: '#E5A800',
      placeholder: 'Quais passos o atendente DEVE seguir? O que pedir ao cliente? Ordem de acoes...\n\nEx: "1. Pedir CPF ou email do pedido. 2. Verificar no Shopify. 3. Se garantia, pedir foto do defeito. 4. Nunca prometer prazo sem confirmar com logistica."' },
    { key: 'politicas', label: 'Politicas (Troca, Garantia, Reembolso)', icon: 'fa-scale-balanced', color: '#16a34a',
      placeholder: 'Regras oficiais de troca, garantia, cancelamento, reembolso...\n\nEx: "Garantia: 1 ano para defeitos de fabrica. Mau uso nao coberto. Troca: ate 7 dias apos recebimento. Reembolso: 5-10 dias uteis apos aprovacao."' },
    { key: 'escalacao', label: 'Regras de Escalacao', icon: 'fa-arrow-up-right-dots', color: '#dc2626',
      placeholder: 'Quando escalar? Para quem? O que NAO fazer antes de escalar...\n\nEx: "Escalar para Victor: ameaca juridica, PROCON, chargeback. Escalar para Lyvia: caso de imprensa ou influenciador. Nunca prometer solucao antes de escalar."' },
    { key: 'produtos', label: 'Conhecimento de Produtos', icon: 'fa-box', color: '#ca8a04',
      placeholder: 'Informacoes tecnicas sobre os produtos que o atendente deve saber...\n\nEx: "Carregador magnetico: compativel com todos os modelos. Resistencia a agua: IP67 (respingos, nao imersao). Pulseira: troca facil pelo pino de liberacao rapida."' },
    { key: 'proibicoes', label: 'Proibicoes e Alertas', icon: 'fa-ban', color: '#7c3aed',
      placeholder: 'O que o atendente NUNCA deve fazer ou dizer...\n\nEx: "Nunca falar mal de concorrentes. Nunca compartilhar dados de outros clientes. Nunca prometer reembolso sem aprovacao. Nunca discutir com cliente irritado."' },
    { key: 'contexto_extra', label: 'Contexto Extra', icon: 'fa-circle-info', color: '#6B7280',
      placeholder: 'Qualquer informacao adicional relevante para a analise...\n\nEx: "A Carbon esta em fase de crescimento. Priorizar retencao de clientes. Victor cuida da operacao, Lyvia das decisoes estrategicas."' },
  ]
  const [guidelines, setGuidelines] = useState({})
  const [guidelinesSaving, setGuidelinesSaving] = useState(false)
  const [activityData, setActivityData] = useState(null)
  const [activityDate, setActivityDate] = useState('')
  const [activityLoading, setActivityLoading] = useState(false)

  useEffect(() => {
    if (user?.role !== 'super_admin') return
    loadOverview()
  }, [])

  const loadGuidelines = async () => {
    try {
      const { data } = await getAnalysisGuidelines()
      const raw = data.guidelines || ''
      // Parse: if it's JSON, use as object; if plain text, put in contexto_extra
      try {
        const parsed = JSON.parse(raw)
        setGuidelines(typeof parsed === 'object' && parsed !== null ? parsed : { contexto_extra: raw })
      } catch {
        setGuidelines(raw ? { contexto_extra: raw } : {})
      }
    } catch { /* ignore */ }
  }

  const updateGuidelineField = (key, value) => {
    setGuidelines(prev => ({ ...prev, [key]: value }))
  }

  const handleSaveGuidelines = async () => {
    setGuidelinesSaving(true)
    try {
      await saveAnalysisGuidelines(JSON.stringify(guidelines))
      toast.success('Documentos salvos!')
    } catch {
      toast.error('Erro ao salvar documentos')
    } finally {
      setGuidelinesSaving(false)
    }
  }

  const loadDailyActivity = async (dateStr) => {
    setActivityLoading(true)
    try {
      const { data } = await getDailyActivity(dateStr || undefined)
      setActivityData(data)
      if (data.date) setActivityDate(data.date)
    } catch (e) {
      toast.error('Erro ao carregar atividade diaria')
    } finally {
      setActivityLoading(false)
    }
  }

  const loadOverview = async () => {
    setLoading(true)
    try {
      const { data } = await getAgentAnalysisOverview()
      setAgents(data)
    } catch (e) {
      if (e.response?.status === 403) toast.error('Acesso restrito a super admin')
      else toast.error('Erro ao carregar overview')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateReport = async (agentId) => {
    setReportLoading(true)
    try {
      const { data } = await generateAgentAnalysis(agentId, { days, sample_size: sampleSize })
      setReport(data)
      toast.success('Analise gerada com sucesso!')
      loadOverview()
    } catch (e) {
      toast.error('Erro ao gerar analise: ' + (e.response?.data?.detail || e.message))
    } finally {
      setReportLoading(false)
    }
  }

  const handleViewReport = async (reportId) => {
    setReportLoading(true)
    try {
      const { data } = await getAgentAnalysisReport(reportId)
      setReport(data)
      setView('detail')
    } catch (e) {
      toast.error('Erro ao carregar relatorio')
    } finally {
      setReportLoading(false)
    }
  }

  const handleLoadHistory = async (agentId) => {
    try {
      const { data } = await getAgentAnalysisHistory({ agent_id: agentId, days: 365 })
      setHistory(data)
    } catch { setHistory([]) }
  }

  const handleSelectAgent = (agent) => {
    setSelectedAgent(agent)
    setReport(null)
    setView('detail')
    handleLoadHistory(agent.agent_id)
    if (agent.latest_report) handleViewReport(agent.latest_report.id)
  }

  /* ACCESS GATE */
  if (user?.role !== 'super_admin') {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <i className="fas fa-lock text-3xl mb-3" style={{ color: '#9CA3AF' }} />
          <p className="text-sm font-medium" style={{ color: '#6B7280' }}>Acesso restrito a Super Admin</p>
        </div>
      </div>
    )
  }

  /* ═══ OVERVIEW ═══ */
  if (view === 'overview') {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'rgba(229,168,0,0.1)' }}>
                <i className="fas fa-microscope text-sm" style={{ color: '#B8860B' }} />
              </div>
              <h1 className="text-lg font-bold" style={{ color: '#111827' }}>Analise de Equipe</h1>
            </div>
            <p className="text-sm ml-11" style={{ color: '#6B7280' }}>
              Avaliacao quantitativa e qualitativa por IA de cada atendente
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => { setView('activity'); loadDailyActivity('') }}
              className="px-4 py-2 rounded-lg text-sm font-medium border transition-colors hover:bg-gray-50"
              style={{ borderColor: '#E5E7EB', color: '#6B7280' }}>
              <i className="fas fa-user-clock mr-1.5" />Atividade Diaria
            </button>
            <button
              onClick={() => { setView('guidelines'); loadGuidelines() }}
              className="px-4 py-2 rounded-lg text-sm font-medium border transition-colors hover:bg-gray-50"
              style={{ borderColor: '#E5E7EB', color: '#6B7280' }}>
              <i className="fas fa-file-lines mr-1.5" />Documentos de Instrucao
            </button>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {[1,2,3,4,5,6].map(i => (
              <div key={i} className="glass-card p-6">
                <div className="flex items-center gap-4 mb-5">
                  <div className="skeleton w-12 h-12 rounded-full" />
                  <div className="flex-1">
                    <div className="skeleton h-4 w-32 mb-2" />
                    <div className="skeleton h-3 w-20" />
                  </div>
                </div>
                <div className="space-y-2">
                  {[1,2,3].map(j => <div key={j} className="skeleton h-2 w-full rounded-full" />)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {agents.map((agent, idx) => {
              const scores = agent.latest_report?.ai_scores?.scores || agent.latest_report?.ai_scores || {}
              const overall = scores.overall || 0
              const metrics = agent.latest_report?.quantitative_metrics || {}
              const hasReport = !!agent.latest_report

              return (
                <div key={agent.agent_id}
                  onClick={() => handleSelectAgent(agent)}
                  className="glass-card p-6 cursor-pointer group relative overflow-hidden"
                  style={{ animationDelay: `${idx * 60}ms` }}
                >
                  {/* Gold top accent line */}
                  <div className="absolute top-0 left-0 right-0 h-[2px] opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ background: 'linear-gradient(90deg, transparent, #E5A800, transparent)' }} />

                  <div className="flex items-start justify-between mb-5">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full flex items-center justify-center text-base font-bold shadow-sm"
                        style={{ background: 'linear-gradient(135deg, #E5A800, #CC9600)', color: '#fff' }}>
                        {agent.agent_name?.[0] || '?'}
                      </div>
                      <div>
                        <p className="text-base font-semibold" style={{ color: '#111827' }}>{agent.agent_name}</p>
                        <p className="text-xs capitalize font-medium" style={{ color: '#6B7280' }}>
                          {agent.role === 'super_admin' ? 'Super Admin' : agent.role}
                        </p>
                      </div>
                    </div>
                    <CircularGauge value={overall} size={72} stroke={5} />
                  </div>

                  {hasReport ? (
                    <>
                      <div className="space-y-2 mb-4">
                        {Object.entries(SCORE_META).filter(([k]) => k !== 'overall').map(([key, meta]) => {
                          const val = scores[key] || 0
                          const c = scoreColor(val)
                          return (
                            <div key={key} className="flex items-center gap-2.5">
                              <span className="text-xs w-32 shrink-0 font-medium" style={{ color: '#4B5563' }}>{meta.label}</span>
                              <div className="flex-1 h-2 rounded-full" style={{ background: '#F3F4F6' }}>
                                <div className="h-2 rounded-full" style={{ width: `${val * 10}%`, background: c, transition: 'width 0.5s ease' }} />
                              </div>
                              <span className="font-mono-carbon text-xs font-bold w-6 text-right" style={{ color: c }}>{val}</span>
                            </div>
                          )
                        })}
                      </div>
                      <div className="flex items-center gap-3 pt-3 border-t" style={{ borderColor: '#E5E7EB' }}>
                        <span className="text-xs font-medium" style={{ color: '#374151' }}>
                          <i className="fas fa-check-circle mr-1 text-green-500" />{metrics.tickets_resolved || 0} resolvidos
                        </span>
                        <span className="text-xs font-medium" style={{ color: '#374151' }}>
                          SLA {metrics.sla_compliance_pct || 0}%
                        </span>
                        <span className="flex-1" />
                        <span className="text-xs font-medium" style={{ color: '#6B7280' }}>
                          {agent.latest_report.report_type === 'weekly_auto' ? 'Auto' : 'Manual'} · {new Date(agent.latest_report.created_at).toLocaleDateString('pt-BR')}
                        </span>
                      </div>
                    </>
                  ) : (
                    <div className="py-5 text-center border-t" style={{ borderColor: '#E5E7EB' }}>
                      <p className="text-sm font-medium" style={{ color: '#6B7280' }}>Nenhuma analise ainda</p>
                      <p className="text-xs mt-1" style={{ color: '#9CA3AF' }}>Clique para gerar</p>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  /* ═══ GUIDELINES VIEW ═══ */
  if (view === 'guidelines') {
    const filledCount = GUIDELINE_SECTIONS.filter(s => (guidelines[s.key] || '').trim().length > 0).length
    return (
      <div className="p-6 lg:p-8 max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <button onClick={() => setView('overview')}
            className="w-8 h-8 rounded-lg flex items-center justify-center border transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: '#6B7280' }}>
            <i className="fas fa-arrow-left text-xs" />
          </button>
          <div className="flex-1">
            <h1 className="text-lg font-bold" style={{ color: '#111827' }}>Documentos de Instrucao</h1>
            <p className="text-sm font-medium" style={{ color: '#6B7280' }}>
              A IA compara o atendimento dos agentes contra estes documentos
            </p>
          </div>
          <button
            onClick={handleSaveGuidelines}
            disabled={guidelinesSaving}
            className="px-5 py-2 rounded-lg text-sm font-semibold shadow-sm transition-all hover:shadow-md active:scale-[0.98] shrink-0"
            style={{ background: guidelinesSaving ? '#D1D5DB' : '#E5A800', color: '#fff' }}>
            {guidelinesSaving
              ? <><i className="fas fa-circle-notch fa-spin mr-2" />Salvando...</>
              : <><i className="fas fa-save mr-2" />Salvar Tudo</>}
          </button>
        </div>

        {/* Progress */}
        <div className="glass-card p-4 mb-5 flex items-center gap-3">
          <i className="fas fa-clipboard-check text-sm" style={{ color: '#6B7280' }} />
          <span className="text-sm font-medium" style={{ color: '#374151' }}>
            {filledCount} de {GUIDELINE_SECTIONS.length} secoes preenchidas
          </span>
          <div className="flex-1 h-2 rounded-full" style={{ background: '#F3F4F6' }}>
            <div className="h-2 rounded-full transition-all"
              style={{ width: `${(filledCount / GUIDELINE_SECTIONS.length) * 100}%`, background: filledCount === GUIDELINE_SECTIONS.length ? '#16a34a' : '#E5A800' }} />
          </div>
          <span className="text-xs" style={{ color: '#9CA3AF' }}>
            A IA tambem usa os {11} macros e {16} artigos da KB automaticamente
          </span>
        </div>

        {/* Section cards */}
        <div className="space-y-4">
          {GUIDELINE_SECTIONS.map(section => {
            const val = guidelines[section.key] || ''
            const filled = val.trim().length > 0
            return (
              <div key={section.key} className="glass-card overflow-hidden" style={{ borderLeft: `3px solid ${section.color}` }}>
                <div className="px-5 py-4">
                  <div className="flex items-center gap-2.5 mb-3">
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                      style={{ background: `${section.color}15` }}>
                      <i className={`fas ${section.icon} text-xs`} style={{ color: section.color }} />
                    </div>
                    <span className="text-sm font-bold" style={{ color: '#374151' }}>{section.label}</span>
                    {filled && (
                      <span className="ml-auto text-xs px-2 py-0.5 rounded-full font-medium"
                        style={{ background: 'rgba(22,163,74,0.08)', color: '#16a34a' }}>
                        <i className="fas fa-check mr-1" />{val.length} chars
                      </span>
                    )}
                  </div>
                  <textarea
                    value={val}
                    onChange={e => updateGuidelineField(section.key, e.target.value)}
                    rows={4}
                    className="w-full p-3 rounded-lg text-sm leading-relaxed resize-y"
                    style={{ border: '1px solid #E5E7EB', color: '#374151', background: '#FAFAFA', minHeight: 80 }}
                    placeholder={section.placeholder}
                  />
                </div>
              </div>
            )
          })}
        </div>

        {/* Bottom save */}
        <div className="flex justify-end mt-5">
          <button
            onClick={handleSaveGuidelines}
            disabled={guidelinesSaving}
            className="px-5 py-2 rounded-lg text-sm font-semibold shadow-sm transition-all hover:shadow-md active:scale-[0.98]"
            style={{ background: guidelinesSaving ? '#D1D5DB' : '#E5A800', color: '#fff' }}>
            {guidelinesSaving
              ? <><i className="fas fa-circle-notch fa-spin mr-2" />Salvando...</>
              : <><i className="fas fa-save mr-2" />Salvar Tudo</>}
          </button>
        </div>
      </div>
    )
  }

  /* ═══ ACTIVITY VIEW ═══ */
  if (view === 'activity') {
    const STATUS_CONFIG = {
      ativo:            { label: 'Ativo',            color: '#16a34a', bg: 'rgba(22,163,74,0.08)',  icon: 'fa-circle-check' },
      parcial:          { label: 'Parcial',          color: '#ca8a04', bg: 'rgba(202,138,4,0.08)',  icon: 'fa-circle-half-stroke' },
      intermitente:     { label: 'Intermitente',     color: '#ea580c', bg: 'rgba(234,88,12,0.08)',  icon: 'fa-wave-square' },
      baixa_atividade:  { label: 'Baixa Atividade',  color: '#dc2626', bg: 'rgba(220,38,38,0.08)',  icon: 'fa-circle-exclamation' },
      ausente:          { label: 'Ausente',          color: '#6B7280', bg: 'rgba(107,114,128,0.08)', icon: 'fa-circle-xmark' },
    }
    const HOURS = Array.from({ length: 24 }, (_, i) => i)

    const shiftDate = (offset) => {
      const d = activityDate ? new Date(activityDate + 'T12:00:00') : new Date()
      d.setDate(d.getDate() + offset)
      const iso = d.toISOString().split('T')[0]
      setActivityDate(iso)
      loadDailyActivity(iso)
    }
    const goToday = () => { setActivityDate(''); loadDailyActivity('') }
    const isToday = !activityDate || activityDate === new Date().toISOString().split('T')[0]
    const summary = activityData?.summary || {}

    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <button onClick={() => setView('overview')}
            className="w-8 h-8 rounded-lg flex items-center justify-center border transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: '#6B7280' }}>
            <i className="fas fa-arrow-left text-xs" />
          </button>
          <div className="flex-1">
            <h1 className="text-lg font-bold" style={{ color: '#111827' }}>
              <i className="fas fa-user-clock mr-2" style={{ color: '#B8860B' }} />
              Atividade Diaria dos Agentes
            </h1>
            <p className="text-sm font-medium" style={{ color: '#6B7280' }}>
              Monitoramento de presenca e produtividade por hora (BRT)
            </p>
          </div>
        </div>

        {/* Date navigation */}
        <div className="glass-card p-3 mb-4 flex items-center gap-2">
          <button onClick={() => shiftDate(-1)}
            className="w-8 h-8 rounded-lg flex items-center justify-center border transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: '#6B7280' }}>
            <i className="fas fa-chevron-left text-xs" />
          </button>
          <input
            type="date"
            value={activityDate}
            onChange={e => { setActivityDate(e.target.value); loadDailyActivity(e.target.value) }}
            className="px-3 py-1.5 rounded-lg text-sm font-medium border"
            style={{ borderColor: '#D1D5DB', color: '#374151' }}
          />
          <button onClick={() => shiftDate(1)}
            className="w-8 h-8 rounded-lg flex items-center justify-center border transition-colors hover:bg-gray-50"
            style={{ borderColor: '#D1D5DB', color: '#6B7280' }}>
            <i className="fas fa-chevron-right text-xs" />
          </button>
          {!isToday && (
            <button onClick={goToday}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors hover:bg-gray-50"
              style={{ borderColor: '#D1D5DB', color: '#6B7280' }}>
              Hoje
            </button>
          )}
          <div className="flex-1" />
          <button
            onClick={() => loadDailyActivity(activityDate)}
            disabled={activityLoading}
            className="px-4 py-1.5 rounded-lg text-sm font-semibold shadow-sm transition-all hover:shadow-md active:scale-[0.98]"
            style={{ background: activityLoading ? '#D1D5DB' : '#E5A800', color: '#fff' }}>
            {activityLoading
              ? <><i className="fas fa-circle-notch fa-spin mr-1.5" />...</>
              : <><i className="fas fa-sync mr-1.5" />Atualizar</>}
          </button>
        </div>

        {activityLoading && !activityData ? (
          <div className="glass-card p-16 text-center">
            <i className="fas fa-circle-notch fa-spin fa-lg mb-3" style={{ color: '#E5A800' }} />
            <p className="text-sm font-medium" style={{ color: '#6B7280' }}>Carregando atividade...</p>
          </div>
        ) : activityData?.agents?.length > 0 ? (
          <div className="space-y-4">
            {/* Summary cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="glass-card p-3 text-center">
                <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#6B7280' }}>
                  <i className="fas fa-calendar-day mr-1" />Dia
                </p>
                <p className="text-sm font-bold" style={{ color: '#111827' }}>
                  {activityData.date ? new Date(activityData.date + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' }) : '-'}
                </p>
              </div>
              <div className="glass-card p-3 text-center">
                <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#6B7280' }}>
                  <i className="fas fa-users mr-1" />Ativos
                </p>
                <p className="text-sm font-bold" style={{ color: '#111827' }}>
                  {summary.active_agents || 0}<span className="text-xs font-normal" style={{ color: '#9CA3AF' }}>/{summary.total_agents || 0}</span>
                </p>
              </div>
              <div className="glass-card p-3 text-center">
                <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#6B7280' }}>
                  <i className="fas fa-envelope mr-1" />Msgs Total
                </p>
                <p className="text-sm font-bold" style={{ color: '#B8860B' }}>
                  {summary.total_messages || 0}
                </p>
              </div>
              <div className="glass-card p-3 text-center">
                <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#6B7280' }}>
                  <i className="fas fa-chart-bar mr-1" />Media/Agente
                </p>
                <p className="text-sm font-bold" style={{ color: '#111827' }}>
                  {summary.avg_messages_per_agent || 0}
                </p>
              </div>
              <div className="glass-card p-3 text-center">
                <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#6B7280' }}>
                  <i className="fas fa-clock mr-1" />Jornada Media
                </p>
                <p className="text-sm font-bold" style={{ color: '#111827' }}>
                  {summary.avg_work_span_hours || 0}h
                </p>
              </div>
            </div>

            {/* Status summary */}
            <div className="flex flex-wrap items-center gap-3 px-1">
              {Object.entries(STATUS_CONFIG).map(([key, cfg]) => {
                const count = activityData.agents.filter(a => a.status === key).length
                if (count === 0) return null
                return (
                  <span key={key} className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold"
                    style={{ background: cfg.bg, color: cfg.color }}>
                    <i className={`fas ${cfg.icon}`} style={{ fontSize: 9 }} /> {count} {cfg.label}
                  </span>
                )
              })}
            </div>

            {/* Heatmap table */}
            <div className="glass-card overflow-hidden">
              {/* Hour labels row */}
              <div className="px-5 py-3 flex items-center gap-2 border-b" style={{ borderColor: '#F3F4F6', background: '#FAFAFA' }}>
                <div className="w-44 shrink-0 text-[10px] font-bold uppercase tracking-wider" style={{ color: '#9CA3AF' }}>Agente</div>
                <div className="flex-1 flex">
                  {HOURS.map(h => (
                    <div key={h} className="flex-1 text-center">
                      <span className="text-[10px] font-mono font-semibold" style={{ color: h >= 8 && h <= 18 ? '#374151' : '#D1D5DB' }}>
                        {String(h).padStart(2, '0')}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="w-32 shrink-0 text-[10px] font-bold uppercase tracking-wider text-right" style={{ color: '#9CA3AF' }}>Resumo</div>
              </div>

              {/* Agent rows */}
              {activityData.agents.map((agent, idx) => {
                const st = STATUS_CONFIG[agent.status] || STATUS_CONFIG.ausente
                const maxInHour = Math.max(1, ...Object.values(agent.hourly_breakdown || {}))
                return (
                  <div key={agent.agent_id}
                    className="px-5 py-3 flex items-center gap-2 transition-colors hover:bg-gray-50"
                    style={{ borderBottom: idx < activityData.agents.length - 1 ? '1px solid #F3F4F6' : 'none' }}>
                    {/* Agent info */}
                    <div className="w-44 shrink-0 flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold shadow-sm shrink-0"
                        style={{ background: `linear-gradient(135deg, ${st.color}cc, ${st.color})`, color: '#fff' }}>
                        {agent.agent_name?.[0] || '?'}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold truncate" style={{ color: '#111827' }}>{agent.agent_name}</p>
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold"
                          style={{ background: st.bg, color: st.color }}>
                          <i className={`fas ${st.icon}`} style={{ fontSize: 8 }} /> {st.label}
                        </span>
                      </div>
                    </div>

                    {/* Hourly heatmap */}
                    <div className="flex-1 flex gap-px">
                      {HOURS.map(h => {
                        const count = (agent.hourly_breakdown || {})[String(h)] || 0
                        const intensity = count > 0 ? Math.max(0.15, count / maxInHour) : 0
                        const isWorkHour = h >= 8 && h <= 18
                        return (
                          <div key={h} className="flex-1 relative group" style={{ minHeight: 32 }}>
                            <div className="w-full h-8 rounded-sm transition-all"
                              style={{
                                background: count > 0
                                  ? `rgba(22,163,74,${intensity})`
                                  : isWorkHour ? 'rgba(243,244,246,0.5)' : 'transparent',
                                border: count > 0 ? 'none' : isWorkHour ? '1px solid rgba(229,231,235,0.5)' : 'none',
                              }} />
                            {count > 0 && (
                              <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 rounded text-xs font-bold whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10"
                                style={{ background: '#111827', color: '#fff' }}>
                                {count} msg{count > 1 ? 's' : ''} as {String(h).padStart(2,'0')}h
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>

                    {/* Stats */}
                    <div className="w-32 shrink-0 text-right">
                      <p className="text-sm font-mono font-bold" style={{ color: '#111827' }}>
                        {agent.total_messages} <span className="text-[10px] font-normal" style={{ color: '#9CA3AF' }}>msgs</span>
                      </p>
                      <p className="text-[10px] font-medium" style={{ color: '#6B7280' }}>
                        {agent.first_message || '--:--'} - {agent.last_message || '--:--'}
                        {agent.work_span_hours > 0 && <span className="ml-1">({agent.work_span_hours}h)</span>}
                      </p>
                      {agent.idle_pct > 0 && agent.status !== 'ausente' && (
                        <p className="text-[10px] font-bold" style={{ color: agent.idle_pct > 40 ? '#dc2626' : agent.idle_pct > 20 ? '#ca8a04' : '#6B7280' }}>
                          <i className="fas fa-pause-circle mr-0.5" style={{ fontSize: 8 }} />
                          {agent.idle_pct}% ocioso
                        </p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Gaps detail */}
            {activityData.agents.some(a => a.gaps?.length > 0) && (
              <div className="glass-card p-5">
                <SectionHeader icon="fa-clock">Gaps de Inatividade (&gt;1h)</SectionHeader>
                <div className="space-y-3">
                  {activityData.agents.filter(a => a.gaps?.length > 0).map(agent => (
                    <div key={agent.agent_id} className="flex items-start gap-3">
                      <span className="text-sm font-semibold w-32 shrink-0" style={{ color: '#374151' }}>
                        {agent.agent_name}
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {agent.gaps.map((gap, i) => (
                          <span key={i} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium"
                            style={{
                              background: gap.minutes > 120 ? 'rgba(220,38,38,0.06)' : 'rgba(202,138,4,0.06)',
                              color: gap.minutes > 120 ? '#dc2626' : '#ca8a04',
                              border: `1px solid ${gap.minutes > 120 ? 'rgba(220,38,38,0.15)' : 'rgba(202,138,4,0.15)'}`,
                            }}>
                            <i className="fas fa-pause text-[8px]" />
                            {gap.from} → {gap.to}
                            <span className="font-bold">({gap.minutes}min)</span>
                          </span>
                        ))}
                      </div>
                      {agent.avg_gap_min > 0 && (
                        <span className="text-xs font-medium shrink-0" style={{ color: '#9CA3AF' }}>
                          media: {agent.avg_gap_min}min
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Legend */}
            <div className="flex items-center gap-6 px-2 py-2">
              <span className="text-xs font-medium" style={{ color: '#9CA3AF' }}>Intensidade:</span>
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-4 rounded-sm" style={{ background: 'rgba(22,163,74,0.15)' }} />
                <span className="text-xs" style={{ color: '#9CA3AF' }}>Pouco</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-4 rounded-sm" style={{ background: 'rgba(22,163,74,0.5)' }} />
                <span className="text-xs" style={{ color: '#9CA3AF' }}>Medio</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-4 rounded-sm" style={{ background: 'rgba(22,163,74,1)' }} />
                <span className="text-xs" style={{ color: '#9CA3AF' }}>Intenso</span>
              </div>
              <span className="text-xs ml-auto" style={{ color: '#D1D5DB' }}>
                Horario comercial: 08h-18h (BRT)
              </span>
            </div>
          </div>
        ) : activityData ? (
          <div className="glass-card p-16 text-center">
            <i className="fas fa-calendar-xmark text-3xl mb-3" style={{ color: '#D1D5DB' }} />
            <p className="text-sm font-medium" style={{ color: '#6B7280' }}>Nenhuma atividade registrada neste dia</p>
            <div className="flex justify-center gap-3 mt-4">
              <button onClick={() => shiftDate(-1)} className="px-3 py-1.5 rounded-lg text-xs font-medium border hover:bg-gray-50" style={{ borderColor: '#D1D5DB', color: '#6B7280' }}>
                <i className="fas fa-chevron-left mr-1" />Dia anterior
              </button>
              {!isToday && (
                <button onClick={goToday} className="px-3 py-1.5 rounded-lg text-xs font-medium border hover:bg-gray-50" style={{ borderColor: '#D1D5DB', color: '#6B7280' }}>
                  Ir para hoje
                </button>
              )}
            </div>
          </div>
        ) : null}
      </div>
    )
  }

  /* ═══ DETAIL VIEW ═══ */
  const aiData = report?.ai_analysis && typeof report.ai_analysis === 'object' ? report.ai_analysis : null
  const aiText = report?.ai_analysis && typeof report.ai_analysis === 'string' ? report.ai_analysis : null
  const aiScores = report?.ai_scores?.scores || report?.ai_scores || {}

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => { setView('overview'); setSelectedAgent(null); setReport(null) }}
          className="w-8 h-8 rounded-lg flex items-center justify-center border transition-colors hover:bg-gray-50"
          style={{ borderColor: '#D1D5DB', color: '#6B7280' }}>
          <i className="fas fa-arrow-left text-xs" />
        </button>
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-full flex items-center justify-center text-base font-bold shadow-sm"
            style={{ background: 'linear-gradient(135deg, #E5A800, #CC9600)', color: '#fff' }}>
            {selectedAgent?.agent_name?.[0] || '?'}
          </div>
          <div>
            <h1 className="text-lg font-bold" style={{ color: '#111827' }}>{selectedAgent?.agent_name || 'Atendente'}</h1>
            <p className="text-sm font-medium" style={{ color: '#6B7280' }}>Analise profunda de desempenho</p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="glass-card p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="text-xs font-bold uppercase tracking-wider block mb-1.5" style={{ color: '#4B5563' }}>Periodo</label>
            <select value={days} onChange={e => setDays(Number(e.target.value))}
              className="px-3 py-2 rounded-lg text-sm font-medium">
              {[7, 14, 30, 60, 90].map(d => <option key={d} value={d}>{d} dias</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-wider block mb-1.5" style={{ color: '#4B5563' }}>Amostra</label>
            <select value={sampleSize || ''} onChange={e => setSampleSize(e.target.value ? Number(e.target.value) : null)}
              className="px-3 py-2 rounded-lg text-sm font-medium">
              <option value="20">20 mensagens</option>
              <option value="50">50 mensagens</option>
              <option value="100">100 mensagens</option>
              <option value="">Todas</option>
            </select>
          </div>
          <div className="flex-1" />
          <button onClick={() => handleGenerateReport(selectedAgent.agent_id)} disabled={reportLoading}
            className="px-5 py-2 rounded-lg text-sm font-semibold shadow-sm transition-all hover:shadow-md active:scale-[0.98]"
            style={{ background: reportLoading ? '#D1D5DB' : '#E5A800', color: '#fff' }}>
            {reportLoading
              ? <><i className="fas fa-circle-notch fa-spin mr-2" />Analisando...</>
              : <><i className="fas fa-wand-magic-sparkles mr-2" />Gerar Analise</>}
          </button>
          {report?.id && (
            <a href={`/api/agent-deep-analysis/${report.id}/export`} target="_blank" rel="noopener noreferrer"
              className="px-4 py-2 rounded-lg text-sm font-medium border transition-colors hover:bg-gray-50"
              style={{ borderColor: '#E5E7EB', color: '#6B7280' }}>
              <i className="fas fa-arrow-up-right-from-square mr-1.5" />Exportar
            </a>
          )}
        </div>
      </div>

      {/* Loading state */}
      {reportLoading && !report ? (
        <div className="glass-card p-16 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-4"
            style={{ background: 'rgba(229,168,0,0.08)' }}>
            <i className="fas fa-circle-notch fa-spin fa-lg" style={{ color: '#E5A800' }} />
          </div>
          <p className="text-base font-medium" style={{ color: '#374151' }}>Gerando analise profunda...</p>
          <p className="text-sm mt-1.5" style={{ color: '#6B7280' }}>A IA esta avaliando as mensagens do atendente</p>
        </div>

      ) : report ? (
        <div className="space-y-6">

          {/* ── Analysis Basis ── */}
          {(() => {
            const meta = report.analysis_meta || report.quantitative_metrics?.analysis_meta || {}
            const periodStart = report.period_start ? new Date(report.period_start).toLocaleDateString('pt-BR') : '-'
            const periodEnd = report.period_end ? new Date(report.period_end).toLocaleDateString('pt-BR') : '-'
            const createdAt = report.created_at ? new Date(report.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'
            return (
              <div className="glass-card p-5" style={{ borderLeft: '3px solid #6B7280' }}>
                <div className="flex items-center gap-2 mb-3">
                  <i className="fas fa-database text-xs" style={{ color: '#6B7280' }} />
                  <span className="text-xs font-bold uppercase tracking-wider" style={{ color: '#6B7280' }}>Base da Analise</span>
                </div>
                <div className="flex flex-wrap gap-x-6 gap-y-2">
                  <span className="text-sm" style={{ color: '#374151' }}>
                    <i className="fas fa-calendar-days text-xs mr-1.5" style={{ color: '#9CA3AF' }} />
                    Periodo: <b>{periodStart}</b> a <b>{periodEnd}</b>
                    {meta.period_days ? <span className="text-xs ml-1" style={{ color: '#6B7280' }}>({meta.period_days} dias)</span> : null}
                  </span>
                  <span className="text-sm" style={{ color: '#374151' }}>
                    <i className="fas fa-ticket text-xs mr-1.5" style={{ color: '#9CA3AF' }} />
                    Tickets no periodo: <b>{meta.tickets_in_period ?? report.quantitative_metrics?.tickets_total ?? '-'}</b>
                  </span>
                  <span className="text-sm" style={{ color: '#374151' }}>
                    <i className="fas fa-envelope text-xs mr-1.5" style={{ color: '#9CA3AF' }} />
                    Mensagens analisadas: <b>{meta.messages_analyzed ?? report.sample_size ?? '-'}</b>
                    {meta.sample_size_requested ? <span className="text-xs ml-1" style={{ color: '#6B7280' }}>(amostra: {meta.sample_size_requested})</span> : null}
                  </span>
                  <span className="text-sm" style={{ color: '#374151' }}>
                    <i className="fas fa-clock text-xs mr-1.5" style={{ color: '#9CA3AF' }} />
                    Gerado: <b>{createdAt}</b>
                  </span>
                  {report.report_type && (
                    <span className="text-sm" style={{ color: '#374151' }}>
                      <i className="fas fa-tag text-xs mr-1.5" style={{ color: '#9CA3AF' }} />
                      Tipo: <b>{report.report_type === 'weekly_auto' ? 'Automatico' : 'Manual'}</b>
                    </span>
                  )}
                </div>
              </div>
            )
          })()}

          {/* ── Quantitative Metrics ── */}
          <div>
            <SectionHeader icon="fa-chart-bar">Metricas Quantitativas</SectionHeader>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <MetricCard value={report.quantitative_metrics?.tickets_resolved || 0} label="Resolvidos" accent />
              <MetricCard value={report.quantitative_metrics?.tickets_total || 0} label="Total Atribuidos" />
              <MetricCard value={`${report.quantitative_metrics?.sla_compliance_pct || 0}%`} label="SLA Cumprido" />
              <MetricCard value={`${report.quantitative_metrics?.avg_first_response_h || 0}h`} label="Tempo 1a Resposta" />
              <MetricCard value={`${report.quantitative_metrics?.avg_resolution_h || 0}h`} label="Tempo Resolucao" />
              <MetricCard value={report.quantitative_metrics?.csat_avg || 0} label={`CSAT (${report.quantitative_metrics?.csat_count || 0})`} />
              <MetricCard value={`${report.quantitative_metrics?.fcr_rate || 0}%`} label="FCR" />
              <MetricCard value={report.quantitative_metrics?.messages_per_ticket_avg || 0} label="Msgs/Ticket" />
            </div>
          </div>

          {/* ── Categories ── */}
          {report.quantitative_metrics?.tickets_by_category && Object.keys(report.quantitative_metrics.tickets_by_category).length > 0 && (
            <div className="glass-card p-6">
              <h3 className="text-xs font-bold uppercase tracking-wider mb-4" style={{ color: '#6B7280' }}>Distribuicao por Categoria</h3>
              <div className="flex flex-wrap gap-2.5">
                {Object.entries(report.quantitative_metrics.tickets_by_category).map(([cat, count]) => (
                  <span key={cat} className="px-3.5 py-1.5 rounded-full text-sm font-semibold"
                    style={{ background: '#F9FAFB', color: '#374151', border: '1px solid #E5E7EB' }}>
                    {cat} <span className="font-mono-carbon ml-1" style={{ color: '#B8860B' }}>{count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* ── AI Scores ── */}
          {report.ai_scores && !report.ai_scores.error && Object.keys(aiScores).length > 0 && (
            <div className="glass-card p-6">
              <SectionHeader icon="fa-brain">Analise Qualitativa IA</SectionHeader>
              <div className="flex flex-col lg:flex-row gap-8">
                <div className="flex flex-col items-center justify-center lg:pr-8 lg:border-r" style={{ borderColor: '#F3F4F6' }}>
                  <CircularGauge value={aiScores.overall} size={120} stroke={8} />
                  <span className="text-xs font-bold uppercase tracking-wider mt-2" style={{ color: '#4B5563' }}>Nota Geral</span>
                </div>
                <div className="flex-1">
                  {Object.entries(SCORE_META).filter(([k]) => k !== 'overall').map(([key, meta], i) => (
                    <ScoreBar key={key} value={aiScores[key]} label={meta.label} icon={meta.icon} delay={i * 80} />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── AI Text Sections ── */}
          {aiData ? (
            <div className="space-y-4">
              {aiData.summary && (
                <div className="glass-card p-6">
                  <SectionHeader icon="fa-file-lines">Parecer Geral</SectionHeader>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: '#374151' }}>
                    {aiData.summary}
                  </p>
                </div>
              )}

              {aiData.strengths?.length > 0 && (
                <div className="glass-card p-6" style={{ borderLeft: '3px solid #16a34a' }}>
                  <SectionHeader icon="fa-circle-check">Pontos Fortes</SectionHeader>
                  <ul className="space-y-2">
                    {aiData.strengths.map((s, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm" style={{ color: '#374151' }}>
                        <i className="fas fa-plus text-xs mt-1.5" style={{ color: '#16a34a' }} /> {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {aiData.improvements?.length > 0 && (
                <div className="glass-card p-6" style={{ borderLeft: '3px solid #ca8a04' }}>
                  <SectionHeader icon="fa-triangle-exclamation">Pontos de Melhoria</SectionHeader>
                  <ul className="space-y-2">
                    {aiData.improvements.map((s, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm" style={{ color: '#374151' }}>
                        <i className="fas fa-exclamation text-xs mt-1.5" style={{ color: '#ca8a04' }} /> {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {aiData.recommendations?.length > 0 && (
                <div className="glass-card p-6" style={{ borderLeft: '3px solid #2563eb' }}>
                  <SectionHeader icon="fa-lightbulb">Recomendacoes</SectionHeader>
                  <ul className="space-y-2">
                    {aiData.recommendations.map((s, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm" style={{ color: '#374151' }}>
                        <i className="fas fa-arrow-right text-xs mt-1.5" style={{ color: '#2563eb' }} /> {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {aiData.notable_examples && (
                <div className="glass-card p-6">
                  <SectionHeader icon="fa-quote-left">Exemplos Notaveis</SectionHeader>
                  <div className="space-y-4">
                    {aiData.notable_examples.best && (
                      <div className="p-4 rounded-lg" style={{ background: 'rgba(22,163,74,0.05)', border: '1px solid rgba(22,163,74,0.15)' }}>
                        <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: '#16a34a' }}>Melhor Exemplo</p>
                        <p className="text-sm leading-relaxed" style={{ color: '#374151' }}>{aiData.notable_examples.best}</p>
                      </div>
                    )}
                    {aiData.notable_examples.worst && (
                      <div className="p-4 rounded-lg" style={{ background: 'rgba(220,38,38,0.04)', border: '1px solid rgba(220,38,38,0.15)' }}>
                        <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: '#dc2626' }}>Ponto de Atencao</p>
                        <p className="text-sm leading-relaxed" style={{ color: '#374151' }}>{aiData.notable_examples.worst}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {aiData.training_priorities?.length > 0 && (
                <div className="glass-card p-6" style={{ borderLeft: '3px solid #7c3aed' }}>
                  <SectionHeader icon="fa-graduation-cap">Prioridades de Treinamento</SectionHeader>
                  <ul className="space-y-2">
                    {aiData.training_priorities.map((s, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm" style={{ color: '#374151' }}>
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold shrink-0 mt-0.5"
                          style={{ background: 'rgba(124,58,237,0.1)', color: '#7c3aed' }}>{i + 1}</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* ── Portuguese Diagnosis ── */}
              {aiData.portuguese_diagnosis && (
                <PortugueseDiagnosis data={aiData.portuguese_diagnosis} />
              )}
            </div>
          ) : aiText ? (
            <div className="glass-card p-6">
              <SectionHeader icon="fa-file-lines">Parecer</SectionHeader>
              <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: '#374151' }}>{aiText}</p>
            </div>
          ) : null}

          {/* AI Error */}
          {report.ai_scores?.error && (
            <div className="glass-card p-5 text-center" style={{ borderColor: 'rgba(220,38,38,0.3)' }}>
              <i className="fas fa-circle-xmark text-lg mb-2" style={{ color: '#dc2626' }} />
              <p className="text-sm font-medium" style={{ color: '#dc2626' }}>Analise IA indisponivel</p>
              <p className="text-xs mt-1" style={{ color: '#9CA3AF' }}>{report.ai_scores.error}</p>
            </div>
          )}

          {/* ── History ── */}
          {history.length > 0 && (
            <div className="glass-card p-6">
              <SectionHeader icon="fa-clock-rotate-left">Historico de Analises</SectionHeader>
              <div className="space-y-1">
                {history.map(h => {
                  const hScores = h.ai_scores?.scores || h.ai_scores || {}
                  const hOverall = hScores.overall || 0
                  const c = scoreColor(hOverall)
                  const isActive = report?.id === h.id
                  return (
                    <div key={h.id} onClick={() => handleViewReport(h.id)}
                      className="flex items-center justify-between p-3.5 rounded-lg cursor-pointer transition-all"
                      style={{
                        background: isActive ? 'rgba(229,168,0,0.06)' : 'transparent',
                        border: isActive ? '1px solid rgba(229,168,0,0.2)' : '1px solid transparent',
                      }}>
                      <div className="flex items-center gap-3">
                        <div className="w-11 h-11 rounded-lg flex items-center justify-center"
                          style={{ background: `${c}18` }}>
                          <span className="font-mono-carbon text-base font-bold" style={{ color: c }}>{hOverall || '-'}</span>
                        </div>
                        <div>
                          <p className="text-sm font-medium" style={{ color: '#374151' }}>
                            {new Date(h.created_at).toLocaleDateString('pt-BR')} · {new Date(h.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                          </p>
                          <p className="text-xs font-medium" style={{ color: '#6B7280' }}>
                            {h.report_type === 'weekly_auto' ? 'Automatico' : 'Manual'} · {h.sample_size || 'todas'} msgs · {new Date(h.period_start).toLocaleDateString('pt-BR')} - {new Date(h.period_end).toLocaleDateString('pt-BR')}
                          </p>
                        </div>
                      </div>
                      <i className="fas fa-chevron-right text-xs" style={{ color: '#9CA3AF' }} />
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

      ) : (
        /* Empty state */
        <div className="glass-card p-16 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl mb-4"
            style={{ background: '#F9FAFB' }}>
            <i className="fas fa-microscope fa-2x" style={{ color: '#E5E7EB' }} />
          </div>
          <p className="text-base font-medium" style={{ color: '#4B5563' }}>Nenhuma analise selecionada</p>
          <p className="text-sm mt-1.5" style={{ color: '#6B7280' }}>Selecione periodo e amostra, e clique em "Gerar Analise"</p>
        </div>
      )}
    </div>
  )
}
