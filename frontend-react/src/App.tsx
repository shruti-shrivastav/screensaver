import { useStore } from './store/useStore'
import AuthModal from './components/AuthModal'
import HistoryPanel from './components/HistoryPanel'
import CapturePanel from './components/CapturePanel'
import QuestionPanel from './components/QuestionPanel'
import SolutionPanel from './components/SolutionPanel'
import { MonitorPlay } from 'lucide-react'

function App() {
  useStore()

  return (
    <div className="app-root">
      <header className="header">
        <div className="logo">
          <div className="logo-icon"><MonitorPlay size={20} /></div>
          <div className="logo-text">Screensaver</div>
        </div>
      </header>

      <main className="app-main">
        <CapturePanel />
        <QuestionPanel />
        <SolutionPanel />
        <HistoryPanel />
      </main>

      <AuthModal />
    </div>
  )
}

export default App
