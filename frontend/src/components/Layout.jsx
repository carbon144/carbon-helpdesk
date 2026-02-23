import React, { useState, useEffect } from 'react'
import Sidebar from './Sidebar'
import TicketsPage from '../pages/TicketsPage'
import TicketDetailPage from '../pages/TicketDetailPage'
import DashboardPage from '../pages/DashboardPage'
import KBPage from '../pages/KBPage'
import IntegrationsPage from '../pages/IntegrationsPage'
import ReportsPage from '../pages/ReportsPage'
import SettingsPage from '../pages/SettingsPage'
import TrackingPage from '../pages/TrackingPage'
import AssistantPage from '../pages/AssistantPage'
import MediaPage from '../pages/MediaPage'
import CatalogPage from '../pages/CatalogPage'
import LeaderboardPage from '../pages/LeaderboardPage'
import { getTicketCounts } from '../services/api'

const AUTO_REFRESH_MS = 30_000

export default function Layout({ user, onLogout }) {
  const [page, setPage] = useState('dashboard')
  const [selectedTicketId, setSelectedTicketId] = useState(null)
  const [ticketFilters, setTicketFilters] = useState({})
  const [ticketCount, setTicketCount] = useState(0)

  useEffect(() => {
    loadTicketCounts()
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      // Only refresh when tab is visible
      if (document.visibilityState === 'visible') {
        loadTicketCounts()
      }
    }, AUTO_REFRESH_MS)
    return () => clearInterval(interval)
  }, [])

  const loadTicketCounts = async () => {
    try {
      const { data } = await getTicketCounts()
      setTicketCount(data.mine)
    } catch (e) {
      console.error('Failed to load ticket counts', e)
    }
  }

  const handleOpenTicket = (ticketId) => {
    setSelectedTicketId(ticketId)
    setPage('ticket-detail')
  }

  const handleBack = () => {
    setSelectedTicketId(null)
    setPage('tickets')
  }

  const renderPage = () => {
    switch (page) {
      case 'dashboard':
        return <DashboardPage user={user} onNavigate={(p, filters) => { setTicketFilters(filters || {}); setPage(p); setSelectedTicketId(null); }} />
      case 'tickets':
        return (
          <TicketsPage
            filters={ticketFilters}
            onOpenTicket={handleOpenTicket}
            user={user}
          />
        )
      case 'ticket-detail':
        return (
          <TicketDetailPage
            ticketId={selectedTicketId}
            onBack={handleBack}
            onOpenTicket={handleOpenTicket}
            user={user}
          />
        )
      case 'kb':
        return <KBPage />
      case 'reports':
        return <ReportsPage />
      case 'integrations':
        return <IntegrationsPage />
      case 'assistant':
        return <AssistantPage user={user} />
      case 'media':
        return <MediaPage />
      case 'catalog':
        return <CatalogPage />
      case 'leaderboard':
        return <LeaderboardPage user={user} />
      case 'tracking':
        return <TrackingPage onOpenTicket={handleOpenTicket} />
      case 'settings':
        return <SettingsPage user={user} />
      default:
        return <DashboardPage />
    }
  }

  return (
    <div className="flex h-screen" style={{ background: 'var(--bg-primary)' }}>
      <Sidebar
        user={user}
        onLogout={onLogout}
        page={page}
        setPage={(p) => { setPage(p); setSelectedTicketId(null); setTicketFilters({}) }}
        ticketCount={ticketCount}
      />
      <main className="flex-1 overflow-auto" style={{ background: 'var(--bg-primary)' }}>
        {renderPage()}
      </main>
    </div>
  )
}
