import React, { useState, useEffect, useRef } from 'react'
import { useToast } from '../components/Toast'
import api from '../services/api'

const STATUS_COLORS = {
  online: { bg: 'rgba(16,185,129,0.12)', color: '#10B981', label: 'Online' },
  offline: { bg: 'rgba(100,116,139,0.12)', color: '#64748B', label: 'Offline' },
}

const ALERT_STYLES = {
  warning: { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.25)', color: '#F59E0B', icon: 'fa-exclamation-triangle' },
  critical: { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.25)', color: '#EF4444', icon: 'fa-circle-exclamation' },
}

export default function LeaderDashboardPage() {
  const toast = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const intervalRef = useRef(null)

  const load = async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const res = await api.get('/dashboard/leader')
      setData(res.data)
    } catch { toast.error('Erro ao carregar painel') }
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
    intervalRef.current = setInterval(() => {
      if (document.visibilityState === 'visible') load(true)
    }, 30_000)
    return () => clearInterval(intervalRef.current)
  }, [])

  if (loading && !data) return (
    <div className="p-6 flex items-center justify-center h-full">
      <i className="fas fa-spinner animate-spin text-2xl" style={{ color: '#64748B' }} />
    </div>
  )

  if (!data) return null

  const { agents, online_count, total_agents, alerts, ai_replies_today, unassigned_count } = data

  return (
    <div className="p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Painel do Lider</h1>
          <p className="text-sm mt-1" style={{ color: '#64748B' }}>
            Acompanhe a equipe em tempo real
          </p>
        </div>
        <button onClick={() => load()}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition cursor-pointer hover:bg-white/10"
          style={{ background: 'rgba(255,255,255,0.05)', color: '#94A3B8', border: '1px solid rgba(255,255,255,0.08)' }}>
          <i className={`fas fa-sync-alt text-xs ${loading ? 'animate-spin' : ''}`} /> Atualizar
        </button>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2 mb-6">
          {alerts.map((alert, i) => {
            const s = ALERT_STYLES[alert.type] || ALERT_STYLES.warning
            return (
              <div key={i} className="flex items-center gap-3 px-4 py-3 rounded-xl"
                style={{ background: s.bg, border: `1px solid ${s.border}` }}>
                <i className={`fas ${s.icon} text-sm`} style={{ color: s.color }} />
                <span className="text-sm font-medium" style={{ color: s.color }}>{alert.message}</span>
              </div>
            )
          })}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <KpiCard icon="fa-users" label="Agentes Online" value={`${online_count}/${total_agents}`}
          color={online_count > 0 ? '#10B981' : '#EF4444'} />
        <KpiCard icon="fa-inbox" label="Sem Agente" value={unassigned_count}
          color={unassigned_count > 5 ? '#F59E0B' : '#3B82F6'} />
        <KpiCard icon="fa-robot" label="Auto-replies IA Hoje" value={ai_replies_today} color="#8B5CF6" />
        <KpiCard icon="fa-check-double" label="Resolvidos Hoje (total)"
          value={agents.reduce((s, a) => s + a.resolved_today, 0)} color="#E5A800" />
      </div>

      {/* Agents Table */}
      <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="px-5 py-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
          <h2 className="text-base font-bold text-white">Equipe</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <Th>Agente</Th>
                <Th align="center">Status</Th>
                <Th align="center">Abertos</Th>
                <Th align="center">Resolvidos Hoje</Th>
                <Th align="center">Resolvidos Semana</Th>
                <Th align="center">Tempo Resp. (7d)</Th>
              </tr>
            </thead>
            <tbody>
              {agents.map(agent => (
                <tr key={agent.id} className="hover:bg-white/[0.02] transition"
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="relative shrink-0">
                        <div className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold"
                          style={{ background: 'linear-gradient(135deg, #E5A800 0%, #CC9600 100%)', color: '#fff' }}>
                          {agent.name?.[0] || '?'}
                        </div>
                        <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2"
                          style={{ background: agent.is_online ? '#10B981' : '#475569', borderColor: 'var(--bg-secondary)' }} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-white">{agent.name}</p>
                        <p className="text-[10px]" style={{ color: '#64748B' }}>{agent.role}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-center">
                    <StatusBadge online={agent.is_online} />
                  </td>
                  <td className="px-5 py-3.5 text-center">
                    <span className="text-sm font-semibold" style={{ color: agent.open_tickets > 10 ? '#F59E0B' : '#E2E8F0' }}>
                      {agent.open_tickets}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-center">
                    <span className="text-sm font-semibold" style={{ color: '#E2E8F0' }}>{agent.resolved_today}</span>
                  </td>
                  <td className="px-5 py-3.5 text-center">
                    <span className="text-sm font-semibold" style={{ color: '#E2E8F0' }}>{agent.resolved_week}</span>
                  </td>
                  <td className="px-5 py-3.5 text-center">
                    <span className="text-sm font-medium" style={{ color: agent.avg_response_hours > 4 ? '#F59E0B' : '#94A3B8' }}>
                      {agent.avg_response_hours > 0 ? `${agent.avg_response_hours}h` : '-'}
                    </span>
                  </td>
                </tr>
              ))}
              {agents.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-sm" style={{ color: '#64748B' }}>
                    Nenhum agente encontrado
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function KpiCard({ icon, label, value, color }) {
  return (
    <div className="rounded-xl p-4" style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.06)' }}>
      <div className="flex items-center gap-3 mb-2">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{ background: `${color}18` }}>
          <i className={`fas ${icon} text-sm`} style={{ color }} />
        </div>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-[11px] mt-0.5" style={{ color: '#64748B' }}>{label}</p>
    </div>
  )
}

function StatusBadge({ online }) {
  const s = online ? STATUS_COLORS.online : STATUS_COLORS.offline
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full"
      style={{ background: s.bg, color: s.color }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.color }} />
      {s.label}
    </span>
  )
}

function Th({ children, align = 'left' }) {
  return (
    <th className={`px-5 py-3 text-[11px] font-bold uppercase tracking-wider text-${align}`}
      style={{ color: '#64748B' }}>
      {children}
    </th>
  )
}
