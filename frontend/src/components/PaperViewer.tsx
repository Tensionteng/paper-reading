import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import { ExternalLink, Trash2, RotateCcw } from 'lucide-react'
import { PaperDetail } from '@/lib/api'

interface Props {
  paper: PaperDetail
  onDelete: () => void
  onRetry: () => void
}

export default function PaperViewer({ paper, onDelete, onRetry }: Props) {
  const imageBase = `/images/${paper.arxiv_id}/`

  const processReportMd = (md: string) => {
    if (!md) return ''
    // Replace relative image paths with absolute paths
    return md.replace(/!\[([^\]]*)\]\(\.\/([^)]+)\)/g, (_match, alt, path) => {
      return `![${alt}](${imageBase}${path})`
    })
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto pb-8">
        {/* Header */}
        <div className="mb-6 bg-white rounded-xl border p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900">
                {paper.title_zh || paper.title || '无标题'}
              </h1>
              {paper.title && paper.title !== paper.title_zh && (
                <p className="text-gray-500 mt-1 text-sm">{paper.title}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <a
                href={`https://arxiv.org/abs/${paper.arxiv_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                title="查看 arXiv 原文"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
              {paper.status === 'failed' && (
                <button
                  onClick={onRetry}
                  className="p-2 text-gray-500 hover:text-orange-600 hover:bg-orange-50 rounded-lg transition-colors"
                  title="重新处理"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={onDelete}
                className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="删除"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
            {paper.authors && <span>作者: {paper.authors}</span>}
            <span>arXiv: {paper.arxiv_id}</span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
              paper.status === 'done' ? 'bg-green-100 text-green-700' :
              paper.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
              paper.status === 'pending' ? 'bg-gray-100 text-gray-700' :
              'bg-red-100 text-red-700'
            }`}>
              {paper.status === 'done' ? '已完成' :
               paper.status === 'processing' ? '处理中' :
               paper.status === 'pending' ? '等待中' :
               '失败'}
            </span>
          </div>

          {paper.error_msg && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              错误: {paper.error_msg}
            </div>
          )}
        </div>

        {/* Content */}
        {paper.status === 'processing' && !paper.report_md && (
          <div className="flex items-center justify-center py-20 text-gray-400">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-3" />
              <p>论文处理中，请稍候...</p>
            </div>
          </div>
        )}

        {paper.report_md && (
          <div className="markdown-body bg-white rounded-xl border p-8 shadow-sm">
            <ReactMarkdown
              remarkPlugins={[remarkMath, remarkGfm]}
              rehypePlugins={[rehypeKatex]}
            >
              {processReportMd(paper.report_md)}
            </ReactMarkdown>
          </div>
        )}

        {paper.status === 'failed' && !paper.report_md && (
          <div className="text-center py-20 text-gray-400">
            <p>处理失败，请查看错误信息或点击重试</p>
          </div>
        )}
      </div>
    </div>
  )
}
