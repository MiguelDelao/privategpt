import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiClient } from '@/lib/api-client'

interface User {
  id: string
  email: string
  name: string
  role?: string
}

interface AuthState {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<boolean>
  logout: () => void
  verifyAuth: () => Promise<boolean>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      user: null,
      token: null,

      login: async (email: string, password: string) => {
        try {
          const response = await apiClient.login(email, password)
          
          const user: User = {
            id: response.user?.user_id?.toString() || '1',
            email: response.user?.email || email,
            name: email.split('@')[0] || 'User',
            role: response.user?.role || 'user'
          }
          
          set({
            isAuthenticated: true,
            user,
            token: response.access_token
          })
          
          // Also ensure the token is available in localStorage for the API client
          if (typeof window !== 'undefined') {
            localStorage.setItem('auth_token', response.access_token)
          }
          
          return true
        } catch (error: any) {
          console.error('Login failed:', error)
          // Always throw the error - no demo fallback
          throw error
        }
      },

      logout: () => {
        apiClient.logout()
        set({
          isAuthenticated: false,
          user: null,
          token: null
        })
        
        // Also clear the auth_token from localStorage
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token')
        }
      },

      verifyAuth: async () => {
        const state = get()
        
        // If no token, not authenticated
        if (!state.token) {
          return false
        }
        
        try {
          const result = await apiClient.verifyToken()
          if (result.valid) {
            return true
          } else {
            // Token invalid, clear auth state
            set({
              isAuthenticated: false,
              user: null,
              token: null
            })
            return false
          }
        } catch (error) {
          console.error('Auth verification failed:', error)
          // Clear auth state on any error
          set({
            isAuthenticated: false,
            user: null,
            token: null
          })
          return false
        }
      }
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        token: state.token
      })
    }
  )
)