import React, { useState, useEffect } from 'react'
import {
  getLeaderboard, getMyStats, getRewards, createReward, updateReward, deleteReward,
  claimReward, getRewardClaims, approveRewardClaim, rejectRewardClaim,
} from '../services/api'

const RANK_ICONS = ['fa-trophy text-yellow-400', 'fa-medal text-gray-300', 'fa-medal text-amber-600']
const RANK_BG = ['bg-yellow-500/10 border-yellow-500/30', 'bg-gray-500/10 border-gray-500/30', 'bg-amber-500/10 border-amber-500/30']

const REWARD_ICONS = [
  { id: 'fa-gift', label: 'Presente' }, { id: 'fa-star', label: 'Estrela' },
  { id: 'fa-coffee', label: 'Café' }, { id: 'fa-pizza-slice', label: 'Pizza' },
  { id: 'fa-money-bill', label: 'Dinheiro' }, { id: 'fa-plane', label: 'Viagem' },
  { id: 'fa-clock', label: 'Folga' }, { id: 'fa-headphones', label: 'Headphone' },
  { id: 'fa-tshirt', label: 'Camiseta' }, { id: 'fa-gem', label: 'Joia' },
]

export default function LeaderboardPage({ user }) {
  const [tab, setTab] = useState('performance')
  const [leaderboard, setLeaderboard] = useState([])
  const [myStats, setMyStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(7)
  // Rewards
  const [rewards, setRewards] = useState([])
  const [claims, setClaims] = useState([])
  const [showAddReward, setShowAddReward] = useState(false)
  const [newReward, setNewReward] = useState({ name: '', description: '', icon: 'fa-gift', color: '#a855f7', points_required: 100, category: 'geral' })
  const [saving, setSaving] = useState(false)
  const [claimsFilter, setClaimsFilter] = useState('')

  const isAdmin = user?.role === 'admin' || user?.role === 'supervisor'

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getLeaderboard(days).then(r => setLeaderboard(r.data || [])),
      getMyStats().then(r => setMyStats(r.data)),
      getRewards().then(r => setRewards(r.data || [])),
      getRewardClaims().then(r => setClaims(r.data || [])),
    ]).catch(() => {}).finally(() => setLoading(false))
  }, [days])

  const myScore = leaderboard.find(a => a.agent_id === user?.id)?.score || 0

  const handleCreateReward = async () => {
    if (!newReward.name) return
    setSaving(true)
    try {
      await createReward(newReward)
      const r = await getRewards(); setRewards(r.data || [])
      setNewReward({ name: '', description: '', icon: 'fa-gift', color: '#a855f7', points_required: 100, category: 'geral' })
      setShowAddReward(false)
    } catch (e) { alert(e.response?.data?.detail || 'Erro') }
    finally { setSaving(false) }
  }

  const handleClaim = async (rewardId) => {
    try {
      const r = await claimReward(rewardId)
      alert(r.data?.message || 'Solicitado!')
      const cl = await getRewardClaims(); setClaims(cl.data || [])
    } catch (e) { alert(e.response?.data?.detail || 'Erro') }
  }

  const handleApprove = async (claimId) => {
    try {
      await approveRewardClaim(claimId)
      const cl = await getRewardClaims(); setClaims(cl.data || [])
    } catch (e) { alert(e.response?.data?.detail || 'Erro') }
  }

  const handleReject = async (claimId) => {
    try {
      await rejectRewardClaim(claimId)
      const cl = await getRewardClaims(); setClaims(cl.data || [])
    } catch (e) { alert(e.response?.data?.detail || 'Erro') }
  }

  const handleDeleteReward = async (rewardId) => {
    if (!confirm('Remover esta premiação?')) return
    try {
      await deleteReward(rewardId)
      const r = await getRewards(); setRewards(r.data || [])
    } catch (e) { alert(e.response?.data?.detail || 'Erro') }
  }

  if (loading) return <div className="p-6 text-center"><i className="fas fa-spinner animate-spin text-purple-400 text-2xl" /></div>

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}><i className="fas fa-gamepad mr-3 text-purple-400" />Performance & Metas</h1>
          <p style={{ color: 'var(--text-tertiary)' }} className="text-sm mt-1">Acompanhe seu desempenho, compare com a equipe e resgate premiações</p>
        </div>
        <div className="flex gap-2">
          {/* Tabs */}
          <div className="flex rounded-lg p-0.5" style={{ background: 'var(--bg-tertiary)' }}>
            {[{ id: 'performance', label: 'Performance', icon: 'fa-chart-line' },
              { id: 'rewards', label: 'Premiações', icon: 'fa-gift' },
              ...(isAdmin ? [{ id: 'claims', label: 'Resgates', icon: 'fa-hand-holding' }] : []),
            ].map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${tab === t.id ? 'bg-purple-600/20 text-purple-400' : ''}`}
                style={tab !== t.id ? { color: 'var(--text-tertiary)' } : {}}>
                <i className={`fas ${t.icon} mr-1.5`} />{t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ═══ PERFORMANCE TAB ═══ */}
      {tab === 'performance' && (
        <>
          <div className="flex justify-end mb-4">
            <div className="flex rounded-lg p-0.5" style={{ background: 'var(--bg-tertiary)' }}>
              {[7, 14, 30].map(d => (
                <button key={d} onClick={() => setDays(d)}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition ${days === d ? 'bg-purple-600/20 text-purple-400' : ''}`}
                  style={days !== d ? { color: 'var(--text-tertiary)' } : {}}>
                  {d}d
                </button>
              ))}
            </div>
          </div>

          {/* My Stats Cards */}
          {myStats && (
            <div className="mb-8">
              <div className="bg-gradient-to-r from-purple-600/20 to-indigo-600/20 rounded-xl p-4 mb-4 border border-purple-500/20">
                <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{myStats.streak_message}</p>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <StatCard icon="fa-check-circle" color="emerald" label="Hoje" value={myStats.today_resolved} sub={`Meta: ${myStats.daily_goal}`} />
                <StatCard icon="fa-calendar-week" color="blue" label="Semana" value={myStats.week_resolved} sub={`Meta: ${myStats.weekly_goal}`} />
                <StatCard icon="fa-inbox" color="amber" label="Na fila" value={myStats.pending} sub={myStats.pending === 0 ? 'Fila zerada!' : 'Aguardando'} />
                <StatCard icon="fa-exclamation-triangle" color="red" label="SLA urgente" value={myStats.sla_urgent + myStats.sla_breached}
                  sub={myStats.sla_breached > 0 ? `${myStats.sla_breached} estourado(s)` : 'Dentro do prazo'} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <ProgressBar label="Meta diária" current={myStats.today_resolved} goal={myStats.daily_goal} color="emerald" />
                <ProgressBar label="Meta semanal" current={myStats.week_resolved} goal={myStats.weekly_goal} color="blue" />
              </div>
            </div>
          )}

          {/* Leaderboard */}
          <div className="rounded-xl border overflow-hidden" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
            <div className="px-5 py-3 border-b" style={{ borderColor: 'var(--border-color)' }}>
              <h2 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}><i className="fas fa-trophy mr-2 text-yellow-400" />Ranking da Equipe</h2>
            </div>
            <div className="divide-y" style={{ borderColor: 'var(--border-color)' }}>
              {leaderboard.map((agent, i) => {
                const isMe = agent.agent_id === user?.id
                return (
                  <div key={agent.agent_id}
                    className={`flex items-center gap-4 px-5 py-3 transition ${isMe ? 'bg-purple-500/10' : ''}`}
                    style={!isMe ? {} : {}}>
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold ${
                      i < 3 ? RANK_BG[i] + ' border' : 'border'
                    }`} style={i >= 3 ? { background: 'var(--bg-tertiary)', borderColor: 'var(--border-color)' } : {}}>
                      {i < 3 ? <i className={`fas ${RANK_ICONS[i]}`} /> : <span style={{ color: 'var(--text-tertiary)' }}>{agent.rank}</span>}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`font-medium text-sm ${isMe ? 'text-purple-400' : ''}`} style={!isMe ? { color: 'var(--text-primary)' } : {}}>{agent.agent_name}</span>
                        {isMe && <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded text-[10px] font-bold">VOCÊ</span>}
                      </div>
                      <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{agent.role === 'admin' ? 'Admin' : agent.role === 'supervisor' ? 'Supervisor' : 'Agente'}</span>
                    </div>
                    <div className="flex items-center gap-6 text-xs">
                      <div className="text-center"><p className="text-emerald-400 font-bold text-lg">{agent.resolved}</p><p style={{ color: 'var(--text-tertiary)' }}>resolvidos</p></div>
                      <div className="text-center"><p className="text-amber-400 font-bold text-lg">{agent.pending}</p><p style={{ color: 'var(--text-tertiary)' }}>na fila</p></div>
                      <div className="text-center">
                        <p className={`font-bold text-lg ${agent.sla_rate >= 90 ? 'text-emerald-400' : agent.sla_rate >= 70 ? 'text-yellow-400' : 'text-red-400'}`}>{agent.sla_rate}%</p>
                        <p style={{ color: 'var(--text-tertiary)' }}>SLA</p>
                      </div>
                      <div className="text-center"><p className="text-purple-400 font-bold text-lg">{agent.score}</p><p style={{ color: 'var(--text-tertiary)' }}>score</p></div>
                    </div>
                  </div>
                )
              })}
              {leaderboard.length === 0 && (
                <div className="text-center py-8 text-sm" style={{ color: 'var(--text-tertiary)' }}>Nenhum dado disponível</div>
              )}
            </div>
          </div>
        </>
      )}

      {/* ═══ REWARDS TAB ═══ */}
      {tab === 'rewards' && (
        <>
          {/* My score */}
          <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-xl p-4 mb-6 border border-purple-500/20 flex items-center justify-between">
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Seus pontos (últimos 30 dias)</p>
              <p className="text-3xl font-bold text-purple-400">{myScore} pts</p>
            </div>
            {isAdmin && (
              <button onClick={() => setShowAddReward(!showAddReward)}
                className="bg-purple-600/20 text-purple-400 hover:bg-purple-600/40 px-4 py-2 rounded-xl text-sm transition">
                <i className={`fas ${showAddReward ? 'fa-times' : 'fa-plus'} mr-2`} />{showAddReward ? 'Cancelar' : 'Nova Premiação'}
              </button>
            )}
          </div>

          {/* Add reward form (admin) */}
          {showAddReward && isAdmin && (
            <div className="rounded-xl p-5 mb-6 border space-y-3" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
              <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}><i className="fas fa-plus-circle mr-2 text-purple-400" />Nova Premiação</p>
              <div className="grid grid-cols-2 gap-3">
                <input value={newReward.name} onChange={e => setNewReward({ ...newReward, name: e.target.value })}
                  placeholder="Nome da premiação" className="col-span-2 rounded-lg px-3 py-2 text-sm border focus:outline-none focus:border-purple-500"
                  style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }} />
                <input value={newReward.description} onChange={e => setNewReward({ ...newReward, description: e.target.value })}
                  placeholder="Descrição" className="col-span-2 rounded-lg px-3 py-2 text-sm border focus:outline-none focus:border-purple-500"
                  style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }} />
                <div>
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-tertiary)' }}>Pontos necessários</label>
                  <input type="number" value={newReward.points_required} onChange={e => setNewReward({ ...newReward, points_required: parseInt(e.target.value) || 0 })}
                    className="w-full rounded-lg px-3 py-2 text-sm border focus:outline-none focus:border-purple-500"
                    style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }} />
                </div>
                <div>
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-tertiary)' }}>Categoria</label>
                  <select value={newReward.category} onChange={e => setNewReward({ ...newReward, category: e.target.value })}
                    className="w-full rounded-lg px-3 py-2 text-sm border"
                    style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}>
                    <option value="geral">Geral</option><option value="semanal">Semanal</option><option value="mensal">Mensal</option>
                  </select>
                </div>
              </div>
              {/* Icon picker */}
              <div>
                <label className="text-xs mb-1.5 block" style={{ color: 'var(--text-tertiary)' }}>Ícone</label>
                <div className="flex flex-wrap gap-2">
                  {REWARD_ICONS.map(ic => (
                    <button key={ic.id} onClick={() => setNewReward({ ...newReward, icon: ic.id })}
                      className={`w-9 h-9 rounded-lg flex items-center justify-center transition border ${newReward.icon === ic.id ? 'border-purple-500 bg-purple-500/20' : ''}`}
                      style={newReward.icon !== ic.id ? { borderColor: 'var(--border-color)', background: 'var(--bg-tertiary)' } : {}}
                      title={ic.label}>
                      <i className={`fas ${ic.id} text-sm`} style={{ color: newReward.icon === ic.id ? '#a855f7' : 'var(--text-tertiary)' }} />
                    </button>
                  ))}
                </div>
              </div>
              {/* Color picker */}
              <div>
                <label className="text-xs mb-1.5 block" style={{ color: 'var(--text-tertiary)' }}>Cor</label>
                <div className="flex gap-2">
                  {['#a855f7', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#06b6d4', '#8b5cf6'].map(c => (
                    <button key={c} onClick={() => setNewReward({ ...newReward, color: c })}
                      className={`w-7 h-7 rounded-full transition ${newReward.color === c ? 'ring-2 ring-white ring-offset-2 ring-offset-[var(--bg-secondary)]' : ''}`}
                      style={{ background: c }} />
                  ))}
                </div>
              </div>
              <button onClick={handleCreateReward} disabled={saving || !newReward.name}
                className="w-full bg-purple-600/20 text-purple-400 hover:bg-purple-600/40 py-2.5 rounded-xl text-sm transition disabled:opacity-50">
                {saving ? <i className="fas fa-spinner animate-spin" /> : <><i className="fas fa-check mr-2" />Criar Premiação</>}
              </button>
            </div>
          )}

          {/* Rewards grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {rewards.map(r => {
              const canClaim = myScore >= r.points_required && r.is_active
              return (
                <div key={r.id} className="rounded-xl border overflow-hidden transition hover:shadow-lg"
                  style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
                  <div className="h-20 flex items-center justify-center" style={{ background: `${r.color}15` }}>
                    <i className={`fas ${r.icon} text-3xl`} style={{ color: r.color }} />
                  </div>
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{r.name}</p>
                      {isAdmin && (
                        <button onClick={() => handleDeleteReward(r.id)} className="text-xs hover:text-red-400 transition" style={{ color: 'var(--text-tertiary)' }}>
                          <i className="fas fa-trash" />
                        </button>
                      )}
                    </div>
                    {r.description && <p className="text-xs mb-3" style={{ color: 'var(--text-tertiary)' }}>{r.description}</p>}
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold" style={{ color: r.color }}>{r.points_required} pts</span>
                      <button onClick={() => handleClaim(r.id)} disabled={!canClaim}
                        className="px-3 py-1 rounded-lg text-xs font-medium transition disabled:opacity-30"
                        style={{ background: `${r.color}20`, color: r.color }}>
                        {canClaim ? <><i className="fas fa-hand-holding mr-1" />Resgatar</> : <><i className="fas fa-lock mr-1" />{r.points_required - myScore} pts faltam</>}
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
            {rewards.length === 0 && (
              <div className="col-span-3 text-center py-12" style={{ color: 'var(--text-tertiary)' }}>
                <i className="fas fa-gift text-4xl mb-3 block opacity-30" />
                <p className="text-sm">Nenhuma premiação configurada ainda</p>
                {isAdmin && <p className="text-xs mt-1">Clique em "Nova Premiação" para criar</p>}
              </div>
            )}
          </div>

          {/* My claims */}
          {claims.filter(c => c.agent_id === user?.id).length > 0 && (
            <div className="mt-8">
              <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}><i className="fas fa-history mr-2 text-purple-400" />Meus Resgates</h3>
              <div className="space-y-2">
                {claims.filter(c => c.agent_id === user?.id).map(c => (
                  <div key={c.id} className="flex items-center gap-3 rounded-lg p-3 border"
                    style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
                    <i className={`fas ${c.icon}`} style={{ color: c.color }} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{c.reward_name}</p>
                      <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{c.points_spent} pts</p>
                    </div>
                    <ClaimBadge status={c.status} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ═══ CLAIMS TAB (admin) ═══ */}
      {tab === 'claims' && isAdmin && (
        <>
          <div className="flex gap-2 mb-4">
            {['', 'pending', 'approved', 'rejected'].map(f => (
              <button key={f} onClick={() => setClaimsFilter(f)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${claimsFilter === f ? 'bg-purple-600/20 text-purple-400' : ''}`}
                style={claimsFilter !== f ? { color: 'var(--text-tertiary)' } : {}}>
                {f === '' ? 'Todos' : f === 'pending' ? 'Pendentes' : f === 'approved' ? 'Aprovados' : 'Rejeitados'}
              </button>
            ))}
          </div>

          <div className="space-y-2">
            {claims.filter(c => !claimsFilter || c.status === claimsFilter).map(c => (
              <div key={c.id} className="flex items-center gap-4 rounded-xl p-4 border"
                style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${c.color}20` }}>
                  <i className={`fas ${c.icon}`} style={{ color: c.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{c.agent_name}</p>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{c.reward_name} — {c.points_spent} pts</p>
                </div>
                <ClaimBadge status={c.status} />
                {c.status === 'pending' && (
                  <div className="flex gap-1.5">
                    <button onClick={() => handleApprove(c.id)}
                      className="w-8 h-8 rounded-lg bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/30 flex items-center justify-center transition">
                      <i className="fas fa-check text-xs" />
                    </button>
                    <button onClick={() => handleReject(c.id)}
                      className="w-8 h-8 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/30 flex items-center justify-center transition">
                      <i className="fas fa-times text-xs" />
                    </button>
                  </div>
                )}
              </div>
            ))}
            {claims.filter(c => !claimsFilter || c.status === claimsFilter).length === 0 && (
              <div className="text-center py-12" style={{ color: 'var(--text-tertiary)' }}>
                <i className="fas fa-hand-holding text-3xl mb-3 block opacity-30" />
                <p className="text-sm">Nenhum resgate {claimsFilter === 'pending' ? 'pendente' : ''}</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function StatCard({ icon, color, label, value, sub }) {
  return (
    <div className="rounded-xl p-4 border" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
      <div className="flex items-center gap-2 mb-2">
        <i className={`fas ${icon} text-${color}-400 text-sm`} />
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</span>
      </div>
      <p className={`text-${color}-400 text-2xl font-bold`}>{value}</p>
      {sub && <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>{sub}</p>}
    </div>
  )
}

function ProgressBar({ label, current, goal, color }) {
  const pct = goal ? Math.min(Math.round(current / goal * 100), 100) : 0
  return (
    <div className="rounded-xl p-4 border" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</span>
        <span className={`text-${color}-400 text-xs font-bold`}>{current}/{goal}</span>
      </div>
      <div className="rounded-full h-3 overflow-hidden" style={{ background: 'var(--bg-tertiary)' }}>
        <div className={`h-full rounded-full transition-all duration-700 ${pct >= 100 ? 'bg-emerald-500' : `bg-${color}-500`}`}
          style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function ClaimBadge({ status }) {
  const styles = {
    pending: { bg: 'bg-amber-500/15', text: 'text-amber-400', label: 'Pendente' },
    approved: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', label: 'Aprovado' },
    rejected: { bg: 'bg-red-500/15', text: 'text-red-400', label: 'Rejeitado' },
  }
  const s = styles[status] || styles.pending
  return (
    <span className={`${s.bg} ${s.text} px-2 py-0.5 rounded-full text-[10px] font-semibold`}>{s.label}</span>
  )
}
