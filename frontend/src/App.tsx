import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import PaperPage from './pages/PaperPage'

function Footer() {
  return (
    <div className="text-center py-3 text-xs text-gray-400 border-t bg-gray-50 shrink-0">
      <p>为弱智硕博提供的论文翻译网站，用于快速搞懂论文的核心要点，如要详细解读，请阅读原文。</p>
      <p className="mt-0.5">中南大学智能软件与影像工程实验室出品</p>
    </div>
  )
}

function App() {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/paper/:arxivId" element={<PaperPage />} />
        </Routes>
      </div>
      <Footer />
    </div>
  )
}

export default App
