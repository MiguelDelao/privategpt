"use client"

import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Send, Command } from 'lucide-react'

interface SlashCommand {
  command: string
  description: string
  usage: string
  category: 'document' | 'ai' | 'template' | 'general'
  handler: (args: string[]) => Promise<void>
}

interface ChatInputProps {
  onSendMessage: (message: string, command?: SlashCommand) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSendMessage, disabled, placeholder = "Type a message or use / for commands..." }: ChatInputProps) {
  const [inputText, setInputText] = useState("")
  const [showCommands, setShowCommands] = useState(false)
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0)
  const [filteredCommands, setFilteredCommands] = useState<SlashCommand[]>([])
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const commandListRef = useRef<HTMLDivElement>(null)

  // Define available slash commands
  const commands: SlashCommand[] = [
    {
      command: '/analyze',
      description: 'Analyze the current document or selected text for legal issues',
      usage: '/analyze [text]',
      category: 'ai',
      handler: async (args) => {
        // Implementation will connect to AI analysis endpoint
        console.log('Analyzing:', args.join(' '))
      }
    },
    {
      command: '/suggest',
      description: 'Get AI suggestions for improving the current document',
      usage: '/suggest [text]',
      category: 'ai',
      handler: async (args) => {
        console.log('Getting suggestions for:', args.join(' '))
      }
    },
    {
      command: '/templates',
      description: 'Search and browse document templates',
      usage: '/templates [search query]',
      category: 'template',
      handler: async (args) => {
        console.log('Searching templates:', args.join(' '))
      }
    },
    {
      command: '/export',
      description: 'Export the current document in various formats',
      usage: '/export [pdf|docx|html]',
      category: 'document',
      handler: async (args) => {
        const format = args[0] || 'pdf'
        console.log('Exporting as:', format)
      }
    },
    {
      command: '/help',
      description: 'Show available commands and shortcuts',
      usage: '/help [command]',
      category: 'general',
      handler: async (args) => {
        console.log('Showing help for:', args.join(' ') || 'all commands')
      }
    },
    {
      command: '/search',
      description: 'Search across all documents and templates',
      usage: '/search <query>',
      category: 'document',
      handler: async (args) => {
        console.log('Searching for:', args.join(' '))
      }
    },
    {
      command: '/new',
      description: 'Create a new document from template',
      usage: '/new [template-name]',
      category: 'document',
      handler: async (args) => {
        console.log('Creating new document:', args.join(' '))
      }
    }
  ]

  // Filter commands based on input
  useEffect(() => {
    if (inputText.startsWith('/')) {
      const query = inputText.slice(1).toLowerCase()
      const filtered = commands.filter(cmd => 
        cmd.command.toLowerCase().includes(`/${query}`) ||
        cmd.description.toLowerCase().includes(query)
      )
      setFilteredCommands(filtered)
      setShowCommands(filtered.length > 0)
      setSelectedCommandIndex(0)
    } else {
      setShowCommands(false)
      setFilteredCommands([])
    }
  }, [inputText])

  // Handle keyboard navigation
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (showCommands && filteredCommands.length > 0) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedCommandIndex(prev => 
            prev < filteredCommands.length - 1 ? prev + 1 : 0
          )
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedCommandIndex(prev => 
            prev > 0 ? prev - 1 : filteredCommands.length - 1
          )
          break
        case 'Tab':
        case 'Enter':
          if (!e.shiftKey) {
            e.preventDefault()
            handleCommandSelect(filteredCommands[selectedCommandIndex])
            return
          }
          break
        case 'Escape':
          e.preventDefault()
          setShowCommands(false)
          setInputText('')
          break
      }
    }

    // Handle message sending
    if (e.key === 'Enter' && !e.shiftKey && !showCommands) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Handle command selection
  const handleCommandSelect = (command: SlashCommand) => {
    setInputText(command.command + ' ')
    setShowCommands(false)
    inputRef.current?.focus()
  }

  // Handle message sending
  const handleSendMessage = () => {
    if (!inputText.trim() || disabled) return

    // Check if it's a command
    const isCommand = inputText.startsWith('/')
    let selectedCommand: SlashCommand | undefined

    if (isCommand) {
      const commandParts = inputText.split(' ')
      const commandName = commandParts[0]
      selectedCommand = commands.find(cmd => cmd.command === commandName)
      
      if (selectedCommand) {
        const args = commandParts.slice(1)
        selectedCommand.handler(args)
      }
    }

    onSendMessage(inputText, selectedCommand)
    setInputText('')
    setShowCommands(false)
  }

  // Scroll selected command into view
  useEffect(() => {
    if (commandListRef.current && showCommands) {
      const selectedElement = commandListRef.current.children[selectedCommandIndex] as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [selectedCommandIndex, showCommands])

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'ai': return '🤖'
      case 'document': return '📄'
      case 'template': return '📋'
      case 'general': return '⚙️'
      default: return '•'
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'ai': return 'text-blue-400'
      case 'document': return 'text-green-400'
      case 'template': return 'text-purple-400'
      case 'general': return 'text-gray-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <div className="relative">
      {/* Command suggestions dropdown */}
      {showCommands && filteredCommands.length > 0 && (
        <div 
          ref={commandListRef}
          className="absolute bottom-full left-0 right-0 mb-2 bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg shadow-xl max-h-60 overflow-y-auto z-50"
        >
          <div className="p-2 border-b border-[#2A2A2A]">
            <div className="flex items-center gap-2 text-xs text-[#6B6B6B]">
              <Command size={12} />
              <span>Commands</span>
              <span className="ml-auto">↑↓ navigate • Enter select • Esc cancel</span>
            </div>
          </div>
          
          {filteredCommands.map((command, index) => (
            <div
              key={command.command}
              onClick={() => handleCommandSelect(command)}
              className={`
                px-3 py-2 cursor-pointer border-l-2 transition-colors
                ${index === selectedCommandIndex 
                  ? 'bg-[#2A2A2A] border-blue-500' 
                  : 'border-transparent hover:bg-[#222]'
                }
              `}
            >
              <div className="flex items-center gap-3">
                <span className="text-lg">{getCategoryIcon(command.category)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">
                      {command.command}
                    </span>
                    <span className={`text-xs ${getCategoryColor(command.category)}`}>
                      {command.category}
                    </span>
                  </div>
                  <p className="text-xs text-[#B4B4B4] truncate">
                    {command.description}
                  </p>
                  <p className="text-xs text-[#6B6B6B] font-mono">
                    {command.usage}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Input field */}
      <div className="flex items-end gap-2 p-3 bg-[#1A1A1A] border-t border-[#2A2A2A]">
        <div className="flex-1 relative">
          <textarea
            ref={inputRef}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            style={{ 
              resize: 'none',
              minHeight: '60px',
              maxHeight: '180px'
            }}
            className="
              w-full px-3 py-2 bg-[#171717] border border-[#2A2A2A] rounded-lg
              text-sm text-white placeholder-[#6B6B6B]
              focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
              disabled:opacity-50 disabled:cursor-not-allowed
              resize-none overflow-hidden
            "
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement
              target.style.height = 'auto'
              target.style.height = Math.min(target.scrollHeight, 180) + 'px'
            }}
          />
          
          {/* Command indicator */}
          {inputText.startsWith('/') && (
            <div className="absolute right-2 top-2 flex items-center gap-1 text-xs text-blue-400">
              <Command size={12} />
              <span>Command mode</span>
            </div>
          )}
        </div>

        <button
          onClick={handleSendMessage}
          disabled={disabled || !inputText.trim()}
          className="
            p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 
            disabled:cursor-not-allowed rounded-lg transition-colors
            flex items-center justify-center min-w-[40px] h-10
          "
          title="Send message (Enter)"
        >
          <Send size={16} className="text-white" />
        </button>
      </div>
    </div>
  )
}