'use client'

import { useState } from 'react'
import { apiClient } from '@/lib/api-client'

export default function LoginTestPage() {
  const [status, setStatus] = useState<string>('')
  const [error, setError] = useState<string>('')
  
  const testLogin = async () => {
    setStatus('Testing login...')
    setError('')
    
    try {
      console.log('Starting login test...')
      const response = await apiClient.login('admin@admin.com', 'admin')
      console.log('Login response:', response)
      
      setStatus(`Login successful! Token: ${response.access_token.substring(0, 50)}...`)
      
      // Test a protected endpoint
      setTimeout(async () => {
        try {
          setStatus(prev => prev + '\n\nTesting protected endpoint...')
          const conversations = await apiClient.getConversations()
          setStatus(prev => prev + `\nFetched ${conversations.length} conversations!`)
        } catch (err) {
          setError(`Protected endpoint error: ${err}`)
        }
      }, 1000)
      
    } catch (err: any) {
      console.error('Login error:', err)
      setError(`Error: ${err.message || err}`)
    }
  }
  
  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Login Test</h1>
      
      <button
        onClick={testLogin}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 mb-4"
      >
        Test Login
      </button>
      
      {status && (
        <div className="p-4 bg-green-900/20 border border-green-500/30 rounded mb-4">
          <pre className="whitespace-pre-wrap text-green-400">{status}</pre>
        </div>
      )}
      
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-500/30 rounded">
          <pre className="whitespace-pre-wrap text-red-400">{error}</pre>
        </div>
      )}
    </div>
  )
}