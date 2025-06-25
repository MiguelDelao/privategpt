"use client"

import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, Send, AlertCircle, CheckCircle } from "lucide-react"

// Test Interface for debugging chat functionality
export default function TestPage() {
  // Direct Chat State
  const [directMessage, setDirectMessage] = useState("")
  const [directResponse, setDirectResponse] = useState("")
  const [directLoading, setDirectLoading] = useState(false)
  const [directError, setDirectError] = useState<string | null>(null)
  
  // Streaming Chat State
  const [streamMessage, setStreamMessage] = useState("")
  const [streamResponse, setStreamResponse] = useState("")
  const [streamLoading, setStreamLoading] = useState(false)
  const [streamError, setStreamError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  
  // Conversation State
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<any[]>([])
  
  // Request/Response Logs
  const [logs, setLogs] = useState<string[]>([])
  
  // Auth State
  const [token, setToken] = useState<string | null>(null)
  
  useEffect(() => {
    // Load token from localStorage
    const storedToken = localStorage.getItem('auth_token')
    if (storedToken) {
      setToken(storedToken)
      addLog("Token loaded from localStorage")
    } else {
      addLog("No token found in localStorage")
    }
  }, [])
  
  const addLog = (message: string) => {
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0]
    setLogs(prev => [`[${timestamp}] ${message}`, ...prev].slice(0, 50))
  }
  
  // Test Direct Chat
  const testDirectChat = async () => {
    setDirectLoading(true)
    setDirectError(null)
    setDirectResponse("")
    
    const payload = {
      message: directMessage,
      model: "tinyllama:1.1b", // Hardcoded small model
      stream: false
    }
    
    addLog(`Direct Chat Request: ${JSON.stringify(payload)}`)
    
    try {
      const response = await fetch("http://localhost:8000/api/chat/direct", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {})
        },
        body: JSON.stringify(payload)
      })
      
      addLog(`Direct Chat Response Status: ${response.status} ${response.statusText}`)
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`${response.status}: ${errorText}`)
      }
      
      const data = await response.json()
      addLog(`Direct Chat Success: ${JSON.stringify(data).substring(0, 100)}...`)
      setDirectResponse(data.text || data.content || "No content in response")
      
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Unknown error"
      addLog(`Direct Chat Error: ${errorMsg}`)
      setDirectError(errorMsg)
    } finally {
      setDirectLoading(false)
    }
  }
  
  // Test Streaming Chat
  const testStreamingChat = async () => {
    setStreamLoading(true)
    setStreamError(null)
    setStreamResponse("")
    
    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    
    const payload = {
      message: streamMessage,
      model: "tinyllama:1.1b", // Hardcoded small model
      stream: true
    }
    
    addLog(`Streaming Request: ${JSON.stringify(payload)}`)
    
    try {
      const response = await fetch("http://localhost:8000/api/chat/direct", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
          ...(token ? { "Authorization": `Bearer ${token}` } : {})
        },
        body: JSON.stringify(payload)
      })
      
      addLog(`Streaming Response Status: ${response.status} ${response.statusText}`)
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`${response.status}: ${errorText}`)
      }
      
      if (!response.body) {
        throw new Error("No response body")
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          addLog("Stream completed")
          break
        }
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ""
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6)
            if (data === "[DONE]") {
              addLog("Stream ended with [DONE]")
              setStreamLoading(false)
              return
            }
            
            try {
              const parsed = JSON.parse(data)
              addLog(`Stream chunk: ${JSON.stringify(parsed).substring(0, 100)}`)
              
              if (parsed.content) {
                setStreamResponse(prev => prev + parsed.content)
              } else if (parsed.delta?.content) {
                setStreamResponse(prev => prev + parsed.delta.content)
              } else if (parsed.text) {
                setStreamResponse(prev => prev + parsed.text)
              }
              
            } catch (e) {
              addLog(`Failed to parse SSE data: ${data}`)
            }
          }
        }
      }
      
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Unknown error"
      addLog(`Streaming Error: ${errorMsg}`)
      setStreamError(errorMsg)
    } finally {
      setStreamLoading(false)
    }
  }
  
  // Test Create Conversation
  const testCreateConversation = async () => {
    addLog("Creating new conversation...")
    
    try {
      const response = await fetch("http://localhost:8000/api/chat/conversations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          title: "Test Conversation",
          model: "tinyllama:1.1b"  // Backend expects "model" not "model_name"
        })
      })
      
      addLog(`Create Conversation Response: ${response.status} ${response.statusText}`)
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`${response.status}: ${errorText}`)
      }
      
      const data = await response.json()
      addLog(`Conversation Created: ${JSON.stringify(data)}`)
      setConversationId(data.id)
      
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Unknown error"
      addLog(`Create Conversation Error: ${errorMsg}`)
    }
  }
  
  // Test List Conversations
  const testListConversations = async () => {
    addLog("Listing conversations...")
    
    try {
      const response = await fetch("http://localhost:8000/api/chat/conversations", {
        headers: {
          ...(token ? { "Authorization": `Bearer ${token}` } : {})
        }
      })
      
      addLog(`List Conversations Response: ${response.status} ${response.statusText}`)
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`${response.status}: ${errorText}`)
      }
      
      const data = await response.json()
      addLog(`Conversations Found: ${data.length}`)
      setConversations(data)
      
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Unknown error"
      addLog(`List Conversations Error: ${errorMsg}`)
    }
  }
  
  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <h1 className="text-3xl font-bold mb-6">Chat API Test Interface</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chat Testing */}
        <Card>
          <CardHeader>
            <CardTitle>Chat Testing</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="direct">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="direct">Direct Chat</TabsTrigger>
                <TabsTrigger value="stream">Streaming Chat</TabsTrigger>
              </TabsList>
              
              <TabsContent value="direct" className="space-y-4">
                <div>
                  <div className="text-sm font-medium mb-2">Message</div>
                  <Textarea
                    value={directMessage}
                    onChange={(e) => setDirectMessage(e.target.value)}
                    placeholder="Enter your message..."
                    className="min-h-[100px]"
                  />
                </div>
                
                <Button 
                  onClick={testDirectChat}
                  disabled={directLoading || !directMessage}
                  className="w-full"
                >
                  {directLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send className="mr-2 h-4 w-4" />
                      Send Direct Message
                    </>
                  )}
                </Button>
                
                {directError && (
                  <div className="p-4 bg-red-100 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5" />
                    <span className="text-sm text-red-600 dark:text-red-400">{directError}</span>
                  </div>
                )}
                
                {directResponse && (
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="text-sm font-medium mb-2">Response:</div>
                    <p className="mt-2">{directResponse}</p>
                  </div>
                )}
              </TabsContent>
              
              <TabsContent value="stream" className="space-y-4">
                <div>
                  <div className="text-sm font-medium mb-2">Message</div>
                  <Textarea
                    value={streamMessage}
                    onChange={(e) => setStreamMessage(e.target.value)}
                    placeholder="Enter your message..."
                    className="min-h-[100px]"
                  />
                </div>
                
                <Button 
                  onClick={testStreamingChat}
                  disabled={streamLoading || !streamMessage}
                  className="w-full"
                >
                  {streamLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Streaming...
                    </>
                  ) : (
                    <>
                      <Send className="mr-2 h-4 w-4" />
                      Start Streaming
                    </>
                  )}
                </Button>
                
                {streamError && (
                  <div className="p-4 bg-red-100 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5" />
                    <span className="text-sm text-red-600 dark:text-red-400">{streamError}</span>
                  </div>
                )}
                
                {streamResponse && (
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="text-sm font-medium mb-2">Response:</div>
                    <p className="mt-2 whitespace-pre-wrap">{streamResponse}</p>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
        
        {/* Conversation Testing */}
        <Card>
          <CardHeader>
            <CardTitle>Conversation Management</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Button onClick={testCreateConversation} className="w-full">
                Create New Conversation
              </Button>
              <Button onClick={testListConversations} variant="outline" className="w-full">
                List Conversations
              </Button>
            </div>
            
            {conversationId && (
              <div className="p-4 bg-green-100 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-start gap-2">
                <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5" />
                <span className="text-sm text-green-600 dark:text-green-400">
                  Active Conversation: {conversationId}
                </span>
              </div>
            )}
            
            {conversations.length > 0 && (
              <div className="space-y-2">
                <div className="text-sm font-medium mb-2">Found {conversations.length} conversations:</div>
                <ScrollArea className="h-[200px] w-full rounded border p-2">
                  {conversations.map((conv, idx) => (
                    <div key={idx} className="text-sm py-1">
                      {conv.id}: {conv.title}
                    </div>
                  ))}
                </ScrollArea>
              </div>
            )}
          </CardContent>
        </Card>
        
        {/* Request Logs */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Request/Response Logs</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px] w-full rounded border">
              <div className="p-4 font-mono text-xs">
                {logs.length === 0 ? (
                  <p className="text-muted-foreground">No logs yet...</p>
                ) : (
                  logs.map((log, idx) => (
                    <div key={idx} className="py-1">
                      {log}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}