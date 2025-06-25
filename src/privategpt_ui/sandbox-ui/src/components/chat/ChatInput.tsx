/**
 * Enhanced Chat Input Component
 * 
 * Provides a comprehensive chat input interface with support for:
 * - Multi-line text input with auto-resize
 * - File uploads and attachments
 * - Model selection
 * - Tool toggles
 * - Quick actions and shortcuts
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { 
  Send, 
  Paperclip, 
  Image, 
  File, 
  Mic, 
  Settings,
  Bot,
  Zap,
  X,
  Plus,
  ChevronDown
} from 'lucide-react'
import { ModelInfo } from '@/types/chat'

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSend: (message: string, options?: ChatInputOptions) => void
  placeholder?: string
  disabled?: boolean
  isStreaming?: boolean
  availableModels?: ModelInfo[]
  selectedModel?: string
  onModelChange?: (modelId: string) => void
  enableFileUpload?: boolean
  enableVoiceInput?: boolean
  enableTools?: boolean
  enabledTools?: string[]
  onToolsChange?: (tools: string[]) => void
  maxLength?: number
  className?: string
}

interface ChatInputOptions {
  model?: string
  temperature?: number
  maxTokens?: number
  useTools?: boolean
  enabledTools?: string[]
  attachments?: File[]
}

interface AttachedFile {
  id: string
  file: File
  preview?: string
}

const AVAILABLE_TOOLS = [
  { id: 'search_documents', name: 'Document Search', description: 'Search through uploaded documents' },
  { id: 'read_file', name: 'File Reader', description: 'Read file contents' },
  { id: 'create_file', name: 'File Creator', description: 'Create new files' },
  { id: 'edit_file', name: 'File Editor', description: 'Edit existing files' },
  { id: 'list_directory', name: 'Directory Lister', description: 'List directory contents' },
  { id: 'get_system_info', name: 'System Info', description: 'Get system information' },
]

export function ChatInput({
  value = '',
  onChange,
  onSend,
  placeholder = "Type your message...",
  disabled = false,
  isStreaming = false,
  availableModels = [],
  selectedModel,
  onModelChange,
  enableFileUpload = true,
  enableVoiceInput = false,
  enableTools = true,
  enabledTools = [],
  onToolsChange,
  maxLength = 10000,
  className
}: ChatInputProps) {
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const [showModelSelect, setShowModelSelect] = useState(false)
  const [showToolSelect, setShowToolSelect] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(2000)
  
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const modelSelectRef = useRef<HTMLDivElement>(null)
  const toolSelectRef = useRef<HTMLDivElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    const adjustHeight = () => {
      textarea.style.height = 'auto'
      const newHeight = Math.min(textarea.scrollHeight, 200) // Max 200px height
      textarea.style.height = `${newHeight}px`
    }

    adjustHeight()
  }, [value])

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Shift+Enter for new line
        return
      } else {
        // Enter to send
        e.preventDefault()
        handleSend()
      }
    }

    if (e.key === 'Escape') {
      // Clear input or close modals
      if (showModelSelect) setShowModelSelect(false)
      else if (showToolSelect) setShowToolSelect(false)
      else if (value) onChange('')
    }
  }, [value, showModelSelect, showToolSelect])

  // Handle file uploads
  const handleFileUpload = useCallback((files: FileList | null) => {
    if (!files) return

    const newFiles: AttachedFile[] = []
    
    Array.from(files).forEach((file) => {
      const id = `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      
      const attachedFile: AttachedFile = { id, file }
      
      // Generate preview for images
      if (file.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onload = (e) => {
          setAttachedFiles(prev => 
            prev.map(f => f.id === id ? { ...f, preview: e.target?.result as string } : f)
          )
        }
        reader.readAsDataURL(file)
      }
      
      newFiles.push(attachedFile)
    })
    
    setAttachedFiles(prev => [...prev, ...newFiles])
  }, [])

  const removeAttachedFile = useCallback((fileId: string) => {
    setAttachedFiles(prev => prev.filter(f => f.id !== fileId))
  }, [])

  const handleSend = useCallback(() => {
    if (!value.trim() || disabled || isStreaming) return

    const options: ChatInputOptions = {
      model: selectedModel,
      temperature,
      maxTokens,
      useTools: enabledTools && enabledTools.length > 0,
      enabledTools,
      attachments: attachedFiles.map(f => f.file)
    }

    onSend(value.trim(), options)
    onChange('')
    setAttachedFiles([])
  }, [value, disabled, isStreaming, selectedModel, temperature, maxTokens, enabledTools, attachedFiles, onSend, onChange])

  const handleToolToggle = useCallback((toolId: string) => {
    const newTools = enabledTools?.includes(toolId)
      ? enabledTools.filter(t => t !== toolId)
      : [...(enabledTools || []), toolId]
    
    onToolsChange?.(newTools)
  }, [enabledTools, onToolsChange])

  // Click outside handlers
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modelSelectRef.current && !modelSelectRef.current.contains(event.target as Node)) {
        setShowModelSelect(false)
      }
      if (toolSelectRef.current && !toolSelectRef.current.contains(event.target as Node)) {
        setShowToolSelect(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const canSend = value.trim().length > 0 && !disabled && !isStreaming

  return (
    <div className={cn('chat-input-container', className)}>
      {/* Attached Files Preview */}
      {attachedFiles.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {attachedFiles.map((file) => (
            <div key={file.id} className="relative">
              <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg border">
                {file.preview ? (
                  <img 
                    src={file.preview} 
                    alt={file.file.name}
                    className="w-8 h-8 object-cover rounded"
                  />
                ) : (
                  <File className="w-4 h-4 text-gray-500" />
                )}
                <div className="text-sm">
                  <div className="font-medium truncate max-w-[150px]">{file.file.name}</div>
                  <div className="text-xs text-gray-500">
                    {(file.file.size / 1024).toFixed(1)} KB
                  </div>
                </div>
                <button
                  onClick={() => removeAttachedFile(file.id)}
                  className="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Main Input Container */}
      <div className="relative bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-xl shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent">
        {/* Top Bar - Model Selection and Tools */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            {/* Model Selection */}
            {availableModels.length > 0 && (
              <div className="relative" ref={modelSelectRef}>
                <button
                  onClick={() => setShowModelSelect(!showModelSelect)}
                  className="flex items-center gap-2 px-2 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  <Bot className="w-3 h-3" />
                  <span className="max-w-[120px] truncate">
                    {availableModels.find(m => m.id === selectedModel)?.name || 'Select Model'}
                  </span>
                  <ChevronDown className="w-3 h-3" />
                </button>

                {showModelSelect && (
                  <div className="absolute bottom-full left-0 mb-2 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto">
                    {availableModels.map((model) => (
                      <button
                        key={model.id}
                        onClick={() => {
                          onModelChange?.(model.id)
                          setShowModelSelect(false)
                        }}
                        className={cn(
                          'w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors',
                          selectedModel === model.id && 'bg-blue-50 dark:bg-blue-900/30'
                        )}
                      >
                        <div className="font-medium text-sm">{model.name}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {model.provider} • {model.description}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tools Selection */}
            {enableTools && (
              <div className="relative" ref={toolSelectRef}>
                <button
                  onClick={() => setShowToolSelect(!showToolSelect)}
                  className={cn(
                    'flex items-center gap-1 px-2 py-1 text-xs rounded-lg transition-colors',
                    enabledTools && enabledTools.length > 0
                      ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                  )}
                >
                  <Zap className="w-3 h-3" />
                  <span>{enabledTools?.length || 0} tools</span>
                </button>

                {showToolSelect && (
                  <div className="absolute bottom-full left-0 mb-2 w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
                    <div className="p-3">
                      <h3 className="font-medium text-sm mb-2">Available Tools</h3>
                      <div className="space-y-2">
                        {AVAILABLE_TOOLS.map((tool) => (
                          <label
                            key={tool.id}
                            className="flex items-start gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={enabledTools?.includes(tool.id) || false}
                              onChange={() => handleToolToggle(tool.id)}
                              className="mt-0.5"
                            />
                            <div>
                              <div className="font-medium text-sm">{tool.name}</div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                {tool.description}
                              </div>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center gap-1">
            {/* Advanced Settings */}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              title="Advanced settings"
            >
              <Settings className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Advanced Settings Panel */}
        {showAdvanced && (
          <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <label className="block text-xs font-medium mb-1">Temperature</label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full"
                />
                <span className="text-xs text-gray-500">{temperature}</span>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Max Tokens</label>
                <input
                  type="number"
                  min="100"
                  max="4000"
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                  className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded text-xs"
                />
              </div>
            </div>
          </div>
        )}

        {/* Text Input Area */}
        <div className="flex items-end gap-3 p-3">
          {/* File Upload Button */}
          {enableFileUpload && (
            <div className="flex gap-1">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => handleFileUpload(e.target.files)}
                accept="image/*,.pdf,.doc,.docx,.txt,.md"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="Attach files"
                disabled={disabled}
              >
                <Paperclip className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Text Input */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              maxLength={maxLength}
              className={cn(
                'w-full resize-none border-0 bg-transparent focus:ring-0 focus:outline-none',
                'placeholder-gray-500 dark:placeholder-gray-400',
                'text-gray-900 dark:text-gray-100',
                'min-h-[20px] max-h-[200px]',
                disabled && 'opacity-50 cursor-not-allowed'
              )}
              rows={1}
            />
            
            {/* Character Count */}
            {maxLength && value.length > maxLength * 0.8 && (
              <div className={cn(
                'absolute -top-5 right-0 text-xs',
                value.length >= maxLength ? 'text-red-500' : 'text-gray-500'
              )}>
                {value.length}/{maxLength}
              </div>
            )}
          </div>

          {/* Voice Input Button */}
          {enableVoiceInput && (
            <button
              className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Voice input"
              disabled={disabled}
            >
              <Mic className="w-4 h-4" />
            </button>
          )}

          {/* Send Button */}
          <button
            onClick={handleSend}
            disabled={!canSend}
            className={cn(
              'p-2 rounded-lg transition-all duration-200',
              canSend
                ? 'bg-blue-500 hover:bg-blue-600 text-white shadow-md hover:shadow-lg transform hover:scale-105'
                : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed',
              isStreaming && 'animate-pulse'
            )}
            title="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Quick Help Text */}
      {!disabled && (
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-4">
          <span>Press Enter to send, Shift+Enter for new line</span>
          {enabledTools && enabledTools.length > 0 && (
            <span className="text-blue-500 dark:text-blue-400">
              {enabledTools.length} tool{enabledTools.length !== 1 ? 's' : ''} enabled
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default ChatInput