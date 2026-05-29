import { type ReactNode } from 'react'

export function KBD({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex min-h-7 min-w-7 items-center justify-center rounded-[5px] border border-white/70 bg-white/62 px-2 py-1 text-[10.5px] font-mono text-text-tertiary shadow-sm">
      {children}
    </kbd>
  )
}
