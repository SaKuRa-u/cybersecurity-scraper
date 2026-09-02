import { useState, useEffect } from 'react'
import { dataAPI, sourcesAPI } from '../services/api'

const DataBrowser = () => {
  const [data, setData] = useState([])
  const [sources, setSources] = useState([])
  const [pagination, setPagination] = useState({ page: 1, per_page: 20, total: 0, pages: 0 })
  const [filters, setFilters] = useState({ search: '', source: '', content_type: '', sort_by: 'last_updated_at', order: 'desc' })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    sourcesAPI.list().then(r => setSources(r.data)).catch(()=>{})
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const params = { page: pagination.page, per_page: pagination.per_page, ...Object.fromEntries(Object.entries(filters).filter(([,v])=>v)) }
      const res = await dataAPI.list(params)
      setData(res.data.items)
      setPagination(p => ({ ...p, total: res.data.total, pages: res.data.pages }))
    } catch(e){ console.error(e) }
    setLoading(false)
  }

  useEffect(()=>{ loadData() }, [pagination.page, filters])

  const handleDelete = async (id) => {
    if(!confirm('Delete this item?')) return
    await dataAPI.delete(id)
    loadData()
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold">Data Browser</h1>

      <div className="card space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <input className="input" placeholder="Search..." value={filters.search} onChange={e=>{setFilters({...filters, search: e.target.value}); setPagination({...pagination, page:1})}} />
          <select className="input" value={filters.source} onChange={e=>{setFilters({...filters, source: e.target.value}); setPagination({...pagination, page:1})}}>
            <option value="">All Sources</option>
            {sources.map(s=><option key={s.id} value={s.name}>{s.display_name}</option>)}
          </select>
          <select className="input" value={filters.content_type} onChange={e=>{setFilters({...filters, content_type: e.target.value}); setPagination({...pagination, page:1})}}>
            <option value="">All Types</option>
            <option value="vulnerability">Vulnerability</option>
            <option value="technique">Technique</option>
            <option value="payload">Payload</option>
            <option value="tool_doc">Tool Doc</option>
          </select>
          <select className="input" value={filters.sort_by} onChange={e=>setFilters({...filters, sort_by: e.target.value})}>
            <option value="last_updated_at">Updated</option>
            <option value="first_seen_at">Created</option>
            <option value="title">Title</option>
          </select>
          <select className="input" value={filters.order} onChange={e=>setFilters({...filters, order: e.target.value})}>
            <option value="desc">Newest</option>
            <option value="asc">Oldest</option>
          </select>
        </div>
      </div>

      <div className="card">
        {loading ? <div className="text-center py-12">Loading...</div> : data.length===0 ? <div className="text-center py-12 text-gray-500">No data. Scrape a source from Dashboard.</div> : (
          <>
            <div className="text-sm text-gray-600 mb-4">Showing {((pagination.page-1)*pagination.per_page)+1} - {Math.min(pagination.page*pagination.per_page, pagination.total)} of {pagination.total}</div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50"><tr><th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Title</th><th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Source</th><th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Type</th><th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Tags</th><th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Actions</th></tr></thead>
                <tbody className="divide-y divide-gray-200">
                  {data.map(item=>(
                    <tr key={item.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2"><div className="text-sm font-medium">{item.title}</div><div className="text-xs text-gray-500 truncate max-w-md">{item.description}</div></td>
                      <td className="px-4 py-2 text-sm">{item.source}</td>
                      <td className="px-4 py-2"><span className="px-2 py-1 text-xs rounded-full bg-gray-100">{item.content_type}</span></td>
                      <td className="px-4 py-2 text-xs">{(item.tags||[]).slice(0,3).join(', ')}</td>
                      <td className="px-4 py-2 text-right"><button onClick={()=>handleDelete(item.id)} className="text-red-600 hover:text-red-800 text-sm">Delete</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {pagination.pages>1 && (
              <div className="mt-4 flex justify-center gap-2">
                <button disabled={pagination.page===1} onClick={()=>setPagination({...pagination, page: pagination.page-1})} className="btn btn-secondary disabled:opacity-50">Prev</button>
                <span className="px-4 py-2 text-sm">Page {pagination.page} of {pagination.pages}</span>
                <button disabled={pagination.page===pagination.pages} onClick={()=>setPagination({...pagination, page: pagination.page+1})} className="btn btn-secondary disabled:opacity-50">Next</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default DataBrowser
