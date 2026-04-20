import { useState, FormEvent } from 'react'
import { Loader2, Link2 } from 'lucide-react'
import { paperApi } from '@/lib/api'

interface Props {
  onSuccess: () => void
}

export default function SubmitForm({ onSuccess }: Props) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return
    setLoading(true)
    setMessage('')
    try {
      const res = await paperApi.create(url.trim())
      if (res.status === 'pending' && res.message?.includes('already exists')) {
        setMessage('⚠️ ' + res.message)
      } else {
        setMessage('✅ ' + res.message)
        setUrl('')
        onSuccess()
      }
    } catch (err: any) {
      setMessage('❌ ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 border-b dark:border-gray-700 px-6 py-4">
      <form onSubmit={handleSubmit} className="flex items-center gap-3 max-w-4xl mx-auto">
        <div className="relative flex-1">
          <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="粘贴 arXiv 链接或 ID，如 2405.12345"
            className="w-full pl-10 pr-4 py-2.5 border dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder:text-gray-400"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          提交
        </button>
      </form>
      {message && (
        <div className="max-w-4xl mx-auto mt-2 text-sm text-gray-700 dark:text-gray-300">{message}</div>
      )}
    </div>
  )
}
