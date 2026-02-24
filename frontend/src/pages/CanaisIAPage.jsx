import React, { useState, useEffect, useCallback } from 'react'
import { getTickets, pauseTicketAI, resumeTicketAI } from '../services/api'

const META_SOURCES = ['whatsapp', 'instagram', 'facebook']

const PLATFORM_CONFIG = {
  whatsapp: { label: 'WhatsApp', color: '#25D366', icon: 'fa-brands fa-whatsapp' },
  instagram: { label: 'Instagram', color: '#E1306C', icon: 'fa-brands fa-instagram' },
  facebook: { label: 'Facebook', color: '#1877F2', icon: 'fa-brands fa-facebook-messenger' },
}

export default function CanaisIAPage({ onOpenTicket, user }) {
  const [tickets, setTickets] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage] = useState(20)
  const [loading, setLoading] = useState(false)
  const [filterPlatform, setFilterPlatform] = useState('')
  const [filterAI, setFilterAI] = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  const loadTickets = useCallback(async () => {
    setLoading(true)
    try {
      const params = {
        source: filterPlatform || META_SOURCES.join(','),
        page,
        per_page: perPage,
        exclude_status: 'archived',
      }
      if (filterStatus) params.status = filterStatus
      const { data } = await getTickets(params)
      let filtered = data.tickets
      if (filterAI === 'active') filtered = filtered.filter(t => t.ai_auto_mode)
      if (filterAI === 'paused') filtered = filtered.filter(t => !t.ai_auto_mode)
      setTickets(filtered)
      setTotal(data.total)
    } catch (e) {
      console.error('Failed to load canais IA tickets', e)
    } finally {
      setLoading(false)
    }
  }, [page, perPage, filterPlatform, filterAI, filterStatus])

  useEffect(() => { loadTickets() }, [loadTickets])

  const stats = {
    total: total,
    whatsapp: tickets.filter(t => t.source === 'whatsapp').length,
    instagram: tickets.filter(t => t.source === 'instagram').length,
    facebook: tickets.filter(t => t.source === 'facebook').length,
    aiActive: tickets.filter(t => t.ai_auto_mode).length,
    aiPaused: tickets.filter(t => !t.ai_auto_mode).length,
  }

  const handleToggleAI = async (ticket) => {
    try {
      if (ticket.ai_auto_mode) {
        await pauseTicketAI(ticket.id)
      } else {
        await resumeTicketAI(ticket.id)
      }
      loadTickets()
    } catch (e) {
      console.error('Failed to toggle AI', e)
    }
  }

  const lastPage = Math.max(1, Math.ceil(total / perPage))

  const formatDate = (d) => {
    if (!d) return '-'
    return new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold" style={{ color: '#f5f5f7' }}>Canais IA</h1>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {[
          { label: 'Total', value: stats.total, color: '#fdd200' },
          { label: 'WhatsApp', value: stats.whatsapp, color: '#25D366' },
          { label: 'Instagram', value: stats.instagram, color: '#E1306C' },
          { label: 'Facebook', value: stats.facebook, color: '#1877F2' },
          { label: 'IA Ativa', value: stats.aiActive, color: '#34d399' },
          { label: 'IA Pausada', value: stats.aiPaused, color: '#f87171' },
        ].map(s => (
          <div key={s.label} className="rounded-lg p-3 text-center" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
            <p className="text-xs" style={{ color: '#8e8e93' }}>{s.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select value={filterPlatform} onChange={e => { setFilterPlatform(e.target.value); setPage(1) }}
          className="px-3 py-1.5 rounded-lg text-sm" style={{ background: 'rgba(255,255,255,0.06)', color: '#f5f5f7', border: '1px solid rgba(255,255,255,0.1)' }}>
          <option value="">Todas plataformas</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="instagram">Instagram</option>
          <option value="facebook">Facebook</option>
        </select>
        <select value={filterAI} onChange={e => { setFilterAI(e.target.value); setPage(1) }}
          className="px-3 py-1.5 rounded-lg text-sm" style={{ background: 'rgba(255,255,255,0.06)', color: '#f5f5f7', border: '1px solid rgba(255,255,255,0.1)' }}>
          <option value="">Status IA</option>
          <option value="active">IA Ativa</option>
          <option value="paused">IA Pausada</option>
        </select>
        <select value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1) }}
          className="px-3 py-1.5 rounded-lg text-sm" style={{ background: 'rgba(255,255,255,0.06)', color: '#f5f5f7', border: '1px solid rgba(255,255,255,0.1)' }}>
          <option value="">Todos status</option>
          <option value="open">Aberto</option>
          <option value="in_progress">Em Andamento</option>
          <option value="waiting">Aguardando</option>
          <option value="resolved">Resolvido</option>
        </select>
      </div>

      {/* Table */}
      <div className="rounded-xl overflow-hidden" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
        {loading ? (
          <div className="p-8 text-center" style={{ color: '#8e8e93' }}>Carregando...</div>
        ) : tickets.length === 0 ? (
          <div className="p-8 text-center" style={{ color: '#8e8e93' }}>Nenhuma conversa encontrada</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <th className="text-left px-4 py-3 font-medium" style={{ color: '#8e8e93' }}>Canal</th>
                <th className="text-left px-4 py-3 font-medium" style={{ color: '#8e8e93' }}>Cliente</th>
                <th className="text-left px-4 py-3 font-medium" style={{ color: '#8e8e93' }}>Assunto</th>
                <th className="text-left px-4 py-3 font-medium" style={{ color: '#8e8e93' }}>Status</th>
                <th className="text-center px-4 py-3 font-medium" style={{ color: '#8e8e93' }}>IA</th>
                <th className="text-left px-4 py-3 font-medium" style={{ color: '#8e8e93' }}>Data</th>
                <th className="text-center px-4 py-3 font-medium" style={{ color: '#8e8e93' }}>Ação</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map(t => {
                const plat = PLATFORM_CONFIG[t.source] || PLATFORM_CONFIG.whatsapp
                return (
                  <tr key={t.id} className="cursor-pointer hover:bg-white/5 transition-colors"
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                    onClick={() => onOpenTicket(t.id)}>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium"
                        style={{ background: `${plat.color}20`, color: plat.color }}>
                        <i className={plat.icon} /> {plat.label}
                      </span>
                    </td>
                    <td className="px-4 py-3" style={{ color: '#f5f5f7' }}>
                      {t.customer?.name || t.customer_name || '-'}
                    </td>
                    <td className="px-4 py-3 max-w-[250px] truncate" style={{ color: '#d1d1d6' }}>
                      {t.subject}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs px-2 py-0.5 rounded-full"
                        style={{ background: 'rgba(255,255,255,0.08)', color: '#d1d1d6' }}>
                        {t.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {t.ai_auto_mode ? (
                        <span className="text-xs font-medium" style={{ color: '#34d399' }}>Ativa</span>
                      ) : (
                        <span className="text-xs font-medium" style={{ color: '#f87171' }}>Pausada</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: '#8e8e93' }}>
                      {formatDate(t.updated_at)}
                    </td>
                    <td className="px-4 py-3 text-center" onClick={e => e.stopPropagation()}>
                      <button onClick={() => handleToggleAI(t)}
                        className="px-2 py-1 rounded text-xs font-medium transition-colors"
                        style={{
                          background: t.ai_auto_mode ? 'rgba(248,113,113,0.15)' : 'rgba(52,211,153,0.15)',
                          color: t.ai_auto_mode ? '#f87171' : '#34d399',
                        }}>
                        {t.ai_auto_mode ? 'Pausar' : 'Retomar'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {total > perPage && (
        <div className="flex items-center justify-between">
          <span className="text-xs" style={{ color: '#8e8e93' }}>
            {total} conversas — Pagina {page} de {lastPage}
          </span>
          <div className="flex gap-1">
            <button onClick={() => setPage(1)} disabled={page <= 1}
              className="px-2 py-1 rounded text-xs disabled:opacity-30"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#f5f5f7' }}>&laquo;</button>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
              className="px-2 py-1 rounded text-xs disabled:opacity-30"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#f5f5f7' }}>&lsaquo;</button>
            <button onClick={() => setPage(p => Math.min(lastPage, p + 1))} disabled={page >= lastPage}
              className="px-2 py-1 rounded text-xs disabled:opacity-30"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#f5f5f7' }}>&rsaquo;</button>
            <button onClick={() => setPage(lastPage)} disabled={page >= lastPage}
              className="px-2 py-1 rounded text-xs disabled:opacity-30"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#f5f5f7' }}>&raquo;</button>
          </div>
        </div>
      )}
    </div>
  )
}
