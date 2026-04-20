import { Routes, Route } from 'react-router-dom'
import { Github } from 'lucide-react'
import ThemeToggle from './components/ThemeToggle'
import HomePage from './pages/HomePage'
import PaperPage from './pages/PaperPage'

function Header() {
  return (
    <div className="absolute top-4 right-4 z-50 flex items-center gap-2">
      <ThemeToggle />
      <a
        href="https://github.com/Tensionteng/paper-reading"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center w-9 h-9 rounded-full bg-gray-800 text-white hover:bg-gray-900 transition-colors shadow-sm"
      >
        <Github size={20} />
      </a>
    </div>
  )
}

function Footer() {
  return (
    <div className="text-center py-3 text-xs text-gray-400 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-900 shrink-0">
      <p>中南大学智能软件与影像工程实验室</p>
    </div>
  )
}

function App() {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Header />
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
