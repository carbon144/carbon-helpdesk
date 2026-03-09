import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useToast } from '../components/Toast'
import {
  getTicket, getTickets, updateTicket, addMessage, getMacros, trackMacroUse, getUsers, getCustomerHistory,
  triageTicket, suggestReply, updateSupplierNotes, updateTracking, refreshTracking,
  blacklistCustomer, unblacklistCustomer, generateSummary, getNextTicket,
  updateInternalNotes, sendProtocolEmail, backfillProtocols,
  getMediaItems, createMediaItem, suggestMedia, uploadMedia, uploadAttachment, getCopilotInsights,
  getEcommerceOrders, getShopifyCustomer, refundShopifyOrder, cancelShopifyOrder,
  pauseTicketAI, resumeTicketAI, sendMetaReply, submitCsat,
  mergeTickets, mergeCustomers, searchCustomers, getCustomerFullHistory,
  unmergeTicket, unmergeCustomer,
} from '../services/api'
import MetaBadge from '../components/MetaBadge'
import { STATUS_LABELS, PRIORITY_LABELS, CATEGORY_LABELS, SENTIMENT_LABELS, TAG_COLORS, TAG_LABELS } from '../constants/ticket'

const MS_PER_HOUR = 3_600_000
const MS_PER_MINUTE = 60_000

// ── Email body cleaner: strips quotes, signatures, headers ──
function cleanEmailBody(text) {
  if (!text) return { clean: '', hasMore: false }
  const lines = text.split('\n')
  const cleanLines = []
  let hitQuoteOrSig = false

  for (const line of lines) {
    const trimmed = line.trim()
    // Signature markers
    if (/^[-—]{2,}\s*$/.test(trimmed)) { hitQuoteOrSig = true; break }
    // Quote headers: "On ... wrote:", "Em ... escreveu:", "De: ...", "From: ..."
    if (/^(On |Em |De: |From: |Enviado: |Sent: |Date: |Para: |To: |Subject: |Assunto: )/.test(trimmed) && trimmed.length > 40) { hitQuoteOrSig = true; break }
    // Quoted lines
    if (/^>/.test(trimmed)) { hitQuoteOrSig = true; break }
    // Gmail-style separator
    if (/^-{4,}/.test(trimmed) && lines.indexOf(line) > 2) { hitQuoteOrSig = true; break }
    cleanLines.push(line)
  }
  // Trim trailing empty lines
  while (cleanLines.length > 0 && cleanLines[cleanLines.length - 1].trim() === '') cleanLines.pop()
  return { clean: cleanLines.join('\n'), hasMore: hitQuoteOrSig }
}

// ── Chat message bubble component ──
function ChatBubble({ msg, isLast, isLastInbound }) {
  const [showFull, setShowFull] = useState(false)
  const { clean, hasMore } = cleanEmailBody(msg.body_text)
  const isInbound = msg.type === 'inbound'
  const isNote = msg.type === 'internal_note'

  return (
    <div className={`chat-bubble flex ${isInbound ? 'justify-start' : 'justify-end'}`}>
      <div className="max-w-[78%]">
        {/* Sender + time */}
        <div className={`flex items-center gap-2 mb-1.5 ${isInbound ? '' : 'justify-end'}`}>
          {isInbound && (
            <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0"
              style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)' }}>
              <i className="fas fa-user text-[9px] text-[var(--text-tertiary)]" />
            </div>
          )}
          <span className="text-[11px] font-semibold text-[var(--text-secondary)]">
            {isNote && <i className="fas fa-sticky-note mr-1 text-green-500" />}
            {msg.sender_name || msg.sender_email || 'Sistema'}
            {msg.sender_name === 'Carbon IA' && (
              <span className="ml-1.5 text-[9px] bg-emerald-500/12 text-emerald-500 px-1.5 py-0.5 rounded-full font-bold">IA</span>
            )}
          </span>
          <span className="text-[10px] text-[var(--text-tertiary)] tabular-nums">
            {new Date(msg.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
          </span>
          {msg.is_scheduled && (
            <span className="text-[9px] bg-purple-500/12 text-purple-500 px-1.5 py-0.5 rounded-full font-semibold">
              <i className="fas fa-clock mr-0.5" />Programado
            </span>
          )}
          {!isInbound && !isNote && (
            <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0"
              style={{ background: 'var(--accent-soft)', border: '1px solid rgba(229,168,0,0.15)' }}>
              <i className="fas fa-headset text-[9px]" style={{ color: 'var(--accent)' }} />
            </div>
          )}
        </div>
        {/* Bubble */}
        <div className={`rounded-2xl px-4 py-3 ${
          isNote ? 'border-l-4 border-l-green-500 rounded-tr-sm' :
          isInbound
            ? `bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-tl-sm shadow-[var(--shadow-xs)] ${isLastInbound ? 'ring-1 ring-[var(--accent)]/20 border-[var(--accent)]/20' : ''}`
            : 'bg-[var(--accent-soft)] border border-[var(--accent)]/10 rounded-tr-sm'
        }`} style={isNote ? { background: 'rgba(34,197,94,0.15)' } : undefined}>
          {isLastInbound && isInbound && (
            <div className="flex items-center gap-1 mb-2">
              <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: 'var(--accent-soft)', color: 'var(--accent-muted)' }}>NOVO</span>
            </div>
          )}
          {msg.cc && <div className="text-[var(--text-tertiary)] text-[10px] mb-1.5">CC: {msg.cc}</div>}
          <p className="text-[var(--text-primary)] text-[13.5px] whitespace-pre-wrap leading-[1.65] break-words">{showFull ? msg.body_text : clean}</p>
          {hasMore && (
            <button onClick={() => setShowFull(!showFull)}
              className="text-[10px] text-[var(--accent-muted)] hover:text-[var(--accent)] mt-2 transition font-medium">
              <i className={`fas fa-chevron-${showFull ? 'up' : 'down'} mr-1`} />
              {showFull ? 'Ocultar original' : 'Ver email completo'}
            </button>
          )}
          {msg.attachments && Array.isArray(msg.attachments) && msg.attachments.length > 0 && (
            <div className="mt-2 space-y-1.5">
              {msg.attachments.map((att, i) => {
                const src = att.url || att.drive_url
                const mime = (att.mime_type || att.content_type || '').toLowerCase()
                const isImage = mime.startsWith('image/') || /\.(jpg|jpeg|png|gif|webp|bmp)$/i.test(att.name || '')
                const isVideo = mime.startsWith('video/') || /\.(mp4|webm|mov|avi)$/i.test(att.name || '')
                if (isImage) return (
                  <a key={i} href={src} target="_blank" rel="noopener noreferrer" className="block">
                    <img src={src} alt={att.name} className="max-w-[280px] max-h-[200px] rounded-lg border border-[var(--border-color)] object-cover hover:opacity-90 transition" />
                  </a>
                )
                if (isVideo) return (
                  <video key={i} src={src} controls className="max-w-[320px] max-h-[220px] rounded-lg border border-[var(--border-color)]" />
                )
                return (
                  <a key={i} href={src} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 bg-[var(--bg-tertiary)] hover:bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs px-2.5 py-1.5 rounded-lg transition border border-[var(--border-color)]">
                    <i className="fas fa-paperclip text-[10px]" />
                    <span className="max-w-[200px] truncate">{att.name}</span>
                  </a>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function applyMacroVars(content, ticket, agentName) {
  return content
    .replace(/\{\{cliente\}\}/gi, ticket.customer?.name || '')
    .replace(/\{\{agente\}\}/gi, agentName || '')
    .replace(/\{\{email\}\}/gi, ticket.customer?.email || '')
    .replace(/\{\{numero\}\}/gi, `#${ticket.number}`)
    .replace(/\{\{assunto\}\}/gi, ticket.subject || '')
    .replace(/\{\{prioridade\}\}/gi, PRIORITY_LABELS[ticket.priority] || ticket.priority)
    .replace(/\{\{categoria\}\}/gi, CATEGORY_LABELS[ticket.category] || ticket.category || '')
    .replace(/\{\{status\}\}/gi, STATUS_LABELS[ticket.status] || ticket.status)
    .replace(/\{\{rastreio\}\}/gi, ticket.tracking_code || '')
}

// ── Sidebar tab config (main + secondary) ──
const SIDEBAR_TABS_MAIN = [
  { id: 'actions', icon: 'fa-sliders-h', label: 'Ações' },
  { id: 'customer', icon: 'fa-user', label: 'Cliente' },
  { id: 'notes', icon: 'fa-sticky-note', label: 'Notas' },
]
const SIDEBAR_TABS_MORE = [
  { id: 'copilot', icon: 'fa-brain', label: 'Copiloto' },
  { id: 'orders', icon: 'fa-shopping-cart', label: 'Pedidos' },
  { id: 'media', icon: 'fa-photo-video', label: 'Mídia' },
]
const SIDEBAR_TABS = [...SIDEBAR_TABS_MAIN, ...SIDEBAR_TABS_MORE]

// Order status colors (dark theme compatible)
const ORDER_STATUS_COLORS = {
  pago: 'bg-emerald-500/15 text-emerald-400',
  enviado: 'bg-blue-500/15 text-blue-400',
  entregue: 'bg-green-500/15 text-green-400',
  pendente: 'bg-yellow-500/15 text-yellow-400',
  nao_pago: 'bg-red-500/15 text-red-400',
  recusado: 'bg-red-500/15 text-red-400',
  abandonado: 'bg-gray-500/15 text-gray-400',
  reembolsado: 'bg-orange-500/15 text-orange-400',
  cancelado: 'bg-red-500/15 text-red-300',
  processando: 'bg-indigo-500/15 text-indigo-400',
}

export default function TicketDetailPage({ user, embeddedTicketId, onEmbeddedBack, onEmbeddedOpen, onTicketUpdate }) {
  const toast = useToast()
  const { id } = useParams()
  const ticketId = embeddedTicketId || id
  const navigate = useNavigate()
  const embedded = !!embeddedTicketId
  const onBack = embedded ? (onEmbeddedBack || (() => {})) : () => navigate(-1)
  const onOpenTicket = embedded ? (onEmbeddedOpen || ((tid) => navigate(`/tickets/${tid}`))) : (tid) => navigate(`/tickets/${tid}`)
  const [ticket, setTicket] = useState(null)
  const [reply, setReply] = useState('')
  const [replyType, setReplyType] = useState('outbound')
  const [macros, setMacros] = useState([])
  const [agents, setAgents] = useState([])
  const [sending, setSending] = useState(false)
  const [showMacros, setShowMacros] = useState(false)
  const [showSendMenu, setShowSendMenu] = useState(false)
  const [slashOpen, setSlashOpen] = useState(false)
  const [slashFilter, setSlashFilter] = useState('')
  const [slashIdx, setSlashIdx] = useState(0)
  const [slaCountdown, setSlaCountdown] = useState('')
  const [history, setHistory] = useState([])
  const [aiLoading, setAiLoading] = useState(false)
  const [aiSuggestion, setAiSuggestion] = useState(null)
  const [supplierNotes, setSupplierNotes] = useState('')
  const [trackingCode, setTrackingCode] = useState('')
  const [activeTab, setActiveTab] = useState('messages')
  const [editingCategory, setEditingCategory] = useState(false)
  const [editingPriority, setEditingPriority] = useState(false)
  const [headerExpanded, setHeaderExpanded] = useState(false)
  const [internalNotes, setInternalNotes] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [showProtocolModal, setShowProtocolModal] = useState(false)
  const [sendingProtocol, setSendingProtocol] = useState(false)
  // Media
  const [mediaItems, setMediaItems] = useState([])
  const [mediaSuggestions, setMediaSuggestions] = useState([])
  const [mediaFilter, setMediaFilter] = useState('')
  const [showAddMedia, setShowAddMedia] = useState(false)
  const [newMedia, setNewMedia] = useState({ name: '', drive_url: '', description: '', category: 'video' })
  const [addingMedia, setAddingMedia] = useState(false)
  const [mediaLoading, setMediaLoading] = useState(false)
  const [mediaUploadFile, setMediaUploadFile] = useState(null)
  const [mediaUploading, setMediaUploading] = useState(false)
  const mediaFileRef = useRef(null)
  // Copilot
  const [copilotData, setCopilotData] = useState(null)
  const [copilotLoading, setCopilotLoading] = useState(false)
  // E-commerce orders (Shopify + Yampi + Appmax)
  const [shopifyOrders, setShopifyOrders] = useState([])
  const [yampiOrders, setYampiOrders] = useState([])
  const [appmaxOrders, setAppmaxOrders] = useState([])
  const [ecomLoading, setEcomLoading] = useState(false)
  const [ecomError, setEcomError] = useState(null)
  const [expandedOrder, setExpandedOrder] = useState(null)
  const [ecomSubTab, setEcomSubTab] = useState('shopify')
  // Shopify customer profile
  const [shopifyCustomer, setShopifyCustomer] = useState(null)
  const [shopifyCustomerLoading, setShopifyCustomerLoading] = useState(false)
  // Shopify actions
  const [actionLoading, setActionLoading] = useState(null)
  const [showRefundModal, setShowRefundModal] = useState(null)
  const [showCancelModal, setShowCancelModal] = useState(null)
  // CSAT
  const [showCsatForm, setShowCsatForm] = useState(false)
  const [csatScore, setCsatScore] = useState(0)
  const [csatComment, setCsatComment] = useState('')
  const [csatSubmitting, setCsatSubmitting] = useState(false)
  const [csatSubmitted, setCsatSubmitted] = useState(false)
  // Collision detection
  const [otherViewers, setOtherViewers] = useState([])
  // Sidebar tab
  const [sidebarTab, setSidebarTab] = useState('actions')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(typeof window !== 'undefined' && window.innerWidth < 1280)
  const [showMergeCandidates, setShowMergeCandidates] = useState(false)
  // Meta AI controls
  const [aiPausing, setAiPausing] = useState(false)
  // Merge
  const [showMergeModal, setShowMergeModal] = useState(false)
  const [mergeSearch, setMergeSearch] = useState('')
  const [mergeResults, setMergeResults] = useState([])
  const [sameCustomerTickets, setSameCustomerTickets] = useState([])
  const [selectedMergeSources, setSelectedMergeSources] = useState({})
  const [mergingBatch, setMergingBatch] = useState(false)
  const [showMergeCustomerModal, setShowMergeCustomerModal] = useState(false)
  const [mergeCustomerSearch, setMergeCustomerSearch] = useState('')
  const [mergeCustomerResults, setMergeCustomerResults] = useState([])
  const textareaRef = useRef(null)
  // Chat history toggle
  const [historyMode, setHistoryMode] = useState('ticket') // 'ticket' or 'full'
  const [fullHistory, setFullHistory] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  // CC/BCC
  const [showCcBcc, setShowCcBcc] = useState(false)
  const [replyCc, setReplyCc] = useState('')
  const [replyBcc, setReplyBcc] = useState('')
  // Scheduled send
  const [showSchedulePicker, setShowSchedulePicker] = useState(false)
  const [scheduleDate, setScheduleDate] = useState('')
  // Attachments
  const [replyAttachments, setReplyAttachments] = useState([])
  const [uploadingAttachment, setUploadingAttachment] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const attachmentInputRef = useRef(null)

  const isMetaChannel = ticket && ['whatsapp', 'instagram', 'facebook'].includes(ticket.source)

  // ── Refs for lazy loading (declared early so all effects can access them) ──
  const loadedTicketRef = useRef(null)
  const ecomLoadedRef = useRef(null)
  const copilotLoadedRef = useRef(null)
  const mediaLoadedRef = useRef(null)

  // ── Load macros/agents once (cached across ticket switches) ──
  const macrosLoadedRef = useRef(false)
  useEffect(() => {
    if (macrosLoadedRef.current) return
    macrosLoadedRef.current = true
    getMacros().then(r => setMacros(r.data)).catch(() => {})
    getUsers().then(r => setAgents(r.data)).catch(() => {})
  }, [])

  // ── Core ticket load + reset state on ticket change ──
  useEffect(() => {
    loadTicket()
    // Reset UI state
    setReply(''); setReplyCc(''); setReplyBcc(''); setShowCcBcc(false)
    setReplyAttachments([]); setShowSchedulePicker(false); setScheduleDate('')
    setAiSuggestion(null); setAiInlineSuggestion('')
    setHistoryMode('ticket'); setFullHistory(null)
    setOtherViewers([])
    setHistory([]); setSameCustomerTickets([])
    setShopifyCustomer(null); setShopifyOrders([]); setYampiOrders([]); setAppmaxOrders([])
    setCopilotData(null); setMediaSuggestions([])
    // Reset lazy-load refs so tabs reload for new ticket
    ecomLoadedRef.current = null
    copilotLoadedRef.current = null
    mediaLoadedRef.current = null
    loadedTicketRef.current = null

    // Collision detection via WebSocket
    const token = localStorage.getItem('carbon_token')
    if (token) {
      try {
        const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsHost = window.location.host
        const ws = new WebSocket(`${wsProto}//${wsHost}/ws/${token}`)
        ws.onopen = () => {
          ws.send(JSON.stringify({ type: 'viewing_ticket', ticket_id: ticketId }))
        }
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'ticket_viewers' && data.ticket_id === ticketId) {
              setOtherViewers(data.viewers?.filter(v => v.user_id !== user?.id) || [])
            }
            if (data.type === 'ticket_update' && data.ticket_id === ticketId) {
              loadTicket()
            }
          } catch (e) { console.warn('WS message parse error:', e) }
        }
        return () => {
          try { ws.send(JSON.stringify({ type: 'leave_ticket', ticket_id: ticketId })); ws.close() } catch { /* WS already closed */ }
        }
      } catch (e) { console.warn('WS connection failed:', e) }
    }
  }, [ticketId])

  // Sync local fields when ticket updates (lightweight)
  useEffect(() => {
    if (ticket) {
      setSupplierNotes(ticket.supplier_notes || '')
      setTrackingCode(ticket.tracking_code || '')
      setInternalNotes(ticket.internal_notes || '')
    }
  }, [ticket?.id, ticket?.supplier_notes, ticket?.tracking_code, ticket?.internal_notes])

  // ── Secondary data: customer history (fast, needed for sidebar) ──
  useEffect(() => {
    if (!ticket?.id || loadedTicketRef.current === ticket.id) return
    loadedTicketRef.current = ticket.id

    if (ticket.customer?.id) {
      getCustomerHistory(ticket.customer.id)
        .then(r => {
          const all = Array.isArray(r.data) ? r.data : []
          setHistory(all.filter(t => t.id !== ticket.id))
          const others = all.filter(t => t.id !== ticket.id && !['merged', 'closed', 'archived', 'resolved'].includes(t.status))
          setSameCustomerTickets(others)
        })
        .catch(() => { setHistory([]); setSameCustomerTickets([]) })
    }
  }, [ticket?.id])

  // ── Lazy loads: ecommerce, copilot, media — only when their sidebar tab is opened ──
  useEffect(() => {
    if (!ticket?.id) return
    if (sidebarTab === 'orders' && ecomLoadedRef.current !== ticket.id) {
      ecomLoadedRef.current = ticket.id
      if (ticket.customer?.email) {
        setShopifyCustomerLoading(true)
        getShopifyCustomer(ticket.customer.email)
          .then(r => { if (r.data?.found && r.data?.customer) setShopifyCustomer(r.data.customer) })
          .catch(() => {})
          .finally(() => setShopifyCustomerLoading(false))
        setEcomLoading(true); setEcomError(null)
        getEcommerceOrders(ticket.customer.email)
          .then(r => {
            setShopifyOrders(r.data?.shopify_orders || [])
            setYampiOrders(r.data?.yampi_orders || [])
            setAppmaxOrders(r.data?.appmax_orders || [])
            const sources = r.data?.sources || {}
            const errors = []
            if (sources.shopify?.error) errors.push(`Shopify: ${sources.shopify.error}`)
            if (sources.yampi?.error) errors.push(`Yampi: ${sources.yampi.error}`)
            if (sources.appmax?.error) errors.push(`Appmax: ${sources.appmax.error}`)
            if (errors.length > 0) setEcomError(errors.join(' | '))
          })
          .catch((err) => {
            setShopifyOrders([]); setYampiOrders([]); setAppmaxOrders([])
            setEcomError(err.response?.data?.detail || 'Erro ao carregar pedidos')
          })
          .finally(() => setEcomLoading(false))
      }
    }
    if (sidebarTab === 'copilot' && copilotLoadedRef.current !== ticket.id) {
      copilotLoadedRef.current = ticket.id
      setCopilotLoading(true)
      getCopilotInsights(ticket.id).then(r => setCopilotData(r.data)).catch(() => {}).finally(() => setCopilotLoading(false))
    }
    if (sidebarTab === 'media' && mediaLoadedRef.current !== ticket.id) {
      mediaLoadedRef.current = ticket.id
      setMediaLoading(true)
      getMediaItems().then(r => setMediaItems(r.data || [])).catch(() => {}).finally(() => setMediaLoading(false))
      suggestMedia(ticket.id).then(r => setMediaSuggestions(r.data?.suggestions || [])).catch(() => {})
    }
  }, [sidebarTab, ticket?.id])

  // Load full customer history when toggle is switched
  const loadFullHistory = async () => {
    if (!ticket?.customer?.id) return
    setLoadingHistory(true)
    try {
      const { data } = await getCustomerFullHistory(ticket.customer.id)
      setFullHistory(data)
    } catch (e) {
      toast.error('Erro ao carregar histórico completo')
    } finally {
      setLoadingHistory(false)
    }
  }

  useEffect(() => {
    if (historyMode === 'full' && !fullHistory) loadFullHistory()
  }, [historyMode])

  useEffect(() => {
    if (!ticket?.sla_deadline) return
    const update = () => {
      const now = new Date()
      const deadline = new Date(ticket.sla_deadline)
      const diff = deadline - now
      if (diff <= 0) { setSlaCountdown('ESTOURADO'); return }
      const h = Math.floor(diff / MS_PER_HOUR)
      const m = Math.floor((diff % MS_PER_HOUR) / MS_PER_MINUTE)
      setSlaCountdown(`${h}h ${m}m`)
    }
    update()
    const interval = setInterval(update, 60_000)
    return () => clearInterval(interval)
  }, [ticket?.sla_deadline])

  // serviceTimer removed — replaced by SLA indicator

  // Keyboard shortcuts
  useEffect(() => {
    const handleGlobalKeys = (e) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
      if (e.altKey && e.key === 'r') { e.preventDefault(); handleStatusChange('resolved') }
      if (e.altKey && e.key === 'e') { e.preventDefault(); handleStatusChange('escalated') }
      if (e.altKey && e.key === 'w') { e.preventDefault(); handleStatusChange('waiting') }
      if (e.altKey && e.key === 'n') {
        e.preventDefault()
        getNextTicket().then(({ data }) => {
          if (data.ticket_id) onOpenTicket?.(data.ticket_id)
          else toast.info('Nenhum ticket pendente na fila')
        }).catch(() => {})
      }
      if (e.altKey && e.key === 's') { e.preventDefault(); handleAiSuggest() }
      if (e.altKey && e.key === 'f') { e.preventDefault(); textareaRef.current?.focus() }
    }
    window.addEventListener('keydown', handleGlobalKeys)
    return () => window.removeEventListener('keydown', handleGlobalKeys)
  }, [ticket])

  // AI proactive suggestion state
  const [aiInlineSuggestion, setAiInlineSuggestion] = useState('')
  const [aiInlineLoading, setAiInlineLoading] = useState(false)
  const aiDebounceRef = useRef(null)

  const loadTicket = async () => {
    try { const { data } = await getTicket(ticketId); setTicket(data) } catch (e) { toast.error('Falha ao carregar ticket') }
  }

  const handleAttachmentUpload = async (e) => {
    const files = Array.from(e.target.files)
    if (!files.length) return
    setUploadingAttachment(true)
    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        const { data } = await uploadAttachment(formData)
        setReplyAttachments(prev => [...prev, data])
      }
    } catch (err) {
      toast.error('Erro ao fazer upload do anexo')
    } finally {
      setUploadingAttachment(false)
      e.target.value = ''
    }
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (!files.length) return
    setUploadingAttachment(true)
    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        const { data } = await uploadAttachment(formData)
        setReplyAttachments(prev => [...prev, data])
      }
    } catch (err) {
      toast.error('Falha ao enviar anexo')
    } finally {
      setUploadingAttachment(false)
    }
  }

  const handlePaste = async (e) => {
    const items = Array.from(e.clipboardData?.items || [])
    const imageItems = items.filter(item => item.type.startsWith('image/'))
    if (!imageItems.length) return
    e.preventDefault()
    setUploadingAttachment(true)
    try {
      for (const item of imageItems) {
        const file = item.getAsFile()
        if (!file) continue
        const formData = new FormData()
        const ext = file.type.split('/')[1] || 'png'
        const name = `screenshot-${Date.now()}.${ext}`
        formData.append('file', file, name)
        const { data } = await uploadAttachment(formData)
        setReplyAttachments(prev => [...prev, data])
      }
      toast.success('Screenshot anexado')
    } catch (err) {
      toast.error('Falha ao colar imagem')
    } finally {
      setUploadingAttachment(false)
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleSend = async (scheduledAt) => {
    if (!reply.trim()) return
    setSending(true)
    try {
      // Build cc/bcc arrays from comma-separated strings
      const ccArr = replyCc ? replyCc.split(',').map(e => e.trim()).filter(Boolean) : undefined
      const bccArr = replyBcc ? replyBcc.split(',').map(e => e.trim()).filter(Boolean) : undefined

      // Meta channel with AI paused: send via Meta API
      if (isMetaChannel && !ticket.ai_auto_mode) {
        await sendMetaReply({ ticket_id: ticket.id, message: reply })
      } else {
        const payload = { body_text: reply, type: replyType }
        if (ccArr && ccArr.length) payload.cc = ccArr
        if (bccArr && bccArr.length) payload.bcc = bccArr
        if (scheduledAt) payload.scheduled_at = scheduledAt
        if (replyAttachments.length > 0) payload.attachments = replyAttachments
        await addMessage(ticketId, payload)
      }
      setReply(''); setReplyCc(''); setReplyBcc(''); setShowCcBcc(false); setShowSchedulePicker(false); setScheduleDate(''); setReplyAttachments([]); loadTicket(); onTicketUpdate?.()
      if (scheduledAt) toast.success('Mensagem programada com sucesso')
    }
    catch (e) { toast.error(e.response?.data?.detail || 'Erro ao enviar mensagem') } finally { setSending(false) }
  }

  const handlePauseAI = async () => {
    setAiPausing(true)
    try {
      await pauseTicketAI(ticket.id)
      setTicket(prev => ({ ...prev, ai_auto_mode: false }))
      toast.success('IA pausada — você pode responder manualmente')
    } catch (e) {
      toast.error('Erro ao pausar IA')
    } finally { setAiPausing(false) }
  }

  const handleResumeAI = async () => {
    setAiPausing(true)
    try {
      await resumeTicketAI(ticket.id)
      setTicket(prev => ({ ...prev, ai_auto_mode: true }))
      toast.success('IA retomada — respostas automáticas ativadas')
    } catch (e) {
      toast.error('Erro ao retomar IA')
    } finally { setAiPausing(false) }
  }

  const executeMacroActions = async (macro) => {
    if (!macro.actions?.length) return
    const updates = {}
    for (const action of macro.actions) {
      if (action.type === 'set_status') updates.status = action.value
      else if (action.type === 'set_priority') updates.priority = action.value
      else if (action.type === 'set_category') updates.category = action.value
      else if (action.type === 'add_tag') {
        const currentTags = ticket.tags ? (Array.isArray(ticket.tags) ? ticket.tags : ticket.tags.split(',').map(t => t.trim())) : []
        if (!currentTags.includes(action.value)) currentTags.push(action.value)
        updates.tags = currentTags.join(', ')
      }
      else if (action.type === 'assign_to') updates.assigned_to = action.value
    }
    if (Object.keys(updates).length > 0) {
      try { await updateTicket(ticketId, updates) } catch (e) { toast.error('Erro ao aplicar ação do macro') }
    }
  }

  // Slash command filtered macros
  const slashListRef = useRef(null)
  const filteredSlashMacros = macros.filter(m =>
    !slashFilter || m.name.toLowerCase().includes(slashFilter.toLowerCase())
  )
  useEffect(() => {
    if (slashOpen && slashListRef.current) {
      const el = slashListRef.current.children[slashIdx]
      if (el) el.scrollIntoView({ block: 'nearest' })
    }
  }, [slashIdx, slashOpen])

  const handleSlashSelect = (macro) => {
    // Remove the "/query" from the reply text
    const slashPos = reply.lastIndexOf('/')
    setReply(applyMacroVars(macro.content, ticket, user?.name))
    setSlashOpen(false); setSlashFilter(''); setSlashIdx(0)
    textareaRef.current?.focus()
    if (macro.actions?.length) executeMacroActions(macro)
    trackMacroUse(macro.id).catch(() => {})
  }

  const handleMacroClick = (macro) => {
    setReply(applyMacroVars(macro.content, ticket, user?.name)); setShowMacros(false); textareaRef.current?.focus()
    if (macro.actions?.length) executeMacroActions(macro)
    trackMacroUse(macro.id).catch(() => {})
  }

  const handleMacroSendDirect = async (macro) => {
    setSending(true)
    try {
      await addMessage(ticketId, { body_text: applyMacroVars(macro.content, ticket, user?.name), type: 'outbound' })
      if (macro.actions?.length) await executeMacroActions(macro)
      setShowMacros(false); loadTicket()
      trackMacroUse(macro.id).catch(() => {})
    }
    catch (e) { toast.error('Falha ao executar macro') } finally { setSending(false) }
  }

  const handleStatusChange = async (status) => {
    try { await updateTicket(ticketId, { status }); loadTicket(); onTicketUpdate?.() }
    catch (e) { toast.error(e.response?.data?.detail || 'Erro ao atualizar status') }
  }
  const handleAssign = async (agentId) => {
    try { await updateTicket(ticketId, { assigned_to: agentId || null }); loadTicket(); onTicketUpdate?.() }
    catch (e) { toast.error(e.response?.data?.detail || 'Erro ao atribuir agente') }
  }

  const _isCreditsError = (e) => e?.response?.status === 402 || e?.response?.data?.error === 'credits_exhausted' || e?.response?.data?.credits_exhausted

  const handleAiTriage = async () => {
    setAiLoading(true)
    try { await triageTicket(ticketId); loadTicket() }
    catch (e) { toast.error(_isCreditsError(e) ? 'Creditos IA esgotados. Recarregue em console.anthropic.com' : 'Erro na triagem IA') }
    finally { setAiLoading(false) }
  }

  const handleAiSuggest = async () => {
    setAiLoading(true); setAiSuggestion(null)
    try { const { data } = await suggestReply(ticketId); setAiSuggestion(data.suggestion) }
    catch (e) { toast.error(_isCreditsError(e) ? 'Creditos IA esgotados. Recarregue em console.anthropic.com' : 'Erro ao gerar sugestão') }
    finally { setAiLoading(false) }
  }

  const handleSaveSupplierNotes = async () => {
    try { await updateSupplierNotes(ticketId, { supplier_notes: supplierNotes }); loadTicket(); toast.success('Notas salvas com sucesso') } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao salvar notas') }
  }

  const handleSaveTracking = async () => {
    try { await updateTracking(ticketId, { tracking_code: trackingCode }); loadTicket(); toast.success('Rastreio salvo') } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao salvar rastreio') }
  }

  const handleBlacklist = async () => {
    if (!ticket?.customer?.id) return
    const reason = prompt('Motivo para adicionar à blacklist:')
    if (!reason) return
    try { await blacklistCustomer(ticket.customer.id, { reason }); loadTicket() } catch (e) { toast.error(e.response?.data?.detail || 'Erro') }
  }

  const handleUnblacklist = async () => {
    if (!ticket?.customer?.id) return
    try { await unblacklistCustomer(ticket.customer.id); loadTicket() } catch (e) { toast.error(e.response?.data?.detail || 'Erro') }
  }

  // Merge ticket search (debounced)
  useEffect(() => {
    if (!mergeSearch || mergeSearch.length < 2) { setMergeResults([]); return }
    const timer = setTimeout(async () => {
      try {
        const { data } = await getTickets({ search: mergeSearch, limit: 10 })
        setMergeResults(data.tickets || [])
      } catch (e) { console.warn('Merge search failed', e) }
    }, 300)
    return () => clearTimeout(timer)
  }, [mergeSearch])

  // Merge customer search (debounced)
  useEffect(() => {
    if (!mergeCustomerSearch || mergeCustomerSearch.length < 2) { setMergeCustomerResults([]); return }
    const timer = setTimeout(async () => {
      try {
        const { data } = await searchCustomers(mergeCustomerSearch)
        setMergeCustomerResults(data || [])
      } catch (e) { console.warn('Customer search failed', e) }
    }, 300)
    return () => clearTimeout(timer)
  }, [mergeCustomerSearch])

  const handleMergeTicket = async (targetId) => {
    try {
      await mergeTickets({ source_ticket_id: ticket.id, target_ticket_id: targetId })
      toast.success('Tickets mesclados com sucesso!')
      setShowMergeModal(false)
      onTicketUpdate?.()
      onOpenTicket(targetId)
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao mesclar tickets')
    }
  }

  const handleBatchMerge = async () => {
    const sourceIds = Object.entries(selectedMergeSources).filter(([, v]) => v).map(([k]) => k)
    if (!sourceIds.length) { toast.error('Selecione ao menos um ticket'); return }
    setMergingBatch(true)
    try {
      await mergeTickets({ source_ticket_ids: sourceIds, target_ticket_id: ticket.id })
      toast.success(`${sourceIds.length} ticket(s) mesclados com sucesso!`)
      setShowMergeModal(false)
      setSelectedMergeSources({})
      setSameCustomerTickets(prev => prev.filter(t => !sourceIds.includes(t.id)))
      loadedTicketRef.current = null  // force customer history reload
      setFullHistory(null)  // force full history reload after merge
      loadTicket()
      onTicketUpdate?.()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao mesclar tickets')
    } finally {
      setMergingBatch(false)
    }
  }

  const openMergeModal = async () => {
    setMergeSearch('')
    setMergeResults([])
    setSelectedMergeSources({})
    setShowMergeModal(true)
    // Fetch other tickets from same customer
    if (ticket?.customer?.id) {
      try {
        const { data } = await getCustomerHistory(ticket.customer.id)
        const all = Array.isArray(data) ? data : []
        const others = all.filter(t => t.id !== ticket.id && !['merged', 'closed', 'archived'].includes(t.status))
        setSameCustomerTickets(others)
        const preSelected = {}
        others.forEach(t => { preSelected[t.id] = true })
        setSelectedMergeSources(preSelected)
      } catch { setSameCustomerTickets([]) }
    }
  }

  const handleMergeCustomer = async (targetId) => {
    try {
      await mergeCustomers({ source_customer_id: ticket.customer.id, target_customer_id: targetId })
      toast.success('Clientes mesclados com sucesso!')
      setShowMergeCustomerModal(false)
      loadTicket()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao mesclar clientes')
    }
  }

  const handleUnmergeTicket = async () => {
    if (!confirm('Tem certeza que deseja desfazer o merge deste ticket?')) return
    try {
      const { data } = await unmergeTicket(ticket.id)
      toast.success(data.message || 'Merge desfeito!')
      loadTicket()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao desfazer merge')
    }
  }

  const handleUnmergeCustomer = async (customerId) => {
    if (!confirm('Tem certeza que deseja desfazer o merge deste cliente?')) return
    try {
      const { data } = await unmergeCustomer(customerId)
      toast.success(data.message || 'Merge de cliente desfeito!')
      loadTicket()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao desfazer merge de cliente')
    }
  }

  const handleKeyDown = (e) => {
    // Slash command navigation
    if (slashOpen) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setSlashIdx(i => Math.min(i + 1, filteredSlashMacros.length - 1)) }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setSlashIdx(i => Math.max(i - 1, 0)) }
      else if (e.key === 'Enter' && filteredSlashMacros.length > 0) { e.preventDefault(); handleSlashSelect(filteredSlashMacros[slashIdx]) }
      else if (e.key === 'Escape') { e.preventDefault(); setSlashOpen(false); setSlashFilter(''); setSlashIdx(0) }
      else if (e.key === 'Tab' && filteredSlashMacros.length > 0) { e.preventDefault(); handleSlashSelect(filteredSlashMacros[slashIdx]) }
      return
    }
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleSend() }
    // Tab to accept AI inline suggestion
    if (e.key === 'Tab' && aiInlineSuggestion) {
      e.preventDefault()
      setReply(prev => prev + aiInlineSuggestion)
      setAiInlineSuggestion('')
    }
    // Escape to dismiss suggestion
    if (e.key === 'Escape' && aiInlineSuggestion) {
      setAiInlineSuggestion('')
    }
  }

  // AI proactive: debounce suggest while typing
  const handleReplyChange = (e) => {
    const val = e.target.value
    setReply(val)
    setAiInlineSuggestion('')

    // Slash command detection: "/" at start or after newline/space
    const slashMatch = val.match(/(?:^|\s)\/([\w\sÀ-ú]*)$/)
    if (slashMatch && macros.length > 0) {
      setSlashOpen(true)
      setSlashFilter(slashMatch[1] || '')
      setSlashIdx(0)
    } else {
      setSlashOpen(false)
      setSlashFilter('')
    }

    if (aiDebounceRef.current) clearTimeout(aiDebounceRef.current)

    // Only suggest if user typed at least 15 chars and not empty
    if (val.trim().length >= 15 && replyType === 'outbound') {
      aiDebounceRef.current = setTimeout(async () => {
        try {
          setAiInlineLoading(true)
          const { data } = await suggestReply(ticketId, val)
          if (data.suggestion) {
            // Show only the continuation (what comes after what user already typed)
            const suggestion = data.suggestion
            if (suggestion.toLowerCase().startsWith(val.toLowerCase())) {
              setAiInlineSuggestion(suggestion.slice(val.length))
            } else {
              // Show full suggestion as completion hint
              setAiInlineSuggestion(suggestion.slice(0, 120))
            }
          }
        } catch (e) { console.warn('AI suggestion failed:', e) }
        finally { setAiInlineLoading(false) }
      }, 1500) // 1.5s debounce
    }
  }

  if (!ticket) return <div className="p-6 text-[var(--text-secondary)]">Carregando...</div>

  const slaBreached = ticket.sla_breached || slaCountdown === 'ESTOURADO'
  const slaUrgent = !slaBreached && ticket.sla_deadline && (new Date(ticket.sla_deadline) - new Date()) < MS_PER_HOUR

  return (
    <div className="flex h-full">
      {/* ═══ MAIN CONTENT ═══ */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-4">
            <button onClick={onBack} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition">
              <i className="fas fa-arrow-left" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[var(--text-primary)] font-semibold">#{ticket.number}</span>
                <span className="text-[var(--text-primary)]">{ticket.subject}</span>
                {ticket.status === 'merged' && (
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium" style={{ background: 'rgba(139,92,246,0.15)', color: '#8b5cf6' }}>
                    <i className="fas fa-code-branch" />Mesclado
                    <button onClick={handleUnmergeTicket} className="ml-1 hover:text-red-400 transition" title="Desfazer merge">
                      <i className="fas fa-undo text-[10px]" />
                    </button>
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-0.5">
                <span className="text-[var(--text-secondary)] text-xs">{ticket.customer?.name}</span>
                <span className="text-[var(--text-tertiary)] text-xs">{ticket.customer?.email}</span>
                {ticket.legal_risk && <span className="text-red-400 text-xs"><i className="fas fa-exclamation-triangle mr-1" />Jurídico</span>}
                {ticket.customer?.is_blacklisted && <span className="text-red-400 text-xs font-bold"><i className="fas fa-ban mr-1" />Blacklist</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`px-2.5 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 ${
              slaBreached ? 'bg-red-500/20 text-red-400 animate-pulse' :
              slaUrgent ? 'bg-yellow-500/20 text-yellow-400 animate-pulse' :
              'bg-emerald-500/15 text-emerald-400'
            }`}>
              <i className={`fas ${slaBreached ? 'fa-exclamation-circle' : slaUrgent ? 'fa-exclamation-triangle' : 'fa-check-circle'}`} />
              <span className="font-mono">{slaBreached ? 'SLA Estourado' : slaCountdown || 'Sem SLA'}</span>
            </div>
            <button onClick={async () => {
              try { const { data } = await getNextTicket(); if (data.ticket_id && data.ticket_id !== ticketId) onOpenTicket?.(data.ticket_id); else toast.info('Nenhum ticket pendente na fila') } catch { toast.error('Erro ao buscar próximo ticket') }
            }} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] p-1.5 rounded transition" title="Próximo ticket (Alt+N)">
              <i className="fas fa-forward" />
            </button>
          </div>
        </div>

        {/* ── Compact info bar (status + priority + tags inline) ── */}
        <div className="flex items-center gap-2 px-6 py-1.5 border-b border-[var(--border-color)] bg-[var(--bg-secondary)]/30 text-xs">
          <span className={`px-2 py-0.5 rounded-full font-medium ${
            ticket.priority === 'urgent' ? 'bg-red-500/15 text-red-400' :
            ticket.priority === 'high' ? 'bg-orange-500/15 text-orange-400' :
            'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
          }`}>{PRIORITY_LABELS[ticket.priority] || ticket.priority}</span>
          <span className="px-2 py-0.5 rounded-full bg-[var(--bg-tertiary)] text-[var(--text-secondary)]">{STATUS_LABELS[ticket.status]}</span>
          {ticket.category && <span className="px-2 py-0.5 rounded-full bg-[var(--bg-tertiary)] text-[var(--text-secondary)]">{CATEGORY_LABELS[ticket.category] || ticket.category}</span>}
          {ticket.assigned_to && agents.find(a => a.id === ticket.assigned_to) && (
            <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400">
              <i className="fas fa-user mr-1 text-[9px]" />{agents.find(a => a.id === ticket.assigned_to)?.name}
            </span>
          )}
          {(ticket.tags || []).slice(0, 2).map(tag => (
            <span key={tag} className={`px-1.5 py-0.5 rounded-full text-[10px] ${TAG_COLORS[tag] || 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'}`}>
              {TAG_LABELS[tag] || tag}
            </span>
          ))}
          {(ticket.tags || []).length > 2 && <span className="text-[10px] text-[var(--text-tertiary)]">+{ticket.tags.length - 2}</span>}
          <div className="flex-1" />
          {ticket.protocol && (
            <span className="text-indigo-400 text-[10px]"><i className="fas fa-shield-alt mr-0.5" />{ticket.protocol}{ticket.protocol_sent && <i className="fas fa-check-circle ml-0.5 text-emerald-400" />}</span>
          )}
          {ticket.sentiment && <span className="text-purple-400 text-[10px]"><i className="fas fa-face-smile mr-0.5" />{SENTIMENT_LABELS[ticket.sentiment] || ticket.sentiment}</span>}
        </div>

        {/* ── Merge candidates (collapsed badge) ── */}
        {sameCustomerTickets.length > 0 && (
          <div className="border-b border-amber-500/20 bg-amber-500/5">
            <button onClick={() => setShowMergeCandidates?.(prev => !prev)}
              className="w-full flex items-center justify-between px-6 py-1.5 hover:bg-amber-500/10 transition">
              <div className="flex items-center gap-2">
                <i className="fas fa-compress-arrows-alt text-amber-400 text-[10px]" />
                <span className="text-amber-400 text-xs font-semibold">{sameCustomerTickets.length} ticket(s) para mesclar</span>
              </div>
              <i className={`fas fa-chevron-${showMergeCandidates ? 'up' : 'down'} text-amber-400 text-[10px]`} />
            </button>
            {showMergeCandidates && (
              <div className="px-6 pb-2">
                <div className="flex items-center gap-2 mb-1.5">
                  {Object.values(selectedMergeSources).some(v => v) && (
                    <button onClick={handleBatchMerge} disabled={mergingBatch}
                      className="px-3 py-1 rounded-lg text-[11px] font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition">
                      {mergingBatch ? <><i className="fas fa-spinner animate-spin mr-1" />Mesclando...</> :
                        <><i className="fas fa-compress-arrows-alt mr-1" />Mesclar {Object.values(selectedMergeSources).filter(v => v).length}</>}
                    </button>
                  )}
                  <button onClick={() => {
                    const allSelected = sameCustomerTickets.every(t => selectedMergeSources[t.id])
                    const next = {}
                    sameCustomerTickets.forEach(t => { next[t.id] = !allSelected })
                    setSelectedMergeSources(next)
                  }} className="text-amber-400 hover:text-amber-300 text-[10px] underline ml-auto">
                    {sameCustomerTickets.every(t => selectedMergeSources[t.id]) ? 'Desmarcar' : 'Selecionar todos'}
                  </button>
                </div>
                <div className="flex gap-2 overflow-x-auto">
                  {sameCustomerTickets.map(t => (
                    <label key={t.id}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer transition shrink-0 border ${
                        selectedMergeSources[t.id] ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-[var(--bg-secondary)] border-[var(--border-color)] hover:border-amber-500/30'
                      }`}>
                      <input type="checkbox" checked={!!selectedMergeSources[t.id]}
                        onChange={e => setSelectedMergeSources(prev => ({ ...prev, [t.id]: e.target.checked }))}
                        className="accent-indigo-500 w-3 h-3" />
                      <span className="font-mono text-[11px] text-amber-400">#{t.number}</span>
                      <span className="text-[11px] text-[var(--text-primary)] max-w-[180px] truncate">{t.subject}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Collision detection banner */}
        {otherViewers.length > 0 && (
          <div className="flex items-center gap-2 px-6 py-1.5 bg-yellow-500/15 border-b border-yellow-500/30">
            <i className="fas fa-eye text-yellow-400 text-xs animate-pulse" />
            <span className="text-yellow-400 text-xs font-medium">
              {otherViewers.map(v => v.name).join(', ')} {otherViewers.length === 1 ? 'está' : 'estão'} vendo este ticket
            </span>
          </div>
        )}

        {/* AI Summary - inline compact (only if exists) */}
        {ticket.ai_summary && (
          <div className="px-6 py-1 border-b border-[var(--border-color)] flex items-center gap-2">
            <i className="fas fa-brain text-orange-400 text-[10px]" />
            <p className="text-[var(--text-tertiary)] text-[11px] flex-1 truncate">{ticket.ai_summary}</p>
          </div>
        )}

        {/* Content tabs */}
        <div className="flex gap-0 border-b border-[var(--border-color)]">
          {[
            { id: 'messages', label: 'Mensagens', icon: 'fa-comments' },
            { id: 'logistics', label: 'Logística', icon: 'fa-shipping-fast' },
          ].map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-2.5 text-xs font-medium transition border-b-2 ${
                activeTab === tab.id ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}>
              <i className={`fas ${tab.icon} mr-1.5`} />{tab.label}
            </button>
          ))}
        </div>

        {/* ═══ TAB CONTENT ═══ */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'messages' && (
            <div className="flex flex-col h-full">
              {/* Meta AI Banner */}
              {isMetaChannel && (
                <div className={`flex items-center justify-between px-4 py-2.5 mx-4 mt-3 rounded-lg ${
                  ticket.ai_auto_mode
                    ? 'bg-emerald-500/10 border border-emerald-500/20'
                    : 'bg-yellow-500/10 border border-yellow-500/20'
                }`}>
                  <div className="flex items-center gap-2 text-sm">
                    <MetaBadge source={ticket.source} size="lg" showLabel />
                    {ticket.ai_auto_mode ? (
                      <span className="text-emerald-400">
                        <i className="fas fa-robot mr-1" />
                        IA respondendo automaticamente
                      </span>
                    ) : (
                      <span className="text-yellow-400">
                        <i className="fas fa-pause-circle mr-1" />
                        IA pausada — modo manual
                      </span>
                    )}
                  </div>
                  <button
                    onClick={ticket.ai_auto_mode ? handlePauseAI : handleResumeAI}
                    disabled={aiPausing}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                      ticket.ai_auto_mode
                        ? 'bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30'
                        : 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30'
                    }`}
                  >
                    {aiPausing ? (
                      <i className="fas fa-spinner fa-spin" />
                    ) : ticket.ai_auto_mode ? (
                      <><i className="fas fa-pause mr-1" />Pausar IA</>
                    ) : (
                      <><i className="fas fa-play mr-1" />Retomar IA</>
                    )}
                  </button>
                </div>
              )}
              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2.5">
                {/* History toggle — compact inline */}
                <div className="flex justify-center">
                  <button onClick={() => setHistoryMode(historyMode === 'ticket' ? 'full' : 'ticket')}
                    className="text-[10px] text-[var(--text-tertiary)] hover:text-indigo-400 transition px-2 py-0.5 rounded-full bg-[var(--bg-tertiary)] hover:bg-indigo-500/10">
                    <i className={`fas ${historyMode === 'full' ? 'fa-compress' : 'fa-history'} mr-1`} />
                    {historyMode === 'full' ? 'Só este ticket' : 'Histórico completo'}
                  </button>
                </div>
                {historyMode === 'full' ? (
                  loadingHistory || !fullHistory ? (
                    <div className="flex items-center justify-center py-8">
                      <i className="fas fa-spinner fa-spin text-xl" style={{ color: 'var(--accent)' }} />
                    </div>
                  ) : (
                    (() => {
                      let lastTicketId = null
                      return fullHistory.messages.map((msg, idx) => {
                        const showSeparator = msg.ticket_id !== lastTicketId
                        lastTicketId = msg.ticket_id
                        const isCurrentTicket = msg.ticket_id === ticket.id
                        return (
                          <React.Fragment key={msg.id}>
                            {showSeparator && (
                              <div className="flex items-center gap-2 px-4 py-2 my-2">
                                <div className="flex-1 h-px" style={{ background: 'var(--border-color)' }} />
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap"
                                  style={{
                                    background: isCurrentTicket ? 'rgba(253,210,0,0.15)' : 'var(--bg-tertiary)',
                                    color: isCurrentTicket ? 'var(--accent)' : 'var(--text-tertiary)',
                                  }}>
                                  #{msg.ticket_number} · {msg.ticket_subject}
                                </span>
                                <div className="flex-1 h-px" style={{ background: 'var(--border-color)' }} />
                              </div>
                            )}
                            <div className={`flex ${msg.type === 'outbound' ? 'justify-end' : 'justify-start'} px-4 py-1`}>
                              <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${msg.type === 'internal_note' ? 'border-l-4' : ''}`}
                                style={{
                                  background: msg.type === 'outbound' ? 'rgba(99,102,241,0.15)' :
                                    msg.type === 'internal_note' ? 'rgba(34,197,94,0.2)' : 'var(--bg-tertiary)',
                                  color: 'var(--text-primary)',
                                  borderColor: msg.type === 'internal_note' ? '#22c55e' : undefined,
                                  opacity: isCurrentTicket ? 1 : 0.7,
                                }}>
                                <div className="flex items-center gap-2 mb-0.5">
                                  <span className="text-[11px] font-semibold" style={{
                                    color: msg.type === 'outbound' ? '#818cf8' :
                                      msg.type === 'internal_note' ? '#22c55e' : 'var(--text-secondary)',
                                  }}>
                                    {msg.type === 'internal_note' && <i className="fas fa-sticky-note mr-1" />}
                                    {msg.sender_name || msg.sender_email || 'Sistema'}
                                  </span>
                                  {msg.is_scheduled && (
                                    <span className="text-[10px] bg-purple-500/15 text-purple-400 px-1.5 py-0.5 rounded flex items-center gap-1">
                                      <i className="fas fa-clock" />Programado {msg.scheduled_at ? new Date(msg.scheduled_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''}
                                    </span>
                                  )}
                                  <span className="text-[10px]" style={{
                                    color: 'var(--text-tertiary)',
                                  }}>
                                    {new Date(msg.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                                  </span>
                                </div>
                                {msg.cc && <div className="text-[10px] mb-0.5" style={{ color: msg.type === 'outbound' ? 'rgba(255,255,255,0.5)' : 'var(--text-tertiary)' }}>CC: {msg.cc}</div>}
                                <div className="text-sm whitespace-pre-wrap break-words">{msg.body_text}</div>
                                {msg.attachments && Array.isArray(msg.attachments) && msg.attachments.length > 0 && (
                                  <div className="mt-2 flex flex-wrap gap-1.5">
                                    {msg.attachments.map((att, i) => (
                                      <a key={i} href={att.drive_url} target="_blank" rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1.5 bg-[var(--bg-tertiary)] hover:bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs px-2.5 py-1.5 rounded-lg transition border border-[var(--border-color)]">
                                        <i className="fas fa-paperclip text-[10px]" />
                                        <span className="max-w-[200px] truncate">{att.name}</span>
                                      </a>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </React.Fragment>
                        )
                      })
                    })()
                  )
                ) : (
                  (() => {
                    const msgs = ticket.messages || []
                    // Find last inbound message index for "NOVO" badge
                    let lastInboundIdx = -1
                    for (let i = msgs.length - 1; i >= 0; i--) {
                      if (msgs[i].type === 'inbound') { lastInboundIdx = i; break }
                    }
                    let prevOriginal = null
                    return msgs.map((msg, idx) => {
                      // Show merge separator when message came from a different ticket
                      const fromMerge = msg.original_ticket_id && msg.original_ticket_id !== ticket.id
                      const showMergeSep = fromMerge && msg.original_ticket_id !== prevOriginal
                      prevOriginal = fromMerge ? msg.original_ticket_id : null
                      return (
                        <React.Fragment key={msg.id}>
                          {showMergeSep && (
                            <div className="flex items-center gap-2 my-2">
                              <div className="flex-1 h-px" style={{ background: 'rgba(139,92,246,0.3)' }} />
                              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full" style={{ background: 'rgba(139,92,246,0.12)', color: '#8b5cf6' }}>
                                <i className="fas fa-code-branch mr-1" />Mesclado de outro ticket
                              </span>
                              <div className="flex-1 h-px" style={{ background: 'rgba(139,92,246,0.3)' }} />
                            </div>
                          )}
                          <ChatBubble key={msg.id} msg={msg} isLast={idx === msgs.length - 1} isLastInbound={idx === lastInboundIdx && msg.type === 'inbound'} />
                        </React.Fragment>
                      )
                    })
                  })()
                )}
              </div>

              {/* AI suggestion banner (collapsed inline, only if suggestion exists) */}
              {aiSuggestion && (
                <div className="mx-4 mb-0 bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-indigo-400 text-xs"><i className="fas fa-lightbulb mr-1" />Sugestão IA:</span>
                    <button onClick={() => { setReply(aiSuggestion); setAiSuggestion(null); textareaRef.current?.focus() }}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-1 rounded text-xs transition">
                      <i className="fas fa-paste mr-1" />Usar
                    </button>
                  </div>
                  <p className="text-[var(--text-primary)] text-xs whitespace-pre-wrap max-h-24 overflow-y-auto">{aiSuggestion}</p>
                </div>
              )}

              {/* Reply box with integrated macros */}
              <div className={`px-6 py-3 border-t border-[var(--border-color)] relative ${isDragging ? 'ring-2 ring-emerald-400 ring-dashed' : ''}`} onDrop={handleDrop} onDragOver={handleDragOver} onDragLeave={handleDragLeave}>
                {isDragging && (
                  <div className="absolute inset-0 bg-emerald-500/10 border-2 border-dashed border-emerald-400 rounded-xl z-10 flex items-center justify-center pointer-events-none">
                    <span className="text-emerald-400 font-medium text-sm"><i className="fas fa-cloud-upload-alt mr-2" />Solte os arquivos aqui</span>
                  </div>
                )}
                <div className="flex items-center gap-3 mb-2">
                  <button onClick={() => setReplyType('outbound')}
                    className="text-xs px-3 py-1 rounded-full transition"
                    style={replyType === 'outbound' ? { background: '#6366f1', color: '#fff' } : { color: 'var(--text-secondary)' }}>
                    <i className="fas fa-reply mr-1" />Responder
                  </button>
                  <button onClick={() => setReplyType('internal_note')}
                    className={`text-xs px-3 py-1 rounded-full transition ${replyType === 'internal_note' ? 'bg-yellow-600 text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}>
                    <i className="fas fa-sticky-note mr-1" />Nota
                  </button>
                  {replyType === 'outbound' && ticket?.source === 'gmail' && (
                    <button onClick={() => setShowCcBcc(!showCcBcc)}
                      className={`text-xs px-2.5 py-1 rounded-full transition ${showCcBcc ? 'bg-blue-600/20 text-blue-400' : 'text-[var(--text-tertiary)] hover:text-blue-400 hover:bg-[var(--bg-tertiary)]'}`}>
                      <i className="fas fa-at mr-1" />CC/CCO
                    </button>
                  )}
                  <button onClick={() => attachmentInputRef.current?.click()}
                    disabled={uploadingAttachment}
                    className={`text-xs px-2.5 py-1 rounded-full transition ${replyAttachments.length > 0 ? 'bg-emerald-600/20 text-emerald-400' : 'text-[var(--text-tertiary)] hover:text-emerald-400 hover:bg-[var(--bg-tertiary)]'}`}>
                    <i className={`fas ${uploadingAttachment ? 'fa-spinner animate-spin' : 'fa-paperclip'} mr-1`} />
                    {replyAttachments.length > 0 ? `${replyAttachments.length} anexo${replyAttachments.length > 1 ? 's' : ''}` : 'Anexar'}
                  </button>
                  <input ref={attachmentInputRef} type="file" multiple className="hidden" onChange={handleAttachmentUpload} />
                  <div className="ml-auto flex items-center gap-2">
                    {/* Macros dropdown */}
                    {macros.length > 0 && (
                      <div className="relative">
                        <button onClick={() => setShowMacros(!showMacros)}
                          className={`text-xs px-2.5 py-1 rounded-full transition flex items-center gap-1 ${showMacros ? 'bg-yellow-600/20 text-yellow-400' : 'text-[var(--text-secondary)] hover:text-yellow-400 hover:bg-[var(--bg-tertiary)]'}`}>
                          <i className="fas fa-bolt" />Macros
                          <i className={`fas fa-chevron-${showMacros ? 'up' : 'down'} text-[8px] ml-0.5`} />
                        </button>
                        {showMacros && (
                          <div className="absolute bottom-full mb-1 right-0 w-72 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl shadow-xl z-50 overflow-hidden">
                            <div className="p-2 border-b border-[var(--border-color)]">
                              <p className="text-[var(--text-tertiary)] text-[10px] uppercase tracking-wider px-2">Clique p/ inserir · Duplo-clique p/ enviar</p>
                            </div>
                            <div className="max-h-48 overflow-y-auto p-1.5">
                              {macros.map(macro => (
                                <button key={macro.id} onClick={() => handleMacroClick(macro)}
                                  onDoubleClick={() => handleMacroSendDirect(macro)}
                                  className="w-full bg-transparent hover:bg-[var(--bg-tertiary)] rounded-lg p-2 text-left transition flex items-start gap-2 group">
                                  <i className={`fas fa-bolt mt-0.5 text-xs ${macro.actions?.length ? 'text-orange-400' : 'text-yellow-400'}`} />
                                  <div className="flex-1 min-w-0">
                                    <p className="text-[var(--text-primary)] text-xs font-medium flex items-center gap-1">
                                      {macro.name}
                                      {macro.actions?.length > 0 && <i className="fas fa-cog text-[9px] text-[var(--text-tertiary)]" title={`Ações: ${macro.actions.map(a => a.type).join(', ')}`} />}
                                    </p>
                                    <p className="text-[var(--text-tertiary)] text-[11px] line-clamp-1 mt-0.5">{applyMacroVars(macro.content, ticket, user?.name).substring(0, 80)}</p>
                                  </div>
                                  <i className="fas fa-arrow-right text-[10px] text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 mt-1 transition" />
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    <span className="text-[var(--text-tertiary)] text-xs">Ctrl+Enter</span>
                  </div>
                </div>
                {/* CC/BCC fields */}
                {showCcBcc && replyType === 'outbound' && ticket?.source === 'gmail' && (
                  <div className="mb-2 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <label className="text-[var(--text-tertiary)] text-xs w-8 shrink-0">CC</label>
                      <input
                        type="text" value={replyCc} onChange={e => setReplyCc(e.target.value)}
                        placeholder="email1@exemplo.com, email2@exemplo.com"
                        className="flex-1 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-[var(--text-primary)] text-xs focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-[var(--text-tertiary)] text-xs w-8 shrink-0">CCO</label>
                      <input
                        type="text" value={replyBcc} onChange={e => setReplyBcc(e.target.value)}
                        placeholder="email1@exemplo.com, email2@exemplo.com"
                        className="flex-1 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-[var(--text-primary)] text-xs focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>
                )}
                {replyAttachments.length > 0 && (
                  <div className="mb-2 flex flex-wrap gap-1.5">
                    {replyAttachments.map((att, i) => (
                      <span key={i} className="inline-flex items-center gap-1.5 bg-emerald-500/10 text-emerald-400 text-xs px-2.5 py-1 rounded-lg">
                        <i className="fas fa-paperclip text-[10px]" />
                        <span className="max-w-[150px] truncate">{att.name}</span>
                        <span className="text-emerald-600 text-[10px]">({(att.size / 1024).toFixed(0)}KB)</span>
                        <button onClick={() => setReplyAttachments(prev => prev.filter((_, j) => j !== i))}
                          className="hover:text-red-400 transition ml-0.5">
                          <i className="fas fa-times text-[10px]" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <textarea ref={textareaRef} value={reply} onChange={handleReplyChange} onKeyDown={handleKeyDown} onPaste={handlePaste} rows={5}
                      spellCheck={true} lang="pt-BR"
                      placeholder={replyType === 'internal_note' ? 'Nota interna...' : 'Escreva sua resposta... (/ para macros)'}
                      className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl px-4 py-2.5 text-[var(--text-primary)] text-sm resize-y focus:outline-none focus:border-indigo-500" style={{ minHeight: '100px' }} />
                    {/* Slash command inline dropdown */}
                    {slashOpen && filteredSlashMacros.length > 0 && (
                      <div className="absolute bottom-full mb-1 left-0 w-80 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl shadow-xl z-50 overflow-hidden">
                        <div className="px-3 py-1.5 border-b border-[var(--border-color)] flex items-center gap-2">
                          <i className="fas fa-bolt text-yellow-400 text-xs" />
                          <span className="text-[var(--text-tertiary)] text-[10px] uppercase tracking-wider">Macros</span>
                          {slashFilter && <span className="text-indigo-400 text-[10px]">"{slashFilter}"</span>}
                          <span className="ml-auto text-[var(--text-tertiary)] text-[10px]">↑↓ navegar · Enter selecionar</span>
                        </div>
                        <div ref={slashListRef} className="max-h-52 overflow-y-auto p-1">
                          {filteredSlashMacros.map((macro, i) => (
                            <button key={macro.id} onClick={() => handleSlashSelect(macro)}
                              className={`w-full bg-transparent rounded-lg px-3 py-2 text-left transition flex items-start gap-2.5 ${
                                i === slashIdx ? 'bg-indigo-500/15 ring-1 ring-indigo-500/30' : 'hover:bg-[var(--bg-tertiary)]'
                              }`}>
                              <i className={`fas fa-bolt mt-0.5 text-xs ${macro.actions?.length ? 'text-orange-400' : 'text-yellow-400'}`} />
                              <div className="flex-1 min-w-0">
                                <p className="text-[var(--text-primary)] text-xs font-medium flex items-center gap-1.5">
                                  {macro.name}
                                  {macro.actions?.length > 0 && (
                                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400">+ ações</span>
                                  )}
                                </p>
                                <p className="text-[var(--text-tertiary)] text-[11px] line-clamp-1 mt-0.5">{applyMacroVars(macro.content, ticket, user?.name).substring(0, 90)}</p>
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    {slashOpen && filteredSlashMacros.length === 0 && slashFilter && (
                      <div className="absolute bottom-full mb-1 left-0 w-64 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl shadow-xl z-50 p-3 text-center">
                        <p className="text-[var(--text-tertiary)] text-xs"><i className="fas fa-search mr-1.5" />Nenhum macro encontrado para "{slashFilter}"</p>
                      </div>
                    )}
                    {/* AI inline suggestion overlay */}
                    {aiInlineSuggestion && (
                      <div className="absolute bottom-1 left-4 right-16 flex items-center gap-2 pointer-events-none">
                        <span className="text-[var(--text-tertiary)] text-xs italic truncate">{aiInlineSuggestion.slice(0, 80)}...</span>
                        <span className="text-indigo-400 text-xs font-medium shrink-0 pointer-events-auto bg-[var(--bg-secondary)] px-1.5 py-0.5 rounded"
                          onClick={() => { setReply(prev => prev + aiInlineSuggestion); setAiInlineSuggestion('') }}
                          style={{ cursor: 'pointer' }}>Tab ↵</span>
                      </div>
                    )}
                    {aiInlineLoading && (
                      <div className="absolute bottom-1 right-16 text-orange-400 text-xs">
                        <i className="fas fa-spinner animate-spin" />
                      </div>
                    )}
                  </div>
                  {/* Send button with dropdown */}
                  <div className="relative">
                    <div className="flex">
                      <button onClick={() => handleSend()} disabled={!reply.trim() || sending}
                        className="px-4 py-2.5 rounded-l-xl text-xs font-medium text-white transition disabled:opacity-40"
                        style={{ background: replyType === 'internal_note' ? '#ca8a04' : '#6366f1' }}>
                        <i className="fas fa-paper-plane mr-1.5" />Enviar
                      </button>
                      <button onClick={() => setShowSendMenu(!showSendMenu)}
                        className="px-2 py-2.5 rounded-r-xl text-xs text-white transition border-l border-white/20"
                        style={{ background: replyType === 'internal_note' ? '#ca8a04' : '#6366f1' }}>
                        <i className={`fas fa-chevron-${showSendMenu ? 'up' : 'down'} text-[9px]`} />
                      </button>
                    </div>
                    {showSendMenu && (
                      <div className="absolute bottom-full mb-1 right-0 w-56 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl shadow-xl z-50 overflow-hidden">
                        <div className="p-1.5">
                          {ticket.status !== 'resolved' && (
                            <button onClick={async () => { setShowSendMenu(false); if (reply.trim()) await handleSend(); await handleStatusChange('resolved') }}
                              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-left hover:bg-emerald-500/10 text-emerald-400 transition">
                              <i className="fas fa-check-circle w-4" />Enviar e Resolver
                            </button>
                          )}
                          {ticket.status === 'open' && (
                            <button onClick={() => { setShowSendMenu(false); if (reply.trim()) handleSend().then(() => handleStatusChange('waiting')); else handleStatusChange('waiting') }}
                              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-left hover:bg-orange-500/10 text-orange-400 transition">
                              <i className="fas fa-hourglass-half w-4" />Enviar e Aguardar Cliente
                            </button>
                          )}
                          <div className="border-t border-[var(--border-color)] my-1" />
                          <button onClick={() => { setShowSendMenu(false); handleStatusChange('resolved') }}
                            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-left hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] transition">
                            <i className="fas fa-check w-4" />Resolver sem enviar
                          </button>
                          {replyType === 'outbound' && ticket?.source === 'gmail' && (
                            <>
                              <div className="border-t border-[var(--border-color)] my-1" />
                              <button onClick={() => { setShowSendMenu(false); setShowSchedulePicker(!showSchedulePicker) }}
                                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-left hover:bg-purple-500/10 text-purple-400 transition">
                                <i className="fas fa-clock w-4" />Programar envio
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                {/* Schedule picker */}
                {showSchedulePicker && replyType === 'outbound' && (
                  <div className="flex items-center gap-2 mt-2 p-2 bg-purple-500/10 rounded-lg border border-purple-500/20">
                    <i className="fas fa-clock text-purple-400 text-xs" />
                    <span className="text-purple-300 text-xs">Programar para:</span>
                    <input
                      type="datetime-local"
                      value={scheduleDate}
                      onChange={e => setScheduleDate(e.target.value)}
                      min={new Date().toISOString().slice(0, 16)}
                      className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-2 py-1 text-[var(--text-primary)] text-xs focus:outline-none focus:border-purple-500"
                    />
                    <button
                      onClick={() => {
                        if (!scheduleDate || !reply.trim()) return
                        handleSend(new Date(scheduleDate).toISOString())
                      }}
                      disabled={!scheduleDate || !reply.trim() || sending}
                      className="bg-purple-600 hover:bg-purple-500 text-white px-3 py-1 rounded-lg text-xs font-medium transition disabled:opacity-40"
                    >
                      <i className="fas fa-paper-plane mr-1" />Programar
                    </button>
                    <button onClick={() => { setShowSchedulePicker(false); setScheduleDate('') }}
                      className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] text-xs transition">
                      <i className="fas fa-times" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'logistics' && (
            <div className="p-6 space-y-5">
              {/* ── Rastreamento ── */}
              <div>
                <h3 className="text-[var(--text-primary)] text-sm font-medium mb-3"><i className="fas fa-map-marker-alt mr-2 text-emerald-400" />Rastreamento</h3>
                <div className="flex gap-2 mb-3">
                  <input value={trackingCode} onChange={(e) => setTrackingCode(e.target.value)}
                    placeholder="Código de rastreio (ex: LP00123456789BR)"
                    className="flex-1 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm font-mono focus:outline-none focus:border-indigo-500" />
                  <button onClick={handleSaveTracking}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm transition">
                    <i className="fas fa-save mr-1" />Salvar
                  </button>
                </div>

              {ticket.tracking_code && (
                <div className="space-y-3">
                  {/* Status card */}
                  <div className={`rounded-xl p-4 ${ticket.tracking_data?.delivered ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-[var(--bg-secondary)] border border-[var(--border-color)]'}`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-[var(--text-primary)] text-sm font-mono font-bold">{ticket.tracking_code}</span>
                        <button onClick={() => { navigator.clipboard.writeText(ticket.tracking_code) }}
                          className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] text-xs" title="Copiar"><i className="fas fa-copy" /></button>
                      </div>
                      <button onClick={async () => {
                        try { const { data } = await refreshTracking(ticket.id); if (data.status) setTicket(prev => ({ ...prev, tracking_status: data.status, tracking_data: data })) } catch { toast.error('Erro ao atualizar rastreio') }
                      }} className="text-blue-400 hover:text-blue-300 text-xs font-medium"><i className="fas fa-sync-alt mr-1" />Atualizar</button>
                    </div>

                    {/* Status principal */}
                    <div className="flex items-center gap-2 mb-2">
                      {ticket.tracking_data?.delivered ? (
                        <span className="inline-flex items-center gap-1 bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded-full text-xs font-bold">
                          <i className="fas fa-check-circle" /> Entregue
                        </span>
                      ) : ticket.tracking_data?.main_status === 10 ? (
                        <span className="inline-flex items-center gap-1 bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full text-xs font-bold">
                          <i className="fas fa-truck" /> Em trânsito
                        </span>
                      ) : ticket.tracking_data?.main_status === 40 ? (
                        <span className="inline-flex items-center gap-1 bg-orange-500/20 text-orange-400 px-2 py-1 rounded-full text-xs font-bold">
                          <i className="fas fa-undo" /> Devolvido
                        </span>
                      ) : ticket.tracking_data?.main_status === 70 ? (
                        <span className="inline-flex items-center gap-1 bg-red-500/20 text-red-400 px-2 py-1 rounded-full text-xs font-bold">
                          <i className="fas fa-exclamation-triangle" /> Falha na entrega
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 bg-gray-500/20 text-gray-400 px-2 py-1 rounded-full text-xs font-bold">
                          <i className="fas fa-clock" /> {ticket.tracking_status || 'Aguardando'}
                        </span>
                      )}
                    </div>
                    <p className="text-[var(--text-primary)] text-sm">{ticket.tracking_status || 'Aguardando atualização da transportadora'}</p>

                    {/* Info extra */}
                    <div className="flex flex-wrap gap-3 mt-3 text-xs text-[var(--text-tertiary)]">
                      {ticket.tracking_data?.carrier && ticket.tracking_data.carrier !== '17track' && (
                        <span><i className="fas fa-shipping-fast mr-1" />{ticket.tracking_data.carrier}</span>
                      )}
                      {ticket.tracking_data?.days_in_transit && (
                        <span><i className="fas fa-calendar-day mr-1" />{ticket.tracking_data.days_in_transit} dias</span>
                      )}
                      {ticket.tracking_data?.location && (
                        <span><i className="fas fa-map-pin mr-1" />{ticket.tracking_data.location}</span>
                      )}
                      {ticket.tracking_data?.last_update && (
                        <span><i className="fas fa-clock mr-1" />{new Date(ticket.tracking_data.last_update).toLocaleDateString('pt-BR')}</span>
                      )}
                    </div>
                  </div>

                  {/* Timeline de eventos */}
                  {ticket.tracking_data?.events?.length > 0 && (
                    <div className="bg-[var(--bg-secondary)] rounded-xl p-4 border border-[var(--border-color)]">
                      <p className="text-[var(--text-tertiary)] text-xs font-medium mb-3"><i className="fas fa-list-ul mr-1" />Histórico ({ticket.tracking_data.events.length} eventos)</p>
                      <div className="space-y-0 max-h-[400px] overflow-auto pr-1">
                        {ticket.tracking_data.events.map((ev, i) => {
                          const isFirst = i === 0
                          const isDelivered = ev.status?.toLowerCase()?.includes('entreg')
                          return (
                            <div key={i} className="flex gap-3">
                              {/* Timeline dot + line */}
                              <div className="flex flex-col items-center">
                                <div className={`w-3 h-3 rounded-full shrink-0 mt-1 ${isDelivered ? 'bg-emerald-400' : isFirst ? 'bg-blue-400' : 'bg-[var(--border-color)]'}`} />
                                {i < ticket.tracking_data.events.length - 1 && (
                                  <div className="w-px flex-1 bg-[var(--border-color)] my-1" />
                                )}
                              </div>
                              {/* Event content */}
                              <div className={`pb-4 ${isFirst ? '' : 'opacity-70'}`}>
                                <p className={`text-xs font-medium ${isFirst ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>{ev.status}</p>
                                <div className="flex items-center gap-2 mt-0.5 text-xs text-[var(--text-tertiary)]">
                                  {ev.date && <span>{new Date(ev.date).toLocaleDateString('pt-BR')} {new Date(ev.date).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>}
                                  {ev.location && <span>· {ev.location}</span>}
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Link 17track */}
                  {ticket.tracking_code && (
                    <a href={`https://t.17track.net/en#nums=${ticket.tracking_code}`} target="_blank" rel="noreferrer"
                      className="flex items-center justify-center gap-2 bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-xl p-3 text-xs text-blue-400 hover:text-blue-300 transition">
                      <i className="fas fa-external-link-alt" /> Ver no 17track.net
                    </a>
                  )}
                </div>
              )}

              {/* Sem código */}
              {!ticket.tracking_code && (
                <div className="text-center text-[var(--text-tertiary)] py-6">
                  <i className="fas fa-truck text-2xl mb-2 opacity-30" />
                  <p className="text-xs">Nenhum rastreio cadastrado</p>
                </div>
              )}
              </div>

              {/* ── Fornecedor ── */}
              <div>
                <h3 className="text-[var(--text-primary)] text-sm font-medium mb-3"><i className="fas fa-industry mr-2 text-blue-400" />Notas do Fornecedor</h3>
                <textarea value={supplierNotes} onChange={(e) => setSupplierNotes(e.target.value)} rows={4}
                  spellCheck={true} lang="pt-BR"
                  placeholder="Registre comunicações com fornecedores..."
                  className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-3 text-[var(--text-primary)] text-sm resize-none focus:outline-none focus:border-indigo-500" />
                <button onClick={handleSaveSupplierNotes}
                  className="mt-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm transition">
                  <i className="fas fa-save mr-1" />Salvar
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ═══ RIGHT SIDEBAR (collapsible icon tabs) ═══ */}
      <div className={`${sidebarCollapsed ? 'w-12' : 'w-[300px]'} shrink-0 border-l border-[var(--border-color)] flex transition-all duration-200`}>
        {/* Icon tab bar */}
        <div className="w-12 shrink-0 border-r border-[var(--border-color)] bg-[var(--bg-secondary)]/50 flex flex-col items-center pt-3 gap-1">
          {/* Collapse toggle */}
          <button onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            title={sidebarCollapsed ? 'Expandir' : 'Recolher'}
            className="w-9 h-9 rounded-lg flex items-center justify-center transition text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] mb-1">
            <i className={`fas fa-chevron-${sidebarCollapsed ? 'left' : 'right'} text-xs`} />
          </button>
          {SIDEBAR_TABS_MAIN.map(tab => (
            <button key={tab.id} onClick={() => { setSidebarTab(tab.id); if (sidebarCollapsed) setSidebarCollapsed(false) }}
              title={tab.label}
              className={`w-9 h-9 rounded-lg flex items-center justify-center transition ${
                sidebarTab === tab.id && !sidebarCollapsed
                  ? 'bg-indigo-600/20 text-indigo-400'
                  : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]'
              }`}>
              <i className={`fas ${tab.icon} text-sm`} />
            </button>
          ))}
          <div className="w-6 h-px bg-[var(--border-color)] my-1" />
          {SIDEBAR_TABS_MORE.map(tab => (
            <button key={tab.id} onClick={() => { setSidebarTab(tab.id); if (sidebarCollapsed) setSidebarCollapsed(false) }}
              title={tab.label}
              className={`w-9 h-9 rounded-lg flex items-center justify-center transition ${
                sidebarTab === tab.id && !sidebarCollapsed
                  ? 'bg-indigo-600/20 text-indigo-400'
                  : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]'
              }`}>
              <i className={`fas ${tab.icon} text-[11px]`} />
            </button>
          ))}
        </div>

        {/* Tab content */}
        {!sidebarCollapsed && <div className="flex-1 overflow-y-auto">
          {/* ── COPILOT TAB ── */}
          {/* ── ACTIONS TAB ── */}
          {sidebarTab === 'actions' && ticket && (
            <div className="p-4 space-y-4">
              <p className="text-indigo-400 text-xs font-semibold uppercase"><i className="fas fa-sliders-h mr-1" />Ações</p>
              {/* Status */}
              <div>
                <label className="text-[var(--text-tertiary)] text-[10px] uppercase tracking-wider font-semibold block mb-1.5">Status</label>
                <select value={ticket.status} onChange={(e) => handleStatusChange(e.target.value)}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500/50">
                  {[['open', 'Aberto'], ['waiting', 'Aguardando Cliente'], ['resolved', 'Resolvido'], ['closed', 'Fechado']].map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              {/* Agent */}
              <div>
                <label className="text-[var(--text-tertiary)] text-[10px] uppercase tracking-wider font-semibold block mb-1.5">Agente</label>
                <select value={ticket.assigned_to || ''} onChange={(e) => handleAssign(e.target.value)}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500/50">
                  <option value="">Sem agente</option>
                  {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
                {ticket.assigned_to && (
                  <button onClick={() => handleAssign('')}
                    className="mt-1.5 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-orange-500/10 text-orange-400 hover:bg-orange-500/20 transition">
                    <i className="fas fa-inbox" />Devolver à Caixa
                  </button>
                )}
              </div>
              {/* Priority */}
              <div>
                <label className="text-[var(--text-tertiary)] text-[10px] uppercase tracking-wider font-semibold block mb-1.5">Prioridade</label>
                <select value={ticket.priority || 'medium'} onChange={async (e) => {
                  try { await updateTicket(ticketId, { priority: e.target.value }); loadTicket() } catch { toast.error('Erro ao atualizar prioridade') }
                }}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500/50">
                  {Object.entries(PRIORITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              {/* Category */}
              <div>
                <label className="text-[var(--text-tertiary)] text-[10px] uppercase tracking-wider font-semibold block mb-1.5">Categoria</label>
                <select value={ticket.category || ''} onChange={async (e) => {
                  try { await updateTicket(ticketId, { category: e.target.value }); loadTicket() } catch { toast.error('Erro ao atualizar categoria') }
                }}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500/50">
                  {[['chargeback','Chargeback'],['ra_procon_juridico','RA/Procon/Jurídico'],['garantia_devolucoes','Garantia/Devoluções/Assistência'],['cancelamento','Cancelamento'],['entrega_rastreio','Entrega/Rastreio'],['pre_venda','Pré-Venda']].map(([k,v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              {/* Tags */}
              <div>
                <label className="text-[var(--text-tertiary)] text-[10px] uppercase tracking-wider font-semibold block mb-1.5">Tags</label>
                <div className="flex gap-1 flex-wrap mb-2">
                  {(ticket.tags || []).map(tag => {
                    const isSystem = ['BLACKLIST', 'AUTO_ESCALADO', 'SLA_ESTOURADO', 'SLA_ALERTA'].includes(tag)
                    return (
                      <span key={tag} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${TAG_COLORS[tag] || 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'}`}>
                        {TAG_LABELS[tag] || tag}
                        {!isSystem && (
                          <button onClick={async () => {
                            const updated = (ticket.tags || []).filter(t => t !== tag)
                            try { await updateTicket(ticketId, { tags: updated }); loadTicket() } catch { toast.error('Erro ao remover tag') }
                          }} className="hover:text-red-400 transition"><i className="fas fa-times text-[8px]" /></button>
                        )}
                      </span>
                    )
                  })}
                </div>
                <select onChange={async (e) => {
                  if (!e.target.value) return
                  const updated = [...(ticket.tags || []), e.target.value]
                  try { await updateTicket(ticketId, { tags: updated }); loadTicket() } catch { toast.error('Erro ao adicionar tag') }
                  e.target.value = ''
                }}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500/50">
                  <option value="">+ Adicionar tag...</option>
                  {Object.entries(TAG_LABELS).filter(([k]) => !['BLACKLIST', 'AUTO_ESCALADO', 'SLA_ESTOURADO', 'SLA_ALERTA'].includes(k) && !(ticket.tags || []).includes(k)).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
              {/* Duplicate alert */}
              {sameCustomerTickets.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 mb-2">
                  <p className="text-amber-400 text-xs font-bold"><i className="fas fa-exclamation-triangle mr-1" />{sameCustomerTickets.length} ticket(s) aberto(s) deste cliente</p>
                  <div className="mt-1.5 space-y-1">
                    {sameCustomerTickets.slice(0, 3).map(t => (
                      <div key={t.id} className="text-xs text-[var(--text-secondary)] cursor-pointer hover:text-[var(--text-primary)] transition truncate" onClick={() => onOpenTicket(t.id)}>
                        <span className="font-mono text-amber-400">#{t.number}</span> {t.subject}
                      </div>
                    ))}
                    {sameCustomerTickets.length > 3 && <p className="text-[10px] text-[var(--text-tertiary)]">+{sameCustomerTickets.length - 3} mais</p>}
                  </div>
                  <button onClick={openMergeModal} className="mt-2 w-full px-2 py-1.5 rounded-lg text-[10px] font-medium text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 transition">
                    <i className="fas fa-compress-arrows-alt mr-1" />Mesclar duplicatas
                  </button>
                </div>
              )}
              {/* Merge */}
              <div className="pt-2 border-t border-[var(--border-color)]">
                <button onClick={openMergeModal}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-[var(--bg-tertiary)] hover:bg-[var(--bg-hover)] transition">
                  <i className="fas fa-code-branch" />Mesclar Ticket
                </button>
              </div>
            </div>
          )}

          {sidebarTab === 'copilot' && (
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="text-orange-400 text-xs font-semibold uppercase"><i className="fas fa-brain mr-1" />Copiloto IA</p>
                <button onClick={() => {
                  setCopilotLoading(true)
                  getCopilotInsights(ticket.id, reply || undefined).then(r => setCopilotData(r.data)).catch(() => {}).finally(() => setCopilotLoading(false))
                }} className="text-orange-400 hover:text-orange-300 text-xs" title="Atualizar">
                  <i className={`fas ${copilotLoading ? 'fa-spinner animate-spin' : 'fa-sync-alt'}`} />
                </button>
              </div>
              {/* AI Actions (moved from chat panel) */}
              <div className="flex items-center gap-2 mb-3 p-2 bg-[var(--bg-secondary)] rounded-lg">
                <button onClick={handleAiTriage} disabled={aiLoading}
                  className="flex-1 text-[var(--text-secondary)] hover:text-orange-400 text-xs px-2 py-1.5 rounded transition disabled:opacity-50 bg-[var(--bg-tertiary)] hover:bg-orange-500/10">
                  <i className={`fas ${aiLoading ? 'fa-spinner animate-spin' : 'fa-magic'} mr-1`} />Retriar
                </button>
                <button onClick={handleAiSuggest} disabled={aiLoading}
                  className="flex-1 text-[var(--text-secondary)] hover:text-indigo-400 text-xs px-2 py-1.5 rounded transition disabled:opacity-50 bg-[var(--bg-tertiary)] hover:bg-indigo-500/10">
                  <i className={`fas ${aiLoading ? 'fa-spinner animate-spin' : 'fa-lightbulb'} mr-1`} />Sugerir
                </button>
                <button onClick={async () => {
                  try { const { data } = await generateSummary(ticket.id); if (data.summary) setTicket(prev => ({ ...prev, ai_summary: data.summary })) } catch (e) { if (_isCreditsError(e)) toast.error('Creditos IA esgotados') }
                }} className="flex-1 text-[var(--text-secondary)] hover:text-orange-400 text-xs px-2 py-1.5 rounded transition bg-[var(--bg-tertiary)] hover:bg-orange-500/10">
                  <i className="fas fa-brain mr-1" />Resumo
                </button>
              </div>
              {ticket.ai_category && (
                <div className="mb-3 text-[var(--text-tertiary)] text-xs">
                  Triagem: <span className="text-orange-400 font-medium">{CATEGORY_LABELS[ticket.ai_category] || ticket.ai_category}</span>
                  {ticket.ai_confidence && <span className="ml-1">({Math.round(ticket.ai_confidence * 100)}%)</span>}
                </div>
              )}
              {copilotLoading && !copilotData ? (
                <div className="text-center py-8"><i className="fas fa-spinner animate-spin text-orange-400" /></div>
              ) : copilotData?.credits_exhausted ? (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-center">
                  <i className="fas fa-coins text-amber-400 text-lg mb-2" />
                  <p className="text-amber-400 text-xs font-medium">Creditos IA esgotados</p>
                  <p className="text-amber-300/70 text-[10px] mt-1">Recarregue em console.anthropic.com</p>
                </div>
              ) : copilotData ? (
                <div className="space-y-3">
                  {/* Sentiment alert */}
                  {copilotData.sentiment_alert && (
                    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3">
                      <p className="text-red-400 text-xs font-medium"><i className="fas fa-exclamation-triangle mr-1" />Alerta</p>
                      <p className="text-red-300 text-xs mt-1">{copilotData.sentiment_alert}</p>
                    </div>
                  )}
                  {/* Next step */}
                  {copilotData.next_step && (
                    <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-3">
                      <p className="text-emerald-400 text-xs font-medium"><i className="fas fa-arrow-right mr-1" />Próximo passo</p>
                      <p className="text-emerald-300 text-xs mt-1">{copilotData.next_step}</p>
                    </div>
                  )}
                  {/* Tips */}
                  {copilotData.tips?.length > 0 && (
                    <div>
                      <p className="text-[var(--text-tertiary)] text-xs mb-1.5"><i className="fas fa-lightbulb mr-1 text-yellow-400" />Dicas</p>
                      <div className="space-y-1">
                        {copilotData.tips.map((tip, i) => (
                          <div key={i} className="bg-[var(--bg-secondary)] rounded-lg p-2 text-[var(--text-primary)] text-xs">{tip}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* KB articles */}
                  {copilotData.kb_articles?.length > 0 && (
                    <div>
                      <p className="text-[var(--text-tertiary)] text-xs mb-1.5"><i className="fas fa-book mr-1 text-blue-400" />Artigos KB</p>
                      <div className="space-y-1">
                        {copilotData.kb_articles.map(a => (
                          <div key={a.id} className="bg-blue-500/10 rounded-lg p-2">
                            <p className="text-blue-400 text-xs font-medium">{a.title}</p>
                            <p className="text-[var(--text-tertiary)] text-[10px] mt-0.5 line-clamp-2">{a.content_preview}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* Actions */}
                  {copilotData.actions?.length > 0 && (
                    <div>
                      <p className="text-[var(--text-tertiary)] text-xs mb-1.5"><i className="fas fa-tasks mr-1 text-purple-400" />Ações sugeridas</p>
                      <div className="space-y-1">
                        {copilotData.actions.map((action, i) => (
                          <div key={i} className="bg-purple-500/10 rounded-lg p-2 flex items-center gap-2">
                            <i className="fas fa-chevron-right text-purple-400 text-[8px]" />
                            <span className="text-purple-300 text-xs">{action}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-[var(--text-tertiary)] text-xs text-center py-4">Sem dados do copiloto</p>
              )}
            </div>
          )}

          {/* ── CUSTOMER TAB ── */}
          {sidebarTab === 'customer' && ticket.customer && (
            <div className="p-4">
              {/* Avatar + Name + Tier badge */}
              <div className="flex flex-col items-center mb-4 pb-4 border-b border-[var(--border-color)]">
                <div className="relative">
                  <div className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold mb-2 ${
                    shopifyCustomer?.tier === 'vip' ? 'bg-yellow-500/20 text-yellow-400 ring-2 ring-yellow-500/50' :
                    shopifyCustomer?.tier === 'problematic' ? 'bg-red-500/20 text-red-400 ring-2 ring-red-500/50' :
                    shopifyCustomer?.tier === 'attention' ? 'bg-orange-500/20 text-orange-400 ring-2 ring-orange-500/50' :
                    'bg-indigo-600/20 text-indigo-400'
                  }`}>
                    {(ticket.customer.name || '?')[0].toUpperCase()}
                  </div>
                  {shopifyCustomer?.tier && shopifyCustomer.tier !== 'regular' && (
                    <span className={`absolute -top-1 -right-1 px-1.5 py-0.5 rounded-full text-xs font-bold ${
                      shopifyCustomer.tier === 'vip' ? 'bg-yellow-500 text-black' :
                      shopifyCustomer.tier === 'problematic' ? 'bg-red-500 text-white' :
                      'bg-orange-500 text-white'
                    }`}>
                      {shopifyCustomer.tier === 'vip' ? <><i className="fas fa-crown mr-0.5" />VIP</> :
                       shopifyCustomer.tier === 'problematic' ? <><i className="fas fa-exclamation mr-0.5" /></> :
                       <><i className="fas fa-eye mr-0.5" /></>}
                    </span>
                  )}
                </div>
                <p className="text-[var(--text-primary)] font-semibold text-sm flex items-center gap-1.5">
                  {shopifyCustomer?.name || ticket.customer.name}
                  <button onClick={() => { navigator.clipboard.writeText(shopifyCustomer?.name || ticket.customer.name); toast.success('Nome copiado') }}
                    className="text-[var(--text-tertiary)] hover:text-indigo-400 transition" title="Copiar nome"><i className="fas fa-copy text-[10px]" /></button>
                </p>
                {(shopifyCustomer?.phone || ticket.customer.phone) && (
                  <p className="text-[var(--text-secondary)] text-xs mt-1 flex items-center gap-1.5">
                    <i className="fas fa-phone" />{shopifyCustomer?.phone || ticket.customer.phone}
                    <button onClick={() => { navigator.clipboard.writeText(shopifyCustomer?.phone || ticket.customer.phone); toast.success('Telefone copiado') }}
                      className="text-[var(--text-tertiary)] hover:text-indigo-400 transition" title="Copiar telefone"><i className="fas fa-copy text-[10px]" /></button>
                  </p>
                )}
                <p className="text-[var(--text-tertiary)] text-xs mt-0.5 flex items-center gap-1.5">
                  <i className="fas fa-envelope" />{ticket.customer.email}
                  <button onClick={() => { navigator.clipboard.writeText(ticket.customer.email); toast.success('Email copiado') }}
                    className="text-[var(--text-tertiary)] hover:text-indigo-400 transition" title="Copiar email"><i className="fas fa-copy text-[10px]" /></button>
                </p>
                {shopifyCustomer?.tier_label && shopifyCustomer.tier !== 'regular' && (
                  <span className={`mt-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                    shopifyCustomer.tier === 'vip' ? 'bg-yellow-500/20 text-yellow-400' :
                    shopifyCustomer.tier === 'problematic' ? 'bg-red-500/20 text-red-400' :
                    'bg-orange-500/20 text-orange-400'
                  }`}>
                    {shopifyCustomer.tier_label}
                  </span>
                )}
              </div>

              {/* Shopify Stats */}
              {shopifyCustomerLoading && <div className="text-center py-2"><i className="fas fa-spinner animate-spin text-indigo-400 text-xs" /></div>}
              {shopifyCustomer && (
                <div className="grid grid-cols-2 gap-2 mb-4">
                  <div className="bg-[var(--bg-secondary)] rounded-lg p-2.5 text-center">
                    <p className="text-[var(--text-primary)] text-lg font-bold">{shopifyCustomer.orders_count || 0}</p>
                    <p className="text-[var(--text-tertiary)] text-xs">Pedidos</p>
                  </div>
                  <div className="bg-[var(--bg-secondary)] rounded-lg p-2.5 text-center">
                    <p className="text-emerald-400 text-lg font-bold">R$ {(shopifyCustomer.total_spent || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
                    <p className="text-[var(--text-tertiary)] text-xs">LTV</p>
                  </div>
                  <div className="bg-[var(--bg-secondary)] rounded-lg p-2.5 text-center">
                    <p className="text-[var(--text-primary)] text-lg font-bold">{ticket.customer.total_tickets || 0}</p>
                    <p className="text-[var(--text-tertiary)] text-xs">Tickets</p>
                  </div>
                  <div className="bg-[var(--bg-secondary)] rounded-lg p-2.5 text-center">
                    <p className="text-red-400 text-lg font-bold">{ticket.customer.chargeback_count || 0}</p>
                    <p className="text-[var(--text-tertiary)] text-xs">Chargebacks</p>
                  </div>
                </div>
              )}

              {/* Shopify Customer Details */}
              {shopifyCustomer && (
                <div className="space-y-2 mb-4">
                  {shopifyCustomer.tags && (
                    <div>
                      <p className="text-[var(--text-tertiary)] text-xs mb-1">Tags Shopify</p>
                      <div className="flex flex-wrap gap-1">
                        {shopifyCustomer.tags.split(',').filter(Boolean).map((tag, i) => (
                          <span key={i} className={`px-1.5 py-0.5 rounded text-xs ${
                            tag.trim().toLowerCase().includes('chargeback') ? 'bg-red-500/20 text-red-400' :
                            tag.trim().toLowerCase().includes('vip') ? 'bg-yellow-500/20 text-yellow-400' :
                            'bg-indigo-500/15 text-indigo-400'
                          }`}>{tag.trim()}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {shopifyCustomer.default_address && (
                    <div className="bg-[var(--bg-secondary)] rounded-lg p-2">
                      <p className="text-[var(--text-tertiary)] text-xs mb-1"><i className="fas fa-map-marker-alt mr-1" />Endereço</p>
                      <p className="text-[var(--text-primary)] text-xs">
                        {shopifyCustomer.default_address.address1}
                        {shopifyCustomer.default_address.address2 && <>, {shopifyCustomer.default_address.address2}</>}
                        <br/>{shopifyCustomer.default_address.city}, {shopifyCustomer.default_address.province} - CEP {shopifyCustomer.default_address.zip}
                      </p>
                    </div>
                  )}
                  {shopifyCustomer.last_order_name && (
                    <p className="text-[var(--text-tertiary)] text-xs">Último pedido: <span className="text-[var(--text-primary)] font-mono">{shopifyCustomer.last_order_name}</span></p>
                  )}
                  {shopifyCustomer.created_at && (
                    <p className="text-[var(--text-tertiary)] text-xs">Cliente desde: <span className="text-[var(--text-secondary)]">{new Date(shopifyCustomer.created_at).toLocaleDateString('pt-BR')}</span></p>
                  )}
                  {shopifyCustomer.note && (
                    <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-2">
                      <p className="text-yellow-400 text-xs"><i className="fas fa-sticky-note mr-1" />{shopifyCustomer.note}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Chargeback/Problem Alert */}
              {shopifyCustomer?.has_chargeback && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-4">
                  <p className="text-red-400 text-xs font-bold"><i className="fas fa-exclamation-triangle mr-1" />Cliente com Chargeback</p>
                  <p className="text-[var(--text-secondary)] text-xs mt-1">Este cliente possui histórico de chargeback ou fraude.</p>
                </div>
              )}

              {shopifyCustomer?.has_many_returns && !shopifyCustomer?.has_chargeback && (
                <div className="bg-orange-500/10 border border-orange-500/20 rounded-xl p-3 mb-4">
                  <p className="text-orange-400 text-xs font-bold"><i className="fas fa-undo mr-1" />Trocas Recorrentes</p>
                  <p className="text-[var(--text-secondary)] text-xs mt-1">Cliente com histórico de trocas frequentes.</p>
                </div>
              )}

              {/* Recent Shopify Orders (inline in customer tab) */}
              {shopifyOrders.length > 0 && (
                <div className="mb-4">
                  <p className="text-[var(--text-secondary)] text-xs font-medium uppercase mb-2">Pedidos Recentes ({shopifyOrders.length})</p>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {shopifyOrders.slice(0, 5).map((order, idx) => (
                      <div key={idx} className="bg-[var(--bg-secondary)] rounded-lg p-2.5 cursor-pointer hover:bg-[var(--bg-tertiary)] transition"
                        onClick={() => { setSidebarTab('orders'); setExpandedOrder(`s-${idx}`) }}>
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-primary)] text-xs font-bold">{order.order_number}</span>
                          <span className="text-emerald-400 text-xs font-medium">R$ {parseFloat(order.total_price || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div className="flex items-center justify-between mt-1">
                          <span className={`text-xs ${order.delivery_status === 'delivered' ? 'text-emerald-400' : order.delivery_status === 'in_transit' ? 'text-blue-400' : 'text-[var(--text-tertiary)]'}`}>
                            {order.delivery_status === 'delivered' ? 'Entregue' : order.delivery_status === 'in_transit' ? 'Em trânsito' : order.financial_status === 'paid' ? 'Pago' : order.financial_status || '—'}
                          </span>
                          <span className="text-[var(--text-tertiary)] text-xs">{order.created_at ? new Date(order.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }) : ''}</span>
                        </div>
                        {order.tracking_code && <span className="text-emerald-400 text-xs font-mono mt-0.5 block">{order.tracking_code}</span>}
                      </div>
                    ))}
                    {shopifyOrders.length > 5 && (
                      <button onClick={() => setSidebarTab('orders')} className="text-indigo-400 text-xs w-full text-center py-1">
                        Ver todos ({shopifyOrders.length})
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Alternate emails from merges */}
              {ticket.customer.alternate_emails?.length > 0 && (
                <div className="mb-3 p-2.5 rounded-lg" style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)' }}>
                  <p className="text-[10px] font-semibold mb-1.5" style={{ color: '#8b5cf6' }}>
                    <i className="fas fa-link mr-1" />Emails vinculados (merge)
                  </p>
                  {ticket.customer.alternate_emails.map((alt, i) => (
                    <div key={i} className="text-xs text-[var(--text-secondary)] truncate">{alt}</div>
                  ))}
                </div>
              )}

              {/* Merge / Unmerge Customer */}
              <div className="flex items-center gap-3 mb-4">
                <button onClick={() => { setMergeCustomerSearch(''); setMergeCustomerResults([]); setShowMergeCustomerModal(true) }}
                  className="text-[var(--text-secondary)] hover:text-purple-400 text-xs transition">
                  <i className="fas fa-users mr-1" />Mesclar Cliente
                </button>
                {ticket.customer.merged_into_id && (
                  <button onClick={() => handleUnmergeCustomer(ticket.customer.id)}
                    className="text-[var(--text-secondary)] hover:text-red-400 text-xs transition">
                    <i className="fas fa-undo mr-1" />Desfazer merge
                  </button>
                )}
              </div>

              {/* Blacklist */}
              {ticket.customer.is_blacklisted ? (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-4">
                  <p className="text-red-400 text-xs font-bold"><i className="fas fa-ban mr-1" />Blacklist</p>
                  <p className="text-[var(--text-secondary)] text-xs mt-1">{ticket.customer.blacklist_reason}</p>
                  {user?.role !== 'agent' && (
                    <button onClick={handleUnblacklist} className="mt-2 text-emerald-400 hover:text-emerald-300 text-xs">Remover</button>
                  )}
                </div>
              ) : user?.role !== 'agent' && (
                <button onClick={handleBlacklist} className="text-red-400 hover:text-red-300 text-xs mb-4">
                  <i className="fas fa-ban mr-1" />Blacklist
                </button>
              )}

              {/* Escalation */}
              {ticket.escalated_at && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-4">
                  <p className="text-red-400 text-xs font-bold"><i className="fas fa-exclamation-circle mr-1" />Escalado</p>
                  <p className="text-[var(--text-secondary)] text-xs mt-1">{ticket.escalation_reason}</p>
                  <p className="text-[var(--text-tertiary)] text-xs mt-1">{new Date(ticket.escalated_at).toLocaleString('pt-BR')}</p>
                </div>
              )}

              {/* Repeat badge */}
              {ticket.customer.is_repeat && (
                <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-2.5 mb-4">
                  <p className="text-purple-400 text-xs"><i className="fas fa-redo mr-1" />Cliente recorrente</p>
                </div>
              )}

              {/* History */}
              {history.length > 0 && (
                <div>
                  <p className="text-[var(--text-secondary)] text-xs font-medium uppercase mb-2">Outros tickets ({history.length})</p>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {history.map(h => (
                      <button key={h.id} onClick={() => onOpenTicket?.(h.id)}
                        className="w-full bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] rounded-lg p-2.5 text-left transition">
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-secondary)] text-xs font-mono">#{h.number}</span>
                          <span className={`px-1.5 py-0.5 rounded-full text-xs ${
                            ['resolved', 'closed'].includes(h.status) ? 'bg-emerald-500/15 text-emerald-400' :
                            h.status === 'escalated' ? 'bg-red-500/15 text-red-400' :
                            'bg-yellow-500/15 text-yellow-400'}`}>
                            {STATUS_LABELS[h.status] || h.status}
                          </span>
                        </div>
                        <p className="text-[var(--text-primary)] text-xs line-clamp-1 mt-1">{h.subject}</p>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── ORDERS TAB (Shopify + Yampi + Appmax) ── */}
          {sidebarTab === 'orders' && (
            <div className="p-4">
              {/* Sub-tabs */}
              <div className="flex gap-1 mb-3 bg-[var(--bg-tertiary)] rounded-lg p-1">
                {[
                  { id: 'shopify', label: 'Pedidos', icon: 'fa-shopping-bag', count: shopifyOrders.length },
                  { id: 'yampi', label: 'Abandonados', icon: 'fa-cart-arrow-down', count: yampiOrders.length },
                  { id: 'appmax', label: 'Pagamentos', icon: 'fa-credit-card', count: appmaxOrders.length },
                ].map(tab => (
                  <button key={tab.id} onClick={() => setEcomSubTab(tab.id)}
                    className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition ${
                      ecomSubTab === tab.id
                        ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                        : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
                    }`}>
                    <i className={`fas ${tab.icon} mr-1`} />{tab.label}
                    {tab.count > 0 && <span className="ml-1 text-xs opacity-60">({tab.count})</span>}
                  </button>
                ))}
              </div>

              {ecomLoading && <div className="text-center py-4"><i className="fas fa-spinner animate-spin text-indigo-400" /></div>}

              {ecomError && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2.5 mb-3">
                  <p className="text-red-400 text-xs"><i className="fas fa-exclamation-triangle mr-1" />{ecomError}</p>
                </div>
              )}

              {/* SHOPIFY — Pedidos */}
              {ecomSubTab === 'shopify' && !ecomLoading && (
                <>
                  {shopifyOrders.length === 0 && (
                    <div className="text-center py-8">
                      <i className="fas fa-shopping-bag text-[var(--text-tertiary)] text-2xl mb-2" />
                      <p className="text-[var(--text-tertiary)] text-xs">Nenhum pedido na Shopify</p>
                    </div>
                  )}
                  <div className="space-y-2">
                    {shopifyOrders.map((order, idx) => {
                      const expanded = expandedOrder === `s-${idx}`
                      const fStatus = order.financial_status || ''
                      const dStatus = order.delivery_status || ''
                      const statusColor = ORDER_STATUS_COLORS[
                        dStatus === 'delivered' ? 'entregue' :
                        dStatus === 'shipped' || dStatus === 'in_transit' ? 'enviado' :
                        fStatus === 'paid' ? 'pago' :
                        fStatus === 'refunded' ? 'reembolsado' :
                        fStatus === 'pending' ? 'pendente' : 'processando'
                      ] || 'bg-gray-500/15 text-gray-400'
                      const statusLabel = dStatus === 'delivered' ? 'Entregue' :
                        dStatus === 'in_transit' ? 'Em trânsito' :
                        dStatus === 'out_for_delivery' ? 'Saiu p/ entrega' :
                        dStatus === 'shipped' ? 'Enviado' :
                        fStatus === 'paid' ? 'Pago' :
                        fStatus === 'refunded' ? 'Reembolsado' :
                        fStatus === 'partially_refunded' ? 'Reembolso parcial' :
                        fStatus === 'pending' ? 'Pendente' :
                        fStatus === 'voided' ? 'Cancelado' : (fStatus || 'Processando')
                      const DELIVERY_ICONS = {
                        delivered: 'fa-check-circle text-emerald-400',
                        in_transit: 'fa-shipping-fast text-blue-400',
                        out_for_delivery: 'fa-truck text-yellow-400',
                        shipped: 'fa-box text-blue-400',
                        pending: 'fa-clock text-gray-400',
                        failed: 'fa-times-circle text-red-400',
                      }
                      const DELIVERY_LABELS = {
                        delivered: 'Entregue', in_transit: 'Em trânsito', out_for_delivery: 'Saiu para entrega',
                        shipped: 'Enviado', pending: 'Aguardando envio', failed: 'Falha na entrega',
                      }
                      const FINANCIAL_LABELS = {
                        paid: 'Pago', pending: 'Pendente', refunded: 'Reembolsado',
                        partially_refunded: 'Reembolso parcial', voided: 'Cancelado', authorized: 'Autorizado',
                      }
                      return (
                        <div key={idx} className="bg-[var(--bg-secondary)] rounded-xl overflow-hidden border border-[var(--border-color)]">
                          <button onClick={() => setExpandedOrder(expanded ? null : `s-${idx}`)}
                            className="relative w-full p-3 text-left hover:bg-[var(--bg-tertiary)] transition">
                            <div className="flex items-center justify-between">
                              <span className="text-[var(--text-primary)] text-sm font-bold">{order.order_number}</span>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor}`}>{statusLabel}</span>
                            </div>
                            {/* Resumo: valor + data + rastreio rápido */}
                            <div className="flex items-center justify-between mt-1.5">
                              <span className="text-[var(--text-secondary)] text-xs font-semibold">
                                R$ {parseFloat(order.total_price || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                              </span>
                              <span className="text-[var(--text-tertiary)] text-xs">
                                {order.created_at ? new Date(order.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—'}
                              </span>
                            </div>
                            {/* Tracking code preview */}
                            {order.tracking_code && (
                              <div className="flex items-center gap-1.5 mt-1.5">
                                <i className={`fas ${DELIVERY_ICONS[dStatus] || 'fa-clock text-gray-400'} text-xs`} />
                                <span className="text-emerald-400 text-xs font-mono">{order.tracking_code}</span>
                              </div>
                            )}
                            <i className={`fas fa-chevron-${expanded ? 'up' : 'down'} text-[var(--text-tertiary)] text-xs absolute right-3 bottom-3`} />
                          </button>

                          {expanded && (
                            <div className="px-3 pb-3 border-t border-[var(--border-color)] pt-2 space-y-2.5">

                              {/* Status detalhado */}
                              <div className="grid grid-cols-2 gap-2">
                                <div className="bg-[var(--bg-tertiary)] rounded-lg p-2">
                                  <p className="text-[var(--text-tertiary)] text-xs mb-0.5">Pagamento</p>
                                  <p className={`text-xs font-medium ${fStatus === 'paid' ? 'text-emerald-400' : fStatus === 'refunded' ? 'text-orange-400' : 'text-yellow-400'}`}>
                                    {FINANCIAL_LABELS[fStatus] || fStatus}
                                  </p>
                                </div>
                                <div className="bg-[var(--bg-tertiary)] rounded-lg p-2">
                                  <p className="text-[var(--text-tertiary)] text-xs mb-0.5">Entrega</p>
                                  <p className="text-xs font-medium text-[var(--text-primary)]">
                                    <i className={`fas ${DELIVERY_ICONS[dStatus] || 'fa-clock text-gray-400'} mr-1`} />
                                    {DELIVERY_LABELS[dStatus] || dStatus || 'Aguardando'}
                                  </p>
                                </div>
                              </div>

                              {/* Itens do pedido */}
                              {order.items?.length > 0 && (
                                <div>
                                  <p className="text-[var(--text-tertiary)] text-xs font-medium mb-1"><i className="fas fa-box-open mr-1" />Itens</p>
                                  {order.items.map((item, i) => (
                                    <div key={i} className="flex justify-between text-xs py-0.5">
                                      <span className="text-[var(--text-primary)] truncate flex-1">
                                        {item.quantity || 1}x {item.title || item.name}
                                        {item.variant_title ? <span className="text-[var(--text-tertiary)]"> ({item.variant_title})</span> : ''}
                                        {item.sku ? <span className="text-[var(--text-tertiary)] ml-1 font-mono">SKU:{item.sku}</span> : ''}
                                      </span>
                                      <span className="text-[var(--text-secondary)] ml-2 whitespace-nowrap">R$ {parseFloat(item.price || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* Rastreio completo */}
                              {order.fulfillments?.length > 0 && (
                                <div className="bg-[var(--bg-tertiary)] rounded-lg p-2.5 space-y-2">
                                  <p className="text-[var(--text-tertiary)] text-xs font-medium"><i className="fas fa-truck mr-1" />Rastreio & Envio</p>
                                  {order.fulfillments.map((ful, fi) => (
                                    <div key={fi} className="space-y-1">
                                      {/* Transportadora */}
                                      {ful.tracking_company && (
                                        <div className="flex items-center gap-1.5">
                                          <i className="fas fa-building text-[var(--text-tertiary)] text-xs" />
                                          <span className="text-[var(--text-primary)] text-xs font-medium">{ful.tracking_company}</span>
                                        </div>
                                      )}
                                      {/* Códigos de rastreio */}
                                      {ful.tracking_numbers?.map((code, ci) => (
                                        <div key={ci} className="flex items-center justify-between">
                                          <span className="text-emerald-400 text-xs font-mono font-bold">{code}</span>
                                          {ful.tracking_urls?.[ci] && (
                                            <a href={ful.tracking_urls[ci]} target="_blank" rel="noreferrer"
                                              className="text-indigo-400 text-xs hover:underline flex items-center gap-1">
                                              <i className="fas fa-external-link-alt text-xs" />rastrear
                                            </a>
                                          )}
                                        </div>
                                      ))}
                                      {/* Status do envio */}
                                      <div className="flex items-center gap-2 flex-wrap">
                                        {ful.shipment_status && (
                                          <span className={`px-1.5 py-0.5 rounded-full text-xs ${
                                            ful.shipment_status === 'delivered' ? 'bg-emerald-500/20 text-emerald-400' :
                                            ful.shipment_status === 'in_transit' ? 'bg-blue-500/20 text-blue-400' :
                                            ful.shipment_status === 'out_for_delivery' ? 'bg-yellow-500/20 text-yellow-400' :
                                            ful.shipment_status === 'confirmed' ? 'bg-indigo-500/20 text-indigo-400' :
                                            ful.shipment_status === 'failure' ? 'bg-red-500/20 text-red-400' :
                                            'bg-gray-500/20 text-gray-400'
                                          }`}>
                                            {DELIVERY_LABELS[ful.shipment_status] || ful.shipment_status}
                                          </span>
                                        )}
                                        {ful.estimated_delivery_at && (
                                          <span className="text-[var(--text-tertiary)] text-xs">
                                            <i className="fas fa-calendar-alt mr-1" />
                                            Previsão: {new Date(ful.estimated_delivery_at).toLocaleDateString('pt-BR')}
                                          </span>
                                        )}
                                      </div>
                                      {/* Data do fulfillment */}
                                      <div className="text-[var(--text-tertiary)] text-xs">
                                        Enviado em: {ful.created_at ? new Date(ful.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                                        {ful.updated_at && ful.updated_at !== ful.created_at && (
                                          <span className="ml-2">| Atualizado: {new Date(ful.updated_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* Rastreio simples (quando não tem fulfillments mas tem tracking_code) */}
                              {!order.fulfillments?.length && order.tracking_code && (
                                <div className="bg-[var(--bg-tertiary)] rounded-lg p-2">
                                  <p className="text-[var(--text-tertiary)] text-xs mb-1"><i className="fas fa-truck mr-1" />Rastreio</p>
                                  <div className="flex items-center justify-between">
                                    <span className="text-emerald-400 text-xs font-mono font-bold">{order.tracking_code}</span>
                                    {order.tracking_url && (
                                      <a href={order.tracking_url} target="_blank" rel="noreferrer"
                                        className="text-indigo-400 text-xs hover:underline"><i className="fas fa-external-link-alt mr-1" />rastrear</a>
                                    )}
                                  </div>
                                </div>
                              )}

                              {/* Transportadora */}
                              {order.carrier && (
                                <div className="text-xs text-[var(--text-secondary)]">
                                  <i className="fas fa-shipping-fast mr-1" />Frete: {order.carrier}
                                </div>
                              )}

                              {/* Endereço de entrega */}
                              {order.shipping_address && (
                                <div className="bg-[var(--bg-tertiary)] rounded-lg p-2">
                                  <p className="text-[var(--text-tertiary)] text-xs mb-1"><i className="fas fa-map-marker-alt mr-1" />Endereço</p>
                                  <p className="text-[var(--text-primary)] text-xs">
                                    {order.shipping_address.name && <span className="font-medium">{order.shipping_address.name}<br/></span>}
                                    {order.shipping_address.city}, {order.shipping_address.province} - CEP {order.shipping_address.zip}
                                  </p>
                                </div>
                              )}

                              {/* Datas */}
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div>
                                  <span className="text-[var(--text-tertiary)]">Criado: </span>
                                  <span className="text-[var(--text-secondary)]">
                                    {order.created_at ? new Date(order.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-[var(--text-tertiary)]">Atualizado: </span>
                                  <span className="text-[var(--text-secondary)]">
                                    {order.updated_at ? new Date(order.updated_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                                  </span>
                                </div>
                              </div>

                              {/* Cancelado */}
                              {order.cancelled_at && (
                                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2">
                                  <p className="text-red-400 text-xs font-medium">
                                    <i className="fas fa-ban mr-1" />Cancelado em {new Date(order.cancelled_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                  </p>
                                </div>
                              )}

                              {/* Nota do pedido */}
                              {order.note && (
                                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-2">
                                  <p className="text-yellow-400 text-xs"><i className="fas fa-sticky-note mr-1" />{order.note}</p>
                                </div>
                              )}

                              {/* Tags */}
                              {order.tags && (
                                <div className="flex flex-wrap gap-1">
                                  {order.tags.split(',').filter(Boolean).map((tag, i) => (
                                    <span key={i} className="px-1.5 py-0.5 bg-indigo-500/15 text-indigo-400 rounded text-xs">{tag.trim()}</span>
                                  ))}
                                </div>
                              )}

                              {/* Ações Shopify */}
                              {order.order_id && !order.cancelled_at && (
                                <div className="flex gap-2 pt-2 border-t border-[var(--border-color)]">
                                  {order.financial_status === 'paid' && (
                                    <button
                                      onClick={() => setShowRefundModal(order)}
                                      disabled={actionLoading === order.order_id}
                                      className="flex-1 bg-orange-500/15 hover:bg-orange-500/25 text-orange-400 px-3 py-1.5 rounded-lg text-xs font-medium transition disabled:opacity-50">
                                      <i className={`fas ${actionLoading === order.order_id ? 'fa-spinner animate-spin' : 'fa-undo'} mr-1`} />Reembolsar
                                    </button>
                                  )}
                                  <button
                                    onClick={() => setShowCancelModal(order)}
                                    disabled={actionLoading === order.order_id}
                                    className="flex-1 bg-red-500/15 hover:bg-red-500/25 text-red-400 px-3 py-1.5 rounded-lg text-xs font-medium transition disabled:opacity-50">
                                    <i className={`fas ${actionLoading === order.order_id ? 'fa-spinner animate-spin' : 'fa-ban'} mr-1`} />Cancelar
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </>
              )}

              {/* YAMPI — Carrinhos/Checkouts Abandonados */}
              {ecomSubTab === 'yampi' && !ecomLoading && (
                <>
                  {yampiOrders.length === 0 && (
                    <div className="text-center py-8">
                      <i className="fas fa-cart-arrow-down text-[var(--text-tertiary)] text-2xl mb-2" />
                      <p className="text-[var(--text-tertiary)] text-xs">Nenhum carrinho abandonado</p>
                    </div>
                  )}
                  <div className="space-y-2">
                    {yampiOrders.map((order, idx) => {
                      const expanded = expandedOrder === `y-${idx}`
                      return (
                        <div key={idx} className="bg-[var(--bg-secondary)] rounded-xl overflow-hidden border border-[var(--border-color)]">
                          <button onClick={() => setExpandedOrder(expanded ? null : `y-${idx}`)}
                            className="relative w-full p-3 text-left hover:bg-[var(--bg-tertiary)] transition">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs bg-green-500/20 text-green-400">Y</span>
                                <span className="text-[var(--text-primary)] text-xs font-bold">#{order.order_number}</span>
                              </div>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ORDER_STATUS_COLORS[order.status] || 'bg-gray-500/15 text-gray-400'}`}>
                                {order.status_label || order.status}
                              </span>
                            </div>
                            <div className="flex items-center justify-between mt-1.5">
                              <span className="text-[var(--text-secondary)] text-xs font-medium">R$ {parseFloat(order.total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                            </div>
                            <p className="text-[var(--text-tertiary)] text-xs mt-1">
                              {order.created_at ? new Date(order.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                            </p>
                            <i className={`fas fa-chevron-${expanded ? 'up' : 'down'} text-[var(--text-tertiary)] text-xs absolute right-3 bottom-3`} />
                          </button>
                          {expanded && order.items?.length > 0 && (
                            <div className="px-3 pb-3 border-t border-[var(--border-color)] pt-2">
                              {order.items.map((item, i) => (
                                <div key={i} className="flex justify-between text-xs py-0.5">
                                  <span className="text-[var(--text-primary)] truncate flex-1">{item.quantity || 1}x {item.name}</span>
                                  <span className="text-[var(--text-secondary)] ml-2">R$ {parseFloat(item.price || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </>
              )}

              {/* APPMAX — Pagamentos / Chargebacks */}
              {ecomSubTab === 'appmax' && !ecomLoading && (
                <>
                  {appmaxOrders.length === 0 && (
                    <div className="text-center py-8">
                      <i className="fas fa-credit-card text-[var(--text-tertiary)] text-2xl mb-2" />
                      <p className="text-[var(--text-tertiary)] text-xs">Nenhum registro no Appmax</p>
                    </div>
                  )}
                  <div className="space-y-2">
                    {appmaxOrders.map((order, idx) => {
                      const expanded = expandedOrder === `a-${idx}`
                      return (
                        <div key={idx} className="bg-[var(--bg-secondary)] rounded-xl overflow-hidden border border-[var(--border-color)]">
                          <button onClick={() => setExpandedOrder(expanded ? null : `a-${idx}`)}
                            className="relative w-full p-3 text-left hover:bg-[var(--bg-tertiary)] transition">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs bg-blue-500/20 text-blue-400">A</span>
                                <span className="text-[var(--text-primary)] text-xs font-bold">#{order.order_number}</span>
                              </div>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ORDER_STATUS_COLORS[order.status] || 'bg-gray-500/15 text-gray-400'}`}>
                                {order.status_label || order.status}
                              </span>
                            </div>
                            <div className="flex items-center justify-between mt-1.5">
                              {order.payment_method && (
                                <span className="text-[var(--text-tertiary)] text-xs flex items-center gap-1">
                                  <i className={`fas ${order.payment_method?.includes('pix') ? 'fa-qrcode' : order.payment_method?.includes('boleto') ? 'fa-barcode' : 'fa-credit-card'} text-xs`} />
                                  {order.payment_method}
                                </span>
                              )}
                              <span className="text-[var(--text-secondary)] text-xs font-medium">R$ {parseFloat(order.total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                            </div>
                            <p className="text-[var(--text-tertiary)] text-xs mt-1">
                              {order.created_at ? new Date(order.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                            </p>
                            <i className={`fas fa-chevron-${expanded ? 'up' : 'down'} text-[var(--text-tertiary)] text-xs absolute right-3 bottom-3`} />
                          </button>
                          {expanded && order.items?.length > 0 && (
                            <div className="px-3 pb-3 border-t border-[var(--border-color)] pt-2">
                              {order.items.map((item, i) => (
                                <div key={i} className="flex justify-between text-xs py-0.5">
                                  <span className="text-[var(--text-primary)] truncate flex-1">{item.quantity || 1}x {item.name}</span>
                                  <span className="text-[var(--text-secondary)] ml-2">R$ {parseFloat(item.price || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── MEDIA TAB ── */}
          {sidebarTab === 'media' && (
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="text-[var(--text-secondary)] text-xs font-medium uppercase">Biblioteca</p>
                <button onClick={() => setShowAddMedia(!showAddMedia)}
                  className="text-pink-400 hover:text-pink-300 text-xs">
                  <i className={`fas ${showAddMedia ? 'fa-times' : 'fa-plus'}`} />
                </button>
              </div>

              {/* AI Suggestions */}
              {mediaSuggestions.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs text-emerald-400 mb-1.5"><i className="fas fa-robot mr-1" />Sugestões IA</p>
                  <div className="space-y-1">
                    {mediaSuggestions.map(m => (
                      <a key={m.id} href={m.drive_url} target="_blank" rel="noreferrer"
                        className="flex items-center gap-2 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-lg p-2 transition">
                        <MediaIcon category={m.category} sourceType={m.source_type} />
                        <div className="flex-1 min-w-0">
                          <p className="text-[var(--text-primary)] text-xs truncate">{m.name}</p>
                        </div>
                        <i className="fas fa-external-link-alt text-[var(--text-tertiary)] text-xs" />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Add Form */}
              {showAddMedia && (
                <div className="bg-[var(--bg-secondary)] rounded-xl p-3 mb-3 space-y-2 border border-[var(--border-color)]">
                  {/* Upload de arquivo */}
                  <input type="file" ref={mediaFileRef} className="hidden" accept="image/*,video/*"
                    onChange={e => setMediaUploadFile(e.target.files[0] || null)} />
                  {mediaUploadFile ? (
                    <div className="flex items-center gap-2 bg-pink-500/10 rounded-lg px-3 py-2">
                      <i className={`fas ${mediaUploadFile.type.startsWith('video') ? 'fa-video' : 'fa-image'} text-pink-400 text-xs`} />
                      <span className="text-[var(--text-primary)] text-xs flex-1 truncate">{mediaUploadFile.name}</span>
                      <button onClick={() => { setMediaUploadFile(null); mediaFileRef.current.value = '' }}
                        className="text-[var(--text-tertiary)] hover:text-red-400 text-xs"><i className="fas fa-times" /></button>
                    </div>
                  ) : (
                    <button onClick={() => mediaFileRef.current?.click()}
                      className="w-full border-2 border-dashed border-[var(--border-color)] hover:border-pink-500/50 rounded-lg py-3 text-[var(--text-tertiary)] hover:text-pink-400 text-xs transition">
                      <i className="fas fa-cloud-upload-alt mr-2" />Enviar Foto/Vídeo
                    </button>
                  )}
                  {mediaUploading && (
                    <div className="w-full bg-[var(--bg-tertiary)] rounded-full h-1.5 overflow-hidden">
                      <div className="h-full bg-pink-500 rounded-full animate-pulse" style={{ width: '60%' }} />
                    </div>
                  )}
                  <button onClick={async () => {
                    if (!mediaUploadFile) return
                    setMediaUploading(true)
                    try {
                      const fd = new FormData()
                      fd.append('file', mediaUploadFile)
                      fd.append('name', mediaUploadFile.name.replace(/\.[^.]+$/, ''))
                      fd.append('category', mediaUploadFile.type.startsWith('video') ? 'video' : 'foto')
                      await uploadMedia(fd)
                      const r = await getMediaItems(); setMediaItems(r.data || [])
                      setMediaUploadFile(null); mediaFileRef.current.value = ''; setShowAddMedia(false)
                    } catch (e) { toast.error(e.response?.data?.detail || 'Erro no upload') }
                    finally { setMediaUploading(false) }
                  }} disabled={mediaUploading || !mediaUploadFile}
                    className="w-full bg-pink-600/20 text-pink-400 hover:bg-pink-600/40 py-1.5 rounded-lg text-xs transition disabled:opacity-50">
                    {mediaUploading ? <><i className="fas fa-spinner animate-spin mr-1" />Enviando...</> : <><i className="fas fa-upload mr-1" />Upload</>}
                  </button>

                  <div className="flex items-center gap-2 my-1">
                    <div className="flex-1 h-px bg-[var(--border-color)]" />
                    <span className="text-[var(--text-tertiary)] text-[10px]">ou cole um link</span>
                    <div className="flex-1 h-px bg-[var(--border-color)]" />
                  </div>

                  <input value={newMedia.name} onChange={e => setNewMedia({ ...newMedia, name: e.target.value })}
                    placeholder="Nome" className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-[var(--text-primary)] text-xs focus:outline-none focus:border-pink-500" />
                  <input value={newMedia.drive_url} onChange={e => setNewMedia({ ...newMedia, drive_url: e.target.value })}
                    placeholder="Link (Drive, Instagram, URL)" className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-[var(--text-primary)] text-xs focus:outline-none focus:border-pink-500" />
                  <select value={newMedia.category} onChange={e => setNewMedia({ ...newMedia, category: e.target.value })}
                    className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-[var(--text-primary)] text-xs">
                    <option value="video">Vídeo</option><option value="foto">Foto</option><option value="instagram">Instagram</option><option value="link">Link</option>
                    <option value="politica">Política</option><option value="manual">Manual</option>
                  </select>
                  <button onClick={async () => {
                    if (!newMedia.name || !newMedia.drive_url) return
                    setAddingMedia(true)
                    try { await createMediaItem(newMedia); const r = await getMediaItems(); setMediaItems(r.data || []); setNewMedia({ name: '', drive_url: '', description: '', category: 'video' }); setShowAddMedia(false) }
                    catch (e) { toast.error(e.response?.data?.detail || 'Erro') } finally { setAddingMedia(false) }
                  }} disabled={addingMedia}
                    className="w-full bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-pink-400 py-1.5 rounded-lg text-xs transition disabled:opacity-50 border border-[var(--border-color)]">
                    {addingMedia ? <i className="fas fa-spinner animate-spin" /> : <><i className="fas fa-link mr-1" />Adicionar Link</>}
                  </button>
                </div>
              )}

              {/* Search */}
              {mediaItems.length > 3 && (
                <input value={mediaFilter} onChange={e => setMediaFilter(e.target.value)}
                  placeholder="Buscar..." className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-[var(--text-primary)] text-xs mb-2 focus:outline-none focus:border-pink-500" />
              )}

              {/* List */}
              {mediaLoading ? (
                <div className="text-center py-4"><i className="fas fa-spinner animate-spin text-pink-400 text-xs" /></div>
              ) : (
                <div className="space-y-1">
                  {mediaItems
                    .filter(m => !mediaFilter || m.name.toLowerCase().includes(mediaFilter.toLowerCase()))
                    .filter(m => !mediaSuggestions.some(s => s.id === m.id))
                    .map(m => (
                      <a key={m.id} href={m.drive_url} target="_blank" rel="noreferrer"
                        className="flex items-center gap-2 bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] rounded-lg p-2 transition">
                        <MediaIcon category={m.category} sourceType={m.source_type} />
                        <div className="flex-1 min-w-0">
                          <p className="text-[var(--text-primary)] text-xs truncate">{m.name}</p>
                          {m.description && <p className="text-[var(--text-tertiary)] text-xs truncate">{m.description}</p>}
                        </div>
                        <i className="fas fa-external-link-alt text-[var(--text-tertiary)] text-xs" />
                      </a>
                    ))}
                  {mediaItems.length === 0 && !mediaLoading && (
                    <p className="text-[var(--text-tertiary)] text-xs text-center py-4">Nenhuma mídia</p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── NOTES TAB ── */}
          {sidebarTab === 'notes' && (
            <div className="p-4">
              <p className="text-[var(--text-secondary)] text-xs font-medium uppercase mb-3">Notas Internas</p>
              <textarea value={internalNotes} onChange={(e) => setInternalNotes(e.target.value)} rows={12}
                spellCheck={true} lang="pt-BR"
                placeholder="Anotações internas sobre este ticket..."
                className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-3 text-[var(--text-primary)] text-sm resize-none focus:outline-none focus:border-yellow-500 leading-relaxed" />
              <button onClick={async () => {
                setSavingNotes(true)
                try { await updateInternalNotes(ticket.id, { internal_notes: internalNotes }) } catch { toast.error('Erro ao salvar notas') }
                finally { setSavingNotes(false) }
              }} disabled={savingNotes}
                className="mt-2 bg-yellow-600/20 text-yellow-400 hover:bg-yellow-600/40 px-4 py-2 rounded-lg text-xs transition disabled:opacity-50 w-full">
                <i className={`fas ${savingNotes ? 'fa-spinner animate-spin' : 'fa-save'} mr-1`} />
                {savingNotes ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          )}
        </div>}
      </div>

      {/* ═══ CSAT MODAL ═══ */}
      {showCsatForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowCsatForm(false)}>
          <div className="bg-[var(--bg-secondary)] rounded-2xl w-full max-w-sm border border-[var(--border-color)] shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-[var(--border-color)]">
              <h2 className="text-[var(--text-primary)] font-bold"><i className="fas fa-star mr-2 text-yellow-400" />Avaliação do Atendimento</h2>
            </div>
            <div className="px-6 py-5">
              <p className="text-[var(--text-secondary)] text-sm mb-4">Como foi o atendimento do ticket #{ticket.number}?</p>

              {/* Stars */}
              <div className="flex justify-center gap-2 mb-4">
                {[1, 2, 3, 4, 5].map(star => (
                  <button key={star} onClick={() => setCsatScore(star)}
                    className={`text-3xl transition-transform hover:scale-110 ${
                      star <= csatScore ? 'text-yellow-400' : 'text-[var(--text-tertiary)]'
                    }`}>
                    <i className={`fas fa-star`} />
                  </button>
                ))}
              </div>
              <p className="text-center text-[var(--text-tertiary)] text-xs mb-4">
                {csatScore === 1 ? 'Péssimo' : csatScore === 2 ? 'Ruim' : csatScore === 3 ? 'Regular' : csatScore === 4 ? 'Bom' : csatScore === 5 ? 'Excelente' : 'Selecione uma nota'}
              </p>

              {/* Comment */}
              <textarea value={csatComment} onChange={e => setCsatComment(e.target.value)} rows={3}
                placeholder="Comentário (opcional)..."
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-xl p-3 text-[var(--text-primary)] text-sm resize-none focus:outline-none focus:border-yellow-500" />
            </div>
            <div className="flex gap-3 justify-end px-6 py-4 border-t border-[var(--border-color)]">
              <button onClick={() => setShowCsatForm(false)}
                className="px-4 py-2 rounded-xl text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition">Cancelar</button>
              <button onClick={async () => {
                if (!csatScore) return
                setCsatSubmitting(true)
                try {
                  await submitCsat(ticket.id, { score: csatScore, comment: csatComment || null })
                  setCsatSubmitted(true)
                  setShowCsatForm(false)
                } catch (e) {
                  const msg = e.response?.data?.detail || 'Erro ao enviar avaliação'
                  if (msg.includes('já enviada')) setCsatSubmitted(true)
                  toast.error(msg)
                } finally { setCsatSubmitting(false) }
              }} disabled={!csatScore || csatSubmitting}
                className="bg-yellow-600 hover:bg-yellow-500 text-white px-5 py-2 rounded-xl text-sm font-medium transition disabled:opacity-50">
                {csatSubmitting ? <><i className="fas fa-spinner animate-spin mr-1" />Enviando...</> : <><i className="fas fa-check mr-1" />Enviar</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ REFUND MODAL ═══ */}
      {showRefundModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowRefundModal(null)}>
          <div className="bg-[var(--bg-secondary)] rounded-2xl w-full max-w-md border border-[var(--border-color)] shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-[var(--border-color)]">
              <h2 className="text-[var(--text-primary)] font-bold"><i className="fas fa-undo mr-2 text-orange-400" />Reembolsar Pedido</h2>
            </div>
            <div className="px-6 py-5">
              <p className="text-[var(--text-secondary)] text-sm mb-4">Tem certeza que deseja reembolsar o pedido <b>{showRefundModal.order_number}</b>?</p>
              <div className="bg-[var(--bg-tertiary)] rounded-xl p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--text-secondary)]">Valor:</span>
                  <span className="text-[var(--text-primary)] font-bold">R$ {parseFloat(showRefundModal.total_price || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--text-secondary)]">Tipo:</span>
                  <span className="text-[var(--text-primary)]">Reembolso total</span>
                </div>
              </div>
            </div>
            <div className="flex gap-3 justify-end px-6 py-4 border-t border-[var(--border-color)]">
              <button onClick={() => setShowRefundModal(null)}
                className="px-4 py-2 rounded-xl text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition">Cancelar</button>
              <button onClick={async () => {
                setActionLoading(showRefundModal.order_id)
                try {
                  const res = await refundShopifyOrder(showRefundModal.order_id, { reason: 'Reembolso via helpdesk', ticket_number: ticket.number, customer_name: ticket.customer?.name || '', customer_email: ticket.customer?.email || '', tracking_code: ticket.tracking_code || '' })
                  if (res.data?.success) { toast.success('Reembolso processado!'); setShowRefundModal(null); getEcommerceOrders(ticket.customer.email).then(r => setShopifyOrders(r.data?.shopify_orders || [])) }
                  else toast.error(res.data?.error || 'Erro ao reembolsar')
                } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao reembolsar') }
                finally { setActionLoading(null) }
              }}
                className="bg-orange-600 hover:bg-orange-500 text-white px-5 py-2 rounded-xl text-sm font-medium transition">
                <i className="fas fa-undo mr-1" />Confirmar Reembolso
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ CANCEL ORDER MODAL ═══ */}
      {showCancelModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowCancelModal(null)}>
          <div className="bg-[var(--bg-secondary)] rounded-2xl w-full max-w-md border border-[var(--border-color)] shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-[var(--border-color)]">
              <h2 className="text-[var(--text-primary)] font-bold"><i className="fas fa-ban mr-2 text-red-400" />Cancelar Pedido</h2>
            </div>
            <div className="px-6 py-5">
              <p className="text-[var(--text-secondary)] text-sm mb-4">Tem certeza que deseja cancelar o pedido <b>{showCancelModal.order_number}</b>?</p>
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                <p className="text-red-400 text-xs"><i className="fas fa-exclamation-triangle mr-1" />Esta ação não pode ser desfeita. O cliente será notificado por email.</p>
              </div>
            </div>
            <div className="flex gap-3 justify-end px-6 py-4 border-t border-[var(--border-color)]">
              <button onClick={() => setShowCancelModal(null)}
                className="px-4 py-2 rounded-xl text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition">Voltar</button>
              <button onClick={async () => {
                setActionLoading(showCancelModal.order_id)
                try {
                  const res = await cancelShopifyOrder(showCancelModal.order_id, { reason: 'customer', email_customer: true, ticket_number: ticket.number, customer_name: ticket.customer?.name || '', customer_email: ticket.customer?.email || '', tracking_code: ticket.tracking_code || '' })
                  if (res.data?.success) { toast.success('Pedido cancelado!'); setShowCancelModal(null); getEcommerceOrders(ticket.customer.email).then(r => setShopifyOrders(r.data?.shopify_orders || [])) }
                  else toast.error(res.data?.error || 'Erro ao cancelar')
                } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao cancelar') }
                finally { setActionLoading(null) }
              }}
                className="bg-red-600 hover:bg-red-500 text-white px-5 py-2 rounded-xl text-sm font-medium transition">
                <i className="fas fa-ban mr-1" />Confirmar Cancelamento
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ MERGE TICKET MODAL ═══ */}
      {showMergeModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={() => setShowMergeModal(false)}>
          <div className="rounded-2xl p-6 w-full max-w-lg" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }} onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4" style={{ color: 'var(--text-primary)' }}>
              <i className="fas fa-code-branch mr-2" />Mesclar Tickets
            </h3>
            <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>
              As mensagens dos tickets selecionados serao movidas para este ticket (#{ticket.number}).
            </p>

            {/* Same customer tickets with checkboxes */}
            {sameCustomerTickets.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-semibold uppercase mb-2" style={{ color: 'var(--accent)' }}>
                  <i className="fas fa-user mr-1" />Tickets do mesmo cliente ({sameCustomerTickets.length})
                </p>
                <div className="max-h-48 overflow-auto space-y-1.5">
                  {sameCustomerTickets.map(t => (
                    <label key={t.id} className="flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition hover:bg-[var(--bg-hover)]"
                      style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)' }}>
                      <input
                        type="checkbox"
                        checked={!!selectedMergeSources[t.id]}
                        onChange={e => setSelectedMergeSources(prev => ({ ...prev, [t.id]: e.target.checked }))}
                        className="accent-indigo-500"
                      />
                      <div className="flex-1 min-w-0">
                        <span className="font-mono text-xs" style={{ color: 'var(--accent)' }}>#{t.number}</span>
                        <span className="text-sm ml-2 truncate" style={{ color: 'var(--text-primary)' }}>{t.subject}</span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--bg-hover)', color: 'var(--text-tertiary)' }}>{t.status}</span>
                          <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>{t.created_at ? new Date(t.created_at).toLocaleDateString('pt-BR') : ''}</span>
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Batch merge button */}
            {sameCustomerTickets.length > 0 && Object.values(selectedMergeSources).some(v => v) && (
              <button onClick={handleBatchMerge} disabled={mergingBatch}
                className="w-full mb-4 px-4 py-2.5 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition">
                {mergingBatch ? <><i className="fas fa-spinner animate-spin mr-2" />Mesclando...</> : <>
                  <i className="fas fa-compress-arrows-alt mr-2" />Mesclar {Object.values(selectedMergeSources).filter(v => v).length} ticket(s) aqui
                </>}
              </button>
            )}

            {/* Divider */}
            <div className="flex items-center gap-2 mb-3">
              <div className="flex-1 border-t" style={{ borderColor: 'var(--border-color)' }} />
              <span className="text-[10px] uppercase" style={{ color: 'var(--text-tertiary)' }}>ou buscar outro ticket</span>
              <div className="flex-1 border-t" style={{ borderColor: 'var(--border-color)' }} />
            </div>

            <input
              type="text"
              placeholder="Buscar por numero, assunto ou cliente..."
              value={mergeSearch}
              onChange={e => setMergeSearch(e.target.value)}
              className="w-full rounded-lg px-4 py-2 text-sm mb-3"
              style={{ background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
            />
            {mergeResults.length > 0 && (
              <div className="max-h-40 overflow-auto space-y-2 mb-4">
                {mergeResults.filter(t => t.id !== ticket.id).map(t => (
                  <button
                    key={t.id}
                    onClick={() => handleMergeTicket(t.id)}
                    className="w-full text-left p-3 rounded-lg transition"
                    style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)' }}
                  >
                    <span className="font-mono text-xs" style={{ color: 'var(--accent)' }}>#{t.number}</span>
                    <span className="text-sm ml-2" style={{ color: 'var(--text-primary)' }}>{t.subject}</span>
                    <span className="text-xs block mt-1" style={{ color: 'var(--text-tertiary)' }}>{t.customer?.name || 'Sem cliente'}</span>
                  </button>
                ))}
              </div>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowMergeModal(false)} className="px-4 py-2 rounded-lg text-sm" style={{ color: 'var(--text-secondary)' }}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Merge Customer Modal */}
      {showMergeCustomerModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={() => setShowMergeCustomerModal(false)}>
          <div className="rounded-2xl p-6 w-full max-w-md" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }} onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4" style={{ color: 'var(--text-primary)' }}>
              <i className="fas fa-users mr-2" />Mesclar Cliente
            </h3>
            <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>
              Todos os tickets do cliente serao transferidos para o cliente destino.
            </p>
            <input
              type="text"
              placeholder="Buscar por nome, email, CPF..."
              value={mergeCustomerSearch}
              onChange={e => setMergeCustomerSearch(e.target.value)}
              className="w-full rounded-lg px-4 py-2 text-sm mb-3"
              style={{ background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
            />
            {mergeCustomerResults.length > 0 && (
              <div className="max-h-60 overflow-auto space-y-2 mb-4">
                {mergeCustomerResults.filter(c => c.id !== ticket.customer?.id).map(c => (
                  <button
                    key={c.id}
                    onClick={() => handleMergeCustomer(c.id)}
                    className="w-full text-left p-3 rounded-lg transition"
                    style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)' }}
                  >
                    <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{c.name}</span>
                    <span className="text-xs block" style={{ color: 'var(--text-secondary)' }}>{c.email}</span>
                    {c.cpf && <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}> · CPF: {c.cpf}</span>}
                  </button>
                ))}
              </div>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowMergeCustomerModal(false)} className="px-4 py-2 rounded-lg text-sm" style={{ color: 'var(--text-secondary)' }}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ PROTOCOL EMAIL MODAL ═══ */}
      {showProtocolModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => !sendingProtocol && setShowProtocolModal(false)}>
          <div className="bg-[var(--bg-secondary)] rounded-2xl w-full max-w-md border border-[var(--border-color)] shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-[var(--border-color)]">
              <h2 className="text-[var(--text-primary)] font-bold"><i className="fas fa-paper-plane mr-2 text-indigo-400" />Enviar Protocolo</h2>
            </div>
            <div className="px-6 py-5">
              <p className="text-[var(--text-secondary)] text-sm mb-4">Enviar email de confirmação ao cliente?</p>
              <div className="bg-[var(--bg-tertiary)] rounded-xl p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--text-secondary)]">Protocolo:</span>
                  <span className="text-[var(--text-primary)] font-bold font-mono">{ticket.protocol}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--text-secondary)]">Cliente:</span>
                  <span className="text-[var(--text-primary)]">{ticket.customer?.name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--text-secondary)]">Email:</span>
                  <span className="text-[var(--text-primary)]">{ticket.customer?.email}</span>
                </div>
              </div>
            </div>
            <div className="flex gap-3 justify-end px-6 py-4 border-t border-[var(--border-color)]">
              <button onClick={() => setShowProtocolModal(false)} disabled={sendingProtocol}
                className="px-4 py-2 rounded-xl text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition">Cancelar</button>
              <button onClick={async () => {
                setSendingProtocol(true)
                try { await sendProtocolEmail(ticket.id); setTicket(prev => ({ ...prev, protocol_sent: true })); setShowProtocolModal(false) }
                catch (e) { toast.error(e.response?.data?.detail || 'Erro') } finally { setSendingProtocol(false) }
              }} disabled={sendingProtocol}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-xl text-sm font-medium transition disabled:opacity-50">
                {sendingProtocol ? <><i className="fas fa-spinner animate-spin mr-1" />Enviando...</> : <><i className="fas fa-paper-plane mr-1" />Enviar</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Helper components ──

function InfoPill({ icon, label, value, color, action }) {
  return (
    <div className="flex items-center gap-1.5">
      <i className={`fas ${icon} text-${color}-400 text-xs`} />
      <span className="text-[var(--text-tertiary)] text-xs">{label}:</span>
      <span className="text-[var(--text-primary)] text-xs font-medium">{value}</span>
      {action && (
        <button onClick={action.onClick} className={`text-${color}-400 hover:text-${color}-300 text-xs ml-0.5`}>
          <i className="fas fa-arrow-right text-xs" />
        </button>
      )}
    </div>
  )
}

function MediaIcon({ category, sourceType }) {
  if (category === 'instagram' || sourceType === 'instagram') {
    return <i className="fab fa-instagram text-pink-400 text-sm" />
  }
  const icons = {
    video: 'fa-play-circle text-red-400',
    foto: 'fa-image text-blue-400',
    link: 'fa-link text-cyan-400',
    politica: 'fa-file-contract text-amber-400',
    manual: 'fa-book text-emerald-400',
  }
  const prefix = sourceType === 'drive' ? 'fab fa-google-drive text-blue-400' : null
  return prefix ? <i className={`${prefix} text-sm`} /> : <i className={`fas ${icons[category] || 'fa-file text-[var(--text-tertiary)]'} text-sm`} />
}
