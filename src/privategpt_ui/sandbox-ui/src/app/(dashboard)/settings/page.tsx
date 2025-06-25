"use client"

import { useState } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Trash2, AlertTriangle } from 'lucide-react'

export default function SettingsRoute() {
  const [isClearing, setIsClearing] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const { clearAllSessions, sessions } = useChatStore()
  const sessionCount = Object.keys(sessions).length
  return (
    <div className="h-full bg-[#171717] flex flex-col">
      <div className="border-b border-[#2A2A2A] bg-[#1A1A1A] p-6">
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-[#B4B4B4] mt-2">Configure your application preferences</p>
      </div>
      
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-white mb-4">General Settings</h2>
            <p className="text-[#B4B4B4]">Settings functionality will be implemented here.</p>
          </div>
          
          <div className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Trash2 className="w-5 h-5" />
              Data Management
            </h2>
            
            <div className="border border-red-500/20 bg-red-500/10 rounded-lg p-4">
              <h3 className="text-lg font-medium text-red-400 mb-2 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                Clear All Conversations
              </h3>
              <p className="text-gray-400 mb-4">
                This will permanently delete all {sessionCount} conversation{sessionCount !== 1 ? 's' : ''} from your account. This action cannot be undone.
              </p>
              
              {!showConfirm ? (
                <button
                  onClick={() => setShowConfirm(true)}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                  disabled={sessionCount === 0}
                >
                  <Trash2 className="w-4 h-4" />
                  Clear All Conversations
                </button>
              ) : (
                <div className="flex items-center gap-3">
                  <button
                    onClick={async () => {
                      setIsClearing(true)
                      try {
                        await clearAllSessions()
                        setShowConfirm(false)
                      } catch (error) {
                        console.error('Failed to clear all sessions:', error)
                      } finally {
                        setIsClearing(false)
                      }
                    }}
                    disabled={isClearing}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                  >
                    {isClearing ? 'Clearing...' : 'Yes, Delete All'}
                  </button>
                  <button
                    onClick={() => setShowConfirm(false)}
                    disabled={isClearing}
                    className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}