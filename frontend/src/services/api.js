import axios from 'axios'

// In production (Nginx), use relative URL so browser hits same host via proxy
// In dev (Vite), use VITE_API_URL or fallback to localhost
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_BASE_URL || undefined,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const sourcesAPI = {
  list: () => api.get('/api/sources'),
  get: (id) => api.get(`/api/sources/${id}`),
  scrape: (id) => api.post(`/api/sources/${id}/scrape`)
}

export const dataAPI = {
  list: (params) => api.get('/api/data', { params }),
  get: (id) => api.get(`/api/data/${id}`),
  delete: (id) => api.delete(`/api/data/${id}`)
}

export const sessionsAPI = {
  list: (params) => api.get('/api/sessions', { params }),
  get: (id) => api.get(`/api/sessions/${id}`)
}

export const analyticsAPI = {
  overview: () => api.get('/api/analytics/overview'),
  coverage: () => api.get('/api/analytics/coverage'),
  trends: () => api.get('/api/analytics/trends')
}

export const exportAPI = {
  toOpenSearch: (params) => api.post('/api/export/opensearch', null, { params }),
  logs: (params) => api.get('/api/export/logs', { params })
}

export default api
