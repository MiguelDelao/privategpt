"use client"

import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { 
  Loader2, Send, AlertCircle, CheckCircle, Bot, Wrench, 
  Clock, Calculator, Search, FileText, Settings, RefreshCw,
  Play, Pause, X, CheckCheck, XCircle, Zap
} from "lucide-react"

// MCP Tool Interface Types
interface MCPTool {
  name: string
  description: string
  parameters: any
  requires_approval: boolean
  auto_approved: boolean
  category: string
}

interface ToolCall {
  id: string
  tool_name: string
  arguments: any
  status: 'pending' | 'approved' | 'rejected' | 'executing' | 'completed' | 'failed'
  result?: any
  error?: string
  timestamp: string
  execution_time_ms?: number
}

interface ApprovalRequest {
  id: string
  tool_name: string
  tool_description: string
  arguments: any
  conversation_id: string
  requested_at: string
  expires_at: string
  time_remaining_seconds: number
}

// MCP Debug Testing Interface
export default function MCPDebugPage() {
  // MCP Connection State
  const [mcpConnected, setMcpConnected] = useState(false)
  const [mcpTools, setMcpTools] = useState<MCPTool[]>([])
  const [loadingTools, setLoadingTools] = useState(false)
  
  // Tool Testing State
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null)
  const [toolArgs, setToolArgs] = useState<string>("{}")
  const [toolCallHistory, setToolCallHistory] = useState<ToolCall[]>([])
  
  // Approval Queue
  const [approvalQueue, setApprovalQueue] = useState<ApprovalRequest[]>([])
  const [autoApproveEnabled, setAutoApproveEnabled] = useState(false)
  const [approvalSimulationOn, setApprovalSimulationOn] = useState(true)
  
  // AI Chat with Tools State
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [chatMessage, setChatMessage] = useState("")
  const [chatResponse, setChatResponse] = useState("")
  const [chatLoading, setChatLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState("")
  const [toolsEnabled, setToolsEnabled] = useState(true)
  const [autoAcceptTools, setAutoAcceptTools] = useState(false)
  const [rawToolCalls, setRawToolCalls] = useState<any[]>([])
  const [conversationHistory, setConversationHistory] = useState<any[]>([])
  
  // Logs
  const [logs, setLogs] = useState<string[]>([])
  const [selectedLogLevel, setSelectedLogLevel] = useState<'all' | 'tools' | 'approvals' | 'errors'>('all')
  
  // Auth
  const [token, setToken] = useState<string | null>(null)
  
  // Streaming Chat State
  const [streamingMessages, setStreamingMessages] = useState<any[]>([])
  const [streamingInput, setStreamingInput] = useState("")
  const [streamingActive, setStreamingActive] = useState(false)
  const [pendingStreamApprovals, setPendingStreamApprovals] = useState<ApprovalRequest[]>([])
  const [streamAutoApprove, setStreamAutoApprove] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token')
    if (storedToken) {
      setToken(storedToken)
      addLog("info", "Token loaded from localStorage")
    }
    
    // Connect to real MCP system and load models
    connectToMCP()
    loadAvailableModels()
  }, [])
  
  const addLog = (level: 'info' | 'success' | 'warning' | 'error' | 'tool' | 'approval', message: string) => {
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0]
    const emoji = {
      info: 'ℹ️',
      success: '✅',
      warning: '⚠️',
      error: '❌',
      tool: '🔧',
      approval: '🔐'
    }[level]
    
    setLogs(prev => [`[${timestamp}] ${emoji} ${message}`, ...prev].slice(0, 100))
  }

  // Real API connection functions
  const connectToMCP = async () => {
    try {
      addLog("info", "Connecting to MCP system...")
      
      // Check MCP health
      const response = await fetch('/api/mcp/health', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const healthData = await response.json()
        setMcpConnected(true)
        addLog("success", `MCP connected - ${Object.keys(healthData.servers).length} servers`)
        await loadMcpTools()
        await loadPendingApprovals()
        await setupWebSocket()
      } else {
        setMcpConnected(false)
        addLog("error", "Failed to connect to MCP system")
      }
    } catch (error) {
      setMcpConnected(false)
      addLog("error", `MCP connection error: ${error}`)
    }
  }
  
  // Load MCP Tools from real API
  const loadMcpTools = async () => {
    setLoadingTools(true)
    addLog("info", "Loading MCP tools...")
    
    try {
      const response = await fetch('/api/mcp/tools?provider=generic', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        
        // Transform API tools to match UI interface
        const transformedTools: MCPTool[] = data.tools.map((tool: any) => ({
          name: tool.name,
          description: tool.description,
          parameters: tool.parameters || tool.input_schema,
          requires_approval: true, // Default to requiring approval
          auto_approved: false,
          category: tool.category || 'uncategorized'
        }))
        
        setMcpTools(transformedTools)
        addLog("success", `Loaded ${transformedTools.length} MCP tools from ${Object.keys(data.servers).length} servers`)
        
        // Auto-select first tool
        if (transformedTools.length > 0) {
          setSelectedTool(transformedTools[0])
          // Set default args based on first tool's parameters
          const firstTool = transformedTools[0]
          if (firstTool.parameters?.properties) {
            const defaultArgs: any = {}
            Object.keys(firstTool.parameters.properties).forEach(key => {
              const prop = firstTool.parameters.properties[key]
              if (prop.default !== undefined) {
                defaultArgs[key] = prop.default
              } else if (prop.type === 'string') {
                defaultArgs[key] = ""
              } else if (prop.type === 'number') {
                defaultArgs[key] = 0
              }
            })
            setToolArgs(JSON.stringify(defaultArgs, null, 2))
          }
        }
      } else {
        addLog("error", "Failed to load MCP tools")
      }
    } catch (error) {
      addLog("error", `Error loading tools: ${error}`)
    } finally {
      setLoadingTools(false)
    }
  }
  
  // Load pending approvals from API
  const loadPendingApprovals = async () => {
    try {
      const response = await fetch('/api/mcp/approvals/pending', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const approvals = await response.json()
        setApprovalQueue(approvals)
        setPendingStreamApprovals(approvals)
        addLog("info", `Loaded ${approvals.length} pending approvals`)
      }
    } catch (error) {
      addLog("error", `Error loading approvals: ${error}`)
    }
  }
  
  // Set up WebSocket for real-time notifications
  const setupWebSocket = async () => {
    if (!token) return
    
    try {
      // Extract user ID from token (simplified)
      const userId = "user123" // In real app, decode from JWT
      const wsUrl = `ws://localhost:8000/api/mcp/ws/approvals?user_id=${userId}`
      
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        addLog("success", "WebSocket connected for real-time notifications")
      }
      
      ws.onmessage = (event) => {
        const notification = JSON.parse(event.data)
        handleWebSocketNotification(notification)
      }
      
      ws.onerror = (error) => {
        addLog("error", `WebSocket error: ${error}`)
      }
      
      ws.onclose = () => {
        addLog("warning", "WebSocket disconnected")
      }
      
    } catch (error) {
      addLog("error", `WebSocket setup error: ${error}`)
    }
  }
  
  // Handle WebSocket notifications
  const handleWebSocketNotification = (notification: any) => {
    switch (notification.type) {
      case 'approval_requested':
        addLog("approval", `New approval request: ${notification.data.tool_name}`)
        loadPendingApprovals() // Refresh the list
        break
        
      case 'approval_decided':
        addLog("approval", `Approval ${notification.data.approved ? 'approved' : 'rejected'}: ${notification.data.tool_name}`)
        loadPendingApprovals() // Refresh the list
        break
        
      case 'approval_expired':
        addLog("warning", `Approval expired: ${notification.data.tool_name}`)
        loadPendingApprovals() // Refresh the list
        break
    }
  }
  
  // Execute Tool Directly
  const executeToolDirectly = async () => {
    if (!selectedTool) return
    
    try {
      const args = JSON.parse(toolArgs)
      const toolCall: ToolCall = {
        id: `tc_${Date.now()}`,
        tool_name: selectedTool.name,
        arguments: args,
        status: 'pending',
        timestamp: new Date().toISOString()
      }
      
      addLog("tool", `Executing tool: ${selectedTool.name}`)
      setToolCallHistory(prev => [toolCall, ...prev])
      
      // Check if approval needed
      if (selectedTool.requires_approval && !autoApproveEnabled) {
        // Create approval request
        const approval: ApprovalRequest = {
          id: `apr_${Date.now()}`,
          tool_name: selectedTool.name,
          tool_description: selectedTool.description,
          arguments: args,
          conversation_id: "debug_session",
          requested_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
          time_remaining_seconds: 300
        }
        
        setApprovalQueue(prev => [approval, ...prev])
        addLog("approval", `Approval required for: ${selectedTool.name}`)
        
        // Update tool call status
        updateToolCallStatus(toolCall.id, 'pending')
        return
      }
      
      // Execute tool
      updateToolCallStatus(toolCall.id, 'executing')
      
      // Simulate execution
      setTimeout(() => {
        const mockResults: Record<string, any> = {
          calculator: { result: 8, expression: "5 + 3 = 8" },
          get_current_time: { current_time: new Date().toISOString(), timezone: "UTC" },
          search_documents: { results: ["Document 1", "Document 2"], total_found: 2 },
          create_file: { status: "created", file_path: "/test/file.txt", size_bytes: 100 }
        }
        
        // Call real MCP API instead of mock
        executeToolViaAPI(toolCall)
      }, 100)
      
    } catch (error) {
      addLog("error", `Failed to parse tool arguments: ${error}`)
    }
  }
  
  // Execute tool via real API
  const executeToolViaAPI = async (toolCall: ToolCall) => {
    try {
      updateToolCallStatus(toolCall.id, 'executing')
      
      const response = await fetch('/api/mcp/execute', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          tool_name: toolCall.tool_name,
          arguments: toolCall.arguments,
          conversation_id: "debug_session",
          require_approval: selectedTool?.requires_approval && !autoApproveEnabled
        })
      })
      
      const result = await response.json()
      
      if (result.success) {
        updateToolCallStatus(toolCall.id, 'completed', result.result, null, result.execution_time_ms)
        addLog("success", `Tool executed: ${toolCall.tool_name} (${result.execution_time_ms}ms)`)
      } else if (result.approval_id) {
        updateToolCallStatus(toolCall.id, 'pending')
        addLog("approval", `Approval required: ${result.approval_id}`)
        await loadPendingApprovals()
      } else {
        updateToolCallStatus(toolCall.id, 'failed', null, result.error)
        addLog("error", `Tool execution failed: ${result.error}`)
      }
      
    } catch (error) {
      updateToolCallStatus(toolCall.id, 'failed', null, String(error))
      addLog("error", `Tool execution error: ${error}`)
    }
  }
  
  // Handle approval with real API
  const handleApprovalReal = async (approvalId: string, approved: boolean) => {
    try {
      const response = await fetch(`/api/mcp/approvals/${approvalId}/approve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          approved: approved,
          reason: approved ? "Approved via debug interface" : "Rejected via debug interface"
        })
      })
      
      if (response.ok) {
        addLog("approval", `${approved ? 'Approved' : 'Rejected'} tool: ${approvalId}`)
        
        if (approved) {
          // Execute the approved tool
          const executeResponse = await fetch(`/api/mcp/approvals/${approvalId}/execute`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          if (executeResponse.ok) {
            const executeResult = await executeResponse.json()
            addLog("success", `Executed approved tool: ${executeResult.execution_time_ms}ms`)
            
            // Add to tool call history
            const approval = approvalQueue.find(a => a.id === approvalId)
            if (approval) {
              const newToolCall: ToolCall = {
                id: `tc_${Date.now()}`,
                tool_name: approval.tool_name,
                arguments: approval.arguments,
                status: executeResult.success ? 'completed' : 'failed',
                result: executeResult.result,
                error: executeResult.error,
                timestamp: new Date().toISOString(),
                execution_time_ms: executeResult.execution_time_ms
              }
              setToolCallHistory(prev => [newToolCall, ...prev])
            }
          }
        }
        
        await loadPendingApprovals()
      } else {
        addLog("error", "Failed to process approval")
      }
    } catch (error) {
      addLog("error", `Approval error: ${error}`)
    }
  }
  
  // Update tool call status
  const updateToolCallStatus = (id: string, status: ToolCall['status'], result?: any, error?: string, execution_time?: number) => {
    setToolCallHistory(prev => prev.map(tc => 
      tc.id === id 
        ? { ...tc, status, result, error, execution_time_ms: execution_time }
        : tc
    ))
  }
  
  // Handle Approval
  const handleApproval = (approvalId: string, approved: boolean) => {
    const approval = approvalQueue.find(a => a.id === approvalId)
    if (!approval) return
    
    // Remove from queue
    setApprovalQueue(prev => prev.filter(a => a.id !== approvalId))
    
    // Find corresponding tool call
    const toolCall = toolCallHistory.find(tc => 
      tc.tool_name === approval.tool_name && tc.status === 'pending'
    )
    
    if (toolCall) {
      if (approved) {
        addLog("approval", `Approved tool: ${approval.tool_name}`)
        updateToolCallStatus(toolCall.id, 'approved')
        
        // Execute after approval
        setTimeout(() => {
          updateToolCallStatus(toolCall.id, 'executing')
          setTimeout(() => {
            updateToolCallStatus(toolCall.id, 'completed', { message: "Executed after approval" }, null, 200)
          }, 1000)
        }, 500)
      } else {
        addLog("approval", `Rejected tool: ${approval.tool_name}`)
        updateToolCallStatus(toolCall.id, 'rejected', null, "User rejected execution")
      }
    }
  }
  
  // Test Chat with Tools
  const testChatWithTools = async () => {
    setChatLoading(true)
    setChatResponse("")
    
    addLog("info", `Chat request with tools ${toolsEnabled ? 'enabled' : 'disabled'}`)
    
    // Simulate chat with tool detection
    setTimeout(() => {
      if (toolsEnabled && chatMessage.toLowerCase().includes('calculate')) {
        // Simulate tool call detection
        setChatResponse("I'll calculate that for you...")
        
        const toolCall: ToolCall = {
          id: `tc_${Date.now()}`,
          tool_name: "calculator",
          arguments: { operation: "multiply", a: 15, b: 0.15 },
          status: 'executing',
          timestamp: new Date().toISOString()
        }
        
        setToolCallHistory(prev => [toolCall, ...prev])
        addLog("tool", "LLM requested calculator tool")
        
        setTimeout(() => {
          updateToolCallStatus(toolCall.id, 'completed', { result: 2.25 }, null, 100)
          setChatResponse("15% of 15 is 2.25")
          setChatLoading(false)
        }, 1500)
      } else {
        // Regular response
        setChatResponse("This is a simulated response without tool usage.")
        setChatLoading(false)
      }
    }, 1000)
  }

  // Load Available Models
  const loadAvailableModels = async () => {
    try {
      addLog("info", "Loading available AI models...")
      
      const response = await fetch('/api/llm/models', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        // Extract model names from the model objects
        const modelNames = data.map((model: any) => model.name || model.id || model.model)
        setAvailableModels(modelNames)
        addLog("success", `Loaded ${modelNames.length} AI models`)
        
        // Auto-select first model
        if (modelNames.length > 0) {
          setSelectedModel(modelNames[0])
        }
      } else {
        addLog("error", "Failed to load AI models")
      }
    } catch (error) {
      addLog("error", `Error loading models: ${error}`)
    }
  }

  // Send AI Chat Message with Streaming
  const sendAIMessage = async () => {
    if (!chatMessage.trim() || chatLoading || !selectedModel) return
    
    // First create a conversation if we don't have one
    let conversationId = localStorage.getItem('test_conversation_id')
    if (!conversationId) {
      try {
        const createResp = await fetch('/api/chat/conversations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            title: "MCP Test Conversation"
          })
        })
        
        if (createResp.ok) {
          const convData = await createResp.json()
          conversationId = convData.id
          localStorage.setItem('test_conversation_id', conversationId)
          addLog("success", `Created conversation: ${conversationId}`)
        } else {
          throw new Error("Failed to create conversation")
        }
      } catch (error) {
        addLog("error", `Failed to create conversation: ${error}`)
        return
      }
    }
    
    const userMessage = {
      role: 'user',
      content: chatMessage,
      timestamp: new Date().toISOString()
    }
    
    setConversationHistory(prev => [...prev, userMessage])
    setChatLoading(true)
    setChatMessage("")
    addLog("info", `Preparing stream with ${selectedModel}`)
    
    try {
      // Step 1: Prepare the stream
      const prepareResponse = await fetch(`/api/chat/conversations/${conversationId}/prepare-mcp-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: chatMessage,
          model: selectedModel,
          tools_enabled: toolsEnabled,
          auto_approve_tools: autoAcceptTools,
          temperature: 0.7,
          max_tokens: 1000
        })
      })
      
      if (!prepareResponse.ok) {
        const errorData = await prepareResponse.json()
        throw new Error(errorData.detail || 'Failed to prepare stream')
      }
      
      const prepareData = await prepareResponse.json()
      addLog("success", `Stream prepared, token: ${prepareData.stream_token}`)
      
      // Step 2: Connect to the stream
      const streamUrl = `/api/chat/live-mcp-stream/${prepareData.stream_token}`
      const eventSource = new EventSource(streamUrl)
      
      let assistantContent = ""
      const assistantMessage = {
        role: 'assistant',
        content: "",
        timestamp: new Date().toISOString(),
        tool_calls: [] as any[]
      }
      
      // Add placeholder for streaming
      setConversationHistory(prev => [...prev, assistantMessage])
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          switch (data.type) {
            case 'content_chunk':
              assistantContent += data.content
              // Update the last message in conversation history
              setConversationHistory(prev => {
                const updated = [...prev]
                updated[updated.length - 1] = {
                  ...assistantMessage,
                  content: assistantContent
                }
                return updated
              })
              break
              
            case 'tools_available':
              addLog("info", `Tools available: ${data.tools.map((t: any) => t.name).join(', ')}`)
              break
              
            case 'tool_call_detected':
              addLog("tool", `Tool call detected: ${data.tool_call}`)
              setRawToolCalls(prev => [...prev, data.tool_call])
              assistantMessage.tool_calls.push(data.tool_call)
              break
              
            case 'tool_executing':
              addLog("tool", `Executing tool: ${data.tool_name}`)
              break
              
            case 'tool_result':
              addLog("success", `Tool result: ${JSON.stringify(data.result)}`)
              break
              
            case 'tool_approval_required':
              addLog("approval", `Tool approval required: ${data.tool_name}`)
              break
              
            case 'assistant_message_complete':
              setChatResponse(data.message.content)
              addLog("success", `AI response complete (${data.message.token_count} tokens)`)
              if (data.message.tool_calls && data.message.tool_calls.length > 0) {
                addLog("tool", `Total tool calls: ${data.message.tool_calls.length}`)
              }
              break
              
            case 'done':
              eventSource.close()
              setChatLoading(false)
              break
              
            case 'error':
              addLog("error", `Stream error: ${data.message}`)
              eventSource.close()
              setChatLoading(false)
              break
          }
        } catch (e) {
          addLog("error", `Failed to parse stream event: ${e}`)
        }
      }
      
      eventSource.onerror = (error) => {
        addLog("error", `Stream connection error`)
        eventSource.close()
        setChatLoading(false)
      }
      
    } catch (error) {
      addLog("error", `AI chat error: ${error}`)
      setChatResponse(`Error: ${error}`)
      setChatLoading(false)
    }
  }
  
  // Get tool icon
  const getToolIcon = (category: string) => {
    switch (category) {
      case 'calculation': return <Calculator className="h-4 w-4" />
      case 'utility': return <Clock className="h-4 w-4" />
      case 'search': return <Search className="h-4 w-4" />
      case 'file_system': return <FileText className="h-4 w-4" />
      default: return <Wrench className="h-4 w-4" />
    }
  }
  
  // Get status color
  const getStatusColor = (status: ToolCall['status']) => {
    switch (status) {
      case 'pending': return 'bg-yellow-500'
      case 'approved': return 'bg-blue-500'
      case 'rejected': return 'bg-red-500'
      case 'executing': return 'bg-orange-500'
      case 'completed': return 'bg-green-500'
      case 'failed': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }
  
  // Handle streaming chat with real MCP
  const handleStreamingChat = async () => {
    if (!streamingInput.trim() || streamingActive || !selectedModel) return
    
    // First create a conversation if we don't have one
    let conversationId = localStorage.getItem('test_stream_conversation_id')
    if (!conversationId) {
      try {
        const createResp = await fetch('/api/chat/conversations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            title: "MCP Stream Test"
          })
        })
        
        if (createResp.ok) {
          const convData = await createResp.json()
          conversationId = convData.id
          localStorage.setItem('test_stream_conversation_id', conversationId)
          addLog("success", `Created stream conversation: ${conversationId}`)
        } else {
          throw new Error("Failed to create conversation")
        }
      } catch (error) {
        addLog("error", `Failed to create conversation: ${error}`)
        return
      }
    }
    
    const userMessage = {
      role: 'user',
      content: streamingInput,
      timestamp: new Date().toISOString()
    }
    
    setStreamingMessages(prev => [...prev, userMessage])
    setStreamingInput("")
    setStreamingActive(true)
    addLog("info", `Starting MCP stream with ${selectedModel}`)
    
    try {
      // Step 1: Prepare the MCP stream
      const prepareResponse = await fetch(`/api/chat/conversations/${conversationId}/prepare-mcp-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: userMessage.content,
          model: selectedModel,
          tools_enabled: toolsEnabled,
          auto_approve_tools: streamAutoApprove,
          temperature: 0.7,
          max_tokens: 1000
        })
      })
      
      if (!prepareResponse.ok) {
        const errorData = await prepareResponse.json()
        throw new Error(errorData.detail || 'Failed to prepare stream')
      }
      
      const prepareData = await prepareResponse.json()
      addLog("success", `MCP Stream prepared, token: ${prepareData.stream_token}`)
      
      // Step 2: Connect to the MCP stream
      const streamUrl = `/api/chat/live-mcp-stream/${prepareData.stream_token}`
      eventSourceRef.current = new EventSource(streamUrl)
      
      // Add assistant message placeholder
      const assistantMessage = {
        role: 'assistant',
        content: '',
        streaming: true,
        timestamp: new Date().toISOString(),
        toolCall: null
      }
      
      setStreamingMessages(prev => [...prev, assistantMessage])
      const messageIndex = streamingMessages.length + 1
      
      let fullContent = ""
      
      eventSourceRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          switch (data.type) {
            case 'content_chunk':
              fullContent += data.content
              setStreamingMessages(prev => {
                const updated = [...prev]
                updated[messageIndex] = {
                  ...updated[messageIndex],
                  content: fullContent
                }
                return updated
              })
              break
              
            case 'tools_available':
              addLog("info", `MCP Tools available: ${data.tools.map((t: any) => t.name).join(', ')}`)
              break
              
            case 'tool_call_detected':
              addLog("tool", `Tool call detected: ${data.tool_call}`)
              setStreamingMessages(prev => {
                const updated = [...prev]
                updated[messageIndex] = {
                  ...updated[messageIndex],
                  toolCall: data.tool_call
                }
                return updated
              })
              break
              
            case 'tool_executing':
              addLog("tool", `Executing tool: ${data.tool_name}`)
              break
              
            case 'tool_result':
              addLog("success", `Tool result: ${JSON.stringify(data.result)}`)
              break
              
            case 'tool_approval_required':
              addLog("approval", `Tool approval required: ${data.tool_name}`)
              // Add to approval queue
              const approval: ApprovalRequest = {
                id: `apr_stream_${Date.now()}`,
                tool_name: data.tool_name,
                tool_description: "Tool execution requested",
                arguments: {},
                conversation_id: conversationId,
                requested_at: new Date().toISOString(),
                expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
                time_remaining_seconds: 300
              }
              setPendingStreamApprovals(prev => [...prev, approval])
              break
              
            case 'assistant_message_complete':
              setStreamingMessages(prev => {
                const updated = [...prev]
                updated[messageIndex] = {
                  ...updated[messageIndex],
                  streaming: false,
                  content: data.message.content
                }
                return updated
              })
              addLog("success", `Stream complete (${data.message.token_count} tokens)`)
              break
              
            case 'done':
              eventSourceRef.current?.close()
              setStreamingActive(false)
              break
              
            case 'error':
              addLog("error", `Stream error: ${data.message}`)
              eventSourceRef.current?.close()
              setStreamingActive(false)
              break
          }
        } catch (e) {
          addLog("error", `Failed to parse stream event: ${e}`)
        }
      }
      
      eventSourceRef.current.onerror = (error) => {
        addLog("error", `Stream connection error`)
        eventSourceRef.current?.close()
        setStreamingActive(false)
      }
      
    } catch (error) {
      addLog("error", `MCP stream error: ${error}`)
      setStreamingActive(false)
    }
  }
  
  // Simulate tool use
  const simulateToolUse = (messageIndex: number, needsCalculator: boolean, needsTime: boolean, needsFile: boolean) => {
    let toolName = ""
    let toolArgs = {}
    let requiresApproval = false
    
    if (needsCalculator) {
      toolName = "calculator"
      toolArgs = { operation: "multiply", a: 2500, b: 0.15 }
    } else if (needsTime) {
      toolName = "get_current_time"
      toolArgs = { timezone: "Asia/Tokyo", format: "human" }
    } else if (needsFile) {
      toolName = "create_file"
      toolArgs = { file_path: "/test/demo.txt", content: "Hello from MCP!" }
      requiresApproval = true
    }
    
    // Show tool call in message
    setStreamingMessages(prev => {
      const updated = [...prev]
      updated[messageIndex] = {
        ...updated[messageIndex],
        content: updated[messageIndex].content + "\n\nI need to use a tool for this...",
        toolCall: { name: toolName, arguments: toolArgs }
      }
      return updated
    })
    
    // Check if approval needed
    if (requiresApproval && !streamAutoApprove) {
      const approval: ApprovalRequest = {
        id: `apr_stream_${Date.now()}`,
        tool_name: toolName,
        tool_description: "Create a new file with content",
        arguments: toolArgs,
        conversation_id: "stream_test",
        requested_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
        time_remaining_seconds: 300
      }
      
      setPendingStreamApprovals(prev => [...prev, approval])
      addLog("approval", `Stream chat: Approval required for ${toolName}`)
      
      // Update message to show waiting for approval
      setTimeout(() => {
        setStreamingMessages(prev => {
          const updated = [...prev]
          updated[messageIndex] = {
            ...updated[messageIndex],
            content: updated[messageIndex].content + "\n\n⏳ Waiting for tool approval...",
            streaming: false
          }
          return updated
        })
        setStreamingActive(false)
      }, 500)
    } else {
      // Execute tool directly
      executeStreamTool(messageIndex, toolName, toolArgs)
    }
  }
  
  // Execute tool for streaming chat
  const executeStreamTool = (messageIndex: number, toolName: string, toolArgs: any) => {
    addLog("tool", `Stream chat: Executing ${toolName}`)
    
    // Simulate tool execution
    setTimeout(() => {
      let result = ""
      if (toolName === "calculator") {
        result = "375"
        completeStreamingMessage(messageIndex, "I've calculated that for you: 15% of 2500 is 375.")
      } else if (toolName === "get_current_time") {
        const time = new Date().toLocaleString('en-US', { timeZone: 'Asia/Tokyo' })
        result = time
        completeStreamingMessage(messageIndex, `The current time in Tokyo is: ${time}`)
      } else if (toolName === "create_file") {
        result = "File created successfully"
        completeStreamingMessage(messageIndex, "I've created the file '/test/demo.txt' with your content.")
      }
      
      addLog("success", `Stream chat: Tool ${toolName} completed with result: ${result}`)
    }, 1000)
  }
  
  // Complete streaming message
  const completeStreamingMessage = (messageIndex: number, finalContent: string) => {
    setStreamingMessages(prev => {
      const updated = [...prev]
      updated[messageIndex] = {
        ...updated[messageIndex],
        content: finalContent,
        streaming: false
      }
      return updated
    })
    setStreamingActive(false)
  }
  
  // Handle stream approval
  const handleStreamApproval = (approvalId: string, approved: boolean) => {
    const approval = pendingStreamApprovals.find(a => a.id === approvalId)
    if (!approval) return
    
    // Remove from pending
    setPendingStreamApprovals(prev => prev.filter(a => a.id !== approvalId))
    
    if (approved) {
      addLog("approval", `Stream chat: Approved tool ${approval.tool_name}`)
      
      // Find the message waiting for this tool
      const messageIndex = streamingMessages.findIndex(msg => 
        msg.role === 'assistant' && 
        msg.content.includes('Waiting for tool approval')
      )
      
      if (messageIndex >= 0) {
        // Update message to show executing
        setStreamingMessages(prev => {
          const updated = [...prev]
          updated[messageIndex] = {
            ...updated[messageIndex],
            content: updated[messageIndex].content.replace('⏳ Waiting for tool approval...', '✅ Tool approved, executing...')
          }
          return updated
        })
        
        // Execute the tool
        executeStreamTool(messageIndex, approval.tool_name, approval.arguments)
      }
    } else {
      addLog("approval", `Stream chat: Rejected tool ${approval.tool_name}`)
      
      // Update message to show rejection
      const messageIndex = streamingMessages.findIndex(msg => 
        msg.role === 'assistant' && 
        msg.content.includes('Waiting for tool approval')
      )
      
      if (messageIndex >= 0) {
        completeStreamingMessage(messageIndex, "The tool request was rejected. I'll help you in another way.")
      }
    }
  }
  
  return (
    <div className="h-full overflow-y-auto">
      <div className="container mx-auto p-6 max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Wrench className="h-8 w-8" />
            MCP Tool Debug Interface
          </h1>
          <p className="text-muted-foreground mt-1">Test and debug MCP tool execution and approvals</p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${mcpConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            <div className={`h-2 w-2 rounded-full ${mcpConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
            {mcpConnected ? 'Connected' : 'Disconnected'}
          </div>
          <Button variant="outline" size="sm" onClick={loadMcpTools}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh Tools
          </Button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tool Execution Panel */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Tool Testing</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="direct">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="direct">Direct Execution</TabsTrigger>
                <TabsTrigger value="chat">Chat with Tools</TabsTrigger>
              </TabsList>
              
              <TabsContent value="direct" className="space-y-4">
                {/* Tool Selection */}
                <div>
                  <div className="text-sm font-medium mb-2">Select Tool</div>
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    {mcpTools.map(tool => (
                      <Button
                        key={tool.name}
                        variant={selectedTool?.name === tool.name ? "default" : "outline"}
                        className="justify-start"
                        onClick={() => {
                          setSelectedTool(tool)
                          setToolArgs(JSON.stringify(
                            Object.fromEntries(
                              Object.entries(tool.parameters.properties || {}).map(([key, prop]: [string, any]) => [
                                key, 
                                prop.default || (prop.type === 'number' ? 0 : '')
                              ])
                            ), null, 2
                          ))
                        }}
                      >
                        {getToolIcon(tool.category)}
                        <span className="ml-2">{tool.name}</span>
                        {tool.requires_approval && (
                          <Badge variant="secondary" className="ml-auto">
                            Approval Required
                          </Badge>
                        )}
                      </Button>
                    ))}
                  </div>
                </div>
                
                {/* Tool Details */}
                {selectedTool && (
                  <>
                    <div className="p-4 bg-muted rounded-lg">
                      <h4 className="font-medium">{selectedTool.name}</h4>
                      <p className="text-sm text-muted-foreground mt-1">{selectedTool.description}</p>
                      <div className="flex gap-2 mt-2">
                        <Badge variant="outline">{selectedTool.category}</Badge>
                        {selectedTool.requires_approval ? (
                          <Badge variant="destructive">Requires Approval</Badge>
                        ) : (
                          <Badge variant="secondary">Auto-approved</Badge>
                        )}
                      </div>
                    </div>
                    
                    {/* Tool Arguments */}
                    <div>
                      <div className="text-sm font-medium mb-2">Arguments (JSON)</div>
                      <Textarea
                        value={toolArgs}
                        onChange={(e) => setToolArgs(e.target.value)}
                        className="font-mono text-sm mt-2"
                        rows={6}
                      />
                    </div>
                    
                    {/* Execute Button */}
                    <Button onClick={executeToolDirectly} className="w-full">
                      <Play className="mr-2 h-4 w-4" />
                      Execute Tool
                    </Button>
                  </>
                )}
              </TabsContent>
              
              <TabsContent value="chat" className="space-y-4">
                {/* AI Model Selection */}
                <div>
                  <div className="text-sm font-medium mb-2">AI Model</div>
                  <Select value={selectedModel} onValueChange={setSelectedModel}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select AI model..." />
                    </SelectTrigger>
                    <SelectContent>
                      {availableModels.map(model => (
                        <SelectItem key={model} value={model}>{model}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Tool Settings */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Enable Tools</span>
                    <Switch checked={toolsEnabled} onCheckedChange={setToolsEnabled} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Auto Accept Tools</span>
                    <Switch checked={autoAcceptTools} onCheckedChange={setAutoAcceptTools} />
                  </div>
                </div>

                {/* Chat Input */}
                <div>
                  <div className="text-sm font-medium mb-2">Message</div>
                  <Textarea
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    placeholder="Try: 'What time is it?' or 'Calculate 25 + 17' or 'What's 15% of 200?'"
                    className="mt-2"
                    rows={3}
                  />
                </div>

                <div className="flex gap-2">
                  <Button 
                    onClick={sendAIMessage}
                    disabled={chatLoading || !chatMessage || !selectedModel}
                    className="flex-1"
                  >
                    {chatLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Sending to {selectedModel}...
                      </>
                    ) : (
                      <>
                        <Send className="mr-2 h-4 w-4" />
                        Send to AI
                      </>
                    )}
                  </Button>
                  <Button 
                    variant="outline"
                    onClick={() => {
                      setConversationHistory([])
                      setRawToolCalls([])
                      setChatResponse("")
                      localStorage.removeItem('test_conversation_id')
                      addLog("info", "Cleared conversation and tool calls")
                    }}
                    disabled={chatLoading}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                {/* Raw Tool Calls Display */}
                {rawToolCalls.length > 0 && (
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <div className="text-sm font-medium mb-2 text-blue-700">Raw Tool Calls:</div>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {rawToolCalls.map((toolCall, index) => (
                        <pre key={index} className="text-xs bg-blue-100 p-2 rounded">
                          {JSON.stringify(toolCall, null, 2)}
                        </pre>
                      ))}
                    </div>
                  </div>
                )}

                {/* AI Response */}
                {chatResponse && (
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="text-sm font-medium mb-2">AI Response:</div>
                    <p className="mt-2 whitespace-pre-wrap">{chatResponse}</p>
                  </div>
                )}

                {/* Conversation History */}
                {conversationHistory.length > 0 && (
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="text-sm font-medium mb-2">Conversation History:</div>
                    <ScrollArea className="h-[200px] space-y-2">
                      {conversationHistory.map((message, index) => (
                        <div key={index} className={`p-2 rounded text-sm ${
                          message.role === 'user' ? 'bg-blue-100 ml-4' : 'bg-green-100 mr-4'
                        }`}>
                          <div className="font-medium">{message.role === 'user' ? 'You' : 'AI'}:</div>
                          <div className="mt-1">{message.content}</div>
                          {message.tool_calls && message.tool_calls.length > 0 && (
                            <div className="mt-2 text-xs bg-yellow-100 p-1 rounded">
                              Tools used: {message.tool_calls.map((tc: any) => tc.function?.name || tc.name).join(', ')}
                            </div>
                          )}
                        </div>
                      ))}
                    </ScrollArea>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
        
        {/* Approval Queue */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Approval Queue</span>
              <Badge variant="outline">{approvalQueue.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 mb-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Auto-approve All</span>
                <Switch checked={autoApproveEnabled} onCheckedChange={setAutoApproveEnabled} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Simulate Approvals</span>
                <Switch checked={approvalSimulationOn} onCheckedChange={setApprovalSimulationOn} />
              </div>
            </div>
            
            <ScrollArea className="h-[300px]">
              {approvalQueue.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No pending approvals</p>
              ) : (
                <div className="space-y-3">
                  {approvalQueue.map(approval => (
                    <div key={approval.id} className="p-3 border rounded-lg space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{approval.tool_name}</span>
                        <Badge variant="outline" className="text-xs">
                          {Math.floor(approval.time_remaining_seconds / 60)}m remaining
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{approval.tool_description}</p>
                      <pre className="text-xs bg-muted p-2 rounded">
                        {JSON.stringify(approval.arguments, null, 2)}
                      </pre>
                      <div className="flex gap-2">
                        <Button 
                          size="sm" 
                          className="flex-1"
                          onClick={() => handleApprovalReal(approval.id, true)}
                        >
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Approve
                        </Button>
                        <Button 
                          size="sm" 
                          variant="destructive" 
                          className="flex-1"
                          onClick={() => handleApprovalReal(approval.id, false)}
                        >
                          <XCircle className="mr-1 h-3 w-3" />
                          Reject
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
        
        {/* Tool Execution History */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Execution History</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px]">
              {toolCallHistory.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No tool executions yet</p>
              ) : (
                <div className="space-y-3">
                  {toolCallHistory.map(call => (
                    <div key={call.id} className="p-3 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className={`h-2 w-2 rounded-full ${getStatusColor(call.status)}`} />
                          <span className="font-medium">{call.tool_name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{call.status}</Badge>
                          {call.execution_time_ms && (
                            <span className="text-xs text-muted-foreground">
                              {call.execution_time_ms}ms
                            </span>
                          )}
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Arguments:</span>
                          <pre className="mt-1 p-2 bg-muted rounded text-xs">
                            {JSON.stringify(call.arguments, null, 2)}
                          </pre>
                        </div>
                        {call.result && (
                          <div>
                            <span className="text-muted-foreground">Result:</span>
                            <pre className="mt-1 p-2 bg-muted rounded text-xs">
                              {JSON.stringify(call.result, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                      
                      {call.error && (
                        <div className="mt-2 p-2 bg-red-100 dark:bg-red-900/20 rounded text-sm text-red-600 dark:text-red-400">
                          {call.error}
                        </div>
                      )}
                      
                      <div className="mt-2 text-xs text-muted-foreground">
                        {new Date(call.timestamp).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
        
        {/* Debug Logs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Debug Logs</span>
              <select 
                className="text-sm px-2 py-1 border rounded"
                value={selectedLogLevel}
                onChange={(e) => setSelectedLogLevel(e.target.value as any)}
              >
                <option value="all">All</option>
                <option value="tools">Tools</option>
                <option value="approvals">Approvals</option>
                <option value="errors">Errors</option>
              </select>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px]">
              <div className="font-mono text-xs space-y-1">
                {logs
                  .filter(log => {
                    if (selectedLogLevel === 'all') return true
                    if (selectedLogLevel === 'tools') return log.includes('🔧')
                    if (selectedLogLevel === 'approvals') return log.includes('🔐')
                    if (selectedLogLevel === 'errors') return log.includes('❌')
                    return true
                  })
                  .map((log, idx) => (
                    <div key={idx} className="py-0.5">
                      {log}
                    </div>
                  ))
                }
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
        
        {/* Streaming Chat Interface */}
        <Card className="lg:col-span-3 mt-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                Streaming Chat with Tool Approvals
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setStreamingMessages([])
                  setPendingStreamApprovals([])
                  localStorage.removeItem('test_stream_conversation_id')
                  addLog("info", "Cleared streaming conversation")
                }}
              >
                <X className="mr-2 h-4 w-4" />
                Clear Chat
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              {/* Chat Messages Area */}
              <div className="flex-1">
                <ScrollArea className="h-[400px] border rounded-lg p-4 mb-4">
                  {streamingMessages.length === 0 ? (
                    <div className="text-center text-muted-foreground py-8">
                      Start a conversation to test streaming with tools...
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {streamingMessages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[70%] rounded-lg p-3 ${
                            msg.role === 'user' 
                              ? 'bg-primary text-primary-foreground' 
                              : 'bg-muted'
                          }`}>
                            {msg.role === 'assistant' && msg.toolCall && (
                              <div className="mb-2 p-2 bg-blue-100 dark:bg-blue-900/20 rounded text-sm">
                                <div className="flex items-center gap-2 font-medium">
                                  <Wrench className="h-4 w-4" />
                                  Using tool: {msg.toolCall.name}
                                </div>
                                <pre className="text-xs mt-1 overflow-x-auto">
                                  {JSON.stringify(msg.toolCall.arguments, null, 2)}
                                </pre>
                              </div>
                            )}
                            <div className={msg.streaming ? 'typing-indicator' : ''}>
                              {msg.content}
                              {msg.streaming && <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
                
                {/* Model Selection and Controls */}
                <div className="mb-4 space-y-3">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Select Model</label>
                    <Select value={selectedModel} onValueChange={setSelectedModel}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select AI model..." />
                      </SelectTrigger>
                      <SelectContent>
                        {availableModels.map(model => (
                          <SelectItem key={model} value={model}>{model}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <Switch checked={toolsEnabled} onCheckedChange={setToolsEnabled} />
                      <label className="text-sm">Enable MCP Tools</label>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch 
                        checked={streamAutoApprove}
                        onCheckedChange={setStreamAutoApprove}
                        disabled={!toolsEnabled}
                      />
                      <label className="text-sm">Auto-approve tools</label>
                    </div>
                  </div>
                </div>

                {/* Input Area */}
                <div className="flex gap-2">
                  <Textarea
                    value={streamingInput}
                    onChange={(e) => setStreamingInput(e.target.value)}
                    placeholder="Type a message... Try 'Calculate 15% of 2500' or 'What time is it in Tokyo?'"
                    className="flex-1"
                    rows={2}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleStreamingChat()
                      }
                    }}
                  />
                  <Button 
                    onClick={handleStreamingChat}
                    disabled={streamingActive || !streamingInput.trim() || !selectedModel}
                    className="px-6"
                  >
                    {streamingActive ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
              
              {/* Tool Approval Panel */}
              <div className="w-80">
                <div className="border rounded-lg p-4 h-[460px] overflow-y-auto">
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    Tool Approvals
                  </h4>
                  
                  {pendingStreamApprovals.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No tools awaiting approval
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {pendingStreamApprovals.map(approval => (
                        <div key={approval.id} className="p-3 border rounded-lg bg-yellow-50 dark:bg-yellow-900/10">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-sm">{approval.tool_name}</span>
                            <Badge variant="outline" className="text-xs">Pending</Badge>
                          </div>
                          <p className="text-xs text-muted-foreground mb-2">{approval.tool_description}</p>
                          <pre className="text-xs bg-muted p-2 rounded mb-2">
                            {JSON.stringify(approval.arguments, null, 2)}
                          </pre>
                          <div className="flex gap-2">
                            <Button 
                              size="sm" 
                              variant="default"
                              className="flex-1"
                              onClick={() => handleApprovalReal(approval.id, true)}
                            >
                              Approve
                            </Button>
                            <Button 
                              size="sm" 
                              variant="destructive"
                              className="flex-1"
                              onClick={() => handleApprovalReal(approval.id, false)}
                            >
                              Reject
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
    </div>
  )
}