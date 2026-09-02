import { useState, useEffect } from 'react'
import { sourcesAPI, analyticsAPI, exportAPI } from '../services/api'
import SourceCard from './SourceCard'

const Dashboard = () => {
  const [sources, setSources] = useState([])
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = async () => {
    try {
      setLoading(true)
      const [sRes, oRes] = await Promise.all([
        sourcesAPI.list(),
        analyticsAPI.overview().catch(() => ({ data: null }))
      ])
      setSources(sRes.data)
      if (oRes.data) setOverview(oRes.data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  // Poll while scrapes are active
  useEffect(() => {
    if (overview?.active_sessions > 0) {
      const id = setInterval(loadData, 3000)
      return () => clearInterval(id)
    }
  }, [overview?.active_sessions])

  const handleScrape = async (id) => {
    await sourcesAPI.scrape(id)
    setTimeout(loadData, 1000)
  }

  const handleExportAll = async () => {
    try {
      const res = await exportAPI.toOpenSearch({ format: 'jsonl' })
      const filename = res.data.filename
      const url = res.data.download_url
      // Trigger download via Nginx proxy
      window.open(url, '_blank')
      alert(`Exported ${res.data.items_exported} items to ${filename}`)
    } catch (e) {
      alert('Export failed: ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleExportSource = async (sourceId) => {
    try {
      const res = await exportAPI.toOpenSearch({ source_id: sourceId, format: 'jsonl' })
      window.open(res.data.download_url, '_blank')
    } catch (e) {
      alert('Export failed: ' + e.message)
    }
  }

  if (loading) return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div></div>
  if (error) return <div className="card bg-red-50 border border-red-200 text-red-800 p-4">Error: {error}</div>

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card text-center">
            <p className="text-sm text-gray-600">Total Items</p>
            <p className="text-2xl font-bold">{overview.total_items?.toLocaleString() ?? 0}</p>
          </div>
          <div className="card text-center">
            <p className="text-sm text-gray-600">Sources</p>
            <p className="text-2xl font-bold">{overview.sources_count ?? 0}</p>
          </div>
          <div className="card text-center">
            <p className="text-sm text-gray-600">Last Scrape</p>
            <p className="text-sm font-semibold">{overview.last_scrape ? new Date(overview.last_scrape).toLocaleString() : 'Never'}</p>
          </div>
          <div className="card text-center">
            <p className="text-sm text-gray-600">Active Scrapes</p>
            <p className="text-2xl font-bold">{overview.active_sessions ?? 0}</p>
          </div>
        </div>
      )}

      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Sources</h2>
        <button onClick={handleExportAll} className="btn btn-secondary">Export All (JSONL)</button>
      </div>
      <div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sources.map(s => (
            <div key={s.id} className="relative">
              <SourceCard source={s} onScrape={handleScrape} />
              <button onClick={()=>handleExportSource(s.id)} className="mt-2 w-full btn btn-secondary text-sm">Export {s.display_name}</button>
            </div>
          ))}
        </div>
        {sources.length === 0 && <p className="text-gray-500">No sources found. Run seed.</p>}
      </div>
    </div>
  )
}

export default Dashboard
