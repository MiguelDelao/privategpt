'use client'

import { useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { config } from '@/lib/config'

export default function DebugPage() {
  const [logs, setLogs] = useState<string[]>([])
  
  const addLog = (message: string) => {
    setLogs(prev => [...prev, `${new Date().toISOString()}: ${message}`])
  }
  
  const testDirectFetch = async () => {
    addLog('Testing direct fetch...')
    try {
      const response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: 'admin@admin.com',
          password: 'admin'
        })
      })
      
      if (!response.ok) {
        addLog(`Direct fetch failed: ${response.status} ${response.statusText}`)
      } else {
        const data = await response.json()
        addLog(`Direct fetch success! Token: ${data.access_token.substring(0, 50)}...`)
      }
    } catch (error) {
      addLog(`Direct fetch error: ${error}`)
    }
  }
  
  const testApiClient = async () => {
    addLog('Testing API client...')
    addLog(`Config API URL: ${config.apiUrl}`)
    addLog(`API Client base URL: ${apiClient['baseURL']}`)
    
    try {
      const response = await apiClient.login('admin@admin.com', 'admin')
      addLog(`API client success! Token: ${response.access_token.substring(0, 50)}...`)
    } catch (error) {
      addLog(`API client error: ${error}`)
    }
  }
  
  const checkEnvironment = () => {
    addLog('=== Environment Check ===')
    addLog(`NODE_ENV: ${process.env.NODE_ENV}`)
    addLog(`NEXT_PUBLIC_API_URL: ${process.env.NEXT_PUBLIC_API_URL}`)
    addLog(`config.apiUrl: ${config.apiUrl}`)
    addLog(`window.location.origin: ${typeof window !== 'undefined' ? window.location.origin : 'SSR'}`)
  }
  
  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">API Debug Page</h1>
      
      <div className="space-y-4">
        <button
          onClick={checkEnvironment}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Check Environment
        </button>
        
        <button
          onClick={testDirectFetch}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          Test Direct Fetch
        </button>
        
        <button
          onClick={testApiClient}
          className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
        >
          Test API Client
        </button>
      </div>
      
      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-2">Logs:</h2>
        <div className="bg-black text-green-400 p-4 rounded font-mono text-sm h-96 overflow-y-auto">
          {logs.length === 0 ? (
            <div className="text-gray-500">No logs yet. Click a button to test.</div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="mb-1">{log}</div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}