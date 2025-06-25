"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { Mail, Lock, ArrowRight, Eye, EyeOff } from "lucide-react"
import { useAuthStore } from "@/stores/authStore"

export function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  
  const { login } = useAuthStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError("")

    try {
      const success = await login(email, password)
      if (!success) {
        setError("Please enter both email and password")
      }
    } catch (err: any) {
      // Show error with suggestions if available
      if (err.getUserMessage) {
        setError(err.getUserMessage())
      } else if (err.code === 'AUTH_ERROR' || err.code === 'UNAUTHORIZED') {
        setError("Invalid email or password")
      } else if (err.code === 'NETWORK_ERROR' || err.message?.includes('fetch failed')) {
        setError("Unable to connect to server. Please check your connection and try again.")
      } else if (err.code === 'RATE_LIMIT_ERROR') {
        setError("Too many login attempts. Please wait a moment and try again.")
      } else {
        setError(err.message || "Login failed. Please try again.")
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleAutoFill = () => {
    setEmail("admin@admin.com")
    setPassword("admin")
  }

  return (
    <div className="min-h-screen bg-[#171717] flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="w-full max-w-md"
      >
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="text-white font-bold text-2xl">S</span>
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">PrivateGPT</h1>
          <p className="text-[#B4B4B4]">Secure AI Chat Interface</p>
        </div>

        {/* Login Form */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-2xl p-8"
        >
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-white mb-2">Welcome back</h2>
            <p className="text-[#B4B4B4] text-sm">Sign in to continue to your workspace</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-white mb-2">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6B6B6B]" />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  className="w-full pl-10 pr-4 py-3 bg-[#171717] border border-[#2A2A2A] rounded-xl text-white placeholder-[#6B6B6B] focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  required
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-white mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6B6B6B]" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full pl-10 pr-12 py-3 bg-[#171717] border border-[#2A2A2A] rounded-xl text-white placeholder-[#6B6B6B] focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#6B6B6B] hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg"
              >
                <p className="text-red-400 text-sm">{error}</p>
              </motion.div>
            )}

            {/* Submit Button */}
            <motion.button
              type="submit"
              disabled={isLoading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Sign in
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </motion.button>
          </form>

          {/* Auto-fill for quick login */}
          <div className="mt-6 pt-6 border-t border-[#2A2A2A]">
            <button
              type="button"
              onClick={handleAutoFill}
              className="w-full text-center text-sm text-[#B4B4B4] hover:text-white transition-colors"
            >
              Use admin credentials
            </button>
          </div>
        </motion.div>

      </motion.div>
    </div>
  )
}