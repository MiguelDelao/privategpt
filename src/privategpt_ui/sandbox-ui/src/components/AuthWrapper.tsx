"use client"

import { useAuthStore } from "@/stores/authStore"
import { LoginPage } from "./LoginPage"
import { ReactNode, useEffect, useState } from "react"

interface AuthWrapperProps {
  children: ReactNode
}

export function AuthWrapper({ children }: AuthWrapperProps) {
  const { isAuthenticated, verifyAuth, logout } = useAuthStore()
  const [isVerifying, setIsVerifying] = useState(true)

  useEffect(() => {
    // Verify stored auth token on mount
    const checkAuth = async () => {
      // Check if we have a token in localStorage
      const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('auth_token')
      
      if (hasToken && isAuthenticated) {
        try {
          const isValid = await verifyAuth()
          if (!isValid) {
            logout()
          }
        } catch (error) {
          console.error('Auth verification failed:', error)
          logout()
        }
      } else if (!hasToken) {
        // No token found, ensure we're logged out
        logout()
      }
      setIsVerifying(false)
    }
    
    checkAuth()
  }, [])

  useEffect(() => {
    // Listen for auth token expiration events
    const handleTokenExpired = () => {
      console.log('Auth token expired, logging out...')
      logout()
    }

    window.addEventListener('auth-token-expired', handleTokenExpired)
    return () => {
      window.removeEventListener('auth-token-expired', handleTokenExpired)
    }
  }, [logout])

  // Show loading state while verifying
  if (isVerifying) {
    return (
      <div className="min-h-screen bg-[#171717] flex items-center justify-center">
        <div className="text-white">Verifying authentication...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginPage />
  }

  return <>{children}</>
}