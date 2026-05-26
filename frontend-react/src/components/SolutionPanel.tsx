import { useState, useEffect, useRef } from 'react'
import { Play, Square, RotateCcw, RotateCw, PlaySquare } from 'lucide-react'
import { useStore } from '../store/useStore'
import { API } from '../lib/api'
import EditorImport from 'react-simple-code-editor'
import Prism from 'prismjs'
import 'prismjs/components/prism-python'
import 'prismjs/themes/prism-tomorrow.css'

const Editor = (EditorImport as any).default || EditorImport

export default function SolutionPanel() {
  const { currentSessionId, currentQuestionId, currentSolution, setCurrentSolution, setCurrentQuestion, showConfirm } = useStore()

  const [activeTab, setActiveTab] = useState('tab-solution')
  const [model, setModel] = useState('gemini-3-flash-preview')
  const [instructions, setInstructions] = useState('')
  const [isInstructing, setIsInstructing] = useState(false)
  const [codeHistory, setCodeHistory] = useState<string[]>([])
  const [redoHistory, setRedoHistory] = useState<string[]>([])
  const [logs, setLogs] = useState<string[]>([])
  const [streamText, setStreamText] = useState('')
  
  const sseSourceRef = useRef<EventSource | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  // Scroll logs to bottom
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => { stopSSE() }
  }, [])

  // Load solution when question changes
  useEffect(() => {
    if (currentSessionId && currentQuestionId) {
      loadSolution()
    } else {
      setCurrentSolution(null)
      setLogs([])
      setStreamText('')
    }
  }, [currentSessionId, currentQuestionId])

  const loadSolution = async () => {
    try {
      const res = await API.get(`/api/sessions/${currentSessionId}/questions/${currentQuestionId}`)
      const data = await API.json(res)
      if (data && data.solution) {
        setCurrentSolution(data.solution)
      } else {
        setCurrentSolution(null)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const stopSSE = () => {
    if (sseSourceRef.current) {
      sseSourceRef.current.close()
      sseSourceRef.current = null
    }
  }

  const startSSE = () => {
    stopSSE()
    if (!currentSessionId || !currentQuestionId) return
    const url = `/api/sessions/${currentSessionId}/questions/${currentQuestionId}/stream`
    sseSourceRef.current = new EventSource(url, { withCredentials: true })
    
    sseSourceRef.current.onmessage = (e) => {
      try {
        const evt = JSON.parse(e.data)
        if (evt.type === 'done') {
          stopSSE()
          loadSolution()
          setStreamText('')
        } else if (evt.type === 'status') {
          // ignore
        } else if (evt.type === 'stream') {
          setStreamText(prev => prev + evt.chunk)
        } else {
          setLogs(prev => [...prev, `[${evt.ts}] ${evt.msg}`])
        }
      } catch {}
    }
    sseSourceRef.current.onerror = () => stopSSE()
  }

  const handleSolve = async () => {
    if (!currentSessionId || !currentQuestionId) return
    setLogs([])
    setStreamText('')
    setActiveTab('tab-logs')
    setCurrentSolution({ ...currentSolution, status: 'solving' } as any)
    const res = await API.post(`/api/sessions/${currentSessionId}/questions/${currentQuestionId}/solve`, { 
      model,
      instructions: instructions.trim() || null
    })
    if (res && res.ok) {
      startSSE()
    }
  }

  const handleRunTests = async () => {
    if (!currentSessionId || !currentQuestionId || !currentSolution?.code) return
    setCurrentSolution({ ...currentSolution, status: 'solving' } as any)
    const res = await API.post(`/api/sessions/${currentSessionId}/questions/${currentQuestionId}/run_tests`, {
      code: currentSolution.code
    })
    const data = await API.json(res)
    if (data && data.ok) {
      setCurrentSolution(data.solution)
      setActiveTab('tab-tests')
    } else {
      setCurrentSolution({ ...currentSolution, status: 'failed' } as any)
    }
  }

  const handleInstruct = async () => {
    if (!currentSessionId || !currentQuestionId || !instructions.trim()) return
    setIsInstructing(true)
    setActiveTab('tab-logs')
    setLogs([])
    setStreamText('')
    startSSE()
    
    try {
      const res = await API.post(`/api/sessions/${currentSessionId}/questions/${currentQuestionId}/instruct`, {
        model,
        instruction: instructions.trim()
      })
      const data = await API.json(res)
      if (data && data.ok) {
        if (data.updates.code && currentSolution?.code) {
          setCodeHistory(prev => [...prev, currentSolution.code!])
          setRedoHistory([]) // Clear redo stack on new action
        }
        setCurrentSolution(data.solution)
        setCurrentQuestion(data.question)
        if (data.updates.focus_tab) {
          setActiveTab(data.updates.focus_tab)
        }
        setInstructions('')
      }
    } catch (e) {
      console.error("Instruct failed", e)
    } finally {
      setIsInstructing(false)
      stopSSE()
    }
  }

  const handleUndo = () => {
    if (codeHistory.length === 0 || !currentSolution) return
    const prevCode = codeHistory[codeHistory.length - 1]
    const currentCode = currentSolution.code || ""
    setCodeHistory(prev => prev.slice(0, -1))
    setRedoHistory(prev => [...prev, currentCode])
    setCurrentSolution({ ...currentSolution, code: prevCode } as any)
  }

  const handleRedo = () => {
    if (redoHistory.length === 0 || !currentSolution) return
    const nextCode = redoHistory[redoHistory.length - 1]
    const currentCode = currentSolution.code || ""
    setRedoHistory(prev => prev.slice(0, -1))
    setCodeHistory(prev => [...prev, currentCode])
    setCurrentSolution({ ...currentSolution, code: nextCode } as any)
  }

  const handleStop = async () => {
    if (!currentSessionId || !currentQuestionId) return
    stopSSE()
    setCurrentSolution({ ...currentSolution, status: 'stopped' } as any)
    setLogs(prev => [...prev, '⛔ Stop requested...'])
    await API.post(`/api/sessions/${currentSessionId}/questions/${currentQuestionId}/stop`, {})
  }

  const handleReset = async () => {
    if (!currentSessionId || !currentQuestionId) return
    showConfirm('Reset Solution', 'Reset solution state?', async () => {
      stopSSE()
      await API.post(`/api/sessions/${currentSessionId}/questions/${currentQuestionId}/reset`, {})
      setLogs([])
      setStreamText('')
      setCurrentSolution(null)
    })
  }

  const handleCopy = () => {
    if (currentSolution?.code) {
      navigator.clipboard.writeText(currentSolution.code).catch(() => {})
    }
  }

  if (!currentQuestionId) return null

  const isSolving = currentSolution?.status === 'solving'
  
  // Extract complexities from explanation if present
  let timeComplexity = null
  let spaceComplexity = null
  if (currentSolution?.explanation) {
    const tMatch = currentSolution.explanation.match(/\bTime(?: Complexity)?:\s*\**\s*(O\([^)]+\))/i)
    if (tMatch) timeComplexity = tMatch[1]
    
    const sMatch = currentSolution.explanation.match(/\bSpace(?: Complexity)?:\s*\**\s*(O\([^)]+\))/i)
    if (sMatch) spaceComplexity = sMatch[1]
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="panel-title">Solution</h2>
        <span className={`status-pill ${
          isSolving ? 'pill-running' : 
          currentSolution?.status === 'solved' ? 'pill-success' : 
          currentSolution?.status === 'failed' ? 'pill-error' : 
          'pill-idle'
        }`}>
          {currentSolution?.status || 'pending'}
        </span>
      </div>

      <div className="solution-meta" style={{ marginBottom: '16px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <span>Iteration {currentSolution?.iterations || 0} · {currentSolution?.model_used || '—'}</span>
        {timeComplexity && (
          <span className="complexity-pill"><span className="complexity-lbl">Time:</span> {timeComplexity}</span>
        )}
        {spaceComplexity && (
          <span className="complexity-pill"><span className="complexity-lbl">Space:</span> {spaceComplexity}</span>
        )}
        <div style={{ display: 'flex', gap: '4px', marginLeft: 'auto' }}>
          <button onClick={handleUndo} disabled={codeHistory.length === 0} className="btn btn-ghost btn-sm">
            <RotateCcw size={14} /> Undo
          </button>
          <button onClick={handleRedo} disabled={redoHistory.length === 0} className="btn btn-ghost btn-sm">
            <RotateCw size={14} /> Redo
          </button>
        </div>
      </div>

      <div className="panel-controls" style={{ marginBottom: '20px', borderTop: 'none', paddingTop: 0, flexDirection: 'column' }}>
        <div className="select-wrap" style={{ width: '100%', marginBottom: '8px' }}>
          <select value={model} onChange={e => setModel(e.target.value)} disabled={isSolving} style={{ width: '100%' }}>
            <option value="gemini-3.1-flash-lite">gemini-3.1-flash-lite</option>
            <option value="gemini-3-flash-preview">gemini-3-flash-preview</option>
            <option value="gemini-2.5-flash">gemini-2.5-flash</option>
            <option value="gemini-2.5-flash-lite">gemini-2.5-flash-lite</option>
            <option value="gemma-4-31b-it">gemma-4-31b-it</option>
            <option value="gemma-4-26b-a4b-it">gemma-4-26b-a4b-it</option>
          </select>
        </div>

        <div style={{ position: 'relative', width: '100%', marginBottom: '8px' }}>
          <textarea 
            placeholder="Custom instructions (e.g. 'Use BFS', 'Optimize space', 'Explain line 5')..."
            value={instructions}
            onChange={e => setInstructions(e.target.value)}
            disabled={isSolving || isInstructing}
            style={{ 
              width: '100%', 
              minHeight: '60px', 
              background: 'rgba(0,0,0,0.2)', 
              border: '1px solid var(--border)', 
              borderRadius: 'var(--radius-sm)', 
              color: 'var(--text)', 
              padding: '10px',
              paddingRight: '60px',
              fontFamily: 'var(--font)',
              fontSize: '0.85rem',
              resize: 'vertical'
            }}
          />
          <button 
            onClick={handleInstruct}
            disabled={isSolving || isInstructing || !instructions.trim()}
            className="btn btn-primary"
            style={{ position: 'absolute', right: '8px', bottom: '12px', padding: '4px 12px', minHeight: 'auto', fontSize: '0.75rem' }}
            title="Send Instruction to update solution without re-running tests"
          >
            {isInstructing ? '...' : 'Send'}
          </button>
        </div>
        
        <div style={{ display: 'flex', gap: '8px', width: '100%' }}>
          {isSolving ? (
            <button onClick={handleStop} className="btn btn-danger" style={{ flex: 1 }}>
              <Square size={16} /> Stop Solver
            </button>
          ) : (
            <button onClick={handleSolve} className="btn btn-primary" style={{ flex: 1 }}>
              <Play size={16} /> {currentSolution?.status === 'failed' ? 'Retry Solve' : 'Solve'}
            </button>
          )}
          
          <button onClick={handleReset} className="btn btn-secondary btn-icon" title="Reset Solution">
            <RotateCcw size={16} />
          </button>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab-btn ${activeTab === 'tab-solution' ? 'active' : ''}`} onClick={() => setActiveTab('tab-solution')}>Solution</button>
        <button className={`tab-btn ${activeTab === 'tab-explanation' ? 'active' : ''}`} onClick={() => setActiveTab('tab-explanation')}>Explanation</button>
        <button className={`tab-btn ${activeTab === 'tab-tests' ? 'active' : ''}`} onClick={() => setActiveTab('tab-tests')}>Tests</button>
        <button className={`tab-btn ${activeTab === 'tab-logs' ? 'active' : ''}`} onClick={() => setActiveTab('tab-logs')}>Logs</button>
      </div>

      <div className={`tab-content ${activeTab === 'tab-solution' ? 'active' : ''}`}>
        {currentSolution?.code ? (
          <div className="code-wrap">
            <div className="code-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="code-label">Python</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button onClick={handleRunTests} className="btn btn-primary btn-sm" disabled={isSolving}>
                  <PlaySquare size={14} style={{ marginRight: '4px' }} /> Run Tests
                </button>
                <button onClick={handleCopy} className="btn btn-ghost btn-sm">⧉ Copy</button>
              </div>
            </div>
            <Editor
              value={currentSolution.code}
              onValueChange={(newCode: string) => {
                if (currentSolution.code !== newCode && codeHistory[codeHistory.length - 1] !== currentSolution.code) {
                  setCodeHistory(prev => [...prev, currentSolution.code!])
                  setRedoHistory([])
                }
                setCurrentSolution({ ...currentSolution, code: newCode } as any)
              }}
              highlight={(code: string) => {
                try {
                  if (Prism && Prism.languages && Prism.languages.python) {
                    return Prism.highlight(code, Prism.languages.python, 'python')
                  }
                  return code // Fallback to plain text if python language definition fails to load
                } catch (e) {
                  return code
                }
              }}
              padding={16}
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 14,
                backgroundColor: 'rgba(0,0,0,0.3)',
                minHeight: '200px',
                borderBottomLeftRadius: 'var(--radius-sm)',
                borderBottomRightRadius: 'var(--radius-sm)'
              }}
              className="code-editor-custom"
            />
          </div>
        ) : (
          <div className="placeholder-text">No solution generated yet.</div>
        )}
      </div>

      <div className={`tab-content ${activeTab === 'tab-explanation' ? 'active' : ''}`}>
        {currentSolution?.explanation ? (
          <div className="explanation-box">{currentSolution.explanation}</div>
        ) : (
          <div className="placeholder-text">No explanation available.</div>
        )}
      </div>

      <div className={`tab-content ${activeTab === 'tab-tests' ? 'active' : ''}`}>
        {currentSolution?.test_results && currentSolution.test_results.length > 0 ? (
          <div className="test-results">
            {currentSolution.test_results.map((r, i) => (
              <div key={i} className={`result-card ${r.passed ? 'passed' : 'failed'}`}>
                <span className="result-icon">{r.passed ? '✅' : '❌'}</span>
                <div className="result-body">
                  <div className="result-io"><strong>In:</strong> {r.input}</div>
                  <div className="result-io"><strong>Exp:</strong> {r.expected}</div>
                  {!r.passed && <div className="result-io"><strong>Got:</strong> {r.actual}</div>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="placeholder-text">No test results yet.</div>
        )}
      </div>

      <div className={`tab-content ${activeTab === 'tab-logs' ? 'active' : ''}`}>
        <div className="log-wrap">
          <div className="log-header">
            <span className="log-label">Live Log</span>
            <button onClick={() => { setLogs([]); setStreamText('') }} className="btn btn-ghost btn-sm">Clear</button>
          </div>
          <div className="log-box">
            {logs.map((log, i) => <div key={i}>{log}</div>)}
            {streamText && (
              <div className="stream-text" style={{ whiteSpace: 'pre-wrap', color: 'var(--primary)', marginTop: '8px', opacity: 0.8, fontSize: '0.85rem' }}>
                {streamText}
              </div>
            )}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>

    </section>
  )
}
