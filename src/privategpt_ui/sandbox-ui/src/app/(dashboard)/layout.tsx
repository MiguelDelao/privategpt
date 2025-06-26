"use client"

import { Sidebar } from "@/components/shell/Sidebar"
import { UploadProgress } from "@/components/documents/UploadProgress"
import { useState } from "react"
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="flex h-full bg-[#171717]">
        {/* Shared Dashboard Sidebar */}
        <Sidebar 
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />
        
        {/* Main Content Area */}
        <div className="flex-1 min-w-0">
          {children}
        </div>
        
        {/* Upload Progress Overlay */}
        <UploadProgress />
      </div>
    </DndProvider>
  )
}