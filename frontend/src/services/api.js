import axios from 'axios'

const LONG_OPERATION_TIMEOUT_MS = 300_000 // 5 minutes

const api = axios.create({
  baseURL: '/api',
})

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('carbon_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 - clear auth state cleanly
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const hadToken = !!localStorage.getItem('carbon_token')
      localStorage.removeItem('carbon_token')
      localStorage.removeItem('carbon_user')
      // Only redirect if we had a token (session expired), not during login
      if (hadToken && !error.config?.url?.includes('/auth/login')) {
        window.location.href = '/'
      }
    }
    return Promise.reject(error)
  }
)

export default api

// ── Auth ──
export const login = (email, password) => api.post('/auth/login', { email, password })
export const getMe = () => api.get('/auth/me')
export const updateMyProfile = (data) => api.patch('/auth/me', data)
export const getUsers = () => api.get('/auth/users')
export const changePassword = (currentPassword, newPassword) => api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword })

// ── Customers ──
export const searchCustomers = (q) => api.get('/customers/search', { params: { q } })
export const getCustomer = (id) => api.get(`/customers/${id}`)
export const getCustomerFullHistory = (id) => api.get(`/customers/${id}/history`)
export const mergeCustomers = (data) => api.post('/customers/merge', data)

// ── Tickets ──
export const getTickets = (params) => api.get('/tickets', { params })
export const getTicketCounts = () => api.get('/tickets/counts')
export const getTicket = (id) => api.get(`/tickets/${id}`)
export const createTicket = (data) => api.post('/tickets', data)
export const updateTicket = (id, data) => api.patch(`/tickets/${id}`, data)
export const bulkAssign = (data) => api.post('/tickets/bulk-assign', data)
export const bulkUpdate = (data) => api.post('/tickets/bulk-update', data)
export const autoAssign = () => api.post('/tickets/auto-assign')
export const getNextTicket = () => api.get('/tickets/next')
export const getCustomerHistory = (customerId) => api.get(`/tickets/customer/${customerId}/history`)
export const getTicketPreview = (ticketId) => api.get(`/tickets/${ticketId}/preview`)
export const getSentMessages = (params) => api.get('/tickets/sent-messages', { params })
export const addMessage = (ticketId, data) => api.post(`/tickets/${ticketId}/messages`, data)

// ── Ticket Merge ──
export const mergeTickets = (data) => api.post('/tickets/merge', data)

// ── Inboxes ──
export const getInboxes = () => api.get('/inboxes')
export const createInbox = (data) => api.post('/inboxes', data)

// ── Dashboard ──
export const getDashboardStats = (days = 30) => api.get('/dashboard/stats', { params: { days } })
export const getAgentDashboardStats = (days = 30) => api.get('/dashboard/agent-stats', { params: { days } })

// ── KB ──
export const getArticles = (params) => api.get('/kb/articles', { params })
export const getArticle = (id) => api.get(`/kb/articles/${id}`)
export const createArticle = (data) => api.post('/kb/articles', data)
export const getMacros = () => api.get('/kb/macros')
export const createMacro = (data) => api.post('/kb/macros', data)
export const updateMacro = (id, data) => api.patch(`/kb/macros/${id}`, data)
export const deleteMacro = (id) => api.delete(`/kb/macros/${id}`)

// ── Slack ──
export const getSlackStatus = () => api.get('/slack/status')
export const sendSlackReply = (data) => api.post('/slack/send-reply', data)

// ── Meta (WhatsApp, Instagram, Facebook) ──
export const getMetaStatus = () => api.get('/meta/status')
export const pauseTicketAI = (ticketId) => api.post(`/meta/tickets/${ticketId}/pause-ai`)
export const resumeTicketAI = (ticketId) => api.post(`/meta/tickets/${ticketId}/resume-ai`)
export const sendMetaReply = (data) => api.post('/meta/send-reply', data)

// ── Moderação de Redes Sociais ──
export const getModerationLog = (params) => api.get('/meta/moderation', { params })
export const getModerationStats = (days = 7) => api.get('/meta/moderation/stats', { params: { days } })
export const reviewComment = (id) => api.post(`/meta/moderation/${id}/review`)
export const replyToComment = (id, reply) => api.post(`/meta/moderation/${id}/reply`, { reply })
export const hideComment = (id, hide = true) => api.post(`/meta/moderation/${id}/hide`, { hide })
export const analyzeComment = (id) => api.post(`/meta/moderation/${id}/reprocess`, { execute_actions: false })
export const reprocessComment = (id) => api.post(`/meta/moderation/${id}/reprocess`, { execute_actions: true })
export const getMetaPosts = (params) => api.get('/meta/posts', { params })
export const syncComments = (data) => api.post('/meta/comments/sync', data)
export const getModerationPostsGrouped = (params) => api.get('/meta/moderation/posts-grouped', { params })
export const getModerationSettings = () => api.get('/meta/moderation/settings')
export const updateModerationSettings = (data) => api.post('/meta/moderation/settings', data)

// ── Gmail ──
export const getGmailStatus = () => api.get('/gmail/status')
export const getGmailAuthUrl = () => api.get('/gmail/auth-url')
export const fetchGmailEmails = () => api.post('/gmail/fetch')
export const fetchGmailHistory = (days = 30) => api.post('/gmail/fetch-history', { days }, { timeout: LONG_OPERATION_TIMEOUT_MS })
export const sendGmailReply = (data) => api.post('/gmail/send-reply', data)
export const composeEmail = (data) => api.post('/gmail/compose', data)
export const fetchSpamEmails = () => api.get('/gmail/spam')
export const rescueFromSpam = (messageId) => api.post(`/gmail/spam/rescue/${messageId}`)
export const rescueAndCreateTicket = (messageId, data) => api.post(`/gmail/spam/rescue-and-create/${messageId}`, data)

// ── AI ──
export const getAIStatus = () => api.get('/ai/status')
export const triageTicket = (ticketId) => api.post(`/ai/triage/${ticketId}`)
export const suggestReply = (ticketId, partialText) => api.post(`/ai/suggest/${ticketId}`, partialText ? { partial_text: partialText } : {})
export const getCopilotInsights = (ticketId, lastMessage) => api.post('/ai/copilot', { ticket_id: ticketId, last_message: lastMessage })

// ── Catalog ──
export const getProducts = (category) => api.get('/catalog/products', { params: category ? { category } : {} })
export const getProduct = (id) => api.get(`/catalog/products/${id}`)

// ── Gamification ──
export const getLeaderboard = (days = 7) => api.get('/gamification/leaderboard', { params: { days } })
export const getMyStats = () => api.get('/gamification/my-stats')
// Rewards
export const getRewards = () => api.get('/rewards/list')
export const createReward = (data) => api.post('/rewards/create', data)
export const updateReward = (id, data) => api.put(`/rewards/${id}`, data)
export const deleteReward = (id) => api.delete(`/rewards/${id}`)
export const claimReward = (id) => api.post(`/rewards/${id}/claim`)
export const getRewardClaims = (status) => api.get('/rewards/claims', { params: status ? { status } : {} })
export const approveRewardClaim = (id) => api.put(`/rewards/claims/${id}/approve`)
export const rejectRewardClaim = (id) => api.put(`/rewards/claims/${id}/reject`)

// ── Reports ──
export const getAgentPerformance = (days = 30) => api.get(`/reports/agents?days=${days}`)
export const getTicketsBySource = (days = 30) => api.get(`/reports/sources?days=${days}`)
export const getSentimentBreakdown = (days = 30) => api.get(`/reports/sentiment?days=${days}`)
export const getTopCustomers = (days = 30) => api.get(`/reports/top-customers?days=${days}`)
export const getCsatReport = (days = 30) => api.get(`/reports/csat?days=${days}`)
export const submitCsat = (ticketId, data) => api.post(`/tickets/${ticketId}/csat`, data)
export const getAgentAnalysis = (agentId, days = 30) => api.get(`/reports/agent-analysis/${agentId}?days=${days}`)
export const getTrends = (days = 30) => api.get(`/reports/trends?days=${days}`)
export const getPatterns = (days = 30) => api.get(`/reports/patterns?days=${days}`)
export const getFullAIAnalysis = (days = 30) => api.get(`/reports/ai-full-analysis?days=${days}`)

// ── Statuses ──
export const getStatuses = () => api.get('/tickets/statuses')

// ── Internal Notes ──
export const updateInternalNotes = (ticketId, data) => api.patch(`/tickets/${ticketId}/internal-notes`, data)

// ── Protocol ──
export const sendProtocolEmail = (ticketId) => api.post(`/tickets/${ticketId}/send-protocol`)
export const backfillProtocols = () => api.post('/tickets/backfill-protocols')

// ── Supplier Notes (RF-026) ──
export const updateSupplierNotes = (ticketId, data) => api.patch(`/tickets/${ticketId}/supplier-notes`, data)

// ── Tracking (RF-021-024) ──
export const updateTracking = (ticketId, data) => api.patch(`/tickets/${ticketId}/tracking`, data)
export const refreshTracking = (ticketId) => api.get(`/tickets/${ticketId}/tracking`)

// ── Blacklist (RF-025) ──
export const blacklistCustomer = (customerId, data) => api.post(`/tickets/customer/${customerId}/blacklist`, data)
export const unblacklistCustomer = (customerId) => api.delete(`/tickets/customer/${customerId}/blacklist`)

// ── AI Summary (RF-019) ──
export const generateSummary = (ticketId) => api.post(`/tickets/${ticketId}/summarize`)

// ── Export (RF-032) ──
export const exportTicketsCsv = (params) => api.get('/export/tickets/csv', { params, responseType: 'blob' })

// ── Shopify ──
export const getShopifyOrders = (email) => api.get('/shopify/orders', { params: { email } })
export const getShopifyOrder = (orderNumber) => api.get(`/shopify/order/${orderNumber}`)

// ── Media Library ──
export const getMediaItems = (params) => api.get('/media/items', { params })
export const createMediaItem = (data) => api.post('/media/items', data)
export const deleteMediaItem = (id) => api.delete(`/media/items/${id}`)
export const suggestMedia = (ticketId) => api.get(`/media/suggest/${ticketId}`)
export const uploadMedia = (formData) => api.post('/media/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 120000,
})

// ── Tracking ──
export const getTrackingList = (params) => api.get('/tracking/list', { params })
export const getTrackingSummary = (days = 30) => api.get('/tracking/summary', { params: { days } })
export const refreshAllTrackings = () => api.post('/tracking/refresh-all')
export const refreshSingleTracking = (ticketId) => api.post(`/tracking/refresh/${ticketId}`)
export const syncShopifyTracking = (days = 30) => api.post('/tracking/sync-shopify', null, { params: { days } })

// ── E-commerce (Shopify + Yampi + Appmax) ──
export const getEcommerceOrders = (email) => api.get('/ecommerce/orders', { params: { email } })
export const getYampiOrders = (email) => api.get('/ecommerce/yampi/orders', { params: { email } })
export const getAppmaxOrders = (email) => api.get('/ecommerce/appmax/orders', { params: { email } })
export const getEcommerceSettings = () => api.get('/ecommerce/settings')
export const saveEcommerceSettings = (data) => api.post('/ecommerce/settings', data)
export const getShopifyCustomer = (email) => api.get('/ecommerce/shopify/customer', { params: { email } })
export const refundShopifyOrder = (orderId, data) => api.post(`/ecommerce/shopify/order/${orderId}/refund`, data)
export const cancelShopifyOrder = (orderId, data) => api.post(`/ecommerce/shopify/order/${orderId}/cancel`, data)
