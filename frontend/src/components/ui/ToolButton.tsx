import { type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface ToolButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode
  label?: string
  active?: boolean
}

export function ToolButton({ icon, label, active, className, ...rest }: ToolButtonProps) {
  return (
    <button
      className={cn(
        'flex min-h-10 items-center gap-2.5 rounded-xl border px-4 py-2.5 text-[12.5px] leading-[1.35] transition-all',
        active
          ? 'border-[oklch(66%_0.115_155_/_0.30)] bg-[oklch(66%_0.115_155_/_0.14)] text-text-primary shadow-sm'
          : 'border-transparent text-text-tertiary hover:border-white/70 hover:bg-white/62 hover:text-text-primary',
        className
      )}
      {...rest}
    >
      {icon}{label}
    </button>
  )
}
