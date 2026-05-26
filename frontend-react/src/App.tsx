import { useStore } from './store/useStore'
import AuthModal from './components/AuthModal'
import HistoryPanel from './components/HistoryPanel'
import CapturePanel from './components/CapturePanel'
import QuestionPanel from './components/QuestionPanel'
import SolutionPanel from './components/SolutionPanel'
import { MonitorPlay, Power, Square, AlertTriangle } from 'lucide-react'
import { API } from './lib/api'

function App() {
  const { dialog, showAlert, showConfirm, closeDialog } = useStore()

  const handleRestart = () => {
    showConfirm("Restart Server", "Are you sure you want to restart the server? This will terminate all current operations.", async () => {
      try {
        const res = await API.post('/api/system/restart', {});
        if (res && res.ok) {
          showAlert('Server Restarting', 'Server is restarting... Please refresh the page in a few seconds.');
        } else {
          showAlert('Restart Failed', 'Failed to restart server.');
        }
      } catch (err) {
        showAlert('Error', 'Error: ' + err);
      }
    });
  };

  const handleStop = () => {
    showConfirm("Stop Server", "Are you sure you want to STOP the server? You will need to start it manually from the terminal.", () => {
      // Need a slight timeout so the first dialog fully closes before opening the second
      setTimeout(() => {
        showConfirm("Double Confirmation", "The server will shut down completely. Continue?", async () => {
          try {
            const res = await API.post('/api/system/stop', {});
            if (res && res.ok) {
              showAlert('Server Stopping', 'Server is stopping... The UI will no longer function.');
            } else {
              showAlert('Stop Failed', 'Failed to stop server.');
            }
          } catch (err) {
            showAlert('Error', 'Error: ' + err);
          }
        });
      }, 50);
    });
  };

  return (
    <div className="app-root">
      <header className="header">
        <div className="logo">
          <div className="logo-icon"><MonitorPlay size={20} /></div>
          <div className="logo-text">Screensaver</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '10px' }}>
          <button 
            onClick={handleStop}
            style={{ 
              padding: '6px 12px', 
              background: 'rgba(225, 29, 72, 0.2)', 
              color: '#fb7185', 
              borderRadius: '6px', 
              border: '1px solid rgba(225, 29, 72, 0.5)', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px',
              fontSize: '13px',
              fontWeight: 500,
              transition: 'all 0.2s'
            }}
            onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(225, 29, 72, 0.3)' }}
            onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(225, 29, 72, 0.2)' }}
          >
            <Square size={14} fill="currentColor" /> Stop Server
          </button>
          
          <button 
            onClick={handleRestart}
            style={{ 
              padding: '6px 12px', 
              background: 'rgba(225, 29, 72, 0.2)', 
              color: '#fb7185', 
              borderRadius: '6px', 
              border: '1px solid rgba(225, 29, 72, 0.5)', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px',
              fontSize: '13px',
              fontWeight: 500,
              transition: 'all 0.2s'
            }}
            onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(225, 29, 72, 0.3)' }}
            onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(225, 29, 72, 0.2)' }}
          >
            <Power size={14} /> Restart Server
          </button>
        </div>
      </header>

      <main className="app-main">
        <CapturePanel />
        <QuestionPanel />
        <SolutionPanel />
        <HistoryPanel />
      </main>

      <AuthModal />

      {/* Custom Dialog Modal */}
      {dialog.isOpen && (
        <div className="modal-overlay" style={{ zIndex: 9999 }}>
          <div className="modal" style={{ maxWidth: '400px' }}>
            <div className="modal-header">
              <h2><AlertTriangle size={20} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--red)' }} /> {dialog.title}</h2>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: '20px', color: 'var(--text-color)', lineHeight: 1.5 }}>
                {dialog.message}
              </p>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                {dialog.type === 'confirm' && (
                  <button 
                    className="btn" 
                    onClick={closeDialog}
                    style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-muted)' }}
                  >
                    Cancel
                  </button>
                )}
                <button 
                  className="btn btn-primary" 
                  style={{ background: 'var(--red)' }}
                  onClick={() => {
                    closeDialog();
                    dialog.onConfirm();
                  }}
                >
                  {dialog.type === 'confirm' ? 'Confirm' : 'OK'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
