interface MiniMolProps {
  size?: number
}

export function MiniMol({ size = 80 }: MiniMolProps) {
  const s = size
  const cx = s / 2
  const cy = s / 2
  const r = s * 0.34
  const nodes = [
    { x: cx, y: cy - r },
    { x: cx + r * 0.87, y: cy - r * 0.5 },
    { x: cx + r * 0.87, y: cy + r * 0.5 },
    { x: cx, y: cy + r },
    { x: cx - r * 0.87, y: cy + r * 0.5 },
    { x: cx - r * 0.87, y: cy - r * 0.5 },
  ]
  const bonds = [[0,1],[1,2],[2,3],[3,4],[4,5],[5,0],[0,3],[1,4]]
  return (
    <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`}>
      {bonds.map(([a, b], i) => (
        <line key={i}
          x1={nodes[a].x} y1={nodes[a].y}
          x2={nodes[b].x} y2={nodes[b].y}
          stroke="var(--color-border)" strokeWidth={1.5} strokeLinecap="round"
        />
      ))}
      {nodes.map((n, i) => (
        <circle key={i} cx={n.x} cy={n.y} r={s * 0.055}
          fill={i === 0 ? 'var(--accent-blue-deep)' : i === 3 ? 'var(--accent-red)' : 'var(--text-disabled)'}
        />
      ))}
    </svg>
  )
}
