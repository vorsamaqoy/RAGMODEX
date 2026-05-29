import { cn } from '../../lib/cn'
import { type HTMLAttributes } from 'react'

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('liquid-panel overflow-hidden rounded-[20px]', className)} {...props} />
  )
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('px-6 py-5 md:px-7 md:py-5', className)}
      style={{ borderBottom: '1px solid var(--border-subtle)' }}
      {...props}
    />
  )
}

export function CardBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('px-6 py-5 md:px-7 md:py-6', className)} {...props} />
}

export function CardFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex items-center gap-4 px-6 py-5 md:px-7', className)}
      style={{ borderTop: '1px solid var(--border-subtle)' }}
      {...props}
    />
  )
}
