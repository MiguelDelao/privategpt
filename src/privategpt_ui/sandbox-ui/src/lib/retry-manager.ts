// Comprehensive Retry Strategy with Circuit Breaker
import { errorHandler, ErrorType, ErrorSeverity } from './error-handler'

export enum CircuitState {
  CLOSED = 'closed',     // Normal operation
  OPEN = 'open',         // Failing fast
  HALF_OPEN = 'half_open' // Testing if service recovered
}

export interface RetryConfig {
  maxAttempts: number
  baseDelay: number
  maxDelay: number
  backoffMultiplier: number
  jitterMs: number
  timeoutMs: number
  retryCondition?: (error: any) => boolean
}

export interface CircuitBreakerConfig {
  failureThreshold: number
  recoveryTimeout: number
  monitoringWindow: number
  volumeThreshold: number
}

class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED
  private failures: number = 0
  private lastFailureTime: number = 0
  private requestCount: number = 0
  private windowStart: number = Date.now()

  constructor(private config: CircuitBreakerConfig) {}

  async execute<T>(operation: () => Promise<T>, operationName: string): Promise<T> {
    // Check if we should allow the request
    if (!this.canExecute()) {
      throw new Error(`Circuit breaker is OPEN for ${operationName}`)
    }

    this.recordRequest()

    try {
      const result = await operation()
      this.recordSuccess()
      return result
    } catch (error) {
      this.recordFailure()
      throw error
    }
  }

  private canExecute(): boolean {
    const now = Date.now()

    // Reset monitoring window if needed
    if (now - this.windowStart > this.config.monitoringWindow) {
      this.resetWindow()
    }

    switch (this.state) {
      case CircuitState.CLOSED:
        return true

      case CircuitState.OPEN:
        // Check if we should transition to half-open
        if (now - this.lastFailureTime > this.config.recoveryTimeout) {
          this.state = CircuitState.HALF_OPEN
          return true
        }
        return false

      case CircuitState.HALF_OPEN:
        // Allow limited requests to test recovery
        return true

      default:
        return false
    }
  }

  private recordRequest(): void {
    this.requestCount++
  }

  private recordSuccess(): void {
    if (this.state === CircuitState.HALF_OPEN) {
      // Recovery successful, close circuit
      this.state = CircuitState.CLOSED
      this.failures = 0
    }
  }

  private recordFailure(): void {
    this.failures++
    this.lastFailureTime = Date.now()

    // Check if we should open the circuit
    if (this.shouldOpenCircuit()) {
      this.state = CircuitState.OPEN
      
      errorHandler.handle({
        type: ErrorType.SERVER,
        severity: ErrorSeverity.HIGH,
        message: `Circuit breaker opened due to ${this.failures} failures`,
        timestamp: new Date(),
        context: 'CircuitBreaker',
        details: {
          failures: this.failures,
          threshold: this.config.failureThreshold,
          requestCount: this.requestCount
        },
        recoverable: true
      })
    }
  }

  private shouldOpenCircuit(): boolean {
    // Need minimum volume to trigger circuit breaker
    if (this.requestCount < this.config.volumeThreshold) {
      return false
    }

    // Check failure rate
    const failureRate = this.failures / this.requestCount
    return failureRate >= this.config.failureThreshold
  }

  private resetWindow(): void {
    this.requestCount = 0
    this.failures = 0
    this.windowStart = Date.now()
  }

  getState(): CircuitState {
    return this.state
  }

  getStats(): {
    state: CircuitState
    failures: number
    requests: number
    failureRate: number
  } {
    return {
      state: this.state,
      failures: this.failures,
      requests: this.requestCount,
      failureRate: this.requestCount > 0 ? this.failures / this.requestCount : 0
    }
  }
}

class RetryManager {
  private circuitBreakers = new Map<string, CircuitBreaker>()
  private defaultRetryConfig: RetryConfig = {
    maxAttempts: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    backoffMultiplier: 2,
    jitterMs: 100,
    timeoutMs: 5000,
    retryCondition: this.defaultRetryCondition
  }

  private defaultCircuitConfig: CircuitBreakerConfig = {
    failureThreshold: 0.5, // 50% failure rate
    recoveryTimeout: 60000, // 1 minute
    monitoringWindow: 60000, // 1 minute window
    volumeThreshold: 10 // Minimum 10 requests
  }

  async withRetry<T>(
    operation: () => Promise<T>,
    options: {
      operationName: string
      retryConfig?: Partial<RetryConfig>
      circuitConfig?: Partial<CircuitBreakerConfig>
      useCircuitBreaker?: boolean
    }
  ): Promise<T> {
    const config = { ...this.defaultRetryConfig, ...options.retryConfig }
    const { operationName, useCircuitBreaker = true } = options

    // Get or create circuit breaker
    let circuitBreaker: CircuitBreaker | undefined
    if (useCircuitBreaker) {
      if (!this.circuitBreakers.has(operationName)) {
        const circuitConfig = { ...this.defaultCircuitConfig, ...options.circuitConfig }
        this.circuitBreakers.set(operationName, new CircuitBreaker(circuitConfig))
      }
      circuitBreaker = this.circuitBreakers.get(operationName)
    }

    const executeWithTimeout = async (): Promise<T> => {
      return new Promise<T>((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          reject(new Error(`Operation ${operationName} timed out after ${config.timeoutMs}ms`))
        }, config.timeoutMs)

        const wrappedOperation = circuitBreaker 
          ? () => circuitBreaker!.execute(operation, operationName)
          : operation

        wrappedOperation()
          .then(result => {
            clearTimeout(timeoutId)
            resolve(result)
          })
          .catch(error => {
            clearTimeout(timeoutId)
            reject(error)
          })
      })
    }

    let lastError: any
    let attempt = 0

    while (attempt < config.maxAttempts) {
      try {
        return await executeWithTimeout()
      } catch (error) {
        attempt++
        lastError = error

        // Check if we should retry
        if (attempt >= config.maxAttempts || !config.retryCondition!(error)) {
          break
        }

        // Calculate delay with exponential backoff and jitter
        const delay = this.calculateDelay(attempt, config)
        
        console.log(`Retry attempt ${attempt}/${config.maxAttempts} for ${operationName} in ${delay}ms`)
        
        await this.sleep(delay)
      }
    }

    // All retries exhausted
    errorHandler.handle({
      type: this.getErrorTypeFromError(lastError),
      severity: ErrorSeverity.HIGH,
      message: `Operation ${operationName} failed after ${config.maxAttempts} attempts`,
      timestamp: new Date(),
      context: `RetryManager.${operationName}`,
      details: {
        attempts: config.maxAttempts,
        lastError: lastError.message,
        circuitState: circuitBreaker?.getState()
      },
      recoverable: false
    })

    throw lastError
  }

  private calculateDelay(attempt: number, config: RetryConfig): number {
    // Exponential backoff: baseDelay * (backoffMultiplier ^ (attempt - 1))
    const exponentialDelay = config.baseDelay * Math.pow(config.backoffMultiplier, attempt - 1)
    
    // Add jitter to prevent thundering herd
    const jitter = Math.random() * config.jitterMs
    
    // Cap at max delay
    const totalDelay = Math.min(exponentialDelay + jitter, config.maxDelay)
    
    return Math.round(totalDelay)
  }

  private defaultRetryCondition(error: any): boolean {
    // Don't retry on auth errors or validation errors
    if (error.status === 401 || error.status === 403 || error.status === 400) {
      return false
    }

    // Don't retry on client errors (4xx except timeout)
    if (error.status >= 400 && error.status < 500 && error.status !== 408) {
      return false
    }

    // Retry on network errors, timeouts, and server errors
    return (
      error.status >= 500 || // Server errors
      error.status === 408 || // Timeout
      error.name === 'NetworkError' ||
      error.message?.includes('Failed to fetch') ||
      error.message?.includes('timeout') ||
      error.message?.includes('Network error')
    )
  }

  private getErrorTypeFromError(error: any): ErrorType {
    if (error.status === 401 || error.status === 403) return ErrorType.AUTH
    if (error.status === 400) return ErrorType.VALIDATION
    if (error.status >= 500) return ErrorType.SERVER
    if (error.message?.includes('timeout')) return ErrorType.TIMEOUT
    if (error.message?.includes('Failed to fetch')) return ErrorType.NETWORK
    return ErrorType.UNKNOWN
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  // Get circuit breaker stats for monitoring
  getCircuitBreakerStats(): Record<string, any> {
    const stats: Record<string, any> = {}
    this.circuitBreakers.forEach((breaker, name) => {
      stats[name] = breaker.getStats()
    })
    return stats
  }

  // Reset circuit breaker for specific operation
  resetCircuitBreaker(operationName: string): void {
    this.circuitBreakers.delete(operationName)
  }

  // Reset all circuit breakers
  resetAllCircuitBreakers(): void {
    this.circuitBreakers.clear()
  }
}

// Export singleton instance
export const retryManager = new RetryManager()

// Convenience functions
export const withRetry = <T>(
  operation: () => Promise<T>,
  operationName: string,
  config?: Partial<RetryConfig>
): Promise<T> => {
  return retryManager.withRetry(operation, {
    operationName,
    retryConfig: config
  })
}

export const withCircuitBreaker = <T>(
  operation: () => Promise<T>,
  operationName: string,
  config?: {
    retryConfig?: Partial<RetryConfig>
    circuitConfig?: Partial<CircuitBreakerConfig>
  }
): Promise<T> => {
  return retryManager.withRetry(operation, {
    operationName,
    retryConfig: config?.retryConfig,
    circuitConfig: config?.circuitConfig,
    useCircuitBreaker: true
  })
}