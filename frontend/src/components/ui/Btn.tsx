import { cn } from '../../lib/cn'
import { type ButtonHTMLAttributes, type ReactNode } from 'react'

interface BtnProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline' | 'danger' | 'success'
  size?: 'sm' | 'md' | 'lg'
  icon?: ReactNode
  iconRight?: ReactNode
}

const sizes = {
  sm: 'min-h-9 px-3.5 py-2 text-[12.5px] gap-2',
  md: 'min-h-10 px-4 py-2.5 text-[13.5px] gap-2.5',
  lg: 'min-h-11 px-5 py-3 text-[14px] gap-3',
}

const variants = {
  primary:  'btn-glow',
  secondary:'liquid-control text-text-primary hover:-translate-y-0.5',
  ghost:    'text-text-tertiary hover:bg-white/70 hover:text-text-primary',
  outline:  'liquid-control bg-transparent text-text-primary',
  danger:   'border border-[oklch(70%_0.16_25_/_0.30)] bg-[oklch(70%_0.16_25_/_0.12)] text-[oklch(45%_0.16_25)] hover:bg-[oklch(70%_0.16_25_/_0.16)]',
  success:  'border border-[oklch(66%_0.115_155_/_0.30)] bg-[oklch(66%_0.115_155_/_0.14)] text-[oklch(38%_0.085_155)] hover:bg-[oklch(66%_0.115_155_/_0.18)]',
}

export function Btn({ children, variant = 'ghost', size = 'md', className = '', icon, iconRight, ...rest }: BtnProps) {
  return (
    <button
      className={cn(
        'inline-flex min-w-fit items-center justify-center rounded-xl text-center font-medium leading-[1.35] transition-all duration-200',
        sizes[size],
        variants[variant],
        className
      )}
      {...rest}
    >
      {icon}{children}{iconRight}
    </button>
  )
}
