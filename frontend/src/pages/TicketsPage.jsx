import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useToast } from '../components/Toast'
import { getTickets, getTicketCounts, bulkAssign, bulkUpdate, autoAssign, getUsers, exportTicketsCsv, fetchGmailEmails, fetchGmailHistory, updateTicket, composeEmail, getSentMessages, fetchSpamEmails, rescueFromSpam, bulkRescueFromSpam, rescueAndCreateTicket, uploadAttachment } from '../services/api'
import MetaBadge from '../components/MetaBadge'

const AUTO_REFRESH_MS = 30_000
const MS_PER_HOUR = 3_600_000
const MS_PER_MINUTE = 60_000
const SLA_URGENT_THRESHOLD_MS = MS_PER_HOUR

const STATUS_COLORS = {
  open: 'bg-blue-500/10 text-blue-300',
  in_progress: 'bg-yellow-500/10 text-yellow-300',
  waiting: 'bg-orange-500/10 text-orange-300',
  waiting_supplier: 'bg-purple-500/10 text-purple-300',
  waiting_resend: 'bg-cyan-500/10 text-cyan-300',
  analyzing: 'bg-indigo-500/10 text-indigo-300',
  resolved: 'bg-green-500/10 text-green-300',
  closed: 'bg-gray-500/10 text-gray-300',
  escalated: 'bg-red-500/10 text-red-300',
  archived: 'bg-gray-600/10 text-gray-400',
}

const PRIORITY_COLORS = {
  low: 'bg-gray-500/10 text-gray-300',
  medium: 'bg-blue-500/10 text-blue-300',
  high: 'bg-orange-500/10 text-orange-300',
  urgent: 'bg-red-500/10 text-red-300',
}

const STATUS_LABELS = {
  open: 'Aberto',
  in_progress: 'Em Andamento',
  waiting: 'Aguardando Cliente',
  waiting_supplier: 'Ag. Fornecedor',
  waiting_resend: 'Ag. Reenvio',
  analyzing: 'Em Análise',
  resolved: 'Resolvido',
  closed: 'Fechado',
  escalated: 'Escalado',
  archived: 'Arquivado',
}

const PRIORITY_LABELS = {
  low: 'Baixa', medium: 'Média', high: 'Alta', urgent: 'Urgente',
}

const CATEGORY_LABELS = {
  chargeback: 'Chargeback',
  reclame_aqui: 'Reclame Aqui',
  procon: 'PROCON',
  defeito_garantia: 'Defeito/Garantia',
  troca: 'Troca',
  reenvio: 'Reenvio',
  mau_uso: 'Mau Uso',
  duvida: 'Dúvida',
  rastreamento: 'Rastreamento',
  elogio: 'Elogio',
  sugestao: 'Sugestão',
  outros: 'Outros',
  garantia: 'Garantia',
  carregador: 'Carregador',
  reclamacao: 'Reclamação',
  juridico: 'Jurídico',
  suporte_tecnico: 'Suporte Técnico',
  financeiro: 'Financeiro',
}

const TAG_COLORS = {
  garantia: 'bg-blue-900/30 text-blue-300',
  troca: 'bg-purple-900/30 text-purple-300',
  carregador: 'bg-cyan-900/30 text-cyan-300',
  mau_uso: 'bg-orange-900/30 text-orange-300',
  procon: 'bg-red-900/30 text-red-300',
  chargeback: 'bg-pink-900/30 text-pink-300',
  BLACKLIST: 'bg-red-700/40 text-red-200',
  AUTO_ESCALADO: 'bg-orange-700/40 text-orange-200',
  SLA_ESTOURADO: 'bg-red-700/40 text-red-200',
  SLA_ALERTA: 'bg-yellow-700/40 text-yellow-200',
}

const TAG_LABELS = {
  garantia: 'Garantia', troca: 'Troca', carregador: 'Carregador',
  mau_uso: 'Mau Uso', procon: 'PROCON', chargeback: 'Chargeback',
  duvida: 'Dúvida', reclamacao: 'Reclamação', juridico: 'Jurídico',
  suporte_tecnico: 'Suporte Técnico',
  BLACKLIST: 'Blacklist', AUTO_ESCALADO: 'Auto-Escalado',
  SLA_ESTOURADO: 'SLA Estourado', SLA_ALERTA: 'Alerta SLA',
}

const SORT_OPTIONS = [
  { value: 'oldest', label: 'Mais antigos', icon: 'fa-arrow-up' },
  { value: 'newest', label: 'Mais recentes', icon: 'fa-arrow-down' },
  { value: 'sla', label: 'SLA (urgente primeiro)', icon: 'fa-clock' },
  { value: 'priority', label: 'Prioridade', icon: 'fa-exclamation' },
  { value: 'updated', label: 'Última atualização', icon: 'fa-sync-alt' },
]

const TABS = [
  { key: 'mine', label: 'Privado', icon: 'fa-lock' },
  { key: 'team', label: 'Equipe', icon: 'fa-users' },
  { key: 'active', label: 'Novos', icon: 'fa-inbox' },
  { key: 'responded', label: 'Respondidos', icon: 'fa-reply' },
  { key: 'escalated', label: 'Prioridade', icon: 'fa-exclamation-triangle' },
  { key: 'resolved', label: 'Arquivado', icon: 'fa-archive' },
  { key: 'all', label: 'Todos', icon: 'fa-list' },
]

export default function TicketsPage({ filters, onOpenTicket, user }) {
  const toast = useToast()
  const [tickets, setTickets] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [agents, setAgents] = useState([])
  const [activeTab, setActiveTab] = useState(() => {
    try {
      const prefs = JSON.parse(localStorage.getItem('carbon_prefs') || '{}')
      return prefs.default_tab || 'all'
    } catch { return 'all' }
  })
  const [counts, setCounts] = useState({ total_open: 0, mine: 0, team: 0, unassigned: 0, escalated: 0 })
  const [showFilters, setShowFilters] = useState(false)
  const [showAdvSearch, setShowAdvSearch] = useState(false)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterPriority, setFilterPriority] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterTag, setFilterTag] = useState('')
  const [filterSource, setFilterSource] = useState('')
  const [filterResponse, setFilterResponse] = useState('')
  const [sort, setSort] = useState('oldest')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [customerName, setCustomerName] = useState('')
  const [autoAssigning, setAutoAssigning] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [sortField, setSortField] = useState('')
  const [sortDir, setSortDir] = useState('desc')
  const [showImportModal, setShowImportModal] = useState(false)
  const [importDays, setImportDays] = useState(30)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const [importError, setImportError] = useState(null)
  const [showComposeModal, setShowComposeModal] = useState(false)
  const [composeTo, setComposeTo] = useState('')
  const [composeCc, setComposeCc] = useState('')
  const [composeBcc, setComposeBcc] = useState('')
  const [composeShowCcBcc, setComposeShowCcBcc] = useState(false)
  const [composeSubject, setComposeSubject] = useState('')
  const [composeBody, setComposeBody] = useState('')
  const [composeSending, setComposeSending] = useState(false)
  const [composeAttachments, setComposeAttachments] = useState([])
  const [composeUploading, setComposeUploading] = useState(false)
  const [composeDragging, setComposeDragging] = useState(false)
  const composeAttachmentRef = useRef(null)
  const [editingCell, setEditingCell] = useState(null) // { ticketId, field }
  const [topView, setTopView] = useState('inbox') // 'inbox' | 'sent' | 'spam'
  const [sentMessages, setSentMessages] = useState([])
  const [sentTotal, setSentTotal] = useState(0)
  const [sentPage, setSentPage] = useState(1)
  const [sentLoading, setSentLoading] = useState(false)
  const [spamEmails, setSpamEmails] = useState([])
  const [spamLoading, setSpamLoading] = useState(false)
  const [spamRescuing, setSpamRescuing] = useState(null) // gmail_id being rescued
  const [selectedSpam, setSelectedSpam] = useState(new Set())
  const [bulkRescuing, setBulkRescuing] = useState(false)
  const searchTimerRef = useRef(null)

  // Debounced search: triggers loadTickets after 300ms of inactivity
  const handleSearchInput = useCallback((value) => {
    setSearch(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      setPage(1)
      loadTickets()
    }, 300)
  }, [])

  useEffect(() => {
    return () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current) }
  }, [])

  // Sync external filters from dashboard into local state
  useEffect(() => {
    if (filters && Object.keys(filters).length > 0) {
      if (filters.status) {
        if (['escalated'].includes(filters.status)) {
          setActiveTab('escalated')
        } else if (['resolved', 'closed'].includes(filters.status)) {
          setActiveTab('resolved')
        } else {
          setActiveTab('all')
          setFilterStatus(filters.status)
        }
      }
      if (filters.category) setFilterCategory(filters.category)
      if (filters.priority) setFilterPriority(filters.priority)
    }
  }, [filters])

  const handleComposeAttachmentUpload = async (e) => {
    const files = Array.from(e.target.files)
    if (!files.length) return
    setComposeUploading(true)
    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        const { data } = await uploadAttachment(formData)
        setComposeAttachments(prev => [...prev, data])
      }
    } catch (err) {
      toast.error('Erro ao fazer upload do anexo')
    } finally {
      setComposeUploading(false)
      e.target.value = ''
    }
  }

  const handleComposeDrop = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    setComposeDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (!files.length) return
    setComposeUploading(true)
    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        const { data } = await uploadAttachment(formData)
        setComposeAttachments(prev => [...prev, data])
      }
    } catch (err) {
      toast.error('Falha ao enviar anexo')
    } finally {
      setComposeUploading(false)
    }
  }

  const handleComposeDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setComposeDragging(true)
  }

  const handleComposeDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setComposeDragging(false)
  }

  const loadTickets = async () => {
    try {
      const params = {
        page,
        search: search || undefined,
        priority: filterPriority || undefined,
        category: filterCategory || undefined,
        tag: filterTag || undefined,
        source: filterSource || undefined,
        exclude_sources: 'whatsapp,instagram,facebook',
        sort: sort || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        customer_name: customerName || undefined,
      }
      // Pass through special dashboard filters
      if (filters?.sla_breached) params.sla_breached = true
      if (filters?.legal_risk) params.legal_risk = true
      if (filters?.assigned_to) params.assigned_to = filters.assigned_to
      if (filters?.inbox_id) params.inbox_id = filters.inbox_id

      if (activeTab === 'mine') {
        params.assigned_to = 'me'
        params.exclude_status = 'resolved,closed,archived,waiting,waiting_supplier,waiting_resend,merged'
        if (filterStatus) params.status = filterStatus
      } else if (activeTab === 'team') {
        params.assigned = 'any'
        params.exclude_status = 'resolved,closed,archived,waiting,waiting_supplier,waiting_resend,merged'
        if (filterStatus) params.status = filterStatus
      } else if (activeTab === 'active') {
        // Novos: tickets que precisam de atenção (não inclui respondidos/aguardando)
        params.exclude_status = 'resolved,closed,archived,waiting,waiting_supplier,waiting_resend,merged'
        if (filterStatus) params.status = filterStatus
      } else if (activeTab === 'responded') {
        // Respondidos: tickets já respondidos, aguardando ação do cliente
        params.status = 'waiting,waiting_supplier,waiting_resend'
        if (filterStatus) params.status = filterStatus
      } else if (activeTab === 'resolved') {
        params.status = 'resolved,closed'
      } else if (activeTab === 'escalated') {
        params.status = 'escalated'
      } else if (activeTab === 'archived') {
        params.status = 'archived'
      } else {
        if (filterStatus) params.status = filterStatus
      }

      const { data } = await getTickets(params)
      let filtered = data.tickets
      if (filterResponse === 'awaiting') {
        filtered = filtered.filter(t => !t.first_response_at && !['resolved', 'closed', 'archived'].includes(t.status))
      } else if (filterResponse === 'responded') {
        filtered = filtered.filter(t => !!t.first_response_at)
      }
      setTickets(filtered)
      setTotal(data.total)
    } catch (e) {
      toast.error('Falha ao carregar tickets')
    }
  }

  const loadSentMessages = async () => {
    setSentLoading(true)
    try {
      const { data } = await getSentMessages({ page: sentPage, per_page: 20 })
      setSentMessages(data.items)
      setSentTotal(data.total)
    } catch (e) {
      toast.error('Falha ao carregar mensagens enviadas')
    } finally {
      setSentLoading(false)
    }
  }

  useEffect(() => {
    loadTickets()
  }, [page, filters, activeTab, filterStatus, filterPriority, filterCategory, filterTag, filterSource, filterResponse, sort, dateFrom, dateTo, customerName])

  useEffect(() => {
    getUsers().then(r => setAgents(r.data)).catch(() => {})
  }, [])

  // Counts only refresh on tab change, not every filter
  useEffect(() => {
    getTicketCounts().then(r => setCounts(r.data)).catch(() => {})
  }, [activeTab])

  // Auto-refresh: stable interval that doesn't recreate on filter changes
  const loadTicketsRef = useRef(null)
  loadTicketsRef.current = loadTickets
  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        loadTicketsRef.current()
      }
    }, AUTO_REFRESH_MS)
    return () => clearInterval(interval)
  }, [])

  const loadSpamEmails = async () => {
    setSpamLoading(true)
    setSelectedSpam(new Set())
    try {
      const { data } = await fetchSpamEmails()
      setSpamEmails(data.emails || [])
    } catch (e) {
      toast.error('Falha ao carregar emails de spam')
    } finally {
      setSpamLoading(false)
    }
  }

  const handleRescueSpam = async (email) => {
    setSpamRescuing(email.gmail_id)
    try {
      await rescueFromSpam(email.gmail_id)
      setSpamEmails(prev => prev.filter(e => e.gmail_id !== email.gmail_id))
      toast.success('Email movido para a caixa de entrada')
    } catch (e) {
      toast.error('Falha ao resgatar email')
    } finally {
      setSpamRescuing(null)
    }
  }

  const handleRescueAndCreate = async (email) => {
    setSpamRescuing(email.gmail_id)
    try {
      const { data } = await rescueAndCreateTicket(email.gmail_id, {
        from_email: email.from_email,
        from_name: email.from_name,
        subject: email.subject,
        body_text: email.body_text,
        thread_id: email.thread_id,
      })
      setSpamEmails(prev => prev.filter(e => e.gmail_id !== email.gmail_id))
      toast.success(data.message || 'Ticket criado com sucesso')
    } catch (e) {
      toast.error('Falha ao criar ticket do spam')
    } finally {
      setSpamRescuing(null)
    }
  }

  const toggleSpamSelect = (gmailId) => {
    setSelectedSpam(prev => {
      const next = new Set(prev)
      if (next.has(gmailId)) next.delete(gmailId)
      else next.add(gmailId)
      return next
    })
  }

  const toggleSpamSelectAll = () => {
    if (selectedSpam.size === spamEmails.length) {
      setSelectedSpam(new Set())
    } else {
      setSelectedSpam(new Set(spamEmails.map(e => e.gmail_id)))
    }
  }

  const handleBulkRescueSpam = async () => {
    if (selectedSpam.size === 0) return
    setBulkRescuing(true)
    try {
      const ids = Array.from(selectedSpam)
      const { data } = await bulkRescueFromSpam(ids)
      const rescuedSet = new Set(data.rescued_ids || ids)
      setSpamEmails(prev => prev.filter(e => !rescuedSet.has(e.gmail_id)))
      setSelectedSpam(new Set())
      const msg = data.failed > 0
        ? `${data.rescued} resgatados, ${data.failed} falharam`
        : `${data.rescued} emails movidos para a caixa de entrada`
      toast.success(msg)
    } catch (e) {
      toast.error('Falha ao resgatar emails em massa')
    } finally {
      setBulkRescuing(false)
    }
  }

  useEffect(() => {
    if (topView === 'sent') loadSentMessages()
    if (topView === 'spam') loadSpamEmails()
  }, [topView, sentPage])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    loadTickets()
  }

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setPage(1)
    setSelected(new Set())
    setFilterStatus('')
  }

  const toggleSelect = (id) => {
    const next = new Set(selected)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelected(next)
  }

  const toggleAll = () => {
    if (selected.size === sortedTickets.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(sortedTickets.map(t => t.id)))
    }
  }

  const handleBulkAction = async (action, value) => {
    try {
      const payload = { ticket_ids: [...selected] }
      if (action === 'assign') payload.assigned_to = value
      else if (action === 'status') payload.status = value
      else if (action === 'priority') payload.priority = value

      if (action === 'assign') {
        await bulkAssign(payload)
      } else {
        await bulkUpdate(payload)
      }
      setSelected(new Set())
      loadTickets()
    } catch (e) {
      toast.error('Falha na ação em lote')
    }
  }

  const handleAutoAssign = async () => {
    setAutoAssigning(true)
    try {
      const { data } = await autoAssign()
      loadTickets()
      toast.success(`${data.assigned} ticket(s) atribuído(s) automaticamente`)
    } catch (e) {
      toast.error('Falha na atribuição automática')
    } finally {
      setAutoAssigning(false)
    }
  }

  const handleExportCsv = async () => {
    setExporting(true)
    try {
      const params = {}
      if (filterStatus) params.status = filterStatus
      if (filterPriority) params.priority = filterPriority
      if (filterCategory) params.category = filterCategory
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo

      const response = await exportTicketsCsv(params)
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `tickets_${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      console.error(e)
      toast.error('Erro ao exportar CSV')
    } finally {
      setExporting(false)
    }
  }

  const clearFilters = () => {
    setFilterStatus('')
    setFilterPriority('')
    setFilterCategory('')
    setFilterTag('')
    setFilterSource('')
    setFilterResponse('')
    setSort('oldest')
    setSearch('')
    setDateFrom('')
    setDateTo('')
    setCustomerName('')
    setPage(1)
  }

  const hasActiveFilters = filterStatus || filterPriority || filterCategory || filterTag || filterSource || filterResponse || (sort && sort !== 'oldest') || dateFrom || dateTo || customerName

  const handleInlineUpdate = async (ticketId, field, value) => {
    try {
      if (field === 'assigned_to') {
        await bulkAssign({ ticket_ids: [ticketId], assigned_to: value })
      } else {
        await updateTicket(ticketId, { [field]: value })
      }
      setTickets(prev => prev.map(t => {
        if (t.id !== ticketId) return t
        if (field === 'assigned_to') {
          const agent = agents.find(a => a.id === parseInt(value))
          return { ...t, assigned_to: value, agent_name: agent?.name || '' }
        }
        return { ...t, [field]: value }
      }))
      if (field === 'assigned_to') {
        toast.success(value ? 'Ticket atribuído com sucesso' : 'Ticket devolvido à caixa de entrada')
      } else if (field === 'status') {
        toast.success('Status atualizado')
      } else if (field === 'priority') {
        toast.success('Prioridade atualizada')
      }
    } catch (e) {
      toast.error('Erro ao atualizar ticket')
      console.error('Inline update failed:', e)
    }
    setEditingCell(null)
  }

  const handleAddTag = async (ticketId, currentTags, newTag) => {
    if (!newTag || currentTags.includes(newTag)) { setEditingCell(null); return }
    const updated = [...currentTags, newTag]
    try {
      await updateTicket(ticketId, { tags: updated })
      setTickets(prev => prev.map(t => t.id === ticketId ? { ...t, tags: updated } : t))
    } catch (e) { toast.error('Falha ao adicionar tag') }
    setEditingCell(null)
  }

  const handleRemoveTag = async (ticketId, currentTags, tagToRemove) => {
    const updated = currentTags.filter(t => t !== tagToRemove)
    try {
      await updateTicket(ticketId, { tags: updated })
      setTickets(prev => prev.map(t => t.id === ticketId ? { ...t, tags: updated } : t))
    } catch (e) { toast.error('Falha ao remover tag') }
  }

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  const PRIORITY_ORDER = { urgent: 4, high: 3, medium: 2, low: 1 }
  const STATUS_ORDER = { escalated: 9, open: 8, in_progress: 7, analyzing: 6, waiting: 5, waiting_supplier: 4, waiting_resend: 3, resolved: 2, closed: 1 }

  const sortedTickets = React.useMemo(() => {
    if (!sortField) return tickets
    const sorted = [...tickets].sort((a, b) => {
      let va, vb
      switch (sortField) {
        case 'number': va = a.number || 0; vb = b.number || 0; break
        case 'subject': va = (a.subject || '').toLowerCase(); vb = (b.subject || '').toLowerCase(); break
        case 'customer': va = (a.customer?.name || '').toLowerCase(); vb = (b.customer?.name || '').toLowerCase(); break
        case 'status': va = STATUS_ORDER[a.status] || 0; vb = STATUS_ORDER[b.status] || 0; break
        case 'priority': va = PRIORITY_ORDER[a.priority] || 0; vb = PRIORITY_ORDER[b.priority] || 0; break
        case 'sla':
          va = a.sla_deadline ? new Date(a.sla_deadline).getTime() : Infinity
          vb = b.sla_deadline ? new Date(b.sla_deadline).getTime() : Infinity
          break
        case 'created_at': va = a.created_at ? new Date(a.created_at).getTime() : 0; vb = b.created_at ? new Date(b.created_at).getTime() : 0; break
        case 'agent': va = (a.agent_name || '').toLowerCase(); vb = (b.agent_name || '').toLowerCase(); break
        case 'tags': va = (a.tags || []).length; vb = (b.tags || []).length; break
        default: return 0
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
    return sorted
  }, [tickets, sortField, sortDir])

  const getSlaStatus = (ticket) => {
    if (ticket.sla_breached) return 'breached'
    if (!ticket.sla_deadline) return 'ok'
    const diff = new Date(ticket.sla_deadline) - new Date()
    if (diff <= 0) return 'breached'
    if (diff < SLA_URGENT_THRESHOLD_MS) return 'urgent'
    return 'ok'
  }

  const formatSla = (ticket) => {
    if (!ticket.sla_deadline) return '-'
    const diff = new Date(ticket.sla_deadline) - new Date()
    if (diff <= 0) return 'Estourado'
    const h = Math.floor(diff / MS_PER_HOUR)
    const m = Math.floor((diff % MS_PER_HOUR) / MS_PER_MINUTE)
    return `${h}h ${m}m`
  }

  // Status options differ by tab
  const statusOptions = activeTab === 'active'
    ? Object.entries(STATUS_LABELS).filter(([k]) => !['resolved', 'closed'].includes(k))
    : activeTab === 'resolved'
    ? []
    : activeTab === 'escalated'
    ? []
    : Object.entries(STATUS_LABELS)

  const sentLastPage = Math.max(1, Math.ceil(sentTotal / 20))

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] p-8">
      {/* Top-level tabs: Caixa de Entrada | Enviados */}
      <div className="flex gap-1 mb-6">
        <button
          onClick={() => setTopView('inbox')}
          className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
            topView === 'inbox'
              ? 'bg-indigo-600 text-white'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
          }`}
        >
          <i className="fas fa-inbox mr-2" />Caixa de Entrada
        </button>
        <button
          onClick={() => setTopView('sent')}
          className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
            topView === 'sent'
              ? 'bg-indigo-600 text-white'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
          }`}
        >
          <i className="fas fa-paper-plane mr-2" />Enviados
        </button>
        <button
          onClick={() => setTopView('spam')}
          className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
            topView === 'spam'
              ? 'bg-red-600 text-white'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
          }`}
        >
          <i className="fas fa-shield-alt mr-2" />Spam
          {spamEmails.length > 0 && (
            <span className="ml-2 bg-red-500/20 text-red-300 text-xs px-1.5 py-0.5 rounded-full">{spamEmails.length}</span>
          )}
        </button>
      </div>

      {/* Spam View */}
      {topView === 'spam' ? (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-[var(--text-primary)]">
                <i className="fas fa-shield-alt mr-2 text-red-400" />Emails no Spam do Gmail
              </h2>
              <p className="text-sm text-[var(--text-tertiary)] mt-1">
                Emails que caíram no spam. Resgate os que forem de clientes reais.
              </p>
            </div>
            <button onClick={loadSpamEmails} disabled={spamLoading}
              className="px-4 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-lg hover:bg-[var(--bg-tertiary)] transition text-sm disabled:opacity-50">
              <i className={`fas fa-sync-alt mr-2 ${spamLoading ? 'animate-spin' : ''}`} />Atualizar
            </button>
          </div>

          {/* Barra de acao flutuante quando tem itens selecionados */}
          {selectedSpam.size > 0 && (
            <div className="mb-3 flex items-center gap-3 p-3 rounded-xl border border-blue-500/30 bg-blue-500/10">
              <span className="text-sm text-blue-300 font-medium">
                {selectedSpam.size} selecionado{selectedSpam.size > 1 ? 's' : ''}
              </span>
              <div className="flex gap-2 ml-auto">
                <button
                  onClick={handleBulkRescueSpam}
                  disabled={bulkRescuing}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-medium transition disabled:opacity-50"
                >
                  <i className={`fas ${bulkRescuing ? 'fa-spinner animate-spin' : 'fa-inbox'} mr-1.5`} />
                  Mover para Caixa de Entrada
                </button>
                <button
                  onClick={async () => {
                    if (!confirm(`Excluir permanentemente ${selectedSpam.size} email(s)?`)) return
                    setBulkRescuing(true)
                    try {
                      const ids = Array.from(selectedSpam)
                      // Apenas remove da lista local (Gmail ja marcou como spam)
                      setSpamEmails(prev => prev.filter(e => !selectedSpam.has(e.gmail_id)))
                      setSelectedSpam(new Set())
                      toast.success(`${ids.length} email(s) removido(s)`)
                    } finally { setBulkRescuing(false) }
                  }}
                  disabled={bulkRescuing}
                  className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/40 text-red-400 rounded-lg text-xs font-medium transition disabled:opacity-50"
                >
                  <i className="fas fa-trash mr-1.5" />Excluir
                </button>
                <button
                  onClick={() => setSelectedSpam(new Set())}
                  className="px-3 py-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-lg text-xs transition"
                >
                  Limpar
                </button>
              </div>
            </div>
          )}

          <div className="bg-[var(--bg-secondary)] rounded-xl overflow-hidden border border-[var(--border-color)]">
            {spamLoading ? (
              <div className="p-12 text-center text-[var(--text-secondary)]">Carregando spam...</div>
            ) : spamEmails.length === 0 ? (
              <div className="p-12 text-center text-[var(--text-secondary)]">
                <i className="fas fa-check-circle text-4xl mb-3 text-emerald-400 opacity-50" />
                <p>Nenhum email no spam</p>
              </div>
            ) : (
              <div className="divide-y divide-[var(--border-color)]">
                {/* Header: selecionar todos */}
                <div className="px-4 py-2.5 flex items-center gap-3 bg-[var(--bg-tertiary)]">
                  <input
                    type="checkbox"
                    checked={selectedSpam.size === spamEmails.length && spamEmails.length > 0}
                    onChange={toggleSpamSelectAll}
                    className="w-4 h-4 rounded accent-blue-500 cursor-pointer"
                  />
                  <span className="text-xs text-[var(--text-secondary)]">
                    {selectedSpam.size === spamEmails.length ? 'Desmarcar todos' : 'Selecionar todos'}
                  </span>
                  <span className="text-xs text-[var(--text-tertiary)] ml-auto">{spamEmails.length} email{spamEmails.length > 1 ? 's' : ''}</span>
                </div>
                {spamEmails.map(email => (
                  <div key={email.gmail_id}
                    className={`p-4 hover:bg-[var(--bg-tertiary)] transition-colors ${selectedSpam.has(email.gmail_id) ? 'bg-blue-500/5' : ''}`}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={selectedSpam.has(email.gmail_id)}
                        onChange={() => toggleSpamSelect(email.gmail_id)}
                        className="w-4 h-4 rounded accent-blue-500 cursor-pointer mt-1 flex-shrink-0"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[var(--text-primary)] font-medium text-sm truncate">{email.from_name}</span>
                          <span className="text-[var(--text-tertiary)] text-xs">&lt;{email.from_email}&gt;</span>
                        </div>
                        <p className="text-[var(--text-primary)] text-sm font-medium truncate">{email.subject}</p>
                        <p className="text-[var(--text-tertiary)] text-xs mt-1 line-clamp-2">{email.snippet || email.body_text?.substring(0, 150)}</p>
                        {email.date && (
                          <p className="text-[var(--text-tertiary)] text-xs mt-2">
                            <i className="far fa-clock mr-1" />
                            {new Date(email.date).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleRescueSpam(email)}
                          disabled={spamRescuing === email.gmail_id}
                          className="px-3 py-1.5 bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 rounded-lg text-xs font-medium transition disabled:opacity-50"
                          title="Mover para caixa de entrada"
                        >
                          <i className={`fas ${spamRescuing === email.gmail_id ? 'fa-spinner animate-spin' : 'fa-inbox'} mr-1`} />
                          Resgatar
                        </button>
                        <button
                          onClick={() => handleRescueAndCreate(email)}
                          disabled={spamRescuing === email.gmail_id}
                          className="px-3 py-1.5 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/40 rounded-lg text-xs font-medium transition disabled:opacity-50"
                          title="Resgatar e criar ticket"
                        >
                          <i className={`fas ${spamRescuing === email.gmail_id ? 'fa-spinner animate-spin' : 'fa-plus'} mr-1`} />
                          Criar Ticket
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : topView === 'sent' ? (
        <div>
          <div className="bg-[var(--bg-secondary)] rounded-xl overflow-hidden border border-[var(--border-color)]">
            {sentLoading ? (
              <div className="p-12 text-center text-[var(--text-secondary)]">Carregando...</div>
            ) : sentMessages.length === 0 ? (
              <div className="p-12 text-center text-[var(--text-secondary)]">
                <i className="fas fa-paper-plane text-4xl mb-3 opacity-30" />
                <p>Nenhuma mensagem enviada</p>
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-color)]">
                    <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Ticket</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Destinatario</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Assunto</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Preview</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Enviado por</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Data</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-color)]">
                  {sentMessages.map(msg => (
                    <tr key={msg.message_id}
                      className="hover:bg-[var(--bg-tertiary)] cursor-pointer transition-colors"
                      onClick={() => onOpenTicket(msg.ticket_id)}>
                      <td className="px-6 py-4 text-[var(--text-secondary)] text-sm font-medium">#{msg.ticket_number}</td>
                      <td className="px-6 py-4">
                        <div className="text-[var(--text-primary)] text-sm">{msg.customer_name || msg.customer_email || '-'}</div>
                        <div className="text-[var(--text-tertiary)] text-xs">{msg.customer_email || ''}</div>
                      </td>
                      <td className="px-6 py-4 text-[var(--text-primary)] text-sm max-w-[200px] truncate">{msg.ticket_subject}</td>
                      <td className="px-6 py-4 text-[var(--text-secondary)] text-sm max-w-[250px] truncate">{msg.body_text}</td>
                      <td className="px-6 py-4 text-[var(--text-secondary)] text-sm">{msg.sender_name || '-'}</td>
                      <td className="px-6 py-4 text-[var(--text-secondary)] text-sm">
                        {msg.created_at ? (
                          <>
                            <div>{new Date(msg.created_at).toLocaleDateString('pt-BR')}</div>
                            <div className="text-[var(--text-tertiary)] text-xs">{new Date(msg.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</div>
                          </>
                        ) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {sentTotal > 20 && (
            <div className="flex justify-center gap-2 mt-6">
              <button disabled={sentPage <= 1} onClick={() => setSentPage(1)}
                className="px-3 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-lg disabled:opacity-30 text-sm font-medium">&laquo;</button>
              <button disabled={sentPage <= 1} onClick={() => setSentPage(p => p - 1)}
                className="px-4 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-lg disabled:opacity-30 text-sm font-medium">
                <i className="fas fa-chevron-left mr-2" />Anterior
              </button>
              <span className="px-4 py-2 text-[var(--text-secondary)] text-sm font-medium">
                Pagina {sentPage} de {sentLastPage}
              </span>
              <button disabled={sentPage >= sentLastPage} onClick={() => setSentPage(p => p + 1)}
                className="px-4 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-lg disabled:opacity-30 text-sm font-medium">
                Proxima<i className="fas fa-chevron-right ml-2" />
              </button>
              <button disabled={sentPage >= sentLastPage} onClick={() => setSentPage(sentLastPage)}
                className="px-3 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-lg disabled:opacity-30 text-sm font-medium">&raquo;</button>
            </div>
          )}
        </div>
      ) : (
      <>
      {/* Page Header with Counter Cards */}
      <div className="mb-6">
        <div className="grid grid-cols-5 gap-4 mb-6">
          <button onClick={() => handleTabChange('mine')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-4 text-left transition hover:border-indigo-500/30 ${activeTab === 'mine' ? 'border-indigo-500/40 ring-1 ring-indigo-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-lock text-indigo-400 text-sm" />
              <span className="text-[var(--text-tertiary)] text-xs">Privado</span>
            </div>
            <p className="text-2xl font-bold text-[var(--text-primary)]">{counts.mine}</p>
          </button>
          <button onClick={() => handleTabChange('team')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-4 text-left transition hover:border-teal-500/30 ${activeTab === 'team' ? 'border-teal-500/40 ring-1 ring-teal-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-users text-teal-400 text-sm" />
              <span className="text-[var(--text-tertiary)] text-xs">Equipe</span>
            </div>
            <p className="text-2xl font-bold text-[var(--text-primary)]">{counts.team}</p>
          </button>
          <button onClick={() => handleTabChange('active')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-4 text-left transition hover:border-orange-500/30 ${activeTab === 'active' ? 'border-orange-500/40 ring-1 ring-orange-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-inbox text-orange-400 text-sm" />
              <span className="text-[var(--text-tertiary)] text-xs">Novos Tickets</span>
            </div>
            <p className="text-2xl font-bold text-orange-400">{counts.unassigned}</p>
          </button>
          <button onClick={() => handleTabChange('escalated')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-4 text-left transition hover:border-red-500/30 ${activeTab === 'escalated' ? 'border-red-500/40 ring-1 ring-red-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-exclamation-triangle text-red-400 text-sm" />
              <span className="text-[var(--text-tertiary)] text-xs">Prioridade</span>
            </div>
            <p className="text-2xl font-bold text-red-400">{counts.escalated}</p>
          </button>
          <button onClick={() => handleTabChange('all')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-4 text-left transition hover:border-blue-500/30 ${activeTab === 'all' ? 'border-blue-500/40 ring-1 ring-blue-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-list text-blue-400 text-sm" />
              <span className="text-[var(--text-tertiary)] text-xs">Todos</span>
            </div>
            <p className="text-2xl font-bold text-[var(--text-primary)]">{counts.total_open}</p>
          </button>
        </div>
      </div>

      {/* Top Action Bar */}
      <div className="mb-6 flex flex-col gap-4">
        {/* Tabs */}
        <div className="flex gap-1">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key)}
              className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-indigo-600 text-white'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
              }`}
            >
              <i className={`fas ${tab.icon} mr-2`} />{tab.label}
            </button>
          ))}
        </div>

        {/* Search and Controls */}
        <div className="flex gap-3 flex-wrap items-center">
          <form onSubmit={handleSearch} className="flex gap-2 flex-1 min-w-64">
            <div className="flex-1 relative">
              <input
                value={search}
                onChange={(e) => handleSearchInput(e.target.value)}
                placeholder="Buscar ticket..."
                className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-4 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
              />
              <i className="fas fa-search absolute right-3 top-3 text-[var(--text-tertiary)] text-sm" />
            </div>
            <button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors">
              Buscar
            </button>
          </form>

          {/* Right-side Controls */}
          <div className="flex gap-2 items-center flex-wrap">
            <button
              onClick={() => { setShowAdvSearch(!showAdvSearch); setShowFilters(false) }}
              className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                showAdvSearch 
                  ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30' 
                  : 'text-[var(--text-secondary)] bg-[var(--bg-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <i className="fas fa-sliders-h" />
              Avançado
            </button>

            <button
              onClick={() => { setShowFilters(!showFilters); setShowAdvSearch(false) }}
              className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                hasActiveFilters 
                  ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30' 
                  : 'text-[var(--text-secondary)] bg-[var(--bg-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <i className="fas fa-filter" />
              Filtros
              {hasActiveFilters && <span className="text-xs font-bold">({[filterStatus, filterPriority, filterCategory, filterTag, filterSource, sort !== "oldest" && sort, dateFrom, dateTo, customerName].filter(Boolean).length})</span>}
            </button>

            <select 
              value={sort} 
              onChange={(e) => { setSort(e.target.value); setPage(1) }}
              className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                sort && sort !== 'oldest'
                  ? 'bg-amber-600/20 text-amber-300 border border-amber-500/30'
                  : 'text-[var(--text-secondary)] bg-[var(--bg-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <option value="" disabled>Ordenar por...</option>
              {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>

            <button
              onClick={async () => {
                setRefreshing(true)
                try {
                  await fetchGmailEmails()
                  await loadTickets()
                } catch (e) { toast.error('Falha ao buscar emails') }
                finally { setRefreshing(false) }
              }}
              disabled={refreshing}
              className="px-4 py-2.5 rounded-lg text-sm font-medium transition-colors text-[var(--text-secondary)] bg-[var(--bg-secondary)] hover:text-[var(--text-primary)] disabled:opacity-50"
              title="Buscar novos emails"
            >
              <i className={`fas fa-envelope ${refreshing ? 'animate-pulse' : ''} mr-2`} />
              {refreshing ? 'Buscando...' : 'Atualizar'}
            </button>

            <button
              onClick={() => setShowComposeModal(true)}
              className="px-4 py-2.5 rounded-lg text-sm font-medium transition-colors text-blue-300 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30"
              title="Escrever novo e-mail"
            >
              <i className="fas fa-pen-to-square mr-2" />
              Novo E-mail
            </button>

            <button
              onClick={() => setShowImportModal(true)}
              className="px-4 py-2.5 rounded-lg text-sm font-medium transition-colors text-purple-300 bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30"
              title="Importar histórico de emails"
            >
              <i className="fas fa-clock-rotate-left mr-2" />
              Histórico
            </button>

            <button
              onClick={handleExportCsv}
              disabled={exporting}
              className="px-4 py-2.5 rounded-lg text-sm font-medium transition-colors text-emerald-300 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 disabled:opacity-50"
              title="Exportar como CSV"
            >
              <i className={`fas fa-file-csv ${exporting ? 'animate-pulse' : ''} mr-2`} />
              {exporting ? 'Exportando...' : 'Exportar'}
            </button>

            <button
              onClick={handleAutoAssign}
              disabled={autoAssigning}
              className="px-4 py-2.5 rounded-lg text-sm font-medium transition-colors text-green-300 bg-green-600/20 hover:bg-green-600/30 border border-green-500/30 disabled:opacity-50"
              title="Distribuir tickets sem agente automaticamente"
            >
              <i className={`fas fa-magic ${autoAssigning ? 'animate-spin' : ''} mr-2`} />
              {autoAssigning ? 'Atribuindo...' : 'Auto-Atribuir'}
            </button>
          </div>
        </div>
      </div>

      {/* Advanced Search Panel */}
      {showAdvSearch && (
        <div className="bg-[var(--bg-secondary)] rounded-xl p-6 mb-6 border border-[var(--border-color)]">
          <div className="flex items-center gap-3 mb-4">
            <i className="fas fa-sliders-h text-purple-400 text-lg" />
            <h3 className="text-[var(--text-primary)] font-semibold">Busca Avançada</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="text-[var(--text-secondary)] text-xs font-medium block mb-2">Nome do Cliente</label>
              <input
                value={customerName}
                onChange={(e) => { setCustomerName(e.target.value); setPage(1) }}
                placeholder="Ex: João Silva"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-xs font-medium block mb-2">Data Início</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(1) }}
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-xs font-medium block mb-2">Data Fim</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(1) }}
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
            </div>
            <div className="flex items-end">
              <button onClick={clearFilters} className="text-red-400 hover:text-red-300 text-sm font-medium px-3 py-2">
                <i className="fas fa-times mr-2" />Limpar tudo
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      {showFilters && (
        <div className="bg-[var(--bg-secondary)] rounded-xl p-6 mb-6 border border-[var(--border-color)]">
          <div className="flex items-center gap-3 mb-4">
            <i className="fas fa-filter text-blue-400 text-lg" />
            <h3 className="text-[var(--text-primary)] font-semibold">Filtros</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {statusOptions.length > 0 && (
              <div>
                <label className="text-[var(--text-secondary)] text-xs font-medium block mb-2">Status</label>
                <select value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setPage(1) }}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                  <option value="">Todos</option>
                  {statusOptions.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
            )}
            <div>
              <label className="text-[var(--text-secondary)] text-xs font-medium block mb-2">Prioridade</label>
              <select value={filterPriority} onChange={(e) => { setFilterPriority(e.target.value); setPage(1) }}
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                <option value="">Todas</option>
                {Object.entries(PRIORITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-xs font-medium block mb-2">Categoria</label>
              <select value={filterCategory} onChange={(e) => { setFilterCategory(e.target.value); setPage(1) }}
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                <option value="">Todas</option>
                {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-xs font-medium block mb-2">Tag</label>
              <select value={filterTag} onChange={(e) => { setFilterTag(e.target.value); setPage(1) }}
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                <option value="">Todas</option>
                {Object.entries(TAG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-xs font-medium block mb-2">Canal</label>
              <select value={filterSource} onChange={(e) => { setFilterSource(e.target.value); setPage(1) }}
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                <option value="">Todos</option>
                <option value="web">Web</option>
                <option value="gmail">Email</option>
                <option value="slack">Slack</option>
              </select>
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-xs font-medium block mb-2">Resposta</label>
              <select value={filterResponse} onChange={(e) => { setFilterResponse(e.target.value); setPage(1) }}
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                <option value="">Todos</option>
                <option value="awaiting">Aguardando resposta</option>
                <option value="responded">Respondido</option>
              </select>
            </div>
            {hasActiveFilters && (
              <div className="flex items-end">
                <button onClick={clearFilters} className="w-full text-red-400 hover:text-red-300 text-sm font-medium px-3 py-2 hover:bg-[var(--bg-tertiary)] rounded-lg transition-colors">
                  <i className="fas fa-times mr-2" />Limpar
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Bulk Actions Bar */}
      {selected.size > 0 && (
        <div className="bg-indigo-600/10 border border-indigo-500/30 rounded-xl p-4 mb-6 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <i className="fas fa-check-square text-indigo-400" />
            <span className="text-indigo-300 text-sm font-medium">{selected.size} selecionado{selected.size !== 1 ? 's' : ''}</span>
          </div>

          <div className="h-6 w-px bg-indigo-500/30" />

          <select
            onChange={(e) => e.target.value && handleBulkAction('assign', e.target.value)}
            className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            defaultValue=""
          >
            <option value="">Atribuir a...</option>
            {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>

          <select
            onChange={(e) => e.target.value && handleBulkAction('status', e.target.value)}
            className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            defaultValue=""
          >
            <option value="">Mudar status...</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>

          <select
            onChange={(e) => e.target.value && handleBulkAction('priority', e.target.value)}
            className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            defaultValue=""
          >
            <option value="">Mudar prioridade...</option>
            {Object.entries(PRIORITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>

          <button onClick={() => setSelected(new Set())} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-sm ml-auto font-medium">
            <i className="fas fa-times mr-2" />Limpar
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-[var(--bg-secondary)] rounded-xl overflow-hidden border border-[var(--border-color)]">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-color)]">
              <th className="px-6 py-4 text-left w-12">
                <input type="checkbox" onChange={toggleAll} checked={selected.size === sortedTickets.length && sortedTickets.length > 0} className="rounded" />
              </th>
              {[
                { key: 'number', label: '#' },
                { key: 'subject', label: 'Assunto' },
                { key: 'customer', label: 'Cliente' },
                { key: 'status', label: 'Status' },
                { key: 'priority', label: 'Prioridade' },
                { key: 'sla', label: activeTab === 'resolved' ? 'Resolvido em' : 'SLA' },
                { key: 'created_at', label: 'Recebido' },
                { key: 'agent', label: 'Agente' },
                { key: 'tags', label: 'Tags' },
              ].map(col => (
                <th key={col.key}
                  onClick={() => toggleSort(col.key)}
                  className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide cursor-pointer select-none group transition-colors hover:text-[var(--accent)]"
                  style={{ color: sortField === col.key ? 'var(--accent)' : 'var(--text-secondary)' }}
                >
                  <span className="inline-flex items-center gap-1.5">
                    {col.label}
                    {sortField === col.key ? (
                      <i className={`fas fa-arrow-${sortDir === 'asc' ? 'up' : 'down'} text-[10px]`} />
                    ) : (
                      <i className="fas fa-sort text-[10px] opacity-0 group-hover:opacity-40 transition-opacity" />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-color)]">
            {sortedTickets.map(ticket => {
              const slaStatus = getSlaStatus(ticket)
              return (
                <tr
                  key={ticket.id}
                  className={`hover:bg-[var(--bg-tertiary)] cursor-pointer transition-colors ${
                    slaStatus === 'breached' && !['resolved', 'closed'].includes(ticket.status) ? 'bg-red-900/5' : ''
                  } ${ticket.status === 'escalated' ? 'border-l-4 border-l-red-500' : ''}`}
                  onClick={() => onOpenTicket(ticket.id)}
                >
                  <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selected.has(ticket.id)}
                      onChange={() => toggleSelect(ticket.id)}
                      className="rounded"
                    />
                  </td>
                  <td className="px-6 py-4 text-[var(--text-secondary)] text-sm font-medium">#{ticket.number}</td>
                  <td className="px-6 py-4">
                    <div>
                      <div className="text-[var(--text-primary)] text-sm font-medium mb-1">{ticket.subject}</div>
                      <div className="flex gap-1.5 flex-wrap">
                        {ticket.legal_risk && (
                          <span className="text-red-300 text-xs font-medium"><i className="fas fa-exclamation-triangle mr-1" />Jurídico</span>
                        )}
                        {ticket.source && ticket.source !== 'web' && (
                          <MetaBadge source={ticket.source} aiAutoMode={ticket.ai_auto_mode} />
                        )}
                        {ticket.customer?.is_repeat && (
                          <span className="text-purple-300 text-xs font-medium"><i className="fas fa-redo mr-1" /></span>
                        )}
                        {ticket.customer?.is_blacklisted && (
                          <span className="text-red-400 text-xs font-bold"><i className="fas fa-ban mr-1" />Blacklist</span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-[var(--text-secondary)] text-sm">{ticket.customer?.name || ticket.customer_name || '-'}</div>
                    {!['resolved', 'closed', 'archived'].includes(ticket.status) && (
                      <div className="mt-0.5">
                        {ticket.first_response_at ? (
                          <span className="text-green-400 text-[10px] font-medium inline-flex items-center gap-1">
                            <i className="fas fa-check-circle" /> Respondido
                          </span>
                        ) : (
                          <span className="text-red-400 text-[10px] font-medium inline-flex items-center gap-1">
                            <i className="fas fa-circle" /> Aguardando resposta
                          </span>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4" onClick={e => e.stopPropagation()}>
                    {editingCell?.ticketId === ticket.id && editingCell?.field === 'status' ? (
                      <select autoFocus value={ticket.status}
                        onChange={e => handleInlineUpdate(ticket.id, 'status', e.target.value)}
                        onBlur={() => setEditingCell(null)}
                        className="bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-2 py-1 text-[var(--text-primary)] text-xs focus:outline-none focus:ring-1 focus:ring-[var(--accent)]">
                        {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    ) : (
                      <span onClick={() => setEditingCell({ ticketId: ticket.id, field: 'status' })}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium inline-block cursor-pointer hover:ring-2 hover:ring-[var(--accent)]/30 transition ${STATUS_COLORS[ticket.status] || ''}`}>
                        {STATUS_LABELS[ticket.status] || ticket.status}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4" onClick={e => e.stopPropagation()}>
                    {editingCell?.ticketId === ticket.id && editingCell?.field === 'priority' ? (
                      <select autoFocus value={ticket.priority}
                        onChange={e => handleInlineUpdate(ticket.id, 'priority', e.target.value)}
                        onBlur={() => setEditingCell(null)}
                        className="bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-2 py-1 text-[var(--text-primary)] text-xs focus:outline-none focus:ring-1 focus:ring-[var(--accent)]">
                        {Object.entries(PRIORITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    ) : (
                      <span onClick={() => setEditingCell({ ticketId: ticket.id, field: 'priority' })}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium inline-block cursor-pointer hover:ring-2 hover:ring-[var(--accent)]/30 transition ${PRIORITY_COLORS[ticket.priority] || ''}`}>
                        {PRIORITY_LABELS[ticket.priority] || ticket.priority}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {['resolved', 'closed'].includes(ticket.status) ? (
                      <div className="text-[var(--text-secondary)] text-sm">
                        {ticket.resolved_at ? (() => {
                          const dt = ticket.resolved_at
                          return dt ? (
                            <>
                              <div>{new Date(dt).toLocaleDateString('pt-BR')}</div>
                              <div className="text-[var(--text-tertiary)] text-xs">{new Date(dt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</div>
                            </>
                          ) : '-'
                        })() : '-'}
                      </div>
                    ) : (
                      <div className={`text-sm font-medium ${
                        slaStatus === 'breached' ? 'text-red-400' : slaStatus === 'urgent' ? 'text-orange-400' : 'text-[var(--text-secondary)]'
                      }`}>
                        {formatSla(ticket)}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-[var(--text-secondary)] text-sm">
                    {(() => {
                      const dt = ticket.created_at
                      return dt ? (
                        <>
                          <div>{new Date(dt).toLocaleDateString('pt-BR')}</div>
                          <div className="text-[var(--text-tertiary)] text-xs">{new Date(dt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</div>
                        </>
                      ) : '-'
                    })()}
                  </td>
                  <td className="px-6 py-4" onClick={e => e.stopPropagation()}>
                    {editingCell?.ticketId === ticket.id && editingCell?.field === 'assigned_to' ? (
                      <select autoFocus value={ticket.assigned_to || ''}
                        onChange={e => handleInlineUpdate(ticket.id, 'assigned_to', e.target.value)}
                        onBlur={() => setEditingCell(null)}
                        className="bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-2 py-1 text-[var(--text-primary)] text-xs focus:outline-none focus:ring-1 focus:ring-[var(--accent)]">
                        <option value="">↩ Devolver à Caixa</option>
                        {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                      </select>
                    ) : (
                      <span onClick={() => setEditingCell({ ticketId: ticket.id, field: 'assigned_to' })}
                        className="text-[var(--text-secondary)] text-sm cursor-pointer hover:text-[var(--accent)] transition">
                        {ticket.agent_name || <span className="text-[var(--text-tertiary)] italic">Aguardando</span>}
                        <i className="fas fa-pen text-[9px] ml-1.5 opacity-0 group-hover:opacity-50" />
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4" onClick={e => e.stopPropagation()}>
                    <div className="flex gap-1 flex-wrap items-center">
                      {(ticket.tags || []).map(tag => (
                        <span key={tag} className={`px-2.5 py-1 rounded-full text-xs font-medium inline-flex items-center gap-1 ${TAG_COLORS[tag] || 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'}`}>
                          {TAG_LABELS[tag] || tag}
                          <button onClick={() => handleRemoveTag(ticket.id, ticket.tags || [], tag)}
                            className="hover:text-red-400 transition ml-0.5"><i className="fas fa-times text-[8px]" /></button>
                        </span>
                      ))}
                      {editingCell?.ticketId === ticket.id && editingCell?.field === 'tags' ? (
                        <select autoFocus
                          onChange={e => { if (e.target.value) handleAddTag(ticket.id, ticket.tags || [], e.target.value) }}
                          onBlur={() => setEditingCell(null)}
                          className="bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-1.5 py-0.5 text-[var(--text-primary)] text-[10px] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]">
                          <option value="">Adicionar...</option>
                          {Object.entries(TAG_LABELS).filter(([k]) => !(ticket.tags || []).includes(k)).map(([k, v]) => (
                            <option key={k} value={k}>{v}</option>
                          ))}
                        </select>
                      ) : (
                        <button onClick={() => setEditingCell({ ticketId: ticket.id, field: 'tags' })}
                          className="w-5 h-5 rounded-full bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] hover:text-[var(--accent)] hover:bg-[var(--bg-hover)] flex items-center justify-center transition text-[9px]">
                          <i className="fas fa-plus" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {sortedTickets.length === 0 && (
          <div className="p-16 text-center text-[var(--text-secondary)]">
            <i className={`fas ${activeTab === 'resolved' ? 'fa-check-circle' : activeTab === 'escalated' ? 'fa-exclamation-triangle' : 'fa-inbox'} text-5xl mb-4 opacity-30`} />
            <p className="text-base font-medium">
              {activeTab === 'resolved' ? 'Nenhum ticket resolvido encontrado'
                : activeTab === 'escalated' ? 'Nenhum ticket escalado'
                : 'Nenhum ticket encontrado'}
            </p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > 20 && (() => {
        const lastPage = Math.ceil(total / 20)
        return (
          <div className="flex justify-center gap-2 mt-6">
            <button
              disabled={page <= 1}
              onClick={() => setPage(1)}
              className="px-3 py-2.5 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-lg disabled:opacity-30 text-sm font-medium transition-colors hover:bg-[var(--bg-tertiary)]"
              title="Primeira página"
            >
              &laquo;
            </button>
            <button
              disabled={page <= 1}
              onClick={() => setPage(p => p - 1)}
              className="px-4 py-2.5 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-lg disabled:opacity-30 text-sm font-medium transition-colors hover:bg-[var(--bg-tertiary)]"
            >
              <i className="fas fa-chevron-left mr-2" />Anterior
            </button>
            <span className="px-4 py-2.5 text-[var(--text-secondary)] text-sm font-medium">
              Página {page} de {lastPage}
            </span>
            <button
              disabled={page >= lastPage}
              onClick={() => setPage(p => p + 1)}
              className="px-4 py-2.5 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-lg disabled:opacity-30 text-sm font-medium transition-colors hover:bg-[var(--bg-tertiary)]"
            >
              Próxima<i className="fas fa-chevron-right ml-2" />
            </button>
            <button
              disabled={page >= lastPage}
              onClick={() => setPage(lastPage)}
              className="px-3 py-2.5 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-lg disabled:opacity-30 text-sm font-medium transition-colors hover:bg-[var(--bg-tertiary)]"
              title="Última página"
            >
              &raquo;
            </button>
          </div>
        )
      })()}

      </>
      )}

      {/* Modal: Import History */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => !importing && setShowImportModal(false)}>
          <div className="bg-[var(--bg-secondary)] rounded-2xl w-full max-w-lg border border-[var(--border-color)] shadow-2xl" onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-8 py-6 border-b border-[var(--border-color)]">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-purple-600/20 flex items-center justify-center border border-purple-500/30">
                  <i className="fas fa-cloud-download-alt text-purple-400 text-lg" />
                </div>
                <div>
                  <h2 className="text-[var(--text-primary)] font-semibold text-lg">Importar Histórico</h2>
                  <p className="text-[var(--text-secondary)] text-sm">Sincronizar emails do Gmail</p>
                </div>
              </div>
              {!importing && (
                <button onClick={() => { setShowImportModal(false); setImportResult(null) }} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition">
                  <i className="fas fa-times text-xl" />
                </button>
              )}
            </div>

            {/* Body */}
            <div className="px-8 py-6">
              <label className="text-[var(--text-primary)] text-sm font-semibold block mb-4">Período de importação</label>
              <div className="grid grid-cols-4 gap-3 mb-6">
                {[
                  { label: '7 dias', value: 7 },
                  { label: '15 dias', value: 15 },
                  { label: '30 dias', value: 30 },
                  { label: '60 dias', value: 60 },
                ].map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setImportDays(opt.value)}
                    disabled={importing}
                    className={`py-3 rounded-xl text-sm font-medium transition-colors ${
                      importDays === opt.value
                        ? 'bg-purple-600 text-white border border-purple-500'
                        : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:text-[var(--text-primary)] hover:border-purple-500/50'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-3 mb-6 bg-[var(--bg-tertiary)] rounded-xl px-4 py-3 border border-[var(--border-color)]">
                <i className="fas fa-calendar text-[var(--text-secondary)] text-lg" />
                <label className="text-[var(--text-secondary)] text-sm font-medium">Personalizado:</label>
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={importDays}
                  onChange={e => setImportDays(Math.max(1, Math.min(365, parseInt(e.target.value) || 1)))}
                  disabled={importing}
                  className="w-16 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm text-center focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                />
                <span className="text-[var(--text-secondary)] text-sm">dias</span>
              </div>

              {importResult && (
                <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4 mb-4">
                  <div className="flex items-center gap-2 mb-3">
                    <i className="fas fa-check-circle text-green-400 text-lg" />
                    <span className="text-green-400 font-semibold text-sm">Importação concluída com sucesso!</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3 mt-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-400">{importResult.created}</div>
                      <div className="text-xs text-[var(--text-secondary)] mt-1">Criados</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-400">{importResult.updated}</div>
                      <div className="text-xs text-[var(--text-secondary)] mt-1">Atualizados</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-[var(--text-secondary)]">{importResult.skipped}</div>
                      <div className="text-xs text-[var(--text-secondary)] mt-1">Já existentes</div>
                    </div>
                  </div>
                </div>
              )}

              {importError && (
                <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4 mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <i className="fas fa-exclamation-circle text-red-400 text-lg" />
                    <span className="text-red-400 font-semibold text-sm">Erro na importação</span>
                  </div>
                  <p className="text-red-300 text-xs mt-2">{importError}</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex gap-3 justify-end px-8 py-6 border-t border-[var(--border-color)]">
              <button
                onClick={() => { setShowImportModal(false); setImportResult(null); setImportError(null) }}
                disabled={importing}
                className="px-6 py-2.5 rounded-lg text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors font-medium"
              >
                {importResult ? 'Fechar' : 'Cancelar'}
              </button>
              {!importResult && (
                <button
                  onClick={async () => {
                    setImporting(true)
                    setImportResult(null)
                    setImportError(null)
                    try {
                      const { data } = await fetchGmailHistory(importDays)
                      setImportResult(data)
                      await loadTickets()
                    } catch (e) {
                      console.error('Gmail history import failed:', e)
                      const msg = e.response?.data?.detail || e.message || 'Erro desconhecido'
                      setImportError(`Não foi possível importar. ${msg}`)
                    } finally {
                      setImporting(false)
                    }
                  }}
                  disabled={importing}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {importing ? (
                    <><i className="fas fa-spinner animate-spin" />Importando...</>
                  ) : (
                    <><i className="fas fa-cloud-download-alt" />Importar {importDays} dias</>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal: Compose Email */}
      {showComposeModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => !composeSending && setShowComposeModal(false)}>
          <div className="bg-[var(--bg-secondary)] rounded-2xl w-full max-w-2xl shadow-2xl border border-[var(--border-color)]" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-5 border-b border-[var(--border-color)]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-600/20 flex items-center justify-center">
                  <i className="fas fa-pen-to-square text-blue-400 text-lg" />
                </div>
                <h2 className="text-[var(--text-primary)] font-semibold text-lg">Novo E-mail</h2>
              </div>
              <button onClick={() => setShowComposeModal(false)} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition">
                <i className="fas fa-times text-lg" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-[var(--text-secondary)] text-sm font-medium">Para</label>
                  <button onClick={() => setComposeShowCcBcc(!composeShowCcBcc)}
                    className="text-xs text-blue-400 hover:text-blue-300 transition">
                    {composeShowCcBcc ? 'Ocultar CC/CCO' : 'CC/CCO'}
                  </button>
                </div>
                <input
                  type="email"
                  value={composeTo}
                  onChange={e => setComposeTo(e.target.value)}
                  placeholder="email@cliente.com"
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                />
              </div>
              {composeShowCcBcc && (
                <>
                  <div>
                    <label className="text-[var(--text-secondary)] text-sm font-medium block mb-1.5">CC</label>
                    <input
                      type="text"
                      value={composeCc}
                      onChange={e => setComposeCc(e.target.value)}
                      placeholder="email1@example.com, email2@example.com"
                      className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    />
                  </div>
                  <div>
                    <label className="text-[var(--text-secondary)] text-sm font-medium block mb-1.5">CCO</label>
                    <input
                      type="text"
                      value={composeBcc}
                      onChange={e => setComposeBcc(e.target.value)}
                      placeholder="email1@example.com, email2@example.com"
                      className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    />
                  </div>
                </>
              )}
              <div>
                <label className="text-[var(--text-secondary)] text-sm font-medium block mb-1.5">Assunto</label>
                <input
                  type="text"
                  value={composeSubject}
                  onChange={e => setComposeSubject(e.target.value)}
                  placeholder="Assunto do e-mail"
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                />
              </div>
              <div className={`relative ${composeDragging ? 'ring-2 ring-emerald-400 ring-dashed rounded-lg' : ''}`} onDrop={handleComposeDrop} onDragOver={handleComposeDragOver} onDragLeave={handleComposeDragLeave}>
                {composeDragging && (
                  <div className="absolute inset-0 bg-emerald-500/10 border-2 border-dashed border-emerald-400 rounded-xl z-10 flex items-center justify-center pointer-events-none">
                    <span className="text-emerald-400 font-medium text-sm"><i className="fas fa-cloud-upload-alt mr-2" />Solte os arquivos aqui</span>
                  </div>
                )}
                <label className="text-[var(--text-secondary)] text-sm font-medium block mb-1.5">Mensagem</label>
                <textarea
                  value={composeBody}
                  onChange={e => setComposeBody(e.target.value)}
                  placeholder="Escreva sua mensagem..."
                  rows={8}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
                />
              </div>
              <div>
                <button onClick={() => composeAttachmentRef.current?.click()}
                  disabled={composeUploading}
                  className={`text-xs px-3 py-1.5 rounded-lg transition ${composeAttachments.length > 0 ? 'bg-emerald-600/20 text-emerald-400' : 'text-[var(--text-tertiary)] hover:text-emerald-400 hover:bg-[var(--bg-tertiary)] border border-[var(--border-color)]'}`}>
                  <i className={`fas ${composeUploading ? 'fa-spinner animate-spin' : 'fa-paperclip'} mr-1`} />
                  {composeAttachments.length > 0 ? `${composeAttachments.length} anexo${composeAttachments.length > 1 ? 's' : ''}` : 'Anexar arquivos'}
                </button>
                <input ref={composeAttachmentRef} type="file" multiple className="hidden" onChange={handleComposeAttachmentUpload} />
                {composeAttachments.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {composeAttachments.map((att, i) => (
                      <span key={i} className="inline-flex items-center gap-1.5 bg-emerald-500/10 text-emerald-400 text-xs px-2.5 py-1 rounded-lg">
                        <i className="fas fa-paperclip text-[10px]" />
                        <span className="max-w-[150px] truncate">{att.name}</span>
                        <span className="text-emerald-600 text-[10px]">({(att.size / 1024).toFixed(0)}KB)</span>
                        <button onClick={() => setComposeAttachments(prev => prev.filter((_, j) => j !== i))}
                          className="hover:text-red-400 transition ml-0.5">
                          <i className="fas fa-times text-[10px]" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex justify-end gap-3 p-5 border-t border-[var(--border-color)]">
              <button
                onClick={() => { setShowComposeModal(false); setComposeTo(''); setComposeCc(''); setComposeBcc(''); setComposeShowCcBcc(false); setComposeSubject(''); setComposeBody(''); setComposeAttachments([]) }}
                className="px-4 py-2.5 rounded-lg text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition"
              >
                Cancelar
              </button>
              <button
                onClick={async () => {
                  if (!composeTo || !composeSubject || !composeBody) return
                  setComposeSending(true)
                  try {
                    const ccList = composeCc ? composeCc.split(',').map(e => e.trim()).filter(Boolean) : undefined
                    const bccList = composeBcc ? composeBcc.split(',').map(e => e.trim()).filter(Boolean) : undefined
                    const { data } = await composeEmail({ to: composeTo, subject: composeSubject, body: composeBody, cc: ccList, bcc: bccList, attachments: composeAttachments.length ? composeAttachments : undefined })
                    setShowComposeModal(false)
                    setComposeTo('')
                    setComposeCc('')
                    setComposeBcc('')
                    setComposeShowCcBcc(false)
                    setComposeSubject('')
                    setComposeBody('')
                    setComposeAttachments([])
                    loadTickets()
                    if (data.ticket_number) {
                      toast.success(`E-mail enviado! Ticket #${data.ticket_number} criado`)
                    }
                  } catch (e) {
                    toast.error(e.response?.data?.detail || 'Erro ao enviar e-mail')
                  } finally {
                    setComposeSending(false)
                  }
                }}
                disabled={composeSending || !composeTo || !composeSubject || !composeBody}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {composeSending ? (
                  <><i className="fas fa-spinner animate-spin" />Enviando...</>
                ) : (
                  <><i className="fas fa-paper-plane" />Enviar E-mail</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
