'use client'

import { useState, useEffect } from 'react'
import { Goal, Milestone } from '@/types'
import { getGoals, saveGoals } from '@/lib/storage'

export function GoalsSection() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')

  useEffect(() => { setGoals(getGoals()) }, [])

  function save(updated: Goal[]) {
    setGoals(updated)
    saveGoals(updated)
  }

  function addGoal() {
    if (!title.trim()) return
    const goal: Goal = {
      id: crypto.randomUUID(),
      title: title.trim(),
      description: description.trim() || undefined,
      progress: 0,
      milestones: [],
      createdAt: new Date().toISOString(),
    }
    save([...goals, goal])
    setTitle('')
    setDescription('')
    setShowAdd(false)
  }

  function toggleMilestone(goalId: string, milestoneId: string) {
    save(goals.map(g => {
      if (g.id !== goalId) return g
      const milestones = g.milestones.map(m =>
        m.id === milestoneId ? { ...m, completed: !m.completed } : m
      )
      const done = milestones.filter(m => m.completed).length
      const progress = milestones.length > 0 ? Math.round((done / milestones.length) * 100) : g.progress
      return { ...g, milestones, progress }
    }))
  }

  function addMilestone(goalId: string) {
    const text = prompt('Nome do marco:')
    if (!text?.trim()) return
    const milestone: Milestone = { id: crypto.randomUUID(), title: text.trim(), completed: false }
    save(goals.map(g => g.id === goalId ? { ...g, milestones: [...g.milestones, milestone] } : g))
  }

  function deleteGoal(id: string) {
    save(goals.filter(g => g.id !== id))
  }

  return (
    <div>
      <div className="section-header">
        <h1 className="section-title">Metas</h1>
        <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Nova Meta</button>
      </div>

      {goals.length === 0 ? (
        <div className="empty-state">Nenhuma meta definida. Defina o que quer alcançar!</div>
      ) : (
        <div className="goal-list">
          {goals.map(goal => (
            <div key={goal.id} className="goal-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div className="goal-title">{goal.title}</div>
                  {goal.description && (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 8 }}>
                      {goal.description}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 4 }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => addMilestone(goal.id)}>+ Marco</button>
                  <button className="btn btn-danger btn-sm" onClick={() => deleteGoal(goal.id)}>×</button>
                </div>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${goal.progress}%` }} />
              </div>
              <div className="progress-label">{goal.progress}% concluído</div>
              {goal.milestones.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  {goal.milestones.map(m => (
                    <div key={m.id} className="milestone-item">
                      <button
                        className={`milestone-check ${m.completed ? 'checked' : ''}`}
                        onClick={() => toggleMilestone(goal.id, m.id)}
                      >
                        {m.completed ? '✓' : ''}
                      </button>
                      <span style={{ textDecoration: m.completed ? 'line-through' : 'none', color: m.completed ? 'var(--text-muted)' : 'var(--text)' }}>
                        {m.title}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowAdd(false)}>
          <div className="modal">
            <h2 className="modal-title">Nova Meta</h2>
            <div className="input-group">
              <label className="label">Título</label>
              <input
                className="input"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Ex: Aprender inglês, Emagrecer 10kg..."
                autoFocus
                onKeyDown={e => e.key === 'Enter' && addGoal()}
              />
            </div>
            <div className="input-group">
              <label className="label">Descrição (opcional)</label>
              <textarea
                className="input"
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Detalhes sobre a meta..."
                rows={3}
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setShowAdd(false)}>Cancelar</button>
              <button className="btn btn-primary" onClick={addGoal}>Criar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
