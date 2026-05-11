import { useStore } from '../store/useStore'
import { FileText, CheckCircle2, XCircle } from 'lucide-react'

export default function QuestionPanel() {
  const { currentSessionId, currentQuestion, currentSolution } = useStore()
  
  if (!currentQuestion || !currentQuestion.data) {
    return (
      <section className="panel empty-state">
        <FileText size={32} opacity={0.3} style={{ margin: '0 auto 12px' }} />
        <div className="placeholder-text" style={{ border: 'none', background: 'transparent' }}>
          Capture and analyze to extract question data.
        </div>
      </section>
    )
  }

  const { title, description, constraints, examples, test_cases } = currentQuestion.data

  const allCases: any[] = []
  const seenInputs = new Set()
  
  if (examples) {
    examples.forEach((ex, i) => {
      allCases.push({ ...ex, type: 'Example', index: i + 1 })
      seenInputs.add(ex.input.trim())
    })
  }
  if (test_cases) {
    test_cases.forEach((tc, i) => {
      if (!seenInputs.has(tc.input.trim())) {
        allCases.push({ ...tc, type: 'Test', index: i + 1 })
        seenInputs.add(tc.input.trim())
      }
    })
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="panel-title"><FileText size={18} /> {title}</h2>
        <span className="status-pill pill-success">analyzed</span>
      </div>
      
      <div className="question-body">
        {currentSessionId && currentQuestion.id && (
          <details className="q-details" style={{ marginBottom: '16px' }}>
            <summary>View Captured Image</summary>
            <div style={{ padding: 0 }}>
              <img 
                src={`/api/sessions/${currentSessionId}/questions/${currentQuestion.id}/image`} 
                alt="Captured problem"
                style={{ width: '100%', display: 'block', maxHeight: '400px', objectFit: 'contain', background: '#000' }}
                onError={(e) => { 
                  const details = (e.target as HTMLImageElement).closest('details');
                  if (details) details.style.display = 'none';
                }}
              />
            </div>
          </details>
        )}
      
        <div className="section-title">Description</div>
        <div className="markdown-body" style={{ whiteSpace: 'pre-wrap', marginBottom: '16px' }}>{description}</div>
        
        {constraints && (
          <div style={{ marginBottom: '20px' }}>
            <div className="section-title">Constraints</div>
            <div className="constraints-list">
              {constraints.split(',').map((c, i) => (
                <span key={i} className="constraint-chip">{c.trim()}</span>
              ))}
            </div>
          </div>
        )}

        {allCases.length > 0 && (
          <div>
            <div className="section-title">Examples & Test Cases</div>
            <div className="test-list">
              {allCases.map((item, i) => {
                const tr = currentSolution?.test_results?.find(r => r.input.trim() === item.input.trim());
                let statusClass = '';
                let statusIcon = null;
                if (tr) {
                  statusClass = tr.passed ? 'tc-passed' : 'tc-failed';
                  statusIcon = tr.passed ? <CheckCircle2 size={16} className="text-green" /> : <XCircle size={16} className="text-red" />;
                }

                return (
                  <div key={i} className={`test-item ${statusClass}`}>
                    <div className="item-header">
                      <span className="item-label">{item.type} {item.index}</span>
                      {statusIcon}
                    </div>
                    <div className="item-val"><span className="io-lbl">In:</span> <span className="io-code">{item.input}</span></div>
                    <div className="item-val"><span className="io-lbl">Out:</span> <span className="io-code">{item.output}</span></div>
                    {item.explanation && (
                      <div className="item-explanation"><em>{item.explanation}</em></div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
