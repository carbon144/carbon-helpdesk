import React, { useState, useEffect } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import api from '../services/api'

function useChartStyles() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  return {
    tooltip: {
      background: isDark ? '#1a1a1f' : '#ffffff',
      border: `1px solid ${isDark ? '#3a3a42' : '#dee2e6'}`,
      color: isDark ? '#fafafa' : '#1a1a2e',
      borderRadius: '8px',
    },
    grid: isDark ? '#2a2a32' : '#e9ecef',
    axisTick: isDark ? '#71717a' : '#868e96',
  }
}

const CARDS_CONFIG = [
  { key: 'tickets_hoje', label: 'Tickets Hoje', icon: 'fa-inbox', color: '#3B82F6' },
  { key: 'resolvidos_hoje', label: 'Resolvidos Hoje', icon: 'fa-check-circle', color: '#10B981' },
  { key: 'sem_resposta', label: 'Sem Resposta', icon: 'fa-clock', color: '#EF4444' },
  { key: 'tempo_medio_resposta_h', label: 'Tempo Medio Resposta', icon: 'fa-stopwatch', color: '#F59E0B', suffix: 'h' },
  { key: 'auto_replies_hoje', label: 'Auto-Replies Hoje', icon: 'fa-robot', color: '#8B5CF6' },
]

export default function MetricasPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const chart = useChartStyles()

  useEffect(() => {
    api.get('/dashboard/metricas')
      .then(res => setData(res.data))
      .catch(err => console.error('Erro ao carregar metricas:', err))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-t-transparent rounded-full" style={{ borderColor: '#E5A800', borderTopColor: 'transparent' }} />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="p-6">
        <p style={{ color: 'var(--text-secondary)' }}>Erro ao carregar metricas.</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Metricas</h1>

      {/* Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {CARDS_CONFIG.map(card => (
          <div key={card.key} className="rounded-xl p-4" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: card.color + '20', color: card.color }}>
                <i className={`fas ${card.icon} text-sm`} />
              </div>
            </div>
            <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              {data.cards[card.key]}{card.suffix || ''}
            </p>
            <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>{card.label}</p>
          </div>
        ))}
      </div>

      {/* Tabela Agentes */}
      <div className="rounded-xl overflow-hidden" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
        <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border-primary)' }}>
          <h2 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Equipe</h2>
        </div>
        <table className="w-full">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-primary)' }}>
              {['Agente', 'Abertos', 'Resolvidos Hoje', 'Resolvidos Semana', 'Tempo Medio'].map(h => (
                <th key={h} className="text-left text-xs font-semibold px-4 py-2.5" style={{ color: 'var(--text-tertiary)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.agentes.map((ag, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--border-primary)' }}>
                <td className="px-4 py-2.5 text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{ag.nome}</td>
                <td className="px-4 py-2.5 text-sm" style={{ color: 'var(--text-secondary)' }}>{ag.abertos}</td>
                <td className="px-4 py-2.5 text-sm font-semibold" style={{ color: '#10B981' }}>{ag.resolvidos_hoje}</td>
                <td className="px-4 py-2.5 text-sm" style={{ color: 'var(--text-secondary)' }}>{ag.resolvidos_semana}</td>
                <td className="px-4 py-2.5 text-sm" style={{ color: 'var(--text-secondary)' }}>{ag.tempo_medio_h}h</td>
              </tr>
            ))}
            {data.agentes.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-sm" style={{ color: 'var(--text-tertiary)' }}>Nenhum agente encontrado</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Grafico Volume Diario */}
      <div className="rounded-xl p-4" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
        <h2 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>Volume Diario (30 dias)</h2>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data.volume_diario}>
            <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} />
            <XAxis
              dataKey="data"
              tick={{ fill: chart.axisTick, fontSize: 11 }}
              tickFormatter={v => { const d = new Date(v + 'T12:00:00'); return `${d.getDate()}/${d.getMonth() + 1}` }}
            />
            <YAxis tick={{ fill: chart.axisTick, fontSize: 11 }} />
            <Tooltip contentStyle={chart.tooltip} />
            <Legend />
            <Bar dataKey="criados" name="Criados" fill="#3B82F6" radius={[3, 3, 0, 0]} />
            <Bar dataKey="resolvidos" name="Resolvidos" fill="#10B981" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
