import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Scripts
export const getOptions = () => api.get('/scripts/options')
export const listScripts = (params) => api.get('/scripts/', { params })
export const getScript = (id) => api.get(`/scripts/${id}`)
export const generateScript = (brief) => api.post('/scripts/generate', brief)
export const updateScript = (id, data) => api.patch(`/scripts/${id}`, data)
export const deleteScript = (id) => api.delete(`/scripts/${id}`)
export const refineScript = (id, data) => api.post(`/scripts/${id}/refine`, data)
export const rateScript = (id, data) => api.post(`/scripts/${id}/rate`, data)

// Meta Ads
export const linkAd = (id, data) => api.post(`/scripts/${id}/link-ad`, data)
export const syncPerformance = (id) => api.post(`/scripts/${id}/sync-performance`)
export const syncAllPerformance = () => api.post('/scripts/sync-all-performance')
export const getCampaigns = () => api.get('/scripts/meta/campaigns')
export const getCampaignAds = (id) => api.get(`/scripts/meta/campaigns/${id}/ads`)

// Insights
export const getCustomerInsights = (productName) =>
  api.get('/scripts/insights/customer', { params: { product_name: productName } })

// Performance
export const getPerformanceStats = () => api.get('/scripts/stats/performance')

// Health
export const getHealth = () => api.get('/health')

export default api
