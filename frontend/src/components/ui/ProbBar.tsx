interface Props {
  label?: string
  value: number
  color?: string
  compact?: boolean
  showPrediction?: boolean
}

export function ProbBar({
  label = 'P(active)',
  value,
  compact = false,
  showPrediction = false,
}: Props) {
  const pct = Math.max(0, Math.min(100, value * 100))
  const active = value >= 0.5
  const color = value >= 0.7
    ? 'oklch(66% 0.115 155)'
    : value >= 0.4
      ? 'oklch(78% 0.14 70)'
      : 'oklch(70% 0.16 25)'
  const gradientEnd = value >= 0.7
    ? 'oklch(74% 0.13 195)'
    : value >= 0.4
      ? 'oklch(84% 0.13 92)'
      : 'oklch(78% 0.11 55)'

  return (
    <div className={compact ? 'space-y-1.5' : 'space-y-2'}>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="text-text-tertiary">{label}</span>
        <span style={{ color }} className="font-mono font-semibold tabular-nums">
          {pct.toFixed(compact ? 1 : 2)}%
        </span>
      </div>
      <div
        className={compact ? 'relative h-2.5 rounded-full bg-[rgb(15_18_28_/_0.06)]' : 'relative h-4 rounded-full bg-[rgb(15_18_28_/_0.06)]'}
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}, ${gradientEnd})` }}
        />
        <div className="absolute inset-y-[-3px] left-1/2 w-px bg-black/20" />
        <div
          className={compact
            ? 'absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-[0_2px_8px_rgb(8_8_8_/_0.22)] transition-all duration-500'
            : 'absolute top-1/2 size-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-white shadow-[0_4px_14px_rgb(8_8_8_/_0.24)] transition-all duration-500'}
          style={{ left: `${pct}%`, background: color }}
        />
      </div>
      {!compact && (
        <div className="flex items-center justify-between text-[10px] font-medium text-text-disabled">
          <span>0%</span>
          <span className="text-text-tertiary">50%</span>
          <span>100%</span>
        </div>
      )}
      {showPrediction && !compact && (
        <p className="text-xs text-text-tertiary">
          {active ? 'Predicted active' : 'Predicted inactive'} at threshold 50%.
        </p>
      )}
    </div>
  )
}
