"use client"

import { MessageSquare, Layout } from "lucide-react"
import { ViewMode } from "@/hooks/useSimpleViews"

interface SimpleViewSwitcherProps {
  currentView: ViewMode
  onViewChange: (view: ViewMode) => void
}

export function SimpleViewSwitcher({ currentView, onViewChange }: SimpleViewSwitcherProps) {
  return (
    <div className="flex flex-col gap-2 p-2">
      <button
        onClick={() => onViewChange('workspace')}
        className={`flex items-center justify-center w-10 h-10 rounded-lg transition-colors ${
          currentView === 'workspace'
            ? 'bg-blue-600 text-white'
            : 'text-[#B4B4B4] hover:text-white hover:bg-[#2A2A2A]'
        }`}
        title="Workspace View"
      >
        <Layout className="w-5 h-5" />
      </button>
      
      <button
        onClick={() => onViewChange('chat-only')}
        className={`flex items-center justify-center w-10 h-10 rounded-lg transition-colors ${
          currentView === 'chat-only'
            ? 'bg-blue-600 text-white'
            : 'text-[#B4B4B4] hover:text-white hover:bg-[#2A2A2A]'
        }`}
        title="Chat Only View"
      >
        <MessageSquare className="w-5 h-5" />
      </button>
    </div>
  )
}