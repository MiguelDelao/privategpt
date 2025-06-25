"use client"

import { ReactNode, useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { MessageSquare, Layout, Sparkles, Search } from "lucide-react"
import { useSimpleViews } from "@/hooks/useSimpleViews"

interface ChatGPTStyleViewProps {
  chat: ReactNode
  onTransitionToWorkspace: () => void
}

const centerToSideVariants = {
  // Initial center state (like ChatGPT)
  center: {
    x: 0,
    y: 0,
    scale: 1,
    width: "100%",
    maxWidth: "768px",
    opacity: 1,
    transition: {
      duration: 0.3,
      ease: "easeOut" as const
    }
  },
  // Transition state - scaling down and moving right
  transitioning: {
    x: "60vw",
    y: 0,
    scale: 0.8,
    width: "320px",
    maxWidth: "320px",
    opacity: 0.8,
    transition: {
      duration: 0.4,
      ease: "easeOut" as const
    }
  },
  // Final state - disappeared (will be replaced by workspace)
  exit: {
    x: "100vw",
    scale: 0.6,
    opacity: 0,
    transition: {
      duration: 0.3,
      ease: "easeOut" as const
    }
  }
}

const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: { duration: 0.3 }
  },
  exit: { 
    opacity: 0,
    transition: { duration: 0.2 }
  }
}

const welcomeVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: {
      duration: 0.3,
      ease: "easeOut" as const,
      delay: 0.1
    }
  },
  exit: { 
    opacity: 0, 
    y: -20,
    transition: { duration: 0.2 }
  }
}

export function ChatGPTStyleView({ chat, onTransitionToWorkspace }: ChatGPTStyleViewProps) {
  const [showWelcome, setShowWelcome] = useState(true)
  const [showChat, setShowChat] = useState(false)

  const handleStartConversation = () => {
    setShowWelcome(false)
    // Show the chat interface instead of transitioning to workspace
    setTimeout(() => {
      setShowChat(true)
    }, 300)
  }

  const handleSuggestedPrompt = (prompt: string) => {
    // Start conversation with the suggested prompt
    handleStartConversation()
  }

  return (
    <div className="h-full bg-[#171717] relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#171717] via-[#1A1A1A] to-[#171717] z-0" />

      <AnimatePresence mode="wait">
        {showWelcome && (
          // Welcome screen with suggestions (ChatGPT style)
          <motion.div
            key="welcome"
            className="flex items-center justify-center h-full p-8 relative z-10"
            variants={overlayVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <motion.div
              className="max-w-3xl w-full text-center"
              variants={welcomeVariants}
            >
              {/* Logo and title */}
              <div className="mb-12">
                <div className="flex items-center justify-center mb-6">
                  <div className="p-4 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl shadow-2xl">
                    <Sparkles className="w-8 h-8 text-white" />
                  </div>
                </div>
                <h1 className="text-4xl font-bold text-white mb-4">
                  Legal Assistant AI
                </h1>
                <p className="text-xl text-[#B4B4B4] max-w-2xl mx-auto leading-relaxed">
                  Your intelligent partner for legal document analysis, contract review, and compliance guidance.
                </p>
              </div>

              {/* Suggested prompts */}
              <motion.div
                className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, staggerChildren: 0.1 }}
              >
                {[
                  {
                    icon: "📄",
                    title: "Analyze Contract",
                    description: "Review my employment contract for key terms and potential issues"
                  },
                  {
                    icon: "🔍", 
                    title: "Legal Research",
                    description: "Research recent case law on intellectual property licensing"
                  },
                  {
                    icon: "✍️",
                    title: "Draft Document", 
                    description: "Help me draft an NDA for my consulting business"
                  },
                  {
                    icon: "⚖️",
                    title: "Compliance Check",
                    description: "Ensure my terms of service comply with GDPR requirements"
                  }
                ].map((prompt, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestedPrompt(prompt.description)}
                    className="p-6 bg-[#1A1A1A] border border-[#2A2A2A] rounded-xl text-left hover:bg-[#2A2A2A] hover:border-blue-500/50 transition-all group"
                  >
                    <div className="flex items-start gap-4">
                      <span className="text-2xl">{prompt.icon}</span>
                      <div>
                        <h3 className="font-semibold text-white mb-2 group-hover:text-blue-400 transition-colors">
                          {prompt.title}
                        </h3>
                        <p className="text-sm text-[#B4B4B4] group-hover:text-[#E5E5E5] transition-colors">
                          {prompt.description}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </motion.div>

              {/* Call to action */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
                className="flex flex-col items-center gap-4"
              >
                <button
                  onClick={handleStartConversation}
                  className="flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-medium shadow-xl hover:shadow-2xl transition-all"
                >
                  <MessageSquare className="w-5 h-5" />
                  Start a New Conversation
                </button>
                
                <button
                  onClick={onTransitionToWorkspace}
                  className="flex items-center gap-2 px-6 py-3 text-[#B4B4B4] hover:text-white border border-[#2A2A2A] hover:border-[#3A3A3A] rounded-xl transition-all"
                >
                  <Layout className="w-4 h-4" />
                  Or go to workspace
                </button>
              </motion.div>
            </motion.div>
          </motion.div>
        )}
        {showChat && (
          // Full-screen chat interface
          <motion.div
            key="chat-interface"
            className="h-full w-full relative z-10"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          >
            {chat}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}