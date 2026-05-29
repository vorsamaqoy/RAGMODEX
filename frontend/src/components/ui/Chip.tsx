import { cn } from '../../lib/cn'
import { type HTMLAttributes } from 'react'

interface ChipProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: 'default' | 'accent' | 'good' | 'bad' | 'plain'
}

const tones = {
  default: 'border-white/70 bg-white/62 text-text-tertiary',
  accent:  'border-[oklch(66%_0.115_240_/_0.30)] bg-[oklch(66%_0.115_240_/_0.12)] text-[oklch(38%_0.085_240)]',
  good:    'border-[oklch(66%_0.115_155_/_0.30)] bg-[oklch(66%_0.115_155_/_0.14)] text-[oklch(38%_0.085_155)]',
  bad:     'border-[oklch(70%_0.16_25_/_0.28)] bg-[oklch(70%_0.16_25_/_0.12)] text-[oklch(45%_0.16_25)]',
  plain:   'border-white/60 bg-transparent text-text-tertiary',
}

export function Chip({ children, tone = 'default', className, ...rest }: ChipProps) {
  return (
    <span
      className={cn(
        'inline-flex min-h-[26px] items-center gap-2 rounded-full border px-3 py-1.5 text-[11.5px] font-medium leading-none shadow-[inset_0_1px_0_rgb(255_255_255_/_0.72)] backdrop-blur-md',
        tones[tone],
        className
      )}
      {...rest}
    >
      {children}
    </span>
  )
}
