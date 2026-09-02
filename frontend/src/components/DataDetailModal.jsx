const DataDetailModal = ({ item, onClose }) => {
  if (!item) return null

  const formatContent = (content) => {
    if (!content) return "—"
    if (typeof content === "string") {
      try {
        const parsed = JSON.parse(content)
        return JSON.stringify(parsed, null, 2)
      } catch {
        return content
      }
    }
    return JSON.stringify(content, null, 2)
  }

  const tags = item.tags || []
  const contentStr = formatContent(item.content)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" onClick={onClose}>
      <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={e=>e.stopPropagation()}>
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-start">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{item.title}</h2>
            <p className="text-sm text-gray-500 mt-1">{item.source} • {item.content_type} • {item.external_id}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">×</button>
        </div>

        <div className="px-6 py-4 space-y-4">
          {item.description && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Description</h3>
              <p className="text-sm text-gray-900 whitespace-pre-wrap bg-gray-50 p-3 rounded">{item.description}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><span className="font-semibold text-gray-700">Source:</span> {item.source}</div>
            <div><span className="font-semibold text-gray-700">Type:</span> {item.content_type}</div>
            <div><span className="font-semibold text-gray-700">External ID:</span> {item.external_id}</div>
            <div><span className="font-semibold text-gray-700">Severity:</span> {item.severity || "—"}</div>
            <div className="col-span-2"><span className="font-semibold text-gray-700">URL:</span> {item.url ? <a href={item.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline break-all">{item.url}</a> : "—"}</div>
            <div><span className="font-semibold text-gray-700">First seen:</span> {item.first_seen_at ? new Date(item.first_seen_at).toLocaleString() : "—"}</div>
            <div><span className="font-semibold text-gray-700">Last updated:</span> {item.last_updated_at ? new Date(item.last_updated_at).toLocaleString() : "—"}</div>
          </div>

          {tags.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Tags</h3>
              <div className="flex flex-wrap gap-1">
                {tags.map((t,i)=><span key={i} className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">{t}</span>)}
              </div>
            </div>
          )}

          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-1">Content (JSON)</h3>
            <pre className="text-xs bg-gray-900 text-gray-100 p-4 rounded overflow-x-auto whitespace-pre-wrap break-words max-h-96 overflow-y-auto">{contentStr}</pre>
          </div>
        </div>

        <div className="sticky bottom-0 bg-white border-t px-6 py-3 flex justify-end">
          <button onClick={onClose} className="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>
  )
}

export default DataDetailModal
