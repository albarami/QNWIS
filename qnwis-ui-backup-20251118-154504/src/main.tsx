import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/common/ErrorBoundary'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
          <div className="max-w-2xl w-full bg-white rounded-2xl shadow-xl border border-red-200 p-8">
            <div className="flex items-center gap-4 mb-6">
              <div className="h-12 w-12 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">Application Error</h2>
                <p className="text-sm text-gray-600">The interface encountered an unexpected issue</p>
              </div>
            </div>
            <div className="mb-6 p-4 bg-red-50 rounded-lg border border-red-200">
              <p className="text-sm text-red-800">
                The frontend UI encountered an error. This may be due to:
              </p>
              <ul className="mt-2 ml-4 text-sm text-red-700 list-disc space-y-1">
                <li>Backend server not running or unreachable</li>
                <li>CORS configuration issue</li>
                <li>Data formatting mismatch between frontend and backend</li>
              </ul>
            </div>
            <div className="space-y-3">
              <button
                onClick={() => window.location.reload()}
                className="w-full rounded-lg bg-red-600 px-6 py-3 text-white font-semibold hover:bg-red-700 transition"
              >
                Reload Application
              </button>
              <div className="text-center text-sm text-gray-600">
                Check console (F12) for detailed error information
              </div>
            </div>
          </div>
        </div>
      }
    >
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
