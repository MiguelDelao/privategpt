"use client"

import { motion, AnimatePresence } from "framer-motion"
import { X, Bot } from "lucide-react"

interface ModelInfo {
  id: string
  name: string
  provider: string
  description?: string
}

interface LLMSettingsPanelProps {
  show: boolean
  onClose: () => void
  availableModels: ModelInfo[]
  selectedModel: string | null
  onModelChange: (modelId: string) => void
}

export function LLMSettingsPanel({ 
  show, 
  onClose, 
  availableModels, 
  selectedModel, 
  onModelChange 
}: LLMSettingsPanelProps) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          className="mb-4 p-4 bg-[#1A1A1A] border border-[#3A3A3A] rounded-xl"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-medium">LLM Settings</h3>
            <button
              onClick={onClose}
              className="text-[#B4B4B4] hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          
          <div className="space-y-4">
            {/* Model Selection */}
            <div>
              <label className="block text-sm font-medium text-[#B4B4B4] mb-2">
                Model
              </label>
              <div className="grid grid-cols-1 gap-2">
                {availableModels.map((model) => {
                  const modelId = model.id || model.name || (model as any).model
                  return (
                    <label
                      key={modelId}
                      className="flex items-center gap-3 p-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg hover:border-[#4A4A4A] transition-colors cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="model"
                        value={modelId}
                        checked={selectedModel === modelId}
                        onChange={() => onModelChange(modelId)}
                        className="text-blue-600"
                      />
                      <div className="flex items-center gap-2 flex-1">
                        <Bot className="w-4 h-4 text-[#B4B4B4]" />
                        <div>
                          <div className="text-white font-medium">{model.name}</div>
                          <div className="text-xs text-[#B4B4B4]">
                            {model.provider}
                            {model.description && ` • ${model.description}`}
                          </div>
                        </div>
                      </div>
                    </label>
                  )
                })}
              </div>
              
              {availableModels.length === 0 && (
                <div className="text-center py-6 text-[#B4B4B4]">
                  <Bot className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <div className="text-sm">No models available</div>
                  <div className="text-xs mt-1">Check your provider configurations</div>
                </div>
              )}
            </div>
            
            {/* Model Status */}
            {selectedModel && (
              <div className="pt-3 border-t border-[#3A3A3A]">
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-[#B4B4B4]">
                    Selected: <span className="text-white">
                      {availableModels.find(m => (m.id || m.name || (m as any).model) === selectedModel)?.name}
                    </span>
                  </span>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}