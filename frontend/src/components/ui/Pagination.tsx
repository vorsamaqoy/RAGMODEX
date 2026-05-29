import { ChevronLeft, ChevronRight, MoreHorizontal } from 'lucide-react'

interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}

function pageWindow(current: number, total: number): (number | 'ellipsis')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)

  const pages: (number | 'ellipsis')[] = [1]

  if (current > 3) pages.push('ellipsis')

  const lo = Math.max(2, current - 1)
  const hi = Math.min(total - 1, current + 1)
  for (let i = lo; i <= hi; i++) pages.push(i)

  if (current < total - 2) pages.push('ellipsis')

  pages.push(total)
  return pages
}

export function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  const pages = pageWindow(page, totalPages)

  const navBtn =
    'flex min-h-11 items-center gap-2 rounded-md px-5 py-2.5 text-sm font-medium text-text-tertiary transition-colors hover:bg-bg-elevated hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-40'

  const pageBtn = (active: boolean) =>
    active
      ? 'size-11 rounded-md text-sm font-semibold btn-glow text-white transition-colors'
      : 'size-11 rounded-md text-sm font-medium text-text-tertiary transition-colors hover:bg-bg-elevated hover:text-text-primary'

  return (
    <nav aria-label="Pagination" className="flex flex-wrap items-center justify-center gap-2">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className={navBtn}
        aria-label="Previous page"
      >
        <ChevronLeft size={15} />
        Previous
      </button>

      {pages.map((p, i) =>
        p === 'ellipsis' ? (
          <span
            key={`e${i}`}
            className="flex size-11 items-center justify-center text-text-tertiary"
          >
            <MoreHorizontal size={14} />
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            aria-current={p === page ? 'page' : undefined}
            className={pageBtn(p === page)}
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page === totalPages}
        className={navBtn}
        aria-label="Next page"
      >
        Next
        <ChevronRight size={15} />
      </button>
    </nav>
  )
}
