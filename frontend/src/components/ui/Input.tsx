import { cn } from '../../lib/cn'
import { type InputHTMLAttributes, forwardRef } from 'react'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'input-glass liquid-control w-full rounded-xl px-4 py-2.5 text-[14px] font-medium leading-[1.35] text-text-primary',
        'placeholder:text-text-disabled',
        'transition-all duration-150',
        className,
      )}
      {...props}
    />
  ),
)
Input.displayName = 'Input'
