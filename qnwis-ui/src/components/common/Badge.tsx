import type { HTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

type BadgeTone = 'default' | 'success' | 'warning' | 'danger' | 'info'

const toneClasses: Record<BadgeTone, string> = {
  default: 'bg-gray-100 text-gray-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  danger: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
}

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
}

export const Badge = ({ tone = 'default', className, ...props }: BadgeProps) => (
  <span
    className={cn('rounded-full px-3 py-1 text-xs font-medium', toneClasses[tone], className)}
    {...props}
  />
)
