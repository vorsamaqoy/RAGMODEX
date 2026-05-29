import { useNavigate } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { Btn } from '../components/ui/Btn'
import { Chip } from '../components/ui/Chip'
import { Stat } from '../components/ui/Stat'
import { KBD } from '../components/ui/KBD'
import { Donut } from '../components/ui/Donut'
import { Divider } from '../components/ui/Divider'
import { SectionLabel } from '../components/ui/SectionLabel'
import { I } from '../lib/icons'
import { useAppStore } from '../store'

const ACTIVITY = [
  { icon: <I.Chat size={16} stroke="var(--accent-blue-deep)"/>,    title: 'Explanation: feature importance for Bioactivity_RF_v1',
    sub: 'TPSA · LogP · Num_HBA — 6 turns', time: 'Today, 11:42', tag: 'Chat',  tone: 'accent' as const },
  { icon: <I.Flask size={16} stroke="var(--accent-green)"/>,   title: 'Design session — Molecule XJ-23',
    sub: '3 of 7 edits applied · prob 0.76 → 0.83',  time: 'Today, 09:18', tag: 'Design', tone: 'good' as const },
  { icon: <I.Predict size={16} stroke="var(--text-tertiary)"/>, title: 'Why was molecule MX-118 predicted negative?',
    sub: '4 turns · contributing features highlighted', time: 'Yesterday, 16:05', tag: 'Chat', tone: 'accent' as const },
  { icon: <I.Screen size={16} stroke="var(--text-tertiary)"/>,  title: 'Screened zinc_drug_like.parquet',
    sub: '248,901 molecules · 1,247 above 0.80 threshold', time: 'Yesterday, 11:02', tag: 'Screen', tone: 'default' as const },
  { icon: <I.Eval size={16} stroke="var(--text-tertiary)"/>,    title: 'Evaluation report exported',
    sub: 'PDF · ROC, calibration, confusion matrix', time: 'Mon, 15:30', tag: 'Report', tone: 'default' as const },
]

const PIPELINE = [
  { state: 'done',    label: 'Featurize MORDRED', sub: '128 descriptors', time: '11:40' },
  { state: 'done',    label: 'Predict batch',     sub: '42 molecules',    time: '11:41' },
  { state: 'running', label: 'Compute SHAP',      sub: 'TreeExplainer',   time: 'now' },
  { state: 'idle',    label: 'Rank & export',     sub: 'pending',         time: '—' },
]

export function DashboardPage() {
  const navigate = useNavigate()
  const { modelLoaded, modelName } = useAppStore()

  return (
    <div className="page-content mx-auto max-w-[1280px]">
      {/* Greeting */}
      <div className="flex items-end justify-between mb-7">
        <div>
          <div className="t-label">Welcome back</div>
          <h1 className="text-[26px] font-semibold tracking-tight mt-1">What would you like to do today?</h1>
        </div>
        <div className="flex items-center gap-2">
          <Btn variant="secondary" icon={<I.Refresh size={15}/>}>Sync dataset</Btn>
          <Btn variant="primary" icon={<I.Plus size={15}/>} onClick={() => navigate('/chat')}>New session</Btn>
        </div>
      </div>

      {/* Active model card */}
      <Card className="p-6 mb-6">
        <div className="flex items-start justify-between gap-8">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-text-tertiary">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-green)]" /> Active model
            </div>
            <div className="mt-2 flex items-baseline gap-3">
              <h2 className="text-[24px] font-semibold tracking-tight font-mono">
                {modelLoaded ? (modelName || 'Model loaded') : 'No model loaded'}
              </h2>
              <Chip tone="accent">v1.3.2</Chip>
              <Chip>Random Forest Classifier</Chip>
            </div>
            <div className="text-[13px] text-text-tertiary mt-2">Trained Aug 14 · 200 estimators · max_depth 18 · scikit-learn 1.4</div>
            <div className="grid grid-cols-4 gap-6 mt-6">
              <Stat label="Dataset" value="bioactivity" sub="bioactivity_dataset.csv" />
              <Stat label="Features" value="128" sub="MORDRED + RDKit" />
              <Stat label="Samples" value="10,532" sub="train + val + test" />
              <Stat label="Last run" value="2h ago" sub="42 predictions today" />
            </div>
          </div>

          <div className="shrink-0 flex items-center gap-6 pl-8 border-l border-border">
            <div className="text-right">
              <div className="text-[11px] uppercase tracking-wider text-text-tertiary">Performance</div>
              <div className="text-[12px] text-text-tertiary mt-1">AUC · ROC</div>
              <div className="text-[12px] text-[var(--accent-green)] mt-3 inline-flex items-center gap-1">
                <I.ArrowUpRight size={13}/> +0.04 vs v1.2
              </div>
            </div>
            <Donut value={0.87} size={92} sw={8} />
            <div className="grid grid-cols-1 gap-2.5 text-right">
              <div><div className="text-[11px] text-text-tertiary">F1</div><div className="font-mono text-[15px]">0.81</div></div>
              <div><div className="text-[11px] text-text-tertiary">Precision</div><div className="font-mono text-[15px]">0.84</div></div>
              <div><div className="text-[11px] text-text-tertiary">Recall</div><div className="font-mono text-[15px]">0.78</div></div>
            </div>
          </div>
        </div>
      </Card>

      {/* Quick actions */}
      <SectionLabel right={<button className="text-[12px] text-text-tertiary hover:text-text-primary">Customize</button>}>Quick actions</SectionLabel>
      <div className="grid grid-cols-4 gap-4 mb-8">
        <QuickAction onClick={() => navigate('/chat')}
          icon={<I.Chat size={20}/>} title="Ask Chat"
          desc="Explain predictions in natural language and explore SHAP attributions."
          kbd="C" />
        <QuickAction onClick={() => navigate('/design')}
          icon={<I.Design size={20}/>} title="Design Molecule"
          desc="Iteratively edit a structure with explainable suggestions."
          kbd="D" />
        <QuickAction onClick={() => navigate('/screening')}
          icon={<I.Screen size={20}/>} title="Screen Library"
          desc="Run the active model over a batch and rank by probability."
          kbd="S" />
        <QuickAction onClick={() => navigate('/evaluate')}
          icon={<I.Eval size={20}/>} title="Evaluate Model"
          desc="Confusion matrix, ROC, calibration and per-class metrics."
          kbd="E" />
      </div>

      {/* Activity + Pipeline */}
      <div className="grid grid-cols-3 gap-5">
        <Card className="col-span-2 p-5">
          <SectionLabel right={<button className="text-[12px] text-[var(--accent-blue-deep)] hover:underline">View all</button>}>
            Recent activity
          </SectionLabel>
          <div className="divide-y divide-border -mx-5">
            {ACTIVITY.map((a, i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-3 transition-colors hover:bg-white/55">
                <div className="inline-flex size-11 items-center justify-center rounded-md border border-white/70 bg-white/60 shadow-sm">
                  {a.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[13.5px] truncate">{a.title}</div>
                  <div className="text-[11.5px] text-text-tertiary mt-0.5 truncate">{a.sub}</div>
                </div>
                <div className="text-[11.5px] text-text-tertiary font-mono">{a.time}</div>
                <Chip tone={a.tone}>{a.tag}</Chip>
                <I.Chevron size={14} stroke="var(--text-tertiary)" />
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <SectionLabel>Pipeline status</SectionLabel>
          <div className="space-y-3">
            {PIPELINE.map((s, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="inline-flex size-9 items-center justify-center rounded-md border border-white/70 bg-white/60 shadow-sm">
                  {s.state === 'done'
                    ? <I.Check size={14} stroke="var(--accent-green)" sw={2}/>
                    : s.state === 'running'
                      ? <span className="w-2 h-2 rounded-full bg-[var(--accent-blue-deep)] animate-pulse"/>
                      : <span className="w-2 h-2 rounded-full bg-text-disabled/50"/>}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] truncate">{s.label}</div>
                  <div className="text-[11px] text-text-tertiary">{s.sub}</div>
                </div>
                <div className="font-mono text-[11.5px] text-text-tertiary">{s.time}</div>
              </div>
            ))}
          </div>
          <Divider className="my-4"/>
          <SectionLabel>Datasets</SectionLabel>
          <div className="space-y-2">
            <DatasetRow name="bioactivity_dataset.csv" rows="10,532" active />
            <DatasetRow name="zinc_drug_like.parquet" rows="248,901" />
            <DatasetRow name="kinase_panel_v2.csv" rows="3,114" />
          </div>
        </Card>
      </div>
    </div>
  )
}

function QuickAction({ icon, title, desc, kbd, onClick }: {
  icon: React.ReactNode; title: string; desc: string; kbd: string; onClick: () => void
}) {
  return (
    <button onClick={onClick}
      className="liquid-panel interactive-surface p-6 text-left transition-all group hover:border-[var(--glass-border-strong)]">
      <div className="flex items-center justify-between">
        <div className="inline-flex size-11 items-center justify-center rounded-md border border-white/70 bg-white/60 text-[var(--accent-blue-deep)] shadow-sm">
          {icon}
        </div>
        <div className="text-text-tertiary group-hover:text-[var(--accent-blue-deep)] transition-colors"><I.ArrowRight size={16}/></div>
      </div>
      <div className="mt-4 text-[15px] font-semibold">{title}</div>
      <div className="mt-2 text-[12.5px] text-text-tertiary leading-relaxed">{desc}</div>
      <div className="mt-5 inline-flex items-center gap-1 text-[11px] text-text-tertiary">
        Press <KBD>G</KBD><KBD>{kbd}</KBD>
      </div>
    </button>
  )
}

function DatasetRow({ name, rows, active }: { name: string; rows: string; active?: boolean }) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      <I.Database size={14} stroke="var(--text-tertiary)" />
      <div className="flex-1 min-w-0 truncate text-[12.5px] font-mono text-text-primary">{name}</div>
      <div className="text-[11.5px] text-text-tertiary font-mono">{rows}</div>
      {active && <Chip tone="good">active</Chip>}
    </div>
  )
}
