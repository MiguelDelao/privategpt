/**
 * Streaming Indicator Component
 * 
 * Shows visual feedback when a message is being streamed from the API.
 */

import React from 'react'
import { cn } from '@/lib/utils'
import { Loader2, Radio } from 'lucide-react'

interface StreamingIndicatorProps {
  layout?: 'comfortable' | 'compact'
  variant?: 'dots' | 'pulse' | 'spinner'
  className?: string
}

export function StreamingIndicator({ 
  layout = 'comfortable', 
  variant = 'dots',
  className 
}: StreamingIndicatorProps) {
  
  if (variant === 'spinner') {
    return (
      <div className={cn(
        'flex items-center gap-2 text-gray-500 dark:text-gray-400',
        layout === 'compact' ? 'text-xs mt-1' : 'text-sm mt-2',
        className
      )}>
        <Loader2 className="w-3 h-3 animate-spin" />
        <span>Generating response...</span>
      </div>
    )
  }

  if (variant === 'pulse') {
    return (
      <div className={cn(
        'flex items-center gap-2 text-gray-500 dark:text-gray-400',
        layout === 'compact' ? 'text-xs mt-1' : 'text-sm mt-2',
        className
      )}>
        <Radio className="w-3 h-3 text-green-500 animate-pulse" />
        <span>Streaming...</span>
      </div>
    )
  }

  // Default dots variant
  return (
    <div className={cn(
      'flex items-center gap-2 text-gray-500 dark:text-gray-400',
      layout === 'compact' ? 'text-xs mt-1' : 'text-sm mt-2',
      className
    )}>
      <div className="flex gap-1">
        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span className="text-xs">Generating...</span>
    </div>
  )
}

export default StreamingIndicator