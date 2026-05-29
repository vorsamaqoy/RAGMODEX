interface BarProps {
  value: number
  max?: number
  color?: string
  track?: string
  height?: number
}

export function Bar({ value, max = 1, color = 'var(--accent-blue-deep)', track = 'rgb(8 8 8 / 0.08)', height = 6 }: BarProps) {
  return (
    <div className="w-full rounded-full overflow-hidden" style={{ background: track, height }}>
      <div style={{ width: `${(value / max) * 100}%`, background: color, height: '100%' }} />
    </div>
  )
}
