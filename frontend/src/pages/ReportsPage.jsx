import React, { useState, useEffect } from 'react'
import { useToast } from '../components/Toast'
import {
  getDashboardStats, getAgentPerformance, getCsatReport,
  getTicketsBySource, getSentimentBreakdown, getTopCustomers,
  getAgentAnalysis, getTrends, getPatterns, getFullAIAnalysis,
  exportTicketsCsv, getAgentEmailMetrics,
} from '../services/api'
import { CATEGORY_LABELS } from '../constants/ticket'
const SENTIMENT_LABELS = { positive: 'Positivo', neutral: 'Neutro', negative: 'Negativo', angry: 'Irritado' }
const SOURCE_LABELS = { web: 'Web', slack: 'Slack', gmail: 'Gmail' }
const PRIORITY_LABELS = { urgent: 'Urgente', high: 'Alta', medium: 'Média', low: 'Baixa' }
const STATUS_LABELS = {
  open: 'Aberto', in_progress: 'Em Andamento', waiting: 'Aguardando',
  waiting_supplier: 'Ag. Fornecedor', waiting_resend: 'Ag. Reenvio',
  analyzing: 'Em Análise', resolved: 'Resolvido', closed: 'Fechado',
  escalated: 'Escalado', archived: 'Arquivado',
}

export default function ReportsPage() {
  const toast = useToast()
  const [days, setDays] = useState(30)
  const [tab, setTab] = useState('overview')
  const [loading, setLoading] = useState(true)

  const [stats, setStats] = useState(null)
  const [agents, setAgents] = useState([])
  const [csat, setCsat] = useState(null)
  const [sources, setSources] = useState({})
  const [sentiments, setSentiments] = useState({})
  const [customers, setCustomers] = useState([])
  const [trends, setTrends] = useState([])
  const [patterns, setPatterns] = useState(null)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [agentAnalysis, setAgentAnalysis] = useState(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [fullAnalysis, setFullAnalysis] = useState(null)
  const [fullAnalysisLoading, setFullAnalysisLoading] = useState(false)
  const [emailMetrics, setEmailMetrics] = useState([])
  const [exporting, setExporting] = useState(false)
  const [exportFilters, setExportFilters] = useState({ status: '', priority: '', category: '', date_from: '', date_to: '' })

  useEffect(() => { loadData() }, [days])

  const loadData = async () => {
    setLoading(true)
    try {
      const [s, a, c, src, sent, cust, tr, pat, em] = await Promise.allSettled([
        getDashboardStats(days), getAgentPerformance(days), getCsatReport(days),
        getTicketsBySource(days), getSentimentBreakdown(days), getTopCustomers(days),
        getTrends(days), getPatterns(days), getAgentEmailMetrics(days),
      ])
      if (s.status === 'fulfilled') setStats(s.value.data)
      if (a.status === 'fulfilled') setAgents(a.value.data.agents || [])
      if (c.status === 'fulfilled') setCsat(c.value.data)
      if (src.status === 'fulfilled') setSources(src.value.data.by_source || {})
      if (sent.status === 'fulfilled') setSentiments(sent.value.data.by_sentiment || {})
      if (cust.status === 'fulfilled') setCustomers(cust.value.data.customers || [])
      if (tr.status === 'fulfilled') setTrends(tr.value.data.trends || [])
      if (pat.status === 'fulfilled') setPatterns(pat.value.data)
      if (em.status === 'fulfilled') setEmailMetrics(em.value.data.agents || [])
    } finally { setLoading(false) }
  }

  const loadAgentAnalysis = async (agentId) => {
    setSelectedAgent(agentId)
    setAgentAnalysis(null)
    setAnalysisLoading(true)
    try { const { data } = await getAgentAnalysis(agentId, days); setAgentAnalysis(data) }
    catch (e) { toast.error('Erro ao carregar análise. Verifique ANTHROPIC_API_KEY.') }
    finally { setAnalysisLoading(false) }
  }

  const loadFullAnalysis = async () => {
    setFullAnalysisLoading(true); setFullAnalysis(null)
    try { const { data } = await getFullAIAnalysis(days); setFullAnalysis(data) }
    catch (e) { toast.error('Erro ao gerar análise. Verifique ANTHROPIC_API_KEY.') }
    finally { setFullAnalysisLoading(false) }
  }

  const handleExportCsv = async () => {
    setExporting(true)
    try {
      const params = {}
      Object.entries(exportFilters).forEach(([k, v]) => { if (v) params[k] = v })
      const response = await exportTicketsCsv(params)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `tickets_${new Date().toISOString().slice(0, 10)}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (e) { toast.error('Erro ao exportar') }
    finally { setExporting(false) }
  }

  const TABS = [
    { id: 'overview', label: 'Visão Geral', icon: 'fa-chart-line' },
    { id: 'trends', label: 'Tendências', icon: 'fa-chart-area' },
    { id: 'agents', label: 'Agentes', icon: 'fa-users' },
    { id: 'csat', label: 'Satisfação', icon: 'fa-star' },
    { id: 'patterns', label: 'Padrões', icon: 'fa-search' },
    { id: 'customers', label: 'Clientes', icon: 'fa-user-friends' },
    { id: 'ai-analysis', label: 'Análise IA', icon: 'fa-brain' },
    { id: 'export', label: 'Exportar', icon: 'fa-download' },
  ]

  const PERIOD_OPTIONS = [
    { value: 7, label: 'Últimos 7 dias' },
    { value: 14, label: 'Últimos 14 dias' },
    { value: 30, label: 'Últimos 30 dias' },
    { value: 60, label: 'Últimos 60 dias' },
    { value: 90, label: 'Últimos 90 dias' },
    { value: 180, label: 'Últimos 6 meses' },
    { value: 365, label: 'Último ano' },
  ]

  return (
    <div className="p-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white"><i className="fas fa-chart-bar mr-2" />Relatórios e Métricas</h1>
          <p className="text-carbon-400 text-sm mt-1">Acompanhe o desempenho da operação em tempo real</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={loadData} disabled={loading}
            className="bg-carbon-700 hover:bg-carbon-600 text-carbon-300 px-3 py-2 rounded-lg text-sm transition">
            <i className={`fas fa-sync-alt ${loading ? 'animate-spin' : ''} mr-1`} />Atualizar
          </button>
          <select value={days} onChange={e => setDays(Number(e.target.value))}
            className="bg-carbon-700 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm">
            {PERIOD_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      {/* Abas */}
      <div className="flex gap-1 mb-6 bg-carbon-700 rounded-lg p-1 flex-wrap">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm transition ${tab === t.id ? 'bg-indigo-600 text-white' : 'text-carbon-300 hover:text-white hover:bg-carbon-600'}`}>
            <i className={`fas ${t.icon} mr-2`} />{t.label}
          </button>
        ))}
      </div>

      {/* Loading global */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <i className="fas fa-spinner animate-spin text-3xl text-indigo-400" />
            <p className="text-carbon-400 mt-3">Carregando dados...</p>
          </div>
        </div>
      )}

      {/* ═══ VISÃO GERAL ═══ */}
      {!loading && tab === 'overview' && stats && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            <KpiCard label="Total de Tickets" value={stats.total_tickets} icon="fa-ticket" />
            <KpiCard label="Conformidade SLA" value={`${stats.sla_compliance}%`} icon="fa-clock"
              color={stats.sla_compliance >= 90 ? 'green' : stats.sla_compliance >= 70 ? 'yellow' : 'red'} />
            <KpiCard label="Tempo de Resposta" value={`${stats.avg_response_hours}h`} icon="fa-reply"
              subtitle="média" />
            <KpiCard label="Tempo de Resolução" value={`${stats.avg_resolution_hours}h`} icon="fa-check-circle"
              subtitle="média" />
            <KpiCard label="Risco Jurídico" value={stats.legal_risk_count} icon="fa-gavel" color="red" />
            <KpiCard label="SLA Estourado" value={stats.sla_breached} icon="fa-exclamation-triangle" color="red" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
            {/* Por Status */}
            <div className="bg-carbon-700 rounded-xl p-4">
              <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-tasks text-indigo-400 mr-2" />Por Status</h3>
              {Object.entries(stats.by_status || {}).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between py-1.5">
                  <span className="text-carbon-300 text-sm">{STATUS_LABELS[k] || k}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-28 bg-carbon-600 rounded-full h-2">
                      <div className="bg-indigo-500 h-2 rounded-full transition-all" style={{ width: `${Math.max((v / Math.max(stats.total_tickets, 1)) * 100, 2)}%` }} />
                    </div>
                    <span className="text-white text-sm font-medium w-8 text-right">{v}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Por Prioridade */}
            <div className="bg-carbon-700 rounded-xl p-4">
              <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-flag text-orange-400 mr-2" />Por Prioridade</h3>
              {Object.entries(stats.by_priority || {}).map(([k, v]) => {
                const colors = { urgent: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-yellow-500', low: 'bg-green-500' }
                return (
                  <div key={k} className="flex items-center justify-between py-1.5">
                    <span className="text-carbon-300 text-sm">{PRIORITY_LABELS[k] || k}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-28 bg-carbon-600 rounded-full h-2">
                        <div className={`${colors[k] || 'bg-indigo-500'} h-2 rounded-full transition-all`} style={{ width: `${Math.max((v / Math.max(stats.total_tickets, 1)) * 100, 2)}%` }} />
                      </div>
                      <span className="text-white text-sm font-medium w-8 text-right">{v}</span>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Canal + Sentimento */}
            <div className="bg-carbon-700 rounded-xl p-4">
              <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-globe text-blue-400 mr-2" />Por Canal</h3>
              {Object.entries(sources).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between py-1.5">
                  <span className="text-carbon-300 text-sm"><i className={`fas ${k === 'web' ? 'fa-globe' : k === 'slack' ? 'fa-hashtag' : k === 'gmail' ? 'fa-envelope' : 'fa-plug'} mr-2 text-carbon-500`} />{SOURCE_LABELS[k] || k}</span>
                  <span className="text-white text-sm font-medium">{v}</span>
                </div>
              ))}
              <div className="mt-3 pt-3 border-t border-carbon-600">
                <h4 className="text-white text-sm font-semibold mb-2"><i className="fas fa-heart text-pink-400 mr-2" />Sentimento</h4>
                {Object.entries(sentiments).map(([k, v]) => {
                  const colors = { positive: 'text-green-400', neutral: 'text-carbon-300', negative: 'text-orange-400', angry: 'text-red-400' }
                  const icons = { positive: 'fa-smile', neutral: 'fa-meh', negative: 'fa-frown', angry: 'fa-angry' }
                  return (
                    <div key={k} className="flex items-center justify-between py-1">
                      <span className={`text-sm ${colors[k] || 'text-carbon-300'}`}>
                        <i className={`fas ${icons[k] || 'fa-circle'} mr-2`} />{SENTIMENT_LABELS[k] || k}
                      </span>
                      <span className="text-white text-sm font-medium">{v}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Por Categoria */}
          <div className="bg-carbon-700 rounded-xl p-4">
            <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-folder text-yellow-400 mr-2" />Por Categoria</h3>
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
              {Object.entries(stats.by_category || {}).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                <div key={k} className="bg-carbon-800 rounded-lg p-3 text-center hover:bg-carbon-600/50 transition cursor-default">
                  <p className="text-white text-lg font-bold">{v}</p>
                  <p className="text-carbon-400 text-xs mt-1">{CATEGORY_LABELS[k] || k}</p>
                  <p className="text-carbon-500 text-xs">{stats.total_tickets > 0 ? Math.round((v / stats.total_tickets) * 100) : 0}%</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ═══ TENDÊNCIAS ═══ */}
      {!loading && tab === 'trends' && (
        <div>
          {/* Gráfico de volume */}
          <div className="bg-carbon-700 rounded-xl p-4 mb-6">
            <h3 className="text-white text-sm font-semibold mb-4"><i className="fas fa-chart-bar text-indigo-400 mr-2" />Volume Diário de Tickets</h3>
            {trends.length > 0 ? (
              <div>
                <div className="flex items-end gap-1 h-40">
                  {trends.map((d, i) => {
                    const maxVal = Math.max(...trends.map(t => t.total), 1)
                    const h = (d.total / maxVal) * 100
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center justify-end group relative">
                        <div className="absolute bottom-full mb-1 bg-carbon-900 text-white text-xs px-2 py-1 rounded hidden group-hover:block whitespace-nowrap z-10">
                          {d.date}: {d.total} tickets, {d.resolved} resolvidos
                        </div>
                        <div className="w-full bg-indigo-500 hover:bg-indigo-400 rounded-t transition-colors" style={{ height: `${h}%`, minHeight: d.total > 0 ? 4 : 0 }} />
                      </div>
                    )
                  })}
                </div>
                <div className="flex justify-between text-carbon-500 text-xs mt-2">
                  <span>{trends[0]?.date}</span>
                  <span>{trends[trends.length - 1]?.date}</span>
                </div>
              </div>
            ) : <EmptyState text="Sem dados de tendência para o período selecionado." />}
          </div>

          {/* Tempos médios */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            <div className="bg-carbon-700 rounded-xl p-4">
              <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-reply text-blue-400 mr-2" />Tempo Médio de Resposta (por dia)</h3>
              {trends.filter(t => t.avg_response_hours > 0).length > 0 ? (
                trends.filter(t => t.avg_response_hours > 0).slice(-15).map((d, i) => (
                  <div key={i} className="flex items-center justify-between py-1">
                    <span className="text-carbon-400 text-xs w-20">{d.date}</span>
                    <div className="flex items-center gap-2 flex-1 ml-2">
                      <div className="flex-1 bg-carbon-600 rounded-full h-2">
                        <div className={`h-2 rounded-full transition-all ${d.avg_response_hours <= 4 ? 'bg-green-500' : d.avg_response_hours <= 12 ? 'bg-yellow-500' : 'bg-red-500'}`}
                          style={{ width: `${Math.min((d.avg_response_hours / 24) * 100, 100)}%` }} />
                      </div>
                      <span className="text-white text-xs w-10 text-right">{d.avg_response_hours}h</span>
                    </div>
                  </div>
                ))
              ) : <EmptyState text="Sem dados de resposta no período." />}
            </div>
            <div className="bg-carbon-700 rounded-xl p-4">
              <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-check-circle text-green-400 mr-2" />Tempo Médio de Resolução (por dia)</h3>
              {trends.filter(t => t.avg_resolution_hours > 0).length > 0 ? (
                trends.filter(t => t.avg_resolution_hours > 0).slice(-15).map((d, i) => (
                  <div key={i} className="flex items-center justify-between py-1">
                    <span className="text-carbon-400 text-xs w-20">{d.date}</span>
                    <div className="flex items-center gap-2 flex-1 ml-2">
                      <div className="flex-1 bg-carbon-600 rounded-full h-2">
                        <div className={`h-2 rounded-full transition-all ${d.avg_resolution_hours <= 12 ? 'bg-green-500' : d.avg_resolution_hours <= 48 ? 'bg-yellow-500' : 'bg-red-500'}`}
                          style={{ width: `${Math.min((d.avg_resolution_hours / 72) * 100, 100)}%` }} />
                      </div>
                      <span className="text-white text-xs w-10 text-right">{d.avg_resolution_hours}h</span>
                    </div>
                  </div>
                ))
              ) : <EmptyState text="Sem dados de resolução no período." />}
            </div>
          </div>

          {/* KPIs do período */}
          {trends.length > 0 && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard label="Total no Período" value={trends.reduce((s, t) => s + t.total, 0)} icon="fa-ticket" />
              <KpiCard label="Resolvidos" value={trends.reduce((s, t) => s + t.resolved, 0)} icon="fa-check" color="green" />
              <KpiCard label="SLA Estourados" value={trends.reduce((s, t) => s + t.sla_breached, 0)} icon="fa-exclamation-triangle" color="red" />
              <KpiCard label="Média por Dia" value={(trends.reduce((s, t) => s + t.total, 0) / Math.max(trends.length, 1)).toFixed(1)} icon="fa-calculator" color="yellow" />
            </div>
          )}
        </div>
      )}

      {/* ═══ AGENTES ═══ */}
      {!loading && tab === 'agents' && (
        <div>
          {agents.length > 0 ? (
            <div className="bg-carbon-700 rounded-xl overflow-hidden mb-6">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-carbon-800 text-carbon-400 text-xs uppercase">
                    <th className="text-left p-3">Agente</th>
                    <th className="text-center p-3">Tickets</th>
                    <th className="text-center p-3">Resolvidos</th>
                    <th className="text-center p-3">Taxa Resolução</th>
                    <th className="text-center p-3">Tempo Resposta</th>
                    <th className="text-center p-3">Tempo Resolução</th>
                    <th className="text-center p-3">SLA</th>
                    <th className="text-center p-3">Satisfação</th>
                    <th className="text-center p-3">Análise</th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map(a => (
                    <tr key={a.id} className="border-t border-carbon-600 hover:bg-carbon-600/30 transition">
                      <td className="p-3 text-white font-medium">{a.name}</td>
                      <td className="p-3 text-center text-carbon-200">{a.total_tickets}</td>
                      <td className="p-3 text-center text-green-400">{a.resolved}</td>
                      <td className="p-3 text-center text-carbon-200">{a.resolution_rate}%</td>
                      <td className={`p-3 text-center ${a.avg_response_hours <= 4 ? 'text-green-400' : a.avg_response_hours <= 12 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {a.avg_response_hours}h
                      </td>
                      <td className={`p-3 text-center ${a.avg_resolution_hours <= 24 ? 'text-green-400' : a.avg_resolution_hours <= 48 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {a.avg_resolution_hours}h
                      </td>
                      <td className={`p-3 text-center font-medium ${a.sla_compliance >= 90 ? 'text-green-400' : a.sla_compliance >= 70 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {a.sla_compliance}%
                      </td>
                      <td className="p-3 text-center">
                        {a.csat_count > 0 ? <span className="text-yellow-400">{a.csat_avg}/5</span> : <span className="text-carbon-500">—</span>}
                      </td>
                      <td className="p-3 text-center">
                        <button onClick={() => loadAgentAnalysis(a.id)}
                          className="bg-orange-600/20 hover:bg-orange-600/40 text-orange-300 px-3 py-1 rounded text-xs transition">
                          <i className="fas fa-brain mr-1" />Analisar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <EmptyState text="Nenhum agente encontrado no período selecionado." />}

          {/* Métricas de Email por Agente */}
          {emailMetrics.length > 0 && (
            <div className="bg-carbon-700 rounded-xl overflow-hidden mb-6">
              <div className="p-4 border-b border-carbon-600">
                <h3 className="text-white text-sm font-semibold"><i className="fas fa-envelope text-blue-400 mr-2" />Métricas de Email por Especialista</h3>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-carbon-800 text-carbon-400 text-xs uppercase">
                    <th className="text-left p-3">Agente</th>
                    <th className="text-center p-3">Recebidos</th>
                    <th className="text-center p-3">Enviados</th>
                    <th className="text-center p-3">Tempo Resp.</th>
                    <th className="text-center p-3">Atribuídos</th>
                    <th className="text-center p-3">Resolvidos</th>
                    <th className="text-center p-3">Redirecionados</th>
                    <th className="text-center p-3">SLA Estourado</th>
                    <th className="text-center p-3">Sem Resposta</th>
                  </tr>
                </thead>
                <tbody>
                  {emailMetrics.map(a => (
                    <tr key={a.id} className="border-t border-carbon-600 hover:bg-carbon-600/30 transition">
                      <td className="p-3 text-white font-medium">{a.name}</td>
                      <td className="p-3 text-center text-blue-400">{a.emails_received}</td>
                      <td className="p-3 text-center text-green-400">{a.emails_sent}</td>
                      <td className={`p-3 text-center ${a.avg_response_time_hours <= 4 ? 'text-green-400' : a.avg_response_time_hours <= 12 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {a.avg_response_time_hours}h
                      </td>
                      <td className="p-3 text-center text-carbon-200">{a.tickets_assigned}</td>
                      <td className="p-3 text-center text-green-400">{a.tickets_resolved}</td>
                      <td className="p-3 text-center text-orange-400">{a.tickets_redirected}</td>
                      <td className={`p-3 text-center font-medium ${a.sla_breached > 0 ? 'text-red-400' : 'text-green-400'}`}>
                        {a.sla_breached}
                      </td>
                      <td className={`p-3 text-center font-medium ${a.unanswered > 0 ? 'text-red-400' : 'text-green-400'}`}>
                        {a.unanswered}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Análise individual do agente */}
          {selectedAgent && (
            <div className="bg-carbon-700 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-semibold"><i className="fas fa-brain text-orange-400 mr-2" />
                  Análise IA — {agentAnalysis?.metrics?.agent_name || 'Carregando...'}</h3>
                <button onClick={() => { setSelectedAgent(null); setAgentAnalysis(null) }}
                  className="text-carbon-400 hover:text-white transition"><i className="fas fa-times" /></button>
              </div>
              {analysisLoading ? (
                <div className="text-center py-8"><i className="fas fa-spinner animate-spin text-2xl text-orange-400" />
                  <p className="text-carbon-400 mt-2">Analisando desempenho do agente...</p></div>
              ) : agentAnalysis?.ai_analysis && !agentAnalysis.ai_analysis.error ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-4 bg-carbon-800 rounded-lg p-4">
                    <div className="text-center">
                      <p className={`text-3xl font-bold ${agentAnalysis.ai_analysis.nota_geral >= 8 ? 'text-green-400' : agentAnalysis.ai_analysis.nota_geral >= 5 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {agentAnalysis.ai_analysis.nota_geral}/10</p>
                      <p className="text-carbon-400 text-xs">Nota Geral</p>
                    </div>
                    <p className="text-carbon-200 text-sm flex-1">{agentAnalysis.ai_analysis.resumo}</p>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <AnalysisCard title="Pontos Fortes" icon="fa-thumbs-up" color="green" items={agentAnalysis.ai_analysis.pontos_fortes} />
                    <AnalysisCard title="Pontos de Melhoria" icon="fa-exclamation-circle" color="orange" items={agentAnalysis.ai_analysis.pontos_melhoria} />
                    <AnalysisCard title="Recomendações" icon="fa-lightbulb" color="indigo" items={agentAnalysis.ai_analysis.recomendacoes} />
                  </div>
                </div>
              ) : <p className="text-carbon-400 text-sm">Configure ANTHROPIC_API_KEY para usar análise por IA.</p>}
            </div>
          )}
        </div>
      )}

      {/* ═══ SATISFAÇÃO (CSAT & NPS) ═══ */}
      {!loading && tab === 'csat' && csat && (
        <div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-carbon-700 rounded-xl p-4 text-center">
              <p className="text-3xl font-bold text-yellow-400">{csat.csat_avg || 0}/5</p>
              <p className="text-carbon-400 text-sm mt-1">Satisfação Média</p>
              <p className="text-carbon-500 text-xs">{csat.total_ratings} avaliações</p>
            </div>
            <div className="bg-carbon-700 rounded-xl p-4 text-center">
              <p className={`text-3xl font-bold ${csat.nps_score >= 50 ? 'text-green-400' : csat.nps_score >= 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                {csat.nps_score}</p>
              <p className="text-carbon-400 text-sm mt-1">Pontuação NPS</p>
              <p className="text-carbon-500 text-xs">{csat.nps_score >= 50 ? 'Excelente' : csat.nps_score >= 0 ? 'Bom' : 'Precisa melhorar'}</p>
            </div>
            <div className="bg-carbon-700 rounded-xl p-4 text-center">
              <p className="text-xl font-bold text-green-400">{csat.nps_promoters}</p>
              <p className="text-carbon-400 text-sm">Promotores</p>
              <p className="text-xl font-bold text-red-400 mt-2">{csat.nps_detractors}</p>
              <p className="text-carbon-400 text-sm">Detratores</p>
            </div>
            <div className="bg-carbon-700 rounded-xl p-4">
              <h4 className="text-white text-sm font-semibold mb-2">Distribuição de Notas</h4>
              {[5, 4, 3, 2, 1].map(n => {
                const count = csat.distribution?.[String(n)] || 0
                const pct = csat.total_ratings > 0 ? (count / csat.total_ratings) * 100 : 0
                const colors = { 5: 'bg-green-500', 4: 'bg-green-400', 3: 'bg-yellow-500', 2: 'bg-orange-500', 1: 'bg-red-500' }
                const stars = '★'.repeat(n)
                return (
                  <div key={n} className="flex items-center gap-2 py-0.5">
                    <span className="text-yellow-400 text-xs w-12">{stars}</span>
                    <div className="flex-1 bg-carbon-600 rounded-full h-2">
                      <div className={`${colors[n]} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-carbon-400 text-xs w-8 text-right">{count}</span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Tendência CSAT */}
          {csat.daily_trend?.length > 0 && (
            <div className="bg-carbon-700 rounded-xl p-4 mb-6">
              <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-chart-line text-yellow-400 mr-2" />Evolução da Satisfação</h3>
              <div className="flex items-end gap-1 h-24">
                {csat.daily_trend.map((d, i) => (
                  <div key={i} className="flex-1 group relative">
                    <div className="absolute bottom-full mb-1 bg-carbon-900 text-white text-xs px-2 py-1 rounded hidden group-hover:block whitespace-nowrap z-10">
                      {d.date}: {d.avg}/5 ({d.count} avaliações)</div>
                    <div className={`w-full rounded-t transition-colors ${d.avg >= 4 ? 'bg-green-500 hover:bg-green-400' : d.avg >= 3 ? 'bg-yellow-500 hover:bg-yellow-400' : 'bg-red-500 hover:bg-red-400'}`}
                      style={{ height: `${(d.avg / 5) * 100}%` }} />
                  </div>
                ))}
              </div>
              <div className="flex justify-between text-carbon-500 text-xs mt-2">
                <span>{csat.daily_trend[0]?.date}</span>
                <span>{csat.daily_trend[csat.daily_trend.length - 1]?.date}</span>
              </div>
            </div>
          )}

          {/* Comentários recentes */}
          {csat.recent_comments?.length > 0 && (
            <div className="bg-carbon-700 rounded-xl p-4">
              <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-comments text-indigo-400 mr-2" />Comentários Recentes dos Clientes</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {csat.recent_comments.map((c, i) => (
                  <div key={i} className="bg-carbon-800 rounded-lg p-3 flex items-start gap-3">
                    <div className={`px-2 py-1 rounded text-xs font-bold shrink-0 ${c.score >= 4 ? 'bg-green-500/20 text-green-400' : c.score === 3 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'}`}>
                      {c.score}/5</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-carbon-200 text-sm">{c.comment}</p>
                      <p className="text-carbon-500 text-xs mt-1">{new Date(c.date).toLocaleDateString('pt-BR')}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══ PADRÕES ═══ */}
      {!loading && tab === 'patterns' && patterns && (
        <div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
            <KpiCard label="Taxa de Escalação" value={`${patterns.escalation_rate}%`} icon="fa-arrow-up"
              color={patterns.escalation_rate > 15 ? 'red' : patterns.escalation_rate > 5 ? 'yellow' : 'green'} />
            <KpiCard label="Risco Jurídico" value={patterns.legal_risk_count} icon="fa-gavel" color="red" />
            <KpiCard label="Clientes Recorrentes" value={patterns.repeat_customers?.length || 0} icon="fa-redo" color="yellow" />
          </div>

          {/* Hotspots */}
          <div className="bg-carbon-700 rounded-xl p-4 mb-6">
            <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-fire text-orange-400 mr-2" />Pontos Críticos (Hotspots)</h3>
            {patterns.hotspots?.length > 0 ? (
              <table className="w-full text-sm">
                <thead><tr className="text-carbon-400 text-xs uppercase">
                  <th className="text-left p-2">Categoria</th><th className="text-left p-2">Prioridade</th>
                  <th className="text-center p-2">Quantidade</th><th className="text-center p-2">SLA Estourado</th>
                  <th className="text-center p-2">Tempo Resolução</th>
                </tr></thead>
                <tbody>
                  {patterns.hotspots.map((h, i) => (
                    <tr key={i} className="border-t border-carbon-600 hover:bg-carbon-600/30 transition">
                      <td className="p-2 text-white">{CATEGORY_LABELS[h.category] || h.category}</td>
                      <td className="p-2"><PriorityBadge priority={h.priority} /></td>
                      <td className="p-2 text-center text-carbon-200">{h.count}</td>
                      <td className="p-2 text-center"><span className={h.sla_breached > 0 ? 'text-red-400 font-medium' : 'text-green-400'}>{h.sla_breached}</span></td>
                      <td className="p-2 text-center text-carbon-200">{h.avg_resolution_hours}h</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <EmptyState text="Nenhum hotspot identificado no período." />}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Tags frequentes */}
            <div className="bg-carbon-700 rounded-xl p-4">
              <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-tags text-indigo-400 mr-2" />Tags Mais Frequentes</h3>
              {patterns.top_tags?.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {patterns.top_tags.map((t, i) => (
                    <span key={i} className="bg-indigo-600/20 text-indigo-300 px-3 py-1.5 rounded-full text-xs">
                      {t.tag} <span className="text-indigo-400 font-bold">({t.count})</span>
                    </span>
                  ))}
                </div>
              ) : <EmptyState text="Nenhuma tag encontrada." />}
            </div>

            {/* Clientes recorrentes */}
            <div className="bg-carbon-700 rounded-xl p-4">
              <h3 className="text-white text-sm font-semibold mb-3"><i className="fas fa-redo text-yellow-400 mr-2" />Clientes Recorrentes</h3>
              {patterns.repeat_customers?.length > 0 ? (
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {patterns.repeat_customers.map((c, i) => (
                    <div key={i} className="flex items-center justify-between py-1.5 hover:bg-carbon-600/30 px-2 rounded transition">
                      <div className="min-w-0">
                        <span className="text-white text-sm">{c.name}</span>
                        <span className="text-carbon-500 text-xs ml-2">{c.email}</span>
                      </div>
                      <span className="bg-yellow-600/20 text-yellow-400 px-2 py-0.5 rounded text-xs font-bold shrink-0">{c.count} tickets</span>
                    </div>
                  ))}
                </div>
              ) : <EmptyState text="Nenhum cliente recorrente no período." />}
            </div>
          </div>
        </div>
      )}

      {/* ═══ CLIENTES ═══ */}
      {!loading && tab === 'customers' && (
        <div>
          {customers.length > 0 ? (
            <div className="bg-carbon-700 rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead><tr className="bg-carbon-800 text-carbon-400 text-xs uppercase">
                  <th className="text-left p-3">Cliente</th><th className="text-left p-3">E-mail</th>
                  <th className="text-center p-3">Nº de Tickets</th><th className="text-center p-3">Risco</th>
                </tr></thead>
                <tbody>
                  {customers.map((c, i) => {
                    const riskPct = Math.round(c.risk_score * 100)
                    return (
                      <tr key={i} className="border-t border-carbon-600 hover:bg-carbon-600/30 transition">
                        <td className="p-3 text-white font-medium">{c.name}</td>
                        <td className="p-3 text-carbon-300">{c.email}</td>
                        <td className="p-3 text-center text-carbon-200">{c.ticket_count}</td>
                        <td className="p-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${riskPct > 50 ? 'bg-red-500/20 text-red-400' : riskPct > 20 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
                            {riskPct}%
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : <EmptyState text="Nenhum cliente encontrado no período selecionado." />}
        </div>
      )}

      {/* ═══ ANÁLISE IA COMPLETA ═══ */}
      {!loading && tab === 'ai-analysis' && (
        <div>
          {!fullAnalysis && !fullAnalysisLoading && (
            <div className="bg-carbon-700 rounded-xl p-8 text-center">
              <i className="fas fa-brain text-5xl text-orange-400 mb-4" />
              <h3 className="text-white text-lg font-semibold mb-2">Análise Completa com Inteligência Artificial</h3>
              <p className="text-carbon-400 text-sm mb-6 max-w-md mx-auto">
                Gere uma análise profunda da operação: padrões identificados, erros recorrentes, desempenho da equipe, perfil de clientes e plano de ação.
              </p>
              <button onClick={loadFullAnalysis}
                className="bg-orange-600 hover:bg-orange-500 text-white px-6 py-3 rounded-lg font-medium transition">
                <i className="fas fa-rocket mr-2" />Gerar Análise ({PERIOD_OPTIONS.find(o => o.value === days)?.label || `${days} dias`})
              </button>
            </div>
          )}
          {fullAnalysisLoading && (
            <div className="bg-carbon-700 rounded-xl p-12 text-center">
              <i className="fas fa-spinner animate-spin text-4xl text-orange-400" />
              <p className="text-carbon-400 mt-4">Analisando toda a operação com IA...</p>
              <p className="text-carbon-500 text-xs mt-1">Isso pode levar alguns segundos</p>
            </div>
          )}
          {fullAnalysis?.ai_analysis && !fullAnalysis.ai_analysis.error && (
            <div className="space-y-6">
              {/* Nota e resumo */}
              <div className="bg-carbon-700 rounded-xl p-6">
                <div className="flex items-center gap-6">
                  <div className="text-center shrink-0">
                    <p className={`text-5xl font-bold ${fullAnalysis.ai_analysis.nota_operacao >= 8 ? 'text-green-400' : fullAnalysis.ai_analysis.nota_operacao >= 5 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {fullAnalysis.ai_analysis.nota_operacao}/10</p>
                    <p className="text-carbon-400 text-sm mt-1">Nota da Operação</p>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-white font-semibold mb-2">Resumo Executivo</h3>
                    <p className="text-carbon-200 text-sm leading-relaxed">{fullAnalysis.ai_analysis.resumo_executivo}</p>
                  </div>
                </div>
              </div>

              {/* Indicadores críticos */}
              {fullAnalysis.ai_analysis.indicadores_criticos?.length > 0 && (
                <div className="bg-carbon-700 rounded-xl p-4">
                  <h3 className="text-white font-semibold mb-3"><i className="fas fa-tachometer-alt text-indigo-400 mr-2" />Indicadores Críticos</h3>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    {fullAnalysis.ai_analysis.indicadores_criticos.map((ind, i) => {
                      const statusColors = { bom: 'border-green-600 bg-green-900/20', atencao: 'border-yellow-600 bg-yellow-900/20', critico: 'border-red-600 bg-red-900/20' }
                      const dotColors = { bom: 'bg-green-400', atencao: 'bg-yellow-400', critico: 'bg-red-400' }
                      const statusLabels = { bom: 'Bom', atencao: 'Atenção', critico: 'Crítico' }
                      return (
                        <div key={i} className={`border rounded-lg p-3 ${statusColors[ind.status] || 'border-carbon-600'}`}>
                          <div className="flex items-center gap-2 mb-1">
                            <div className={`w-2 h-2 rounded-full ${dotColors[ind.status] || 'bg-carbon-400'}`} />
                            <span className="text-white text-sm font-medium">{ind.indicador}</span>
                            <span className="text-carbon-400 text-xs ml-auto">{statusLabels[ind.status] || ind.status}</span>
                            <span className="text-carbon-300 text-sm font-bold">{ind.valor}</span>
                          </div>
                          <p className="text-carbon-400 text-xs">{ind.explicacao}</p>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Padrões + Erros */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {fullAnalysis.ai_analysis.padroes_identificados?.length > 0 && (
                  <div className="bg-carbon-700 rounded-xl p-4">
                    <h3 className="text-white font-semibold mb-3"><i className="fas fa-search text-indigo-400 mr-2" />Padrões Identificados</h3>
                    {fullAnalysis.ai_analysis.padroes_identificados.map((p, i) => (
                      <div key={i} className="bg-carbon-800 rounded-lg p-3 mb-2">
                        <div className="flex items-center gap-2 mb-1">
                          <ImpactBadge level={p.impacto} />
                          <span className="text-white text-sm">{p.padrao}</span>
                        </div>
                        <p className="text-carbon-400 text-xs"><i className="fas fa-lightbulb text-yellow-400 mr-1" />Ação sugerida: {p.acao_sugerida}</p>
                      </div>
                    ))}
                  </div>
                )}
                {fullAnalysis.ai_analysis.erros_recorrentes?.length > 0 && (
                  <div className="bg-carbon-700 rounded-xl p-4">
                    <h3 className="text-white font-semibold mb-3"><i className="fas fa-bug text-red-400 mr-2" />Erros Recorrentes</h3>
                    {fullAnalysis.ai_analysis.erros_recorrentes.map((e, i) => (
                      <div key={i} className="bg-carbon-800 rounded-lg p-3 mb-2">
                        <p className="text-white text-sm font-medium">{e.problema}</p>
                        <p className="text-carbon-400 text-xs mt-1"><i className="fas fa-question-circle mr-1" />Causa provável: {e.causa_provavel}</p>
                        <p className="text-green-400 text-xs mt-0.5"><i className="fas fa-check-circle mr-1" />Solução: {e.solucao}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Equipe + Clientes */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {fullAnalysis.ai_analysis.analise_equipe && (
                  <div className="bg-carbon-700 rounded-xl p-4">
                    <h3 className="text-white font-semibold mb-3"><i className="fas fa-users text-indigo-400 mr-2" />Análise da Equipe</h3>
                    <div className="space-y-3">
                      <div className="bg-green-900/20 border border-green-700/30 rounded-lg p-3">
                        <p className="text-green-400 text-xs font-semibold mb-1"><i className="fas fa-star mr-1" />Destaque Positivo</p>
                        <p className="text-carbon-200 text-sm">{fullAnalysis.ai_analysis.analise_equipe.destaque_positivo}</p>
                      </div>
                      <div className="bg-orange-900/20 border border-orange-700/30 rounded-lg p-3">
                        <p className="text-orange-400 text-xs font-semibold mb-1"><i className="fas fa-exclamation-triangle mr-1" />Ponto de Atenção</p>
                        <p className="text-carbon-200 text-sm">{fullAnalysis.ai_analysis.analise_equipe.ponto_atencao}</p>
                      </div>
                      <div className="bg-indigo-900/20 border border-indigo-700/30 rounded-lg p-3">
                        <p className="text-indigo-400 text-xs font-semibold mb-1"><i className="fas fa-graduation-cap mr-1" />Sugestão de Treinamento</p>
                        <p className="text-carbon-200 text-sm">{fullAnalysis.ai_analysis.analise_equipe.recomendacao_treinamento}</p>
                      </div>
                    </div>
                  </div>
                )}
                {fullAnalysis.ai_analysis.analise_clientes && (
                  <div className="bg-carbon-700 rounded-xl p-4">
                    <h3 className="text-white font-semibold mb-3"><i className="fas fa-user-friends text-yellow-400 mr-2" />Análise de Clientes</h3>
                    <div className="space-y-3">
                      <div className="bg-carbon-800 rounded-lg p-3">
                        <p className="text-carbon-400 text-xs font-semibold mb-1"><i className="fas fa-chart-pie mr-1" />Perfil das Reclamações</p>
                        <p className="text-carbon-200 text-sm">{fullAnalysis.ai_analysis.analise_clientes.perfil_reclamacoes}</p>
                      </div>
                      <div className="bg-carbon-800 rounded-lg p-3">
                        <p className="text-red-400 text-xs font-semibold mb-1"><i className="fas fa-user-minus mr-1" />Risco de Perda (Churn)</p>
                        <p className="text-carbon-200 text-sm">{fullAnalysis.ai_analysis.analise_clientes.risco_churn}</p>
                      </div>
                      <div className="bg-carbon-800 rounded-lg p-3">
                        <p className="text-green-400 text-xs font-semibold mb-1"><i className="fas fa-gem mr-1" />Oportunidades</p>
                        <p className="text-carbon-200 text-sm">{fullAnalysis.ai_analysis.analise_clientes.oportunidades}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Plano de ação */}
              {fullAnalysis.ai_analysis.plano_acao?.length > 0 && (
                <div className="bg-carbon-700 rounded-xl p-4">
                  <h3 className="text-white font-semibold mb-3"><i className="fas fa-tasks text-green-400 mr-2" />Plano de Ação</h3>
                  {fullAnalysis.ai_analysis.plano_acao.map((a, i) => (
                    <div key={i} className="flex items-start gap-3 bg-carbon-800 rounded-lg p-3 mb-2">
                      <span className="bg-indigo-600 text-white w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0">
                        {a.prioridade}
                      </span>
                      <div className="flex-1">
                        <p className="text-white text-sm font-medium">{a.acao}</p>
                        <div className="flex items-center gap-4 mt-1">
                          <span className="text-carbon-400 text-xs"><i className="fas fa-clock mr-1" />Prazo: {a.prazo}</span>
                          <span className="text-green-400 text-xs"><i className="fas fa-chart-line mr-1" />Impacto: {a.impacto_esperado}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <button onClick={loadFullAnalysis} className="bg-carbon-700 hover:bg-carbon-600 text-carbon-300 px-4 py-2 rounded-lg text-sm transition">
                <i className="fas fa-redo mr-2" />Gerar Nova Análise
              </button>
            </div>
          )}
          {fullAnalysis?.ai_analysis?.error && (
            <div className="bg-red-900/20 border border-red-700/30 rounded-xl p-6 text-center">
              <i className="fas fa-exclamation-triangle text-red-400 text-2xl mb-2" />
              <p className="text-red-300">Erro na análise. Verifique se a ANTHROPIC_API_KEY está configurada.</p>
            </div>
          )}
        </div>
      )}

      {/* ═══ EXPORTAR ═══ */}
      {!loading && tab === 'export' && (
        <div className="max-w-2xl">
          <div className="bg-carbon-700 rounded-xl p-6">
            <h3 className="text-white font-semibold mb-2"><i className="fas fa-download text-indigo-400 mr-2" />Exportar Tickets</h3>
            <p className="text-carbon-400 text-sm mb-4">Exporte os tickets em formato CSV com filtros personalizados.</p>
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label className="text-carbon-400 text-xs block mb-1">Status</label>
                <select value={exportFilters.status} onChange={e => setExportFilters(f => ({...f, status: e.target.value}))}
                  className="w-full bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm">
                  <option value="">Todos os status</option>
                  <option value="open">Aberto</option>
                  <option value="in_progress">Em Andamento</option>
                  <option value="waiting">Aguardando</option>
                  <option value="resolved">Resolvido</option>
                  <option value="escalated">Escalado</option>
                </select>
              </div>
              <div>
                <label className="text-carbon-400 text-xs block mb-1">Prioridade</label>
                <select value={exportFilters.priority} onChange={e => setExportFilters(f => ({...f, priority: e.target.value}))}
                  className="w-full bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm">
                  <option value="">Todas as prioridades</option>
                  <option value="urgent">Urgente</option>
                  <option value="high">Alta</option>
                  <option value="medium">Média</option>
                  <option value="low">Baixa</option>
                </select>
              </div>
              <div>
                <label className="text-carbon-400 text-xs block mb-1">Categoria</label>
                <select value={exportFilters.category} onChange={e => setExportFilters(f => ({...f, category: e.target.value}))}
                  className="w-full bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm">
                  <option value="">Todas as categorias</option>
                  {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="text-carbon-400 text-xs block mb-1">Data Início</label>
                <input type="date" value={exportFilters.date_from} onChange={e => setExportFilters(f => ({...f, date_from: e.target.value}))}
                  className="w-full bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
              <div className="col-span-2 grid grid-cols-2 gap-4">
                <div>
                  <label className="text-carbon-400 text-xs block mb-1">Data Fim</label>
                  <input type="date" value={exportFilters.date_to} onChange={e => setExportFilters(f => ({...f, date_to: e.target.value}))}
                    className="w-full bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
            </div>
            <button onClick={handleExportCsv} disabled={exporting}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-lg font-medium w-full disabled:opacity-50 transition">
              {exporting ? <><i className="fas fa-spinner animate-spin mr-2" />Exportando...</> : <><i className="fas fa-file-csv mr-2" />Baixar CSV</>}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── Componentes auxiliares ─── */

function KpiCard({ label, value, icon, color, subtitle }) {
  const c = { green: 'text-green-400', yellow: 'text-yellow-400', red: 'text-red-400' }
  return (
    <div className="bg-carbon-700 rounded-xl p-4 hover:bg-carbon-600/50 transition">
      <div className="flex items-center gap-2 mb-2">
        <i className={`fas ${icon} ${c[color] || 'text-carbon-400'}`} />
        <span className="text-carbon-400 text-xs">{label}</span>
      </div>
      <p className={`text-xl font-bold ${c[color] || 'text-white'}`}>{value}</p>
      {subtitle && <p className="text-carbon-500 text-xs mt-0.5">{subtitle}</p>}
    </div>
  )
}

function AnalysisCard({ title, icon, color, items }) {
  return (
    <div className={`bg-${color}-900/20 border border-${color}-700/30 rounded-lg p-4`}>
      <h4 className={`text-${color}-400 text-sm font-semibold mb-2`}><i className={`fas ${icon} mr-1`} />{title}</h4>
      {items?.length > 0 ? (
        <ul className="space-y-1">{items.map((p, i) => <li key={i} className="text-carbon-200 text-sm">• {p}</li>)}</ul>
      ) : <p className="text-carbon-500 text-xs">Sem dados.</p>}
    </div>
  )
}

function PriorityBadge({ priority }) {
  const s = { urgent: 'bg-red-500/20 text-red-400', high: 'bg-orange-500/20 text-orange-400', medium: 'bg-yellow-500/20 text-yellow-400', low: 'bg-green-500/20 text-green-400' }
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${s[priority] || 'bg-carbon-600 text-carbon-300'}`}>{PRIORITY_LABELS[priority] || priority}</span>
}

function ImpactBadge({ level }) {
  const s = { alto: 'bg-red-500/20 text-red-400', medio: 'bg-yellow-500/20 text-yellow-400', baixo: 'bg-green-500/20 text-green-400' }
  const labels = { alto: 'Alto', medio: 'Médio', baixo: 'Baixo' }
  return <span className={`px-2 py-0.5 rounded text-xs ${s[level] || 'bg-carbon-600 text-carbon-300'}`}>{labels[level] || level}</span>
}

function EmptyState({ text }) {
  return (
    <div className="text-center py-8">
      <i className="fas fa-inbox text-2xl text-carbon-600 mb-2" />
      <p className="text-carbon-400 text-sm">{text}</p>
    </div>
  )
}
