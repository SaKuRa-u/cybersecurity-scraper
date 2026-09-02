import { useState } from 'react'

const SourceCard = ({ source, onScrape, progress }) => {
  const [isLoading, setIsLoading] = useState(false)

  const handleScrape = async () => {
    setIsLoading(true)
    try {
      await onScrape(source.id)
    } catch (e) {
      console.error(e)
    } finally {
      setIsLoading(false)
    }
  }

  const formatTimestamp = (ts) => {
    if (!ts) return 'Never'
    return new Date(ts).toLocaleString()
  }

  const getStatusColor = () => {
    if (progress) return 'text-blue-600'
    if (source.last_session_status === 'completed') return 'text-green-600'
    if (source.last_session_status === 'failed') return 'text-red-600'
    return 'text-gray-400'
  }

  return (
    <div className="card">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{source.display_name}</h3>
          <p className="text-sm text-gray-500">{source.total_items ?? 0} items</p>
        </div>
        <span className={`text-sm font-medium ${getStatusColor()}`}>
          {progress ? 'Running...' : source.last_session_status || 'idle'}
        </span>
      </div>

      {progress && (
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>{progress.status}</span>
            <span>{progress.percentage ?? 0}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${progress.percentage ?? 0}%` }} />
          </div>
        </div>
      )}

      <div className="text-sm text-gray-600 mb-4 space-y-1">
        <p>Last scraped: {formatTimestamp(source.last_scraped_at)}</p>
        <p>Total scrapes: {source.scrape_count ?? 0}</p>
      </div>

      <button
        onClick={handleScrape}
        disabled={isLoading || !!progress}
        className="btn btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? 'Starting...' : progress ? 'Scraping...' : 'Scrape Now'}
      </button>
    </div>
  )
}

export default SourceCard
