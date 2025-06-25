"use client"

import { useState } from "react"
import { LogOut, User, ChevronDown } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { useAuthStore } from "@/stores/authStore"

export function UserDropdown() {
  const { logout, user } = useAuthStore()
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="relative flex items-center gap-2">
      {/* Username display */}
      {user && (
        <span className="text-sm text-[#B4B4B4] hidden md:block">
          {user.email || user.name || 'User'}
        </span>
      )}
      
      {/* User Avatar - Clickable */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="w-8 h-8 bg-white rounded-full flex items-center justify-center hover:ring-2 hover:ring-white/30 transition-all"
      >
        <User className="w-4 h-4 text-gray-700" />
      </motion.button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop to close dropdown */}
            <div 
              className="fixed inset-0 z-10" 
              onClick={() => setIsOpen(false)}
            />
            
            {/* Dropdown Content */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-10 z-20 bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg shadow-xl py-2 min-w-48"
            >
              {/* User info */}
              {user && (
                <div className="px-3 py-2 border-b border-[#2A2A2A]">
                  <div className="text-sm text-white font-medium">
                    {user.name || 'User'}
                  </div>
                  <div className="text-xs text-[#6B6B6B]">
                    {user.email}
                  </div>
                </div>
              )}
              
              <button
                onClick={() => {
                  logout()
                  setIsOpen(false)
                }}
                className="w-full text-left px-3 py-2 text-sm text-[#B4B4B4] hover:text-white hover:bg-[#2A2A2A] transition-colors flex items-center gap-3"
              >
                <LogOut className="w-4 h-4" />
                Sign out
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}