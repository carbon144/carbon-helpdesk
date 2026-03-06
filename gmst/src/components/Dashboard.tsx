'use client'

import { useState, useEffect } from 'react'
import { Task, Habit, Goal } from '@/types'
import { getTasks, getHabits, getGoals } from '@/lib/storage'

interface DashboardProps {
  onNavigate: (tab: 'tasks' | 'habits' | 'goals') => void
}

function today() {
  return new Date().toISOString().split('T')[0]
}

export function Dashboard({ onNavigate }: DashboardProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [habits, setHabits] = useState<Habit[]>([])
  const [goals, setGoals] = useState<Goal[]>([])

  useEffect(() => {
    setTasks(getTasks())
    setHabits(getHabits())
    setGoals(getGoals())
  }, [])

  const todayStr = today()
  const pendingTasks = tasks.filter(t => !t.completed).length
  const completedTasks = tasks.filter(t => t.completed).length
  const urgentTasks = tasks.filter(t => !t.completed && (t.priority === 'urgent' || t.priority === 'high')).length
  const habitsToday = habits.filter(h => h.completedDates.includes(todayStr)).length
  const avgGoalProgress = goals.length > 0 ? Math.round(goals.reduce((s, g) => s + g.progress, 0) / goals.length) : 0

  return (
    <div>
      <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: 8, letterSpacing: '-0.5px' }}>
        Get My Shit Together
      </h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>
        {new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
      </p>

      <div className="stats-grid">
        <div className="stat-card" onClick={() => onNavigate('tasks')} style={{ cursor: 'pointer' }}>
          <div className="stat-value">{pendingTasks}</div>
          <div className="stat-label">Tarefas pendentes</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: urgentTasks > 0 ? 'var(--danger)' : 'var(--success)' }}>
            {urgentTasks}
          </div>
          <div className="stat-label">Urgentes / Alta prioridade</div>
        </div>
        <div className="stat-card" onClick={() => onNavigate('habits')} style={{ cursor: 'pointer' }}>
          <div className="stat-value">{habitsToday}/{habits.length}</div>
          <div className="stat-label">Hábitos feitos hoje</div>
        </div>
        <div className="stat-card" onClick={() => onNavigate('goals')} style={{ cursor: 'pointer' }}>
          <div className="stat-value">{avgGoalProgress}%</div>
          <div className="stat-label">Progresso médio das metas</div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Tarefas urgentes</h2>
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate('tasks')}>Ver todas →</button>
          </div>
          {tasks.filter(t => !t.completed && (t.priority === 'urgent' || t.priority === 'high')).length === 0 ? (
            <div className="empty-state" style={{ padding: 20 }}>Nenhuma tarefa urgente</div>
          ) : (
            <div className="task-list">
              {tasks
                .filter(t => !t.completed && (t.priority === 'urgent' || t.priority === 'high'))
                .slice(0, 5)
                .map(task => (
                  <div key={task.id} className="task-item">
                    <span className={`priority-dot priority-${task.priority}`} />
                    <span className="task-title">{task.title}</span>
                  </div>
                ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Metas em andamento</h2>
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate('goals')}>Ver todas →</button>
          </div>
          {goals.length === 0 ? (
            <div className="empty-state" style={{ padding: 20 }}>Nenhuma meta definida</div>
          ) : (
            <div className="goal-list">
              {goals.slice(0, 3).map(goal => (
                <div key={goal.id} style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: '0.9rem', fontWeight: 500, marginBottom: 4 }}>{goal.title}</div>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${goal.progress}%` }} />
                  </div>
                  <div className="progress-label">{goal.progress}%</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {completedTasks > 0 && (
        <div style={{ textAlign: 'center', marginTop: 32, color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          {completedTasks} tarefa{completedTasks > 1 ? 's' : ''} concluída{completedTasks > 1 ? 's' : ''} no total
        </div>
      )}
    </div>
  )
}
