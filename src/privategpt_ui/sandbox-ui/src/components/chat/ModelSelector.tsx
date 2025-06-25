"use client"

import { useState, useRef, useEffect } from "react"
import { ChevronDown, X, Bot } from "lucide-react"

interface ModelInfo {
  id: string
  name: string
  provider: string
  description?: string
}

interface ModelSelectorProps {
  availableModels: ModelInfo[]
  selectedModel: string | null
  onModelChange: (modelId: string) => void
  isLoading: boolean
  className?: string
}

export function ModelSelector({ 
  availableModels, 
  selectedModel, 
  onModelChange, 
  isLoading,
  className = ""
}: ModelSelectorProps) {
  const [showDropdown, setShowDropdown] = useState(false)
  const [forceRender, setForceRender] = useState(0)
  const selectorRef = useRef<HTMLDivElement>(null)

  // Click outside handler
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectorRef.current && !selectorRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const selectedModelInfo = availableModels.find(m => 
    (m.id || m.name || (m as any).model) === selectedModel
  )

  return (
    <div ref={selectorRef} className={`relative ${className}`}>
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-1 text-[#B4B4B4] hover:text-white transition-colors cursor-pointer"
        disabled={isLoading}
      >
        <span className="text-sm font-medium">
          {isLoading 
            ? 'Loading...' 
            : selectedModelInfo?.name || 'No models available'}
        </span>
        <ChevronDown className="w-4 h-4" />
      </button>

      {/* Model dropdown */}
      {showDropdown && (
        <div className="absolute bottom-full right-0 mb-2 w-60 bg-[#1A1A1A] border border-[#3A3A3A] rounded-lg shadow-xl z-50 max-h-56 overflow-y-auto">
          <div className="p-2">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-medium text-white">Available Models</div>
              <button
                onClick={() => setShowDropdown(false)}
                className="text-[#B4B4B4] hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            {availableModels.map((model, index) => {
              const modelId = model.id || model.name || (model as any).model
              return (
                <button
                  key={modelId}
                  onClick={() => {
                    console.log('🔄 CLICKING MODEL:', modelId, model)
                    console.log('🔄 Current selectedModel before:', selectedModel)
                    onModelChange(modelId)
                    console.log('🔄 onModelChange called with:', modelId)
                    setShowDropdown(false)
                    setForceRender(prev => prev + 1)
                  }}
                  className={`w-full text-left p-2 rounded-md transition-colors ${
                    selectedModel === modelId
                      ? 'bg-[#2A2A2A] text-white border border-[#4A4A4A]'
                      : 'text-white hover:bg-[#2A2A2A]'
                  } ${index < availableModels.length - 1 ? 'mb-1' : ''}`}
                >
                  <div className="flex items-center gap-2">
                    <Bot className="w-3 h-3 text-current" />
                    <div>
                      <div className="font-medium text-sm">{model.name}</div>
                      <div className="text-xs opacity-70">
                        {model.provider}
                        {model.description && ` • ${model.description}`}
                      </div>
                    </div>
                  </div>
                </button>
              )
            })}
            
            {isLoading && (
              <div className="text-center py-6 text-[#B4B4B4]">
                <Bot className="w-8 h-8 mx-auto mb-2 opacity-50 animate-pulse" />
                <div className="text-sm">Loading models...</div>
              </div>
            )}
            
            {!isLoading && availableModels.length === 0 && (
              <div className="text-center py-6 text-[#B4B4B4]">
                <Bot className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <div className="text-sm">No models available</div>
                <div className="text-xs mt-1">Check your provider configurations</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}