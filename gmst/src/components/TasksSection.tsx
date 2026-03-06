'use client'

import { useState, useEffect } from 'react'
import { Task } from '@/types'
import { getTasks, saveTasks } from '@/lib/storage'

export function TasksSection() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState<Task['priority']>('medium')
  const [category, setCategory] = useState('')
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed'>('all')

  useEffect(() => { setTasks(getTasks()) }, [])

  function save(updated: Task[]) {
    setTasks(updated)
    saveTasks(updated)
  }

  function addTask() {
    if (!title.trim()) return
    const task: Task = {
      id: crypto.randomUUID(),
      title: title.trim(),
      completed: false,
      priority,
      category: category.trim() || 'Geral',
      createdAt: new Date().toISOString(),
    }
    save([task, ...tasks])
    setTitle('')
    setPriority('medium')
    setCategory('')
    setShowAdd(false)
  }

  function toggleTask(id: string) {
    save(tasks.map(t => t.id === id ? { ...t, completed: !t.completed } : t))
  }

  function deleteTask(id: string) {
    save(tasks.filter(t => t.id !== id))
  }

  const filtered = tasks.filter(t => {
    if (filter === 'pending') return !t.completed
    if (filter === 'completed') return t.completed
    return true
  })

  const sorted = [...filtered].sort((a, b) => {
    if (a.completed !== b.completed) return a.completed ? 1 : -1
    const pOrder = { urgent: 0, high: 1, medium: 2, low: 3 }
    return pOrder[a.priority] - pOrder[b.priority]
  })

  return (
    <div>
      <div className="section-header">
        <h1 className="section-title">Tarefas</h1>
        <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Nova Tarefa</button>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {(['all', 'pending', 'completed'] as const).map(f => (
          <button
            key={f}
            className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setFilter(f)}
          >
            {f === 'all' ? 'Todas' : f === 'pending' ? 'Pendentes' : 'Concluídas'}
          </button>
        ))}
      </div>

      {sorted.length === 0 ? (
        <div className="empty-state">Nenhuma tarefa encontrada. Crie uma para começar!</div>
      ) : (
        <div className="task-list">
          {sorted.map(task => (
            <div key={task.id} className="task-item">
              <button
                className={`task-checkbox ${task.completed ? 'checked' : ''}`}
                onClick={() => toggleTask(task.id)}
              >
                {task.completed ? '✓' : ''}
              </button>
              <span className={`priority-dot priority-${task.priority}`} title={task.priority} />
              <span className={`task-title ${task.completed ? 'completed' : ''}`}>{task.title}</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{task.category}</span>
              <button className="btn btn-danger btn-sm" onClick={() => deleteTask(task.id)}>×</button>
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowAdd(false)}>
          <div className="modal">
            <h2 className="modal-title">Nova Tarefa</h2>
            <div className="input-group">
              <label className="label">Título</label>
              <input
                className="input"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="O que precisa fazer?"
                autoFocus
                onKeyDown={e => e.key === 'Enter' && addTask()}
              />
            </div>
            <div className="input-group">
              <label className="label">Prioridade</label>
              <select className="input" value={priority} onChange={e => setPriority(e.target.value as Task['priority'])}>
                <option value="low">Baixa</option>
                <option value="medium">Média</option>
                <option value="high">Alta</option>
                <option value="urgent">Urgente</option>
              </select>
            </div>
            <div className="input-group">
              <label className="label">Categoria</label>
              <input
                className="input"
                value={category}
                onChange={e => setCategory(e.target.value)}
                placeholder="Ex: Trabalho, Pessoal, Saúde..."
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setShowAdd(false)}>Cancelar</button>
              <button className="btn btn-primary" onClick={addTask}>Criar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
