import { cn } from '../../lib/cn'
import { type ButtonHTMLAttributes, forwardRef } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg' | 'icon-sm' | 'icon-md'
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant = 'primary', size = 'md', loading, className, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        'inline-flex min-w-fit shrink-0 items-center justify-center gap-3 rounded-md text-center font-medium leading-[1.35] whitespace-nowrap',
        'transition-all duration-200 cursor-pointer select-none',
        'disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none',
        variant === 'primary'   && 'btn-glow',
        variant === 'secondary' && 'liquid-control text-text-primary hover:-translate-y-0.5 hover:shadow-[0_18px_44px_rgb(75_224_142_/_0.12)]',
        variant === 'ghost'     && 'text-text-tertiary hover:text-text-primary hover:bg-[rgb(255_244_204_/_0.08)] hover:shadow-[0_12px_28px_rgb(0_0_0_/_0.18)]',
        variant === 'danger'    && 'border border-red-400/30 bg-red-400/90 text-[#07110f] shadow-[0_16px_34px_rgb(255_93_114_/_0.18)] hover:bg-red-300',
        size === 'sm'      && 'min-h-10 px-4 py-2 text-[13.5px]',
        size === 'md'      && 'min-h-11 px-5 py-2.5 text-sm',
        size === 'lg'      && 'min-h-12 px-7 py-3 text-base',
        size === 'icon-sm' && 'h-10 w-10 p-0',
        size === 'icon-md' && 'h-11 w-11 p-0',
        className,
      )}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
      )}
      {children}
    </button>
  ),
)
Button.displayName = 'Button'
