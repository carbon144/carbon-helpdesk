import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  getModerationLog, getModerationStats, reviewComment,
  replyToComment, hideComment, reprocessComment, analyzeComment,
  syncComments, getModerationSettings, updateModerationSettings,
  getModerationPostsGrouped, getMetaPosts,
} from '../services/api'

const ACTION_LABELS = {
  replied: 'Respondido', hidden: 'Ocultado', hidden_replied: 'Ocultado + Respondido',
  ignored: 'Ignorado', flagged: 'Sinalizado', pending: 'Pendente',
}
const ACTION_COLORS = {
  replied: { bg: '#dcfce7', text: '#166534', icon: 'fa-reply' },
  hidden: { bg: '#fee2e2', text: '#991b1b', icon: 'fa-eye-slash' },
  hidden_replied: { bg: '#fef3c7', text: '#92400e', icon: 'fa-shield-alt' },
  ignored: { bg: '#f3f4f6', text: '#4b5563', icon: 'fa-check' },
  flagged: { bg: '#fce4ec', text: '#880e4f', icon: 'fa-flag' },
  pending: { bg: '#e0e7ff', text: '#3730a3', icon: 'fa-clock' },
}
const SENTIMENT_MAP = {
  positive: { label: 'Positivo', color: '#22c55e', bg: '#dcfce7', icon: 'fa-smile' },
  neutral: { label: 'Neutro', color: '#6b7280', bg: '#f3f4f6', icon: 'fa-meh' },
  negative: { label: 'Negativo', color: '#f59e0b', bg: '#fef3c7', icon: 'fa-frown' },
  offensive: { label: 'Ofensivo', color: '#ef4444', bg: '#fee2e2', icon: 'fa-angry' },
}

function getTimeAgo(dateStr) {
  const now = new Date()
  const date = new Date(dateStr)
  const diff = (now - date) / 1000
  if (diff < 60) return 'agora'
  if (diff < 3600) return `${Math.floor(diff / 60)}min`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  if (diff < 604800) return `${Math.floor(diff / 86400)}d`
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
}

function ActionBtn({ icon, label, onClick, loading, color, active, disabled, small }) {
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className={`inline-flex items-center gap-1.5 ${small ? 'px-2 py-1 text-[11px]' : 'px-2.5 py-1.5 text-xs'} rounded-lg font-medium transition-all disabled:opacity-40`}
      style={{
        background: active ? color || '#E5A800' : 'var(--bg-tertiary)',
        color: active ? '#fff' : 'var(--text-secondary)',
        border: `1px solid ${active ? 'transparent' : 'var(--border-primary)'}`,
      }}
      onMouseEnter={e => { if (!active && !disabled) { e.currentTarget.style.background = color ? `${color}18` : 'var(--bg-hover)'; e.currentTarget.style.borderColor = color || 'var(--border-primary)' }}}
      onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.borderColor = 'var(--border-primary)' }}}
    >
      <i className={`fas ${loading ? 'fa-spinner fa-spin' : icon}`} />
      {label}
    </button>
  )
}

function Toggle({ label, value, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-medium" style={{ color: 'var(--text-tertiary)' }}>{label}</span>
      <button onClick={() => onChange(!value)}
        className="relative w-8 h-4 rounded-full transition-colors"
        style={{ background: value ? '#22c55e' : '#6b7280' }}>
        <div className="absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform"
          style={{ left: value ? '17px' : '2px' }} />
      </button>
    </div>
  )
}

/* ── Post list item (left panel) ── */
function PostItem({ post, metaPost, isActive, onClick, platform }) {
  const thumb = metaPost?.image
  const caption = post.post_caption || metaPost?.text || 'Post sem legenda'
  const latest = post.latest_comment
  const timeAgo = post.latest_commented_at ? getTimeAgo(post.latest_commented_at) : ''
  const platformColor = platform === 'instagram' ? '#E1306C' : '#1877F2'

  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-3 transition-all border-b flex gap-3"
      style={{
        background: isActive ? 'var(--bg-tertiary)' : 'transparent',
        borderColor: 'var(--border-primary)',
        borderLeft: isActive ? `3px solid ${platformColor}` : '3px solid transparent',
      }}
      onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--bg-secondary)' }}
      onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent' }}
    >
      {/* Thumbnail */}
      <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0" style={{ background: 'var(--bg-tertiary)' }}>
        {thumb ? (
          <img src={thumb} alt="" className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <i className={`fab fa-${platform} text-lg`} style={{ color: platformColor, opacity: 0.5 }} />
          </div>
        )}
      </div>

      {/* Text content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
            {caption.substring(0, 50)}{caption.length > 50 ? '...' : ''}
          </p>
          <span className="text-[10px] shrink-0" style={{ color: 'var(--text-tertiary)' }}>{timeAgo}</span>
        </div>
        {latest && (
          <p className="text-[11px] truncate mt-0.5" style={{ color: 'var(--text-secondary)' }}>
            <span className="font-medium">{latest.author_name || 'Anonimo'}</span>
            {' - '}
            {latest.text?.substring(0, 40)}{(latest.text?.length || 0) > 40 ? '...' : ''}
          </p>
        )}
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
            style={{ background: 'var(--bg-tertiary)', color: 'var(--text-tertiary)' }}>
            <i className="fas fa-comment mr-0.5" />{post.comment_count}
          </span>
          {post.pending_count > 0 && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
              style={{ background: '#fef3c7', color: '#92400e' }}>
              <i className="fas fa-clock mr-0.5" />{post.pending_count} pendente{post.pending_count > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

/* ── Comment in the right panel ── */
function CommentItem({ c, onReply, onHide, onReprocess, onAnalyze, onReview, actionLoading }) {
  const [replying, setReplying] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [replyLoading, setReplyLoading] = useState(false)

  const sentiment = SENTIMENT_MAP[c.ai_sentiment]
  const action = ACTION_COLORS[c.ai_action] || ACTION_COLORS.pending
  const isLoading = actionLoading[c.id]
  const timeAgo = c.commented_at ? getTimeAgo(c.commented_at) : c.created_at ? getTimeAgo(c.created_at) : ''
  const isReply = !!c.parent_comment_id

  const handleSendReply = async () => {
    if (!replyText.trim()) return
    setReplyLoading(true)
    try {
      await onReply(c.id, replyText.trim())
      setReplyText('')
      setReplying(false)
    } finally {
      setReplyLoading(false)
    }
  }

  return (
    <div className={`py-3 ${isReply ? 'ml-10' : ''}`} style={{ borderBottom: '1px solid var(--border-primary)' }}>
      {/* Author row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
            style={{ background: c.platform === 'instagram' ? '#E1306C' : '#1877F2', color: '#fff' }}>
            {(c.author_name || '?')[0].toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                {c.author_name || 'Anonimo'}
              </span>
              <span className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>{timeAgo}</span>
            </div>
          </div>
        </div>

        {/* Badges */}
        <div className="flex items-center gap-1 shrink-0">
          {sentiment && (
            <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full"
              style={{ background: sentiment.bg, color: sentiment.color }}>
              <i className={`fas ${sentiment.icon}`} style={{ fontSize: 8 }} />
              {sentiment.label}
            </span>
          )}
          <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full"
            style={{ background: action.bg, color: action.text }}>
            <i className={`fas ${action.icon}`} style={{ fontSize: 8 }} />
            {ACTION_LABELS[c.ai_action] || c.ai_action}
          </span>
        </div>
      </div>

      {/* Comment text */}
      <p className="text-sm mt-1.5 ml-10 leading-relaxed" style={{ color: 'var(--text-primary)' }}>
        {c.text}
      </p>

      {/* AI Reply preview */}
      {c.ai_reply && (
        <div className="ml-10 mt-2 rounded-lg p-2" style={{ background: 'var(--bg-tertiary)', borderLeft: '3px solid #22c55e' }}>
          <div className="flex items-center gap-1.5 mb-0.5">
            <i className="fas fa-robot text-[9px]" style={{ color: '#22c55e' }} />
            <span className="text-[10px] font-semibold uppercase" style={{ color: '#22c55e' }}>Resposta IA</span>
            {c.reply_sent && (
              <span className="text-[10px] font-medium ml-auto" style={{ color: '#22c55e' }}>
                <i className="fas fa-check-circle mr-0.5" /> Enviada
              </span>
            )}
          </div>
          <p className="text-xs leading-relaxed" style={{ color: 'var(--text-primary)' }}>{c.ai_reply}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="ml-10 mt-2 flex items-center gap-1.5 flex-wrap">
        <ActionBtn icon="fa-robot" label="Analisar" onClick={() => onAnalyze(c.id)}
          loading={isLoading === 'analyze'} color="#8b5cf6" small />
        <ActionBtn icon="fa-magic" label="Ação IA" onClick={() => onReprocess(c.id)}
          loading={isLoading === 'reprocess'} color="#f59e0b" small />
        <ActionBtn icon="fa-reply" label="Responder" onClick={() => setReplying(!replying)}
          active={replying} color="#3b82f6" small />
        <ActionBtn icon={c.was_hidden ? 'fa-eye' : 'fa-eye-slash'} label={c.was_hidden ? 'Mostrar' : 'Ocultar'}
          onClick={() => onHide(c.id, !c.was_hidden)} loading={isLoading === 'hide'} color="#ef4444" small />
        {c.manually_reviewed ? (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full ml-auto"
            style={{ background: '#dbeafe', color: '#1e40af' }}>
            <i className="fas fa-check-circle" /> Revisado
          </span>
        ) : (
          <ActionBtn icon="fa-check" label="Revisar" onClick={() => onReview(c.id)} color="#22c55e" small />
        )}
        {c.ai_confidence != null && (
          <span className="text-[10px] ml-auto" style={{ color: 'var(--text-tertiary)' }}>
            {Math.round(c.ai_confidence * 100)}%
          </span>
        )}
      </div>

      {/* Reply input */}
      {replying && (
        <div className="ml-10 mt-2">
          <div className="flex gap-2">
            <textarea
              value={replyText}
              onChange={e => setReplyText(e.target.value)}
              placeholder="Escreva sua resposta..."
              rows={2}
              className="flex-1 text-sm rounded-lg px-3 py-2 resize-none"
              style={{ background: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)' }}
              onKeyDown={e => { if (e.key === 'Enter' && e.metaKey) handleSendReply() }}
              autoFocus
            />
            <div className="flex flex-col gap-1">
              <button onClick={handleSendReply} disabled={replyLoading || !replyText.trim()}
                className="px-3 py-2 rounded-lg text-xs font-semibold transition-colors disabled:opacity-40"
                style={{ background: '#E5A800', color: '#FFFFFF' }}>
                {replyLoading ? <i className="fas fa-spinner fa-spin" /> : <i className="fas fa-paper-plane" />}
              </button>
              <button onClick={() => { setReplying(false); setReplyText('') }}
                className="text-[10px] rounded-lg py-1" style={{ color: 'var(--text-tertiary)' }}>
                <i className="fas fa-times" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Main Page ── */
export default function ModerationPage() {
  // Data
  const [groupedPosts, setGroupedPosts] = useState([])
  const [metaPosts, setMetaPosts] = useState([])
  const [comments, setComments] = useState([])
  const [stats, setStats] = useState(null)

  // Selection
  const [activeTab, setActiveTab] = useState('instagram')
  const [selectedPostId, setSelectedPostId] = useState(null)

  // Loading
  const [loadingPosts, setLoadingPosts] = useState(true)
  const [loadingComments, setLoadingComments] = useState(false)

  // Filters
  const [filterDays, setFilterDays] = useState(7)

  // Settings
  const [aiSettings, setAiSettings] = useState({ ai_enabled: true, auto_reply: true, auto_hide: true })

  // Sync
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState(null)

  // Action loading
  const [actionLoading, setActionLoading] = useState({})

  // AI batch
  const [batchLoading, setBatchLoading] = useState(false)

  // Load settings
  useEffect(() => {
    getModerationSettings().then(r => setAiSettings(r.data)).catch(() => {})
  }, [])

  // Load posts list (left panel)
  const loadPosts = useCallback(async () => {
    setLoadingPosts(true)
    try {
      const [groupedRes, metaRes, statsRes] = await Promise.all([
        getModerationPostsGrouped({ platform: activeTab, days: filterDays }),
        getMetaPosts({ platform: activeTab }),
        getModerationStats(filterDays),
      ])
      setGroupedPosts(groupedRes.data.posts || [])
      setMetaPosts(metaRes.data.posts || [])
      setStats(statsRes.data)

      // Auto-select first post if none selected
      const posts = groupedRes.data.posts || []
      if (posts.length > 0 && (!selectedPostId || !posts.find(p => p.post_id === selectedPostId))) {
        setSelectedPostId(posts[0].post_id)
      }
    } catch (e) {
      console.error('Failed to load posts', e)
    } finally {
      setLoadingPosts(false)
    }
  }, [activeTab, filterDays])

  useEffect(() => { loadPosts() }, [loadPosts])

  // Load comments for selected post (right panel)
  const loadComments = useCallback(async () => {
    if (!selectedPostId) { setComments([]); return }
    setLoadingComments(true)
    try {
      const res = await getModerationLog({
        post_id: selectedPostId,
        platform: activeTab,
        days: filterDays,
        per_page: 200,
      })
      setComments(res.data.comments || [])
    } catch (e) {
      console.error('Failed to load comments', e)
    } finally {
      setLoadingComments(false)
    }
  }, [selectedPostId, activeTab, filterDays])

  useEffect(() => { loadComments() }, [loadComments])

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        loadPosts()
        if (selectedPostId) loadComments()
      }
    }, 45000)
    return () => clearInterval(interval)
  }, [loadPosts, loadComments, selectedPostId])

  // Get meta post data for selected post
  const selectedMeta = metaPosts.find(p => p.id === selectedPostId)
  const selectedGrouped = groupedPosts.find(p => p.post_id === selectedPostId)

  // Handlers
  const handleReply = async (id, text) => {
    try {
      await replyToComment(id, text)
      setComments(prev => prev.map(c => c.id === id
        ? { ...c, reply_sent: true, ai_reply: text, ai_action: c.ai_action === 'pending' ? 'replied' : c.ai_action }
        : c))
    } catch (e) {
      console.error('Failed to reply', e)
    }
  }

  const handleHide = async (id, hide) => {
    setActionLoading(prev => ({ ...prev, [id]: 'hide' }))
    try {
      await hideComment(id, hide)
      setComments(prev => prev.map(c => c.id === id ? { ...c, was_hidden: hide } : c))
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: null }))
    }
  }

  const handleReprocess = async (id) => {
    setActionLoading(prev => ({ ...prev, [id]: 'reprocess' }))
    try {
      const res = await reprocessComment(id)
      const d = res.data
      setComments(prev => prev.map(c => c.id === id ? {
        ...c, ai_action: d.ai_action, ai_sentiment: d.ai_sentiment,
        ai_category: d.ai_category, ai_confidence: d.ai_confidence,
        ai_reply: d.ai_reply || c.ai_reply,
      } : c))
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: null }))
    }
  }

  const handleAnalyze = async (id) => {
    setActionLoading(prev => ({ ...prev, [id]: 'analyze' }))
    try {
      const res = await analyzeComment(id)
      const d = res.data
      setComments(prev => prev.map(c => c.id === id ? {
        ...c, ai_sentiment: d.ai_sentiment, ai_category: d.ai_category,
        ai_confidence: d.ai_confidence,
      } : c))
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: null }))
    }
  }

  const handleReview = async (id) => {
    try {
      await reviewComment(id)
      setComments(prev => prev.map(c => c.id === id ? { ...c, manually_reviewed: true } : c))
    } catch (e) {
      console.error('Failed to review', e)
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const res = await syncComments({ sync_all: true, days: filterDays })
      setSyncResult(res.data)
      loadPosts()
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
      setAiSettings(prev => ({ ...prev, [key]: !value }))
    }
  }

  // Analyze all pending comments in selected post
  const handleAnalyzeAll = async () => {
    const pending = comments.filter(c => c.ai_action === 'pending')
    if (pending.length === 0) return
    setBatchLoading(true)
    for (const c of pending) {
      try {
        await handleAnalyze(c.id)
      } catch (e) { /* continue */ }
    }
    setBatchLoading(false)
  }

  // Reprocess all pending comments (with actions)
  const handleReprocessAll = async () => {
    const pending = comments.filter(c => c.ai_action === 'pending')
    if (pending.length === 0) return
    setBatchLoading(true)
    for (const c of pending) {
      try {
        await handleReprocess(c.id)
      } catch (e) { /* continue */ }
    }
    setBatchLoading(false)
  }

  const platStats = stats?.by_platform || {}
  const pendingInPost = comments.filter(c => c.ai_action === 'pending').length

  return (
    <div className="h-full flex flex-col" style={{ height: 'calc(100vh - 56px)' }}>

      {/* Top bar */}
      <div className="px-4 py-3 flex items-center justify-between shrink-0" style={{ borderBottom: '1px solid var(--border-primary)' }}>
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            Moderação Social
          </h1>

          {/* Platform tabs */}
          <div className="flex items-center gap-1 p-0.5 rounded-lg" style={{ background: 'var(--bg-tertiary)' }}>
            {[
              { id: 'instagram', icon: 'fa-instagram', gradient: 'linear-gradient(135deg, #E1306C, #F77737)', label: 'Instagram', count: platStats.instagram },
              { id: 'facebook', icon: 'fa-facebook', gradient: 'linear-gradient(135deg, #1877F2, #42b0ff)', label: 'Facebook', count: platStats.facebook },
            ].map(tab => {
              const isActive = activeTab === tab.id
              return (
                <button key={tab.id}
                  onClick={() => { setActiveTab(tab.id); setSelectedPostId(null) }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all"
                  style={{
                    background: isActive ? tab.gradient : 'transparent',
                    color: isActive ? '#fff' : 'var(--text-secondary)',
                    boxShadow: isActive ? '0 1px 4px rgba(0,0,0,0.15)' : 'none',
                  }}>
                  <i className={`fab ${tab.icon}`} />
                  {tab.label}
                  {tab.count != null && (
                    <span className="text-[10px] px-1 py-0.5 rounded-full font-bold"
                      style={{ background: isActive ? 'rgba(255,255,255,0.25)' : 'var(--bg-secondary)', color: isActive ? '#fff' : 'var(--text-tertiary)' }}>
                      {tab.count}
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          {/* Period filter */}
          <div className="flex items-center gap-0.5 p-0.5 rounded-lg" style={{ background: 'var(--bg-tertiary)' }}>
            {[1, 2, 3, 7].map(d => (
              <button key={d} onClick={() => { setFilterDays(d); setSelectedPostId(null) }}
                className="px-2 py-1 rounded-md text-[11px] font-medium transition-all"
                style={{
                  background: filterDays === d ? 'var(--bg-secondary)' : 'transparent',
                  color: filterDays === d ? 'var(--text-primary)' : 'var(--text-tertiary)',
                  boxShadow: filterDays === d ? '0 1px 2px rgba(0,0,0,0.08)' : 'none',
                }}>
                {d}d
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-3 rounded-lg px-3 py-1.5" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
            <Toggle label="IA" value={aiSettings.ai_enabled} onChange={v => handleToggleAI('ai_enabled', v)} />
            <div style={{ width: 1, height: 14, background: 'var(--border-primary)' }} />
            <Toggle label="Auto-reply" value={aiSettings.auto_reply} onChange={v => handleToggleAI('auto_reply', v)} />
            <Toggle label="Auto-hide" value={aiSettings.auto_hide} onChange={v => handleToggleAI('auto_hide', v)} />
          </div>
          <button onClick={handleSync} disabled={syncing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
            style={{ background: syncing ? 'var(--bg-tertiary)' : '#E5A800', color: '#FFFFFF', opacity: syncing ? 0.7 : 1 }}>
            <i className={`fas fa-sync-alt ${syncing ? 'fa-spin' : ''}`} />
            {syncing ? 'Sincronizando...' : 'Sincronizar'}
          </button>
        </div>
      </div>

      {/* Sync result toast */}
      {syncResult && (
        <div className="mx-4 mt-2 rounded-lg p-2.5 flex items-center justify-between"
          style={{ background: syncResult.error ? '#fee2e2' : '#dcfce7', border: `1px solid ${syncResult.error ? '#fecaca' : '#bbf7d0'}` }}>
          <span className="text-xs font-medium" style={{ color: syncResult.error ? '#991b1b' : '#166534' }}>
            {syncResult.error
              ? 'Erro ao sincronizar'
              : `${syncResult.synced} novos comentarios de ${syncResult.total_posts} posts (ultimos ${syncResult.days_filter || 7}d)${syncResult.skipped_old ? ` · ${syncResult.skipped_old} antigos ignorados` : ''}`}
          </span>
          <button onClick={() => setSyncResult(null)} className="text-xs px-1" style={{ color: 'var(--text-secondary)' }}>
            <i className="fas fa-times" />
          </button>
        </div>
      )}

      {/* Main split layout */}
      <div className="flex flex-1 min-h-0">

        {/* ── LEFT PANEL: Posts list ── */}
        <div className="w-[340px] shrink-0 overflow-y-auto" style={{ borderRight: '1px solid var(--border-primary)' }}>
          {loadingPosts ? (
            <div className="py-12 text-center">
              <i className="fas fa-spinner fa-spin text-lg" style={{ color: 'var(--text-tertiary)' }} />
            </div>
          ) : groupedPosts.length === 0 ? (
            <div className="py-12 text-center px-6">
              <i className={`fab fa-${activeTab} text-3xl mb-2`}
                style={{ color: activeTab === 'instagram' ? '#E1306C' : '#1877F2', opacity: 0.3 }} />
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                Nenhum comentario nos ultimos {filterDays}d
              </p>
              <p className="text-[10px] mt-1" style={{ color: 'var(--text-tertiary)' }}>
                Clique em Sincronizar para importar
              </p>
            </div>
          ) : (
            groupedPosts.map(post => (
              <PostItem
                key={post.post_id}
                post={post}
                metaPost={metaPosts.find(mp => mp.id === post.post_id)}
                isActive={selectedPostId === post.post_id}
                onClick={() => setSelectedPostId(post.post_id)}
                platform={activeTab}
              />
            ))
          )}
        </div>

        {/* ── RIGHT PANEL: Post detail + comments ── */}
        <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
          {!selectedPostId ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <i className="fas fa-comments text-4xl mb-3" style={{ color: 'var(--text-tertiary)', opacity: 0.2 }} />
                <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
                  Selecione um post para ver os comentarios
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Post header with media */}
              <div className="shrink-0" style={{ borderBottom: '1px solid var(--border-primary)' }}>
                {/* Media */}
                {selectedMeta?.image && (
                  <div className="relative w-full" style={{ maxHeight: 300, overflow: 'hidden', background: '#000' }}>
                    <img
                      src={selectedMeta.image}
                      alt=""
                      className="w-full object-contain"
                      style={{ maxHeight: 300 }}
                    />
                  </div>
                )}

                {/* Post info */}
                <div className="px-4 py-3">
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                    {selectedGrouped?.post_caption || selectedMeta?.text || 'Post sem legenda'}
                  </p>
                  <div className="flex items-center gap-4 mt-2">
                    {selectedMeta?.url && (
                      <a href={selectedMeta.url} target="_blank" rel="noopener noreferrer"
                        className="text-[11px] font-medium transition-colors hover:underline"
                        style={{ color: activeTab === 'instagram' ? '#E1306C' : '#1877F2' }}>
                        <i className={`fab fa-${activeTab} mr-1`} /> Ver no {activeTab === 'instagram' ? 'Instagram' : 'Facebook'}
                      </a>
                    )}
                    <span className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
                      <i className="fas fa-comment mr-1" /> {comments.length} comentarios
                    </span>
                    {selectedMeta?.comment_count != null && selectedMeta.comment_count !== comments.length && (
                      <span className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
                        ({selectedMeta.comment_count} no total)
                      </span>
                    )}
                  </div>

                  {/* Batch AI actions */}
                  {pendingInPost > 0 && (
                    <div className="flex items-center gap-2 mt-3 pt-3" style={{ borderTop: '1px solid var(--border-primary)' }}>
                      <span className="text-[11px] font-medium" style={{ color: 'var(--text-tertiary)' }}>
                        {pendingInPost} pendente{pendingInPost > 1 ? 's' : ''}
                      </span>
                      <ActionBtn icon="fa-robot" label={`Analisar todos (${pendingInPost})`}
                        onClick={handleAnalyzeAll} loading={batchLoading} color="#8b5cf6" small />
                      <ActionBtn icon="fa-magic" label={`Ação IA todos (${pendingInPost})`}
                        onClick={handleReprocessAll} loading={batchLoading} color="#f59e0b" small />
                    </div>
                  )}
                </div>
              </div>

              {/* Comments list */}
              <div className="flex-1 px-4">
                {loadingComments ? (
                  <div className="py-12 text-center">
                    <i className="fas fa-spinner fa-spin text-lg" style={{ color: 'var(--text-tertiary)' }} />
                  </div>
                ) : comments.length === 0 ? (
                  <div className="py-12 text-center">
                    <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
                      Nenhum comentario sincronizado para este post
                    </p>
                  </div>
                ) : (
                  comments.map(c => (
                    <CommentItem key={c.id} c={c}
                      onReply={handleReply} onHide={handleHide}
                      onReprocess={handleReprocess} onAnalyze={handleAnalyze}
                      onReview={handleReview} actionLoading={actionLoading} />
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
