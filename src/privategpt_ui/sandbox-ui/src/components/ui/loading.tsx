"use client"

import { cn } from "@/lib/utils"

interface LoadingSkeletonProps {
  className?: string
}

export function LoadingSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div 
      className={cn(
        "animate-pulse bg-[#2A2A2A] rounded",
        className
      )}
    />
  )
}

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6', 
    lg: 'w-8 h-8'
  }

  return (
    <div 
      className={cn(
        "border-2 border-[#2A2A2A] border-t-blue-500 rounded-full animate-spin",
        sizeClasses[size],
        className
      )}
    />
  )
}

interface LoadingDotsProps {
  className?: string
}

export function LoadingDots({ className }: LoadingDotsProps) {
  return (
    <div className={cn("flex space-x-1", className)}>
      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
    </div>
  )
}

// Document loading skeleton
export function DocumentSkeleton() {
  return (
    <div className="p-6 space-y-4">
      <LoadingSkeleton className="h-8 w-3/4" />
      <LoadingSkeleton className="h-4 w-full" />
      <LoadingSkeleton className="h-4 w-5/6" />
      <LoadingSkeleton className="h-4 w-4/5" />
      <div className="space-y-2 mt-6">
        <LoadingSkeleton className="h-4 w-full" />
        <LoadingSkeleton className="h-4 w-11/12" />
        <LoadingSkeleton className="h-4 w-3/4" />
      </div>
    </div>
  )
}

// Chat message loading skeleton
export function ChatMessageSkeleton() {
  return (
    <div className="space-y-3">
      <div className="flex items-start gap-3">
        <LoadingSkeleton className="w-8 h-8 rounded-full flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <LoadingSkeleton className="h-4 w-3/4" />
          <LoadingSkeleton className="h-4 w-1/2" />
        </div>
      </div>
    </div>
  )
}

// Sidebar item loading skeleton
export function SidebarSkeleton() {
  return (
    <div className="space-y-2 p-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <LoadingSkeleton className="w-4 h-4 rounded" />
          <LoadingSkeleton className="h-4 flex-1" />
        </div>
      ))}
    </div>
  )
}

// Template grid loading skeleton
export function TemplateSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="border border-[#2A2A2A] rounded-lg p-4 space-y-3">
          <LoadingSkeleton className="h-6 w-3/4" />
          <LoadingSkeleton className="h-4 w-full" />
          <LoadingSkeleton className="h-4 w-2/3" />
          <div className="flex gap-2 mt-4">
            <LoadingSkeleton className="h-6 w-16 rounded-full" />
            <LoadingSkeleton className="h-6 w-20 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  )
}

// Full page loading component
export function PageLoading() {
  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="text-center">
        <LoadingSpinner size="lg" className="mx-auto mb-4" />
        <p className="text-sm text-[#B4B4B4]">Loading...</p>
      </div>
    </div>
  )
}

// Typing indicator for chat
export function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 px-4 py-2 text-[#6B6B6B]">
      <LoadingDots />
      <span className="text-sm">AI is typing...</span>
    </div>
  )
}