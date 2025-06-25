"use client"

import { motion } from "framer-motion"

interface DemoButton {
  label: string
  message: string
  response: string
  hasToolCall?: boolean
}

interface WelcomeScreenProps {
  onDemoClick: (demo: DemoButton) => void
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

export function WelcomeScreen({ onDemoClick }: WelcomeScreenProps) {
  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.6, ease: "easeInOut" }}
      className="flex flex-col items-center justify-center flex-1 px-4"
    >
      <div className="flex flex-col items-center text-center max-w-2xl mx-auto mb-12">
        <h1 className="text-4xl font-bold text-white mb-3">Good afternoon, M</h1>
        <p className="text-xl text-[#B4B4B4] mb-12">
          How can I help you today?
        </p>
      </div>

      {/* Demo buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-3xl mb-8">
        {demoButtons.map((demo, index) => (
          <button
            key={index}
            onClick={() => onDemoClick(demo)}
            className="p-4 border border-[#2A2A2A] bg-[#1A1A1A] rounded-xl hover:border-[#3A3A3A] hover:bg-[#2A2A2A] transition-colors text-left"
          >
            <div className="font-medium text-white mb-1">{demo.label}</div>
            <div className="text-sm text-[#B4B4B4] line-clamp-2">{demo.message}</div>
          </button>
        ))}
      </div>
    </motion.div>
  )
}

export type { DemoButton }