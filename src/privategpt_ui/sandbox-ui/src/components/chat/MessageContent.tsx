/**
 * Message Content Component
 * 
 * Renders message content with syntax highlighting, markdown support,
 * and special formatting for different content types.
 */

import React, { useMemo } from 'react'
import { cn } from '@/lib/utils'
import { MessageMetadata, MessageType } from '@/types/chat'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useTheme } from 'next-themes'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Search, BarChart, Terminal, FileText, Table } from 'lucide-react'

interface MessageContentProps {
  content: string
  type?: MessageType
  metadata?: MessageMetadata
  layout?: 'comfortable' | 'compact'
  enableSyntaxHighlighting?: boolean
}

export function MessageContent({
  content,
  type = 'text',
  metadata,
  layout = 'comfortable',
  enableSyntaxHighlighting = true
}: MessageContentProps) {
  const { theme } = useTheme()

  // Custom components for markdown rendering
  const markdownComponents = useMemo(() => ({
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '')
      const language = match ? match[1] : ''

      if (!inline && enableSyntaxHighlighting && language) {
        return (
          <div className="relative">
            <div className="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-t-lg border-b">
              <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                {language}
              </span>
            </div>
            <SyntaxHighlighter
              style={theme === 'dark' ? vscDarkPlus : vs}
              language={language}
              PreTag="div"
              className="rounded-t-none"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          </div>
        )
      }

      return (
        <code
          className={cn(
            'px-1.5 py-0.5 rounded text-sm font-mono',
            'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200'
          )}
          {...props}
        >
          {children}
        </code>
      )
    },
    
    pre({ children }: any) {
      return <div className="not-prose">{children}</div>
    },

    table({ children }: any) {
      return (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            {children}
          </table>
        </div>
      )
    },

    th({ children }: any) {
      return (
        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider bg-gray-50 dark:bg-gray-800">
          {children}
        </th>
      )
    },

    td({ children }: any) {
      return (
        <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
          {children}
        </td>
      )
    },

    blockquote({ children }: any) {
      return (
        <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-600 dark:text-gray-400">
          {children}
        </blockquote>
      )
    }
  }), [theme, enableSyntaxHighlighting])

  // Render content based on type
  const renderTypedContent = () => {
    switch (type) {
      case 'search':
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
              <Search className="w-4 h-4" />
              <span className="font-medium">Search: {metadata?.searchQuery}</span>
            </div>
            
            {metadata?.searchResults && metadata.searchResults.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Found {metadata.searchResults.length} results:
                </h4>
                <div className="space-y-1">
                  {metadata.searchResults.slice(0, 5).map((result: any, index: number) => (
                    <div key={index} className="p-2 bg-gray-50 dark:bg-gray-800 rounded text-sm">
                      <div className="font-medium truncate">{result.title || `Result ${index + 1}`}</div>
                      <div className="text-gray-600 dark:text-gray-400 text-xs truncate">
                        {result.content || result.description}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            <div className="prose dark:prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={markdownComponents}
              >
                {content}
              </ReactMarkdown>
            </div>
          </div>
        )

      case 'analyze':
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400">
              <BarChart className="w-4 h-4" />
              <span className="font-medium">Analysis: {metadata?.analysisTarget}</span>
            </div>
            
            <div className="prose dark:prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={markdownComponents}
              >
                {content}
              </ReactMarkdown>
            </div>
          </div>
        )

      case 'code':
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <Terminal className="w-4 h-4" />
              <span className="font-medium">
                Code{metadata?.codeLanguage && ` (${metadata.codeLanguage})`}
              </span>
            </div>
            
            {enableSyntaxHighlighting && metadata?.codeLanguage ? (
              <SyntaxHighlighter
                style={theme === 'dark' ? vscDarkPlus : vs}
                language={metadata.codeLanguage}
                PreTag="div"
              >
                {content}
              </SyntaxHighlighter>
            ) : (
              <pre className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-x-auto">
                <code>{content}</code>
              </pre>
            )}

            {metadata?.codeOutput && (
              <div className="mt-3">
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
                  Output:
                </div>
                <pre className="p-3 bg-black text-green-400 rounded-lg text-sm overflow-x-auto">
                  <code>{metadata.codeOutput}</code>
                </pre>
              </div>
            )}
          </div>
        )

      case 'table':
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
              <Table className="w-4 h-4" />
              <span className="font-medium">Table Data</span>
            </div>
            
            <div className="prose dark:prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={markdownComponents}
              >
                {content}
              </ReactMarkdown>
            </div>
          </div>
        )

      case 'command':
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-orange-600 dark:text-orange-400">
              <Terminal className="w-4 h-4" />
              <span className="font-medium">Command Execution</span>
            </div>
            
            <div className="p-3 bg-gray-900 text-gray-100 rounded-lg font-mono text-sm">
              <div className="text-green-400">$ {metadata?.command}</div>
              <div className="mt-2 whitespace-pre-wrap">{content}</div>
            </div>
          </div>
        )

      case 'thinking':
        // Thinking content is handled separately in ThinkingContent component
        return (
          <div className="prose dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {content}
            </ReactMarkdown>
          </div>
        )

      default:
        return (
          <div className="prose dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {content}
            </ReactMarkdown>
          </div>
        )
    }
  }

  const containerClasses = cn(
    'message-content',
    layout === 'compact' ? 'text-sm' : 'text-base',
    type === 'system' && 'font-mono text-sm'
  )

  return (
    <div className={containerClasses}>
      {renderTypedContent()}
      
      {/* Performance metadata */}
      {metadata?.duration && layout === 'comfortable' && (
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          Generated in {metadata.duration}ms
          {metadata.tokenUsage && (
            <span> • {metadata.tokenUsage.total_tokens} tokens</span>
          )}
        </div>
      )}
    </div>
  )
}

export default MessageContent