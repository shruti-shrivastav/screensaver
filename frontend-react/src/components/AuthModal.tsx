import { useState, useEffect } from 'react'
import { Lock } from 'lucide-react'
import { useStore } from '../store/useStore'
import { API } from '../lib/api'

export default function AuthModal() {
  const { isAuthModalOpen, setAuthModalOpen } = useStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    // Check initial auth status
    API.get('/auth/me').then(res => {
      if (!res || !res.ok) setAuthModalOpen(true)
    })

    const handleUnauth = () => setAuthModalOpen(true)
    window.addEventListener('app:unauthorized', handleUnauth)
    return () => window.removeEventListener('app:unauthorized', handleUnauth)
  }, [setAuthModalOpen])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    // Attempt login using exact same JSON payload format as original vanilla auth.js
    const loginRes = await API.post('/auth/login', { username, password })
    
    if (loginRes && loginRes.ok) {
      setAuthModalOpen(false)
      setPassword('')
      window.dispatchEvent(new Event('app:loggedin'))
      return
    }

    setError('Invalid credentials.')
  }

  if (!isAuthModalOpen) return null

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h2><Lock size={20} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Access Required</h2>
        </div>
        <div className="modal-body">
          <p style={{ marginBottom: '16px', color: 'var(--text-muted)' }}>
            Please log in to access the workspace.
          </p>
          <form onSubmit={handleSubmit}>
            <input 
              type="text" 
              className="input" 
              placeholder="Username..." 
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoFocus
              required
              style={{ marginBottom: '12px' }}
            />
            <input 
              type="password" 
              className="input" 
              placeholder="Password..." 
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            {error && <div style={{ color: 'var(--red)', marginTop: '8px', fontSize: '0.9rem' }}>{error}</div>}
            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary">Unlock</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
