import { create } from 'zustand'

export interface Session {
  id: string
  label: string
  created_at: string
  question_count: number
}

export interface QuestionSummary {
  id: string
  title: string
  status: string
  created_at: string
}

export interface Example {
  input: string
  output: string
  explanation?: string
}

export interface TestCase {
  input: string
  output: string
}

export interface QuestionData {
  title: string
  description: string
  constraints: string
  examples: Example[]
  test_cases: TestCase[]
}

export interface TestResult {
  input: string
  expected: string
  actual: string
  passed: boolean
}

export interface Solution {
  status: string
  code: string
  explanation: string
  iterations: number
  test_results: TestResult[]
  model_used: string
}

export interface Question {
  id: string
  session_id: string
  status: string
  data?: QuestionData
  model_used: string
  created_at: string
}

interface AppState {
  isAuthModalOpen: boolean
  setAuthModalOpen: (open: boolean) => void
  
  sessions: Session[]
  setSessions: (sessions: Session[]) => void
  
  currentSessionId: string | null
  setCurrentSessionId: (id: string | null) => void
  
  questions: QuestionSummary[]
  setQuestions: (q: QuestionSummary[]) => void
  
  currentQuestionId: string | null
  setCurrentQuestionId: (id: string | null) => void
  
  currentQuestion: Question | null
  setCurrentQuestion: (q: Question | null) => void
  
  currentSolution: Solution | null
  setCurrentSolution: (s: Solution | null) => void
  
  isAnalyzing: boolean
  setIsAnalyzing: (val: boolean) => void
}

export const useStore = create<AppState>((set) => ({
  isAuthModalOpen: false,
  setAuthModalOpen: (open) => set({ isAuthModalOpen: open }),
  
  sessions: [],
  setSessions: (sessions) => set({ sessions }),
  
  currentSessionId: null,
  setCurrentSessionId: (id) => set({ currentSessionId: id, currentQuestionId: null, currentQuestion: null, currentSolution: null }),
  
  questions: [],
  setQuestions: (questions) => set({ questions }),
  
  currentQuestionId: null,
  setCurrentQuestionId: (id) => set({ currentQuestionId: id }),
  
  currentQuestion: null,
  setCurrentQuestion: (q) => set({ currentQuestion: q }),
  
  currentSolution: null,
  setCurrentSolution: (s) => set({ currentSolution: s }),
  
  isAnalyzing: false,
  setIsAnalyzing: (val) => set({ isAnalyzing: val }),
}))
