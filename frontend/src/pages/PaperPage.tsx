import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import PaperViewer from '@/components/PaperViewer'
import { paperApi, PaperDetail } from '@/lib/api'

export default function PaperPage() {
  const { arxivId } = useParams<{ arxivId: string }>()
  const navigate = useNavigate()
  const [paper, setPaper] = useState<PaperDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!arxivId) return
    setLoading(true)
    paperApi.get(arxivId)
      .then(setPaper)
      .catch((err) => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [arxivId])

  const handleDelete = async () => {
    if (!arxivId || !confirm('确定要删除这篇论文吗？')) return
    await paperApi.delete(arxivId)
    navigate('/')
  }

  const handleRetry = async () => {
    if (!arxivId) return
    await paperApi.retry(arxivId)
    // Refresh
    const detail = await paperApi.get(arxivId)
    setPaper(detail)
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center text-gray-400">
        <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !paper) {
    return (
      <div className="h-screen flex flex-col items-center justify-center text-gray-500">
        <p className="mb-4">{error || '论文不存在'}</p>
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          <ArrowLeft className="w-4 h-4" />
          返回首页
        </button>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="bg-white border-b px-6 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate('/')}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </button>
        <span className="text-sm text-gray-500">返回列表</span>
      </div>
      <div className="flex-1 overflow-hidden flex flex-col">
        <PaperViewer paper={paper} onDelete={handleDelete} onRetry={handleRetry} />
      </div>
    </div>
  )
}
