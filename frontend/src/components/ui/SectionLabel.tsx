import { cn } from '../../lib/cn'
import { type ReactNode } from 'react'

interface SectionLabelProps {
  children: ReactNode
  right?: ReactNode
  className?: string
}

export function SectionLabel({ children, right = null, className }: SectionLabelProps) {
  return (
    <div className={cn('flex items-center justify-between mb-3', className)}>
      <div className="text-[11px] uppercase tracking-[0.14em] text-text-tertiary font-medium">{children}</div>
      {right}
    </div>
  )
}
