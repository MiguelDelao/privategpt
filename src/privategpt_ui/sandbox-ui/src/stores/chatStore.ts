import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import { apiClient } from '@/lib/api-client'
import { toastUtils, toastMessages } from '@/lib/toast'
import { handleApiError, showSuccess, showError, ErrorType, ErrorSeverity } from '@/lib/error-handler'
import {
  Conversation,
  ChatSession,
  ChatRequest,
  ChatUIState,
  ChatError,
  ModelInfo
} from '@/types/chat'

// Convert backend Conversation to frontend ChatSession
function conversationToSession(conversation: Conversation): ChatSession {
  return {
    id: conversation.id,
    title: conversation.title,
    messages: (conversation.messages || []).map(msg => ({
        id: msg.id,
        role: msg.role as 'user' | 'assistant' | 'system',
        content: msg.content,
        timestamp: msg.created_at || new Date().toISOString(),
        type: 'text' as const,
        status: 'complete' as const,
        thinking_content: msg.thinking_content,
        tool_calls: msg.tool_calls,
        metadata: {
          tokenUsage: msg.metadata?.tokenUsage
        }
      })),
    created: new Date(conversation.created_at || Date.now()),
    modified: new Date(conversation.updated_at || Date.now()),
    metadata: {
      messageCount: conversation.message_count,
      tags: conversation.data?.tags || [],
      isArchived: conversation.status === 'archived',
      isPinned: conversation.data?.isPinned || false,
      isFavorited: conversation.data?.isFavorited || false,
      defaultModel: conversation.model_name,
      enableMCP: conversation.data?.enableMCP || false,
      enabledTools: conversation.data?.enabledTools || [],
      totalTokens: conversation.data?.totalTokens,
      averageResponseTime: conversation.data?.averageResponseTime,
      totalCost: conversation.data?.totalCost,
    },
    isActive: false,
    isStreaming: false,
    currentModel: conversation.model_name,
    enabledTools: conversation.data?.enabledTools || []
  }
}

// Convert frontend ChatSession to backend Conversation update
function sessionToConversationUpdate(session: ChatSession) {
  return {
    title: session.title,
    status: session.metadata.isArchived ? 'archived' as const : 'active' as const,
    model_name: session.currentModel,
    data: {
      enableMCP: session.metadata.enableMCP,
      enabledTools: session.enabledTools,
      tags: session.metadata.tags,
      isPinned: session.metadata.isPinned,
      isFavorited: session.metadata.isFavorited,
      totalTokens: session.metadata.totalTokens,
      averageResponseTime: session.metadata.averageResponseTime,
      totalCost: session.metadata.totalCost,
    }
  }
}

// Chat message interface
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date | string
  type?: 'text'
  status?: 'loading' | 'streaming' | 'complete' | 'error'
  thinking_content?: string
  tool_calls?: ToolCall[]
  metadata?: {
    duration?: number
    tokenUsage?: TokenUsage
    error?: string
  }
}

interface ChatState {
  // Core state
  sessions: Record<string, ChatSession>
  activeSessionId: string | null
  recentSessions: string[]
  
  // UI state
  uiState: ChatUIState
  
  // Models and providers
  availableModels: ModelInfo[]
  selectedModel: string | null
  
  // Error and loading state
  error?: ChatError
  isLoading: boolean
  isSyncing: boolean // Backend sync status
  
  // Real-time streaming
  activeStreaming: Record<string, EventSource> // sessionId -> EventSource
}

interface ChatStore extends ChatState {
  // Backend Sync Methods
  syncWithBackend: () => Promise<void>
  loadConversations: (limit?: number, offset?: number) => Promise<void>
  loadConversation: (conversationId: string) => Promise<ChatSession | null>
  saveSession: (sessionId: string) => Promise<void>
  syncSession: (sessionId: string) => Promise<void>
  
  // Session Management
  createSession: (title?: string, model?: string) => Promise<string>
  deleteSession: (sessionId: string) => Promise<void>
  setActiveSession: (sessionId: string | null) => Promise<void>
  updateSessionTitle: (sessionId: string, title: string) => Promise<void>
  archiveSession: (sessionId: string) => Promise<void>
  pinSession: (sessionId: string) => Promise<void>
  duplicateSession: (sessionId: string) => Promise<string>
  
  // Message Management
  addMessage: (sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) => Promise<string>
  updateMessage: (sessionId: string, messageId: string, updates: Partial<ChatMessage>) => void
  deleteMessage: (sessionId: string, messageId: string) => void
  clearMessages: (sessionId: string) => Promise<void>
  
  // Chat Methods
  sendMessage: (sessionId: string, message: string, options?: Partial<ChatRequest>) => Promise<void>
  streamMessage: (sessionId: string, message: string, options?: Partial<ChatRequest>) => Promise<EventSource>
  stopStreaming: (sessionId: string) => void
  retryMessage: (sessionId: string, messageId: string) => Promise<void>
  
  // Message Status
  updateMessageStatus: (sessionId: string, messageId: string, status: 'loading' | 'streaming' | 'complete' | 'error') => void
  
  // Model Management
  loadModels: () => Promise<void>
  setSelectedModel: (modelId: string) => void
  getModelInfo: (modelId: string) => ModelInfo | undefined
  
  // UI State Management
  updateUIState: (updates: Partial<ChatUIState>) => void
  setInputValue: (value: string) => void
  setStreamingState: (isStreaming: boolean, messageId?: string) => void
  setError: (error: ChatError | null) => void
  clearError: () => void
  
  // Getters
  getActiveSession: () => ChatSession | undefined
  getSession: (sessionId: string) => ChatSession | undefined
  getRecentSessions: () => ChatSession[]
  getAllSessions: () => ChatSession[]
  searchSessions: (query: string) => ChatSession[]
  isSessionStreaming: (sessionId: string) => boolean
  
  // Utility
  exportSession: (sessionId: string) => string
  importSession: (sessionData: string) => Promise<string>
  getSessionStats: (sessionId: string) => { messageCount: number; wordCount: number; duration: number } | undefined
  clearAllSessions: () => Promise<void>
}

export const useChatStore = create<ChatStore>()((set, get) => ({
      // Initial state
      sessions: {},
      activeSessionId: null,
      recentSessions: [],
      
      // UI state
      uiState: {
        inputValue: '',
        isComposing: false,
        isStreaming: false,
        streamingContent: '',
        selectedMessages: [],
        showThinking: true,
        showToolCalls: true,
        isLoading: false
      },
      
      // Models and providers
      availableModels: [],
      selectedModel: null as string | null,
      
      // Error and loading state
      error: undefined,
      isLoading: false,
      isSyncing: false,
      
      // Real-time streaming
      activeStreaming: {},

      // Backend Sync Methods
      syncWithBackend: async () => {
        set({ isSyncing: true })
        try {
          // Ensure the API client has the latest auth token
          apiClient.refreshAuthToken()
          
          await get().loadConversations()
          await get().loadModels()
        } catch (error) {
          console.error('Failed to sync with backend:', error)
          toastUtils.error(toastMessages.networkError)
          get().setError({
            type: 'api',
            message: 'Failed to sync with backend',
            timestamp: new Date(),
            recoverable: true
          })
        } finally {
          set({ isSyncing: false })
        }
      },

      loadConversations: async (limit = 50, offset = 0) => {
        try {
          // Check if we have a valid auth token before making the request
          const token = apiClient.getStoredToken()
          if (!token || token === 'null' || token === 'undefined') {
            console.log('No valid auth token available, skipping conversation loading')
            return
          }
          
          // Refresh auth token if we have one
          apiClient.refreshAuthToken()
          
          const conversations = await apiClient.getConversations(limit, offset)
          const sessions: Record<string, ChatSession> = {}
          
          for (const conversation of conversations) {
            sessions[conversation.id] = conversationToSession(conversation)
          }

          set(state => ({
            sessions: { ...state.sessions, ...sessions },
            recentSessions: conversations.map(c => c.id)
          }))
        } catch (error) {
          // Only log auth errors once, don't spam
          if (error?.status === 401) {
            console.warn('Authentication failed for conversation loading')
            return
          }
          
          console.error('Failed to load conversations:', error)
          // Reduce error severity to prevent spam
          handleApiError(error, 'ChatStore.loadConversations')
        }
      },

      loadConversation: async (conversationId: string) => {
        try {
          const conversation = await apiClient.getConversation(conversationId)
          const messages = await apiClient.getMessages(conversationId)
          
          const session = conversationToSession({ ...conversation, messages })
          
          set(state => ({
            sessions: {
              ...state.sessions,
              [conversationId]: session
            }
          }))
          
          return session
        } catch (error) {
          console.error('Failed to load conversation:', error)
          handleApiError(error, 'ChatStore.loadConversation')
          return null
        }
      },

      saveSession: async (sessionId: string) => {
        const session = get().sessions[sessionId]
        if (!session) return

        try {
          const updateData = sessionToConversationUpdate(session)
          await apiClient.updateConversation(sessionId, updateData)
        } catch (error) {
          console.error('Failed to save session:', error)
          throw error
        }
      },

      syncSession: async (sessionId: string) => {
        try {
          const updatedSession = await get().loadConversation(sessionId)
          if (updatedSession) {
            set(state => ({
              sessions: {
                ...state.sessions,
                [sessionId]: updatedSession
              }
            }))
          }
        } catch (error) {
          console.error('Failed to sync session:', error)
        }
      },

      // Session Management
      createSession: async (title = 'New Chat', model) => {
        try {
          // Ensure the API client has the latest auth token
          apiClient.refreshAuthToken()
          
          // Generate a unique title using timestamp to avoid duplicates
          const timestamp = new Date().toISOString().slice(11, 19).replace(/:/g, '');
          const conversationTitle = title === 'New Chat' ? `Chat ${timestamp}` : title;
          
          const conversation = await apiClient.createConversation({
            title: conversationTitle,
            model_name: model,
            data: {
              enableMCP: false,
              enabledTools: []
            }
          })

          const session = conversationToSession(conversation)
          
          set(state => ({
            sessions: {
              ...state.sessions,
              [session.id]: session
            },
            activeSessionId: session.id,
            recentSessions: [session.id, ...state.recentSessions.filter(sid => sid !== session.id)].slice(0, 10)
          }))

          return session.id
        } catch (error) {
          console.error('Failed to create session:', error)
          handleApiError(error, 'ChatStore.createSession')
          
          // Fallback to local session creation
          const id = uuidv4()
          const now = new Date()
          
          const newSession: ChatSession = {
            id,
            title: title === 'New Chat' ? `Chat ${Object.keys(get().sessions).length + 1}` : title,
            messages: [],
            created: now,
            modified: now,
            metadata: {
              messageCount: 0,
              tags: [],
              isArchived: false,
              isPinned: false,
              isFavorited: false,
              defaultModel: model,
              enableMCP: false,
              enabledTools: []
            },
            isActive: false,
            isStreaming: false,
            currentModel: model,
            enabledTools: []
          }

          set(state => ({
            sessions: {
              ...state.sessions,
              [id]: newSession
            },
            activeSessionId: id,
            recentSessions: [id, ...state.recentSessions.filter(sid => sid !== id)].slice(0, 10)
          }))

          return id // Return the local session ID instead of throwing
        }
      },

      deleteSession: async (sessionId) => {
        try {
          await apiClient.deleteConversation(sessionId)
          showSuccess('Conversation deleted successfully')
        } catch (error) {
          console.error('Failed to delete conversation on backend:', error)
          handleApiError(error, 'ChatStore.deleteSession')
        }

        // Stop any active streaming
        get().stopStreaming(sessionId)

        set(state => {
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          const { [sessionId]: _deleted, ...remainingSessions } = state.sessions
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          const { [sessionId]: _stream, ...remainingStreams } = state.activeStreaming
          
          return {
            sessions: remainingSessions,
            activeStreaming: remainingStreams,
            activeSessionId: state.activeSessionId === sessionId ? null : state.activeSessionId,
            recentSessions: state.recentSessions.filter(id => id !== sessionId)
          }
        })
      },

      setActiveSession: async (sessionId) => {
        // Update the active session ID immediately
        set(state => ({
          activeSessionId: sessionId,
          recentSessions: [sessionId, ...state.recentSessions.filter(id => id !== sessionId)].slice(0, 10)
        }))
        
        // If sessionId is null, we're clearing the active session
        if (!sessionId) return
        
        // Check if we already have the session loaded with messages
        const existingSession = get().sessions[sessionId]
        if (existingSession && existingSession.messages.length > 0) {
          // Session already loaded with messages
          return
        }
        
        // Load the conversation from backend if not fully loaded
        try {
          await get().loadConversation(sessionId)
        } catch (error) {
          console.error('Failed to load conversation:', error)
        }
      },

      updateSessionTitle: async (sessionId, title) => {
        // Update local state immediately
        set(state => {
          const session = state.sessions[sessionId]
          if (!session) return state

          return {
            sessions: {
              ...state.sessions,
              [sessionId]: {
                ...session,
                title,
                modified: new Date()
              }
            }
          }
        })

        // Sync with backend
        try {
          await apiClient.updateConversation(sessionId, { title })
          showSuccess('Conversation renamed successfully')
        } catch (error) {
          console.error('Failed to update session title:', error)
          handleApiError(error, 'ChatStore.updateSessionTitle')
          // Could revert local changes here if needed
        }
      },

      archiveSession: async (sessionId) => {
        set(state => {
          const session = state.sessions[sessionId]
          if (!session) return state

          return {
            sessions: {
              ...state.sessions,
              [sessionId]: {
                ...session,
                metadata: {
                  ...session.metadata,
                  isArchived: !session.metadata.isArchived
                },
                modified: new Date()
              }
            }
          }
        })
      },

      pinSession: (sessionId) => {
        set(state => {
          const session = state.sessions[sessionId]
          if (!session) return state

          return {
            sessions: {
              ...state.sessions,
              [sessionId]: {
                ...session,
                metadata: {
                  ...session.metadata,
                  isPinned: !session.metadata.isPinned
                },
                modified: new Date()
              }
            }
          }
        })
      },

      duplicateSession: (sessionId) => {
        const session = get().sessions[sessionId]
        if (!session) return ''

        const newId = uuidv4()
        const now = new Date()

        const duplicatedSession: ChatSession = {
          ...session,
          id: newId,
          title: `${session.title} (Copy)`,
          created: now,
          modified: now,
          messages: session.messages.map(msg => ({
            ...msg,
            id: uuidv4(),
            timestamp: new Date(msg.timestamp || msg.created_at || Date.now())
          }))
        }

        set(state => ({
          sessions: {
            ...state.sessions,
            [newId]: duplicatedSession
          }
        }))

        return newId
      },

      // Message Management
      addMessage: async (sessionId, message) => {
        const messageId = uuidv4()
        const timestamp = new Date()

        const newMessage: ChatMessage = {
          ...message,
          id: messageId,
          timestamp
        }

        set(state => {
          const session = state.sessions[sessionId]
          if (!session) return state

          return {
            sessions: {
              ...state.sessions,
              [sessionId]: {
                ...session,
                messages: [...session.messages, newMessage],
                modified: timestamp,
                metadata: {
                  ...session.metadata,
                  messageCount: session.metadata.messageCount + 1
                }
              }
            }
          }
        })

        // Don't save messages to backend here - streaming will handle it
        // The prepare-stream endpoint creates both user and assistant messages

        return messageId
      },

      updateMessage: (sessionId, messageId, updates) => {
        set(state => {
          const session = state.sessions[sessionId]
          if (!session) return state

          return {
            sessions: {
              ...state.sessions,
              [sessionId]: {
                ...session,
                messages: session.messages.map(msg =>
                  msg.id === messageId ? { ...msg, ...updates } : msg
                ),
                modified: new Date()
              }
            }
          }
        })
      },

      deleteMessage: (sessionId, messageId) => {
        set(state => {
          const session = state.sessions[sessionId]
          if (!session) return state

          return {
            sessions: {
              ...state.sessions,
              [sessionId]: {
                ...session,
                messages: session.messages.filter(msg => msg.id !== messageId),
                modified: new Date(),
                metadata: {
                  ...session.metadata,
                  messageCount: Math.max(0, session.metadata.messageCount - 1)
                }
              }
            }
          }
        })
      },

      clearMessages: async (sessionId) => {
        set(state => {
          const session = state.sessions[sessionId]
          if (!session) return state

          return {
            sessions: {
              ...state.sessions,
              [sessionId]: {
                ...session,
                messages: [],
                modified: new Date(),
                metadata: {
                  ...session.metadata,
                  messageCount: 0
                }
              }
            }
          }
        })
        
        showSuccess('Messages cleared')
      },

      // Message Status Management

      updateMessageStatus: (sessionId, messageId, status) => {
        get().updateMessage(sessionId, messageId, {
          metadata: {
            ...get().sessions[sessionId]?.messages.find(m => m.id === messageId)?.metadata,
            status
          }
        })
      },

      // Getters
      getActiveSession: () => {
        const state = get()
        return state.activeSessionId ? state.sessions[state.activeSessionId] : undefined
      },

      getSession: (sessionId) => {
        return get().sessions[sessionId]
      },

      getRecentSessions: () => {
        const state = get()
        return state.recentSessions
          .map(id => state.sessions[id])
          .filter(session => session && !session.metadata.isArchived)
          .slice(0, 10)
      },

      getAllSessions: () => {
        return Object.values(get().sessions)
          .sort((a, b) => {
            const aTime = new Date(a.modified).getTime()
            const bTime = new Date(b.modified).getTime()
            return bTime - aTime
          })
      },

      searchSessions: (query) => {
        const sessions = get().getAllSessions()
        const searchTerm = query.toLowerCase()
        
        return sessions.filter(session =>
          session.title.toLowerCase().includes(searchTerm) ||
          session.messages.some(msg => 
            msg.content.toLowerCase().includes(searchTerm)
          ) ||
          session.metadata.tags.some(tag => 
            tag.toLowerCase().includes(searchTerm)
          )
        )
      },

      // Utility
      exportSession: (sessionId) => {
        const session = get().sessions[sessionId]
        if (!session) return ''
        
        return JSON.stringify(session, null, 2)
      },

      importSession: (sessionData) => {
        try {
          const session: ChatSession = JSON.parse(sessionData)
          const newId = uuidv4()
          
          // Ensure dates are properly converted
          const importedSession = {
            ...session,
            id: newId,
            created: new Date(session.created),
            modified: new Date(session.modified),
            messages: session.messages.map(msg => ({
              ...msg,
              timestamp: new Date(msg.timestamp || msg.created_at || Date.now())
            }))
          }

          set(state => ({
            sessions: {
              ...state.sessions,
              [newId]: importedSession
            }
          }))

          return newId
        } catch (error) {
          console.error('Failed to import session:', error)
          return ''
        }
      },

      getSessionStats: (sessionId) => {
        const session = get().sessions[sessionId]
        if (!session) return undefined

        const wordCount = session.messages.reduce((total, msg) => {
          return total + msg.content.split(/\s+/).filter(word => word.length > 0).length
        }, 0)

        const duration = new Date(session.modified).getTime() - new Date(session.created).getTime()

        return {
          messageCount: session.metadata.messageCount,
          wordCount,
          duration
        }
      },

      // Chat Methods
      sendMessage: async (sessionId, message, options = {}) => {
        // Add user message
        await get().addMessage(sessionId, {
          role: 'user',
          content: message
        })

        // Prepare chat request
        const chatRequest = {
          message,
          model_name: get().selectedModel,
          ...options
        }

        try {
          const response = await apiClient.conversationChat(sessionId, chatRequest)
          
          // Add assistant response
          // Backend returns response.response.content for conversation chat
          const assistantContent = response.response?.content || response.text || ''
          await get().addMessage(sessionId, {
            role: 'assistant',
            content: assistantContent,
            thinking_content: response.thinking_content,
            tool_calls: response.tool_calls,
            metadata: {
              tokenUsage: response.usage,
              duration: response.metadata?.response_time
            }
          })
        } catch (error) {
          console.error('Failed to send message:', error)
          handleApiError(error, 'ChatStore.sendMessage')
          
          // Add error message
          await get().addMessage(sessionId, {
            role: 'assistant',
            content: 'Sorry, I encountered an error processing your message.',
            status: 'error',
            metadata: {
              error: error instanceof Error ? error.message : 'Unknown error'
            }
          })
          
          throw error
        }
      },

      streamMessage: async (sessionId, message, options = {}) => {
        console.log('streamMessage called with sessionId:', sessionId)
        console.log('Message:', message)
        console.log('Selected model:', get().selectedModel)
        
        // Verify session exists
        const session = get().sessions[sessionId]
        if (!session) {
          console.error('Session not found:', sessionId)
          throw new Error(`Session ${sessionId} not found`)
        }
        
        // Add user message locally only - prepare-stream will handle backend
        await get().addMessage(sessionId, {
          role: 'user',
          content: message
        })

        // Add placeholder assistant message
        const assistantMessageId = await get().addMessage(sessionId, {
          role: 'assistant',
          content: '',
          status: 'streaming'
        })

        // Ensure the API client has the latest auth token
        apiClient.refreshAuthToken()
        
        // Start streaming
        const chatRequest = {
          message,
          stream: true,
          model_name: get().selectedModel,
          ...options
        }

        const eventSource = apiClient.streamConversationChat(sessionId, chatRequest, {
          onStart: () => {
            get().setStreamingState(true, assistantMessageId)
          },
          onMessage: (data) => {
            const currentMessage = get().sessions[sessionId]?.messages.find(m => m.id === assistantMessageId)
            const currentContent = currentMessage?.content || ''
            
            get().updateMessage(sessionId, assistantMessageId, {
              content: currentContent + (data.content || ''),
              thinking_content: data.thinking_content,
              tool_calls: data.tool_calls,
              status: data.done ? 'complete' : 'streaming'
            })
          },
          onComplete: () => {
            get().setStreamingState(false)
            get().updateMessage(sessionId, assistantMessageId, {
              status: 'complete'
            })
            // Remove the EventSource from activeStreaming to re-enable input
            set(state => {
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { [sessionId]: _removed, ...remaining } = state.activeStreaming
              return { activeStreaming: remaining }
            })
          },
          onError: (error) => {
            console.error('Streaming error:', error)
            handleApiError(error, 'ChatStore.streamMessage')
            get().setStreamingState(false)
            get().updateMessage(sessionId, assistantMessageId, {
              content: 'Sorry, I encountered an error while streaming the response.',
              status: 'error',
              metadata: {
                error: error.message
              }
            })
            // Remove the EventSource from activeStreaming to re-enable input
            set(state => {
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { [sessionId]: _removed, ...remaining } = state.activeStreaming
              return { activeStreaming: remaining }
            })
          }
        })

        // Store the EventSource for cleanup
        set(state => ({
          activeStreaming: {
            ...state.activeStreaming,
            [sessionId]: eventSource
          }
        }))

        return eventSource
      },

      stopStreaming: (sessionId) => {
        const state = get()
        const eventSource = state.activeStreaming[sessionId]
        
        if (eventSource) {
          eventSource.close()
          
          set(state => {
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { [sessionId]: _removed, ...remaining } = state.activeStreaming
            return {
              activeStreaming: remaining,
              uiState: {
                ...state.uiState,
                isStreaming: false,
                streamingMessageId: undefined
              }
            }
          })
        }
      },

      retryMessage: async (sessionId, messageId) => {
        const session = get().sessions[sessionId]
        if (!session) return

        const message = session.messages.find(m => m.id === messageId)
        if (!message || message.role !== 'user') return

        // Find the assistant message after this user message
        const messageIndex = session.messages.findIndex(m => m.id === messageId)
        const assistantMessage = session.messages[messageIndex + 1]
        
        if (assistantMessage && assistantMessage.role === 'assistant') {
          // Remove the failed assistant message
          get().deleteMessage(sessionId, assistantMessage.id)
        }

        // Retry with the original message
        await get().sendMessage(sessionId, message.content)
      },

      // Model Management
      loadModels: async () => {
        try {
          // Ensure the API client has the latest auth token
          apiClient.refreshAuthToken()
          
          const models = await apiClient.getModels()
          set({ availableModels: models })
          
          // Set default model if none selected
          if (!get().selectedModel && models.length > 0) {
            // Use name or model field instead of id
            const modelId = models[0].name || models[0].model || models[0].id
            set({ selectedModel: modelId })
          }
        } catch (error) {
          console.error('Failed to load models:', error)
          handleApiError(error, 'ChatStore.loadModels')
          set({ availableModels: [] })
        }
      },

      setSelectedModel: (modelId) => {
        set({ selectedModel: modelId })
      },

      getModelInfo: (modelId) => {
        return get().availableModels.find(model => model.name === modelId || model.id === modelId)
      },

      // UI State Management
      updateUIState: (updates) => {
        set(state => ({
          uiState: { ...state.uiState, ...updates }
        }))
      },

      setInputValue: (value) => {
        get().updateUIState({ inputValue: value })
      },

      setStreamingState: (isStreaming, messageId) => {
        get().updateUIState({
          isStreaming,
          streamingMessageId: messageId
        })
      },

      isSessionStreaming: (sessionId) => {
        return !!get().activeStreaming[sessionId]
      },

      clearAllSessions: async () => {
        const state = get()
        const sessionIds = Object.keys(state.sessions)
        
        // Delete all sessions from backend
        const deletePromises = sessionIds.map(async (sessionId) => {
          try {
            await apiClient.deleteConversation(sessionId, true)
          } catch (error) {
            console.error(`Failed to delete session ${sessionId}:`, error)
          }
        })
        
        // Wait for all deletions to complete
        await Promise.all(deletePromises)
        
        // Clear local state
        set({
          sessions: {},
          activeSessionId: null,
          recentSessions: [],
          activeStreaming: {}
        })
        
        showSuccess('All conversations cleared')
      },

      setError: (error) => {
        set({ error })
      },

      clearError: () => {
        set({ error: undefined })
      }
    }))