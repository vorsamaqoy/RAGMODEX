import { cn } from '../../lib/cn'

interface Props {
  children: React.ReactNode
  variant?: 'active' | 'inactive' | 'neutral' | 'warn'
  className?: string
}

export function Badge({ children, variant = 'neutral', className }: Props) {
  return (
    <span className={cn(
      'inline-flex min-h-[26px] items-center gap-2 rounded-full px-3 py-1.5 text-[12px] font-semibold leading-none tracking-normal shadow-[inset_0_1px_0_rgb(255_255_255_/_0.72),0_0_0_1px_rgb(15_18_28_/_0.04)] backdrop-blur-md',
      variant === 'active'   && 'border border-[oklch(66%_0.115_155_/_0.35)] bg-[oklch(66%_0.115_155_/_0.14)] text-[oklch(38%_0.085_155)]',
      variant === 'inactive' && 'border border-[oklch(70%_0.16_25_/_0.30)] bg-[oklch(70%_0.16_25_/_0.12)] text-[oklch(45%_0.16_25)]',
      variant === 'neutral'  && 'border border-white/70 bg-white/62 text-[oklch(38%_0.085_240)]',
      variant === 'warn'     && 'border border-[oklch(70%_0.13_60_/_0.30)] bg-[oklch(85%_0.10_60_/_0.45)] text-[oklch(40%_0.10_60)]',
      className,
    )}>
      {children}
    </span>
  )
}
