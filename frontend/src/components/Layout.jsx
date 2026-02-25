import React, { useState, useEffect, Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import TicketsPage from '../pages/TicketsPage'
import TicketDetailPage from '../pages/TicketDetailPage'
import { getTicketCounts } from '../services/api'
import { SkeletonDashboard } from './Skeleton'

const KBPage = lazy(() => import('../pages/KBPage'))
const IntegrationsPage = lazy(() => import('../pages/IntegrationsPage'))
const ReportsPage = lazy(() => import('../pages/ReportsPage'))
const SettingsPage = lazy(() => import('../pages/SettingsPage'))
const TrackingPage = lazy(() => import('../pages/TrackingPage'))
const AssistantPage = lazy(() => import('../pages/AssistantPage'))
const MediaPage = lazy(() => import('../pages/MediaPage'))
const CatalogPage = lazy(() => import('../pages/CatalogPage'))
const LeaderboardPage = lazy(() => import('../pages/LeaderboardPage'))
const ModerationPage = lazy(() => import('../pages/ModerationPage'))
const CanaisIAPage = lazy(() => import('../pages/CanaisIAPage'))
const DashboardPage = lazy(() => import('../pages/DashboardPage'))

const AUTO_REFRESH_MS = 30_000

export default function Layout({ user, onLogout }) {
  const [ticketCount, setTicketCount] = useState(0)
  const [metaCount, setMetaCount] = useState(0)

  useEffect(() => { loadTicketCounts() }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') loadTicketCounts()
    }, AUTO_REFRESH_MS)
    return () => clearInterval(interval)
  }, [])

  const loadTicketCounts = async () => {
    try {
      const { data } = await getTicketCounts()
      setTicketCount(data.mine)
      setMetaCount(data.meta_channels || 0)
    } catch (e) {
      console.error('Failed to load ticket counts', e)
    }
  }

  return (
    <div className="flex h-screen" style={{ background: 'var(--bg-primary)' }}>
      <Sidebar user={user} onLogout={onLogout} ticketCount={ticketCount} metaCount={metaCount} />
      <main className="flex-1 overflow-auto" style={{ background: 'var(--bg-primary)' }}>
        <Suspense fallback={<SkeletonDashboard />}>
          <Routes>
            <Route path="/dashboard" element={<DashboardPage user={user} />} />
            <Route path="/tickets" element={<TicketsPage user={user} />} />
            <Route path="/tickets/:id" element={<TicketDetailPage user={user} />} />
            <Route path="/kb" element={<KBPage />} />
            <Route path="/assistant" element={<AssistantPage user={user} />} />
            <Route path="/media" element={<MediaPage />} />
            <Route path="/catalog" element={<CatalogPage />} />
            <Route path="/leaderboard" element={<LeaderboardPage user={user} />} />
            <Route path="/tracking" element={<TrackingPage />} />
            <Route path="/canais-ia" element={<CanaisIAPage user={user} />} />
            <Route path="/moderation" element={<ModerationPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/integrations" element={<IntegrationsPage />} />
            <Route path="/settings" element={<SettingsPage user={user} />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
