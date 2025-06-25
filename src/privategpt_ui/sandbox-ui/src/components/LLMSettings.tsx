/**
 * LLM Settings Component
 * 
 * Provides interface for configuring LLM providers, models, and settings.
 * Mirrors functionality from the Streamlit admin panel.
 */

"use client"

import React, { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api-client'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { 
  Settings, 
  Cpu, 
  Cloud, 
  Brain, 
  CheckCircle, 
  XCircle, 
  Loader,
  RefreshCw,
  Eye,
  EyeOff
} from 'lucide-react'

interface ModelInfo {
  id: string
  name: string
  provider: string
  description?: string
  context_window?: number
  parameters?: number
}

interface ProviderInfo {
  name: string
  status: 'healthy' | 'unhealthy' | 'unknown'
  models: ModelInfo[]
  config?: Record<string, any>
}

interface ProvidersResponse {
  providers: Record<string, ProviderInfo>
}

export default function LLMSettings() {
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({})
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [isLoading, setIsLoading] = useState(true)
  const [showApiKeys, setShowApiKeys] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load providers and models on component mount
  useEffect(() => {
    loadLLMData()
  }, [])

  const loadLLMData = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      // Load models first
      const modelsResponse = await apiClient.getModels()
      console.log('Models response:', modelsResponse)
      
      // Handle different response formats
      const modelsList = Array.isArray(modelsResponse) ? modelsResponse : 
                        modelsResponse.models || []
      setModels(modelsList)
      
      // Set default selected model if none selected
      if (!selectedModel && modelsList.length > 0) {
        setSelectedModel(modelsList[0].id)
      }
      
      // Try to load providers, but don't fail if not available
      try {
        const providersResponse = await apiClient.getProviders()
        setProviders(providersResponse.providers)
      } catch (providerErr) {
        console.warn('Providers endpoint not available, continuing with models only')
        // Create provider info from models
        const providersFromModels: Record<string, ProviderInfo> = {}
        modelsList.forEach(model => {
          const providerName = model.provider || 'Unknown'
          if (!providersFromModels[providerName]) {
            providersFromModels[providerName] = {
              name: providerName,
              status: 'unknown',
              models: []
            }
          }
          providersFromModels[providerName].models.push(model)
        })
        setProviders(providersFromModels)
      }
    } catch (err) {
      console.error('Failed to load LLM data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load LLM settings')
    } finally {
      setIsLoading(false)
    }
  }

  const getProviderIcon = (providerName: string) => {
    switch (providerName.toLowerCase()) {
      case 'ollama':
        return <Cpu className="w-5 h-5" />
      case 'openai':
        return <Cloud className="w-5 h-5" />
      case 'anthropic':
        return <Brain className="w-5 h-5" />
      default:
        return <Settings className="w-5 h-5" />
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'unhealthy':
        return <XCircle className="w-4 h-4 text-red-500" />
      default:
        return <Loader className="w-4 h-4 text-gray-400 animate-spin" />
    }
  }

  const formatModelSize = (parameters?: number) => {
    if (!parameters) return ''
    
    if (parameters >= 1_000_000_000) {
      return `${(parameters / 1_000_000_000).toFixed(1)}B`
    } else if (parameters >= 1_000_000) {
      return `${(parameters / 1_000_000).toFixed(1)}M`
    }
    return `${parameters}`
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-gray-600 dark:text-gray-400">Loading LLM settings...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <XCircle className="w-8 h-8 mx-auto mb-4 text-red-500" />
          <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
          <Button onClick={loadLLMData} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            LLM Settings
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Configure language model providers and models
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => setShowApiKeys(!showApiKeys)}
            variant="outline"
            size="sm"
          >
            {showApiKeys ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            {showApiKeys ? 'Hide' : 'Show'} API Keys
          </Button>
          <Button onClick={loadLLMData} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Providers Status */}
      <Card className="p-6">
        <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Provider Status
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(providers).map(([name, provider]) => (
            <div
              key={name}
              className="border rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {getProviderIcon(name)}
                  <span className="font-medium capitalize">{name}</span>
                </div>
                {getStatusIcon(provider.status)}
              </div>
              
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {provider.models.length} model{provider.models.length !== 1 ? 's' : ''} available
              </div>
              
              {provider.status === 'healthy' && (
                <div className="mt-2 text-xs text-green-600 dark:text-green-400">
                  Connected
                </div>
              )}
              
              {provider.status === 'unhealthy' && (
                <div className="mt-2 text-xs text-red-600 dark:text-red-400">
                  Connection failed
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Available Models */}
      <Card className="p-6">
        <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
          <Brain className="w-5 h-5" />
          Available Models
        </h3>
        
        <div className="space-y-3">
          {models.map((model) => (
            <div
              key={model.id}
              className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                selectedModel === model.id
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-800'
              }`}
              onClick={() => setSelectedModel(model.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {getProviderIcon(model.provider)}
                  <div>
                    <div className="font-medium">{model.name}</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      Provider: {model.provider}
                      {model.parameters && (
                        <span className="ml-2">
                          • {formatModelSize(model.parameters)} parameters
                        </span>
                      )}
                      {model.context_window && (
                        <span className="ml-2">
                          • {model.context_window.toLocaleString()} context
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                
                {selectedModel === model.id && (
                  <CheckCircle className="w-5 h-5 text-blue-500" />
                )}
              </div>
              
              {model.description && (
                <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                  {model.description}
                </div>
              )}
            </div>
          ))}
        </div>

        {models.length === 0 && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No models available. Check your provider configurations.
          </div>
        )}
      </Card>

      {/* Model Selection Summary */}
      {selectedModel && (
        <Card className="p-4 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">
              Selected Model: {models.find(m => m.id === selectedModel)?.name}
            </span>
          </div>
          <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
            This model will be used for new conversations. Existing conversations will continue using their original model.
          </p>
        </Card>
      )}
    </div>
  )
}