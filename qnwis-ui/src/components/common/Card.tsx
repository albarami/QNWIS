import type { PropsWithChildren, ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface CardProps extends PropsWithChildren {
  className?: string
  title?: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
}

export const Card = ({ className, children, title, subtitle, actions }: CardProps) => (
  <section className={cn('bg-white rounded-xl shadow p-6', className)}>
    {(title || subtitle || actions) && (
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          {title && <h3 className="text-lg font-semibold text-gray-900">{title}</h3>}
          {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
        </div>
        {actions}
      </header>
    )}
    {children}
  </section>
)
