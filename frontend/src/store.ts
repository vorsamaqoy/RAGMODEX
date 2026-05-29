import { create } from 'zustand'

export interface StoredSession {
  modelLoaded: boolean
  trainingData: boolean
  testData?: boolean
  modelName: string
  nMolecules: number
  nTest?: number
  fpRadius?: number
  fpNbits?: number
  llmProvider: string
  llmModel: string
  temperature: number
  savedAt: number
}

interface AppStore {
  modelLoaded: boolean
  trainingData: boolean
  modelName: string
  nMolecules: number
  llmProvider: string
  llmModel: string
  temperature: number
  setModelStatus: (s: { modelLoaded: boolean; trainingData: boolean; modelName: string; nMolecules: number }) => void
  setLlmStatus: (s: { provider: string; model: string; temperature?: number }) => void
}

export const useAppStore = create<AppStore>(set => ({
  modelLoaded: false,
  trainingData: false,
  modelName: '',
  nMolecules: 0,
  llmProvider: 'groq',
  llmModel: 'llama-3.3-70b-versatile',
  temperature: 0.3,
  setModelStatus: s => set(s),
  setLlmStatus: s => set(state => ({
    llmProvider: s.provider,
    llmModel: s.model,
    temperature: s.temperature ?? state.temperature,
  })),
}))
