"use client"

import { useState } from "react"
import { 
  Shield, 
  Users, 
  Settings, 
  Database, 
  Globe, 
  Lock, 
  Bell,
  Eye,
  EyeOff,
  Save
} from "lucide-react"

export function AdminSettings() {
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
    encryptionLevel: "AES-256"
  })

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

  return (
    <div className="h-full bg-[#171717] p-6 overflow-y-auto">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Shield className="w-8 h-8 text-blue-500" />
            <h1 className="text-3xl font-bold text-white">Admin Settings</h1>
          </div>
          <p className="text-[#B4B4B4]">Manage your organization's configuration and security settings</p>
        </div>

        {/* Settings Sections */}
        <div className="space-y-8">
          
          {/* Organization Settings */}
          <div className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Users className="w-5 h-5 text-blue-500" />
              <h2 className="text-xl font-semibold text-white">Organization</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            </div>
          </div>

          {/* Security Settings */}
          <div className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Lock className="w-5 h-5 text-blue-500" />
              <h2 className="text-xl font-semibold text-white">Security</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">Two-Factor Authentication</div>
                  <div className="text-sm text-[#B4B4B4]">Require 2FA for all admin accounts</div>
                </div>
                <button
                  onClick={() => handleToggle('twoFactorAuth')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.twoFactorAuth ? 'bg-blue-600' : 'bg-[#2A2A2A]'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.twoFactorAuth ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">Audit Logging</div>
                  <div className="text-sm text-[#B4B4B4]">Track all user activities and changes</div>
                </div>
                <button
                  onClick={() => handleToggle('enableAuditLog')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.enableAuditLog ? 'bg-blue-600' : 'bg-[#2A2A2A]'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.enableAuditLog ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
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
                  <option value="RSA-2048">RSA-2048</option>
                </select>
              </div>
            </div>
          </div>

          {/* Data Management */}
          <div className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Database className="w-5 h-5 text-blue-500" />
              <h2 className="text-xl font-semibold text-white">Data Management</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">Auto Backup</div>
                  <div className="text-sm text-[#B4B4B4]">Daily automated backups</div>
                </div>
                <button
                  onClick={() => handleToggle('autoBackup')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.autoBackup ? 'bg-blue-600' : 'bg-[#2A2A2A]'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.autoBackup ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
            
            {/* Clear Conversations Section */}
            <div className="mt-6 pt-6 border-t border-[#2A2A2A]">
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

          {/* API & Access */}
          <div className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Globe className="w-5 h-5 text-blue-500" />
              <h2 className="text-xl font-semibold text-white">API & Access</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">API Access</div>
                  <div className="text-sm text-[#B4B4B4]">Enable REST API endpoints</div>
                </div>
                <button
                  onClick={() => handleToggle('apiAccess')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.apiAccess ? 'bg-blue-600' : 'bg-[#2A2A2A]'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.apiAccess ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">Public Access</div>
                  <div className="text-sm text-[#B4B4B4]">Allow public registration</div>
                </div>
                <button
                  onClick={() => handleToggle('publicAccess')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.publicAccess ? 'bg-blue-600' : 'bg-[#2A2A2A]'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.publicAccess ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">Notifications</div>
                  <div className="text-sm text-[#B4B4B4]">Email notifications for admin events</div>
                </div>
                <button
                  onClick={() => handleToggle('enableNotifications')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.enableNotifications ? 'bg-blue-600' : 'bg-[#2A2A2A]'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.enableNotifications ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <button className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              <Save className="w-4 h-4" />
              Save Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}