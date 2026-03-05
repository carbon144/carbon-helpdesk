import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../../services/api'
import ChannelIcon from './ChannelIcon'
import { Inbox, Loader2, Search, X } from 'lucide-react'

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'agora'
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  return `${days}d`
}

const channelOptions = [
  { key: null, label: 'Todos' },
  { key: 'chat', label: 'Chat' },
  { key: 'whatsapp', label: 'WhatsApp' },
  { key: 'instagram', label: 'Instagram' },
  { key: 'facebook', label: 'Facebook' },
  { key: 'tiktok', label: 'TikTok' },
]

const statusOptions = [
  { key: null, label: 'Todos' },
  { key: 'open', label: 'Abertos' },
  { key: 'pending', label: 'Pendentes' },
  { key: 'resolved', label: 'Resolvidos' },
]

const statusDots = {
  open: '#22C55E',
  pending: '#EAB308',
  resolved: '#71717A',
  closed: '#52525B',
}

export default function ChatList({ activeConversationId, onSelectConversation }) {
  const [conversations, setConversations] = useState([])
  const [customers, setCustomers] = useState({})
  const [loading, setLoading] = useState(true)
  const [channel, setChannel] = useState(null)
  const [status, setStatus] = useState('open')
  const [search, setSearch] = useState('')
  const searchTimeout = useRef(null)

  const fetchConversations = useCallback(async () => {
    try {
      const params = { limit: 50 }
      if (channel) params.channel = channel
      if (status) params.status = status

      const res = await api.get('/chat/conversations', { params })
      const convs = res.data || []

      // Fetch customer names
      const custIds = [...new Set(convs.map((c) => c.customer_id))]
      const newCusts = { ...customers }
      await Promise.all(
        custIds
          .filter((id) => !newCusts[id])
          .map(async (id) => {
            try {
              const r = await api.get(`/customers/${id}`)
              newCusts[id] = r.data
            } catch { /* skip */ }
          })
      )
      setCustomers(newCusts)
      setConversations(convs)
    } catch (err) {
      console.error('Failed to fetch conversations:', err)
    } finally {
      setLoading(false)
    }
  }, [channel, status])

  useEffect(() => {
    setLoading(true)
    fetchConversations()
  }, [fetchConversations])

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(fetchConversations, 10000)
    return () => clearInterval(interval)
  }, [fetchConversations])

  const filteredConversations = search
    ? conversations.filter((c) => {
        const cust = customers[c.customer_id]
        const name = (cust?.name || '').toLowerCase()
        const email = (cust?.email || '').toLowerCase()
        const q = search.toLowerCase()
        return name.includes(q) || email.includes(q) || (c.subject || '').toLowerCase().includes(q)
      })
    : conversations

  return (
    <div className="w-80 shrink-0 flex flex-col h-full"
      style={{ borderRight: '1px solid rgba(255,255,255,0.06)', background: '#1F1F23' }}>
      {/* Header */}
      <div className="px-4 py-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <h2 className="text-lg font-semibold" style={{ color: '#E4E4E7' }}>Conversas</h2>
      </div>

      {/* Filters */}
      <div className="p-3 space-y-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: '#52525B' }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar conversa..."
            className="w-full pl-9 pr-8 py-2 rounded-lg text-sm focus:outline-none focus:ring-1"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: '#E4E4E7',
              focusRingColor: '#E5A800',
            }}
          />
          {search && (
            <button onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 cursor-pointer" style={{ color: '#52525B' }}>
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="flex gap-1 overflow-x-auto pb-1">
          {channelOptions.map((c) => (
            <button key={c.key || 'all'} onClick={() => setChannel(c.key)}
              className="px-2.5 py-1 text-xs font-medium rounded-full whitespace-nowrap transition cursor-pointer"
              style={{
                background: channel === c.key ? '#E5A800' : 'rgba(255,255,255,0.06)',
                color: channel === c.key ? '#000' : '#A1A1AA',
              }}>
              {c.label}
            </button>
          ))}
        </div>

        <div className="flex gap-1">
          {statusOptions.map((s) => (
            <button key={s.key || 'all'} onClick={() => setStatus(s.key)}
              className="px-2.5 py-1 text-xs font-medium rounded-full transition cursor-pointer"
              style={{
                background: status === s.key ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.04)',
                color: status === s.key ? '#E4E4E7' : '#71717A',
              }}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: '#52525B' }} />
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12" style={{ color: '#3F3F46' }}>
            <Inbox className="w-10 h-10 mb-2" />
            <p className="text-sm">Nenhuma conversa</p>
          </div>
        ) : (
          <div>
            {filteredConversations.map((conv) => {
              const cust = customers[conv.customer_id]
              const name = cust?.name || 'Visitante'
              const isActive = conv.id === activeConversationId

              return (
                <button key={conv.id} onClick={() => onSelectConversation(conv, cust)}
                  className="w-full text-left px-4 py-3 flex items-start gap-3 transition cursor-pointer"
                  style={{
                    background: isActive ? 'rgba(229,168,0,0.1)' : 'transparent',
                    borderLeft: isActive ? '3px solid #E5A800' : '3px solid transparent',
                  }}
                  onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.03)' }}
                  onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent' }}>
                  <div className="relative flex-shrink-0">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold"
                      style={{ background: '#E5A800', color: '#000' }}>
                      {name.charAt(0).toUpperCase()}
                    </div>
                    <div className="absolute -bottom-0.5 -right-0.5 w-5 h-5 rounded-full flex items-center justify-center shadow-sm"
                      style={{ background: '#27272A' }}>
                      <ChannelIcon channel={conv.channel} size="w-3 h-3" />
                    </div>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-sm truncate" style={{ color: '#E4E4E7' }}>{name}</span>
                      <span className="text-xs whitespace-nowrap flex-shrink-0" style={{ color: '#52525B' }}>
                        {timeAgo(conv.last_message_at)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <p className="text-xs truncate flex-1" style={{ color: '#71717A' }}>
                        {conv.subject || `#${conv.number || ''}`}
                      </p>
                      <div className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: statusDots[conv.status] || '#52525B' }} />
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
