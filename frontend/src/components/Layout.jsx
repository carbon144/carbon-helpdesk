import React, { useState, useEffect, Suspense, lazy } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import CommandPalette from './CommandPalette'
import KeyboardShortcutsModal from './KeyboardShortcutsModal'
import TicketsPage from '../pages/TicketsPage'
import TicketDetailPage from '../pages/TicketDetailPage'
import api, { getTicketCounts } from '../services/api'
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
const AgentAnalysisPage = lazy(() => import('../pages/AgentAnalysisPage'))
const ChatPage = lazy(() => import('../pages/ChatPage'))
const ChatbotFlowsPage = lazy(() => import('../pages/ChatbotFlowsPage'))
const VoiceCallsPage = lazy(() => import('../pages/VoiceCallsPage'))

const AUTO_REFRESH_MS = 30_000

export default function Layout({ user, onLogout }) {
  const navigate = useNavigate()
  const [ticketCount, setTicketCount] = useState(0)
  const [metaCount, setMetaCount] = useState(0)
  const [chatCount, setChatCount] = useState(0)

  useEffect(() => { loadTicketCounts() }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') loadTicketCounts()
    }, AUTO_REFRESH_MS)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    let gPending = false
    let gTimer = null

    const handleKeyDown = (e) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
      if (e.metaKey || e.ctrlKey || e.altKey) return

      if (gPending) {
        gPending = false
        clearTimeout(gTimer)
        if (e.key === 'd') { e.preventDefault(); navigate('/dashboard') }
        else if (e.key === 't') { e.preventDefault(); navigate('/tickets') }
        else if (e.key === 'k') { e.preventDefault(); navigate('/kb') }
        return
      }

      if (e.key === 'g') {
        gPending = true
        gTimer = setTimeout(() => { gPending = false }, 500)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      if (gTimer) clearTimeout(gTimer)
    }
  }, [navigate])

  const loadTicketCounts = async () => {
    try {
      const { data } = await getTicketCounts()
      setTicketCount(data.mine)
      setMetaCount(data.meta_channels || 0)
    } catch (e) {
      console.error('Failed to load ticket counts', e)
    }
    try {
      const chatRes = await api.get('/chat/conversations/counts')
      setChatCount(chatRes.data?.open || 0)
    } catch (e) {
      console.error('Failed to load chat counts', e)
    }
  }

  return (
    <div className="flex h-screen" style={{ background: 'var(--bg-primary)' }}>
      <CommandPalette />
      <KeyboardShortcutsModal />
      <Sidebar user={user} onLogout={onLogout} ticketCount={ticketCount} metaCount={metaCount} chatCount={chatCount} />
      <main className="flex-1 overflow-auto" style={{ background: 'var(--bg-primary)' }}>
        <Suspense fallback={<SkeletonDashboard />}>
          <Routes>
            <Route path="/dashboard" element={<DashboardPage user={user} />} />
            <Route path="/tickets" element={<TicketsPage user={user} />} />
            <Route path="/chat" element={<ChatPage user={user} />} />
            <Route path="/chatbot-flows" element={<ChatbotFlowsPage />} />
            <Route path="/voice-calls" element={<VoiceCallsPage />} />
            <Route path="/tickets/:id" element={<TicketDetailPage user={user} />} />
            <Route path="/kb" element={<KBPage />} />
            <Route path="/assistant" element={<AssistantPage user={user} />} />
            <Route path="/media" element={<MediaPage />} />
            <Route path="/catalog" element={<CatalogPage />} />
            <Route path="/leaderboard" element={<LeaderboardPage user={user} />} />
            <Route path="/tracking" element={<TrackingPage />} />
            <Route path="/canais-ia" element={<CanaisIAPage user={user} />} />
            {/* <Route path="/moderation" element={<ModerationPage />} /> */}
            <Route path="/agent-analysis" element={<AgentAnalysisPage user={user} />} />
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
