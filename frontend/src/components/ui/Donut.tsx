interface DonutProps {
  value?: number
  size?: number
  sw?: number
  color?: string
  track?: string
  label?: string
}

export function Donut({ value = 0.87, size = 64, sw = 6, color = 'var(--accent-blue-deep)', track = 'rgb(8 8 8 / 0.08)', label }: DonutProps) {
  const r = (size - sw) / 2
  const c = 2 * Math.PI * r
  const off = c * (1 - value)
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={sw} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={sw}
          strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-text-primary font-semibold" style={{ fontSize: size * 0.22 }}>
        {label ?? value.toFixed(2)}
      </div>
    </div>
  )
}
