"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Link from "next/link"
import { useRouter, usePathname } from "next/navigation"
import {
  FileText,
  Settings as SettingsIcon,
  MessageSquarePlus,
  Clock,
  Layout,
  LayoutDashboard,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Plus,
  Database,
  Folder,
  Rss,
  Shield,
  Search,
  MoreHorizontal,
  Edit3,
  Trash2,
  Archive,
  Pin,
  X
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useChatStore } from "@/stores/chatStore"
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog"

const navItems = [
  { id: "newchat", label: "New chat", icon: MessageSquarePlus, route: "/" },
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, route: "#", disabled: true },
  { id: "documents", label: "Documents", icon: FileText, route: "/documents" },
  { id: "test", label: "Test Chat", icon: Rss, route: "/test" },
  { id: "admin", label: "Admin", icon: Shield, route: "/admin" },
  { id: "settings", label: "Settings", icon: SettingsIcon, route: "/settings" },
]

// Helper function to format time relative to now
function formatTimeAgo(date: Date | string | number): string {
  const now = new Date()
  let dateObj: Date
  
  // Handle different date formats
  if (date instanceof Date) {
    dateObj = date
  } else if (typeof date === 'string') {
    dateObj = new Date(date)
  } else if (typeof date === 'number') {
    dateObj = new Date(date)
  } else {
    return 'Unknown'
  }
  
  // Check if date is valid
  if (isNaN(dateObj.getTime())) {
    return 'Unknown'
  }
  
  const diffMs = now.getTime() - dateObj.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return dateObj.toLocaleDateString()
}

const initialDataSources = [
  { id: "1", name: "Legal Database", type: "folder", description: "Case law and legal precedents", documentCount: 45 },
  { id: "2", name: "Contract Templates", type: "folder", description: "Standard contract templates", documentCount: 23 },
  { id: "3", name: "Regulatory Updates", type: "folder", description: "Latest regulatory changes", documentCount: 67 },
  { id: "4", name: "Client Files", type: "folder", description: "Confidential client documents", documentCount: 12 },
  { id: "5", name: "Legal Research", type: "folder", description: "Academic and research papers", documentCount: 34 },
]

interface ConversationItemProps {
  session: any
  isActive: boolean
  onSelect: (id: string) => Promise<void>
  onEdit: (id: string, title: string) => void
  onDelete: (id: string) => void
  onArchive: (id: string) => void
  onPin: (id: string) => void
}

function ConversationItem({ session, isActive, onSelect, onEdit, onDelete, onArchive, onPin }: ConversationItemProps) {
  const [showMenu, setShowMenu] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(session.title)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
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
    if (editTitle.trim() && editTitle !== session.title) {
      onEdit(session.id, editTitle.trim())
    }
    setIsEditing(false)
  }

  const handleCancelEdit = () => {
    setEditTitle(session.title)
    setIsEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveEdit()
    } else if (e.key === 'Escape') {
      handleCancelEdit()
    }
  }

  const lastMessage = session.messages[session.messages.length - 1]
  const timeAgo = formatTimeAgo(session.modified)

  return (
    <div className="group relative">
      <div
        onClick={() => onSelect(session.id)}
        className={cn(
          "w-full text-left p-2 rounded text-sm transition-colors relative cursor-pointer",
          isActive
            ? "bg-[#2A2A2A] text-white" 
            : "text-[#B4B4B4] hover:bg-[#2A2A2A] hover:text-white"
        )}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0 pr-2">
            {isEditing ? (
              <input
                ref={editInputRef}
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onBlur={handleSaveEdit}
                onKeyDown={handleKeyDown}
                className="w-full bg-[#1A1A1A] text-white text-sm px-1 py-0.5 rounded border border-[#3A3A3A] focus:outline-none focus:border-blue-500"
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <div className="font-medium mb-1 truncate flex items-center gap-1">
                {session.metadata.isPinned && <Pin className="w-3 h-3 text-yellow-500 flex-shrink-0" />}
                {session.title}
              </div>
            )}
            
            <div className="text-xs text-[#6B6B6B] mb-1">
              {timeAgo} • {session.metadata.messageCount} msgs
            </div>
            
            {lastMessage && (
              <div className="text-xs text-[#6B6B6B] truncate">
                {lastMessage.role === 'user' ? 'You: ' : ''}
                {lastMessage.content.substring(0, 40)}
                {lastMessage.content.length > 40 ? '...' : ''}
              </div>
            )}
          </div>
          
          <button
            onClick={(e) => {
              e.stopPropagation()
              setShowMenu(!showMenu)
            }}
            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-[#3A3A3A] rounded transition-all"
          >
            <MoreHorizontal className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Context Menu */}
      <AnimatePresence>
        {showMenu && (
          <motion.div
            ref={menuRef}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute right-0 top-8 w-36 bg-[#1A1A1A] border border-[#3A3A3A] rounded shadow-xl z-50"
          >
            <div className="py-1">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleEdit()
                }}
                className="w-full text-left px-3 py-1.5 text-xs text-white hover:bg-[#2A2A2A] flex items-center gap-2"
              >
                <Edit3 className="w-3 h-3" />
                Rename
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onPin(session.id)
                  setShowMenu(false)
                }}
                className="w-full text-left px-3 py-1.5 text-xs text-white hover:bg-[#2A2A2A] flex items-center gap-2"
              >
                <Pin className="w-3 h-3" />
                {session.metadata.isPinned ? 'Unpin' : 'Pin'}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onArchive(session.id)
                  setShowMenu(false)
                }}
                className="w-full text-left px-3 py-1.5 text-xs text-white hover:bg-[#2A2A2A] flex items-center gap-2"
              >
                <Archive className="w-3 h-3" />
                {session.metadata.isArchived ? 'Unarchive' : 'Archive'}
              </button>
              <hr className="border-[#3A3A3A] my-1" />
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setShowDeleteDialog(true)
                  setShowMenu(false)
                }}
                className="w-full text-left px-3 py-1.5 text-xs text-red-400 hover:bg-[#2A2A2A] flex items-center gap-2"
              >
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Conversation"
        description={`Are you sure you want to delete "${session.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="destructive"
        onConfirm={() => {
          onDelete(session.id)
        }}
      />
    </div>
  )
}

interface SidebarProps {
  isCollapsed?: boolean
  onToggleCollapse?: () => void
}

export function Sidebar({ isCollapsed = false, onToggleCollapse }: SidebarProps) {
  const router = useRouter()
  const pathname = usePathname()
  
  // Determine active state based on current pathname
  const getActiveFromPath = (path: string) => {
    // Find nav item that matches the current path
    const item = navItems.find(item => {
      if (item.route === '/' && path === '/') return true
      if (item.route !== '/' && path.startsWith(item.route)) return true
      return false
    })
    return item?.id || 'newchat'
  }
  
  const [active, setActive] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return getActiveFromPath(window.location.pathname)
    }
    return "newchat"
  })
  const [activeTab, setActiveTab] = useState<string>("history")
  const [dataSources, setDataSources] = useState(initialDataSources)
  // Removed search and filter state - no longer needed
  
  // Chat store integration
  const {
    sessions,
    activeSessionId,
    setActiveSession,
    createSession,
    getRecentSessions,
    getAllSessions,
    updateSessionTitle,
    deleteSession,
    archiveSession,
    pinSession,
    syncWithBackend,
    isSyncing
  } = useChatStore()
  
  // Get all non-archived conversations
  const filteredConversations = getAllSessions().filter(c => !c.metadata.isArchived)

  // Listen for data source updates from documents page
  useEffect(() => {
    const handleDataSourceUpdate = (event: CustomEvent<{ folders: any[] }>) => {
      const updatedSources = event.detail.folders.map((folder: any) => ({
        id: folder.id,
        name: folder.name,
        type: 'folder',
        description: `${folder.documentCount} documents`,
        documentCount: folder.documentCount
      }))
      setDataSources(updatedSources)
    }

    window.addEventListener('updateDataSources', handleDataSourceUpdate as EventListener)
    
    return () => {
      window.removeEventListener('updateDataSources', handleDataSourceUpdate as EventListener)
    }
  }, [])

  // Update active state when pathname changes
  useEffect(() => {
    const newActive = getActiveFromPath(pathname)
    setActive(newActive)
  }, [pathname])

  const handleNavClick = async (id: string) => {
    setActive(id)
    
    // Find the nav item and navigate to its route
    const navItem = navItems.find(item => item.id === id)
    if (!navItem) return
    
    // Special handling for new chat
    if (id === 'newchat') {
      // Clear active session - new session will be created when user sends first message
      await setActiveSession(null)
    }
    
    // Navigate to the route
    router.push(navItem.route)
  }


  return (
    <motion.aside 
      className="h-full bg-[#171717] text-text-primary flex flex-col border-r border-[#2A2A2A] overflow-hidden"
      initial={false}
      animate={{ width: isCollapsed ? 64 : 320 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
    >

      {/* Main Navigation */}
      <div className="p-4 flex-shrink-0">
        <div className="flex items-center justify-between mb-4">
          {/* Action buttons on the left - only show when expanded */}
          <AnimatePresence>
            {!isCollapsed && (
              <motion.div 
                className="flex items-center gap-1"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <button
                  className="p-1.5 rounded-lg hover:bg-[#2A2A2A] text-[#B4B4B4] hover:text-white transition-colors"
                  title="New Chat"
                >
                  <MessageSquarePlus className="w-4 h-4" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
          
          {isCollapsed && <div />} {/* Spacer when collapsed */}
          
          {/* Collapse button - always visible */}
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="p-1.5 rounded-lg hover:bg-[#2A2A2A] text-[#B4B4B4] hover:text-white transition-colors"
              title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          )}
        </div>

        <nav className="space-y-2">
          {navItems.map(({ id, label, icon: Icon, route, disabled }) => (
            <button
              key={id}
              onClick={() => !disabled && handleNavClick(id)}
              disabled={disabled}
              className={cn(
                "flex items-center gap-3 w-full text-left rounded-lg transition-colors",
                isCollapsed 
                  ? "justify-center px-2 py-4" 
                  : "px-3 py-2.5",
                disabled 
                  ? "text-[#666666] cursor-not-allowed opacity-50"
                  : active === id
                    ? "bg-[#2A2A2A] text-white"
                    : "text-[#B4B4B4] hover:bg-[#2A2A2A] hover:text-white"
              )}
              title={isCollapsed ? label : undefined}
            >
              <Icon size={isCollapsed ? 24 : 16} />
              {!isCollapsed && <span className="text-sm">{label}</span>}
            </button>
          ))}
        </nav>
      </div>

      {/* Content Area */}
      <AnimatePresence>
        {!isCollapsed && (
          <motion.div 
            className="flex-1 overflow-hidden flex flex-col min-h-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
          >
          {active === "documents" ? (
            <div className="px-4 py-6 text-center text-[#B4B4B4]">
              <FileText className="mx-auto mb-2 h-8 w-8" />
              <p>Document management coming soon...</p>
            </div>
          ) : (
            <div className="flex flex-col flex-1 min-h-0 px-4">
              {/* Tab Navigation */}
              <div className="flex border-b border-[#2A2A2A] mb-4 flex-shrink-0">
                {[
                  { id: "history", label: "History", icon: Clock },
                  { id: "files", label: "Files", icon: FileText },
                  { id: "data", label: "Data", icon: Database }
                ].map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setActiveTab(id)}
                    className={cn(
                      "flex items-center justify-center w-10 h-8 text-sm transition-colors border-b-2",
                      activeTab === id
                        ? "text-white border-blue-500"
                        : "text-[#B4B4B4] border-transparent hover:text-white"
                    )}
                    title={label}
                  >
                    <Icon size={14} />
                  </button>
                ))}
              </div>

            {/* Tab Content */}
            {activeTab === "history" && (
              <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
                
                {/* Conversations List */}
                <div className="flex-1 overflow-y-auto sidebar-scroll" style={{ height: '100%' }}>
                  {filteredConversations.length > 0 ? (
                    <div className="space-y-1">
                      {filteredConversations.map((session) => (
                        <ConversationItem
                          key={session.id}
                          session={session}
                          isActive={activeSessionId === session.id}
                          onSelect={async (id) => {
                            await setActiveSession(id)
                            // Navigate to chat page using Next.js router
                            router.push('/chat')
                          }}
                          onEdit={updateSessionTitle}
                          onDelete={deleteSession}
                          onArchive={archiveSession}
                          onPin={pinSession}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-[#6B6B6B]">
                      <MessageSquarePlus className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No conversations yet</p>
                        <button
                          onClick={async () => {
                            try {
                              const sessionId = await createSession()
                              await setActiveSession(sessionId)
                              // Navigate to chat page using Next.js router
                              router.push('/chat')
                            } catch (error) {
                              console.error('Failed to create conversation:', error)
                            }
                          }}
                          className="text-xs text-blue-400 hover:text-blue-300 mt-2 transition-colors"
                        >
                          Start your first conversation
                        </button>
                    </div>
                  )}
                </div>
                
                {/* Footer Stats */}
                <div className="px-3 py-2 border-t border-[#2A2A2A] text-xs text-[#6B6B6B] flex-shrink-0">
                  {filteredConversations.length} conversations
                </div>
              </div>
            )}

            {activeTab === "files" && (
              <div>
                <div className="text-xs font-medium text-[#B4B4B4] px-3 py-2 uppercase tracking-wider">
                  Recent Files
                </div>
                <div className="space-y-1">
                  <div className="text-center py-8 text-[#6B6B6B]">
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No files uploaded yet</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "data" && (
              <div>
                <div className="text-xs font-medium text-[#B4B4B4] px-3 py-2 uppercase tracking-wider">
                  Data Sources
                </div>
                <div className="space-y-1">
                  {dataSources.map((source) => (
                    <div
                      key={source.id}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-[#2A2A2A] transition-colors group"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <Folder className="w-4 h-4 text-[#B4B4B4]" />
                        <div className="min-w-0 flex-1">
                          <div className="text-white text-sm font-medium truncate">{source.name}</div>
                          <div className="text-xs text-[#6B6B6B] truncate">{source.description}</div>
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          // Dispatch custom event to attach data source to chat
                          const event = new CustomEvent('attachDataSource', {
                            detail: {
                              id: source.id,
                              name: source.name,
                              icon: '',
                              type: source.type
                            }
                          })
                          window.dispatchEvent(event)
                        }}
                        className="flex items-center justify-center w-6 h-6 rounded-full bg-[#3A3A3A] text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-[#4A4A4A]"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            </div>
          )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bottom spacing */}
      <div className="p-4"></div>
    </motion.aside>
  )
} 