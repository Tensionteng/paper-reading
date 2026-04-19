import { useState, useCallback } from 'react'
import SubmitForm from '@/components/SubmitForm'
import PaperList from '@/components/PaperList'
import PaperViewer from '@/components/PaperViewer'
import { paperApi, Paper, PaperDetail } from '@/lib/api'

export default function HomePage() {
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)
  const [paperDetail, setPaperDetail] = useState<PaperDetail | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleSelect = useCallback(async (paper: Paper) => {
    setSelectedPaper(paper)
    try {
      const detail = await paperApi.get(paper.arxiv_id)
      setPaperDetail(detail)
    } catch (err) {
      console.error(err)
    }
  }, [])

  const handleSuccess = useCallback(() => {
    setRefreshTrigger(t => t + 1)
  }, [])

  const handleDelete = useCallback(async () => {
    if (!selectedPaper) return
    if (!confirm('确定要删除这篇论文吗？')) return
    await paperApi.delete(selectedPaper.arxiv_id)
    setSelectedPaper(null)
    setPaperDetail(null)
    setRefreshTrigger(t => t + 1)
  }, [selectedPaper])

  const handleRetry = useCallback(async () => {
    if (!selectedPaper) return
    await paperApi.retry(selectedPaper.arxiv_id)
    setRefreshTrigger(t => t + 1)
    // Refresh detail
    const detail = await paperApi.get(selectedPaper.arxiv_id)
    setPaperDetail(detail)
  }, [selectedPaper])

  return (
    <div className="h-full flex flex-col">
      <SubmitForm onSuccess={handleSuccess} />
      <div className="flex-1 flex overflow-hidden">
        <PaperList
          selectedId={selectedPaper?.arxiv_id || null}
          onSelect={handleSelect}
          refreshTrigger={refreshTrigger}
        />
        {paperDetail ? (
          <PaperViewer
            paper={paperDetail}
            onDelete={handleDelete}
            onRetry={handleRetry}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-600 mb-2">救救孩子</h2>
              <p className="text-sm">在左侧选择论文，或上方提交新的 arXiv 链接</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
