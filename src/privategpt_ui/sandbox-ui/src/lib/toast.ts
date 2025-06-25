import toast, { ToastOptions } from 'react-hot-toast'
import { APIError } from './api-client'

// Default toast options
const defaultOptions: ToastOptions = {
  duration: 4000,
  style: {
    background: '#1A1A1A',
    color: '#fff',
    border: '1px solid #2A2A2A',
  },
}

// Toast utility functions for consistent messaging
export const toastUtils = {
  // Success messages
  success: (message: string, options?: ToastOptions) => {
    return toast.success(message, { ...defaultOptions, ...options })
  },

  // Error messages
  error: (message: string, options?: ToastOptions) => {
    return toast.error(message, { ...defaultOptions, ...options })
  },

  // Info messages
  info: (message: string, options?: ToastOptions) => {
    return toast(message, { 
      ...defaultOptions,
      icon: 'ℹ️',
      ...options 
    })
  },

  // Loading messages
  loading: (message: string, options?: ToastOptions) => {
    return toast.loading(message, { ...defaultOptions, ...options })
  },

  // Promise-based toasts for async operations
  promise: <T>(
    promise: Promise<T>,
    messages: {
      loading: string
      success: string | ((data: T) => string)
      error: string | ((error: Error) => string)
    },
    options?: ToastOptions
  ) => {
    return toast.promise(promise, messages, { ...defaultOptions, ...options })
  },

  // Dismiss specific toast
  dismiss: (toastId?: string) => {
    return toast.dismiss(toastId)
  },

  // Dismiss all toasts
  dismissAll: () => {
    return toast.dismiss()
  },
  
  // Handle API errors with suggestions
  apiError: (error: APIError | Error, fallbackMessage?: string) => {
    let message = fallbackMessage || 'An error occurred'
    
    if (error instanceof APIError) {
      message = error.message
      
      // Add suggestions if available
      if (error.suggestions && error.suggestions.length > 0) {
        const suggestions = error.suggestions.slice(0, 2).join(' ')
        message = `${message}. ${suggestions}`
      }
    } else if (error instanceof Error) {
      message = error.message
    }
    
    return toast.error(message, { 
      ...defaultOptions,
      duration: 6000 // Longer duration for errors with suggestions
    })
  },
}

// Specific toast messages for common scenarios
export const toastMessages = {
  // Model management
  modelLoaded: (modelName: string) => `Model "${modelName}" loaded successfully`,
  modelLoadError: 'Failed to load models. Please check your connection.',
  modelSelected: (modelName: string) => `Switched to "${modelName}"`,

  // Session management
  sessionCreated: 'New conversation created',
  sessionCreateError: 'Failed to create conversation',
  sessionDeleted: 'Conversation deleted',
  sessionDeleteError: 'Failed to delete conversation',
  sessionRenamed: 'Conversation renamed',
  sessionRenameError: 'Failed to rename conversation',

  // Chat functionality
  messageError: 'Failed to send message. Please try again.',
  streamingError: 'Connection interrupted. Please try again.',
  
  // Authentication
  loginSuccess: 'Successfully logged in!',
  logoutSuccess: 'Successfully logged out',
  loginError: 'Login failed. Please check your credentials.',
  authError: 'Authentication required. Please log in.',
  tokenExpired: 'Your session has expired. Please log in again.',
  
  // General errors
  networkError: 'Network error. Please check your connection.',
  unknownError: 'Something went wrong. Please try again.',
  rateLimitError: 'Too many requests. Please wait a moment.',
  validationError: 'Invalid input. Please check your data.',
  
  // Success messages
  settingsSaved: 'Settings saved successfully',
  copySuccess: 'Copied to clipboard',
}