import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useToast } from '../components/Toast'
import { getTickets, getTicketCounts, bulkAssign, bulkUpdate, autoAssign, getUsers, exportTicketsCsv, fetchGmailEmails, updateTicket, getSentMessages, fetchSpamEmails, rescueFromSpam, bulkRescueFromSpam, rescueAndCreateTicket, markTicketViewed } from '../services/api'
import MetaBadge from '../components/MetaBadge'
import { SkeletonTicketList } from '../components/Skeleton'
import AutoAssignModal from '../components/AutoAssignModal'
import ImportHistoryModal from '../components/ImportHistoryModal'
import ComposeEmailModal from '../components/ComposeEmailModal'
import { STATUS_COLORS, PRIORITY_COLORS, STATUS_LABELS, PRIORITY_LABELS, CATEGORY_LABELS, TAG_COLORS, TAG_LABELS, PRIORITY_ORDER, STATUS_ORDER } from '../constants/ticket'

const AUTO_REFRESH_MS = 60_000
const MS_PER_HOUR = 3_600_000
const MS_PER_MINUTE = 60_000
const SLA_URGENT_THRESHOLD_MS = MS_PER_HOUR

const SORT_OPTIONS = [
  { value: 'oldest', label: 'Mais antigos', icon: 'fa-arrow-up' },
  { value: 'newest', label: 'Mais recentes', icon: 'fa-arrow-down' },
  { value: 'sla', label: 'SLA (urgente primeiro)', icon: 'fa-clock' },
  { value: 'priority', label: 'Prioridade', icon: 'fa-exclamation' },
  { value: 'updated', label: 'Última atualização', icon: 'fa-sync-alt' },
]

const TABS = [
  { key: 'mine', label: 'Privado', icon: 'fa-lock', countKey: 'mine' },
  { key: 'team', label: 'Equipe', icon: 'fa-users', countKey: 'team' },
  { key: 'active', label: 'Novos', icon: 'fa-inbox', countKey: 'unassigned' },
  { key: 'responded', label: 'Respondidos', icon: 'fa-reply', countKey: 'waiting' },
  { key: 'escalated', label: 'Prioridade', icon: 'fa-exclamation-triangle', countKey: 'escalated' },
  { key: 'resolved', label: 'Arquivado', icon: 'fa-archive' },
]

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  return `${days}d`
}

export default function TicketsPage({ user }) {
  const toast = useToast()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const filters = Object.fromEntries(searchParams.entries())
  const onOpenTicket = (id) => {
    markTicketViewed(id).catch(() => {})
    setTickets(prev => prev.map(t => t.id === id ? { ...t, is_unread: false } : t))
    navigate(`/tickets/${id}`)
  }
  const [tickets, setTickets] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [agents, setAgents] = useState([])
  const [activeTab, setActiveTab] = useState(() => {
    try {
      const prefs = JSON.parse(localStorage.getItem('carbon_prefs') || '{}')
      return prefs.active_tab || prefs.default_tab || 'mine'
    } catch { return 'mine' }
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
  const [filterAgent, setFilterAgent] = useState('')
  const [sort, setSort] = useState('oldest')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [customerName, setCustomerName] = useState('')
  const [autoAssigning, setAutoAssigning] = useState(false)
  const [showAutoAssignModal, setShowAutoAssignModal] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [sortField, setSortField] = useState('')
  const [sortDir, setSortDir] = useState('desc')
  const [showImportModal, setShowImportModal] = useState(false)
  const [showComposeModal, setShowComposeModal] = useState(false)
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
  const [sentSearch, setSentSearch] = useState('')
  const [spamSearch, setSpamSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const sentSearchTimerRef = useRef(null)
  const searchTimerRef = useRef(null)
  const abortRef = useRef(null)
  const requestIdRef = useRef(0)

  // Debounced search: only sets page to 1 (useEffect handles the reload)
  const handleSearchInput = useCallback((value) => {
    setSearch(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      setPage(1)
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

  const loadTickets = async () => {
    // Cancel previous in-flight request
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const thisRequest = ++requestIdRef.current

    setLoading(true)
    try {
      const params = {
        page,
        search: search || undefined,
        priority: filterPriority || undefined,
        category: filterCategory || undefined,
        tag: filterTag || undefined,
        source: filterSource || undefined,
        // No longer exclude chat sources — escalated tickets from WA/IG/FB should appear
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
        if (filterAgent) {
          params.assigned_to = filterAgent
        } else {
          params.assigned = 'any'
        }
        params.exclude_status = 'resolved,closed,archived,waiting,waiting_supplier,waiting_resend,merged'
        if (filterStatus) params.status = filterStatus
      } else if (activeTab === 'active') {
        // Novos: tickets não atribuídos que precisam de atenção
        params.assigned = 'none'
        params.exclude_status = 'resolved,closed,archived,waiting,waiting_supplier,waiting_resend,merged'
        if (filterStatus) params.status = filterStatus
      } else if (activeTab === 'responded') {
        // Respondidos: tickets já respondidos, aguardando ação do cliente (agentes veem só os seus)
        params.status = 'waiting,waiting_supplier,waiting_resend'
        if (user?.role === 'agent') params.assigned_to = 'me'
        if (filterStatus) params.status = filterStatus
      } else if (activeTab === 'resolved') {
        params.status = 'resolved'
      } else if (activeTab === 'closed') {
        params.status = 'closed,archived'
      } else if (activeTab === 'escalated') {
        params.status = 'escalated'
      } else if (activeTab === 'archived') {
        params.status = 'archived'
      } else {
        if (filterStatus) params.status = filterStatus
      }

      const { data } = await getTickets(params, { signal: controller.signal })
      // Ignore stale responses
      if (thisRequest !== requestIdRef.current) return
      let filtered = data.tickets
      if (filterResponse === 'awaiting') {
        filtered = filtered.filter(t => !t.first_response_at && !['resolved', 'closed', 'archived'].includes(t.status))
      } else if (filterResponse === 'responded') {
        filtered = filtered.filter(t => !!t.first_response_at)
      }
      setTickets(filtered)
      setTotal(data.total)
    } catch (e) {
      // Ignore aborted requests
      if (e.name === 'AbortError' || e.code === 'ERR_CANCELED') return
      if (thisRequest !== requestIdRef.current) return
      toast.error('Falha ao carregar tickets')
    } finally {
      if (thisRequest === requestIdRef.current) setLoading(false)
    }
  }

  const loadSentMessages = async () => {
    setSentLoading(true)
    try {
      const params = { page: sentPage, per_page: 20 }
      if (sentSearch.trim()) params.search = sentSearch.trim()
      const { data } = await getSentMessages(params)
      setSentMessages(data.items)
      setSentTotal(data.total)
    } catch (e) {
      toast.error('Falha ao carregar mensagens enviadas')
    } finally {
      setSentLoading(false)
    }
  }

  const handleSentSearchInput = (value) => {
    setSentSearch(value)
    if (sentSearchTimerRef.current) clearTimeout(sentSearchTimerRef.current)
    sentSearchTimerRef.current = setTimeout(() => {
      setSentPage(1)
    }, 300)
  }

  useEffect(() => {
    loadTickets()
    return () => { if (abortRef.current) abortRef.current.abort() }
  }, [page, search, filters, activeTab, filterStatus, filterPriority, filterCategory, filterTag, filterSource, filterResponse, filterAgent, sort, dateFrom, dateTo, customerName])

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
    const visible = spamSearch.trim()
      ? spamEmails.filter(e => {
          const q = spamSearch.toLowerCase()
          return (e.from_name || '').toLowerCase().includes(q)
            || (e.from_email || '').toLowerCase().includes(q)
            || (e.subject || '').toLowerCase().includes(q)
            || (e.snippet || '').toLowerCase().includes(q)
        })
      : spamEmails
    if (selectedSpam.size === visible.length) {
      setSelectedSpam(new Set())
    } else {
      setSelectedSpam(new Set(visible.map(e => e.gmail_id)))
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
  }, [topView, sentPage, sentSearch])

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
    setFilterAgent('')
    // Persist active tab so back navigation restores it
    try {
      const prefs = JSON.parse(localStorage.getItem('carbon_prefs') || '{}')
      prefs.active_tab = tab
      localStorage.setItem('carbon_prefs', JSON.stringify(prefs))
    } catch {}
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

  const handleAutoAssign = async (agentIds) => {
    setAutoAssigning(true)
    setShowAutoAssignModal(false)
    try {
      const ids = agentIds && agentIds.length > 0 ? agentIds : null
      const { data } = await autoAssign(ids)
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

  const hasActiveFilters = useMemo(() => filterStatus || filterPriority || filterCategory || filterTag || filterSource || filterResponse || (sort && sort !== 'oldest') || dateFrom || dateTo || customerName, [filterStatus, filterPriority, filterCategory, filterTag, filterSource, filterResponse, sort, dateFrom, dateTo, customerName])

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

  const statusOptions = useMemo(() => activeTab === 'active'
    ? Object.entries(STATUS_LABELS).filter(([k]) => !['resolved', 'closed', 'archived'].includes(k))
    : ['resolved', 'closed', 'escalated'].includes(activeTab) ? [] : Object.entries(STATUS_LABELS), [activeTab])

  const sentLastPage = useMemo(() => Math.max(1, Math.ceil(sentTotal / 20)), [sentTotal])

  const filteredSpam = useMemo(() => spamSearch.trim()
    ? spamEmails.filter(e => {
        const q = spamSearch.toLowerCase()
        return (e.from_name || '').toLowerCase().includes(q)
          || (e.from_email || '').toLowerCase().includes(q)
          || (e.subject || '').toLowerCase().includes(q)
          || (e.snippet || '').toLowerCase().includes(q)
      })
    : spamEmails, [spamSearch, spamEmails])

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

          <div className="mb-4">
            <div className="relative">
              <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] text-sm" />
              <input
                type="text"
                value={spamSearch}
                onChange={(e) => setSpamSearch(e.target.value)}
                placeholder="Buscar por remetente, email ou assunto..."
                className="w-full pl-10 pr-10 py-2.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] text-sm placeholder-[var(--text-tertiary)] focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition"
              />
              {spamSearch && (
                <button onClick={() => setSpamSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition">
                  <i className="fas fa-times text-sm" />
                </button>
              )}
            </div>
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
            ) : filteredSpam.length === 0 ? (
              <div className="p-12 text-center text-[var(--text-secondary)]">
                <i className="fas fa-check-circle text-4xl mb-3 text-emerald-400 opacity-50" />
                <p>{spamSearch ? 'Nenhum resultado encontrado' : 'Nenhum email no spam'}</p>
              </div>
            ) : (
              <div className="divide-y divide-[var(--border-color)]">
                {/* Header: selecionar todos */}
                <div className="px-4 py-2.5 flex items-center gap-3 bg-[var(--bg-tertiary)]">
                  <input
                    type="checkbox"
                    checked={selectedSpam.size === filteredSpam.length && filteredSpam.length > 0}
                    onChange={toggleSpamSelectAll}
                    className="w-4 h-4 rounded accent-blue-500 cursor-pointer"
                  />
                  <span className="text-xs text-[var(--text-secondary)]">
                    {selectedSpam.size === filteredSpam.length ? 'Desmarcar todos' : 'Selecionar todos'}
                  </span>
                  <span className="text-xs text-[var(--text-tertiary)] ml-auto">{filteredSpam.length} email{filteredSpam.length > 1 ? 's' : ''}</span>
                </div>
                {filteredSpam.map(email => (
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
          <div className="mb-4">
            <div className="relative">
              <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] text-sm" />
              <input
                type="text"
                value={sentSearch}
                onChange={(e) => handleSentSearchInput(e.target.value)}
                placeholder="Buscar por destinatario, assunto ou conteudo..."
                className="w-full pl-10 pr-10 py-2.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] text-sm placeholder-[var(--text-tertiary)] focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition"
              />
              {sentSearch && (
                <button onClick={() => { setSentSearch(''); setSentPage(1) }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition">
                  <i className="fas fa-times text-sm" />
                </button>
              )}
            </div>
          </div>
          <div className="bg-[var(--bg-secondary)] rounded-xl overflow-hidden border border-[var(--border-color)]">
            {sentLoading ? (
              <div className="p-12 text-center text-[var(--text-secondary)]">Carregando...</div>
            ) : sentMessages.length === 0 ? (
              <div className="p-12 text-center text-[var(--text-secondary)]">
                <i className={`fas ${sentSearch ? 'fa-search' : 'fa-paper-plane'} text-4xl mb-3 opacity-30`} />
                <p>{sentSearch ? 'Nenhum resultado encontrado' : 'Nenhuma mensagem enviada'}</p>
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
      <div>
      <div className="flex-1">
      <>
      {/* Page Header with Counter Cards */}
      <div className="mb-6">
        <div className="grid grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
          <button onClick={() => handleTabChange('mine')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-3 text-left transition hover:border-indigo-500/30 ${activeTab === 'mine' ? 'border-indigo-500/40 ring-1 ring-indigo-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-lock text-indigo-400 text-xs" />
              <span className="text-[var(--text-tertiary)] text-[11px]">Privado</span>
            </div>
            <p className="text-xl font-bold text-[var(--text-primary)]">{counts.mine}</p>
          </button>
          <button onClick={() => handleTabChange('team')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-3 text-left transition hover:border-teal-500/30 ${activeTab === 'team' ? 'border-teal-500/40 ring-1 ring-teal-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-users text-teal-400 text-xs" />
              <span className="text-[var(--text-tertiary)] text-[11px]">Equipe</span>
            </div>
            <p className="text-xl font-bold text-[var(--text-primary)]">{counts.team}</p>
          </button>
          {user?.role !== 'agent' && (
          <button onClick={() => handleTabChange('active')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-3 text-left transition hover:border-orange-500/30 ${activeTab === 'active' ? 'border-orange-500/40 ring-1 ring-orange-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-inbox text-orange-400 text-xs" />
              <span className="text-[var(--text-tertiary)] text-[11px]">Novos</span>
            </div>
            <p className="text-xl font-bold text-orange-400">{counts.unassigned}</p>
          </button>
          )}
          <button onClick={() => handleTabChange('escalated')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-3 text-left transition hover:border-red-500/30 ${activeTab === 'escalated' ? 'border-red-500/40 ring-1 ring-red-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-exclamation-triangle text-red-400 text-xs" />
              <span className="text-[var(--text-tertiary)] text-[11px]">Prioridade</span>
            </div>
            <p className="text-xl font-bold text-red-400">{counts.escalated}</p>
          </button>
          <button onClick={() => handleTabChange('resolved')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-3 text-left transition hover:border-green-500/30 ${activeTab === 'resolved' ? 'border-green-500/40 ring-1 ring-green-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-check-circle text-green-400 text-xs" />
              <span className="text-[var(--text-tertiary)] text-[11px]">Resolvidos</span>
            </div>
            <p className="text-xl font-bold text-green-400">{counts.resolved || 0}</p>
          </button>
          <button onClick={() => handleTabChange('closed')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-3 text-left transition hover:border-gray-500/30 ${activeTab === 'closed' ? 'border-gray-500/40 ring-1 ring-gray-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-archive text-gray-400 text-xs" />
              <span className="text-[var(--text-tertiary)] text-[11px]">Fechados</span>
            </div>
            <p className="text-xl font-bold text-gray-400">{counts.closed || 0}</p>
          </button>
          <button onClick={() => handleTabChange('all')} className={`bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-3 text-left transition hover:border-blue-500/30 ${activeTab === 'all' ? 'border-blue-500/40 ring-1 ring-blue-500/20' : ''}`}>
            <div className="flex items-center gap-2 mb-1">
              <i className="fas fa-list text-blue-400 text-xs" />
              <span className="text-[var(--text-tertiary)] text-[11px]">Todos</span>
            </div>
            <p className="text-xl font-bold text-[var(--text-primary)]">{counts.total_open}</p>
          </button>
        </div>
      </div>

      {/* Top Action Bar */}
      <div className="mb-6 flex flex-col gap-4">
        {/* Agent filter - visible on team tab */}
        <div className="flex gap-1">
          {activeTab === 'team' && agents.length > 0 && (
            <select
              value={filterAgent}
              onChange={(e) => { setFilterAgent(e.target.value); setPage(1) }}
              className="ml-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            >
              <option value="">Todos os agentes</option>
              {agents.map(a => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          )}
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
              onClick={() => setShowAutoAssignModal(true)}
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
        <div className="bg-indigo-600/10 border border-indigo-500/30 rounded-xl p-4 mb-6 flex items-center gap-4 flex-wrap sticky top-0 z-30">
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

      {/* Ticket List */}
      <div className="bg-[var(--bg-secondary)] rounded-xl overflow-hidden border border-[var(--border-color)]">
        {loading && tickets.length === 0 ? <SkeletonTicketList /> : (<>
        {/* Header */}
        <div className="grid items-center px-4 py-3 border-b border-[var(--border-color)] bg-[var(--bg-tertiary)]/50 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]"
          style={{ gridTemplateColumns: '36px minmax(140px,1.2fr) minmax(100px,1fr) minmax(80px,0.7fr) 90px 80px 90px 130px 80px 60px' }}>
          <div className="flex items-center justify-center">
            <input type="checkbox" onChange={toggleAll} checked={selected.size === sortedTickets.length && sortedTickets.length > 0} className="rounded" />
          </div>
          <button onClick={() => toggleSort('customer')} className="text-left select-none hover:text-[var(--accent)] transition-colors"
            style={{ color: sortField === 'customer' ? 'var(--accent)' : undefined }}>
            Cliente {sortField === 'customer' && <i className={`fas fa-arrow-${sortDir === 'asc' ? 'up' : 'down'} text-[10px] ml-1`} />}
          </button>
          <span>Assunto</span>
          <span>Categoria</span>
          <span>Status</span>
          <span>Prioridade</span>
          <span>Agente</span>
          <span>Etiquetas</span>
          <button onClick={() => toggleSort('sla')} className="text-left select-none hover:text-[var(--accent)] transition-colors"
            style={{ color: sortField === 'sla' ? 'var(--accent)' : undefined }}>
            {activeTab === 'resolved' ? 'Resolvido' : activeTab === 'closed' ? 'Fechado' : 'SLA'} {sortField === 'sla' && <i className={`fas fa-arrow-${sortDir === 'asc' ? 'up' : 'down'} text-[10px] ml-1`} />}
          </button>
          <button onClick={() => toggleSort('created_at')} className="text-left select-none hover:text-[var(--accent)] transition-colors"
            style={{ color: sortField === 'created_at' ? 'var(--accent)' : undefined }}>
            Data {sortField === 'created_at' && <i className={`fas fa-arrow-${sortDir === 'asc' ? 'up' : 'down'} text-[10px] ml-1`} />}
          </button>
        </div>
        {/* Rows */}
        <div className="divide-y divide-[var(--border-color)]">
          {sortedTickets.map(ticket => {
            const slaStatus = getSlaStatus(ticket)
            return (
              <div key={ticket.id}
                className={`group grid items-center px-4 py-2.5 cursor-pointer transition-colors ${
                  slaStatus === 'breached' && !['resolved', 'closed'].includes(ticket.status) ? 'bg-red-900/5 hover:bg-red-900/10' :
                  ticket.is_unread ? 'bg-indigo-500/[0.03] hover:bg-indigo-500/[0.06]' :
                  'hover:bg-[var(--bg-hover)]'
                } ${ticket.status === 'escalated' ? 'border-l-4 border-l-red-500' : ''} ${
                  (ticket.tags || []).includes('auto_escalado') && !['resolved', 'closed'].includes(ticket.status)
                    ? 'border-l-4 border-l-amber-500 bg-amber-500/[0.03]' : ''
                }`}
                style={{ gridTemplateColumns: '36px minmax(140px,1.2fr) minmax(100px,1fr) minmax(80px,0.7fr) 90px 80px 90px 130px 80px 60px' }}
                onClick={() => onOpenTicket(ticket.id)}
              >
                {/* Checkbox */}
                <div className="flex items-center justify-center" onClick={e => e.stopPropagation()}>
                  <input type="checkbox" checked={selected.has(ticket.id)} onChange={() => toggleSelect(ticket.id)} className="rounded" />
                </div>

                {/* Cliente */}
                <div className="min-w-0 pr-2">
                  <div className="flex items-center gap-1.5">
                    {ticket.is_unread && <span className="w-2 h-2 rounded-full bg-indigo-500 flex-shrink-0" />}
                    <span className={`text-[var(--text-primary)] text-sm truncate ${ticket.is_unread ? 'font-bold' : 'font-medium'}`}>
                      {ticket.customer?.name || ticket.customer_name || '-'}
                    </span>
                    {ticket.last_message_type === 'inbound' && (
                      <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" title="Cliente respondeu" />
                    )}
                  </div>
                  {ticket.source && ticket.source !== 'web' && <div className="mt-0.5"><MetaBadge source={ticket.source} aiAutoMode={ticket.ai_auto_mode} /></div>}
                </div>

                {/* Assunto */}
                <div className="min-w-0 pr-2">
                  <div className="flex items-center gap-1.5">
                    <p className={`text-sm truncate ${ticket.is_unread ? 'font-semibold text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>
                      {ticket.subject}
                    </p>
                    {(ticket.tags || []).includes('auto_escalado') && (
                      <span className="flex-shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-400 border border-amber-500/20">
                        Escalado
                      </span>
                    )}
                  </div>
                  {ticket.last_message_preview && (
                    <p className="text-[11px] mt-0.5 truncate text-[var(--text-tertiary)]">
                      {ticket.last_message_preview.substring(0, 80)}
                    </p>
                  )}
                </div>

                {/* Categoria */}
                <div className="text-xs text-[var(--text-secondary)] truncate pr-2">
                  {CATEGORY_LABELS[ticket.category] || ticket.category || '-'}
                </div>

                {/* Status */}
                <div>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-[10px] font-medium whitespace-nowrap ${STATUS_COLORS[ticket.status] || 'bg-gray-500/10 text-gray-300'}`}>
                    {STATUS_LABELS[ticket.status] || ticket.status}
                  </span>
                </div>

                {/* Prioridade */}
                <div>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-[10px] font-medium ${
                    ticket.priority === 'urgent' ? 'bg-red-500/15 text-red-400' :
                    ticket.priority === 'high' ? 'bg-orange-500/15 text-orange-400' :
                    ticket.priority === 'medium' ? 'bg-blue-500/15 text-blue-300' :
                    'bg-gray-500/10 text-gray-400'
                  }`}>
                    {PRIORITY_LABELS[ticket.priority] || ticket.priority || '-'}
                  </span>
                </div>

                {/* Agente */}
                <div className="text-xs text-[var(--text-tertiary)] truncate pr-2">
                  {ticket.agent_name || '-'}
                </div>

                {/* Etiquetas */}
                <div className="flex gap-1 flex-wrap items-center overflow-hidden max-h-[40px]">
                  {ticket.legal_risk && <span className="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-red-500/15 text-red-400">Jurídico</span>}
                  {(ticket.tags || []).slice(0, 3).map(tag => (
                    <span key={tag} className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${TAG_COLORS[tag] || 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'}`}>
                      {TAG_LABELS[tag] || tag}
                    </span>
                  ))}
                  {(ticket.tags || []).length > 3 && (
                    <span className="text-[var(--text-tertiary)] text-[10px]">+{ticket.tags.length - 3}</span>
                  )}
                </div>

                {/* SLA */}
                <div>
                  {['resolved', 'closed'].includes(ticket.status) ? (
                    <span className="text-[var(--text-tertiary)] text-[11px]">
                      {ticket.resolved_at ? new Date(ticket.resolved_at).toLocaleDateString('pt-BR') : '-'}
                    </span>
                  ) : (
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium ${
                      slaStatus === 'breached' ? 'bg-red-500/15 text-red-400' :
                      slaStatus === 'urgent' ? 'bg-yellow-500/15 text-yellow-400' :
                      'bg-emerald-500/15 text-emerald-400'
                    }`}>
                      <i className={`fas ${slaStatus === 'breached' ? 'fa-exclamation-circle' : slaStatus === 'urgent' ? 'fa-clock' : 'fa-check-circle'} text-[10px]`} />
                      {formatSla(ticket)}
                    </span>
                  )}
                </div>

                {/* Data */}
                <div className="text-[var(--text-tertiary)] text-[11px]">
                  {ticket.created_at ? timeAgo(ticket.created_at) : '-'}
                </div>
              </div>
            )
          })}
        </div>

        {sortedTickets.length === 0 && !loading && (
          <div className="p-16 text-center text-[var(--text-secondary)]">
            <i className={`fas ${activeTab === 'resolved' ? 'fa-check-circle' : activeTab === 'closed' ? 'fa-archive' : activeTab === 'escalated' ? 'fa-exclamation-triangle' : 'fa-inbox'} text-5xl mb-4 opacity-30`} />
            <p className="text-base font-medium">
              {activeTab === 'resolved' ? 'Nenhum ticket resolvido encontrado'
                : activeTab === 'closed' ? 'Nenhum ticket fechado encontrado'
                : activeTab === 'escalated' ? 'Nenhum ticket escalado'
                : 'Nenhum ticket encontrado'}
            </p>
          </div>
        )}
        </>)}
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
      </div>
      </div>
      )}

      <AutoAssignModal open={showAutoAssignModal} onClose={() => setShowAutoAssignModal(false)} agents={agents}
        onAssign={(ids) => handleAutoAssign(ids)} />

      <ImportHistoryModal open={showImportModal} onClose={() => setShowImportModal(false)} onSuccess={loadTickets} />

      <ComposeEmailModal open={showComposeModal} onClose={() => setShowComposeModal(false)} toast={toast}
        onSuccess={(data) => { loadTickets(); if (data.ticket_number) toast.success(`E-mail enviado! Ticket #${data.ticket_number} criado`) }} />
    </div>
  )
}
