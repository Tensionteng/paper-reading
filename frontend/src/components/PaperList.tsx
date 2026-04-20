import { useState, useEffect } from 'react'
import { Search, FileText, Loader2, AlertCircle } from 'lucide-react'
import { paperApi, Paper } from '@/lib/api'

interface Props {
  selectedId: string | null
  onSelect: (paper: Paper) => void
  refreshTrigger: number
}

export default function PaperList({ selectedId, onSelect, refreshTrigger }: Props) {
  const [papers, setPapers] = useState<Paper[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    paperApi.list(query || undefined)
      .then(setPapers)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [query, refreshTrigger])

  // Poll processing papers every 5s
  useEffect(() => {
    const hasProcessing = papers.some(p => p.status === 'processing' || p.status === 'pending')
    if (!hasProcessing) return
    const interval = setInterval(() => {
      paperApi.list(query || undefined).then(setPapers).catch(console.error)
    }, 5000)
    return () => clearInterval(interval)
  }, [papers, query])

  return (
    <div className="w-80 border-r dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col h-full">
      <div className="p-4 border-b dark:border-gray-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索论文..."
            className="w-full pl-9 pr-3 py-2 border dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder:text-gray-400"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && papers.length === 0 && (
          <div className="flex items-center justify-center py-8 text-gray-400">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            加载中...
          </div>
        )}

        {papers.length === 0 && !loading && (
          <div className="text-center py-8 text-gray-400 text-sm">
            <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
            暂无论文，请在上方提交
          </div>
        )}

        {papers.map((paper) => (
          <button
            key={paper.arxiv_id}
            onClick={() => onSelect(paper)}
            className={`w-full text-left px-4 py-3 border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
              selectedId === paper.arxiv_id ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-l-blue-600' : 'border-l-4 border-l-transparent'
            }`}
          >
            <div className="flex items-start gap-2">
              <div className="mt-0.5">
                {paper.status === 'done' ? (
                  <FileText className="w-4 h-4 text-gray-400" />
                ) : paper.status === 'processing' || paper.status === 'pending' ? (
                  <Loader2 className="w-4 h-4 text-yellow-500 animate-spin" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {paper.title_zh || paper.title || paper.arxiv_id}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                  {(() => {
                    const firstAuthor = paper.authors ? paper.authors.split(',')[0].trim() : null
                    const aff = paper.affiliation ? paper.affiliation.split(',')[0].trim() : null
                    if (firstAuthor && aff) return `${firstAuthor} · ${aff}`
                    return firstAuthor || paper.arxiv_id
                  })()}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="p-3 border-t dark:border-gray-700 text-xs text-gray-400 text-center">
        共 {papers.length} 篇论文
      </div>
    </div>
  )
}
