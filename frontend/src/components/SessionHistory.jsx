import { useState, useEffect } from 'react'
import { sessionsAPI } from '../services/api'

const SessionHistory = () => {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(()=>{
    sessionsAPI.list({limit:100}).then(r=>setSessions(r.data)).catch(()=>{}).finally(()=>setLoading(false))
  },[])

  const formatDuration = (s)=> s? `${Math.floor(s/60)}m ${s%60}s` : 'N/A'

  if(loading) return <div className="p-6 text-center">Loading...</div>

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold">Scrape History</h1>
      <div className="card">
        {sessions.length===0 ? <div className="text-center py-12 text-gray-500">No sessions yet. Trigger a scrape from Dashboard.</div> : (
          <div className="space-y-4">
            {sessions.map(s=>(
              <div key={s.id} className="border rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold">{s.source_display_name} <span className="ml-2 text-xs px-2 py-1 rounded-full bg-gray-100">{s.status}</span></h3>
                  <span className="text-sm text-gray-500">{new Date(s.started_at).toLocaleString()}</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div><p className="text-gray-500">Duration</p><p className="font-medium">{formatDuration(s.duration_seconds)}</p></div>
                  <div><p className="text-gray-500">Found</p><p className="font-medium">{s.items_found}</p></div>
                  <div><p className="text-gray-500">Inserted</p><p className="font-medium text-green-600">+{s.items_inserted}</p></div>
                  <div><p className="text-gray-500">Triggered</p><p className="font-medium">{s.triggered_by}</p></div>
                </div>
                {s.error_message && <div className="mt-2 p-2 bg-red-50 text-red-800 text-sm rounded">{s.error_message}</div>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default SessionHistory
