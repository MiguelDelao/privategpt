/**
 * Tool Call Renderer Component
 * 
 * Displays tool execution information including parameters, results,
 * and execution status with proper formatting.
 */

import React, { useState } from 'react'
import { cn } from '@/lib/utils'
import { ToolCall } from '@/types/chat'
import { 
  ChevronDown, 
  ChevronRight, 
  Wrench, 
  CheckCircle, 
  XCircle, 
  Loader, 
  Clock,
  FileText,
  SearchIcon,
  TerminalIcon,
  DatabaseIcon
} from 'lucide-react'

interface ToolCallRendererProps {
  toolCall: ToolCall
  layout?: 'comfortable' | 'compact'
}

export function ToolCallRenderer({ toolCall, layout = 'comfortable' }: ToolCallRendererProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Get tool-specific icon and color
  const getToolConfig = (toolName: string) => {
    const configs: Record<string, { icon: any; color: string; bgColor: string }> = {
      search_documents: {
        icon: SearchIcon,
        color: 'text-blue-600 dark:text-blue-400',
        bgColor: 'bg-blue-100 dark:bg-blue-900'
      },
      read_file: {
        icon: FileText,
        color: 'text-green-600 dark:text-green-400',
        bgColor: 'bg-green-100 dark:bg-green-900'
      },
      create_file: {
        icon: FileText,
        color: 'text-purple-600 dark:text-purple-400',
        bgColor: 'bg-purple-100 dark:bg-purple-900'
      },
      edit_file: {
        icon: FileText,
        color: 'text-orange-600 dark:text-orange-400',
        bgColor: 'bg-orange-100 dark:bg-orange-900'
      },
      list_directory: {
        icon: DatabaseIcon,
        color: 'text-indigo-600 dark:text-indigo-400',
        bgColor: 'bg-indigo-100 dark:bg-indigo-900'
      },
      get_system_info: {
        icon: TerminalIcon,
        color: 'text-gray-600 dark:text-gray-400',
        bgColor: 'bg-gray-100 dark:bg-gray-800'
      },
      default: {
        icon: Wrench,
        color: 'text-gray-600 dark:text-gray-400',
        bgColor: 'bg-gray-100 dark:bg-gray-800'
      }
    }
    
    return configs[toolName] || configs.default
  }

  // Get status icon and color
  const getStatusConfig = (status?: string) => {
    switch (status) {
      case 'completed':
        return { icon: CheckCircle, color: 'text-green-500' }
      case 'failed':
        return { icon: XCircle, color: 'text-red-500' }
      case 'running':
        return { icon: Loader, color: 'text-blue-500 animate-spin' }
      case 'pending':
        return { icon: Clock, color: 'text-yellow-500' }
      default:
        return { icon: Clock, color: 'text-gray-400' }
    }
  }

  const toolConfig = getToolConfig(toolCall.function.name)
  const statusConfig = getStatusConfig(toolCall.status)
  const ToolIcon = toolConfig.icon
  const StatusIcon = statusConfig.icon

  // Parse arguments safely
  let parsedArguments: any = {}
  try {
    parsedArguments = JSON.parse(toolCall.function.arguments)
  } catch (error) {
    parsedArguments = { raw: toolCall.function.arguments }
  }

  // Format result for display
  const formatResult = (result: any) => {
    if (typeof result === 'string') {
      return result.length > 200 ? result.substring(0, 200) + '...' : result
    }
    if (typeof result === 'object') {
      return JSON.stringify(result, null, 2)
    }
    return String(result)
  }

  return (
    <div className={cn(
      'tool-call border rounded-lg',
      'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50',
      layout === 'compact' ? 'text-sm' : 'text-base'
    )}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'w-full flex items-center gap-3 p-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors rounded-t-lg',
          !isExpanded && 'rounded-b-lg'
        )}
      >
        <div className={cn('p-1.5 rounded-full', toolConfig.bgColor)}>
          <ToolIcon className={cn('w-3 h-3', toolConfig.color)} />
        </div>
        
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-800 dark:text-gray-200">
              {toolCall.function.name.replace(/_/g, ' ')}
            </span>
            
            <StatusIcon className={cn('w-3 h-3', statusConfig.color)} />
            
            {toolCall.duration && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {toolCall.duration}ms
              </span>
            )}
          </div>
          
          {/* Preview of arguments */}
          {!isExpanded && (
            <div className="text-xs text-gray-600 dark:text-gray-400 truncate">
              {Object.keys(parsedArguments).length > 0 && (
                <>
                  {Object.entries(parsedArguments).slice(0, 2).map(([key, value]) => (
                    <span key={key} className="mr-2">
                      {key}: {String(value).substring(0, 30)}
                      {String(value).length > 30 && '...'}
                    </span>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
        
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-200 dark:border-gray-700 space-y-3">
          {/* Tool Information */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Tool Execution Details
            </h4>
            <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
              <div>ID: {toolCall.id}</div>
              <div>Type: {toolCall.type}</div>
              <div>Status: <span className={statusConfig.color}>{toolCall.status || 'unknown'}</span></div>
              {toolCall.duration && <div>Duration: {toolCall.duration}ms</div>}
            </div>
          </div>

          {/* Arguments */}
          {Object.keys(parsedArguments).length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Parameters
              </h4>
              <div className="bg-gray-100 dark:bg-gray-800 rounded p-2 text-xs font-mono">
                <pre className="whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                  {JSON.stringify(parsedArguments, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Result */}
          {toolCall.result !== undefined && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Result
              </h4>
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded p-2">
                <pre className="text-xs font-mono text-green-800 dark:text-green-200 whitespace-pre-wrap">
                  {formatResult(toolCall.result)}
                </pre>
              </div>
            </div>
          )}

          {/* Error */}
          {toolCall.error && (
            <div>
              <h4 className="text-sm font-medium text-red-700 dark:text-red-300 mb-2">
                Error
              </h4>
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-2">
                <div className="text-xs text-red-800 dark:text-red-200">
                  {toolCall.error}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ToolCallRenderer