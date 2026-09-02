import { useState, useEffect } from 'react'
import { analyticsAPI } from '../services/api'
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']

const Analytics = () => {
  const [coverage, setCoverage] = useState([])
  const [trends, setTrends] = useState([])
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(()=>{
    Promise.all([
      analyticsAPI.coverage().then(r=>setCoverage(r.data)).catch(()=>{}),
      analyticsAPI.trends().then(r=>setTrends(r.data)).catch(()=>{}),
      analyticsAPI.overview().then(r=>setOverview(r.data)).catch(()=>{})
    ]).finally(()=>setLoading(false))
  },[])

  if(loading) return <div className="p-6 text-center">Loading...</div>

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold">Analytics</h1>

      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card text-center"><p className="text-sm text-gray-600">Total Items</p><p className="text-2xl font-bold">{overview.total_items?.toLocaleString()}</p></div>
          <div className="card text-center"><p className="text-sm text-gray-600">Sources</p><p className="text-2xl font-bold">{overview.sources_count}</p></div>
          <div className="card text-center"><p className="text-sm text-gray-600">Last Scrape</p><p className="text-sm">{overview.last_scrape? new Date(overview.last_scrape).toLocaleString(): 'Never'}</p></div>
          <div className="card text-center"><p className="text-sm text-gray-600">Active</p><p className="text-2xl font-bold">{overview.active_sessions}</p></div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Coverage by Source (Bar)</h2>
          {coverage.length===0 ? <p className="text-gray-500">No data</p> : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={coverage}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="display_name" tick={{fontSize:10}} interval={0} angle={-15} textAnchor="end" height={60} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" name="Items" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Distribution (Pie)</h2>
          {coverage.length===0 ? <p className="text-gray-500">No data</p> : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={coverage} cx="50%" cy="50%" labelLine={false} label={({display_name, percentage})=> `${display_name}: ${percentage.toFixed(1)}%`} outerRadius={100} dataKey="count">
                  {coverage.map((e,i)=><Cell key={i} fill={COLORS[i%COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Trends (30 days)</h2>
        {trends.length===0 ? <p className="text-gray-500">No trends yet — trigger a scrape</p> : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="scrapes" stroke="#3b82f6" name="Scrapes" />
              <Line yAxisId="right" type="monotone" dataKey="items_added" stroke="#10b981" name="Items Added" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Source Details</h2>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50"><tr><th className="px-4 py-2 text-left text-xs">Source</th><th className="px-4 py-2 text-right text-xs">Items</th><th className="px-4 py-2 text-right text-xs">%</th><th className="px-4 py-2 text-left text-xs">Last Scraped</th></tr></thead>
          <tbody className="divide-y divide-gray-200">
            {coverage.map(s=>(
              <tr key={s.source}><td className="px-4 py-2 font-medium">{s.display_name}</td><td className="px-4 py-2 text-right">{s.count.toLocaleString()}</td><td className="px-4 py-2 text-right">{s.percentage}%</td><td className="px-4 py-2 text-sm text-gray-500">{s.last_scraped? new Date(s.last_scraped).toLocaleString(): 'Never'}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Analytics
