// Client-side only API client instance
import { PrivateGPTClient } from './api-client'

let apiClientInstance: PrivateGPTClient | null = null

export function getApiClient(): PrivateGPTClient {
  if (typeof window === 'undefined') {
    // Server-side: create a new instance each time
    return new PrivateGPTClient('')
  }
  
  // Client-side: use singleton
  if (!apiClientInstance) {
    apiClientInstance = new PrivateGPTClient('')
  }
  
  return apiClientInstance
}

// For backward compatibility
export const apiClient = typeof window !== 'undefined' ? getApiClient() : null!