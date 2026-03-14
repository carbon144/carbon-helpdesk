import React, { useState, useEffect } from 'react'
import { Search, Filter, Star, Clock, Film, Trash2, ExternalLink, Link2, Loader2 } from 'lucide-react'
import { listScripts, deleteScript, updateScript, linkAd, syncPerformance } from '../services/api'
import ScriptResult from '../components/ScriptResult'

const TYPE_LABELS = { teleprompter: 'Teleprompter', ugc: 'UGC', founder_ad: 'Founder Ad', meta_ad: 'Meta Ad' }
const STATUS_LABELS = { draft: 'Rascunho', generating: 'Gerando', completed: 'Pronto', error: 'Erro', archived: 'Arquivado' }
const STATUS_COLORS = { draft: 'bg-gray-100 text-gray-700', generating: 'bg-yellow-100 text-yellow-700', completed: 'bg-green-100 text-green-700', error: 'bg-red-100 text-red-700', archived: 'bg-gray-100 text-gray-500' }

export default function HistoryPage() {
  const [scripts, setScripts] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState(null)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [linkingId, setLinkingId] = useState(null)
  const [adId, setAdId] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const params = { sort: '-created_at', limit: 100 }
      if (search) params.q = search
      if (typeFilter) params.script_type = typeFilter
      const { data } = await listScripts(params)
      setScripts(data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [typeFilter])

  const handleSearch = (e) => {
    e.preventDefault()
    load()
  }

  const handleDelete = async (id) => {
    if (!confirm('Deletar este roteiro?')) return
    try {
      await deleteScript(id)
      setScripts(s => s.filter(x => x.id !== id))
      if (selectedId === id) setSelectedId(null)
    } catch {}
  }

  const handleFavorite = async (id, current) => {
    try {
      await updateScript(id, { is_favorite: !current })
      setScripts(s => s.map(x => x.id === id ? { ...x, is_favorite: !current } : x))
    } catch {}
  }

  const handleLinkAd = async (scriptId) => {
    if (!adId.trim()) return
    try {
      const { data } = await linkAd(scriptId, { meta_ad_id: adId })
      setScripts(s => s.map(x => x.id === scriptId ? data : x))
      setLinkingId(null)
      setAdId('')
    } catch {}
  }

  const handleSync = async (scriptId) => {
    try {
      const { data } = await syncPerformance(scriptId)
      setScripts(s => s.map(x => x.id === scriptId ? data : x))
    } catch {}
  }

  const selected = scripts.find(s => s.id === selectedId)

  return (
    <div className="flex gap-6">
      {/* List */}
      <div className={`${selectedId ? 'w-1/3' : 'w-full'} space-y-4 transition-all`}>
        <div className="flex items-center gap-3">
          <form onSubmit={handleSearch} className="flex-1 relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar roteiros..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-carbon-500 focus:border-carbon-500 text-sm"
            />
          </form>
          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            className="px-3 py-2.5 rounded-xl border border-gray-300 text-sm"
          >
            <option value="">Todos os tipos</option>
            {Object.entries(TYPE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            Carregando...
          </div>
        ) : scripts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Film className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <p className="text-sm">Nenhum roteiro encontrado</p>
          </div>
        ) : (
          <div className="space-y-2">
            {scripts.map(s => (
              <div
                key={s.id}
                onClick={() => setSelectedId(s.id === selectedId ? null : s.id)}
                className={`bg-white rounded-xl border p-4 cursor-pointer transition-all hover:shadow-sm ${
                  selectedId === s.id ? 'border-carbon-500 shadow-sm' : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-sm text-gray-900 truncate">{s.title}</h3>
                      {s.is_favorite && <Star className="w-3.5 h-3.5 fill-carbon-500 text-carbon-500 flex-shrink-0" />}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span className={`px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[s.status] || 'bg-gray-100 text-gray-600'}`}>
                        {STATUS_LABELS[s.status] || s.status}
                      </span>
                      <span className="bg-gray-100 px-2 py-0.5 rounded-full uppercase">{s.script_type}</span>
                      <span>{s.product_name}</span>
                    </div>
                    {s.meta_ad_id && (
                      <div className="flex items-center gap-2 mt-1.5 text-xs">
                        <Link2 className="w-3 h-3 text-blue-500" />
                        <span className="text-blue-600">Ad vinculado</span>
                        {s.roas && <span className="text-green-600 font-semibold">ROAS {s.roas.toFixed(2)}x</span>}
                        {s.ctr && <span className="text-gray-500">CTR {s.ctr.toFixed(2)}%</span>}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 ml-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleFavorite(s.id, s.is_favorite) }}
                      className="p-1.5 rounded-lg hover:bg-gray-100"
                    >
                      <Star className={`w-4 h-4 ${s.is_favorite ? 'fill-carbon-500 text-carbon-500' : 'text-gray-300'}`} />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(s.id) }}
                      className="p-1.5 rounded-lg hover:bg-red-50"
                    >
                      <Trash2 className="w-4 h-4 text-gray-300 hover:text-red-500" />
                    </button>
                  </div>
                </div>

                <p className="text-xs text-gray-400 mt-2 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(s.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Detail */}
      {selected && (
        <div className="flex-1 space-y-4">
          <ScriptResult script={selected} onRefine={() => load()} generating={false} />

          {/* Link Ad */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <Link2 className="w-4 h-4" /> Vincular a Meta Ad
            </h4>
            {selected.meta_ad_id ? (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Ad ID: <code className="bg-gray-100 px-2 py-0.5 rounded">{selected.meta_ad_id}</code></span>
                <button
                  onClick={() => handleSync(selected.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-600 text-sm hover:bg-blue-100"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Sincronizar metricas
                </button>
              </div>
            ) : (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={adId}
                  onChange={e => setAdId(e.target.value)}
                  placeholder="ID do anuncio Meta (ex: 23851234567890)"
                  className="flex-1 px-3 py-2 rounded-lg border border-gray-300 text-sm"
                />
                <button
                  onClick={() => handleLinkAd(selected.id)}
                  disabled={!adId.trim()}
                  className="px-4 py-2 rounded-lg bg-carbon-500 text-white text-sm font-medium disabled:opacity-50 hover:bg-carbon-600"
                >
                  Vincular
                </button>
              </div>
            )}
          </div>

          {/* Performance */}
          {selected.meta_ad_id && selected.impressions && (
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Performance do Ad</h4>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
                {[
                  { label: 'Impressoes', value: selected.impressions?.toLocaleString() },
                  { label: 'Cliques', value: selected.clicks?.toLocaleString() },
                  { label: 'CTR', value: selected.ctr ? `${selected.ctr.toFixed(2)}%` : '-' },
                  { label: 'CPC', value: selected.cpc ? `R$${selected.cpc.toFixed(2)}` : '-' },
                  { label: 'Gasto', value: selected.spend ? `R$${selected.spend.toFixed(2)}` : '-' },
                  { label: 'ROAS', value: selected.roas ? `${selected.roas.toFixed(2)}x` : '-' },
                  { label: 'Conversoes', value: selected.conversions || '-' },
                  { label: 'Views', value: selected.video_views?.toLocaleString() || '-' },
                  { label: 'Hook Rate', value: selected.hook_rate ? `${selected.hook_rate.toFixed(1)}%` : '-' },
                  { label: 'Hold Rate', value: selected.hold_rate ? `${selected.hold_rate.toFixed(1)}%` : '-' },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-gray-50 rounded-lg p-2.5 text-center">
                    <p className="text-xs text-gray-500">{label}</p>
                    <p className="text-sm font-bold text-gray-900">{value}</p>
                  </div>
                ))}
              </div>
              {selected.performance_synced_at && (
                <p className="text-xs text-gray-400 mt-2">
                  Sincronizado em {new Date(selected.performance_synced_at).toLocaleString('pt-BR')}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
