"use client"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Copy, RefreshCw, Check, User, Bot, Minimize2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { useState, useEffect } from "react"

interface Message {
  id: string
  content: string
  role: "user" | "assistant" | "system"
  timestamp: Date
}

interface AIChatPanelProps {
  className?: string
  externalMessage?: string
  onExternalMessageProcessed?: () => void
  isMinimized?: boolean
  onToggleMinimize?: () => void
}

export function AIChatPanel({ 
  className, 
  externalMessage, 
  onExternalMessageProcessed,
  isMinimized = false,
  onToggleMinimize
}: AIChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content: "Hello! I'm your AI legal assistant. I can help you with document drafting, review, and legal analysis. How can I assist you today?",
      role: "assistant",
      timestamp: new Date(Date.now() - 60000)
    }
  ])

  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (externalMessage) {
      setInput(externalMessage)
      onExternalMessageProcessed?.()
    }
  }, [externalMessage, onExternalMessageProcessed])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: "user",
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [...messages, userMessage].map(m => ({
            role: m.role,
            content: m.content
          }))
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.content,
        role: "assistant",
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        content: "Sorry, I encountered an error. Please try again.",
        role: "assistant",
        timestamp: new Date()
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const MessageComponent = ({ message }: { message: Message }) => {
    const isUser = message.role === "user"
    
    return (
      <div className={cn("flex gap-3 mb-4", isUser && "flex-row-reverse")}>
        <div className="flex-shrink-0">
          <div className={cn(
            "h-7 w-7 rounded-full flex items-center justify-center text-xs",
            isUser ? "bg-primary text-primary-foreground" : "bg-muted"
          )}>
            {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
          </div>
        </div>
        
        <div className={cn(
          "rounded-lg p-3 max-w-[85%] text-sm",
          isUser 
            ? "bg-primary text-primary-foreground ml-auto" 
            : "bg-muted"
        )}>
          <div className="whitespace-pre-wrap">{message.content}</div>
          <div className={cn(
            "text-xs mt-2 opacity-70",
            isUser ? "text-right" : "text-left"
          )}>
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
          
          {!isUser && (
            <div className="flex gap-1 mt-2 opacity-60">
              <Button size="sm" variant="ghost" className="h-6 w-6 p-0 hover:opacity-100">
                <Copy className="h-3 w-3" />
              </Button>
              <Button size="sm" variant="ghost" className="h-6 w-6 p-0 hover:opacity-100">
                <RefreshCw className="h-3 w-3" />
              </Button>
              <Button size="sm" variant="ghost" className="h-6 w-6 p-0 hover:opacity-100">
                <Check className="h-3 w-3" />
              </Button>
            </div>
          )}
        </div>
      </div>
    )
  }

  if (isMinimized) {
    return (
      <div className={cn("w-12 h-full bg-background border-l flex flex-col items-center justify-start pt-4", className)}>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={onToggleMinimize}
        >
          <Bot className="h-4 w-4" />
        </Button>
      </div>
    )
  }

  return (
    <div className={cn("flex h-full w-80 flex-col bg-background border-l", className)}>
      {/* Header */}
      <div className="flex h-12 items-center justify-between px-4 border-b bg-muted/50">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4" />
          <h2 className="font-medium text-sm">AI Assistant</h2>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={onToggleMinimize}
        >
          <Minimize2 className="h-3 w-3" />
        </Button>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        {messages.map((message) => (
          <MessageComponent key={message.id} message={message} />
        ))}
        {isLoading && (
          <div className="flex gap-3 mb-4">
            <div className="flex-shrink-0">
              <div className="h-7 w-7 rounded-full flex items-center justify-center bg-muted">
                <Bot className="h-4 w-4" />
              </div>
            </div>
            <div className="bg-muted rounded-lg p-3 text-sm">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Input */}
      <div className="p-4 border-t bg-muted/20">
        <div className="flex gap-2">
          <Textarea
            placeholder="Ask about legal documents, clauses, or get drafting help..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="min-h-[60px] resize-none text-sm"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
          />
          <Button 
            size="sm" 
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-3 self-end"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}