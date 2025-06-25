// Chat and Conversation Types - Aligned with Backend Models

export type MessageRole = 'user' | 'assistant' | 'system'
export type MessageType = 'text' | 'thinking' | 'search' | 'analyze' | 'code' | 'table' | 'command' | 'tool_call'
export type MessageStatus = 'loading' | 'streaming' | 'complete' | 'error'
export type ConversationStatus = 'active' | 'archived' | 'deleted'

// Core Message Interface (matches backend MessageResponse)
export interface Message {
  id: string
  conversation_id?: string
  role: MessageRole
  content: string
  type?: MessageType
  status?: MessageStatus
  created_at: string
  metadata?: MessageMetadata
  tool_calls?: ToolCall[]
  thinking_content?: string
}

// Frontend-specific message metadata
export interface MessageMetadata {
  // Thinking and reasoning
  thinkingContent?: string
  isThinkingCollapsed?: boolean
  
  // Search functionality
  searchQuery?: string
  searchResults?: SearchResult[]
  
  // Analysis
  analysisTarget?: string
  analysisType?: string
  
  // Code-related
  codeLanguage?: string
  codeOutput?: string
  
  // Tool execution
  toolExecutionId?: string
  toolExecutionStatus?: 'pending' | 'running' | 'completed' | 'failed'
  
  // Performance
  duration?: number
  tokenUsage?: TokenUsage
  
  // UI state
  isCollapsed?: boolean
  isEditing?: boolean
  isFavorited?: boolean
  
  // Error handling
  error?: string
  retryCount?: number
}

// Tool call structure (matches backend)
export interface ToolCall {
  id: string
  type: string
  function: {
    name: string
    arguments: string
  }
  result?: any
  status?: 'pending' | 'running' | 'completed' | 'failed'
  duration?: number
  error?: string
}

// Search result structure
export interface SearchResult {
  id: string
  title: string
  content: string
  score: number
  source: string
  metadata?: Record<string, any>
}

// Token usage tracking
export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cost?: number
}

// Conversation interface (matches backend ConversationResponse)
export interface Conversation {
  id: string
  title: string
  status: ConversationStatus
  model_name?: string
  system_prompt?: string
  data: Record<string, any>
  created_at: string
  updated_at: string
  message_count: number
  
  // Frontend-specific fields
  messages?: Message[]
  isLoading?: boolean
  error?: string
  
  // UI metadata
  metadata?: ConversationMetadata
}

// Frontend conversation metadata
export interface ConversationMetadata {
  tags: string[]
  isArchived: boolean
  isPinned: boolean
  isFavorited: boolean
  
  // Statistics
  totalTokens?: number
  totalCost?: number
  averageResponseTime?: number
  
  // Collaboration
  sharedWith?: string[]
  lastAccessedAt?: string
  
  // Session management
  sessionDuration?: number
  messageTypes?: Record<MessageType, number>
}

// Chat request structure (matches backend)
export interface ChatRequest {
  message: string
  stream?: boolean
  model_name?: string
  temperature?: number
  max_tokens?: number
  top_p?: number
  top_k?: number
  use_mcp?: boolean
  available_tools?: string[]
  system_prompt?: string
  conversation_id?: string
}

// Streaming response structure
export interface StreamingChatResponse {
  content: string
  done: boolean
  thinking_content?: string
  tool_calls?: ToolCall[]
  metadata?: {
    model?: string
    provider?: string
    usage?: TokenUsage
    response_time?: number
  }
  error?: string
}

// Chat session for frontend state management
export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  created: Date
  modified: Date
  metadata: ChatSessionMetadata
  
  // Real-time state
  isActive?: boolean
  isStreaming?: boolean
  currentModel?: string
  enabledTools?: string[]
}

// Frontend session metadata
export interface ChatSessionMetadata {
  messageCount: number
  totalTokens?: number
  tags: string[]
  isArchived: boolean
  isPinned: boolean
  isFavorited: boolean
  
  // Settings
  defaultModel?: string
  defaultTemperature?: number
  enableMCP?: boolean
  enabledTools?: string[]
  
  // Statistics
  sessionDuration?: number
  averageResponseTime?: number
  totalCost?: number
}

// Model and provider types
export interface ModelInfo {
  id: string
  name: string
  provider: string
  description?: string
  context_window?: number
  parameters?: number
  pricing?: {
    input_cost_per_token?: number
    output_cost_per_token?: number
  }
  capabilities?: string[]
  status?: 'available' | 'unavailable' | 'loading'
}

export interface ProviderInfo {
  name: string
  status: 'healthy' | 'unhealthy' | 'unknown'
  models: ModelInfo[]
  config?: {
    api_key_configured?: boolean
    base_url?: string
    rate_limits?: Record<string, any>
  }
  health_check_at?: string
}

// Chat UI state
export interface ChatUIState {
  // Input state
  inputValue: string
  isComposing: boolean
  
  // Streaming state
  isStreaming: boolean
  streamingMessageId?: string
  streamingContent: string
  
  // Selection state
  selectedMessages: string[]
  selectedModel?: string
  
  // UI preferences
  showThinking: boolean
  showToolCalls: boolean
  showTimestamps: boolean
  messageLayout: 'comfortable' | 'compact'
  
  // Errors and loading
  error?: string
  isLoading: boolean
  
  // Advanced features
  enableAutoSave: boolean
  enableNotifications: boolean
  enableSyntaxHighlighting: boolean
}

// Error types
export interface ChatError {
  type: 'network' | 'api' | 'validation' | 'permission' | 'rate_limit' | 'unknown'
  message: string
  code?: string
  details?: Record<string, any>
  timestamp: Date
  conversationId?: string
  messageId?: string
  recoverable: boolean
}

// Export utility types
export type ChatEventType = 'message_sent' | 'message_received' | 'streaming_started' | 'streaming_ended' | 'error_occurred' | 'conversation_created' | 'conversation_updated'

export interface ChatEvent {
  type: ChatEventType
  payload: any
  timestamp: Date
  conversationId?: string
  messageId?: string
}

// Legacy compatibility - will be removed
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  isStreaming?: boolean
  isComplete?: boolean
}

export interface ChatState {
  messages: ChatMessage[]
  isStreaming: boolean
  currentTool: 'none' | 'demo-chat' | 'command-loading' | 'command-complete'
  toolFadeState: '' | 'fade-out' | 'fade-in'
}

export type ToolAction = 'start-demo' | 'start-command' | 'complete-tool' | 'clear-tool'