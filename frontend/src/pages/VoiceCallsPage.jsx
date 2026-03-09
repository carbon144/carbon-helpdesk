import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../components/Toast'
import { getVoiceCalls } from '../services/api'

/* ═══════════════════════════════════════════════
   VOICE CALLS — Carbon Expert Hub
   Layout: Live panel (top) + History (bottom)
   ═══════════════════════════════════════════════ */

const ENDED_REASON_LABELS = {
  'customer-ended-call': 'Cliente desligou',
  'silence-timed-out': 'Silencio',
  'exceeded-max-duration': 'Tempo excedido',
  'customer-busy': 'Ocupado',
  'customer-did-not-answer': 'Nao atendeu',
  'voicemail': 'Caixa postal',
  'manually-canceled': 'Cancelada',
  'assistant-error': 'Erro IA',
  'phone-call-provider-closed-websocket': 'Conexao perdida',
  'pipeline-error-openai-voice-failed': 'Erro de voz',
}

const REASON_COLORS = {
  'customer-ended-call': { bg: 'rgba(34,197,94,0.1)', text: '#22C55E', icon: 'fa-phone-slash' },
  'silence-timed-out': { bg: 'rgba(245,158,11,0.1)', text: '#F59E0B', icon: 'fa-clock' },
  'exceeded-max-duration': { bg: 'rgba(245,158,11,0.1)', text: '#F59E0B', icon: 'fa-hourglass-end' },
  'customer-did-not-answer': { bg: 'rgba(239,68,68,0.1)', text: '#EF4444', icon: 'fa-phone-missed' },
}

function fmt(seconds) {
  if (!seconds || seconds <= 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  const yesterday = new Date(now); yesterday.setDate(yesterday.getDate() - 1)
  const isYesterday = d.toDateString() === yesterday.toDateString()

  const time = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  if (isToday) return `Hoje ${time}`
  if (isYesterday) return `Ontem ${time}`
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }) + ` ${time}`
}

function fmtPhone(phone) {
  if (!phone) return 'Numero oculto'
  const d = phone.replace(/\D/g, '')
  if (d.length === 13 && d.startsWith('55')) {
    const ddd = d.slice(2, 4)
    const num = d.slice(4)
    return num.length === 9
      ? `(${ddd}) ${num.slice(0,5)}-${num.slice(5)}`
      : `(${ddd}) ${num.slice(0,4)}-${num.slice(4)}`
  }
  if (d.length === 11) {
    return `(${d.slice(0,2)}) ${d.slice(2,7)}-${d.slice(7)}`
  }
  return phone
}

/* ─── Live Call Pulse ─── */
function LivePulse() {
  return (
    <span className="relative flex h-2.5 w-2.5">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
        style={{ background: '#22C55E' }} />
      <span className="relative inline-flex rounded-full h-2.5 w-2.5"
        style={{ background: '#22C55E' }} />
    </span>
  )
}

/* ─── Elapsed Timer ─── */
function ElapsedTimer({ startedAt }) {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const start = new Date(startedAt).getTime()
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [startedAt])
  return <span className="font-mono text-[13px] tabular-nums">{fmt(elapsed)}</span>
}

/* ─── Audio Player ─── */
function AudioPlayer({ url }) {
  const ref = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [dur, setDur] = useState(0)
  const barRef = useRef(null)

  if (!url) return (
    <span className="text-[12px] flex items-center gap-1.5" style={{ color: 'var(--text-tertiary)' }}>
      <i className="fas fa-microphone-slash text-[10px]" /> Sem gravacao
    </span>
  )

  const toggle = () => {
    if (!ref.current) return
    playing ? ref.current.pause() : ref.current.play()
    setPlaying(!playing)
  }

  const seek = (e) => {
    if (!ref.current || !barRef.current) return
    const rect = barRef.current.getBoundingClientRect()
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    ref.current.currentTime = pct * ref.current.duration
  }

  return (
    <div className="flex items-center gap-2.5 group">
      <audio
        ref={ref}
        src={url}
        preload="metadata"
        onLoadedMetadata={() => setDur(ref.current?.duration || 0)}
        onTimeUpdate={() => {
          const a = ref.current
          if (a?.duration) setProgress((a.currentTime / a.duration) * 100)
        }}
        onEnded={() => { setPlaying(false); setProgress(0) }}
      />
      <button onClick={toggle}
        className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all"
        style={{
          background: playing ? 'rgba(239,68,68,0.12)' : 'var(--accent-soft)',
          color: playing ? '#EF4444' : 'var(--accent)',
        }}>
        <i className={`fas ${playing ? 'fa-pause' : 'fa-play'} text-[10px] ${!playing ? 'ml-0.5' : ''}`} />
      </button>
      <div className="flex-1 flex items-center gap-2">
        <div ref={barRef} onClick={seek}
          className="flex-1 h-1 rounded-full cursor-pointer group-hover:h-1.5 transition-all"
          style={{ background: 'var(--border-color)' }}>
          <div className="h-full rounded-full transition-all"
            style={{ width: `${progress}%`, background: 'var(--accent)' }} />
        </div>
        <span className="text-[11px] font-mono tabular-nums shrink-0" style={{ color: 'var(--text-tertiary)' }}>
          {fmt(dur)}
        </span>
      </div>
    </div>
  )
}

/* ─── Live Call Card ─── */
function LiveCallCard({ call }) {
  const transcriptRef = useRef(null)

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
    }
  }, [call.transcript_lines])

  return (
    <div className="glass-card p-4 flex flex-col gap-3" style={{ borderColor: 'rgba(34,197,94,0.3)' }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LivePulse />
          <div className="w-9 h-9 rounded-full flex items-center justify-center"
            style={{ background: 'rgba(34,197,94,0.1)' }}>
            <i className="fas fa-phone-volume text-[13px]" style={{ color: '#22C55E' }} />
          </div>
          <div>
            <p className="text-[13px] font-semibold" style={{ color: 'var(--text-primary)' }}>
              {fmtPhone(call.caller_phone)}
            </p>
            <p className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
              Ligacao ativa com Carlos IA
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2" style={{ color: '#22C55E' }}>
          <ElapsedTimer startedAt={call.started_at} />
        </div>
      </div>

      {/* Live transcript */}
      {call.transcript_lines?.length > 0 && (
        <div ref={transcriptRef}
          className="rounded-lg p-3 max-h-[160px] overflow-auto space-y-1.5"
          style={{ background: 'var(--bg-tertiary)' }}>
          {call.transcript_lines.map((line, i) => (
            <div key={i} className="flex gap-2 text-[12px]">
              <span className="shrink-0 font-semibold" style={{
                color: line.role === 'assistant' ? 'var(--accent)' : '#3B82F6',
              }}>
                {line.role === 'assistant' ? 'Carlos:' : 'Cliente:'}
              </span>
              <span style={{ color: 'var(--text-secondary)' }}>{line.text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── Call History Row ─── */
function CallRow({ call, isExpanded, onToggle, onNavigate }) {
  const reasonStyle = REASON_COLORS[call.ended_reason] || { bg: 'rgba(100,116,139,0.08)', text: '#94A3B8', icon: 'fa-phone' }

  return (
    <>
      <div
        className="flex items-center gap-4 px-5 py-3.5 cursor-pointer transition-colors"
        style={{ borderBottom: '1px solid var(--border-color)' }}
        onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
        onClick={onToggle}
      >
        {/* Icon */}
        <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
          style={{ background: reasonStyle.bg }}>
          <i className={`fas ${reasonStyle.icon} text-[12px]`} style={{ color: reasonStyle.text }} />
        </div>

        {/* Phone + Customer */}
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
            {fmtPhone(call.caller_phone)}
          </p>
          {call.customer ? (
            <button
              onClick={e => { e.stopPropagation(); onNavigate(`/tickets?customer=${call.customer.id}`) }}
              className="text-[11px] font-medium hover:underline truncate block"
              style={{ color: 'var(--accent)' }}
            >
              {call.customer.name}
            </button>
          ) : (
            <p className="text-[11px] truncate" style={{ color: 'var(--text-tertiary)' }}>
              {call.summary ? call.summary.slice(0, 60) + (call.summary.length > 60 ? '...' : '') : 'Sem identificacao'}
            </p>
          )}
        </div>

        {/* Duration */}
        <div className="text-center shrink-0" style={{ width: 60 }}>
          <p className="text-[13px] font-mono tabular-nums" style={{ color: 'var(--text-primary)' }}>
            {fmt(call.duration_seconds)}
          </p>
        </div>

        {/* Reason badge */}
        <div className="shrink-0" style={{ width: 120 }}>
          <span className="text-[11px] font-medium px-2 py-1 rounded-md inline-flex items-center gap-1"
            style={{ background: reasonStyle.bg, color: reasonStyle.text }}>
            {ENDED_REASON_LABELS[call.ended_reason] || call.ended_reason || '-'}
          </span>
        </div>

        {/* Date */}
        <div className="shrink-0 text-right" style={{ width: 100 }}>
          <p className="text-[12px]" style={{ color: 'var(--text-secondary)' }}>{fmtDate(call.created_at)}</p>
        </div>

        {/* Ticket */}
        <div className="shrink-0" style={{ width: 80 }}>
          {call.ticket_id ? (
            <button
              onClick={e => { e.stopPropagation(); onNavigate(`/tickets/${call.ticket_id}`) }}
              className="text-[11px] font-semibold px-2 py-1 rounded-md transition-colors"
              style={{ background: 'rgba(59,130,246,0.08)', color: '#3B82F6' }}
            >
              <i className="fas fa-ticket-alt mr-1" /> Ticket
            </button>
          ) : <span />}
        </div>

        {/* Expand chevron */}
        <div className="shrink-0 w-5">
          <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'} text-[10px]`}
            style={{ color: 'var(--text-tertiary)' }} />
        </div>
      </div>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="px-5 py-4" style={{ background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-color)' }}>
          <div className="grid grid-cols-3 gap-5">
            {/* Recording */}
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider mb-2.5" style={{ color: 'var(--text-tertiary)' }}>
                Gravacao
              </p>
              <AudioPlayer url={call.recording_url} />
            </div>

            {/* Summary */}
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider mb-2.5" style={{ color: 'var(--text-tertiary)' }}>
                Resumo
              </p>
              <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                {call.summary || 'Sem resumo'}
              </p>
            </div>

            {/* Transcript */}
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider mb-2.5" style={{ color: 'var(--text-tertiary)' }}>
                Transcricao
              </p>
              <div className="text-[12px] leading-relaxed max-h-[200px] overflow-auto rounded-lg p-3 space-y-1"
                style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                {call.transcript ? call.transcript.split('\n').map((line, i) => {
                  const isAI = line.startsWith('AI:')
                  const isUser = line.startsWith('User:')
                  return (
                    <p key={i} style={{ color: isAI ? 'var(--accent-muted)' : isUser ? '#3B82F6' : 'var(--text-secondary)' }}>
                      {line}
                    </p>
                  )
                }) : <p style={{ color: 'var(--text-tertiary)' }}>Sem transcricao</p>}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

/* ═══════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════ */

export default function VoiceCallsPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [calls, setCalls] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [activeCalls, setActiveCalls] = useState([])
  const wsRef = useRef(null)

  // Load history
  useEffect(() => { loadData() }, [page, search])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, per_page: 30 }
      if (search) params.search = search
      const { data } = await getVoiceCalls(params)
      setCalls(data.items)
      setTotalPages(data.pages)
      setTotal(data.total)
    } catch { toast.error('Falha ao carregar ligacoes') }
    setLoading(false)
  }, [page, search])

  // WebSocket for live calls
  useEffect(() => {
    const token = localStorage.getItem('carbon_token')
    if (!token) return

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/api/voice-calls/ws?token=${token}`)

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'active_calls') {
          setActiveCalls(msg.calls || [])
        } else if (msg.type === 'call_started') {
          setActiveCalls(prev => {
            if (prev.find(c => c.call_id === msg.call?.call_id)) return prev
            return [...prev, msg.call]
          })
        } else if (msg.type === 'call_ended') {
          setActiveCalls(prev => prev.filter(c => c.call_id !== msg.call_id))
          // Refresh history after call ends
          setTimeout(() => loadData(), 2000)
        } else if (msg.type === 'transcript') {
          setActiveCalls(prev => prev.map(c => {
            if (c.call_id !== msg.call_id) return c
            return {
              ...c,
              transcript_lines: [...(c.transcript_lines || []), { role: msg.role, text: msg.text }],
            }
          }))
        }
      } catch { /* ignore parse errors */ }
    }

    ws.onclose = () => {
      // Reconnect after 3s
      setTimeout(() => {
        if (wsRef.current === ws) wsRef.current = null
      }, 3000)
    }

    wsRef.current = ws
    return () => ws.close()
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    setSearch(searchInput)
  }

  // Stats from loaded calls
  const todayCalls = calls.filter(c => {
    if (!c.created_at) return false
    return new Date(c.created_at).toDateString() === new Date().toDateString()
  }).length
  const avgDuration = calls.length > 0
    ? Math.round(calls.reduce((sum, c) => sum + (c.duration_seconds || 0), 0) / calls.length)
    : 0

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-6 pt-5 pb-4" style={{ borderBottom: '1px solid var(--border-color)' }}>
        <div className="flex items-center justify-between max-w-[1400px] mx-auto">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'var(--accent-soft)' }}>
              <i className="fas fa-phone text-[15px]" style={{ color: 'var(--accent)' }} />
            </div>
            <div>
              <h1 className="text-[17px] font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Ligacoes
              </h1>
              <p className="text-[12px]" style={{ color: 'var(--text-tertiary)' }}>
                Central de atendimento por voz
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="flex items-center gap-5">
            {activeCalls.length > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
                style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)' }}>
                <LivePulse />
                <span className="text-[12px] font-semibold" style={{ color: '#22C55E' }}>
                  {activeCalls.length} ativa{activeCalls.length > 1 ? 's' : ''}
                </span>
              </div>
            )}
            <div className="text-center">
              <p className="text-[16px] font-bold tabular-nums" style={{ color: 'var(--text-primary)' }}>{total}</p>
              <p className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>Total</p>
            </div>
            <div className="text-center">
              <p className="text-[16px] font-bold tabular-nums" style={{ color: 'var(--text-primary)' }}>{todayCalls}</p>
              <p className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>Hoje</p>
            </div>
            <div className="text-center">
              <p className="text-[16px] font-bold font-mono tabular-nums" style={{ color: 'var(--text-primary)' }}>{fmt(avgDuration)}</p>
              <p className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>Media</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-[1400px] mx-auto px-6 py-4 space-y-4">

          {/* Live Calls */}
          {activeCalls.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <LivePulse />
                <h2 className="text-[13px] font-bold uppercase tracking-wider" style={{ color: '#22C55E' }}>
                  Ligacoes ativas
                </h2>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {activeCalls.map(call => (
                  <LiveCallCard key={call.call_id} call={call} />
                ))}
              </div>
            </div>
          )}

          {/* Search */}
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="flex-1 relative">
              <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-[12px]"
                style={{ color: 'var(--text-tertiary)' }} />
              <input
                type="text"
                value={searchInput}
                onChange={e => setSearchInput(e.target.value)}
                placeholder="Buscar por telefone, resumo ou transcricao..."
                className="w-full pl-9 pr-3 py-2 rounded-lg text-[13px]"
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                }}
              />
            </div>
            {search && (
              <button type="button"
                onClick={() => { setSearch(''); setSearchInput(''); setPage(1) }}
                className="px-3 py-2 rounded-lg text-[12px] font-medium"
                style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}>
                <i className="fas fa-times mr-1" /> Limpar
              </button>
            )}
          </form>

          {/* History */}
          <div className="card overflow-hidden">
            {/* Table header */}
            <div className="flex items-center gap-4 px-5 py-2.5"
              style={{ background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-color)' }}>
              <div className="w-9" />
              <div className="flex-1 text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Contato
              </div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-center" style={{ color: 'var(--text-tertiary)', width: 60 }}>
                Duracao
              </div>
              <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)', width: 120 }}>
                Status
              </div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-right" style={{ color: 'var(--text-tertiary)', width: 100 }}>
                Data
              </div>
              <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)', width: 80 }}>
                Ticket
              </div>
              <div className="w-5" />
            </div>

            {loading ? (
              <div className="p-16 text-center">
                <div className="inline-flex items-center gap-2 text-[13px]" style={{ color: 'var(--text-secondary)' }}>
                  <i className="fas fa-circle-notch fa-spin" style={{ color: 'var(--accent)' }} />
                  Carregando ligacoes...
                </div>
              </div>
            ) : calls.length === 0 ? (
              <div className="p-16 text-center">
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-3"
                  style={{ background: 'var(--bg-tertiary)' }}>
                  <i className="fas fa-phone text-[20px]" style={{ color: 'var(--text-tertiary)' }} />
                </div>
                <p className="text-[14px] font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  Nenhuma ligacao encontrada
                </p>
                <p className="text-[12px] mt-1" style={{ color: 'var(--text-tertiary)' }}>
                  As ligacoes recebidas pelo Carlos IA aparecerao aqui
                </p>
              </div>
            ) : (
              calls.map(call => (
                <CallRow
                  key={call.id}
                  call={call}
                  isExpanded={expandedId === call.id}
                  onToggle={() => setExpandedId(expandedId === call.id ? null : call.id)}
                  onNavigate={navigate}
                />
              ))
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between py-2">
              <p className="text-[12px]" style={{ color: 'var(--text-tertiary)' }}>
                {total} ligacao{total !== 1 ? 'es' : ''} &middot; Pagina {page}/{totalPages}
              </p>
              <div className="flex gap-1.5">
                <button onClick={() => setPage(1)} disabled={page <= 1}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-[11px] disabled:opacity-20 transition-colors card">
                  <i className="fas fa-angles-left" style={{ color: 'var(--text-secondary)' }} />
                </button>
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-[11px] disabled:opacity-20 transition-colors card">
                  <i className="fas fa-chevron-left" style={{ color: 'var(--text-secondary)' }} />
                </button>
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-[11px] disabled:opacity-20 transition-colors card">
                  <i className="fas fa-chevron-right" style={{ color: 'var(--text-secondary)' }} />
                </button>
                <button onClick={() => setPage(totalPages)} disabled={page >= totalPages}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-[11px] disabled:opacity-20 transition-colors card">
                  <i className="fas fa-angles-right" style={{ color: 'var(--text-secondary)' }} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
