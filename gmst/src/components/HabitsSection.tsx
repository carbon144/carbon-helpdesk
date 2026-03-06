'use client'

import { useState, useEffect } from 'react'
import { Habit } from '@/types'
import { getHabits, saveHabits } from '@/lib/storage'

function today() {
  return new Date().toISOString().split('T')[0]
}

function getStreak(habit: Habit): number {
  let streak = 0
  const d = new Date()
  for (let i = 0; i < 365; i++) {
    const dateStr = d.toISOString().split('T')[0]
    if (habit.completedDates.includes(dateStr)) {
      streak++
    } else if (i > 0) {
      break
    }
    d.setDate(d.getDate() - 1)
  }
  return streak
}

export function HabitsSection() {
  const [habits, setHabits] = useState<Habit[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [name, setName] = useState('')
  const [icon, setIcon] = useState('🎯')

  useEffect(() => { setHabits(getHabits()) }, [])

  function save(updated: Habit[]) {
    setHabits(updated)
    saveHabits(updated)
  }

  function addHabit() {
    if (!name.trim()) return
    const habit: Habit = {
      id: crypto.randomUUID(),
      name: name.trim(),
      icon,
      frequency: 'daily',
      completedDates: [],
      createdAt: new Date().toISOString(),
    }
    save([...habits, habit])
    setName('')
    setIcon('🎯')
    setShowAdd(false)
  }

  function toggleToday(id: string) {
    const todayStr = today()
    save(habits.map(h => {
      if (h.id !== id) return h
      const has = h.completedDates.includes(todayStr)
      return {
        ...h,
        completedDates: has
          ? h.completedDates.filter(d => d !== todayStr)
          : [...h.completedDates, todayStr],
      }
    }))
  }

  function deleteHabit(id: string) {
    save(habits.filter(h => h.id !== id))
  }

  const todayStr = today()

  return (
    <div>
      <div className="section-header">
        <h1 className="section-title">Hábitos</h1>
        <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Novo Hábito</button>
      </div>

      {habits.length === 0 ? (
        <div className="empty-state">Nenhum hábito criado. Comece a construir rotinas!</div>
      ) : (
        <div className="habit-grid">
          {habits.map(habit => {
            const doneToday = habit.completedDates.includes(todayStr)
            const streak = getStreak(habit)
            return (
              <div key={habit.id} className="habit-card">
                <div className="habit-header">
                  <span className="habit-name">{habit.icon} {habit.name}</span>
                  <button className="btn btn-danger btn-sm" onClick={() => deleteHabit(habit.id)}>×</button>
                </div>
                {streak > 0 && <span className="habit-streak">{streak} dia{streak > 1 ? 's' : ''} seguido{streak > 1 ? 's' : ''}</span>}
                <button
                  className={`habit-toggle ${doneToday ? 'done' : 'pending'}`}
                  onClick={() => toggleToday(habit.id)}
                >
                  {doneToday ? '✓ Feito hoje' : 'Marcar como feito'}
                </button>
              </div>
            )
          })}
        </div>
      )}

      {showAdd && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowAdd(false)}>
          <div className="modal">
            <h2 className="modal-title">Novo Hábito</h2>
            <div className="input-group">
              <label className="label">Nome</label>
              <input
                className="input"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Ex: Exercício, Leitura, Meditação..."
                autoFocus
                onKeyDown={e => e.key === 'Enter' && addHabit()}
              />
            </div>
            <div className="input-group">
              <label className="label">Ícone</label>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {['🎯', '💪', '📚', '🧘', '💧', '🏃', '✍️', '🎵', '💤', '🥗'].map(e => (
                  <button
                    key={e}
                    className={`btn btn-sm ${icon === e ? 'btn-primary' : 'btn-ghost'}`}
                    onClick={() => setIcon(e)}
                    style={{ fontSize: '1.2rem', padding: '6px 10px' }}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setShowAdd(false)}>Cancelar</button>
              <button className="btn btn-primary" onClick={addHabit}>Criar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
