"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { 
  Shield, 
  Users, 
  Settings, 
  Database, 
  Lock, 
  Save,
  Server,
  Activity,
  Clock,
  CheckCircle,
  AlertCircle,
  Wifi,
  WifiOff
} from "lucide-react"
import { useConnectionStatus, useServiceHealth, useLatency } from "@/lib/connection-monitor"
import { retryManager } from "@/lib/retry-manager"
import { errorHandler } from "@/lib/error-handler"

export function AdminPage() {
  const connectionStatus = useConnectionStatus()
  const serviceHealth = useServiceHealth()
  const latency = useLatency()
  
  const [settings, setSettings] = useState({
    organizationName: "Legal Firm LLC",
    maxUsers: "50",
    dataRetention: "365",
    enableAuditLog: true,
    enableNotifications: true,
    twoFactorAuth: true,
    publicAccess: false,
    apiAccess: true,
    autoBackup: true,
    encryptionLevel: "AES-256",
    sessionTimeout: "60",
    maxFileSize: "100",
    enableLogging: true
  })

  const [systemMetrics, setSystemMetrics] = useState({
    uptime: "99.8%",
    totalRequests: "1,247",
    activeUsers: "12",
    errorRate: "0.2%",
    responseTime: latency ? `${latency}ms` : "---",
    diskUsage: "45%"
  })

  useEffect(() => {
    // Update response time when latency changes
    if (latency) {
      setSystemMetrics(prev => ({
        ...prev,
        responseTime: `${latency}ms`
      }))
    }
  }, [latency])

  const handleToggle = (key: keyof typeof settings) => {
    setSettings(prev => ({
      ...prev,
      [key]: !prev[key]
    }))
  }

  const handleInputChange = (key: keyof typeof settings, value: string) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const handleSaveSettings = async () => {
    try {
      // Here you would save settings to the backend
      console.log('Saving settings:', settings)
      // await apiClient.saveAdminSettings(settings)
      
      // Show success message
      // showSuccess('Settings saved successfully')
    } catch (error) {
      console.error('Failed to save settings:', error)
      // errorHandler.handleApiError(error, 'AdminPage.saveSettings')
    }
  }

  const getConnectionStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <Wifi className="w-4 h-4 text-green-500" />
      case 'degraded':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />
      default:
        return <WifiOff className="w-4 h-4 text-red-500" />
    }
  }

  const getServiceStatusIcon = (healthy: boolean) => {
    return healthy 
      ? <CheckCircle className="w-4 h-4 text-green-500" />
      : <AlertCircle className="w-4 h-4 text-red-500" />
  }

  const circuitBreakerStats = retryManager.getCircuitBreakerStats()
  const errorStats = errorHandler.getErrorStats()

  return (
    <div className="h-full bg-[#171717] p-6 overflow-y-auto">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-8 h-8 text-blue-500" />
          <h1 className="text-3xl font-bold text-white">Admin Settings</h1>
        </div>

        {/* System Status Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-6"
        >
          <div className="flex items-center gap-2 mb-6">
            <Activity className="w-5 h-5 text-blue-500" />
            <h2 className="text-xl font-semibold text-white">System Status</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Connection Status */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-[#B4B4B4] uppercase tracking-wider">Connection</h3>
              <div className="flex items-center justify-between">
                <span className="text-white">Status</span>
                <div className="flex items-center gap-2">
                  {getConnectionStatusIcon()}
                  <span className="text-sm capitalize">{connectionStatus}</span>
                </div>
              </div>
              {latency && (
                <div className="flex items-center justify-between">
                  <span className="text-[#B4B4B4]">Latency</span>
                  <span className="text-white">{latency}ms</span>
                </div>
              )}
            </div>

            {/* Service Health */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-[#B4B4B4] uppercase tracking-wider">Services</h3>
              {Object.entries(serviceHealth).map(([service, healthy]) => (
                <div key={service} className="flex items-center justify-between">
                  <span className="text-[#B4B4B4] capitalize">{service}</span>
                  <div className="flex items-center gap-2">
                    {getServiceStatusIcon(healthy)}
                    <span className="text-sm">{healthy ? 'Healthy' : 'Degraded'}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* System Metrics */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-[#B4B4B4] uppercase tracking-wider">Metrics</h3>
              {Object.entries(systemMetrics).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-[#B4B4B4] capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</span>
                  <span className="text-white">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Error Statistics */}
          {errorStats.total > 0 && (
            <div className="mt-6 pt-6 border-t border-[#2A2A2A]">
              <h3 className="text-sm font-medium text-[#B4B4B4] mb-4">Error Statistics</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-[#B4B4B4]">Total Errors:</span>
                  <span className="text-white ml-2">{errorStats.total}</span>
                </div>
                <div>
                  <span className="text-[#B4B4B4]">Recent:</span>
                  <span className="text-white ml-2">{errorStats.recent}</span>
                </div>
                <div>
                  <span className="text-[#B4B4B4]">Network:</span>
                  <span className="text-white ml-2">{errorStats.byType.NETWORK_ERROR || 0}</span>
                </div>
                <div>
                  <span className="text-[#B4B4B4]">Server:</span>
                  <span className="text-white ml-2">{errorStats.byType.SERVER_ERROR || 0}</span>
                </div>
              </div>
            </div>
          )}
        </motion.div>

        {/* Organization Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-6"
        >
          <div className="flex items-center gap-2 mb-6">
            <Users className="w-5 h-5 text-blue-500" />
            <h2 className="text-xl font-semibold text-white">Organization</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-medium text-[#B4B4B4] mb-2">
                Organization Name
              </label>
              <input
                type="text"
                value={settings.organizationName}
                onChange={(e) => handleInputChange('organizationName', e.target.value)}
                className="w-full px-3 py-2 bg-[#171717] border border-[#2A2A2A] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-[#B4B4B4] mb-2">
                Maximum Users
              </label>
              <input
                type="number"
                value={settings.maxUsers}
                onChange={(e) => handleInputChange('maxUsers', e.target.value)}
                className="w-full px-3 py-2 bg-[#171717] border border-[#2A2A2A] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#B4B4B4] mb-2">
                Session Timeout (minutes)
              </label>
              <input
                type="number"
                value={settings.sessionTimeout}
                onChange={(e) => handleInputChange('sessionTimeout', e.target.value)}
                className="w-full px-3 py-2 bg-[#171717] border border-[#2A2A2A] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </motion.div>

        {/* Security Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-6"
        >
          <div className="flex items-center gap-2 mb-6">
            <Lock className="w-5 h-5 text-blue-500" />
            <h2 className="text-xl font-semibold text-white">Security</h2>
          </div>
          
          <div className="space-y-6">
            {[
              { key: 'twoFactorAuth', label: 'Two-Factor Authentication', description: 'Require 2FA for all admin accounts' },
              { key: 'enableAuditLog', label: 'Audit Logging', description: 'Track all user activities and changes' },
              { key: 'publicAccess', label: 'Public Access', description: 'Allow access without authentication (development only)' },
              { key: 'apiAccess', label: 'API Access', description: 'Enable external API access' },
              { key: 'enableLogging', label: 'Enable Debug Logging', description: 'Log detailed request/response information' }
            ].map((setting) => (
              <div key={setting.key} className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">{setting.label}</div>
                  <div className="text-sm text-[#B4B4B4]">{setting.description}</div>
                </div>
                <button
                  onClick={() => handleToggle(setting.key as keyof typeof settings)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings[setting.key as keyof typeof settings] ? 'bg-blue-600' : 'bg-[#2A2A2A]'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings[setting.key as keyof typeof settings] ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Data Management Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-6"
        >
          <div className="flex items-center gap-2 mb-6">
            <Database className="w-5 h-5 text-blue-500" />
            <h2 className="text-xl font-semibold text-white">Data Management</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
            <div>
              <label className="block text-sm font-medium text-[#B4B4B4] mb-2">
                Data Retention (days)
              </label>
              <input
                type="number"
                value={settings.dataRetention}
                onChange={(e) => handleInputChange('dataRetention', e.target.value)}
                className="w-full px-3 py-2 bg-[#171717] border border-[#2A2A2A] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-[#B4B4B4] mb-2">
                Max File Size (MB)
              </label>
              <input
                type="number"
                value={settings.maxFileSize}
                onChange={(e) => handleInputChange('maxFileSize', e.target.value)}
                className="w-full px-3 py-2 bg-[#171717] border border-[#2A2A2A] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#B4B4B4] mb-2">
                Encryption Level
              </label>
              <select
                value={settings.encryptionLevel}
                onChange={(e) => handleInputChange('encryptionLevel', e.target.value)}
                className="w-full px-3 py-2 bg-[#171717] border border-[#2A2A2A] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="AES-128">AES-128</option>
                <option value="AES-256">AES-256</option>
              </select>
            </div>
          </div>

          <div className="space-y-4">
            {[
              { key: 'autoBackup', label: 'Automatic Backups', description: 'Enable daily automated backups' },
              { key: 'enableNotifications', label: 'System Notifications', description: 'Receive notifications for system events' }
            ].map((setting) => (
              <div key={setting.key} className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">{setting.label}</div>
                  <div className="text-sm text-[#B4B4B4]">{setting.description}</div>
                </div>
                <button
                  onClick={() => handleToggle(setting.key as keyof typeof settings)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings[setting.key as keyof typeof settings] ? 'bg-blue-600' : 'bg-[#2A2A2A]'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings[setting.key as keyof typeof settings] ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Save Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="flex justify-end"
        >
          <button 
            onClick={handleSaveSettings}
            className="flex items-center gap-2 px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            <Save className="w-4 h-4" />
            Save Settings
          </button>
        </motion.div>
      </div>
    </div>
  )
}