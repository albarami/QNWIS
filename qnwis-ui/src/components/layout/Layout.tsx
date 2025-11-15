import type { PropsWithChildren, ReactNode } from 'react'
import { Header } from './Header'
import { Footer } from './Footer'
import { cn } from '@/utils/cn'

interface LayoutProps extends PropsWithChildren {
  mainClassName?: string
  headerTitle?: string
  headerSubtitle?: string
  toolbar?: ReactNode
}

export const Layout = ({
  children,
  mainClassName,
  toolbar,
  headerTitle,
  headerSubtitle,
}: LayoutProps) => (
  <div className="min-h-screen bg-gray-50">
    <Header title={headerTitle} subtitle={headerSubtitle} />
    {toolbar && <div className="mx-auto max-w-6xl px-4 py-3">{toolbar}</div>}
    <main className={cn('mx-auto max-w-6xl px-4 py-6', mainClassName)}>{children}</main>
    <Footer />
  </div>
)
