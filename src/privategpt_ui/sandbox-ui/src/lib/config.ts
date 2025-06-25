// PrivateGPT Configuration
interface AppConfig {
  // API Configuration
  apiUrl: string
  wsUrl: string
  keycloakUrl: string
  
  // Environment flags
  isProduction: boolean
  isDevelopment: boolean
  debugMode: boolean
  
  // App metadata
  appName: string
  version: string
  
  // Feature flags
  features: {
    enableOfflineMode: boolean
    enableAdvancedLogging: boolean
    enableMetrics: boolean
    enableCircuitBreaker: boolean
    maxRetries: number
    retryDelay: number
  }
  
  // UI Settings
  ui: {
    theme: 'dark' | 'light' | 'auto'
    animationsEnabled: boolean
    compactMode: boolean
    showLatency: boolean
    showConnectionStatus: boolean
  }
  
  // Error Handling
  errorHandling: {
    enableCrashReporting: boolean
    enableDetailedLogging: boolean
    maxErrorLogEntries: number
    reportCriticalErrors: boolean
  }
}

// Default configuration
const defaultConfig: AppConfig = {
  // API Configuration
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  keycloakUrl: process.env.NEXT_PUBLIC_KEYCLOAK_URL || 'http://localhost:8180',
  
  // Environment flags
  isProduction: process.env.NODE_ENV === 'production',
  isDevelopment: process.env.NODE_ENV === 'development',
  debugMode: process.env.NEXT_PUBLIC_DEBUG_MODE === 'true' || process.env.NODE_ENV === 'development',
  
  // App metadata
  appName: 'PrivateGPT',
  version: '2.0.0',
  
  // Feature flags
  features: {
    enableOfflineMode: false, // Disabled for now as requested
    enableAdvancedLogging: process.env.NODE_ENV === 'development',
    enableMetrics: true,
    enableCircuitBreaker: true,
    maxRetries: parseInt(process.env.NEXT_PUBLIC_MAX_RETRIES || '3'),
    retryDelay: parseInt(process.env.NEXT_PUBLIC_RETRY_DELAY || '1000')
  },
  
  // UI Settings
  ui: {
    theme: 'dark',
    animationsEnabled: true,
    compactMode: false,
    showLatency: true,
    showConnectionStatus: true
  },
  
  // Error Handling
  errorHandling: {
    enableCrashReporting: process.env.NODE_ENV === 'production',
    enableDetailedLogging: process.env.NODE_ENV === 'development',
    maxErrorLogEntries: 100,
    reportCriticalErrors: process.env.NODE_ENV === 'production'
  }
}

// Runtime configuration - can be updated during app lifecycle
let runtimeConfig: AppConfig = { ...defaultConfig }

// Configuration manager
class ConfigManager {
  private config: AppConfig = { ...defaultConfig }
  private listeners: Array<(config: AppConfig) => void> = []

  getConfig(): AppConfig {
    return { ...this.config }
  }

  updateConfig(updates: Partial<AppConfig>): void {
    this.config = { ...this.config, ...updates }
    this.notifyListeners()
  }

  updateFeature(feature: keyof AppConfig['features'], value: any): void {
    this.config.features = {
      ...this.config.features,
      [feature]: value
    }
    this.notifyListeners()
  }

  updateUI(setting: keyof AppConfig['ui'], value: any): void {
    this.config.ui = {
      ...this.config.ui,
      [setting]: value
    }
    this.notifyListeners()
  }

  updateErrorHandling(setting: keyof AppConfig['errorHandling'], value: any): void {
    this.config.errorHandling = {
      ...this.config.errorHandling,
      [setting]: value
    }
    this.notifyListeners()
  }

  subscribe(listener: (config: AppConfig) => void): () => void {
    this.listeners.push(listener)
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener)
    }
  }

  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.config))
  }

  // Load configuration from remote source
  async loadRemoteConfig(): Promise<void> {
    try {
      // In a real app, this would fetch from your backend
      // const response = await fetch('/api/config')
      // const remoteConfig = await response.json()
      // this.updateConfig(remoteConfig)
      
      console.log('Remote config loading not implemented')
    } catch (error) {
      console.warn('Failed to load remote configuration:', error)
    }
  }

  // Reset to defaults
  reset(): void {
    this.config = { ...defaultConfig }
    this.notifyListeners()
  }

  // Export configuration for debugging
  export(): string {
    return JSON.stringify(this.config, null, 2)
  }

  // Import configuration (for testing or migration)
  import(configJson: string): void {
    try {
      const importedConfig = JSON.parse(configJson)
      this.updateConfig(importedConfig)
    } catch (error) {
      console.error('Failed to import configuration:', error)
    }
  }
}

// Global configuration manager instance
export const configManager = new ConfigManager()

// Export current config for backwards compatibility
export const config = configManager.getConfig()

// Export type
export type Config = AppConfig

// Initialize remote config loading in browser
if (typeof window !== 'undefined') {
  configManager.loadRemoteConfig()
}