import { useState, useRef, useEffect } from 'react'
import { Video, RefreshCw, Square } from 'lucide-react'
import { useStore } from '../store/useStore'
import { API } from '../lib/api'

export default function CapturePanel() {
  const [model, setModel] = useState('gemini-3-flash-preview')
  const [streamText, setStreamText] = useState('')
  const [frames, setFrames] = useState<string[]>([])
  const { 
    currentSessionId, isAnalyzing, setIsAnalyzing, setCurrentQuestionId, setCurrentQuestion,
    sessions, setSessions, setCurrentSessionId,
    setQuestions, showAlert
  } = useStore()
  const imgRef = useRef<HTMLImageElement>(null)
  
  useEffect(() => {
    API.get('/api/sessions').then(r => API.json(r)).then(d => {
      if (d) {
        setSessions(d)
        if (d.length > 0 && !useStore.getState().currentSessionId) {
          setCurrentSessionId(d[0].id)
        }
      }
    })
  }, [])

  const loadFrames = async () => {
    if (!currentSessionId) return
    try {
      const res = await API.get(`/api/sessions/${currentSessionId}/frames`)
      const data = await API.json(res)
      if (data && data.frames) setFrames(data.frames)
    } catch {}
  }

  useEffect(() => {
    if (currentSessionId) {
      loadFrames()
    } else {
      setFrames([])
    }
  }, [currentSessionId])

  const refreshFrame = () => {
    if (imgRef.current) {
      imgRef.current.src = `/api/frame?t=${Date.now()}`
    }
  }

  const abortControllerRef = useRef<AbortController | null>(null)

  const handleAnalyze = async () => {
    if (!currentSessionId) return
    refreshFrame()
    setIsAnalyzing(true)
    setStreamText('')
    
    abortControllerRef.current = new AbortController()
    
    const source = new EventSource(`/api/sessions/${currentSessionId}/stream`, { withCredentials: true })
    source.onmessage = (e) => {
      try {
        const evt = JSON.parse(e.data)
        if (evt.type === 'stream') setStreamText(prev => prev + evt.chunk)
      } catch {}
    }
    source.onerror = () => source.close()
    
    try {
      const res = await API.post(`/api/sessions/${currentSessionId}/analyze`, { model }, {
        signal: abortControllerRef.current.signal
      })
      
      const q = await API.json(res)
      if (q && q.id) {
        setCurrentQuestionId(q.id)
        setCurrentQuestion(q)
        
        // Reload questions to reflect new/updated question in history
        const qsRes = await API.get(`/api/sessions/${currentSessionId}`)
        const qsData = await API.json(qsRes)
        if (qsData && qsData.questions) {
          setQuestions(qsData.questions)
        }
        loadFrames()
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        showAlert('Analysis Failed', err.message || 'An error occurred during analysis.')
      }
    } finally {
      setIsAnalyzing(false)
      abortControllerRef.current = null
      source.close()
    }
  }

  const handleManualCapture = async () => {
    if (!currentSessionId) return
    refreshFrame()
    try {
      await API.post(`/api/sessions/${currentSessionId}/capture`, {})
      loadFrames()
    } catch (e) {
      console.error(e)
    }
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsAnalyzing(false)
  }

  const createSession = async () => {
    const res = await API.post('/api/sessions', { label: 'New Session' })
    const data = await API.json(res)
    if (data) {
      setCurrentSessionId(data.id)
      API.get('/api/sessions').then(r => API.json(r)).then(d => d && setSessions(d))
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="panel-title"><Video size={18} style={{verticalAlign: 'bottom'}} /> Capture & Analyze</h2>
        <button onClick={refreshFrame} className="btn btn-ghost btn-sm" title="Refresh Image">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>
      
      <div className="preview-container" onClick={refreshFrame}>
        <img ref={imgRef} src="/api/frame" alt="Stream Preview" className="preview-img" />
      </div>

      <div className="panel-controls">
        <div className="select-wrap">
          <select value={model} onChange={e => setModel(e.target.value)} disabled={isAnalyzing}>
            <option value="gemini-3.1-flash-lite">gemini-3.1-flash-lite</option>
            <option value="gemini-3-flash-preview">gemini-3-flash-preview</option>
            <option value="gemini-2.5-flash">gemini-2.5-flash</option>
            <option value="gemini-2.5-flash-lite">gemini-2.5-flash-lite</option>
            <option value="gemma-4-31b-it">gemma-4-31b-it</option>
            <option value="gemma-4-26b-a4b-it">gemma-4-26b-a4b-it</option>
          </select>
        </div>

        <div className="select-wrap">
          <select 
            value={currentSessionId || ''} 
            onChange={e => setCurrentSessionId(e.target.value)}
          >
            <option value="">New session…</option>
            {sessions.map(s => (
              <option key={s.id} value={s.id}>
                {s.label || s.id} ({s.question_count}q)
              </option>
            ))}
          </select>
        </div>
        <button onClick={createSession} className="btn btn-ghost btn-sm" title="New Session">
          ＋
        </button>
      </div>

      <div className="panel-actions" style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
        <button onClick={handleManualCapture} className="btn btn-secondary btn-large" disabled={isAnalyzing || !currentSessionId} style={{ flex: 1 }} title="Save a screenshot without analyzing">
          <Video size={16} style={{verticalAlign: 'text-bottom', marginRight: '4px'}} /> Capture
        </button>
        {isAnalyzing ? (
          <button onClick={handleStop} className="btn btn-danger btn-large" style={{ flex: 1 }}>
            <Square size={16} style={{verticalAlign: 'text-bottom'}} /> Stop
          </button>
        ) : (
          <button onClick={handleAnalyze} className="btn btn-primary btn-large" disabled={!currentSessionId} style={{ flex: 1 }} title="Extract problem text using LLM">
            Analyze Screen
          </button>
        )}
      </div>

      {streamText && (
        <div className="stream-text" style={{ whiteSpace: 'pre-wrap', color: 'var(--primary)', marginTop: '16px', padding: '12px', background: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem' }}>
          {streamText}
        </div>
      )}

      {frames.length > 0 && (
        <div className="frames-gallery" style={{ marginTop: '20px' }}>
          <div className="section-title">Session Captures ({frames.length})</div>
          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '8px' }}>
            {frames.map(f => (
              <img 
                key={f}
                src={`/api/sessions/${currentSessionId}/frames/${f}`} 
                alt="Frame"
                style={{ height: '80px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: '#000', cursor: 'pointer' }}
                onClick={() => {
                  if (imgRef.current) imgRef.current.src = `/api/sessions/${currentSessionId}/frames/${f}`
                }}
                title="Click to view in main preview"
              />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
