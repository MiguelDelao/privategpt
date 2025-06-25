"use client"

import { useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  isToolCall?: boolean
  toolName?: string
}

interface MessagesListProps {
  messages: Message[]
  className?: string
}

export function MessagesList({ messages, className = "" }: MessagesListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      transition={{ duration: 0.6, ease: "easeInOut" }}
      className={`flex-1 overflow-y-auto px-4 py-6 ${className}`}
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
                    {message.isToolCall ? (
                      <div className="flex items-center gap-2 text-blue-600">
                        <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                        <span className="font-medium">{message.content}</span>
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap">
                        {message.content}
                        {message.isStreaming && (
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
  )
}