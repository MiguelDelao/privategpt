"use client"

import { useState } from "react"
import { ChevronDown, ChevronRight, Brain, Search, BarChart3, Code, Table, Clock } from "lucide-react"
import { ChatMessage } from "@/stores/chatStore"

interface MessageRendererProps {
  message: ChatMessage
  isChatOnly?: boolean
}

export function MessageRenderer({ message, isChatOnly = false }: MessageRendererProps) {
  const [isThinkingCollapsed, setIsThinkingCollapsed] = useState(message.metadata?.isCollapsed ?? false)

  const formatTimestamp = (timestamp: Date) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  const getMessageIcon = () => {
    switch (message.type) {
      case 'thinking': return <Brain className="w-4 h-4 text-purple-400" />
      case 'search': return <Search className="w-4 h-4 text-blue-400" />
      case 'analyze': return <BarChart3 className="w-4 h-4 text-green-400" />
      case 'code': return <Code className="w-4 h-4 text-orange-400" />
      case 'table': return <Table className="w-4 h-4 text-cyan-400" />
      default: return null
    }
  }

  const getStatusIndicator = () => {
    if (!message.metadata?.status) return null

    switch (message.metadata.status) {
      case 'loading':
        return (
          <div className="flex items-center gap-1 text-xs text-[#6B6B6B]">
            <div className="w-3 h-3 border border-gray-400 border-t-transparent rounded-full animate-spin"></div>
            Processing...
          </div>
        )
      case 'error':
        return (
          <div className="text-xs text-red-400">
            ⚠ Error occurred
          </div>
        )
      case 'complete':
        return (
          <div className="text-xs text-green-400">
            ✓ Complete
          </div>
        )
      default:
        return null
    }
  }

  const parseMessageContent = (content: string) => {
    // Parse <think> tags
    const thinkPattern = /<think>(.*?)<\/think>/gs
    const searchPattern = /<search>(.*?)<\/search>/gs
    const codePattern = /<code lang="([^"]*)">(.*?)<\/code>/gs
    
    let parsedContent = content

    // Replace <think> tags with special rendering
    parsedContent = parsedContent.replace(thinkPattern, (match, thinkContent) => {
      return `[THINKING: ${thinkContent.trim()}]`
    })

    // Replace <search> tags
    parsedContent = parsedContent.replace(searchPattern, (match, searchQuery) => {
      return `[SEARCH: ${searchQuery.trim()}]`
    })

    // Replace <code> tags
    parsedContent = parsedContent.replace(codePattern, (match, lang, code) => {
      return `[CODE(${lang}): ${code.trim()}]`
    })

    return parsedContent
  }

  const renderContent = () => {
    if (message.type === 'thinking' && message.metadata?.thinkingContent) {
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-purple-300">Thinking</span>
            <button
              onClick={() => setIsThinkingCollapsed(!isThinkingCollapsed)}
              className="text-[#6B6B6B] hover:text-white transition-colors"
            >
              {isThinkingCollapsed ? (
                <ChevronRight className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
            </button>
          </div>
          
          {!isThinkingCollapsed && (
            <div className="bg-[#1A1A1A] border border-[#3A3A3A] rounded-lg p-3 text-sm text-[#B4B4B4]">
              <div className="whitespace-pre-wrap break-words overflow-wrap-anywhere">{message.metadata.thinkingContent}</div>
            </div>
          )}
          
          <div className="whitespace-pre-wrap break-words overflow-wrap-anywhere">{message.content}</div>
        </div>
      )
    }

    if (message.type === 'search' && message.metadata?.searchQuery) {
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-blue-300">Search</span>
            <code className="text-xs bg-[#1A1A1A] px-2 py-1 rounded">
              {message.metadata.searchQuery}
            </code>
          </div>
          
          {message.metadata.searchResults && message.metadata.searchResults.length > 0 && (
            <div className="bg-[#1A1A1A] border border-[#3A3A3A] rounded-lg p-3">
              <div className="text-xs text-[#6B6B6B] mb-2">
                Found {message.metadata.searchResults.length} results
              </div>
              {message.metadata.searchResults.slice(0, 3).map((result, index) => (
                <div key={index} className="text-sm text-[#B4B4B4] mb-1">
                  • {typeof result === 'string' ? result : (result as any)?.title || 'Result'}
                </div>
              ))}
            </div>
          )}
          
          <div className="whitespace-pre-wrap break-words overflow-wrap-anywhere">{message.content}</div>
        </div>
      )
    }

    if (message.type === 'analyze' && message.metadata?.analysisTarget) {
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-green-400" />
            <span className="text-sm font-medium text-green-300">Analysis</span>
            <code className="text-xs bg-[#1A1A1A] px-2 py-1 rounded">
              {message.metadata.analysisTarget}
            </code>
          </div>
          <div className="whitespace-pre-wrap break-words overflow-wrap-anywhere">{message.content}</div>
        </div>
      )
    }

    if (message.type === 'code' && message.metadata?.codeLanguage) {
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Code className="w-4 h-4 text-orange-400" />
            <span className="text-sm font-medium text-orange-300">Code</span>
            <code className="text-xs bg-[#1A1A1A] px-2 py-1 rounded">
              {message.metadata.codeLanguage}
            </code>
          </div>
          <div className="bg-[#1A1A1A] border border-[#3A3A3A] rounded-lg p-3 font-mono text-sm overflow-x-auto">
            <pre className="whitespace-pre-wrap">{message.content}</pre>
          </div>
        </div>
      )
    }

    // Parse content for inline special syntax
    const hasSpecialSyntax = /<(think|search|code|analyze)/.test(message.content)
    if (hasSpecialSyntax) {
      return (
        <div className="whitespace-pre-wrap break-words overflow-wrap-anywhere">
          {parseMessageContent(message.content)}
        </div>
      )
    }

    // Default content rendering
    return (
      <div className="whitespace-pre-wrap break-words overflow-wrap-anywhere">
        {message.content}
      </div>
    )
  }

  return (
    <div className="flex flex-col">
      <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed break-words ${isChatOnly ? 'max-w-[95%]' : 'max-w-[85%]'} min-w-[120px] shadow-lg ${
            message.role === 'user'
              ? 'bg-[#3A3A3A] text-white rounded-br-md'
              : 'bg-[#2A2A2A] text-white rounded-bl-md border border-[#3A3A3A]'
          }`}
        >
          {/* Message Type Header */}
          {message.type && message.type !== 'text' && message.role === 'assistant' && (
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-[#3A3A3A]">
              {getMessageIcon()}
              <span className="text-xs font-medium capitalize text-[#B4B4B4]">
                {message.type}
              </span>
              {message.metadata?.duration && (
                <div className="flex items-center gap-1 text-xs text-[#6B6B6B] ml-auto">
                  <Clock className="w-3 h-3" />
                  {message.metadata.duration}ms
                </div>
              )}
            </div>
          )}
          
          {/* Message Content */}
          <div className="w-full">
            {renderContent()}
          </div>
          
          {/* Status Indicator */}
          {getStatusIndicator()}
        </div>
      </div>
      
      {/* Timestamp */}
      <div className={`text-xs text-[#6B6B6B] mt-1 px-1 ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
        {formatTimestamp(message.timestamp)}
      </div>
    </div>
  )
}