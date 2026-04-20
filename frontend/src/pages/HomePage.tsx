import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import SubmitForm from '@/components/SubmitForm'
import PaperList from '@/components/PaperList'
import { Paper } from '@/lib/api'

export default function HomePage() {
  const navigate = useNavigate()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleSelect = useCallback((paper: Paper) => {
    setSelectedId(paper.arxiv_id)
    navigate(`/paper/${paper.arxiv_id}`)
  }, [navigate])

  const handleSuccess = useCallback(() => {
    setRefreshTrigger(t => t + 1)
  }, [])

  return (
    <div className="h-full flex flex-col">
      <SubmitForm onSuccess={handleSuccess} />
      <div className="flex-1 flex overflow-hidden">
        <PaperList
          selectedId={selectedId}
          onSelect={handleSelect}
          refreshTrigger={refreshTrigger}
        />
        <div className="flex-1 flex items-center justify-center text-gray-400 dark:text-gray-500">
          <div className="text-center">
            <h2 className="text-xl font-semibold text-gray-600 dark:text-gray-300 mb-2">救救孩子</h2>
            <p className="text-sm dark:text-gray-400">在左侧选择论文，或上方提交新的 arXiv 链接</p>
          </div>
        </div>
      </div>
    </div>
  )
}
