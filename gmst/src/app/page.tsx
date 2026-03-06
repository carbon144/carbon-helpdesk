'use client'

import { useState } from 'react'
import { TasksSection } from '@/components/TasksSection'
import { HabitsSection } from '@/components/HabitsSection'
import { GoalsSection } from '@/components/GoalsSection'
import { Dashboard } from '@/components/Dashboard'

type Tab = 'dashboard' | 'tasks' | 'habits' | 'goals'

export default function Home() {
  const [tab, setTab] = useState<Tab>('dashboard')

  return (
    <>
      <header className="header">
        <div className="container header-inner">
          <div className="logo">GMST</div>
          <nav className="nav">
            {(['dashboard', 'tasks', 'habits', 'goals'] as Tab[]).map((t) => (
              <button
                key={t}
                className={`nav-link ${tab === t ? 'active' : ''}`}
                onClick={() => setTab(t)}
              >
                {t === 'dashboard' ? 'Dashboard' : t === 'tasks' ? 'Tarefas' : t === 'habits' ? 'Hábitos' : 'Metas'}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="container" style={{ padding: '24px 20px' }}>
        {tab === 'dashboard' && <Dashboard onNavigate={setTab} />}
        {tab === 'tasks' && <TasksSection />}
        {tab === 'habits' && <HabitsSection />}
        {tab === 'goals' && <GoalsSection />}
      </main>
    </>
  )
}
