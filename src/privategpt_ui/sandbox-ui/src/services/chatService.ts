/**
 * Chat Service Layer
 * 
 * Provides a clean abstraction between UI components and the backend API.
 * Handles business logic, error handling, and data transformation.
 */

import { apiClient, APIError } from '@/lib/api-client'
import {
  ChatRequest,
  ChatResponse,
  StreamingChatResponse,
  StreamHandler,
  ModelInfo,
  ProviderInfo,
  Message,
  Conversation,
  ChatError
} from '@/types/chat'

export class ChatService {
  private static instance: ChatService
  private abortControllers: Map<string, AbortController> = new Map()

  static getInstance(): ChatService {
    if (!ChatService.instance) {
      ChatService.instance = new ChatService()
    }
    return ChatService.instance
  }

  /**
   * Model Management
   */
  async getAvailableModels(): Promise<ModelInfo[]> {
    try {
      const response = await apiClient.getModels()
      return response.models
    } catch (error) {
      throw this.handleError('Failed to load models', error)
    }
  }

  async getProviders(): Promise<Record<string, ProviderInfo>> {
    try {
      const response = await apiClient.getProviders()
      return response.providers
    } catch (error) {
      throw this.handleError('Failed to load providers', error)
    }
  }

  /**
   * Conversation Management
   */
  async createConversation(title: string, modelName?: string): Promise<Conversation> {
    try {
      return await apiClient.createConversation({
        title,
        model_name: modelName,
        data: {}
      })
    } catch (error) {
      throw this.handleError('Failed to create conversation', error)
    }
  }

  async getConversations(limit = 50, offset = 0): Promise<Conversation[]> {
    try {
      return await apiClient.getConversations(limit, offset)
    } catch (error) {
      throw this.handleError('Failed to load conversations', error)
    }
  }

  async getConversation(conversationId: string): Promise<Conversation> {
    try {
      return await apiClient.getConversation(conversationId)
    } catch (error) {
      throw this.handleError('Failed to load conversation', error)
    }
  }

  async updateConversation(conversationId: string, updates: Partial<Conversation>): Promise<Conversation> {
    try {
      return await apiClient.updateConversation(conversationId, updates)
    } catch (error) {
      throw this.handleError('Failed to update conversation', error)
    }
  }

  async deleteConversation(conversationId: string): Promise<void> {
    try {
      await apiClient.deleteConversation(conversationId)
    } catch (error) {
      throw this.handleError('Failed to delete conversation', error)
    }
  }

  /**
   * Message Management
   */
  async getMessages(conversationId: string, limit = 50, offset = 0): Promise<Message[]> {
    try {
      return await apiClient.getMessages(conversationId, limit, offset)
    } catch (error) {
      throw this.handleError('Failed to load messages', error)
    }
  }

  async addMessage(conversationId: string, content: string, role: 'user' | 'assistant' | 'system' = 'user'): Promise<Message> {
    try {
      return await apiClient.addMessage(conversationId, {
        content,
        role,
        metadata: {}
      })
    } catch (error) {
      throw this.handleError('Failed to add message', error)
    }
  }

  /**
   * Chat Methods
   */
  async sendDirectMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      return await apiClient.directChat(request)
    } catch (error) {
      throw this.handleError('Failed to send message', error)
    }
  }

  async sendConversationMessage(conversationId: string, request: ChatRequest): Promise<ChatResponse> {
    try {
      return await apiClient.conversationChat(conversationId, request)
    } catch (error) {
      throw this.handleError('Failed to send conversation message', error)
    }
  }

  /**
   * Streaming Chat Methods
   */
  streamConversationMessage(conversationId: string, request: ChatRequest, handlers: StreamHandler): EventSource {
    const eventSource = apiClient.streamConversationChat(conversationId, request, {
      ...handlers,
      onError: (error) => {
        const chatError = this.handleError('Streaming error', error)
        handlers.onError?.(chatError)
      }
    })

    return eventSource
  }

  /**
   * Advanced Chat Features
   */
  async sendMessageWithThinking(
    conversationId: string,
    message: string,
    options: Partial<ChatRequest> = {}
  ): Promise<{ response: ChatResponse; thinkingContent?: string }> {
    try {
      const request: ChatRequest = {
        message,
        model_name: options.model_name,
        temperature: options.temperature,
        max_tokens: options.max_tokens,
        use_mcp: false,
        ...options
      }

      const response = await this.sendConversationMessage(conversationId, request)
      
      return {
        response,
        thinkingContent: response.thinking_content
      }
    } catch (error) {
      throw this.handleError('Failed to send message with thinking', error)
    }
  }

  async sendMessageWithTools(
    conversationId: string,
    message: string,
    tools: string[] = [],
    options: Partial<ChatRequest> = {}
  ): Promise<ChatResponse> {
    try {
      const request: ChatRequest = {
        message,
        use_mcp: true,
        available_tools: tools,
        model_name: options.model_name,
        temperature: options.temperature,
        max_tokens: options.max_tokens,
        ...options
      }

      return await this.sendConversationMessage(conversationId, request)
    } catch (error) {
      throw this.handleError('Failed to send message with tools', error)
    }
  }

  /**
   * Batch Operations
   */
  async bulkDeleteConversations(conversationIds: string[]): Promise<{ success: string[]; failed: string[] }> {
    const success: string[] = []
    const failed: string[] = []

    await Promise.allSettled(
      conversationIds.map(async (id) => {
        try {
          await this.deleteConversation(id)
          success.push(id)
        } catch (error) {
          console.error(`Failed to delete conversation ${id}:`, error)
          failed.push(id)
        }
      })
    )

    return { success, failed }
  }

  async exportConversation(conversationId: string): Promise<string> {
    try {
      const conversation = await this.getConversation(conversationId)
      const messages = await this.getMessages(conversationId)
      
      const exportData = {
        conversation,
        messages,
        exportedAt: new Date().toISOString(),
        version: '1.0'
      }

      return JSON.stringify(exportData, null, 2)
    } catch (error) {
      throw this.handleError('Failed to export conversation', error)
    }
  }

  /**
   * Health and Status
   */
  async checkHealth(): Promise<{ status: string; service: string }> {
    try {
      return await apiClient.healthCheck()
    } catch (error) {
      throw this.handleError('Health check failed', error)
    }
  }

  async getServiceStatus(): Promise<Record<string, any>> {
    try {
      return await apiClient.getServiceStatus()
    } catch (error) {
      throw this.handleError('Failed to get service status', error)
    }
  }

  /**
   * Utility Methods
   */
  validateChatRequest(request: Partial<ChatRequest>): { valid: boolean; errors: string[] } {
    const errors: string[] = []

    if (!request.message || request.message.trim().length === 0) {
      errors.push('Message cannot be empty')
    }

    if (request.message && request.message.length > 10000) {
      errors.push('Message is too long (max 10,000 characters)')
    }

    if (request.temperature !== undefined && (request.temperature < 0 || request.temperature > 2)) {
      errors.push('Temperature must be between 0 and 2')
    }

    if (request.max_tokens !== undefined && (request.max_tokens < 1 || request.max_tokens > 100000)) {
      errors.push('Max tokens must be between 1 and 100,000')
    }

    return {
      valid: errors.length === 0,
      errors
    }
  }

  formatMessageForDisplay(message: Message): {
    content: string
    timestamp: string
    hasThinking: boolean
    hasToolCalls: boolean
  } {
    return {
      content: message.content,
      timestamp: new Date(message.created_at).toLocaleString(),
      hasThinking: !!message.thinking_content,
      hasToolCalls: !!(message.tool_calls && message.tool_calls.length > 0)
    }
  }

  /**
   * Error Handling
   */
  private handleError(context: string, error: unknown): ChatError {
    console.error(`${context}:`, error)

    if (error instanceof APIError) {
      return {
        type: this.mapAPIErrorType(error.code),
        message: `${context}: ${error.message}`,
        code: error.code,
        details: error.details,
        timestamp: new Date(),
        recoverable: this.isRecoverableError(error)
      }
    }

    if (error instanceof Error) {
      return {
        type: 'unknown',
        message: `${context}: ${error.message}`,
        timestamp: new Date(),
        recoverable: true
      }
    }

    return {
      type: 'unknown',
      message: `${context}: Unknown error occurred`,
      timestamp: new Date(),
      recoverable: true
    }
  }

  private mapAPIErrorType(code?: string): ChatError['type'] {
    switch (code) {
      case 'AUTH_ERROR':
        return 'permission'
      case 'NETWORK_ERROR':
        return 'network'
      case 'API_ERROR':
        return 'api'
      case 'VALIDATION_ERROR':
        return 'validation'
      case 'RATE_LIMIT_ERROR':
        return 'rate_limit'
      default:
        return 'unknown'
    }
  }

  private isRecoverableError(error: APIError): boolean {
    // Network errors and temporary API errors are generally recoverable
    return error.code === 'NETWORK_ERROR' || 
           (error.details?.status && error.details.status >= 500)
  }

  /**
   * Cleanup
   */
  cleanup(): void {
    // Cancel any pending abort controllers
    this.abortControllers.forEach(controller => controller.abort())
    this.abortControllers.clear()
  }
}

// Export singleton instance
export const chatService = ChatService.getInstance()

// Export specific service functions for convenience
export const {
  getAvailableModels,
  getProviders,
  createConversation,
  getConversations,
  getConversation,
  updateConversation,
  deleteConversation,
  getMessages,
  addMessage,
  sendDirectMessage,
  sendConversationMessage,
  streamConversationMessage,
  sendMessageWithThinking,
  sendMessageWithTools,
  bulkDeleteConversations,
  exportConversation,
  checkHealth,
  getServiceStatus,
  validateChatRequest,
  formatMessageForDisplay
} = chatService