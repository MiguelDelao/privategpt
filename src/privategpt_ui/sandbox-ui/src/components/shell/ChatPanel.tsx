"use client"

import React from "react"
import { ChevronRight, Send, CheckCircle, Maximize2, MessageSquare, Trash2, Pin, MoreVertical } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useChatStore, ChatMessage } from "@/stores/chatStore"
import { MessageRenderer } from "./MessageRenderer"
import { ChatInput } from "./ChatInput"


interface ChatPanelProps {
  collapseButton?: React.ReactNode
}

export function ChatPanel({ collapseButton }: ChatPanelProps = {}) {
  const [currentTool, setCurrentTool] = useState<'none' | 'command-loading' | 'command-complete'>('none')
  const [toolFadeState, setToolFadeState] = useState('') // 'fade-out', 'fade-in'
  const [userScrolledUp, setUserScrolledUp] = useState(false)
  const [showSessionMenu, setShowSessionMenu] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  
  const {
    getActiveSession,
    createSession,
    addMessage,
    addThinkingMessage,
    setActiveSession,
    getRecentSessions,
    activeSessionId
  } = useChatStore()
  
  const activeSession = getActiveSession()
  const recentSessions = getRecentSessions()
  const messages = activeSession?.messages || []
  
  // Auto-create session if none exists
  useEffect(() => {
    if (!activeSessionId && !activeSession) {
      createSession('Legal Assistant Chat')
    }
  }, [activeSessionId, activeSession, createSession])

  const scrollToBottom = () => {
    if (!userScrolledUp) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }

  const checkIfUserScrolledUp = () => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current
      const isAtBottom = scrollHeight - scrollTop <= clientHeight + 50 // 50px threshold
      setUserScrolledUp(!isAtBottom)
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSlashCommand = (commandName: string, args: string[]) => {
    if (!activeSession) return

    switch (commandName) {
      case '/analyze':
        addMessage(activeSession.id, {
          role: "assistant",
          content: `🔍 **Document Analysis**\n\nAnalyzing ${args.length > 0 ? args.join(' ') : 'current document'}...\n\n**Findings:**\n• Legal compliance: ✅ Standard clauses identified\n• Risk level: 🟡 Medium - requires review\n• Recommendations: Consider strengthening liability clauses\n\n*This is a demo analysis. Real implementation would connect to AI analysis service.*`,
          type: "analyze",
          metadata: {
            analysisTarget: args.length > 0 ? args.join(' ') : 'Current Document',
            status: "complete"
          }
        })
        break

      case '/suggest':
        addMessage(activeSession.id, {
          role: "assistant", 
          content: `💡 **AI Suggestions**\n\nHere are improvement suggestions for ${args.length > 0 ? args.join(' ') : 'the current document'}:\n\n1. **Clarity Enhancement**: Use more specific terminology\n2. **Legal Protection**: Add force majeure clause\n3. **Compliance**: Include GDPR compliance section\n4. **Structure**: Reorganize sections for better flow\n\n*These are demo suggestions. Real implementation would use advanced AI analysis.*`,
          type: "analyze"
        })
        break


      case '/export':
        const format = args[0] || 'pdf'
        addMessage(activeSession.id, {
          role: "assistant",
          content: `📄 **Export Document**\n\nExporting current document as ${format.toUpperCase()}...\n\n✅ Export completed!\n📎 Download ready: document.${format}\n\n*This is a demo export. Real implementation would generate and download the actual file.*`
        })
        break

      case '/help':
        const specificCommand = args[0]
        if (specificCommand) {
          addMessage(activeSession.id, {
            role: "assistant",
            content: `ℹ️ **Help: ${specificCommand}**\n\nCommand details and usage examples would be shown here.\n\n*Real implementation would show comprehensive help for each command.*`
          })
        } else {
          addMessage(activeSession.id, {
            role: "assistant",
            content: `🛠️ **Available Commands**\n\n• \`/analyze [text]\` - Analyze document or text\n• \`/suggest [text]\` - Get improvement suggestions\n• \`/export [format]\` - Export current document\n• \`/search <query>\` - Search all documents\n• \`/new [type]\` - Create new document\n• \`/help [command]\` - Show help\n\n**Tips:**\n• Type \`/\` to see command suggestions\n• Use ↑↓ arrows to navigate commands\n• Press Enter or Tab to select a command`
          })
        }
        break

      case '/search':
        const query = args.join(' ')
        addMessage(activeSession.id, {
          role: "assistant",
          content: `🔍 **Search Results**\n\n${query ? `Searching for: "${query}"` : 'Please provide a search query'}\n\n${query ? '• Contract Template - Employment\n• NDA Template - Standard\n• Recent Document - Client Agreement\n\n*Real implementation would show actual search results.*' : 'Usage: `/search <your query>`'}`,
          type: "search",
          metadata: {
            searchQuery: query,
            searchResults: []
          }
        })
        break

      case '/new':
        const docType = args[0] || 'contract'
        addMessage(activeSession.id, {
          role: "assistant",
          content: `📝 **Create New Document**\n\nCreating new ${docType}...\n\n✅ Document created successfully!\n📄 New document opened in editor.\n\n*Available types: contract, nda, agreement, memo*\n*Usage: \`/new [type]\`*`
        })
        break

      default:
        addMessage(activeSession.id, {
          role: "assistant",
          content: `❌ **Unknown Command**\n\nCommand \`${commandName}\` not recognized.\n\nType \`/help\` to see available commands.`
        })
    }
  }

  const handleSend = (message: string, command?: any) => {
    if (!message.trim() || !activeSession) return

    // Add user message
    addMessage(activeSession.id, {
      role: "user",
      content: message.trim(),
      type: command ? 'command' : 'text',
      metadata: command ? { command: command.command } : undefined
    })

    const messageText = message.trim().toLowerCase()
    setUserScrolledUp(false) // Reset scroll position

    // Handle slash commands
    if (command) {
      setTimeout(() => {
        handleSlashCommand(command.command, message.split(' ').slice(1))
      }, 500)
      return
    }

    // Check if user typed "tool" to trigger demo
    if (messageText === "tool") {
      // Prevent multiple tool executions
      if (currentTool !== 'none') return
      
      setCurrentTool('command-loading')
      setToolFadeState('')
      
      // Simulate tool processing
      setTimeout(() => {
        setCurrentTool('command-complete')
        setToolFadeState('fade-in')
        
        addMessage(activeSession.id, {
          role: "assistant",
          content: "✅ Analysis complete! I've analyzed the document and found key areas for review:\n\n• **Legal compliance**: All clauses appear standard\n• **Risk assessment**: Low to medium risk detected\n• **Recommendations**: Consider reviewing liability sections\n\nWhat would you like me to focus on next?",
          type: "analyze",
          metadata: {
            analysisTarget: "Current Document",
            status: "complete"
          }
        })
        
        // Clear tool state after completion
        setTimeout(() => {
          setCurrentTool('none')
          setToolFadeState('')
        }, 2000)
      }, 1500)
    } else if (messageText.startsWith("<think>")) {
      // Handle thinking syntax
      const thinkingContent = messageText.slice(7, -8) // Remove <think> and </think>
      addThinkingMessage(
        activeSession.id,
        "Let me think about this...",
        thinkingContent || "Processing your request and considering the best approach."
      )
    } else {
      // Normal response
      setTimeout(() => {
        addMessage(activeSession.id, {
          role: "assistant",
          content: "I understand your question. This is a demo response to show the chat functionality working. I can help you with legal document analysis, contract review, and compliance questions."
        })
      }, 1000)
    }
  }


  return (
    <aside className="h-full w-full bg-[#171717] border-l border-[#2A2A2A] flex flex-col overflow-hidden">
      {/* Enhanced Header with Session Controls */}
      <header className="h-12 flex items-center justify-between px-4 border-b border-[#2A2A2A] flex-shrink-0">
        <div className="flex items-center gap-3">
          {/* Chevron button moved to the left */}
          {collapseButton && (
            <div className="flex items-center">
              {collapseButton}
            </div>
          )}
          
          <div className="relative">
            <button
              onClick={() => setShowSessionMenu(!showSessionMenu)}
              className="flex items-center gap-2 text-[#B4B4B4] hover:text-white transition-colors p-1.5 rounded-md hover:bg-[#2A2A2A]"
              title="Chat sessions"
            >
              <MessageSquare className="w-4 h-4" />
              <span className="text-sm font-medium truncate max-w-32">
                {activeSession?.title || 'New Chat'}
              </span>
            </button>
            
            {/* Session Menu */}
            {showSessionMenu && (
              <div className="absolute top-10 left-0 z-50 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg shadow-xl min-w-64 max-h-80 overflow-y-auto py-2">
                <div className="px-3 py-1 text-xs text-[#6B6B6B] uppercase font-medium">Recent Sessions</div>
                
                <button
                  onClick={() => { createSession('New Chat'); setShowSessionMenu(false); }}
                  className="w-full text-left px-3 py-2 text-sm text-[#B4B4B4] hover:bg-[#3A3A3A] hover:text-white transition-colors flex items-center gap-2"
                >
                  <MessageSquare className="w-4 h-4" />
                  New Chat
                </button>
                
                <div className="border-t border-[#3A3A3A] my-1"></div>
                
                {recentSessions.slice(0, 8).map((session) => (
                  <button
                    key={session.id}
                    onClick={() => { setActiveSession(session.id); setShowSessionMenu(false); }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-[#3A3A3A] transition-colors flex items-center justify-between group ${
                      session.id === activeSessionId ? 'text-white bg-[#3A3A3A]' : 'text-[#B4B4B4]'
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="truncate font-medium">{session.title}</div>
                      <div className="text-xs text-[#6B6B6B]">
                        {session.metadata.messageCount} messages • {new Date(session.modified).toLocaleDateString()}
                      </div>
                    </div>
                    {session.metadata.isPinned && (
                      <Pin className="w-3 h-3 text-[#6B6B6B] flex-shrink-0" />
                    )}
                  </button>
                ))}
                
                {recentSessions.length === 0 && (
                  <div className="px-3 py-4 text-center text-[#6B6B6B] text-sm">
                    No recent sessions
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        
      </header>

      {/* Messages */}
      <div 
        ref={messagesContainerRef}
        onScroll={checkIfUserScrolledUp}
        className="flex-1 overflow-y-auto overflow-x-hidden p-4"
        style={{
          scrollbarWidth: 'thin',
          scrollbarColor: '#3A3A3A transparent'
        }}
      >
        {/* Tool Indicator */}
        {currentTool !== 'none' && (
          <div className="flex mb-4">
            <div className={`rounded-xl px-4 py-3 w-full max-w-[85%] min-w-[200px] shadow-lg border transition-all duration-300 bg-[#2A2A2A] border-[#3A3A3A] ${toolFadeState === 'fade-in' ? 'fade-in' : ''}`}>
              <div className="flex items-center gap-2 text-sm">
                {currentTool === 'command-loading' ? (
                  <>
                    <div className="w-4 h-4 flex-shrink-0">
                      <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                    <span className="font-medium text-gray-300 shimmer-effect">Document Analyzer</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 flex-shrink-0 text-green-400" />
                    <span className="font-medium text-gray-300">Document Analyzer</span>
                  </>
                )}
              </div>
              <div className="text-xs mt-1">
                {currentTool === 'command-loading' ? (
                  <span className="text-gray-400 shimmer-effect">Analyzing document...</span>
                ) : (
                  <span className="text-gray-400">Analysis complete</span>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="space-y-4">
          {messages.map((message) => (
            <MessageRenderer 
              key={message.id} 
              message={message} 
              isChatOnly={false}
            />
          ))}
        </div>
        
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input with Slash Commands */}
      <ChatInput 
        onSendMessage={handleSend}
        disabled={currentTool !== 'none'}
        placeholder="Ask about legal documents, contracts, compliance, or use / for commands..."
      />
    </aside>
  )
} 