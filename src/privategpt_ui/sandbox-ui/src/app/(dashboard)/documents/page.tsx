"use client"

import { useState, useEffect } from 'react'
import { DataSourcesPanel } from '@/components/documents/DataSourcesPanel'
import { DocumentUploader } from '@/components/documents/DocumentUploader'
import { DocumentsList } from '@/components/documents/DocumentsList'
import { useDocumentStore } from '@/stores/documentStore'
import { Folder, Upload, FileText, Clock } from 'lucide-react'

export default function DocumentsRoute() {
  const { selectedCollectionId, getCollectionById, uploadingFiles } = useDocumentStore()
  const selectedCollection = selectedCollectionId ? getCollectionById(selectedCollectionId) : null
  
  return (
    <div className="flex h-full bg-[#171717]">
      {/* Sidebar */}
      <div className="w-80 border-r border-gray-800 bg-gray-900">
        <DataSourcesPanel />
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-800 px-6 py-4">
          <h1 className="text-2xl font-semibold text-white">Documents</h1>
          <p className="text-gray-400 mt-1">
            {selectedCollection 
              ? `${selectedCollection.icon} ${selectedCollection.name}` 
              : 'Select a collection to manage documents'}
          </p>
        </div>
        
        {selectedCollection ? (
          <div className="flex-1 overflow-hidden">
            <div className="h-full flex">
              {/* Left: Upload and Status */}
              <div className="w-96 border-r border-gray-800 flex flex-col">
                {/* Upload Section */}
                <div className="p-6 border-b border-gray-800">
                  <h2 className="text-lg font-medium text-white mb-4 flex items-center">
                    <Upload className="w-5 h-5 mr-2" />
                    Upload Documents
                  </h2>
                  <DocumentUploader 
                    collectionId={selectedCollection.id} 
                    embedded={true}
                  />
                </div>
                
                {/* Upload Status Section */}
                {uploadingFiles.length > 0 && (
                  <div className="flex-1 p-6 overflow-y-auto">
                    <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center">
                      <Clock className="w-4 h-4 mr-2" />
                      Upload Progress ({uploadingFiles.length})
                    </h3>
                    <div className="space-y-3">
                      {uploadingFiles.map((file) => (
                        <div key={file.id} className="bg-gray-800 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm text-white truncate">{file.file.name}</span>
                            <span className="text-xs text-gray-400">{file.progress}%</span>
                          </div>
                          <div className="w-full bg-gray-700 rounded-full h-1.5">
                            <div 
                              className="bg-green-600 h-1.5 rounded-full transition-all"
                              style={{ width: `${file.progress}%` }}
                            />
                          </div>
                          <p className="text-xs text-gray-500 mt-1">{file.status}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              
              {/* Right: Documents List */}
              <div className="flex-1 p-6">
                <DocumentsList collectionId={selectedCollection.id} />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Folder className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h2 className="text-xl font-medium text-gray-400 mb-2">No Collection Selected</h2>
              <p className="text-gray-500">Select a collection from the sidebar to view and manage documents</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}