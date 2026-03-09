import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../components/Toast'
import api from '../services/api'

const STATUS_LABELS = {
  open: { label: 'Aberto', color: '#3B82F6', bg: 'rgba(59,130,246,0.15)' },
  in_progress: { label: 'Em Andamento', color: '#F59E0B', bg: 'rgba(245,158,11,0.15)' },
  waiting: { label: 'Aguardando', color: '#8B5CF6', bg: 'rgba(139,92,246,0.15)' },
  resolved: { label: 'Resolvido', color: '#10B981', bg: 'rgba(16,185,129,0.15)' },
  closed: { label: 'Fechado', color: '#64748B', bg: 'rgba(100,116,139,0.15)' },
  escalated: { label: 'Escalado', color: '#EF4444', bg: 'rgba(239,68,68,0.15)' },
}

const PRIORITY_LABELS = {
  low: { label: 'Baixa', color: '#64748B', bg: 'rgba(100,116,139,0.15)' },
  medium: { label: 'Media', color: '#3B82F6', bg: 'rgba(59,130,246,0.15)' },
  high: { label: 'Alta', color: '#F97316', bg: 'rgba(249,115,22,0.15)' },
  urgent: { label: 'Urgente', color: '#EF4444', bg: 'rgba(239,68,68,0.15)' },
}

export default function RAMonitorPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [tickets, setTickets] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get('/ra-monitor/tickets', { params: { limit: 50 } })
      setTickets(res.data.tickets || [])
      setTotal(res.data.total || 0)
    } catch { toast.error('Erro ao carregar tickets RA') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const sync = async () => {
    setSyncing(true)
    try {
      const res = await api.post('/ra-monitor/sync')
      const { new_complaints, tickets_created, errors } = res.data
      if (tickets_created > 0) {
        toast.success(`${tickets_created} ticket(s) criado(s) de ${new_complaints} reclamacao(oes)`)
      } else if (new_complaints === 0) {
        toast.info('Nenhuma reclamacao nova encontrada')
      } else {
        toast.info(`${new_complaints} reclamacao(oes) encontrada(s), 0 tickets criados`)
      }
      if (errors?.length > 0) {
        toast.error(`${errors.length} erro(s) ao criar tickets`)
      }
      await load()
    } catch { toast.error('Erro ao sincronizar') }
    finally { setSyncing(false) }
  }

  const formatDate = (iso) => {
    if (!iso) return '-'
    const d = new Date(iso)
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })
  }

  const openCount = tickets.filter(t => !['resolved', 'closed'].includes(t.status)).length

  return (
    <div className="p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Monitor Reclame Aqui</h1>
            <p className="text-sm mt-1" style={{ color: '#64748B' }}>
              Acompanhe reclamacoes do Reclame Aqui
            </p>
          </div>
          {total > 0 && (
            <span className="text-[11px] font-bold px-3 py-1.5 rounded-full"
              style={{ background: openCount > 0 ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)',
                       color: openCount > 0 ? '#EF4444' : '#10B981' }}>
              {openCount} aberto{openCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <button onClick={sync} disabled={syncing}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition cursor-pointer hover:opacity-90 disabled:opacity-50"
          style={{ background: '#E5A800', color: '#000' }}>
          <i className={`fas fa-sync-alt text-xs ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? 'Sincronizando...' : 'Sincronizar'}
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <i className="fas fa-spinner animate-spin text-2xl" style={{ color: '#64748B' }} />
        </div>
      ) : tickets.length === 0 ? (
        <div className="text-center py-20 rounded-2xl" style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: 'rgba(229,168,0,0.1)' }}>
            <i className="fas fa-shield-alt text-2xl" style={{ color: '#E5A800' }} />
          </div>
          <p className="font-semibold text-white mb-1">Nenhum ticket do Reclame Aqui</p>
          <p className="text-sm" style={{ color: '#64748B' }}>
            Clique em "Sincronizar" ou aguarde reclamacoes chegarem via email
          </p>
        </div>
      ) : (
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <Th>#</Th>
                  <Th>Assunto</Th>
                  <Th align="center">Status</Th>
                  <Th align="center">Prioridade</Th>
                  <Th align="center">Data</Th>
                  <Th align="center">Tags</Th>
                </tr>
              </thead>
              <tbody>
                {tickets.map(ticket => {
                  const st = STATUS_LABELS[ticket.status] || STATUS_LABELS.open
                  const pr = PRIORITY_LABELS[ticket.priority] || PRIORITY_LABELS.medium
                  return (
                    <tr key={ticket.id}
                      className="hover:bg-white/[0.03] transition cursor-pointer"
                      style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                      onClick={() => navigate(`/tickets/${ticket.id}`)}>
                      <td className="px-5 py-3.5">
                        <span className="text-xs font-mono" style={{ color: '#64748B' }}>
                          {ticket.number || ticket.id}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <p className="text-sm font-medium text-white truncate max-w-md">{ticket.subject || 'Sem assunto'}</p>
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full"
                          style={{ background: st.bg, color: st.color }}>
                          {st.label}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full"
                          style={{ background: pr.bg, color: pr.color }}>
                          {pr.label}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <span className="text-xs" style={{ color: '#94A3B8' }}>
                          {formatDate(ticket.created_at)}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <div className="flex items-center justify-center gap-1 flex-wrap">
                          {(ticket.tags || []).map(tag => (
                            <span key={tag} className="text-[10px] font-medium px-2 py-0.5 rounded-full"
                              style={{ background: tag === 'reclame_aqui' ? 'rgba(239,68,68,0.12)' : 'rgba(255,255,255,0.06)',
                                       color: tag === 'reclame_aqui' ? '#EF4444' : '#64748B' }}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="mt-6 flex items-center gap-2 text-[11px]" style={{ color: '#475569' }}>
        <i className="fas fa-info-circle" />
        <span>Reclamacoes sao detectadas automaticamente via Gmail forwarding. Use "Sincronizar" para buscar manualmente.</span>
      </div>
    </div>
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
