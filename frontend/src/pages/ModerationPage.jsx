import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  getModerationLog, getModerationStats, reviewComment,
  replyToComment, hideComment, reprocessComment,
  syncComments, getModerationSettings, updateModerationSettings,
} from '../services/api'

const ACTION_LABELS = {
  replied: 'Respondido',
  hidden: 'Ocultado',
  hidden_replied: 'Ocultado + Respondido',
  ignored: 'Ignorado',
  flagged: 'Sinalizado',
  pending: 'Pendente',
}

const ACTION_COLORS = {
  replied: { bg: '#dcfce7', text: '#166534', border: '#bbf7d0' },
  hidden: { bg: '#fee2e2', text: '#991b1b', border: '#fecaca' },
  hidden_replied: { bg: '#fef3c7', text: '#92400e', border: '#fde68a' },
  ignored: { bg: '#f3f4f6', text: '#4b5563', border: '#e5e7eb' },
  flagged: { bg: '#fce4ec', text: '#880e4f', border: '#f8bbd0' },
  pending: { bg: '#e0e7ff', text: '#3730a3', border: '#c7d2fe' },
}

const SENTIMENT_LABELS = {
  positive: 'Positivo',
  neutral: 'Neutro',
  negative: 'Negativo',
  offensive: 'Ofensivo',
}

const SENTIMENT_COLORS = {
  positive: '#22c55e',
  neutral: '#6b7280',
  negative: '#f59e0b',
  offensive: '#ef4444',
}

const CATEGORY_LABELS = {
  elogio: 'Elogio',
  duvida: 'Duvida',
  reclamacao: 'Reclamacao',
  ofensivo: 'Ofensivo',
  spam: 'Spam',
  mencao: 'Mencao',
  outro: 'Outro',
}

const PLATFORM_CONFIG = {
  instagram: { icon: 'fa-instagram', color: '#E1306C', label: 'Instagram' },
  facebook: { icon: 'fa-facebook', color: '#1877F2', label: 'Facebook' },
}

export default function ModerationPage() {
  const [comments, setComments] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [statsDays, setStatsDays] = useState(7)

  // Filters
  const [filterPlatform, setFilterPlatform] = useState('')
  const [filterAction, setFilterAction] = useState('')
  const [filterSentiment, setFilterSentiment] = useState('')
  const [searchText, setSearchText] = useState('')
  const [searchDebounced, setSearchDebounced] = useState('')

  // Expanded comment
  const [expandedId, setExpandedId] = useState(null)

  // Reply input
  const [replyingId, setReplyingId] = useState(null)
  const [replyText, setReplyText] = useState('')
  const [replyLoading, setReplyLoading] = useState(false)

  // Settings
  const [aiSettings, setAiSettings] = useState({ ai_enabled: true, auto_reply: true, auto_hide: true })

  // Sync
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState(null)

  // Action loading states
  const [actionLoading, setActionLoading] = useState({})

  const perPage = 30
  const searchTimer = useRef(null)

  // Debounce search
  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => {
      setSearchDebounced(searchText)
      setCurrentPage(1)
    }, 400)
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current) }
  }, [searchText])

  // Load settings
  useEffect(() => {
    getModerationSettings().then(r => setAiSettings(r.data)).catch(() => {})
  }, [])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page: currentPage, per_page: perPage }
      if (filterPlatform) params.platform = filterPlatform
      if (filterAction) params.action = filterAction
      if (filterSentiment) params.sentiment = filterSentiment
      if (searchDebounced) params.search = searchDebounced

      const [logRes, statsRes] = await Promise.all([
        getModerationLog(params),
        getModerationStats(statsDays),
      ])
      setComments(logRes.data.comments || [])
      setTotal(logRes.data.total || 0)
      setStats(statsRes.data)
    } catch (e) {
      console.error('Failed to load moderation data', e)
    } finally {
      setLoading(false)
    }
  }, [currentPage, filterPlatform, filterAction, filterSentiment, searchDebounced, statsDays])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(() => { loadData() }, 30000)
    return () => clearInterval(interval)
  }, [loadData])

  const handleReview = async (id) => {
    try {
      await reviewComment(id)
      setComments(prev => prev.map(c => c.id === id ? { ...c, manually_reviewed: true } : c))
    } catch (e) {
      console.error('Failed to review comment', e)
    }
  }

  const handleReply = async (id) => {
    if (!replyText.trim()) return
    setReplyLoading(true)
    try {
      await replyToComment(id, replyText.trim())
      setComments(prev => prev.map(c => c.id === id ? { ...c, reply_sent: true, ai_reply: replyText.trim(), ai_action: c.ai_action === 'pending' ? 'replied' : c.ai_action } : c))
      setReplyText('')
      setReplyingId(null)
    } catch (e) {
      console.error('Failed to reply', e)
    } finally {
      setReplyLoading(false)
    }
  }

  const handleHide = async (id, hide) => {
    setActionLoading(prev => ({ ...prev, [id]: 'hide' }))
    try {
      await hideComment(id, hide)
      setComments(prev => prev.map(c => c.id === id ? { ...c, was_hidden: hide } : c))
    } catch (e) {
      console.error('Failed to hide/unhide comment', e)
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: null }))
    }
  }

  const handleReprocess = async (id) => {
    setActionLoading(prev => ({ ...prev, [id]: 'reprocess' }))
    try {
      const res = await reprocessComment(id)
      const data = res.data
      setComments(prev => prev.map(c => c.id === id ? {
        ...c,
        ai_action: data.ai_action,
        ai_sentiment: data.ai_sentiment,
        ai_category: data.ai_category,
        ai_confidence: data.ai_confidence,
        ai_reply: data.ai_reply || c.ai_reply,
      } : c))
    } catch (e) {
      console.error('Failed to reprocess comment', e)
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: null }))
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const res = await syncComments({ sync_all: true })
      setSyncResult(res.data)
      loadData()
    } catch (e) {
      console.error('Sync failed', e)
      setSyncResult({ error: true })
    } finally {
      setSyncing(false)
    }
  }

  const handleToggleAI = async (key, value) => {
    const newSettings = { ...aiSettings, [key]: value }
    setAiSettings(newSettings)
    try {
      await updateModerationSettings({ [key]: value })
    } catch (e) {
      console.error('Failed to update settings', e)
      setAiSettings(prev => ({ ...prev, [key]: !value }))
    }
  }

  const clearFilters = () => {
    setFilterPlatform('')
    setFilterAction('')
    setFilterSentiment('')
    setSearchText('')
    setSearchDebounced('')
    setCurrentPage(1)
  }

  const hasFilters = filterPlatform || filterAction || filterSentiment || searchDebounced
  const totalPages = Math.ceil(total / perPage)

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Header with IA toggle and Sync */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            <i className="fab fa-instagram mr-2" style={{ color: '#E1306C' }} />
            Moderacao de Redes Sociais
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Comentarios moderados automaticamente por IA no Instagram e Facebook
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* AI Toggle */}
          <div className="flex items-center gap-2 rounded-xl px-4 py-2" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
            <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>IA</span>
            <button
              onClick={() => handleToggleAI('ai_enabled', !aiSettings.ai_enabled)}
              className="relative w-10 h-5 rounded-full transition-colors"
              style={{ background: aiSettings.ai_enabled ? '#22c55e' : '#6b7280' }}
            >
              <div className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform"
                style={{ left: aiSettings.ai_enabled ? '22px' : '2px' }} />
            </button>
            <span className="text-xs font-medium" style={{ color: aiSettings.ai_enabled ? '#22c55e' : '#ef4444' }}>
              {aiSettings.ai_enabled ? 'Ativa' : 'Desativada'}
            </span>
          </div>

          {/* Auto-reply toggle */}
          <div className="flex items-center gap-2 rounded-xl px-3 py-2" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
            <span className="text-[10px] font-medium" style={{ color: 'var(--text-tertiary)' }}>Auto-reply</span>
            <button
              onClick={() => handleToggleAI('auto_reply', !aiSettings.auto_reply)}
              className="relative w-8 h-4 rounded-full transition-colors"
              style={{ background: aiSettings.auto_reply ? '#22c55e' : '#6b7280' }}
            >
              <div className="absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform"
                style={{ left: aiSettings.auto_reply ? '17px' : '2px' }} />
            </button>
          </div>

          {/* Auto-hide toggle */}
          <div className="flex items-center gap-2 rounded-xl px-3 py-2" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
            <span className="text-[10px] font-medium" style={{ color: 'var(--text-tertiary)' }}>Auto-hide</span>
            <button
              onClick={() => handleToggleAI('auto_hide', !aiSettings.auto_hide)}
              className="relative w-8 h-4 rounded-full transition-colors"
              style={{ background: aiSettings.auto_hide ? '#22c55e' : '#6b7280' }}
            >
              <div className="absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform"
                style={{ left: aiSettings.auto_hide ? '17px' : '2px' }} />
            </button>
          </div>

          {/* Sync button */}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors"
            style={{
              background: syncing ? 'var(--bg-tertiary)' : '#fdd200',
              color: '#1d1d1f',
              opacity: syncing ? 0.7 : 1,
            }}
          >
            <i className={`fas fa-sync-alt ${syncing ? 'fa-spin' : ''}`} />
            {syncing ? 'Sincronizando...' : 'Sincronizar'}
          </button>
        </div>
      </div>

      {/* Sync result toast */}
      {syncResult && (
        <div className="mb-4 rounded-xl p-3 flex items-center justify-between"
          style={{
            background: syncResult.error ? '#fee2e2' : '#dcfce7',
            border: `1px solid ${syncResult.error ? '#fecaca' : '#bbf7d0'}`,
          }}>
          <span className="text-sm font-medium" style={{ color: syncResult.error ? '#991b1b' : '#166534' }}>
            {syncResult.error
              ? 'Erro ao sincronizar comentarios'
              : `Sincronizados ${syncResult.synced} comentarios de ${syncResult.total_posts} posts (${syncResult.errors} erros)`
            }
          </span>
          <button onClick={() => setSyncResult(null)} className="text-xs px-2 py-1 rounded" style={{ color: 'var(--text-secondary)' }}>
            <i className="fas fa-times" />
          </button>
        </div>
      )}

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
          {/* Total */}
          <div className="rounded-xl p-4" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
            <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>Total</p>
            <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{stats.total}</p>
            <p className="text-[10px] mt-1" style={{ color: 'var(--text-tertiary)' }}>ultimos {statsDays} dias</p>
          </div>

          {/* By action */}
          {Object.entries(stats.by_action || {}).map(([action, count]) => (
            <div key={action} className="rounded-xl p-4" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
              <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>
                {ACTION_LABELS[action] || action}
              </p>
              <p className="text-2xl font-bold" style={{ color: ACTION_COLORS[action]?.text || 'var(--text-primary)' }}>
                {count}
              </p>
              <div className="mt-1 h-1 rounded-full" style={{ background: 'var(--bg-tertiary)' }}>
                <div className="h-full rounded-full" style={{
                  width: `${stats.total ? (count / stats.total * 100) : 0}%`,
                  background: ACTION_COLORS[action]?.text || '#6b7280',
                }} />
              </div>
            </div>
          ))}

          {/* By platform */}
          {Object.entries(stats.by_platform || {}).map(([plat, count]) => {
            const cfg = PLATFORM_CONFIG[plat]
            return cfg ? (
              <div key={plat} className="rounded-xl p-4" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
                <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>
                  <i className={`fab ${cfg.icon} mr-1`} style={{ color: cfg.color }} />
                  {cfg.label}
                </p>
                <p className="text-2xl font-bold" style={{ color: cfg.color }}>{count}</p>
              </div>
            ) : null
          })}
        </div>
      )}

      {/* Sentiment breakdown */}
      {stats && stats.by_sentiment && Object.keys(stats.by_sentiment).length > 0 && (
        <div className="rounded-xl p-4 mb-6" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
          <p className="text-xs font-medium mb-3" style={{ color: 'var(--text-tertiary)' }}>Sentimento dos Comentarios</p>
          <div className="flex gap-6 flex-wrap">
            {Object.entries(stats.by_sentiment).map(([sentiment, count]) => (
              <div key={sentiment} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: SENTIMENT_COLORS[sentiment] || '#6b7280' }} />
                <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                  {SENTIMENT_LABELS[sentiment] || sentiment}
                </span>
                <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
                  {count} ({stats.total ? Math.round(count / stats.total * 100) : 0}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters + search + period */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        {/* Search */}
        <div className="relative">
          <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-xs" style={{ color: 'var(--text-tertiary)' }} />
          <input
            type="text"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            placeholder="Buscar comentario ou autor..."
            className="text-sm rounded-lg pl-8 pr-3 py-2 w-64"
            style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)' }}
          />
        </div>

        <select
          value={filterPlatform}
          onChange={e => { setFilterPlatform(e.target.value); setCurrentPage(1) }}
          className="text-sm rounded-lg px-3 py-2"
          style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)' }}
        >
          <option value="">Todas plataformas</option>
          <option value="instagram">Instagram</option>
          <option value="facebook">Facebook</option>
        </select>

        <select
          value={filterAction}
          onChange={e => { setFilterAction(e.target.value); setCurrentPage(1) }}
          className="text-sm rounded-lg px-3 py-2"
          style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)' }}
        >
          <option value="">Todas acoes</option>
          <option value="replied">Respondido</option>
          <option value="hidden">Ocultado</option>
          <option value="hidden_replied">Ocultado + Respondido</option>
          <option value="ignored">Ignorado</option>
          <option value="pending">Pendente</option>
        </select>

        <select
          value={filterSentiment}
          onChange={e => { setFilterSentiment(e.target.value); setCurrentPage(1) }}
          className="text-sm rounded-lg px-3 py-2"
          style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)' }}
        >
          <option value="">Todos sentimentos</option>
          <option value="positive">Positivo</option>
          <option value="neutral">Neutro</option>
          <option value="negative">Negativo</option>
          <option value="offensive">Ofensivo</option>
        </select>

        {hasFilters && (
          <button
            onClick={clearFilters}
            className="text-xs px-3 py-2 rounded-lg font-medium"
            style={{ color: '#ef4444' }}
          >
            <i className="fas fa-times mr-1" /> Limpar filtros
          </button>
        )}

        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Periodo:</span>
          <select
            value={statsDays}
            onChange={e => setStatsDays(Number(e.target.value))}
            className="text-sm rounded-lg px-3 py-2"
            style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)' }}
          >
            <option value={7}>7 dias</option>
            <option value={14}>14 dias</option>
            <option value={30}>30 dias</option>
          </select>
        </div>
      </div>

      {/* Comments list */}
      <div className="rounded-xl overflow-hidden" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
        {loading ? (
          <div className="p-12 text-center">
            <i className="fas fa-spinner fa-spin text-xl mb-2" style={{ color: 'var(--text-tertiary)' }} />
            <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Carregando moderacao...</p>
          </div>
        ) : comments.length === 0 ? (
          <div className="p-12 text-center">
            <i className="fas fa-shield-alt text-3xl mb-3" style={{ color: 'var(--text-tertiary)' }} />
            <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Nenhum comentario moderado</p>
            <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
              Clique em "Sincronizar" para puxar comentarios do Facebook e Instagram
            </p>
          </div>
        ) : (
          <>
            {/* Table header */}
            <div className="grid grid-cols-12 gap-2 px-4 py-3 text-xs font-semibold uppercase tracking-wider"
              style={{ color: 'var(--text-tertiary)', borderBottom: '1px solid var(--border-primary)' }}>
              <div className="col-span-1">Plataforma</div>
              <div className="col-span-3">Comentario</div>
              <div className="col-span-1">Autor</div>
              <div className="col-span-1">Sentimento</div>
              <div className="col-span-1">Categoria</div>
              <div className="col-span-1">Acao IA</div>
              <div className="col-span-1">Confianca</div>
              <div className="col-span-3 text-right">Acoes</div>
            </div>

            {/* Rows */}
            {comments.map(c => {
              const platCfg = PLATFORM_CONFIG[c.platform] || {}
              const actionColor = ACTION_COLORS[c.ai_action] || ACTION_COLORS.ignored
              const isExpanded = expandedId === c.id
              const isActioning = actionLoading[c.id]

              return (
                <div key={c.id}>
                  <div
                    className="grid grid-cols-12 gap-2 px-4 py-3 items-center cursor-pointer transition-colors"
                    style={{ borderBottom: '1px solid var(--border-primary)' }}
                    onClick={() => setExpandedId(isExpanded ? null : c.id)}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    {/* Platform */}
                    <div className="col-span-1">
                      <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full"
                        style={{ background: `${platCfg.color}20`, color: platCfg.color }}>
                        <i className={`fab ${platCfg.icon}`} />
                        {platCfg.label}
                      </span>
                    </div>

                    {/* Comment text */}
                    <div className="col-span-3">
                      <p className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>{c.text}</p>
                    </div>

                    {/* Author */}
                    <div className="col-span-1">
                      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                        {c.author_name || 'Anonimo'}
                      </span>
                    </div>

                    {/* Sentiment */}
                    <div className="col-span-1">
                      <span className="inline-flex items-center gap-1 text-xs font-medium">
                        <span className="w-2 h-2 rounded-full" style={{ background: SENTIMENT_COLORS[c.ai_sentiment] || '#6b7280' }} />
                        <span style={{ color: 'var(--text-secondary)' }}>
                          {SENTIMENT_LABELS[c.ai_sentiment] || c.ai_sentiment || '-'}
                        </span>
                      </span>
                    </div>

                    {/* Category */}
                    <div className="col-span-1">
                      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                        {CATEGORY_LABELS[c.ai_category] || c.ai_category || '-'}
                      </span>
                    </div>

                    {/* AI Action */}
                    <div className="col-span-1">
                      <span className="inline-flex items-center text-xs font-medium px-2 py-1 rounded-md"
                        style={{ background: actionColor.bg, color: actionColor.text, border: `1px solid ${actionColor.border}` }}>
                        {c.ai_action === 'replied' && <i className="fas fa-reply mr-1" />}
                        {c.ai_action === 'hidden' && <i className="fas fa-eye-slash mr-1" />}
                        {c.ai_action === 'hidden_replied' && <i className="fas fa-shield-alt mr-1" />}
                        {c.ai_action === 'ignored' && <i className="fas fa-minus mr-1" />}
                        {c.ai_action === 'pending' && <i className="fas fa-clock mr-1" />}
                        {ACTION_LABELS[c.ai_action] || c.ai_action}
                      </span>
                    </div>

                    {/* Confidence */}
                    <div className="col-span-1">
                      <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                        {c.ai_confidence ? `${Math.round(c.ai_confidence * 100)}%` : '-'}
                      </span>
                    </div>

                    {/* Actions */}
                    <div className="col-span-3 flex items-center justify-end gap-1" onClick={e => e.stopPropagation()}>
                      {/* Reply button */}
                      <button
                        onClick={() => { setReplyingId(replyingId === c.id ? null : c.id); setExpandedId(c.id) }}
                        className="text-xs font-medium px-2 py-1 rounded-md transition-colors"
                        style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}
                        title="Responder"
                      >
                        <i className="fas fa-reply" />
                      </button>

                      {/* Hide/Unhide button */}
                      <button
                        onClick={() => handleHide(c.id, !c.was_hidden)}
                        disabled={isActioning === 'hide'}
                        className="text-xs font-medium px-2 py-1 rounded-md transition-colors"
                        style={{
                          background: c.was_hidden ? '#fee2e2' : 'var(--bg-tertiary)',
                          color: c.was_hidden ? '#991b1b' : 'var(--text-secondary)',
                        }}
                        title={c.was_hidden ? 'Mostrar' : 'Ocultar'}
                      >
                        <i className={`fas ${isActioning === 'hide' ? 'fa-spinner fa-spin' : (c.was_hidden ? 'fa-eye' : 'fa-eye-slash')}`} />
                      </button>

                      {/* Reprocess button */}
                      <button
                        onClick={() => handleReprocess(c.id)}
                        disabled={isActioning === 'reprocess'}
                        className="text-xs font-medium px-2 py-1 rounded-md transition-colors"
                        style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}
                        title="Reprocessar IA"
                      >
                        <i className={`fas ${isActioning === 'reprocess' ? 'fa-spinner fa-spin' : 'fa-robot'}`} />
                      </button>

                      {/* Review button */}
                      {c.manually_reviewed ? (
                        <span className="text-xs font-medium px-2 py-1 rounded-md"
                          style={{ background: '#dbeafe', color: '#1e40af' }}>
                          <i className="fas fa-check" />
                        </span>
                      ) : (
                        <button
                          onClick={() => handleReview(c.id)}
                          className="text-xs font-medium px-2 py-1 rounded-md transition-colors"
                          style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}
                          title="Marcar como revisado"
                          onMouseEnter={e => { e.currentTarget.style.background = '#fdd200'; e.currentTarget.style.color = '#1d1d1f' }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
                        >
                          <i className="fas fa-check" />
                        </button>
                      )}

                      <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'} text-xs ml-1`}
                        style={{ color: 'var(--text-tertiary)', cursor: 'pointer' }}
                        onClick={() => setExpandedId(isExpanded ? null : c.id)} />
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {isExpanded && (
                    <div className="px-6 py-4" style={{ background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-primary)' }}>
                      <div className="grid grid-cols-2 gap-6">
                        <div>
                          <p className="text-xs font-semibold mb-2" style={{ color: 'var(--text-tertiary)' }}>COMENTARIO COMPLETO</p>
                          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>{c.text}</p>
                          <div className="mt-3 flex gap-4 text-xs flex-wrap" style={{ color: 'var(--text-tertiary)' }}>
                            <span><i className="fas fa-user mr-1" /> {c.author_name || 'Anonimo'}</span>
                            <span><i className="fas fa-clock mr-1" /> {c.created_at ? new Date(c.created_at).toLocaleString('pt-BR') : '-'}</span>
                            {c.reply_sent && <span className="text-green-500"><i className="fas fa-check-circle mr-1" /> Resposta enviada</span>}
                            {c.was_hidden && <span className="text-red-500"><i className="fas fa-eye-slash mr-1" /> Comentario ocultado</span>}
                          </div>
                        </div>
                        {c.ai_reply && (
                          <div>
                            <p className="text-xs font-semibold mb-2" style={{ color: 'var(--text-tertiary)' }}>RESPOSTA DA IA</p>
                            <div className="rounded-lg p-3 text-sm" style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}>
                              {c.ai_reply}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Manual reply input */}
                      {replyingId === c.id && (
                        <div className="mt-4 flex gap-2">
                          <textarea
                            value={replyText}
                            onChange={e => setReplyText(e.target.value)}
                            placeholder="Escreva sua resposta..."
                            rows={2}
                            className="flex-1 text-sm rounded-lg px-3 py-2 resize-none"
                            style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)' }}
                            onKeyDown={e => { if (e.key === 'Enter' && e.metaKey) handleReply(c.id) }}
                          />
                          <div className="flex flex-col gap-1">
                            <button
                              onClick={() => handleReply(c.id)}
                              disabled={replyLoading || !replyText.trim()}
                              className="px-4 py-2 rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
                              style={{ background: '#fdd200', color: '#1d1d1f' }}
                            >
                              {replyLoading ? <i className="fas fa-spinner fa-spin" /> : <><i className="fas fa-paper-plane mr-1" /> Enviar</>}
                            </button>
                            <button
                              onClick={() => { setReplyingId(null); setReplyText('') }}
                              className="px-4 py-1 rounded-lg text-xs"
                              style={{ color: 'var(--text-tertiary)' }}
                            >
                              Cancelar
                            </button>
                          </div>
                        </div>
                      )}

                      {c.reviewed_by && (
                        <p className="mt-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          <i className="fas fa-user-check mr-1" /> Revisado por: {c.reviewed_by}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3">
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  Mostrando {(currentPage - 1) * perPage + 1}-{Math.min(currentPage * perPage, total)} de {total}
                </p>
                <div className="flex gap-1">
                  <button
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage(p => p - 1)}
                    className="px-3 py-1 rounded-lg text-xs font-medium disabled:opacity-30"
                    style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}
                  >
                    <i className="fas fa-chevron-left" />
                  </button>
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const start = Math.max(1, Math.min(currentPage - 2, totalPages - 4))
                    const p = start + i
                    if (p > totalPages) return null
                    return (
                      <button
                        key={p}
                        onClick={() => setCurrentPage(p)}
                        className="px-3 py-1 rounded-lg text-xs font-medium"
                        style={{
                          background: p === currentPage ? '#fdd200' : 'var(--bg-tertiary)',
                          color: p === currentPage ? '#1d1d1f' : 'var(--text-secondary)',
                        }}
                      >
                        {p}
                      </button>
                    )
                  })}
                  <button
                    disabled={currentPage === totalPages}
                    onClick={() => setCurrentPage(p => p + 1)}
                    className="px-3 py-1 rounded-lg text-xs font-medium disabled:opacity-30"
                    style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}
                  >
                    <i className="fas fa-chevron-right" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
