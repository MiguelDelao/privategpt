// Centralized Error Handling Service
import { toast } from 'react-hot-toast'

export enum ErrorType {
  NETWORK = 'NETWORK_ERROR',
  AUTH = 'AUTH_ERROR',
  VALIDATION = 'VALIDATION_ERROR',
  SERVER = 'SERVER_ERROR',
  TIMEOUT = 'TIMEOUT_ERROR',
  RATE_LIMIT = 'RATE_LIMIT_ERROR',
  UNKNOWN = 'UNKNOWN_ERROR'
}

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium', 
  HIGH = 'high',
  CRITICAL = 'critical'
}

export interface AppError {
  type: ErrorType
  severity: ErrorSeverity
  message: string
  code?: string
  details?: Record<string, any>
  timestamp: Date
  userId?: string
  requestId?: string
  context?: string
  suggestions?: string[]
  recoverable: boolean
}

export interface ErrorHandler {
  handle(error: AppError): void
  handleApiError(error: any, context?: string): AppError
  showUserError(error: AppError): void
  logError(error: AppError): void
}

class ErrorHandlerService implements ErrorHandler {
  private errorLog: AppError[] = []
  private maxLogEntries = 100
  private toastRateLimit = new Map<string, number>() // Track last toast time per error type
  private toastCooldown = 5000 // 5 seconds between same error toasts

  handle(error: AppError): void {
    this.logError(error)
    
    // Only show user errors for high+ severity to reduce spam
    if (error.severity === ErrorSeverity.HIGH || error.severity === ErrorSeverity.CRITICAL) {
      this.showUserError(error)
    }

    // Report critical errors to monitoring service
    if (error.severity === ErrorSeverity.CRITICAL) {
      this.reportCriticalError(error)
    }
  }

  handleApiError(error: any, context?: string): AppError {
    const appError = this.categorizeError(error, context)
    this.handle(appError)
    return appError
  }

  private categorizeError(error: any, context?: string): AppError {
    const timestamp = new Date()
    
    // Handle API errors with structured response
    if (error.name === 'APIError' || error.code) {
      return {
        type: this.mapErrorCode(error.code),
        severity: this.getSeverityFromCode(error.code),
        message: this.getUserFriendlyMessage(error),
        code: error.code,
        details: error.details,
        timestamp,
        context,
        suggestions: error.suggestions || this.getSuggestions(error.code),
        recoverable: this.isRecoverable(error.code)
      }
    }

    // Handle network errors
    if (error.message?.includes('Failed to fetch') || 
        error.message?.includes('Network error') ||
        error.name === 'NetworkError') {
      return {
        type: ErrorType.NETWORK,
        severity: ErrorSeverity.HIGH,
        message: 'Unable to connect to the server. Please check your internet connection.',
        timestamp,
        context,
        suggestions: [
          'Check your internet connection',
          'Refresh the page',
          'Try again in a few moments'
        ],
        recoverable: true
      }
    }

    // Handle timeout errors
    if (error.message?.includes('timeout') || error.code === 'TIMEOUT') {
      return {
        type: ErrorType.TIMEOUT,
        severity: ErrorSeverity.MEDIUM,
        message: 'The request took too long to complete.',
        timestamp,
        context,
        suggestions: [
          'Try again',
          'Check your internet connection'
        ],
        recoverable: true
      }
    }

    // Handle authentication errors
    if (error.status === 401 || error.code === 'AUTH_ERROR') {
      return {
        type: ErrorType.AUTH,
        severity: ErrorSeverity.HIGH,
        message: 'Your session has expired. Please log in again.',
        timestamp,
        context,
        suggestions: [
          'Log in again',
          'Clear browser cache'
        ],
        recoverable: true
      }
    }

    // Handle validation errors
    if (error.status === 400 || error.code === 'VALIDATION_ERROR') {
      return {
        type: ErrorType.VALIDATION,
        severity: ErrorSeverity.MEDIUM,
        message: error.message || 'Please check your input and try again.',
        timestamp,
        context,
        suggestions: [
          'Check your input',
          'Ensure all required fields are filled'
        ],
        recoverable: true
      }
    }

    // Handle server errors
    if (error.status >= 500 || error.code === 'SERVER_ERROR') {
      return {
        type: ErrorType.SERVER,
        severity: ErrorSeverity.HIGH,
        message: 'A server error occurred. Our team has been notified.',
        timestamp,
        context,
        suggestions: [
          'Try again in a few minutes',
          'Contact support if the problem persists'
        ],
        recoverable: false
      }
    }

    // Default unknown error
    return {
      type: ErrorType.UNKNOWN,
      severity: ErrorSeverity.MEDIUM,
      message: 'An unexpected error occurred.',
      timestamp,
      context,
      details: { originalError: error },
      suggestions: [
        'Try refreshing the page',
        'Contact support if the problem persists'
      ],
      recoverable: true
    }
  }

  private mapErrorCode(code?: string): ErrorType {
    if (!code) return ErrorType.UNKNOWN
    
    if (code.includes('NETWORK')) return ErrorType.NETWORK
    if (code.includes('AUTH')) return ErrorType.AUTH
    if (code.includes('VALIDATION')) return ErrorType.VALIDATION
    if (code.includes('TIMEOUT')) return ErrorType.TIMEOUT
    if (code.includes('RATE_LIMIT')) return ErrorType.RATE_LIMIT
    if (code.includes('SERVER')) return ErrorType.SERVER
    
    return ErrorType.UNKNOWN
  }

  private getSeverityFromCode(code?: string): ErrorSeverity {
    if (!code) return ErrorSeverity.MEDIUM
    
    if (code.includes('AUTH') || code.includes('NETWORK')) return ErrorSeverity.HIGH
    if (code.includes('SERVER') || code.includes('CRITICAL')) return ErrorSeverity.CRITICAL
    if (code.includes('VALIDATION')) return ErrorSeverity.MEDIUM
    
    return ErrorSeverity.MEDIUM
  }

  private getUserFriendlyMessage(error: any): string {
    // Return user-friendly message if available
    if (error.getUserMessage && typeof error.getUserMessage === 'function') {
      return error.getUserMessage()
    }
    
    // Fallback to error message or default
    return error.message || 'An error occurred'
  }

  private getSuggestions(code?: string): string[] {
    const suggestionMap: Record<string, string[]> = {
      'NETWORK_ERROR': [
        'Check your internet connection',
        'Refresh the page',
        'Try again in a few moments'
      ],
      'AUTH_ERROR': [
        'Log in again',
        'Clear browser cache and cookies'
      ],
      'VALIDATION_ERROR': [
        'Check your input',
        'Ensure all required fields are filled correctly'
      ],
      'SERVER_ERROR': [
        'Try again in a few minutes',
        'Contact support if the problem persists'
      ],
      'TIMEOUT_ERROR': [
        'Try again',
        'Check your internet connection'
      ]
    }
    
    return suggestionMap[code || ''] || [
      'Try refreshing the page',
      'Contact support if the problem persists'
    ]
  }

  private isRecoverable(code?: string): boolean {
    const nonRecoverableCodes = ['SERVER_ERROR', 'CRITICAL_ERROR']
    return !nonRecoverableCodes.some(nonRecoverable => code?.includes(nonRecoverable))
  }

  showUserError(error: AppError): void {
    // Rate limit toasts to prevent flooding
    const errorKey = `${error.type}-${error.code || 'unknown'}`
    const lastToastTime = this.toastRateLimit.get(errorKey) || 0
    const now = Date.now()
    
    if (now - lastToastTime < this.toastCooldown) {
      // Skip this toast, too soon after the last one
      return
    }
    
    this.toastRateLimit.set(errorKey, now)
    
    const message = error.suggestions && error.suggestions.length > 0
      ? `${error.message}\n\nSuggestions:\n${error.suggestions.map(s => `• ${s}`).join('\n')}`
      : error.message

    switch (error.severity) {
      case ErrorSeverity.CRITICAL:
      case ErrorSeverity.HIGH:
        toast.error(message, {
          duration: 8000,
          id: `error-${errorKey}`
        })
        break
      case ErrorSeverity.MEDIUM:
        toast.error(message, {
          duration: 5000,
          id: `error-${errorKey}`
        })
        break
      default:
        // Low severity - just log, don't show to user
        break
    }
  }

  logError(error: AppError): void {
    // Add to internal log
    this.errorLog.unshift(error)
    
    // Trim log if too large
    if (this.errorLog.length > this.maxLogEntries) {
      this.errorLog = this.errorLog.slice(0, this.maxLogEntries)
    }

    // Console log in development
    if (process.env.NODE_ENV === 'development') {
      console.group(`🚨 ${error.type} - ${error.severity}`)
      console.error('Message:', error.message)
      console.error('Code:', error.code)
      console.error('Context:', error.context)
      console.error('Details:', error.details)
      console.error('Suggestions:', error.suggestions)
      console.groupEnd()
    }
  }

  private reportCriticalError(error: AppError): void {
    // In production, this would report to monitoring service (Sentry, etc.)
    console.error('CRITICAL ERROR:', error)
    
    // Could also trigger email alerts, Slack notifications, etc.
  }

  getErrorLog(): AppError[] {
    return [...this.errorLog]
  }

  clearErrorLog(): void {
    this.errorLog = []
  }

  getErrorStats(): {
    total: number
    byType: Record<ErrorType, number>
    bySeverity: Record<ErrorSeverity, number>
    recent: number
  } {
    const recent = this.errorLog.filter(e => 
      Date.now() - e.timestamp.getTime() < 60000 // Last minute
    ).length

    const byType = this.errorLog.reduce((acc, error) => {
      acc[error.type] = (acc[error.type] || 0) + 1
      return acc
    }, {} as Record<ErrorType, number>)

    const bySeverity = this.errorLog.reduce((acc, error) => {
      acc[error.severity] = (acc[error.severity] || 0) + 1
      return acc
    }, {} as Record<ErrorSeverity, number>)

    return {
      total: this.errorLog.length,
      byType,
      bySeverity,
      recent
    }
  }
}

// Export singleton instance
export const errorHandler = new ErrorHandlerService()

// Helper functions for common use cases
export const handleApiError = (error: any, context?: string) => 
  errorHandler.handleApiError(error, context)

export const showError = (message: string, type: ErrorType = ErrorType.UNKNOWN, severity: ErrorSeverity = ErrorSeverity.MEDIUM) => {
  const error: AppError = {
    type,
    severity,
    message,
    timestamp: new Date(),
    recoverable: true
  }
  errorHandler.handle(error)
}

export const showSuccess = (message: string) => {
  toast.success(message)
}

export const showInfo = (message: string) => {
  toast(message)
}