/**
 * Message Actions Component
 * 
 * Provides interactive actions for messages like copy, edit, delete, retry, etc.
 */

import React, { useState } from 'react'
import { cn } from '@/lib/utils'
import { Message } from '@/types/chat'
import { 
  Copy, 
  Edit3, 
  Trash2, 
  RotateCcw, 
  Heart, 
  ThumbsUp, 
  ThumbsDown,
  MoreHorizontal,
  Check
} from 'lucide-react'

interface MessageActionsProps {
  message: Message
  onEdit?: () => void
  onDelete?: (messageId: string) => void
  onRetry?: (messageId: string) => void
  onCopy?: (content: string) => void
  onReact?: (messageId: string, reaction: string) => void
  layout?: 'comfortable' | 'compact'
  isEditing?: boolean
}

export function MessageActions({
  message,
  onEdit,
  onDelete,
  onRetry,
  onCopy,
  onReact,
  layout = 'comfortable',
  isEditing = false
}: MessageActionsProps) {
  const [showReactions, setShowReactions] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (onCopy) {
      onCopy(message.content)
    } else {
      try {
        await navigator.clipboard.writeText(message.content)
      } catch (error) {
        console.error('Failed to copy text:', error)
      }
    }
    
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleReact = (reaction: string) => {
    onReact?.(message.id, reaction)
    setShowReactions(false)
  }

  const reactions = [
    { emoji: '👍', name: 'like' },
    { emoji: '👎', name: 'dislike' },
    { emoji: '❤️', name: 'love' },
    { emoji: '😂', name: 'laugh' },
    { emoji: '😮', name: 'wow' },
    { emoji: '😢', name: 'sad' }
  ]

  if (isEditing) {
    return null
  }

  return (
    <div className={cn(
      'message-actions opacity-0 group-hover:opacity-100 transition-opacity duration-200',
      'flex items-center gap-1',
      layout === 'compact' ? 'mt-1' : 'mt-2'
    )}>
      {/* Copy Button */}
      <button
        onClick={handleCopy}
        className={cn(
          'p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors',
          copied && 'text-green-500'
        )}
        title="Copy message"
      >
        {copied ? (
          <Check className="w-3 h-3" />
        ) : (
          <Copy className="w-3 h-3" />
        )}
      </button>

      {/* Edit Button (for user messages) */}
      {message.role === 'user' && onEdit && (
        <button
          onClick={onEdit}
          className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          title="Edit message"
        >
          <Edit3 className="w-3 h-3" />
        </button>
      )}

      {/* Retry Button (for failed assistant messages) */}
      {message.role === 'assistant' && message.status === 'error' && onRetry && (
        <button
          onClick={() => onRetry(message.id)}
          className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-orange-500"
          title="Retry message"
        >
          <RotateCcw className="w-3 h-3" />
        </button>
      )}

      {/* React Button */}
      {onReact && (
        <div className="relative">
          <button
            onClick={() => setShowReactions(!showReactions)}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="Add reaction"
          >
            <Heart className="w-3 h-3" />
          </button>

          {/* Reactions Popup */}
          {showReactions && (
            <div className="absolute bottom-full left-0 mb-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-2 flex gap-1 z-10">
              {reactions.map((reaction) => (
                <button
                  key={reaction.name}
                  onClick={() => handleReact(reaction.name)}
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm"
                  title={reaction.name}
                >
                  {reaction.emoji}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Delete Button */}
      {onDelete && (
        <button
          onClick={() => onDelete(message.id)}
          className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-red-500"
          title="Delete message"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      )}

      {/* More Actions */}
      <button
        className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        title="More actions"
      >
        <MoreHorizontal className="w-3 h-3" />
      </button>
    </div>
  )
}

export default MessageActions