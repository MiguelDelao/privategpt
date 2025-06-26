// PrivateGPT API Client
import { config, getConfig } from './config'
import { handleApiError, ErrorType, ErrorSeverity } from './error-handler'
import { withCircuitBreaker } from './retry-manager'

// Authentication Types
export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token?: string
  user?: {
    user_id: number
    email: string
    role: string
    name?: string
  }
}

export interface TokenVerifyResponse {
  valid: boolean
  user?: {
    user_id: number
    email: string
    role: string
    name?: string
  }
  expires_at?: string
}

// Conversation Types
export interface ConversationCreate {
  title: string
  model_name?: string
  system_prompt?: string
  data?: Record<string, any>
}

export interface ConversationUpdate {
  title?: string
  status?: 'active' | 'archived' | 'deleted'
  model_name?: string
  system_prompt?: string
  data?: Record<string, any>
}

export interface ConversationResponse {
  id: string
  title: string
  status: string
  model_name?: string
  system_prompt?: string
  data: Record<string, any>
  created_at: string
  updated_at: string
  message_count: number
}

// Message Types
export interface MessageCreate {
  content: string
  role: 'user' | 'assistant' | 'system'
  metadata?: Record<string, any>
}

export interface MessageResponse {
  id: string
  conversation_id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  metadata: Record<string, any>
  created_at: string
  tool_calls?: ToolCall[]
}

export interface ToolCall {
  id: string
  type: string
  function: {
    name: string
    arguments: string
  }
  result?: any
}

// Chat Types
export interface ChatRequest {
  message: string
  stream?: boolean
  model_name?: string
  temperature?: number
  max_tokens?: number
  use_mcp?: boolean
  available_tools?: string[]
}

export interface ChatResponse {
  text: string
  model: string
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  thinking_content?: string
  tool_calls?: ToolCall[]
}

export interface StreamingChatResponse {
  content: string
  done: boolean
  thinking_content?: string
  tool_calls?: ToolCall[]
  metadata?: Record<string, any>
}

// Model Types
export interface ModelInfo {
  id: string
  name: string
  provider: string
  description?: string
  context_window?: number
  parameters?: number
}

export interface ProviderInfo {
  name: string
  status: 'healthy' | 'unhealthy' | 'unknown'
  models: ModelInfo[]
  config?: Record<string, any>
}

// Error Types
export interface APIError {
  message: string
  code?: string
  details?: Record<string, any>
}

// Streaming Types
export interface StreamHandler {
  onMessage?: (data: StreamingChatResponse) => void
  onError?: (error: Error) => void
  onComplete?: () => void
  onStart?: () => void
}

interface RequestMetadata {
  endpoint: string
  method: string
  startTime: number
  requestId: string
}

export class PrivateGPTClient {
  private baseURL: string
  private authToken?: string
  private requestCounter = 0
  private loginTimestamp?: number
  
  constructor(baseURL: string = config.apiUrl) {
    this.baseURL = baseURL
    this.authToken = this.getStoredToken()
    
    // Use static config to avoid circular dependency
    if (config.debugMode) {
      console.log('API Client initialized')
      console.log('- Config apiUrl:', config.apiUrl)
      console.log('- BaseURL:', this.baseURL)
      console.log('- Environment:', process.env.NODE_ENV)
    }
  }

  getStoredToken(): string | undefined {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token')
      // Filter out invalid token values
      if (token && token !== 'null' && token !== 'undefined' && token.length > 10) {
        return token
      }
    }
    return undefined
  }

  private setStoredToken(token: string) {
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token)
    }
    this.authToken = token
  }

  private clearStoredToken() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
    }
    this.authToken = undefined
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${++this.requestCounter}`
  }

  private logRequest(metadata: RequestMetadata, options: RequestInit): void {
    if (config.debugMode) {
      console.group(`🌐 API Request [${metadata.requestId}]`)
      console.log('URL:', `${this.baseURL}${metadata.endpoint}`)
      console.log('Method:', metadata.method)
      console.log('Headers:', options.headers)
      if (options.body) {
        console.log('Body:', options.body)
      }
      console.groupEnd()
    }
  }

  private logResponse(metadata: RequestMetadata, response: Response, data?: any): void {
    if (config.debugMode) {
      const duration = Date.now() - metadata.startTime
      console.group(`📡 API Response [${metadata.requestId}] - ${duration}ms`)
      console.log('Status:', response.status, response.statusText)
      console.log('Headers:', Object.fromEntries(response.headers.entries()))
      if (data !== undefined) {
        console.log('Data:', data)
      }
      console.groupEnd()
    }
  }

  private logError(metadata: RequestMetadata, error: any): void {
    if (config.debugMode) {
      const duration = Date.now() - metadata.startTime
      console.group(`❌ API Error [${metadata.requestId}] - ${duration}ms`)
      console.error('Error:', error)
      console.groupEnd()
    }
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    // Skip retries for certain endpoints
    const noRetryEndpoints = ['/api/auth/logout', '/api/auth/verify']
    const shouldRetry = !noRetryEndpoints.some(ep => endpoint.includes(ep))
    
    const metadata: RequestMetadata = {
      endpoint,
      method: options.method || 'GET',
      startTime: Date.now(),
      requestId: this.generateRequestId()
    }
    
    if (!shouldRetry) {
      return this.performRequest<T>(endpoint, options, metadata)
    }

    return withCircuitBreaker(
      () => this.performRequest<T>(endpoint, options, metadata),
      `api_${metadata.method.toLowerCase()}_${endpoint.replace(/\/|\?/g, '_')}`,
      {
        retryConfig: {
          maxAttempts: 3,
          baseDelay: 1000,
          timeoutMs: 10000
        },
        circuitConfig: {
          failureThreshold: 0.9, // 90% failure rate before opening
          recoveryTimeout: 60000,
          monitoringWindow: 120000,
          volumeThreshold: 20 // Need 20 requests before considering circuit breaking
        }
      }
    )
  }

  private async performRequest<T>(
    endpoint: string,
    options: RequestInit,
    metadata: RequestMetadata
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    
    // Refresh auth token from storage before each request
    this.refreshAuthToken()
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'X-Request-ID': metadata.requestId,
      ...options.headers,
    }

    if (this.authToken) {
      headers.Authorization = `Bearer ${this.authToken}`
    } else {
      console.warn('No auth token found - requests may fail')
    }

    const requestOptions: RequestInit = {
      ...options,
      headers,
      credentials: 'include',
    }

    this.logRequest(metadata, requestOptions)

    try {
      const response = await fetch(url, requestOptions)

      let responseData: any
      
      if (!response.ok) {
        // Handle authentication errors immediately
        if (response.status === 401) {
          // Don't clear auth state if it's a conversations request right after login
          // This prevents the auth state from being cleared when the UI tries to load data
          const isConversationsRequest = url.includes('/api/chat/conversations');
          const hasJustLoggedIn = this.authToken && (Date.now() - (this.loginTimestamp || 0)) < 5000;
          
          if (!isConversationsRequest || !hasJustLoggedIn) {
            this.clearStoredToken()
            if (typeof window !== 'undefined') {
              window.dispatchEvent(new CustomEvent('auth-token-expired'))
            }
          }
        }

        // Try to extract error details from response
        let errorData: any
        let errorMessage: string
        try {
          errorData = await response.json()
          
          if (errorData.error) {
            errorMessage = errorData.error.message || `HTTP ${response.status}`
            const apiError = new APIError(
              errorMessage,
              errorData.error.code || 'API_ERROR',
              {
                status: response.status,
                type: errorData.error.type,
                details: errorData.error.details,
                suggestions: errorData.error.suggestions,
                request_id: metadata.requestId
              }
            )
            this.logError(metadata, apiError)
            throw apiError
          }
          errorMessage = errorData.message || errorData.detail || `HTTP ${response.status}`
        } catch (e) {
          if (e instanceof APIError) throw e
          errorMessage = await response.text() || `HTTP ${response.status}`
        }

        const error = new APIError(errorMessage, 'API_ERROR', { 
          status: response.status,
          request_id: metadata.requestId 
        })
        this.logError(metadata, error)
        throw error
      }

      // Handle empty responses (like 204 No Content)
      if (response.status === 204 || response.headers.get('content-length') === '0') {
        responseData = undefined
        this.logResponse(metadata, response, responseData)
        return responseData as T
      }
      
      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        const text = await response.text()
        responseData = text ? JSON.parse(text) : undefined
      } else {
        responseData = await response.text()
      }
      
      this.logResponse(metadata, response, responseData)
      return responseData as T
    } catch (error) {
      // Re-throw APIErrors as-is
      if (error instanceof APIError) {
        throw error
      }

      // Handle network and other errors
      const networkError = new APIError(
        `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'NETWORK_ERROR',
        { 
          originalError: error,
          request_id: metadata.requestId 
        }
      )
      
      this.logError(metadata, networkError)
      throw networkError
    }
  }


  // Authentication Methods
  async login(email: string, password: string): Promise<LoginResponse> {
    console.log('Login attempt - API URL:', this.baseURL)
    console.log('Full login URL:', `${this.baseURL}/api/auth/login`)
    
    const response = await this.request<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    
    this.setStoredToken(response.access_token)
    this.loginTimestamp = Date.now() // Track when we logged in
    return response
  }

  async logout(): Promise<void> {
    try {
      // Don't retry logout - if it fails, just clear local state
      await this.performRequest('/api/auth/logout', { 
        method: 'POST',
        headers: this.authToken ? {
          'Authorization': `Bearer ${this.authToken}`
        } : {}
      })
    } catch (error) {
      // Continue with logout even if API call fails
      console.warn('Logout API call failed:', error)
    } finally {
      this.clearStoredToken()
    }
  }

  async verifyToken(): Promise<TokenVerifyResponse> {
    if (!this.authToken) {
      return { valid: false }
    }

    try {
      return await this.request<TokenVerifyResponse>('/api/auth/verify', {
        method: 'POST',
      })
    } catch (error) {
      this.clearStoredToken()
      return { valid: false }
    }
  }

  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    
    this.setStoredToken(response.access_token)
    return response
  }

  // Conversation Management
  async createConversation(data: ConversationCreate): Promise<ConversationResponse> {
    return this.request<ConversationResponse>('/api/chat/conversations', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getConversations(limit = 50, offset = 0): Promise<ConversationResponse[]> {
    // Check for auth token before making request
    if (!this.authToken && typeof window !== 'undefined') {
      console.warn('No auth token, skipping conversations API call')
      return []
    }
    
    return this.request<ConversationResponse[]>(
      `/api/chat/conversations?limit=${limit}&offset=${offset}`
    )
  }

  async getConversation(conversationId: string): Promise<ConversationResponse> {
    return this.request<ConversationResponse>(`/api/chat/conversations/${conversationId}`)
  }

  async updateConversation(conversationId: string, data: ConversationUpdate): Promise<ConversationResponse> {
    return this.request<ConversationResponse>(`/api/chat/conversations/${conversationId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deleteConversation(conversationId: string, hardDelete: boolean = true): Promise<void> {
    await this.request(`/api/chat/conversations/${conversationId}?hard_delete=${hardDelete}`, {
      method: 'DELETE',
    })
  }

  // Message Management
  async getMessages(conversationId: string, limit = 50, offset = 0): Promise<MessageResponse[]> {
    return this.request<MessageResponse[]>(
      `/api/chat/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`
    )
  }

  async addMessage(conversationId: string, message: MessageCreate): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/api/chat/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify(message),
    })
  }

  // Chat Methods
  async directChat(request: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/chat/direct', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async conversationChat(conversationId: string, request: ChatRequest): Promise<ChatResponse> {
    // Convert ChatRequest to format expected by backend
    const chatRequest = {
      message: request.message,
      model: request.model_name, // Backend expects "model" not "model_name"
      temperature: request.temperature,
      max_tokens: request.max_tokens,
      use_mcp: request.use_mcp || false
    }
    
    return this.request<ChatResponse>(`/api/chat/conversations/${conversationId}/chat`, {
      method: 'POST',
      body: JSON.stringify(chatRequest),
    })
  }


  // Two-Phase Streaming Methods
  async prepareStream(conversationId: string, request: {
    message: string
    model: string  // Now required
    temperature?: number
    max_tokens?: number
  }): Promise<{
    stream_token: string
    stream_url: string
    user_message_id: string
    assistant_message_id: string
  }> {
    return this.request<{
      stream_token: string
      stream_url: string
      user_message_id: string
      assistant_message_id: string
    }>(`/api/chat/conversations/${conversationId}/prepare-stream`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  streamConversationChat(conversationId: string, request: ChatRequest, handlers: StreamHandler): EventSource {
    // Use two-phase streaming approach
    const controller = new AbortController()
    let eventSource: EventSource | null = null
    
    // Create a mock EventSource interface for compatibility
    const mockEventSource = {
      readyState: 0, // CONNECTING
      onopen: null as ((event: Event) => void) | null,
      onmessage: null as ((event: MessageEvent) => void) | null,
      onerror: null as ((event: Event) => void) | null,
      close: () => {
        controller.abort()
        if (eventSource) {
          eventSource.close()
        }
        mockEventSource.readyState = 2 // CLOSED
      },
      CONNECTING: 0,
      OPEN: 1,
      CLOSED: 2
    }

    // Start the two-phase streaming process
    this.startTwoPhaseStream(conversationId, request, handlers, controller, mockEventSource)
      .then(es => {
        eventSource = es
      })
      .catch(error => {
        handlers.onError?.(error)
        mockEventSource.readyState = 2 // CLOSED
      })
    
    return mockEventSource as EventSource
  }

  private async startTwoPhaseStream(
    conversationId: string,
    request: ChatRequest,
    handlers: StreamHandler,
    controller: AbortController,
    mockEventSource: any
  ): Promise<EventSource> {
    try {
      handlers.onStart?.()
      
      // Phase 1: Prepare the stream
      if (!request.model_name) {
        throw new Error('Model must be specified for streaming')
      }
      
      // Ensure we have fresh auth token
      this.refreshAuthToken()
      
      let prepareResponse;
      try {
        console.log('Preparing stream for conversation:', conversationId)
        console.log('Request:', {
          message: request.message,
          model: request.model_name,
          temperature: request.temperature,
          max_tokens: request.max_tokens
        })
        
        prepareResponse = await this.prepareStream(conversationId, {
          message: request.message,
          model: request.model_name,
          temperature: request.temperature,
          max_tokens: request.max_tokens
        })
        
        console.log('Prepare stream response:', prepareResponse)
      } catch (prepareError) {
        console.error('Failed to prepare streaming session:', prepareError)
        console.error('Conversation ID:', conversationId)
        console.error('Error details:', {
          message: prepareError.message,
          code: (prepareError as APIError).code,
          details: (prepareError as APIError).details
        })
        
        // Check if it's an auth error
        if ((prepareError as APIError).status === 401) {
          // Clear auth state and redirect to login
          this.clearStoredToken()
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('auth-token-expired'))
          }
          handlers.onError?.(new Error('Authentication expired. Please log in again.'))
        } else {
          // If prepare fails, we can't proceed with streaming
          handlers.onError?.(new Error(`Failed to prepare streaming session: ${prepareError.message}`))
        }
        
        mockEventSource.readyState = 2 // CLOSED
        throw prepareError
      }

      // Phase 2: Connect to the stream
      const streamUrl = `${this.baseURL}${prepareResponse.stream_url}`
      
      // Use native EventSource - no query parameters needed
      // The stream token is already in the URL path
      const eventSource = new EventSource(streamUrl)
      
      mockEventSource.readyState = 1 // OPEN
      
      // Track if we've already completed to avoid duplicate calls
      let hasCompleted = false
      
      eventSource.onopen = () => {
        console.log('Stream connected')
      }

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('Stream event:', data.type)
          
          // Handle different event types
          switch (data.type) {
            case 'content_chunk':
              handlers.onMessage?.({
                content: data.content || '',
                done: false,
                thinking_content: data.thinking_content,
                tool_calls: data.tool_calls
              })
              break
              
            case 'assistant_message_complete':
              handlers.onMessage?.({
                content: data.message?.content || '',
                done: true,
                metadata: {
                  token_count: data.message?.token_count
                }
              })
              break
              
            case 'done':
              hasCompleted = true
              handlers.onComplete?.()
              eventSource.close()
              mockEventSource.readyState = 2 // CLOSED
              break
              
            case 'error':
              handlers.onError?.(new Error(data.message || 'Stream error'))
              eventSource.close()
              mockEventSource.readyState = 2 // CLOSED
              break
              
            // Ignore other event types like stream_start, user_message, assistant_message_start
          }
        } catch (error) {
          console.error('Failed to parse stream event:', error)
        }
      }

      eventSource.onerror = (error) => {
        console.log('EventSource state change, readyState:', eventSource.readyState)
        
        // Always close the connection to prevent automatic reconnection
        eventSource.close()
        
        // Check if it's a connection error or stream ended normally
        if (eventSource.readyState === EventSource.CLOSED) {
          // Connection closed - this happens after 'done' event or on error
          // Don't treat this as an error if we've already completed
          if (!hasCompleted && mockEventSource.readyState !== 2) {
            // Only call onComplete if we haven't already
            handlers.onComplete?.()
            hasCompleted = true
          }
        } else if (!hasCompleted) {
          // This is a real error (not a normal completion)
          console.error('Stream connection failed')
          handlers.onError?.(new Error('Stream connection failed'))
        }
        
        mockEventSource.readyState = 2 // CLOSED
      }

      return eventSource
    } catch (error) {
      console.error('Two-phase streaming error:', error)
      throw error
    }
  }


  // Model and Provider Management
  async getModels(): Promise<ModelInfo[]> {
    return this.request<ModelInfo[]>('/api/llm/models')
  }

  async getProviders(): Promise<{ providers: Record<string, ProviderInfo> }> {
    return this.request<{ providers: Record<string, ProviderInfo> }>('/api/llm/providers')
  }

  // Health and Status
  async healthCheck(): Promise<{ status: string; service: string }> {
    return this.request<{ status: string; service: string }>('/health')
  }

  async getServiceStatus(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>('/status')
  }

  // User Management
  async getCurrentUser(): Promise<any> {
    return this.request('/api/users/me')
  }

  async updateCurrentUser(userData: any): Promise<any> {
    return this.request('/api/users/me', {
      method: 'PUT',
      body: JSON.stringify(userData),
    })
  }

  // Utility Methods
  isAuthenticated(): boolean {
    return !!this.authToken
  }

  getAuthToken(): string | undefined {
    return this.authToken
  }

  setAuthToken(token: string): void {
    this.setStoredToken(token)
  }
  
  refreshAuthToken(): void {
    // Refresh the auth token from localStorage
    this.authToken = this.getStoredToken()
  }
}

// Custom API Error class
export class APIError extends Error {
  public code?: string
  public status?: number
  public details?: Record<string, any>
  public suggestions?: string[]
  public request_id?: string

  constructor(message: string, code?: string, details?: Record<string, any>) {
    super(message)
    this.name = 'APIError'
    this.code = code
    this.status = details?.status
    this.details = details
    this.suggestions = details?.suggestions
    this.request_id = details?.request_id
  }

  // Get user-friendly error message with suggestions
  getUserMessage(): string {
    let message = this.message
    
    if (this.suggestions && this.suggestions.length > 0) {
      message += '\n\nSuggestions:\n' + this.suggestions.map(s => `• ${s}`).join('\n')
    }
    
    return message
  }
}

// Global client instance
export const apiClient = new PrivateGPTClient()