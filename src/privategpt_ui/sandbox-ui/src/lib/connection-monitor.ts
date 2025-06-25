// Connection State Management Service
import { create } from 'zustand'
import { config } from './config'
import { errorHandler, ErrorType, ErrorSeverity } from './error-handler'

export enum ConnectionStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  RECONNECTING = 'reconnecting',
  DEGRADED = 'degraded'
}

export interface ConnectionState {
  status: ConnectionStatus
  lastConnected: Date | null
  lastError: string | null
  retryCount: number
  latency: number | null
  serviceHealth: {
    gateway: boolean
    llm: boolean
    auth: boolean
    database: boolean
  }
}

interface ConnectionStore extends ConnectionState {
  // Actions
  setStatus: (status: ConnectionStatus) => void
  setLatency: (latency: number) => void
  setError: (error: string) => void
  incrementRetry: () => void
  resetRetry: () => void
  updateServiceHealth: (service: keyof ConnectionState['serviceHealth'], healthy: boolean) => void
  // Computed
  isOnline: () => boolean
  isHealthy: () => boolean
}

export const useConnectionStore = create<ConnectionStore>()((set, get) => ({
  // Initial state
  status: ConnectionStatus.CONNECTING,
  lastConnected: null,
  lastError: null,
  retryCount: 0,
  latency: null,
  serviceHealth: {
    gateway: true,
    llm: true,
    auth: true,
    database: true
  },

  // Actions
  setStatus: (status) => set({ status }),
  setLatency: (latency) => set({ latency }),
  setError: (error) => set({ lastError: error }),
  incrementRetry: () => set(state => ({ retryCount: state.retryCount + 1 })),
  resetRetry: () => set({ retryCount: 0 }),
  updateServiceHealth: (service, healthy) => set(state => ({
    serviceHealth: {
      ...state.serviceHealth,
      [service]: healthy
    }
  })),

  // Computed
  isOnline: () => {
    const status = get().status
    return status === ConnectionStatus.CONNECTED || status === ConnectionStatus.DEGRADED
  },
  isHealthy: () => {
    const { serviceHealth } = get()
    return Object.values(serviceHealth).every(healthy => healthy)
  }
}))

class ConnectionMonitor {
  private healthCheckInterval?: NodeJS.Timeout
  private heartbeatInterval?: NodeJS.Timeout
  private abortController?: AbortController
  private readonly healthCheckIntervalMs = 30000 // 30 seconds
  private readonly heartbeatIntervalMs = 60000 // 1 minute
  private readonly timeoutMs = 5000 // 5 seconds

  start(): void {
    this.stop() // Clean up any existing intervals
    
    // Initial health check
    this.performHealthCheck()
    
    // Set up periodic health checks
    this.healthCheckInterval = setInterval(() => {
      this.performHealthCheck()
    }, this.healthCheckIntervalMs)

    // Set up heartbeat
    this.heartbeatInterval = setInterval(() => {
      this.heartbeat()
    }, this.heartbeatIntervalMs)

    // Listen for online/offline events
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.handleOnline)
      window.addEventListener('offline', this.handleOffline)
      window.addEventListener('beforeunload', this.stop)
    }
  }

  stop(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval)
      this.healthCheckInterval = undefined
    }

    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = undefined
    }

    if (this.abortController) {
      this.abortController.abort()
      this.abortController = undefined
    }

    if (typeof window !== 'undefined') {
      window.removeEventListener('online', this.handleOnline)
      window.removeEventListener('offline', this.handleOffline)
      window.removeEventListener('beforeunload', this.stop)
    }
  }

  private handleOnline = (): void => {
    console.log('Browser back online, checking services...')
    useConnectionStore.getState().setStatus(ConnectionStatus.CONNECTING)
    this.performHealthCheck()
  }

  private handleOffline = (): void => {
    console.log('Browser offline detected')
    useConnectionStore.getState().setStatus(ConnectionStatus.DISCONNECTED)
    useConnectionStore.getState().setError('Browser is offline')
  }

  private async performHealthCheck(): Promise<void> {
    if (!navigator.onLine) {
      useConnectionStore.getState().setStatus(ConnectionStatus.DISCONNECTED)
      return
    }

    const startTime = Date.now()
    const store = useConnectionStore.getState()
    
    try {
      this.abortController = new AbortController()
      const timeoutId = setTimeout(() => this.abortController?.abort(), this.timeoutMs)

      // Check gateway health
      const response = await fetch(`${config.apiUrl}/health`, {
        signal: this.abortController.signal,
        cache: 'no-cache'
      })

      clearTimeout(timeoutId)
      
      const latency = Date.now() - startTime
      store.setLatency(latency)

      if (response.ok) {
        const healthData = await response.json()
        
        // Update service health based on response
        this.updateServiceHealthFromResponse(healthData)
        
        // Determine overall status
        const isHealthy = store.isHealthy()
        const newStatus = isHealthy ? ConnectionStatus.CONNECTED : ConnectionStatus.DEGRADED
        
        if (store.status !== newStatus) {
          store.setStatus(newStatus)
          store.resetRetry()
          
          if (newStatus === ConnectionStatus.CONNECTED) {
            store.setError(null)
            set({ lastConnected: new Date() })
          }
        }
      } else {
        throw new Error(`Health check failed: ${response.status}`)
      }
    } catch (error: any) {
      this.handleHealthCheckError(error)
    }
  }

  private updateServiceHealthFromResponse(healthData: any): void {
    const store = useConnectionStore.getState()
    
    // Update based on actual health response structure
    if (healthData.service === 'gateway' && healthData.status) {
      const isHealthy = healthData.status === 'healthy'
      store.updateServiceHealth('gateway', isHealthy)
      
      // For now, assume other services are healthy if gateway is healthy
      // In a real system, each service would have its own health endpoint
      if (isHealthy) {
        store.updateServiceHealth('llm', true)
        store.updateServiceHealth('auth', true) 
        store.updateServiceHealth('database', true)
      }
    }
    
    // If health endpoint includes service statuses (future enhancement)
    if (healthData.services) {
      Object.entries(healthData.services).forEach(([service, data]: [string, any]) => {
        if (service in store.serviceHealth) {
          store.updateServiceHealth(
            service as keyof ConnectionState['serviceHealth'], 
            data.status === 'healthy'
          )
        }
      })
    }
  }

  private handleHealthCheckError(error: any): void {
    const store = useConnectionStore.getState()
    
    console.warn('Health check failed:', error.message)
    
    store.incrementRetry()
    store.setError(error.message)
    
    // Determine status based on error type
    if (error.name === 'AbortError') {
      store.setStatus(ConnectionStatus.DISCONNECTED)
      store.setError('Connection timeout')
    } else if (error.message?.includes('Failed to fetch')) {
      store.setStatus(ConnectionStatus.DISCONNECTED)
      store.setError('Cannot reach server')
    } else {
      store.setStatus(ConnectionStatus.DEGRADED)
    }

    // Mark all services as unhealthy on connection failure
    store.updateServiceHealth('gateway', false)
    store.updateServiceHealth('llm', false)
    store.updateServiceHealth('auth', false)
    store.updateServiceHealth('database', false)

    // Report error for high retry counts
    if (store.retryCount > 3) {
      errorHandler.handle({
        type: ErrorType.NETWORK,
        severity: ErrorSeverity.HIGH,
        message: `Connection failed after ${store.retryCount} attempts`,
        timestamp: new Date(),
        context: 'ConnectionMonitor.healthCheck',
        details: { error: error.message, retryCount: store.retryCount },
        recoverable: true
      })
    }
  }

  private async heartbeat(): Promise<void> {
    // Lightweight ping to keep connection alive
    try {
      const response = await fetch(`${config.apiUrl}/health`, {
        method: 'HEAD',
        cache: 'no-cache'
      })
      
      if (!response.ok) {
        throw new Error(`Heartbeat failed: ${response.status}`)
      }
    } catch (error) {
      console.warn('Heartbeat failed:', error)
      // Trigger full health check on heartbeat failure
      this.performHealthCheck()
    }
  }

  // Manual connection test
  async testConnection(): Promise<{
    success: boolean
    latency: number
    error?: string
  }> {
    const startTime = Date.now()
    
    try {
      const response = await fetch(`${config.apiUrl}/health`, {
        cache: 'no-cache'
      })
      
      const latency = Date.now() - startTime
      
      if (response.ok) {
        return { success: true, latency }
      } else {
        return { 
          success: false, 
          latency,
          error: `HTTP ${response.status}` 
        }
      }
    } catch (error: any) {
      return {
        success: false,
        latency: Date.now() - startTime,
        error: error.message
      }
    }
  }
}

// Export singleton instance
export const connectionMonitor = new ConnectionMonitor()

// Helper hooks
export const useConnectionStatus = () => useConnectionStore(state => state.status)
export const useIsOnline = () => useConnectionStore(state => state.isOnline())
export const useIsHealthy = () => useConnectionStore(state => state.isHealthy())
export const useLatency = () => useConnectionStore(state => state.latency)
export const useServiceHealth = () => useConnectionStore(state => state.serviceHealth)

// Auto-start in browser environment - DISABLED for now to prevent error spam
// if (typeof window !== 'undefined') {
//   // Start monitoring when module loads
//   connectionMonitor.start()
// }