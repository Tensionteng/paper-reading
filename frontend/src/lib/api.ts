import axios from 'axios'

const API_BASE = (import.meta as any).env?.VITE_API_URL || ''

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Paper {
  id: number
  arxiv_id: string
  title: string | null
  title_zh: string | null
  authors: string | null
  affiliation: string | null
  abstract: string | null
  status: string
  error_msg: string | null
  created_at: string
  updated_at: string | null
}

export interface PaperDetail extends Paper {
  report_md: string | null
  raw_sections: any[] | null
  images: string[] | null
}

export const paperApi = {
  list: (q?: string) => api.get<Paper[]>('/papers/', { params: { q } }).then(r => r.data),
  get: (arxivId: string) => api.get<PaperDetail>(`/papers/${arxivId}`).then(r => r.data),
  create: (arxivUrl: string) => api.post('/papers/', { arxiv_url: arxivUrl }).then(r => r.data),
  delete: (arxivId: string) => api.delete(`/papers/${arxivId}`).then(r => r.data),
  retry: (arxivId: string) => api.post(`/papers/${arxivId}/retry`).then(r => r.data),
}

export default api
