interface ErrorBannerProps {
  message: string
  onRetry?: () => void
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  if (!message) {
    return null
  }

  return (
    <div className="rounded-2xl border border-red-500/50 bg-red-500/10 text-red-200 p-4 flex items-center justify-between" data-testid="error-banner">
      <div>
        <p className="text-sm uppercase tracking-[0.3em]">Critical Error</p>
        <p className="text-base text-red-100 font-semibold">{message}</p>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-xl border border-red-400 px-4 py-2 text-sm font-semibold hover:bg-red-500/20"
        >
          Retry
        </button>
      )}
    </div>
  )
}
