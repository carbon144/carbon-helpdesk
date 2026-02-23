import React, { useState, useEffect } from 'react'
import { getDashboardStats, getAgentDashboardStats } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts'
import { useTheme } from '../contexts/ThemeContext'

const COLORS = ['#fdd200', '#e6c000', '#f59e0b', '#10b981', '#3b82f6', '#ec4899', '#ef4444', '#14b8a6', '#f97316']

const CATEGORY_LABELS = {
  garantia: 'Garantia', troca: 'Troca', mau_uso: 'Mau Uso', carregador: 'Carregador',
  duvida: 'Dúvida', reclamacao: 'Reclamação', juridico: 'Jurídico',
  suporte_tecnico: 'Suporte Técnico', financeiro: 'Financeiro', chargeback: 'Chargeback',
}

const STATUS_LABELS = {
  open: 'Aberto', in_progress: 'Em Andamento', waiting: 'Aguardando',
  waiting_supplier: 'Ag. Fornecedor', waiting_resend: 'Ag. Reenvio',
  analyzing: 'Em Análise', resolved: 'Resolvido', closed: 'Fechado', escalated: 'Escalado',
}

const PRIORITY_LABELS = { low: 'Baixa', medium: 'Média', high: 'Alta', urgent: 'Urgente' }

const SENTIMENT_LABELS = { positive: 'Positivo', neutral: 'Neutro', negative: 'Negativo', angry: 'Irritado' }

const DASHBOARD_VIEWS = [
  { id: 'admin', label: 'Administrador', icon: 'fa-shield-halved', desc: 'Visão completa da operação' },
  { id: 'gestao', label: 'Gestão', icon: 'fa-chart-pie', desc: 'KPIs e performance da equipe' },
  { id: 'agente', label: 'Agente', icon: 'fa-headset', desc: 'Meus tickets e performance' },
  { id: 'trocas', label: 'Trocas', icon: 'fa-rotate', desc: 'Tickets de troca e devolução' },
  { id: 'problemas', label: 'Problemas', icon: 'fa-triangle-exclamation', desc: 'Garantia, defeitos, técnico' },
  { id: 'reclamacoes', label: 'Reclamações', icon: 'fa-face-angry', desc: 'Reclamações e jurídico' },
]

// Theme-aware chart styles
function useChartStyles() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  return {
    tooltip: {
      background: isDark ? '#1a1a1f' : '#ffffff',
      border: `1px solid ${isDark ? '#3a3a42' : '#dee2e6'}`,
      color: isDark ? '#fafafa' : '#1a1a2e',
      borderRadius: '8px',
      boxShadow: isDark ? '0 4px 12px rgba(0,0,0,0.5)' : '0 4px 12px rgba(0,0,0,0.08)',
    },
    grid: isDark ? '#2a2a32' : '#e9ecef',
    axisTick: isDark ? '#71717a' : '#868e96',
    axisLabel: isDark ? '#a1a1aa' : '#495057',
    pieLabel: isDark ? '#d4d4d8' : '#343a40',
  }
}

export default function DashboardPage({ user, onNavigate }) {
  const [stats, setStats] = useState(null)
  const [agentStats, setAgentStats] = useState(null)
  const [days, setDays] = useState(30)
  const [view, setView] = useState(() => {
    if (user?.role === 'agent') return 'agente'
    if (user?.role === 'supervisor') return 'gestao'
    return 'admin'
  })

  useEffect(() => { loadStats() }, [days])

  const loadStats = async () => {
    try {
      const [s, a] = await Promise.all([
        getDashboardStats(days),
        getAgentDashboardStats(days),
      ])
      setStats(s.data)
      setAgentStats(a.data)
    } catch (e) { console.error('Failed to load dashboard stats:', e) }
  }

  const goToTickets = (filters = {}) => {
    if (onNavigate) onNavigate('tickets', filters)
  }

  if (!stats) return (
    <div className="p-6 flex items-center gap-2" style={{ color: 'var(--text-tertiary)' }}>
      <i className="fas fa-spinner fa-spin" /> Carregando...
    </div>
  )

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Dashboard</h1>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg px-3 py-2 text-sm"
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
          }}
        >
          <option value={7}>7 dias</option>
          <option value={14}>14 dias</option>
          <option value={30}>30 dias</option>
          <option value={60}>60 dias</option>
          <option value={90}>90 dias</option>
        </select>
      </div>

      {/* View Selector */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {DASHBOARD_VIEWS.map(v => (
          <button
            key={v.id}
            onClick={() => setView(v.id)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition font-medium"
            style={{
              background: view === v.id ? 'var(--accent)' : 'var(--bg-tertiary)',
              color: view === v.id ? 'var(--accent-text)' : 'var(--text-secondary)',
              border: `1px solid ${view === v.id ? 'var(--accent)' : 'var(--border-color)'}`,
            }}
            onMouseEnter={e => { if (view !== v.id) { e.currentTarget.style.borderColor = 'var(--border-hover)'; e.currentTarget.style.color = 'var(--text-primary)' }}}
            onMouseLeave={e => { if (view !== v.id) { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.color = 'var(--text-secondary)' }}}
            title={v.desc}
          >
            <i className={`fas ${v.icon}`} />
            {v.label}
          </button>
        ))}
      </div>

      {/* View Content */}
      {view === 'admin' && <AdminDashboard stats={stats} goToTickets={goToTickets} />}
      {view === 'gestao' && <GestaoDashboard stats={stats} goToTickets={goToTickets} />}
      {view === 'agente' && <AgenteDashboard stats={stats} agentStats={agentStats} goToTickets={goToTickets} />}
      {view === 'trocas' && <TrocasDashboard stats={stats} goToTickets={goToTickets} />}
      {view === 'problemas' && <ProblemasDashboard stats={stats} goToTickets={goToTickets} />}
      {view === 'reclamacoes' && <ReclamacoesDashboard stats={stats} goToTickets={goToTickets} />}
    </div>
  )
}

// ─── Admin Dashboard ───
const SOURCE_LABELS = { email: 'E-mail', gmail: 'E-mail', web: 'Web', slack: 'Slack', whatsapp: 'WhatsApp', instagram: 'Instagram', facebook: 'Facebook', phone: 'Telefone', api: 'API' }
const SOURCE_COLORS = { web: '#6B7280', gmail: '#EF4444', email: '#EF4444', slack: '#8B5CF6', whatsapp: '#22C55E', instagram: '#EC4899', facebook: '#3B82F6' }

function AdminDashboard({ stats, goToTickets }) {
  const cs = useChartStyles()
  const categoryData = Object.entries(stats.by_category || {}).map(([name, value]) => ({ name: CATEGORY_LABELS[name] || name, value, key: name }))
  const statusData = Object.entries(stats.by_status || {}).map(([name, value]) => ({ name: STATUS_LABELS[name] || name, value, key: name }))
  const priorityData = Object.entries(stats.by_priority || {}).map(([name, value]) => ({ name: PRIORITY_LABELS[name] || name, value, key: name }))
  const sourceData = Object.entries(stats.by_source || {}).map(([name, value]) => ({ name: SOURCE_LABELS[name] || name, value }))
  const sentimentData = Object.entries(stats.by_sentiment || {}).map(([name, value]) => ({ name: SENTIMENT_LABELS[name] || name, value }))

  return (
    <>
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        <KPICard label="Total Tickets" value={stats.total_tickets} icon="fa-ticket" color="accent" onClick={() => goToTickets({})} />
        <KPICard label="Abertos" value={stats.open_tickets} icon="fa-folder-open" color="blue" onClick={() => goToTickets({ status: 'open' })} />
        <KPICard label="SLA Cumprido" value={`${stats.sla_compliance}%`} icon="fa-clock" color="green" onClick={() => goToTickets({ sla_breached: 'true' })} />
        <KPICard label="Trocas" value={stats.trocas_count} icon="fa-rotate" color="yellow" onClick={() => goToTickets({ category: 'troca' })} />
        <KPICard label="Problemas" value={stats.problemas_count} icon="fa-triangle-exclamation" color="orange" onClick={() => goToTickets({ category: 'garantia' })} />
        <KPICard label="Risco Jurídico" value={stats.legal_risk_count} icon="fa-gavel" color="red" onClick={() => goToTickets({ legal_risk: 'true' })} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        <KPICard label="Reclamações" value={stats.reclamacoes_count} icon="fa-face-angry" color="red" onClick={() => goToTickets({ category: 'reclamacao' })} />
        <KPICard label="Escalados" value={stats.escalated_count} icon="fa-arrow-up" color="red" onClick={() => goToTickets({ status: 'escalated' })} />
        <KPICard label="Tempo Resposta" value={`${stats.avg_response_hours}h`} icon="fa-reply" color="blue" />
        <KPICard label="FCR" value={`${stats.fcr_rate || 0}%`} icon="fa-bullseye" color="green" />
        <KPICard label="Não Atribuídos" value={stats.unassigned_count || 0} icon="fa-user-slash" color="orange" onClick={() => goToTickets({ assigned_to: 'none' })} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KPICard label="Resolvidos Hoje" value={stats.resolved_today} icon="fa-check-circle" color="green" onClick={() => goToTickets({ status: 'resolved' })} />
        <KPICard label="Tempo Resolução" value={`${stats.avg_resolution_hours}h`} icon="fa-check-double" color="purple" />
        <KPICard label="SLA Quebrados" value={stats.sla_breached} icon="fa-exclamation-triangle" color="red" onClick={() => goToTickets({ sla_breached: 'true' })} />
        <KPICard label="Resolv. 1ª Resp" value={stats.fcr_count || 0} icon="fa-bullseye" color="green" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ChartCard title="Volume Diário">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stats.daily_volume}>
              <CartesianGrid strokeDasharray="3 3" stroke={cs.grid} />
              <XAxis dataKey="date" tick={{ fill: cs.axisTick, fontSize: 10 }} />
              <YAxis tick={{ fill: cs.axisTick, fontSize: 11 }} />
              <Tooltip contentStyle={cs.tooltip} />
              <Bar dataKey="count" name="Tickets" fill="#fdd200" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Por Categoria">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={categoryData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={{ fill: cs.pieLabel, fontSize: 11 }}>
                {categoryData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={cs.tooltip} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Por Status">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={statusData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke={cs.grid} />
              <XAxis type="number" tick={{ fill: cs.axisTick, fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: cs.axisLabel, fontSize: 11 }} width={110} />
              <Tooltip contentStyle={cs.tooltip} />
              <Bar dataKey="value" name="Qtd" fill="#fdd200" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Por Prioridade">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={priorityData}>
              <CartesianGrid strokeDasharray="3 3" stroke={cs.grid} />
              <XAxis dataKey="name" tick={{ fill: cs.axisTick, fontSize: 11 }} />
              <YAxis tick={{ fill: cs.axisTick, fontSize: 11 }} />
              <Tooltip contentStyle={cs.tooltip} />
              <Bar dataKey="value" name="Qtd" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Por Canal">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={sourceData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={{ fill: cs.pieLabel, fontSize: 11 }}>
                {sourceData.map((_, i) => <Cell key={i} fill={['#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#14b8a6'][i] || COLORS[i]} />)}
              </Pie>
              <Tooltip contentStyle={cs.tooltip} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Sentimento">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={sentimentData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={{ fill: cs.pieLabel, fontSize: 11 }}>
                {sentimentData.map((_, i) => <Cell key={i} fill={['#10b981', '#fdd200', '#f59e0b', '#ef4444'][i] || COLORS[i]} />)}
              </Pie>
              <Tooltip contentStyle={cs.tooltip} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Quick Access */}
      <h3 className="font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Acesso Rápido por Categoria</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {Object.entries(stats.by_category || {}).map(([cat, count]) => (
          <button key={cat} onClick={() => goToTickets({ category: cat })}
            className="rounded-xl p-4 text-left transition group border"
            style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border-hover)'; e.currentTarget.style.boxShadow = 'var(--shadow-sm)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.boxShadow = 'none' }}>
            <p className="text-xs mb-1" style={{ color: 'var(--text-tertiary)' }}>{CATEGORY_LABELS[cat] || cat}</p>
            <p className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{count}</p>
            <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>clique para ver <i className="fas fa-arrow-right text-[10px]" /></p>
          </button>
        ))}
      </div>
    </>
  )
}

// ─── Gestão Dashboard ───
function GestaoDashboard({ stats, goToTickets }) {
  const cs = useChartStyles()
  const sentimentData = Object.entries(stats.by_sentiment || {}).map(([name, value]) => ({ name: SENTIMENT_LABELS[name] || name, value }))

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KPICard label="Total Tickets" value={stats.total_tickets} icon="fa-ticket" color="accent" onClick={() => goToTickets({})} />
        <KPICard label="SLA Cumprido" value={`${stats.sla_compliance}%`} icon="fa-clock" color="green" />
        <KPICard label="Tempo Médio Resposta" value={`${stats.avg_response_hours}h`} icon="fa-reply" color="blue" />
        <KPICard label="Tempo Médio Resolução" value={`${stats.avg_resolution_hours}h`} icon="fa-check-double" color="purple" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <KPICard label="Abertos" value={stats.open_tickets} icon="fa-folder-open" color="blue" onClick={() => goToTickets({ status: 'open' })} />
        <KPICard label="Escalados" value={stats.escalated_count} icon="fa-arrow-up" color="red" onClick={() => goToTickets({ status: 'escalated' })} />
        <KPICard label="Risco Jurídico" value={stats.legal_risk_count} icon="fa-gavel" color="red" onClick={() => goToTickets({ legal_risk: 'true' })} />
        <KPICard label="FCR" value={`${stats.fcr_rate || 0}%`} icon="fa-bullseye" color="green" />
        <KPICard label="Resolvidos Hoje" value={stats.resolved_today} icon="fa-check-circle" color="green" onClick={() => goToTickets({ status: 'resolved' })} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ChartCard title="Volume Diário">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={stats.daily_volume}>
              <CartesianGrid strokeDasharray="3 3" stroke={cs.grid} />
              <XAxis dataKey="date" tick={{ fill: cs.axisTick, fontSize: 10 }} />
              <YAxis tick={{ fill: cs.axisTick, fontSize: 11 }} />
              <Tooltip contentStyle={cs.tooltip} />
              <Line type="monotone" dataKey="count" stroke="#fdd200" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Sentimento dos Clientes">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={sentimentData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={{ fill: cs.pieLabel, fontSize: 11 }}>
                {sentimentData.map((_, i) => <Cell key={i} fill={['#10b981', '#fdd200', '#f59e0b', '#ef4444'][i] || COLORS[i]} />)}
              </Pie>
              <Tooltip contentStyle={cs.tooltip} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <h3 className="font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Resumo por Tipo</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <CategoryCard label="Trocas" count={stats.trocas_count} icon="fa-rotate" color="#f59e0b" onClick={() => goToTickets({ category: 'troca' })} />
        <CategoryCard label="Problemas Técnicos" count={stats.problemas_count} icon="fa-triangle-exclamation" color="#f97316" onClick={() => goToTickets({ category: 'garantia' })} />
        <CategoryCard label="Reclamações" count={stats.reclamacoes_count} icon="fa-face-angry" color="#ef4444" onClick={() => goToTickets({ category: 'reclamacao' })} />
      </div>
    </>
  )
}

// ─── Agente Dashboard ───
function AgenteDashboard({ stats, agentStats, goToTickets }) {
  const cs = useChartStyles()
  if (!agentStats) return <div style={{ color: 'var(--text-tertiary)' }}>Carregando dados do agente...</div>

  const myStatusData = Object.entries(agentStats.my_by_status || {}).map(([name, value]) => ({ name: STATUS_LABELS[name] || name, value }))
  const myCatData = Object.entries(agentStats.my_by_category || {}).map(([name, value]) => ({ name: CATEGORY_LABELS[name] || name, value }))

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KPICard label="Meus Abertos" value={agentStats.my_open} icon="fa-folder-open" color="blue" onClick={() => goToTickets({ assigned_to: 'me', status: 'open' })} />
        <KPICard label="Meus Resolvidos" value={agentStats.my_resolved} icon="fa-check-circle" color="green" onClick={() => goToTickets({ assigned_to: 'me', status: 'resolved' })} />
        <KPICard label="Meu Tempo Resposta" value={`${agentStats.my_avg_response_hours}h`} icon="fa-reply" color="blue" />
        <KPICard label="Meu SLA" value={`${agentStats.my_sla_compliance}%`} icon="fa-clock" color="green" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <KPICard label="Total Meus" value={agentStats.my_total} icon="fa-ticket" color="accent" onClick={() => goToTickets({ assigned_to: 'me' })} />
        <KPICard label="SLA Quebrados" value={agentStats.my_sla_breached} icon="fa-exclamation-triangle" color="red" onClick={() => goToTickets({ assigned_to: 'me', sla_breached: 'true' })} />
        <KPICard label="Fila Geral" value={stats.open_tickets} icon="fa-list" color="purple" onClick={() => goToTickets({ status: 'open' })} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Meus Tickets por Status">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={myStatusData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke={cs.grid} />
              <XAxis type="number" tick={{ fill: cs.axisTick, fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: cs.axisLabel, fontSize: 11 }} width={110} />
              <Tooltip contentStyle={cs.tooltip} />
              <Bar dataKey="value" name="Qtd" fill="#fdd200" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Meus Tickets por Categoria">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={myCatData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={{ fill: cs.pieLabel, fontSize: 11 }}>
                {myCatData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={cs.tooltip} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </>
  )
}

// ─── Trocas Dashboard ───
function TrocasDashboard({ stats, goToTickets }) {
  const cs = useChartStyles()
  const trocaStatuses = Object.entries(stats.by_status || {}).map(([name, value]) => ({ name: STATUS_LABELS[name] || name, value }))

  return (
    <>
      <div className="rounded-xl p-4 mb-6 border-l-4 border-yellow-500" style={{ background: 'var(--bg-secondary)' }}>
        <div className="flex items-center gap-3">
          <i className="fas fa-rotate text-yellow-400 text-2xl" />
          <div>
            <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Painel de Trocas</h2>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{stats.trocas_count} tickets de troca no período</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KPICard label="Trocas Totais" value={stats.trocas_count} icon="fa-rotate" color="yellow" onClick={() => goToTickets({ category: 'troca' })} />
        <KPICard label="Aguardando Reenvio" value={stats.by_status?.waiting_resend || 0} icon="fa-truck" color="orange" onClick={() => goToTickets({ status: 'waiting_resend' })} />
        <KPICard label="Ag. Fornecedor" value={stats.by_status?.waiting_supplier || 0} icon="fa-warehouse" color="purple" onClick={() => goToTickets({ status: 'waiting_supplier' })} />
        <KPICard label="SLA Cumprido" value={`${stats.sla_compliance}%`} icon="fa-clock" color="green" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Status dos Tickets de Troca">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trocaStatuses} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke={cs.grid} />
              <XAxis type="number" tick={{ fill: cs.axisTick, fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: cs.axisLabel, fontSize: 11 }} width={120} />
              <Tooltip contentStyle={cs.tooltip} />
              <Bar dataKey="value" name="Qtd" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Volume Diário">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={stats.daily_volume}>
              <CartesianGrid strokeDasharray="3 3" stroke={cs.grid} />
              <XAxis dataKey="date" tick={{ fill: cs.axisTick, fontSize: 10 }} />
              <YAxis tick={{ fill: cs.axisTick, fontSize: 11 }} />
              <Tooltip contentStyle={cs.tooltip} />
              <Line type="monotone" dataKey="count" stroke="#f59e0b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="mt-6">
        <button onClick={() => goToTickets({ category: 'troca' })}
          className="px-6 py-3 rounded-lg font-medium transition text-sm"
          style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--accent-hover)'}
          onMouseLeave={e => e.currentTarget.style.background = 'var(--accent)'}>
          <i className="fas fa-arrow-right mr-2" />
          Ver todos os tickets de troca
        </button>
      </div>
    </>
  )
}

// ─── Problemas Dashboard ───
function ProblemasDashboard({ stats, goToTickets }) {
  const cs = useChartStyles()
  const problemCats = ['garantia', 'mau_uso', 'suporte_tecnico', 'carregador']
  const problemData = problemCats.map(cat => ({
    name: CATEGORY_LABELS[cat] || cat,
    value: stats.by_category?.[cat] || 0,
    key: cat,
  }))

  return (
    <>
      <div className="rounded-xl p-4 mb-6 border-l-4 border-orange-500" style={{ background: 'var(--bg-secondary)' }}>
        <div className="flex items-center gap-3">
          <i className="fas fa-triangle-exclamation text-orange-400 text-2xl" />
          <div>
            <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Painel de Problemas</h2>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{stats.problemas_count} tickets de problemas técnicos no período</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KPICard label="Garantia" value={stats.by_category?.garantia || 0} icon="fa-shield" color="blue" onClick={() => goToTickets({ category: 'garantia' })} />
        <KPICard label="Mau Uso" value={stats.by_category?.mau_uso || 0} icon="fa-ban" color="red" onClick={() => goToTickets({ category: 'mau_uso' })} />
        <KPICard label="Suporte Técnico" value={stats.by_category?.suporte_tecnico || 0} icon="fa-wrench" color="accent" onClick={() => goToTickets({ category: 'suporte_tecnico' })} />
        <KPICard label="Carregador" value={stats.by_category?.carregador || 0} icon="fa-bolt" color="yellow" onClick={() => goToTickets({ category: 'carregador' })} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Distribuição de Problemas">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={problemData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={{ fill: cs.pieLabel, fontSize: 11 }}>
                {problemData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={cs.tooltip} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Volume Diário">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stats.daily_volume}>
              <CartesianGrid strokeDasharray="3 3" stroke={cs.grid} />
              <XAxis dataKey="date" tick={{ fill: cs.axisTick, fontSize: 10 }} />
              <YAxis tick={{ fill: cs.axisTick, fontSize: 11 }} />
              <Tooltip contentStyle={cs.tooltip} />
              <Bar dataKey="count" name="Tickets" fill="#f97316" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="mt-6 flex gap-3 flex-wrap">
        {problemCats.map(cat => (
          <button key={cat} onClick={() => goToTickets({ category: cat })}
            className="px-4 py-2 rounded-lg text-sm font-medium transition"
            style={{ background: 'rgba(249,115,22,0.1)', color: '#fb923c' }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(249,115,22,0.2)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(249,115,22,0.1)'}>
            <i className="fas fa-arrow-right mr-2" />
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>
    </>
  )
}

// ─── Reclamações Dashboard ───
function ReclamacoesDashboard({ stats, goToTickets }) {
  const cs = useChartStyles()
  const sentimentData = Object.entries(stats.by_sentiment || {}).map(([name, value]) => ({
    name: SENTIMENT_LABELS[name] || name, value,
  }))

  return (
    <>
      <div className="rounded-xl p-4 mb-6 border-l-4 border-red-500" style={{ background: 'var(--bg-secondary)' }}>
        <div className="flex items-center gap-3">
          <i className="fas fa-face-angry text-red-400 text-2xl" />
          <div>
            <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Painel de Reclamações</h2>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{stats.reclamacoes_count} reclamações + {stats.legal_risk_count} risco jurídico no período</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KPICard label="Reclamações" value={stats.reclamacoes_count} icon="fa-face-angry" color="red" onClick={() => goToTickets({ category: 'reclamacao' })} />
        <KPICard label="Risco Jurídico" value={stats.legal_risk_count} icon="fa-gavel" color="red" onClick={() => goToTickets({ legal_risk: 'true' })} />
        <KPICard label="Escalados" value={stats.escalated_count} icon="fa-arrow-up" color="orange" onClick={() => goToTickets({ status: 'escalated' })} />
        <KPICard label="Chargeback" value={stats.by_category?.chargeback || 0} icon="fa-credit-card" color="red" onClick={() => goToTickets({ category: 'chargeback' })} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Sentimento dos Clientes">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={sentimentData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={{ fill: cs.pieLabel, fontSize: 11 }}>
                {sentimentData.map((_, i) => <Cell key={i} fill={['#10b981', '#fdd200', '#f59e0b', '#ef4444'][i] || COLORS[i]} />)}
              </Pie>
              <Tooltip contentStyle={cs.tooltip} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Volume Diário">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={stats.daily_volume}>
              <CartesianGrid strokeDasharray="3 3" stroke={cs.grid} />
              <XAxis dataKey="date" tick={{ fill: cs.axisTick, fontSize: 10 }} />
              <YAxis tick={{ fill: cs.axisTick, fontSize: 11 }} />
              <Tooltip contentStyle={cs.tooltip} />
              <Line type="monotone" dataKey="count" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="mt-6 flex gap-3 flex-wrap">
        <button onClick={() => goToTickets({ category: 'reclamacao' })}
          className="bg-red-600 hover:bg-red-500 text-white px-6 py-3 rounded-lg font-medium transition text-sm">
          <i className="fas fa-arrow-right mr-2" /> Ver reclamações
        </button>
        <button onClick={() => goToTickets({ category: 'juridico' })}
          className="px-6 py-3 rounded-lg font-medium transition text-sm"
          style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171' }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.2)'}
          onMouseLeave={e => e.currentTarget.style.background = 'rgba(239,68,68,0.1)'}>
          <i className="fas fa-gavel mr-2" /> Ver jurídico
        </button>
        <button onClick={() => goToTickets({ category: 'chargeback' })}
          className="px-6 py-3 rounded-lg font-medium transition text-sm"
          style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171' }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.2)'}
          onMouseLeave={e => e.currentTarget.style.background = 'rgba(239,68,68,0.1)'}>
          <i className="fas fa-credit-card mr-2" /> Ver chargebacks
        </button>
      </div>
    </>
  )
}

// ─── Shared Components ───
const KPI_COLORS = {
  accent: { bg: 'rgba(253,210,0,0.1)', text: '#fdd200' },
  green: { bg: 'rgba(16,185,129,0.1)', text: '#10b981' },
  blue: { bg: 'rgba(59,130,246,0.1)', text: '#3b82f6' },
  red: { bg: 'rgba(239,68,68,0.1)', text: '#ef4444' },
  yellow: { bg: 'rgba(245,158,11,0.1)', text: '#f59e0b' },
  orange: { bg: 'rgba(249,115,22,0.1)', text: '#f97316' },
  purple: { bg: 'rgba(168,85,247,0.1)', text: '#a855f7' },
}

function KPICard({ label, value, icon, color, onClick }) {
  const c = KPI_COLORS[color] || KPI_COLORS.accent
  const Wrapper = onClick ? 'button' : 'div'

  return (
    <Wrapper
      onClick={onClick}
      className="rounded-xl p-4 text-left transition border"
      style={{
        background: 'var(--bg-secondary)',
        borderColor: 'var(--border-color)',
      }}
      onMouseEnter={e => { if (onClick) { e.currentTarget.style.borderColor = 'var(--border-hover)'; e.currentTarget.style.boxShadow = 'var(--shadow-sm)' }}}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.boxShadow = 'none' }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</span>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: c.bg, color: c.text }}>
          <i className={`fas ${icon} text-sm`} />
        </div>
      </div>
      <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{value}</p>
      {onClick && <p className="text-[10px] mt-1" style={{ color: 'var(--text-tertiary)' }}>clique para ver <i className="fas fa-arrow-right" /></p>}
    </Wrapper>
  )
}

function ChartCard({ title, children }) {
  return (
    <div className="rounded-xl p-4 border"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
      <h3 className="font-semibold mb-3 text-sm" style={{ color: 'var(--text-primary)' }}>{title}</h3>
      {children}
    </div>
  )
}

function CategoryCard({ label, count, icon, color, onClick }) {
  return (
    <button onClick={onClick}
      className="rounded-xl p-4 text-left border-l-4 transition border"
      style={{ borderLeftColor: color, background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = 'var(--shadow-sm)' }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none' }}>
      <div className="flex items-center gap-3">
        <i className={`fas ${icon} text-xl`} style={{ color }} />
        <div>
          <p className="font-bold text-xl" style={{ color: 'var(--text-primary)' }}>{count}</p>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{label}</p>
        </div>
      </div>
      <p className="text-xs mt-2" style={{ color: 'var(--text-tertiary)' }}>clique para ver tickets <i className="fas fa-arrow-right text-[10px]" /></p>
    </button>
  )
}
