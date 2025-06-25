/**
 * Message Header Component
 * 
 * Displays message metadata like sender, timestamp, and status indicators.
 */

import React from 'react'
import { cn } from '@/lib/utils'
import { Message } from '@/types/chat'
import { formatDistanceToNow } from 'date-fns'
import { User, Bot, Settings, Clock, CheckCircle, AlertCircle, Loader } from 'lucide-react'

interface MessageHeaderProps {
  message: Message
  showTimestamp?: boolean
  layout?: 'comfortable' | 'compact'
}

export function MessageHeader({ message, showTimestamp = false, layout = 'comfortable' }: MessageHeaderProps) {
  const roleConfig = {
    user: {
      icon: User,
      name: 'You',
      bgColor: 'bg-blue-100 dark:bg-blue-900',
      textColor: 'text-blue-800 dark:text-blue-200'
    },
    assistant: {
      icon: Bot,
      name: 'Assistant',
      bgColor: 'bg-green-100 dark:bg-green-900',
      textColor: 'text-green-800 dark:text-green-200'
    },
    system: {
      icon: Settings,
      name: 'System',
      bgColor: 'bg-gray-100 dark:bg-gray-800',
      textColor: 'text-gray-800 dark:text-gray-200'
    }
  }

  const config = roleConfig[message.role]
  const Icon = config.icon

  const getStatusIcon = () => {
    switch (message.status) {
      case 'loading':
      case 'streaming':
        return <Loader className="w-3 h-3 animate-spin" />
      case 'complete':
        return <CheckCircle className="w-3 h-3" />
      case 'error':
        return <AlertCircle className="w-3 h-3 text-red-500" />
      default:
        return null
    }
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      if (showTimestamp) {
        return date.toLocaleString()
      }
      return formatDistanceToNow(date, { addSuffix: true })
    } catch {
      return 'Unknown time'
    }
  }

  if (layout === 'compact') {
    return (
      <div className="flex items-center gap-2 mb-2 text-xs text-gray-600 dark:text-gray-400">
        <div className={cn('p-1 rounded-full', config.bgColor)}>
          <Icon className={cn('w-3 h-3', config.textColor)} />
        </div>
        <span className="font-medium">{config.name}</span>
        {getStatusIcon()}
        <span className="ml-auto">{formatTimestamp(message.created_at)}</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-3 mb-3">
      <div className={cn('p-2 rounded-full', config.bgColor)}>
        <Icon className={cn('w-4 h-4', config.textColor)} />
      </div>
      
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className={cn('font-medium text-sm', config.textColor)}>
            {config.name}
          </span>
          
          {message.type && message.type !== 'text' && (
            <span className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 rounded-full">
              {message.type}
            </span>
          )}
          
          {getStatusIcon()}
        </div>
        
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <Clock className="w-3 h-3" />
          <span>{formatTimestamp(message.created_at)}</span>
          
          {message.metadata?.duration && (
            <span>• {message.metadata.duration}ms</span>
          )}
          
          {message.metadata?.tokenUsage && (
            <span>• {message.metadata.tokenUsage.total_tokens} tokens</span>
          )}
        </div>
      </div>
    </div>
  )
}

export default MessageHeader