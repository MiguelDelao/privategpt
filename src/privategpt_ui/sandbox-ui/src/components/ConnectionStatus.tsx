"use client"

import { motion, AnimatePresence } from "framer-motion"
import { Wifi, WifiOff, AlertTriangle, CheckCircle, X } from "lucide-react"
import { useState } from "react"
import { useConnectionStatus, useLatency, connectionMonitor } from "@/lib/connection-monitor"

export function ConnectionStatus() {
  const status = useConnectionStatus()
  const latency = useLatency()
  const [showDetails, setShowDetails] = useState(false)
  const [isRunningTest, setIsRunningTest] = useState(false)

  const getStatusConfig = () => {
    switch (status) {
      case 'connected':
        return {
          icon: Wifi,
          color: 'text-green-500',
          bgColor: 'bg-green-500/10',
          borderColor: 'border-green-500/20',
          text: 'Connected',
          showBanner: false
        }
      case 'degraded':
        return {
          icon: AlertTriangle,
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-500/10',
          borderColor: 'border-yellow-500/20',
          text: 'Degraded',
          showBanner: true
        }
      case 'disconnected':
        return {
          icon: WifiOff,
          color: 'text-red-500',
          bgColor: 'bg-red-500/10',
          borderColor: 'border-red-500/20',
          text: 'Disconnected',
          showBanner: true
        }
      case 'reconnecting':
        return {
          icon: Wifi,
          color: 'text-blue-500',
          bgColor: 'bg-blue-500/10',
          borderColor: 'border-blue-500/20',
          text: 'Reconnecting...',
          showBanner: true
        }
      default:
        return {
          icon: WifiOff,
          color: 'text-gray-500',
          bgColor: 'bg-gray-500/10',
          borderColor: 'border-gray-500/20',
          text: 'Unknown',
          showBanner: false
        }
    }
  }

  const handleTestConnection = async () => {
    setIsRunningTest(true)
    try {
      const result = await connectionMonitor.testConnection()
      console.log('Connection test result:', result)
    } catch (error) {
      console.error('Connection test failed:', error)
    } finally {
      setIsRunningTest(false)
    }
  }

  const config = getStatusConfig()
  const Icon = config.icon

  return (
    <>
      {/* Connection Banner - shown when not connected properly */}
      <AnimatePresence>
        {config.showBanner && (
          <motion.div
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -50 }}
            className={`fixed top-0 left-0 right-0 z-50 ${config.bgColor} ${config.borderColor} border-b backdrop-blur-sm`}
            style={{ paddingTop: 'env(safe-area-inset-top)' }}
          >
            <div className="container mx-auto px-4 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Icon className={`w-5 h-5 ${config.color}`} />
                  <div>
                    <span className={`font-medium ${config.color}`}>
                      Connection {config.text}
                    </span>
                    {status === 'degraded' && (
                      <span className="text-sm text-yellow-400 ml-2">
                        Some features may be limited
                      </span>
                    )}
                    {status === 'disconnected' && (
                      <span className="text-sm text-red-400 ml-2">
                        Please check your internet connection
                      </span>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleTestConnection}
                    disabled={isRunningTest}
                    className="text-xs px-3 py-1 rounded-full bg-white/10 hover:bg-white/20 transition-colors disabled:opacity-50"
                  >
                    {isRunningTest ? 'Testing...' : 'Test Connection'}
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Status Indicator - always visible in bottom right */}
      <div className="fixed bottom-4 right-4 z-40">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowDetails(!showDetails)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg ${config.bgColor} ${config.borderColor} border backdrop-blur-sm shadow-lg transition-all`}
        >
          <Icon className={`w-4 h-4 ${config.color}`} />
          <span className={`text-sm font-medium ${config.color}`}>
            {config.text}
          </span>
          {latency && (
            <span className="text-xs text-gray-400">
              {latency}ms
            </span>
          )}
        </motion.button>

        {/* Connection Details Modal */}
        <AnimatePresence>
          {showDetails && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 10 }}
              className="absolute bottom-full right-0 mb-2 w-80 bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-4 shadow-xl"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-medium">Connection Status</h3>
                <button
                  onClick={() => setShowDetails(false)}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400 text-sm">Status</span>
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${config.color}`} />
                    <span className={`text-sm ${config.color}`}>{config.text}</span>
                  </div>
                </div>

                {latency && (
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400 text-sm">Latency</span>
                    <span className="text-white text-sm">{latency}ms</span>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <span className="text-gray-400 text-sm">Services</span>
                  <div className="flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-green-500" />
                    <span className="text-xs text-green-500">Gateway</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-[#2A2A2A]">
                  <button
                    onClick={handleTestConnection}
                    disabled={isRunningTest}
                    className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white text-sm rounded-lg transition-colors"
                  >
                    {isRunningTest ? 'Testing Connection...' : 'Test Connection'}
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  )
}