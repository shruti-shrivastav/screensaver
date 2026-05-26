import { useEffect } from 'react'
import { Trash2 } from 'lucide-react'
import { useStore } from '../store/useStore'
import { API } from '../lib/api'

export default function HistoryPanel() {
  const { 
    currentSessionId,
    questions, setQuestions,
    currentQuestionId, setCurrentQuestionId, setCurrentQuestion,
    showConfirm
  } = useStore()


  // Load questions when session changes
  useEffect(() => {
    if (currentSessionId) {
      loadQuestions(currentSessionId)
    } else {
      setQuestions([])
    }
  }, [currentSessionId])

  // Load specific question details when selected
  useEffect(() => {
    if (currentSessionId && currentQuestionId) {
      loadQuestionDetails(currentSessionId, currentQuestionId)
    }
  }, [currentQuestionId])


  const loadQuestions = async (sid: string) => {
    const res = await API.get(`/api/sessions/${sid}`)
    const data = await API.json(res)
    if (data && data.questions) {
      setQuestions(data.questions)
    }
  }

  const loadQuestionDetails = async (sid: string, qid: string) => {
    const res = await API.get(`/api/sessions/${sid}/questions/${qid}`)
    const data = await API.json(res)
    if (data && data.question) {
      setCurrentQuestion(data.question)
    }
  }

  const deleteQuestion = async (e: React.MouseEvent, qid: string) => {
    e.stopPropagation()
    if (!currentSessionId) return
    showConfirm('Delete Question', 'Delete this question?', async () => {
      await API.post(`/api/sessions/${currentSessionId}/questions/${qid}/delete`, {})
      if (currentQuestionId === qid) {
        setCurrentQuestionId(null)
        setCurrentQuestion(null)
      }
      loadQuestions(currentSessionId)
    })
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="panel-title">History</h2>
        <button onClick={() => currentSessionId && loadQuestions(currentSessionId)} className="btn btn-ghost btn-sm" title="Refresh">
          ↻
        </button>
      </div>

      <div className="history-list">
        {questions.length === 0 ? (
          <div className="history-empty">No sessions yet.</div>
        ) : (
          questions.map(q => (
            <div 
              key={q.id}
              className={`history-question ${currentQuestionId === q.id ? 'active' : ''}`}
              onClick={() => setCurrentQuestionId(q.id)}
            >
              <img 
                src={`/api/sessions/${currentSessionId}/questions/${q.id}/image`} 
                alt="thumb" 
                className="history-thumb"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
              />
              <div className="history-q-info">
                <div className="history-q-title">{q.title}</div>
                <div className="history-q-meta">{q.status}</div>
              </div>
              <button 
                className="btn-del-history" 
                onClick={(e) => deleteQuestion(e, q.id)}
                title="Delete Question"
                style={{ justifySelf: 'end' }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
