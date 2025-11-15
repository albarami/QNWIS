import type { FormEvent } from 'react'
import { Button } from '@/components/common/Button'

interface QueryInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (value: string) => Promise<void> | void
  onStop: () => void
  isStreaming: boolean
  history: string[]
}

export const QueryInput = ({
  value,
  onChange,
  onSubmit,
  onStop,
  isStreaming,
  history,
}: QueryInputProps) => {
  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!value.trim() || isStreaming) return
    await onSubmit(value.trim())
  }

  return (
    <div className="bg-white rounded-xl shadow p-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Enter Ministerial Query
          </label>
          <div className="flex gap-3">
            <input
              type="text"
              value={value}
              onChange={(event) => onChange(event.target.value)}
              disabled={isStreaming}
              placeholder="e.g., What is the unemployment rate trend across GCC?"
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
            {!isStreaming ? (
              <Button type="submit" disabled={!value.trim()}>
                Analyze
              </Button>
            ) : (
              <Button type="button" variant="danger" onClick={onStop}>
                Stop
              </Button>
            )}
          </div>
        </div>
      </form>

      {history.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-gray-500 mb-2">Recent queries</p>
          <div className="flex flex-wrap gap-2">
            {history.map((entry, idx) => (
              <button
                key={`${entry}-${idx}`}
                type="button"
                onClick={() => onChange(entry)}
                disabled={isStreaming}
                className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700 hover:bg-gray-200 disabled:opacity-50"
              >
                {entry.length > 56 ? `${entry.slice(0, 56)}…` : entry}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
