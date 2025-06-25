/**
 * Message Error Component
 * 
 * Displays error messages with retry functionality and error details.
 */

import React, { useState } from 'react'
import { cn } from '@/lib/utils'
import { AlertTriangle, RotateCcw, ChevronDown, ChevronRight, Info } from 'lucide-react'

interface MessageErrorProps {
  error: string
  onRetry?: () => void
  details?: Record<string, any>
  className?: string
}

export function MessageError({ error, onRetry, details, className }: MessageErrorProps) {
  const [showDetails, setShowDetails] = useState(false)

  return (
    <div className={cn(
      'message-error bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-3',
      className
    )}>
      {/* Error Header */}
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
        
        <div className="flex-1">
          <div className="font-medium text-red-800 dark:text-red-200 text-sm">
            Error occurred
          </div>
          <div className="text-red-700 dark:text-red-300 text-sm mt-1">
            {error}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Retry Button */}
          {onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-800 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Retry
            </button>
          )}

          {/* Details Toggle */}
          {details && Object.keys(details).length > 0 && (
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="p-1 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900 rounded transition-colors"
              title="Show error details"
            >
              {showDetails ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Error Details */}
      {showDetails && details && (
        <div className="mt-3 pt-3 border-t border-red-200 dark:border-red-800">
          <div className="flex items-center gap-2 text-xs text-red-600 dark:text-red-400 mb-2">
            <Info className="w-3 h-3" />
            <span className="font-medium">Error Details</span>
          </div>
          
          <div className="bg-red-100 dark:bg-red-900/40 rounded p-2 text-xs font-mono">
            <pre className="text-red-800 dark:text-red-200 whitespace-pre-wrap overflow-x-auto">
              {JSON.stringify(details, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Common Error Solutions */}
      <div className="mt-2 text-xs text-red-600 dark:text-red-400">
        <div className="flex items-center gap-1">
          <Info className="w-3 h-3" />
          <span>
            {error.toLowerCase().includes('network') && 'Check your internet connection and try again.'}
            {error.toLowerCase().includes('auth') && 'Please log in again to continue.'}
            {error.toLowerCase().includes('rate') && 'Too many requests. Please wait a moment and try again.'}
            {!error.toLowerCase().includes('network') && 
             !error.toLowerCase().includes('auth') && 
             !error.toLowerCase().includes('rate') && 
             'This appears to be a temporary issue. Please try again.'}
          </span>
        </div>
      </div>
    </div>
  )
}

export default MessageError