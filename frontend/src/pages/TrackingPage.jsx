import React, { useState, useEffect } from 'react'
import { useToast } from '../components/Toast'
import { getTrackingList, getTrackingSummary, refreshAllTrackings, refreshSingleTracking, syncShopifyTracking } from '../services/api'

const CARRIER_LABELS = {
  correios: 'Correios', cainiao: 'Cainiao', '17track': '17Track', generic: 'Genérico', desconhecido: 'Desconhecido',
}

const CATEGORY_LABELS = {
  garantia: 'Garantia', troca: 'Troca', mau_uso: 'Mau Uso', carregador: 'Carregador',
  duvida: 'Dúvida', reclamacao: 'Reclamação', suporte_tecnico: 'Suporte Técnico',
}

const STATUS_LABELS = {
  open: 'Aberto', in_progress: 'Em Andamento', waiting: 'Aguardando',
  waiting_supplier: 'Ag. Fornecedor', waiting_resend: 'Ag. Reenvio',
  resolved: 'Resolvido', closed: 'Fechado', escalated: 'Escalado',
}

export default function TrackingPage({ onOpenTicket }) {
  const toast = useToast()
  const [items, setItems] = useState([])
  const [summary, setSummary] = useState(null)
  const [statusFilter, setStatusFilter] = useState('all')
  const [carrierFilter, setCarrierFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [syncDays, setSyncDays] = useState(30)
  const [showSyncOpts, setShowSyncOpts] = useState(false)

  useEffect(() => { loadData() }, [statusFilter, carrierFilter, page])
  useEffect(() => { loadSummary() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const { data } = await getTrackingList({
        status_filter: statusFilter,
        carrier_filter: carrierFilter,
        page,
        per_page: 30,
      })
      setItems(data.items)
      setTotalPages(data.pages)
      setTotal(data.total)
    } catch (e) { toast.error('Falha ao carregar rastreios') }
    setLoading(false)
  }

  const loadSummary = async () => {
    try {
      const { data } = await getTrackingSummary(90)
      setSummary(data)
    } catch (e) { toast.error('Falha ao carregar resumo de rastreios') }
  }

  const handleRefreshAll = async () => {
    setRefreshing(true)
    try {
      const { data } = await refreshAllTrackings()
      toast.success(`Atualizado: ${data.updated} | Erros: ${data.errors}`)
      loadData()
      loadSummary()
    } catch (e) { toast.error('Erro ao atualizar rastreios') }
    setRefreshing(false)
  }

  const handleRefreshOne = async (ticketId) => {
    try {
      await refreshSingleTracking(ticketId)
      loadData()
    } catch (e) { toast.error('Falha ao atualizar rastreio') }
  }

  const PROBLEM_KEYWORDS = ['barr', 'exce', 'devol', 'extrav', 'ausente', 'recusad', 'não encontr', 'tentativa', 'retorn', 'falh', 'sinistro', 'roub', 'avaria', 'cancel', 'bloqueado', 'fiscaliz', 'tribut', 'retido', 'apreend']

  const getDeliveryBadge = (item) => {
    const st = (item.tracking_status || '').toLowerCase()
    if (item.delivered) return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-600/20 text-green-400">Entregue</span>
    if (PROBLEM_KEYWORDS.some(k => st.includes(k)))
      return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-600/20 text-red-400"><i className="fas fa-exclamation-triangle mr-1" />Problema</span>
    if (st.includes('erro')) return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-600/20 text-red-400">Erro</span>
    if (st.includes('aguardando') || !st || st === 'sem atualização')
      return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-600/20 text-yellow-400">Pendente</span>
    return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-600/20 text-blue-400">Em Trânsito</span>
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold text-white">Rastreamento de Pacotes</h1>
          <p className="text-carbon-400 text-sm mt-1">{total} pacotes com código de rastreio</p>
        </div>
        <div className="flex gap-2 items-center">
          <div className="relative">
            <div className="flex">
              <button
                onClick={async () => {
                  setSyncing(true)
                  try {
                    const { data } = await syncShopifyTracking(syncDays)
                    toast.success(`Sincronizado: ${data.synced} | Sem rastreio: ${data.no_tracking} | Erros: ${data.errors}`)
                    loadData()
                    loadSummary()
                  } catch (e) { toast.error('Erro ao sincronizar com Shopify') }
                  setSyncing(false)
                  setShowSyncOpts(false)
                }}
                disabled={syncing}
                className="bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white px-4 py-2 rounded-l-lg text-sm font-medium transition flex items-center gap-2"
              >
                <i className={`fab fa-shopify ${syncing ? 'animate-pulse' : ''}`} />
                {syncing ? 'Sincronizando...' : 'Sync Shopify'}
              </button>
              <button
                onClick={() => setShowSyncOpts(!showSyncOpts)}
                className="bg-green-700 hover:bg-green-600 text-white px-2 py-2 rounded-r-lg text-sm border-l border-green-500/50"
              >
                <i className="fas fa-chevron-down text-xs" />
              </button>
            </div>
            {showSyncOpts && (
              <div className="absolute right-0 top-full mt-1 bg-carbon-700 border border-carbon-600 rounded-lg shadow-xl z-20 p-3 min-w-[200px]">
                <p className="text-carbon-400 text-xs mb-2">Período dos tickets:</p>
                {[7, 15, 30, 60, 90, 180].map(d => (
                  <button key={d}
                    onClick={() => { setSyncDays(d); setShowSyncOpts(false) }}
                    className={`block w-full text-left px-3 py-1.5 text-sm rounded transition ${syncDays === d ? 'bg-green-600/30 text-green-400' : 'text-carbon-300 hover:bg-carbon-600'}`}>
                    Últimos {d} dias
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={handleRefreshAll}
            disabled={refreshing}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2"
          >
            <i className={`fas fa-sync-alt ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Atualizando...' : 'Atualizar Todos'}
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
          <SummaryCard label="Total Rastreios" value={summary.total} icon="fa-box" color="indigo" onClick={() => { setStatusFilter('all'); setPage(1) }} />
          <SummaryCard label="Entregues" value={summary.delivered} icon="fa-check-circle" color="green" onClick={() => { setStatusFilter('delivered'); setPage(1) }} />
          <SummaryCard label="Em Trânsito" value={summary.in_transit} icon="fa-truck" color="blue" onClick={() => { setStatusFilter('in_transit'); setPage(1) }} />
          <SummaryCard label="Pendentes" value={summary.pending} icon="fa-clock" color="yellow" onClick={() => { setStatusFilter('pending'); setPage(1) }} />
          <SummaryCard label="Problemas" value={summary.problems || 0} icon="fa-exclamation-triangle" color="red" onClick={() => { setStatusFilter('problem'); setPage(1) }} />
          <SummaryCard label="Taxa Entrega" value={`${summary.delivery_rate}%`} icon="fa-chart-line" color="green" />
        </div>
      )}

      {/* Carrier breakdown */}
      {summary?.by_carrier && Object.keys(summary.by_carrier).length > 0 && (
        <div className="bg-carbon-700 rounded-xl p-4 mb-6">
          <h3 className="text-white text-sm font-semibold mb-3">Por Transportadora</h3>
          <div className="flex gap-4 flex-wrap">
            {Object.entries(summary.by_carrier).map(([carrier, count]) => (
              <div key={carrier} className="flex items-center gap-2">
                <span className="text-carbon-400 text-sm">{CARRIER_LABELS[carrier] || carrier}:</span>
                <span className="text-white font-bold">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="bg-carbon-700 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm">
          <option value="all">Todos os Status</option>
          <option value="pending">Pendentes</option>
          <option value="in_transit">Em Trânsito</option>
          <option value="delivered">Entregues</option>
          <option value="problem">Problemas (Barrados/Exceção/Devolvido)</option>
          <option value="error">Com Erro</option>
        </select>

        <select value={carrierFilter} onChange={(e) => { setCarrierFilter(e.target.value); setPage(1) }}
          className="bg-carbon-700 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm">
          <option value="all">Todas Transportadoras</option>
          <option value="correios">Correios</option>
          <option value="cainiao">Cainiao</option>
          <option value="17track">17Track</option>
          <option value="generic">Genérico</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-carbon-400 py-8 text-center">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="text-carbon-400 py-8 text-center">
          <i className="fas fa-box-open text-3xl mb-3 block" />
          Nenhum rastreio encontrado
        </div>
      ) : (
        <div className="bg-carbon-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-carbon-600">
                <th className="text-left text-carbon-400 font-medium px-4 py-3">Ticket</th>
                <th className="text-left text-carbon-400 font-medium px-4 py-3">Cliente</th>
                <th className="text-left text-carbon-400 font-medium px-4 py-3">Código</th>
                <th className="text-left text-carbon-400 font-medium px-4 py-3">Transportadora</th>
                <th className="text-left text-carbon-400 font-medium px-4 py-3">Status Rastreio</th>
                <th className="text-left text-carbon-400 font-medium px-4 py-3">Entrega</th>
                <th className="text-center text-carbon-400 font-medium px-4 py-3">Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <React.Fragment key={item.ticket_id}>
                  <tr className="border-b border-carbon-600/50 hover:bg-carbon-600/30 transition cursor-pointer"
                    onClick={() => setExpandedId(expandedId === item.ticket_id ? null : item.ticket_id)}>
                    <td className="px-4 py-3">
                      <button onClick={(e) => { e.stopPropagation(); onOpenTicket && onOpenTicket(item.ticket_id) }}
                        className="text-indigo-400 hover:text-indigo-300 font-medium">
                        #{item.ticket_number}
                      </button>
                      <p className="text-carbon-400 text-xs truncate max-w-[150px]">{item.subject}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-white text-sm">{item.customer_name}</p>
                      <p className="text-carbon-500 text-xs">{item.customer_email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-green-400 font-mono text-xs bg-carbon-800 px-2 py-1 rounded">
                        {item.tracking_code}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-carbon-300 text-sm">{CARRIER_LABELS[item.carrier] || item.carrier}</span>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-white text-xs">{item.tracking_status}</p>
                      {item.last_event && (
                        <p className="text-carbon-500 text-xs mt-0.5">{item.last_event.location} — {item.last_event.date}</p>
                      )}
                    </td>
                    <td className="px-4 py-3">{getDeliveryBadge(item)}</td>
                    <td className="px-4 py-3 text-center flex items-center gap-2 justify-center">
                      <button onClick={(e) => { e.stopPropagation(); onOpenTicket && onOpenTicket(item.ticket_id) }}
                        className="text-carbon-400 hover:text-indigo-400 transition" title="Abrir ticket">
                        <i className="fas fa-external-link-alt" />
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); handleRefreshOne(item.ticket_id) }}
                        className="text-carbon-400 hover:text-indigo-400 transition" title="Atualizar rastreio">
                        <i className="fas fa-sync-alt" />
                      </button>
                    </td>
                  </tr>

                  {/* Expanded detail panel */}
                  {expandedId === item.ticket_id && (
                    <tr>
                      <td colSpan={7} className="px-4 py-4 bg-carbon-800/50">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Info do pacote */}
                          <div className="space-y-3">
                            <div className="flex items-center gap-2 mb-2">
                              <h4 className="text-white text-sm font-semibold">Detalhes do Pacote</h4>
                              <button onClick={(e) => { e.stopPropagation(); onOpenTicket && onOpenTicket(item.ticket_id) }}
                                className="text-indigo-400 hover:text-indigo-300 text-xs font-medium ml-auto">
                                <i className="fas fa-external-link-alt mr-1" />Abrir Ticket
                              </button>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div className="bg-carbon-700 rounded-lg p-2">
                                <span className="text-carbon-400 block">Código</span>
                                <span className="text-green-400 font-mono">{item.tracking_code}</span>
                              </div>
                              <div className="bg-carbon-700 rounded-lg p-2">
                                <span className="text-carbon-400 block">Transportadora</span>
                                <span className="text-white">{CARRIER_LABELS[item.carrier] || item.carrier}</span>
                              </div>
                              <div className="bg-carbon-700 rounded-lg p-2">
                                <span className="text-carbon-400 block">Status Ticket</span>
                                <span className="text-white">{STATUS_LABELS[item.status] || item.status}</span>
                              </div>
                              <div className="bg-carbon-700 rounded-lg p-2">
                                <span className="text-carbon-400 block">Categoria</span>
                                <span className="text-white">{CATEGORY_LABELS[item.category] || item.category || '—'}</span>
                              </div>
                              {item.tracking_data?.days_in_transit && (
                                <div className="bg-carbon-700 rounded-lg p-2">
                                  <span className="text-carbon-400 block">Dias em trânsito</span>
                                  <span className="text-white">{item.tracking_data.days_in_transit} dias</span>
                                </div>
                              )}
                              {item.tracking_data?.location && (
                                <div className="bg-carbon-700 rounded-lg p-2">
                                  <span className="text-carbon-400 block">Última localização</span>
                                  <span className="text-white">{item.tracking_data.location}</span>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Timeline de eventos */}
                          <div>
                            <h4 className="text-white text-sm font-semibold mb-2">
                              <i className="fas fa-route mr-1 text-indigo-400" />Movimentação
                              {item.tracking_data?.events?.length > 0 && <span className="text-carbon-400 font-normal ml-1">({item.tracking_data.events.length})</span>}
                            </h4>
                            {item.tracking_data?.events?.length > 0 ? (
                              <div className="space-y-0 max-h-52 overflow-auto pr-1">
                                {item.tracking_data.events.map((ev, i) => {
                                  const isFirst = i === 0
                                  const isDelivered = (ev.status || '').toLowerCase().includes('entreg')
                                  return (
                                    <div key={i} className="flex gap-3">
                                      <div className="flex flex-col items-center">
                                        <div className={`w-2.5 h-2.5 rounded-full shrink-0 mt-1.5 ${isDelivered ? 'bg-emerald-400' : isFirst ? 'bg-blue-400' : 'bg-carbon-600'}`} />
                                        {i < item.tracking_data.events.length - 1 && <div className="w-px flex-1 bg-carbon-600 my-0.5" />}
                                      </div>
                                      <div className={`pb-3 ${isFirst ? '' : 'opacity-70'}`}>
                                        <p className={`text-xs font-medium ${isFirst ? 'text-white' : 'text-carbon-300'}`}>{ev.status}</p>
                                        <p className="text-carbon-500 text-xs">{ev.location}{ev.date ? ` — ${ev.date}` : ''}</p>
                                      </div>
                                    </div>
                                  )
                                })}
                              </div>
                            ) : (
                              <p className="text-carbon-500 text-xs">Nenhum evento registrado</p>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-3 py-1 rounded bg-carbon-700 text-carbon-300 hover:bg-carbon-600 disabled:opacity-30 text-sm">
            <i className="fas fa-chevron-left" />
          </button>
          <span className="text-carbon-400 text-sm">Página {page} de {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="px-3 py-1 rounded bg-carbon-700 text-carbon-300 hover:bg-carbon-600 disabled:opacity-30 text-sm">
            <i className="fas fa-chevron-right" />
          </button>
        </div>
      )}
    </div>
  )
}

function SummaryCard({ label, value, icon, color, onClick }) {
  const colorMap = {
    indigo: 'bg-indigo-600/20 text-indigo-400',
    green: 'bg-green-600/20 text-green-400',
    blue: 'bg-blue-600/20 text-blue-400',
    yellow: 'bg-yellow-600/20 text-yellow-400',
    red: 'bg-red-600/20 text-red-400',
  }

  return (
    <div className={`bg-carbon-700 rounded-xl p-4 ${onClick ? 'cursor-pointer hover:bg-carbon-600 transition' : ''}`} onClick={onClick}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-carbon-400 text-xs">{label}</span>
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${colorMap[color]}`}>
          <i className={`fas ${icon} text-xs`} />
        </div>
      </div>
      <p className="text-xl font-bold text-white">{value}</p>
    </div>
  )
}
