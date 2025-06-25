"use client"

import { useState, useRef, useEffect } from "react"
import { Send, X, Database, Plus, Settings, Bot, ChevronDown, Menu } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { UserDropdown } from "./LogoutButton"
import { Sidebar } from "./shell/Sidebar"
import { useChatStore } from '@/stores/chatStore'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  isToolCall?: boolean
  toolName?: string
}

interface AttachedDataSource {
  id: string
  name: string
  icon: string
  type: string
}

interface ModelInfo {
  id: string
  name: string
  provider: string
  description?: string
}

interface DemoButton {
  label: string
  message: string
  response: string
  hasToolCall?: boolean
}

const demoButtons: DemoButton[] = [
  {
    label: "Analyze Contract",
    message: "Can you help me analyze this employment contract?",
    response: "I'd be happy to help you analyze your employment contract! Please share the contract document and I'll review the key terms, potential issues, and important clauses you should be aware of."
  },
  {
    label: "Legal Research",
    message: "Research intellectual property licensing laws",
    response: "I'll research current intellectual property licensing laws for you. Let me gather the most recent information on licensing requirements, regulations, and best practices.",
    hasToolCall: true
  },
  {
    label: "Draft Document",
    message: "Help me draft an NDA",
    response: "I can help you draft a comprehensive Non-Disclosure Agreement. Let me create a template that includes all the essential clauses for protecting confidential information in your business relationships."
  }
]

interface ChatInterfaceProps {
  showSidebar?: boolean
}

export function ChatInterface({ showSidebar = true }: ChatInterfaceProps) {
  // Chat store integration
  const {
    getActiveSession,
    activeSessionId,
    createSession,
    sendMessage,
    streamMessage,
    availableModels,
    selectedModel,
    setSelectedModel,
    loadModels,
    loadConversations,
    uiState,
    setInputValue,
    isLoading,
    isSessionStreaming
  } = useChatStore()
  
  // Local UI state
  const [attachedDataSources, setAttachedDataSources] = useState<AttachedDataSource[]>([])
  const [showModelSelector, setShowModelSelector] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const modelSelectorRef = useRef<HTMLDivElement>(null)
  
  // Derived state
  const activeSession = getActiveSession()
  const messages = activeSession?.messages || []
  const isWelcomeMode = !activeSession || messages.length === 0
  const isStreaming = uiState?.isStreaming || (activeSessionId ? isSessionStreaming(activeSessionId) : false)
  const inputValue = uiState?.inputValue || ""

  // Load models and conversations on component mount
  useEffect(() => {
    const initializeChat = async () => {
      try {
        // Load available models
        await loadModels()
        
        // Load real conversations from backend
        try {
          await loadConversations()
        } catch (error) {
          console.error('Failed to load conversations:', error)
          // Continue even if conversations fail to load
        }
        
        // Do NOT auto-create sessions - wait for user to actually send a message
      } catch (error) {
        console.error('Failed to initialize chat:', error)
      }
    }

    initializeChat()
    
    // Set up periodic refresh to handle token expiration
    const refreshInterval = setInterval(() => {
      // Silently refresh conversations to keep auth token fresh
      // Only refresh if the document is visible to avoid unnecessary requests
      if (document.visibilityState === 'visible') {
        loadConversations().catch(() => {
          // Ignore errors - this is just a background refresh
        })
      }
    }, 5 * 60 * 1000) // Refresh every 5 minutes
    
    return () => clearInterval(refreshInterval)
  }, [loadModels, loadConversations])

  // Listen for data source attachments from sidebar
  useEffect(() => {
    const handleAttachDataSource = (event: CustomEvent<AttachedDataSource>) => {
      setAttachedDataSources(prev => {
        // Don't add duplicates
        if (prev.find(source => source.id === event.detail.id)) {
          return prev
        }
        return [...prev, event.detail]
      })
    }

    window.addEventListener('attachDataSource', handleAttachDataSource as EventListener)
    
    return () => {
      window.removeEventListener('attachDataSource', handleAttachDataSource as EventListener)
    }
  }, [])

  // Click outside handler for model selector
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modelSelectorRef.current && !modelSelectorRef.current.contains(event.target as Node)) {
        setShowModelSelector(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const removeDataSource = (id: string) => {
    setAttachedDataSources(prev => prev.filter(source => source.id !== id))
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async (messageText?: string, demoResponse?: string, hasToolCall = false) => {
    const text = messageText || (inputValue || "").trim()
    if (!text || isStreaming) return

    // Ensure we have an active session, create one if needed
    let sessionId = activeSessionId
    if (!sessionId) {
      try {
        sessionId = await createSession('New Chat', selectedModel || undefined)
      } catch (error) {
        console.error('Failed to create session:', error)
        return
      }
    }

    // Clear input
    setInputValue("")

    try {
      // Use streaming for real-time responses
      await streamMessage(sessionId, text, {
        model_name: selectedModel,
        use_mcp: false
      })
    } catch (error) {
      console.error('Failed to send message:', error)
      // Error handling is managed by the ChatStore
    }
  }

  const handleDemoClick = (demo: DemoButton) => {
    handleSendMessage(demo.message, demo.response, demo.hasToolCall)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="flex h-full bg-[#171717]">
      {/* Sidebar - only show if showSidebar is true */}
      {showSidebar && (
        <Sidebar 
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />
      )}
      
      {/* Main Chat Area */}
      <div className="flex flex-col flex-1 relative">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#2A2A2A] bg-[#1A1A1A]">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-lg font-semibold text-white">
                {activeSession?.title || 'Select a conversation'}
              </h1>
              {activeSession && (
                <p className="text-sm text-[#B4B4B4]">
                  {activeSession.metadata.messageCount} messages
                  {activeSession.currentModel && (
                    <span className="ml-2">
                      • {activeSession.currentModel}
                    </span>
                  )}
                </p>
              )}
            </div>
          </div>
          <UserDropdown />
        </div>

        {/* Welcome mode - centered content */}
        {isWelcomeMode ? (
          <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.6, ease: "easeInOut" }}
            className="flex flex-col items-center justify-center flex-1 px-4"
          >
            <div className="flex flex-col items-center text-center max-w-2xl mx-auto mb-12">
              <h1 className="text-4xl font-bold text-white mb-3">
                {activeSession ? activeSession.title : 'Good afternoon, M'}
              </h1>
              <p className="text-xl text-[#B4B4B4] mb-12">
                How can I help you today?
              </p>
            </div>

            {/* Demo buttons */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-3xl mb-8">
              {demoButtons.map((demo, index) => (
                <button
                  key={index}
                  onClick={() => handleDemoClick(demo)}
                  className="p-4 border border-[#2A2A2A] bg-[#1A1A1A] rounded-xl hover:border-[#3A3A3A] hover:bg-[#2A2A2A] transition-colors text-left"
                >
                  <div className="font-medium text-white mb-1">{demo.label}</div>
                  <div className="text-sm text-[#B4B4B4] line-clamp-2">{demo.message}</div>
                </button>
              ))}
            </div>
          </motion.div>
        ) : (
          /* Conversation mode - messages area */
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            transition={{ duration: 0.6, ease: "easeInOut" }}
            className="flex-1 overflow-y-auto px-4 py-6"
          >
          <div className="max-w-3xl mx-auto space-y-6">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={`${message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}`}
                >
                  {/* Message content */}
                  <div className="max-w-2xl">
                    {message.role === 'user' ? (
                      <div className="inline-block px-4 py-3 rounded-2xl bg-[#2A2A2A] text-white">
                        <div className="whitespace-pre-wrap">{message.content}</div>
                      </div>
                    ) : (
                      <div className="text-white">
                        {message.tool_calls && message.tool_calls.length > 0 ? (
                          <div className="space-y-2">
                            {message.tool_calls.map((toolCall, idx) => (
                              <div key={idx} className="flex items-center gap-2 text-blue-600">
                                <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                                <span className="font-medium">{toolCall.function.name}</span>
                              </div>
                            ))}
                            {message.content && (
                              <div className="whitespace-pre-wrap text-white mt-2">
                                {message.content}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="whitespace-pre-wrap">
                            {message.content}
                            {message.status === 'streaming' && (
                              <span className="inline-block w-2 h-5 bg-current ml-1 animate-pulse" />
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        </motion.div>
        )}

        {/* Input area - fixed at bottom */}
        <div className="border-t border-[#2A2A2A] bg-[#1A1A1A] mt-auto">
          {/* Attached Data Sources */}
          <AnimatePresence>
            {attachedDataSources.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="border-b border-[#2A2A2A] p-4"
              >
                <div className="max-w-3xl mx-auto">
                    <div className="flex flex-wrap gap-2">
                      {attachedDataSources.map((source) => (
                        <motion.div
                          key={source.id}
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.9 }}
                          className="flex items-center gap-2 px-3 py-2 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-sm shadow-lg"
                        >
                          <Database className="w-3 h-3 text-[#B4B4B4]" />
                          <span className="text-white">{source.name}</span>
                          <button
                            onClick={() => removeDataSource(source.id)}
                            className="text-[#B4B4B4] hover:text-white transition-colors"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                </motion.div>
            )}
          </AnimatePresence>
          
          <div className="max-w-3xl mx-auto p-4">
            {/* LLM Settings Panel */}
            <AnimatePresence>
              {showSettings && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  className="mb-4 p-4 bg-[#1A1A1A] border border-[#3A3A3A] rounded-xl"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-white font-medium">LLM Settings</h3>
                  <button
                    onClick={() => setShowSettings(false)}
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
                              onChange={() => setSelectedModel(modelId)}
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
          
          {/* Single seamless input container */}
          <div className="flex items-center gap-3 p-3 bg-[#2A2A2A] rounded-2xl border border-[#3A3A3A]">
            {/* Tools and Settings buttons */}
            <div className="flex items-center gap-2">
              <button className="flex items-center justify-center w-8 h-8 rounded-full bg-[#3A3A3A] text-[#B4B4B4] hover:bg-[#4A4A4A] hover:text-white transition-colors">
                <Plus className="w-4 h-4" />
              </button>
              <button 
                onClick={() => setShowSettings(!showSettings)}
                className="flex items-center justify-center w-8 h-8 rounded-full bg-[#3A3A3A] text-[#B4B4B4] hover:bg-[#4A4A4A] hover:text-white transition-colors"
                title="LLM Settings"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
            
            {/* Input with seamless model selector and send button */}
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Message Legal Assistant AI..."
                className="w-full pl-4 pr-40 py-3 bg-transparent text-white rounded-xl focus:outline-none placeholder-[#6B6B6B] resize-none"
                disabled={isStreaming}
              />
              
              {/* Seamless model selector - matches original styling */}
              <div 
                ref={modelSelectorRef}
                className="absolute right-12 top-1/2 -translate-y-1/2"
              >
                <button
                  onClick={() => setShowModelSelector(!showModelSelector)}
                  className="flex items-center gap-1 text-[#B4B4B4] hover:text-white transition-colors cursor-pointer"
                  disabled={isLoading}
                >
                  <span className="text-sm font-medium">
                    {isLoading 
                      ? 'Loading...' 
                      : availableModels.find(m => (m.id || m.name || (m as any).model) === selectedModel)?.name || 'No models available'}
                  </span>
                  <ChevronDown className="w-4 h-4" />
                </button>

                {/* Model dropdown - positioned inline with the model selector */}
                {showModelSelector && (
                  <div className="absolute bottom-full right-0 mb-2 w-60 bg-[#1A1A1A] border border-[#3A3A3A] rounded-lg shadow-xl z-50 max-h-56 overflow-y-auto">
                    <div className="p-2">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-xs font-medium text-white">Available Models</div>
                        <button
                          onClick={() => setShowModelSelector(false)}
                          className="text-[#B4B4B4] hover:text-white transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                      
                      {availableModels.map((model, index) => {
                        // Use name or model field as the identifier
                        const modelId = model.id || model.name || (model as any).model
                        return (
                          <button
                            key={modelId}
                            onClick={() => {
                              setSelectedModel(modelId)
                              setShowModelSelector(false)
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
              
              <button
                onClick={() => handleSendMessage()}
                disabled={!(inputValue || "").trim() || isStreaming}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    </div>
  )
}