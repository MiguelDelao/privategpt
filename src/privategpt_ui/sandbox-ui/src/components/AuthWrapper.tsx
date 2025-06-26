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
    // Skip token verification on mount - just trust stored state for now
    const checkAuth = async () => {
      console.log('AuthWrapper: Skipping token verification, trusting stored auth state')
      setIsVerifying(false)
    }
    
    checkAuth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Intentionally empty - only run on mount

  useEffect(() => {
    // Listen for auth token expiration events
    const handleTokenExpired = () => {
      console.log('Auth token expired, logging out...')
      // Get the latest logout function directly from store to avoid dependency issues
      useAuthStore.getState().logout()
    }

    window.addEventListener('auth-token-expired', handleTokenExpired)
    return () => {
      window.removeEventListener('auth-token-expired', handleTokenExpired)
    }
  }, [])

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