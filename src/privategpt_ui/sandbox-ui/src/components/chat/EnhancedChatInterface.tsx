/**
 * Enhanced Chat Interface
 * 
 * A complete chat interface that integrates all chat components with
 * real-time streaming, backend persistence, and advanced features.
 */

import React, { useEffect, useRef, useCallback, useState } from 'react'
import { cn } from '@/lib/utils'
import { useChatStore } from '@/stores/chatStore'
import { useAuthStore } from '@/stores/authStore'
import { 
  MessageRenderer, 
  ChatInput,
  MessageHeader,
  MessageContent,
  ThinkingContent,
  ToolCallRenderer,
  StreamingIndicator
} from '@/components/chat'
import { Message, ChatUIState, ModelInfo } from '@/types/chat'
import { AlertCircle, Loader2, RefreshCw, Plus, Archive, Star, MoreVertical } from 'lucide-react'

interface EnhancedChatInterfaceProps {
  sessionId?: string
  className?: string
  showSidebar?: boolean
  layout?: 'comfortable' | 'compact'
  autoCreateSession?: boolean
}

export function EnhancedChatInterface({ 
  sessionId,
  className,
  showSidebar = false,
  layout = 'comfortable',
  autoCreateSession = true
}: EnhancedChatInterfaceProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const [isUserScrolling, setIsUserScrolling] = useState(false)
  const [showScrollToBottom, setShowScrollToBottom] = useState(false)

  // Store hooks
  const { user } = useAuthStore()
  const {
    // State
    sessions,
    activeSessionId,
    uiState,
    availableModels,
    selectedModel,
    error,
    isLoading,
    isSyncing,
    activeStreaming,
    
    // Actions
    syncWithBackend,
    createSession,
    setActiveSession,
    updateSessionTitle,
    sendMessage,
    streamMessage,
    stopStreaming,
    retryMessage,
    deleteMessage,
    updateMessage,
    loadModels,
    setSelectedModel,
    updateUIState,
    setInputValue,
    clearError,
    
    // Getters
    getActiveSession,
    isSessionStreaming
  } = useChatStore()

  const currentSession = sessionId ? sessions[sessionId] : getActiveSession()
  const isStreaming = currentSession ? isSessionStreaming(currentSession.id) : false

  // Initialize chat system
  useEffect(() => {
    const initialize = async () => {
      try {
        // Sync with backend
        await syncWithBackend()

        // Do NOT auto-create sessions - sessions should only be created when user sends a message
        // if (autoCreateSession && !activeSessionId && Object.keys(sessions).length === 0) {
        //   const newSessionId = await createSession('New Chat', selectedModel)
        //   setActiveSession(newSessionId)
        // }

        // Set active session if provided
        if (sessionId && sessions[sessionId]) {
          setActiveSession(sessionId)
        }
      } catch (error) {
        console.error('Failed to initialize chat:', error)
      }
    }

    if (user) {
      initialize()
    }
  }, [user, sessionId])

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback((force = false) => {
    if (!messagesEndRef.current || (!force && isUserScrolling)) return
    
    messagesEndRef.current.scrollIntoView({ 
      behavior: 'smooth',
      block: 'end'
    })
  }, [isUserScrolling])

  useEffect(() => {
    if (currentSession && currentSession.messages.length > 0) {
      // Small delay to ensure DOM is updated
      setTimeout(() => scrollToBottom(), 100)
    }
  }, [currentSession?.messages.length, scrollToBottom])

  // Handle scroll events to detect user scrolling
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container
      const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 50
      
      setIsUserScrolling(!isAtBottom)
      setShowScrollToBottom(!isAtBottom && scrollHeight > clientHeight)
    }

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [])

  // Message handlers
  const handleSendMessage = useCallback(async (message: string, options?: any) => {
    if (!currentSession) {
      // Create new session if none exists
      if (autoCreateSession) {
        const newSessionId = await createSession('New Chat', options?.model)
        setActiveSession(newSessionId)
        // The message will be sent after the session is created
        setTimeout(() => {
          handleSendMessage(message, options)
        }, 100)
        return
      }
      return
    }

    try {
      clearError()
      
      if (options?.useStreaming !== false) {
        // Use streaming by default
        await streamMessage(currentSession.id, message, {
          model_name: options?.model || selectedModel,
          temperature: options?.temperature,
          max_tokens: options?.maxTokens,
          use_mcp: options?.useTools,
          available_tools: options?.enabledTools
        })
      } else {
        // Non-streaming fallback
        await sendMessage(currentSession.id, message, {
          model_name: options?.model || selectedModel,
          temperature: options?.temperature,
          max_tokens: options?.maxTokens,
          use_mcp: options?.useTools,
          available_tools: options?.enabledTools
        })
      }
    } catch (error) {
      console.error('Failed to send message:', error)
    }
  }, [currentSession, selectedModel, autoCreateSession, createSession, setActiveSession, streamMessage, sendMessage, clearError])

  const handleEditMessage = useCallback((messageId: string, newContent: string) => {
    if (!currentSession) return
    
    updateMessage(currentSession.id, messageId, { content: newContent })
  }, [currentSession, updateMessage])

  const handleDeleteMessage = useCallback((messageId: string) => {
    if (!currentSession) return
    
    deleteMessage(currentSession.id, messageId)
  }, [currentSession, deleteMessage])

  const handleRetryMessage = useCallback((messageId: string) => {
    if (!currentSession) return
    
    retryMessage(currentSession.id, messageId)
  }, [currentSession, retryMessage])

  const handleCopyMessage = useCallback(async (content: string) => {
    try {
      await navigator.clipboard.writeText(content)
    } catch (error) {
      console.error('Failed to copy message:', error)
    }
  }, [])

  const handleStopStreaming = useCallback(() => {
    if (currentSession) {
      stopStreaming(currentSession.id)
    }
  }, [currentSession, stopStreaming])

  // Loading state
  if (isLoading || isSyncing) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-gray-600 dark:text-gray-400">
            {isSyncing ? 'Syncing with backend...' : 'Loading chat...'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('enhanced-chat-interface flex flex-col h-full', className)}>
      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <div className="flex-1">
            <div className="font-medium text-red-800 dark:text-red-200">{error.message}</div>
            {error.recoverable && (
              <button
                onClick={() => window.location.reload()}
                className="text-sm text-red-600 dark:text-red-400 hover:underline mt-1"
              >
                Try refreshing the page
              </button>
            )}
          </div>
          <button
            onClick={clearError}
            className="text-red-500 hover:text-red-600 p-1"
          >
            ×
          </button>
        </div>
      )}

      {/* Chat Header */}
      {currentSession && (
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <h2 className="font-semibold text-lg text-gray-900 dark:text-gray-100">
              {currentSession.title}
            </h2>
            
            {currentSession.currentModel && (
              <span className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full">
                {availableModels.find(m => m.id === currentSession.currentModel)?.name || currentSession.currentModel}
              </span>
            )}

            {isStreaming && (
              <div className="flex items-center gap-2">
                <StreamingIndicator variant="pulse" layout={layout} />
                <button
                  onClick={handleStopStreaming}
                  className="px-2 py-1 text-xs bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded hover:bg-red-200 dark:hover:bg-red-800 transition-colors"
                >
                  Stop
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => updateSessionTitle(currentSession.id, prompt('New title:') || currentSession.title)}
              className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Rename conversation"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Messages Container */}
      <div 
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto px-4 py-6 space-y-6"
      >
        {currentSession?.messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-500 dark:text-gray-400 mb-4">
              Start a conversation by typing a message below
            </div>
            <div className="text-sm text-gray-400 dark:text-gray-500">
              {availableModels.find(m => m.id === selectedModel)?.name && (
                <>Using {availableModels.find(m => m.id === selectedModel)?.name}</>
              )}
            </div>
          </div>
        ) : (
          <>
            {currentSession?.messages.map((message) => (
              <MessageRenderer
                key={message.id}
                message={message}
                isStreaming={isStreaming && message.status === 'streaming'}
                showTimestamp={uiState.showTimestamps}
                showThinking={uiState.showThinking}
                showToolCalls={uiState.showToolCalls}
                layout={layout}
                onEdit={handleEditMessage}
                onDelete={handleDeleteMessage}
                onRetry={handleRetryMessage}
                onCopy={handleCopyMessage}
              />
            ))}
          </>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Scroll to Bottom Button */}
      {showScrollToBottom && (
        <div className="absolute bottom-24 right-6">
          <button
            onClick={() => scrollToBottom(true)}
            className="p-2 bg-blue-500 text-white rounded-full shadow-lg hover:bg-blue-600 transition-colors"
            title="Scroll to bottom"
          >
            ↓
          </button>
        </div>
      )}

      {/* Chat Input */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        <ChatInput
          value={uiState.inputValue}
          onChange={setInputValue}
          onSend={handleSendMessage}
          disabled={isLoading || (!currentSession && !autoCreateSession)}
          isStreaming={isStreaming}
          availableModels={availableModels}
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
          enabledTools={currentSession?.enabledTools}
          onToolsChange={(tools) => {
            if (currentSession) {
              updateMessage(currentSession.id, 'session-tools', { enabledTools: tools } as any)
            }
          }}
          placeholder={
            !currentSession && !autoCreateSession 
              ? "Select a conversation to start chatting"
              : isStreaming 
                ? "AI is responding..."
                : "Type your message..."
          }
        />
      </div>
    </div>
  )
}

export default EnhancedChatInterface