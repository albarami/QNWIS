import type { HTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export const Spinner = ({ className, ...props }: HTMLAttributes<HTMLSpanElement>) => (
  <span
    className={cn('inline-flex h-4 w-4 animate-spin text-blue-600', className)}
    {...props}
  >
    <svg viewBox="0 0 24 24" role="presentation">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
        fill="none"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4l3-3-3-3v4a10 10 0 00-10 10h4z"
      />
    </svg>
  </span>
)
