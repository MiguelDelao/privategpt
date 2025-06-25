"use client"

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Plus, 
  MessageSquare, 
  Search, 
  MoreHorizontal, 
  Edit3, 
  Trash2, 
  Archive, 
  Pin, 
  Calendar,
  Clock,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import { useChatStore } from '@/stores/chatStore'
import { ChatSession } from '@/types/chat'
import { formatTimeAgo } from '@/lib/utils'

interface ConversationSidebarProps {
  isCollapsed: boolean
  onToggleCollapse: () => void
}

interface ConversationItemProps {
  conversation: ChatSession
  isActive: boolean
  onClick: () => void
  onEdit: (id: string, title: string) => void
  onDelete: (id: string) => void
  onArchive: (id: string) => void
  onPin: (id: string) => void
}

function ConversationItem({ 
  conversation, 
  isActive, 
  onClick, 
  onEdit, 
  onDelete, 
  onArchive, 
  onPin 
}: ConversationItemProps) {
  const [showMenu, setShowMenu] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(conversation.title)
  const menuRef = useRef<HTMLDivElement>(null)
  const editInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isEditing && editInputRef.current) {
      editInputRef.current.focus()
      editInputRef.current.select()
    }
  }, [isEditing])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleEdit = () => {
    setIsEditing(true)
    setShowMenu(false)
  }

  const handleSaveEdit = () => {
    if (editTitle.trim() && editTitle !== conversation.title) {
      onEdit(conversation.id, editTitle.trim())
    }
    setIsEditing(false)
  }

  const handleCancelEdit = () => {
    setEditTitle(conversation.title)
    setIsEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveEdit()
    } else if (e.key === 'Escape') {
      handleCancelEdit()
    }
  }

  const lastMessage = conversation.messages[conversation.messages.length - 1]
  const timeAgo = formatTimeAgo(new Date(conversation.modified))

  return (
    <div
      className={`group relative flex items-center p-3 rounded-lg cursor-pointer transition-all hover:bg-[#2A2A2A] ${
        isActive ? 'bg-[#2A2A2A] border-l-2 border-blue-500' : 'border-l-2 border-transparent'
      }`}
      onClick={onClick}
    >
      {/* Conversation Icon */}
      <div className="flex-shrink-0 mr-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
          isActive ? 'bg-blue-600' : 'bg-[#3A3A3A]'
        }`}>
          <MessageSquare className="w-4 h-4 text-white" />
        </div>
      </div>

      {/* Conversation Content */}
      <div className="flex-1 min-w-0">
        {isEditing ? (
          <input
            ref={editInputRef}
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onBlur={handleSaveEdit}
            onKeyDown={handleKeyDown}
            className="w-full bg-[#1A1A1A] text-white text-sm font-medium px-2 py-1 rounded border border-[#3A3A3A] focus:outline-none focus:border-blue-500"
          />
        ) : (
          <div className="text-sm font-medium text-white truncate">
            {conversation.metadata.isPinned && <Pin className="inline w-3 h-3 mr-1 text-yellow-500" />}
            {conversation.title}
          </div>
        )}
        
        <div className="flex items-center justify-between mt-1">
          <div className="text-xs text-[#B4B4B4] truncate flex-1">
            {lastMessage ? (
              <span className="truncate">
                {lastMessage.role === 'user' ? 'You: ' : ''}
                {lastMessage.content.substring(0, 40)}
                {lastMessage.content.length > 40 ? '...' : ''}
              </span>
            ) : (
              'No messages yet'
            )}
          </div>
          <div className="text-xs text-[#666] ml-2 flex-shrink-0">
            {timeAgo}
          </div>
        </div>

        {/* Message count and model info */}
        <div className="flex items-center justify-between mt-1">
          <div className="text-xs text-[#666]">
            {conversation.metadata.messageCount} messages
            {conversation.currentModel && (
              <span className="ml-2 px-1.5 py-0.5 bg-[#3A3A3A] rounded text-[10px]">
                {conversation.currentModel.split(':')[0]}
              </span>
            )}
          </div>
          {conversation.metadata.totalTokens && (
            <div className="text-xs text-[#666]">
              {conversation.metadata.totalTokens.toLocaleString()} tokens
            </div>
          )}
        </div>
      </div>

      {/* More menu */}
      <div className="relative" ref={menuRef}>
        <button
          onClick={(e) => {
            e.stopPropagation()
            setShowMenu(!showMenu)
          }}
          className={`p-1 rounded hover:bg-[#3A3A3A] transition-colors ${
            showMenu ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
          }`}
        >
          <MoreHorizontal className="w-4 h-4 text-[#B4B4B4]" />
        </button>

        <AnimatePresence>
          {showMenu && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute right-0 top-8 w-48 bg-[#1A1A1A] border border-[#3A3A3A] rounded-lg shadow-xl z-50"
            >
              <div className="py-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleEdit()
                  }}
                  className="w-full text-left px-3 py-2 text-sm text-white hover:bg-[#2A2A2A] flex items-center gap-2"
                >
                  <Edit3 className="w-4 h-4" />
                  Rename
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onPin(conversation.id)
                    setShowMenu(false)
                  }}
                  className="w-full text-left px-3 py-2 text-sm text-white hover:bg-[#2A2A2A] flex items-center gap-2"
                >
                  <Pin className="w-4 h-4" />
                  {conversation.metadata.isPinned ? 'Unpin' : 'Pin'}
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onArchive(conversation.id)
                    setShowMenu(false)
                  }}
                  className="w-full text-left px-3 py-2 text-sm text-white hover:bg-[#2A2A2A] flex items-center gap-2"
                >
                  <Archive className="w-4 h-4" />
                  {conversation.metadata.isArchived ? 'Unarchive' : 'Archive'}
                </button>
                <hr className="border-[#3A3A3A] my-1" />
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDelete(conversation.id)
                    setShowMenu(false)
                  }}
                  className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-[#2A2A2A] flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export function ConversationSidebar({ isCollapsed, onToggleCollapse }: ConversationSidebarProps) {
  const {
    getAllSessions,
    activeSessionId,
    setActiveSession,
    createSession,
    updateSessionTitle,
    deleteSession,
    archiveSession,
    pinSession,
    syncWithBackend,
    isSyncing
  } = useChatStore()

  // Get all non-archived conversations
  const conversations = getAllSessions().filter(c => !c.metadata.isArchived)

  // Sync with backend on mount
  useEffect(() => {
    // Only sync once on mount, not on every re-render
    syncWithBackend().catch(() => {
      // Silently handle sync errors - the sidebar can work with cached data
    })
  }, []) // Remove syncWithBackend from deps to prevent re-running

  const handleNewConversation = async () => {
    try {
      const sessionId = await createSession('New Chat')
      setActiveSession(sessionId)
    } catch (error) {
      console.error('Failed to create new conversation:', error)
    }
  }

  const handleEditConversation = async (id: string, title: string) => {
    try {
      await updateSessionTitle(id, title)
    } catch (error) {
      console.error('Failed to update conversation title:', error)
    }
  }

  const handleDeleteConversation = async (id: string) => {
    if (confirm('Are you sure you want to delete this conversation?')) {
      try {
        await deleteSession(id)
      } catch (error) {
        console.error('Failed to delete conversation:', error)
      }
    }
  }

  const handleArchiveConversation = async (id: string) => {
    try {
      await archiveSession(id)
    } catch (error) {
      console.error('Failed to archive conversation:', error)
    }
  }

  const handlePinConversation = async (id: string) => {
    try {
      await pinSession(id)
    } catch (error) {
      console.error('Failed to pin conversation:', error)
    }
  }

  if (isCollapsed) {
    return (
      <div className="w-12 bg-[#1A1A1A] border-r border-[#2A2A2A] flex flex-col items-center py-4 h-full">
        <button
          onClick={onToggleCollapse}
          className="p-2 rounded-lg hover:bg-[#2A2A2A] text-[#B4B4B4] hover:text-white transition-colors mb-4"
          title="Expand sidebar"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
        
        <button
          onClick={handleNewConversation}
          className="p-2 rounded-lg hover:bg-[#2A2A2A] text-[#B4B4B4] hover:text-white transition-colors mb-4"
          title="New conversation"
        >
          <Plus className="w-5 h-5" />
        </button>

        <div className="flex-1 flex flex-col gap-2 overflow-y-auto sidebar-scroll">
          {getRecentSessions().slice(0, 8).map((conversation) => (
            <button
              key={conversation.id}
              onClick={() => setActiveSession(conversation.id)}
              className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                activeSessionId === conversation.id 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-[#3A3A3A] text-[#B4B4B4] hover:text-white hover:bg-[#4A4A4A]'
              }`}
              title={conversation.title}
            >
              <MessageSquare className="w-4 h-4" />
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="w-80 bg-[#1A1A1A] border-r border-[#2A2A2A] flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-[#2A2A2A]">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Conversations</h2>
          <div className="flex items-center gap-2">
            {isSyncing && (
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            )}
            <button
              onClick={handleNewConversation}
              className="p-2 rounded-lg hover:bg-[#2A2A2A] text-[#B4B4B4] hover:text-white transition-colors"
              title="New conversation"
            >
              <Plus className="w-5 h-5" />
            </button>
            <button
              onClick={onToggleCollapse}
              className="p-2 rounded-lg hover:bg-[#2A2A2A] text-[#B4B4B4] hover:text-white transition-colors"
              title="Collapse sidebar"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto sidebar-scroll" style={{ minHeight: 0 }}>
        {conversations.length === 0 ? (
          <div className="p-8 text-center">
            <MessageSquare className="w-12 h-12 text-[#666] mx-auto mb-4" />
            <h3 className="text-white font-medium mb-2">No conversations yet</h3>
            <p className="text-[#B4B4B4] text-sm mb-4">
              Start a new conversation to get started
            </p>
            <button
              onClick={handleNewConversation}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Start New Conversation
            </button>
          </div>
        ) : (
          <div className="p-2">
            {conversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                isActive={activeSessionId === conversation.id}
                onClick={() => setActiveSession(conversation.id)}
                onEdit={handleEditConversation}
                onDelete={handleDeleteConversation}
                onArchive={handleArchiveConversation}
                onPin={handlePinConversation}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer with stats */}
      <div className="p-4 border-t border-[#2A2A2A] text-xs text-[#666]">
        <div className="flex justify-between">
          <span>{conversations.length} conversations</span>
          <span>
            {conversations.reduce((total, conv) => total + conv.metadata.messageCount, 0)} messages
          </span>
        </div>
      </div>
    </div>
  )
}