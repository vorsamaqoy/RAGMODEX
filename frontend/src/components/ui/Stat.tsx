interface StatProps {
  label: string
  value: string | number
  sub?: string
  tone?: 'default' | 'good' | 'bad'
}

export function Stat({ label, value, sub, tone = 'default' }: StatProps) {
  const c = tone === 'good' ? 'text-[var(--accent-green)]' : tone === 'bad' ? 'text-[var(--accent-red)]' : 'text-text-primary'
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-text-tertiary">{label}</div>
      <div className={`text-[20px] font-semibold mt-1 ${c} font-mono tracking-tight`}>{value}</div>
      {sub && <div className="text-[12px] text-text-tertiary mt-0.5">{sub}</div>}
    </div>
  )
}
