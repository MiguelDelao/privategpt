/**
 * Message Renderer Component
 * 
 * Renders different types of messages with proper formatting, tool calls,
 * thinking content, and interactive features.
 */

import React, { useState, useMemo } from 'react'
import { cn } from '@/lib/utils'
import { Message, ToolCall } from '@/types/chat'
import { MessageHeader } from './MessageHeader'
import { MessageContent } from './MessageContent'
import { ThinkingContent } from './ThinkingContent'
import { ToolCallRenderer } from './ToolCallRenderer'
import { MessageActions } from './MessageActions'
import { MessageError } from './MessageError'
import { StreamingIndicator } from './StreamingIndicator'

interface MessageRendererProps {
  message: Message
  isStreaming?: boolean
  showTimestamp?: boolean
  showThinking?: boolean
  showToolCalls?: boolean
  layout?: 'comfortable' | 'compact'
  onEdit?: (messageId: string, newContent: string) => void
  onDelete?: (messageId: string) => void
  onRetry?: (messageId: string) => void
  onCopy?: (content: string) => void
  onReact?: (messageId: string, reaction: string) => void
}

export function MessageRenderer({
  message,
  isStreaming = false,
  showTimestamp = false,
  showThinking = true,
  showToolCalls = true,
  layout = 'comfortable',
  onEdit,
  onDelete,
  onRetry,
  onCopy,
  onReact
}: MessageRendererProps) {
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(!message.metadata?.isThinkingCollapsed)
  const [isEditing, setIsEditing] = useState(false)
  const [editContent, setEditContent] = useState(message.content)

  // Determine message styling based on role and status
  const messageClasses = useMemo(() => {
    const base = 'group relative'
    
    const roleClasses = {
      user: 'ml-8 md:ml-16',
      assistant: 'mr-8 md:mr-16',
      system: 'mx-4 border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20'
    }

    const layoutClasses = {
      comfortable: 'mb-6 p-4',
      compact: 'mb-3 p-2'
    }

    return cn(
      base,
      roleClasses[message.role],
      layoutClasses[layout],
      message.status === 'error' && 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'
    )
  }, [message.role, message.status, layout])

  const handleSaveEdit = () => {
    if (editContent.trim() !== message.content && onEdit) {
      onEdit(message.id, editContent.trim())
    }
    setIsEditing(false)
  }

  const handleCancelEdit = () => {
    setEditContent(message.content)
    setIsEditing(false)
  }

  return (
    <div className={messageClasses}>
      {/* Message Header */}
      <MessageHeader
        message={message}
        showTimestamp={showTimestamp}
        layout={layout}
      />

      {/* Error Display */}
      {message.status === 'error' && (
        <MessageError
          error={message.metadata?.error || 'An error occurred'}
          onRetry={onRetry ? () => onRetry(message.id) : undefined}
        />
      )}

      {/* Thinking Content */}
      {showThinking && message.thinking_content && (
        <ThinkingContent
          content={message.thinking_content}
          isExpanded={isThinkingExpanded}
          onToggle={() => setIsThinkingExpanded(!isThinkingExpanded)}
          layout={layout}
        />
      )}

      {/* Tool Calls */}
      {showToolCalls && message.tool_calls && message.tool_calls.length > 0 && (
        <div className="mb-3">
          {message.tool_calls.map((toolCall, index) => (
            <ToolCallRenderer
              key={toolCall.id || index}
              toolCall={toolCall}
              layout={layout}
            />
          ))}
        </div>
      )}

      {/* Main Message Content */}
      <div className="relative">
        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full min-h-[100px] p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:border-gray-600 dark:text-white"
              placeholder="Edit message..."
            />
            <div className="flex gap-2">
              <button
                onClick={handleSaveEdit}
                className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              >
                Save
              </button>
              <button
                onClick={handleCancelEdit}
                className="px-3 py-1 text-sm bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <>
            <MessageContent
              content={message.content}
              type={message.type}
              metadata={message.metadata}
              layout={layout}
            />
            
            {/* Streaming Indicator */}
            {isStreaming && message.status === 'streaming' && (
              <StreamingIndicator layout={layout} />
            )}
          </>
        )}
      </div>

      {/* Message Actions */}
      <MessageActions
        message={message}
        onEdit={() => setIsEditing(true)}
        onDelete={onDelete}
        onRetry={onRetry}
        onCopy={onCopy}
        onReact={onReact}
        layout={layout}
        isEditing={isEditing}
      />
    </div>
  )
}

// Export for easier imports
export default MessageRenderer