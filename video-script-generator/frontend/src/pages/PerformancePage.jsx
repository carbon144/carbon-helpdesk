import React, { useState, useEffect } from 'react'
import { BarChart3, TrendingUp, DollarSign, Eye, MousePointer, ShoppingCart, RefreshCw, Loader2, Trophy } from 'lucide-react'
import { getPerformanceStats, syncAllPerformance, listScripts } from '../services/api'

export default function PerformancePage() {
  const [stats, setStats] = useState(null)
  const [topScripts, setTopScripts] = useState([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [statsRes, scriptsRes] = await Promise.all([
        getPerformanceStats(),
        listScripts({ has_ad: true, sort: '-roas', limit: 10 }),
      ])
      setStats(statsRes.data)
      setTopScripts(scriptsRes.data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleSyncAll = async () => {
    setSyncing(true)
    try {
      await syncAllPerformance()
      await load()
    } catch {}
    setSyncing(false)
  }

  if (loading) {
    return (
      <div className="text-center py-20 text-gray-500">
        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
        Carregando performance...
      </div>
    )
  }

  const cards = [
    { label: 'Total Roteiros', value: stats?.total_scripts || 0, icon: BarChart3, color: 'bg-blue-100 text-blue-600' },
    { label: 'Com Ads Vinculados', value: stats?.scripts_with_ads || 0, icon: MousePointer, color: 'bg-green-100 text-green-600' },
    { label: 'ROAS Medio', value: stats?.avg_roas ? `${stats.avg_roas.toFixed(2)}x` : '-', icon: TrendingUp, color: 'bg-purple-100 text-purple-600' },
    { label: 'CTR Medio', value: stats?.avg_ctr ? `${stats.avg_ctr.toFixed(2)}%` : '-', icon: MousePointer, color: 'bg-yellow-100 text-yellow-600' },
    { label: 'Gasto Total', value: stats?.total_spend ? `R$${stats.total_spend.toFixed(0)}` : '-', icon: DollarSign, color: 'bg-red-100 text-red-600' },
    { label: 'Conversoes', value: stats?.total_conversions || '-', icon: ShoppingCart, color: 'bg-carbon-100 text-carbon-600' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Performance dos Roteiros</h2>
          <p className="text-sm text-gray-500">Metricas dos roteiros vinculados a Meta Ads</p>
        </div>
        <button
          onClick={handleSyncAll}
          disabled={syncing}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-carbon-500 text-white text-sm font-medium hover:bg-carbon-600 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? 'Sincronizando...' : 'Sincronizar Tudo'}
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {cards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center mb-3`}>
              <Icon className="w-4 h-4" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Best Script */}
      {stats?.best_script_title && (
        <div className="bg-gradient-to-r from-carbon-500 to-carbon-600 rounded-xl p-5 text-white">
          <div className="flex items-center gap-2 mb-1">
            <Trophy className="w-5 h-5" />
            <span className="font-semibold">Melhor Roteiro</span>
          </div>
          <p className="text-xl font-bold">{stats.best_script_title}</p>
          <p className="text-carbon-100 text-sm mt-1">ROAS: {stats.best_roas?.toFixed(2)}x</p>
        </div>
      )}

      {/* Top Scripts Table */}
      {topScripts.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">Ranking de Roteiros</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">#</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Roteiro</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Tipo</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">ROAS</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">CTR</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">Hook Rate</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">Gasto</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">Conversoes</th>
                </tr>
              </thead>
              <tbody>
                {topScripts.map((s, i) => (
                  <tr key={s.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        i === 0 ? 'bg-carbon-500 text-white' : i === 1 ? 'bg-gray-300 text-white' : i === 2 ? 'bg-orange-300 text-white' : 'bg-gray-100 text-gray-500'
                      }`}>{i + 1}</span>
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900">{s.title}</td>
                    <td className="px-4 py-3 text-gray-500 uppercase text-xs">{s.script_type}</td>
                    <td className="px-4 py-3 text-right font-semibold text-green-600">{s.roas ? `${s.roas.toFixed(2)}x` : '-'}</td>
                    <td className="px-4 py-3 text-right">{s.ctr ? `${s.ctr.toFixed(2)}%` : '-'}</td>
                    <td className="px-4 py-3 text-right">{s.hook_rate ? `${s.hook_rate.toFixed(1)}%` : '-'}</td>
                    <td className="px-4 py-3 text-right">{s.spend ? `R$${s.spend.toFixed(0)}` : '-'}</td>
                    <td className="px-4 py-3 text-right">{s.conversions || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {topScripts.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <BarChart3 className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Nenhum roteiro vinculado a ads ainda.</p>
          <p className="text-gray-400 text-xs mt-1">Vincule roteiros a Meta Ads no historico para ver a performance aqui.</p>
        </div>
      )}
    </div>
  )
}
