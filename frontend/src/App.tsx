import { useEffect, useState, Component, type ErrorInfo, type ReactNode, type MouseEvent } from 'react'
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { Toaster } from './components/shadcn/sonner'
import { TooltipProvider } from './components/shadcn/tooltip'
import { ScaledCanvas } from './components/layout/ScaledCanvas'
import { Icon, TOKENS } from './glass'
import {
  ChatPage,
  PredictionPage,
  DesignPage,
  ScreeningPage,
  EvaluationPage,
  VisualizerPage,
  SettingsPage,
} from './pages'
import { LandingPage } from './pages/LandingPage'
import { useAppStore, type StoredSession } from './store'
import { getModelStatus, restoreSession, startNewSession } from './lib/api'

const qc = new QueryClient()

// ── Error boundary ────────────────────────────────────────────────────────────

class PageErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null }
  static getDerivedStateFromError(error: Error) { return { error } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('[PageError]', error, info) }
  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center h-full gap-3 p-8">
          <p className="text-red-400 font-mono text-sm">
            {(this.state.error as Error).message || 'Unexpected error'}
          </p>
          <button
            className="text-xs text-muted-foreground underline hover:text-foreground"
            onClick={() => this.setState({ error: null })}
          >
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

const GLASS_NAV_ITEMS = [
  { label: 'Chat', to: '/' },
  { label: 'Prediction', to: '/predict' },
  { label: 'Design', to: '/design' },
  { label: 'Screening', to: '/screening' },
  { label: 'Evaluation', to: '/evaluate' },
  { label: 'Visualizer', to: '/visualizer' },
]

function GlassRouteCanvas({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  function handleClick(event: MouseEvent<HTMLDivElement>) {
    if (event.target instanceof HTMLInputElement) return
    if (event.clientX === 0 && event.clientY === 0) return

    const bounds = event.currentTarget.getBoundingClientRect()
    const scale = Math.min(1, bounds.width / 1440, Math.max(320, window.innerHeight - bounds.top) / 1024)
    const canvasLeft = (bounds.width - 1440 * scale) / 2
    const x = event.clientX - bounds.left - canvasLeft
    const y = event.clientY - bounds.top

    const path = event.nativeEvent.composedPath()
    for (const node of path) {
      if (!(node instanceof HTMLElement)) continue
      if (node === event.currentTarget) break

      const text = node.textContent?.replace(/\s+/g, ' ').trim()
      if (text === 'RAGMODEX') {
        navigate('/?landing=1')
        return
      }
      if (text === 'Model' || text === 'Dataset') {
        navigate('/settings')
        return
      }
      const route = GLASS_NAV_ITEMS.find(item => item.label === text)
      if (route) {
        navigate(route.to)
        return
      }
    }

    const sidebarWidth = sidebarCollapsed ? 74 : 230
    const clickedSidebarToggle = sidebarCollapsed
      ? x < sidebarWidth * scale && y > 16 * scale && y < 58 * scale
      : x > 185 * scale && x < 230 * scale && y > 16 * scale && y < 58 * scale
    if (clickedSidebarToggle) {
      setSidebarCollapsed(current => !current)
      return
    }

    if (x > sidebarWidth * scale) return

    if (y < 70 * scale) {
      navigate('/?landing=1')
      return
    }

    if (y > 910 * scale && x < 120 * scale) {
      navigate('/settings')
    }
  }

  return (
    <div
      className={`glass-route-canvas${sidebarCollapsed ? ' glass-route-canvas--collapsed' : ''}`}
      onClick={handleClick}
    >
      <style>{`
        .glass-route-canvas {
          min-height: 100vh;
          overflow-y: auto;
          overflow-x: hidden;
        }
        .glass-route-canvas [data-scaled-wrap] {
          overflow: visible !important;
        }
        .glass-route-canvas [data-scaled-inner] {
          overflow: visible !important;
        }
        .glass-route-canvas [data-glass-sidebar] {
          height: 1024px !important;
          max-height: 1024px !important;
          overflow: hidden !important;
          flex-shrink: 0;
        }
        .glass-route-canvas [data-glass-main] {
          min-height: 0 !important;
          overflow: visible;
        }
        .glass-route-canvas [data-scaled-inner] > div > div > div:nth-child(2) > div:first-child {
          position: sticky;
          top: 0;
          height: 1024px;
          overflow: visible;
          transition: width .2s ease, flex-basis .2s ease;
        }
        .glass-route-canvas--collapsed [data-scaled-inner] > div > div > div:nth-child(2) > div:first-child {
          width: 74px !important;
          flex-basis: 74px !important;
          overflow: hidden !important;
        }
        .glass-route-canvas--collapsed [data-scaled-inner] > div > div > div:nth-child(2) > div:first-child > div:first-child {
          justify-content: center !important;
          padding-left: 0 !important;
          padding-right: 0 !important;
        }
        .glass-route-canvas--collapsed [data-scaled-inner] > div > div > div:nth-child(2) > div:first-child > div:first-child > div:first-child > div:nth-child(2) {
          display: none !important;
        }
        .glass-route-canvas--collapsed [data-scaled-inner] > div > div > div:nth-child(2) > div:first-child > div:not(:first-child):not(:last-child) {
          font-size: 0 !important;
          justify-content: center !important;
          padding-left: 0 !important;
          padding-right: 0 !important;
        }
      `}</style>
      <ScaledCanvas>{children}</ScaledCanvas>
      <button
        type="button"
        aria-label="Open settings"
        title="Settings"
        className="glass-settings-fixed"
        onClick={event => {
          event.stopPropagation()
          navigate('/settings')
        }}
      >
        <Icon name="gear" size={17} />
      </button>
      <style>{`
        .glass-settings-fixed {
          position: fixed;
          left: min(16px, 1.12vw);
          bottom: 14px;
          z-index: 50;
          width: 46px;
          height: 46px;
          display: grid;
          place-items: center;
          appearance: none;
          border: none;
          border-radius: 16px;
          background: rgba(255,255,255,0.78);
          color: ${TOKENS.accent};
          box-shadow: 0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.07), 0 8px 22px -10px rgba(15,18,28,0.35);
          backdrop-filter: blur(24px) saturate(170%);
          -webkit-backdrop-filter: blur(24px) saturate(170%);
          cursor: pointer;
        }
        .glass-settings-fixed:hover {
          background: #fff;
        }
      `}</style>
    </div>
  )
}

function glassPage(page: ReactNode) {
  return <GlassRouteCanvas>{page}</GlassRouteCanvas>
}

const ROUTES = [
  {
    path: '/',
    page: glassPage(<ChatPage />),
  },
  {
    path: 'predict',
    page: glassPage(<PredictionPage />),
  },
  {
    path: 'design',
    page: glassPage(<DesignPage />),
  },
  {
    path: 'screening',
    page: glassPage(<ScreeningPage />),
  },
  {
    path: 'evaluate',
    page: glassPage(<EvaluationPage />),
  },
  {
    path: 'visualizer',
    page: glassPage(<VisualizerPage />),
  },
  {
    path: 'settings',
    page: glassPage(<SettingsPage />),
  },
]

// ── AppInner — inside QueryClientProvider so store hooks work ─────────────────

function AppInner() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}

function AppRoutes() {
  const setModelStatus = useAppStore(s => s.setModelStatus)
  const setLlmStatus = useAppStore(s => s.setLlmStatus)
  const location = useLocation()
  const navigate = useNavigate()
  const [entered, setEntered] = useState(false)
  const statusQ = useQuery({
    queryKey: ['model-status-global'],
    queryFn: getModelStatus,
    refetchInterval: 5000,
    retry: false,
  })

  useEffect(() => {
    if (!statusQ.data) return
    setModelStatus({
      modelLoaded: !!statusQ.data.model_loaded,
      trainingData: !!statusQ.data.training_data,
      modelName: String(statusQ.data.model_name ?? ''),
      nMolecules: Number(statusQ.data.n_molecules ?? 0),
    })
    setLlmStatus({
      provider: String(statusQ.data.llm_provider ?? 'groq'),
      model: String(statusQ.data.llm_model ?? 'llama-3.3-70b-versatile'),
      temperature: Number(statusQ.data.temperature ?? 0.3),
    })
  }, [setLlmStatus, setModelStatus, statusQ.data])

  function applyStatus(status: {
    model_loaded: boolean
    training_data: boolean
    model_name: string
    n_molecules: number
    llm_provider?: string
    llm_model?: string
    temperature?: number
  }) {
    setModelStatus({
      modelLoaded: !!status.model_loaded,
      trainingData: !!status.training_data,
      modelName: String(status.model_name ?? ''),
      nMolecules: Number(status.n_molecules ?? 0),
    })
    setLlmStatus({
      provider: String(status.llm_provider ?? 'groq'),
      model: String(status.llm_model ?? 'llama-3.3-70b-versatile'),
      temperature: Number(status.temperature ?? 0.3),
    })
  }

  async function handleEnter(session?: StoredSession) {
    try {
      const status = session ? await restoreSession() : await startNewSession()
      applyStatus(status)
    } catch (err) {
      console.error('[Session enter]', err)
    }
    setEntered(true)
    navigate('/', { replace: true })
  }

  if (!entered || location.search.includes('landing=1')) {
    return <LandingPage onEnter={handleEnter} onSetup={async () => {
      try {
        const status = await startNewSession()
        applyStatus(status)
      } catch (err) {
        console.error('[Session setup]', err)
      }
      setEntered(true)
      navigate('/settings', { replace: true })
    }} />
  }

  return (
    <Routes>
      {ROUTES.map(({ path, page }) => (
        <Route
          key={path}
          path={path === '/' ? undefined : path}
          index={path === '/'}
          element={<PageErrorBoundary>{page}</PageErrorBoundary>}
        />
      ))}
    </Routes>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <TooltipProvider delayDuration={400}>
        <AppInner />
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
