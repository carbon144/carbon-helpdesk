import React, { useState } from 'react'
import { Film, PlusCircle, BarChart3, Lightbulb, List } from 'lucide-react'
import GeneratorPage from './pages/GeneratorPage'
import HistoryPage from './pages/HistoryPage'
import PerformancePage from './pages/PerformancePage'
import InsightsPage from './pages/InsightsPage'

const NAV_ITEMS = [
  { id: 'generate', label: 'Gerar Roteiro', icon: PlusCircle },
  { id: 'history', label: 'Historico', icon: List },
  { id: 'performance', label: 'Performance', icon: BarChart3 },
  { id: 'insights', label: 'Insights', icon: Lightbulb },
]

export default function App() {
  const [activePage, setActivePage] = useState('generate')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-carbon-500 flex items-center justify-center">
                <Film className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">Carbon Scripts</h1>
                <p className="text-xs text-gray-500 -mt-0.5">Gerador de Roteiros</p>
              </div>
            </div>

            <nav className="flex items-center gap-1">
              {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActivePage(id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activePage === id
                      ? 'bg-carbon-50 text-carbon-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activePage === 'generate' && <GeneratorPage onViewScript={(id) => setActivePage('history')} />}
        {activePage === 'history' && <HistoryPage />}
        {activePage === 'performance' && <PerformancePage />}
        {activePage === 'insights' && <InsightsPage />}
      </main>
    </div>
  )
}
