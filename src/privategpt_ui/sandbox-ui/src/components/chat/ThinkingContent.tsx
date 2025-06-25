/**
 * Thinking Content Component
 * 
 * Displays AI thinking/reasoning content with collapsible functionality.
 * Similar to DeepSeek R1 thinking display.
 */

import React from 'react'
import { cn } from '@/lib/utils'
import { ChevronDown, ChevronRight, Brain, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ThinkingContentProps {
  content: string
  isExpanded?: boolean
  onToggle?: () => void
  layout?: 'comfortable' | 'compact'
  showIcon?: boolean
}

export function ThinkingContent({
  content,
  isExpanded = false,
  onToggle,
  layout = 'comfortable',
  showIcon = true
}: ThinkingContentProps) {
  if (!content) return null

  const previewContent = content.length > 100 ? content.substring(0, 100) + '...' : content

  return (
    <div className={cn(
      'thinking-content border rounded-lg mb-3',
      'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30',
      layout === 'compact' ? 'text-sm' : 'text-base'
    )}>
      {/* Header */}
      <button
        onClick={onToggle}
        className={cn(
          'w-full flex items-center gap-2 p-3 text-left hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors rounded-t-lg',
          !isExpanded && 'rounded-b-lg'
        )}
      >
        {showIcon && (
          <div className="p-1 rounded-full bg-blue-100 dark:bg-blue-900">
            <Brain className="w-3 h-3 text-blue-600 dark:text-blue-400" />
          </div>
        )}
        
        <div className="flex items-center gap-2 flex-1">
          <span className="font-medium text-blue-800 dark:text-blue-200 text-sm">
            Thinking
          </span>
          <Sparkles className="w-3 h-3 text-blue-500 dark:text-blue-400" />
        </div>
        
        <div className="flex items-center gap-2">
          {!isExpanded && (
            <span className="text-xs text-blue-600 dark:text-blue-400 max-w-[200px] truncate">
              {previewContent}
            </span>
          )}
          
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-blue-200 dark:border-blue-800">
          <div className={cn(
            'thinking-text text-blue-800 dark:text-blue-200',
            layout === 'compact' ? 'text-xs' : 'text-sm'
          )}>
            <div className="prose prose-sm dark:prose-invert max-w-none prose-blue">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Style thinking content appropriately
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  ul: ({ children }) => <ul className="ml-4 mb-2">{children}</ul>,
                  ol: ({ children }) => <ol className="ml-4 mb-2">{children}</ol>,
                  li: ({ children }) => <li className="mb-1">{children}</li>,
                  code: ({ children }) => (
                    <code className="px-1 py-0.5 bg-blue-100 dark:bg-blue-900 rounded text-xs">
                      {children}
                    </code>
                  ),
                  pre: ({ children }) => (
                    <pre className="p-2 bg-blue-100 dark:bg-blue-900 rounded text-xs overflow-x-auto">
                      {children}
                    </pre>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-2 border-blue-300 dark:border-blue-700 pl-2 ml-2 italic">
                      {children}
                    </blockquote>
                  ),
                  h1: ({ children }) => <h1 className="text-base font-semibold mb-2">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-sm font-semibold mb-2">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-medium mb-1">{children}</h3>,
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
            
            {/* Thinking metadata */}
            <div className="mt-2 pt-2 border-t border-blue-200 dark:border-blue-800">
              <div className="text-xs text-blue-600 dark:text-blue-400 flex items-center gap-2">
                <span>Reasoning process • {content.split(/\s+/).length} words</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ThinkingContent