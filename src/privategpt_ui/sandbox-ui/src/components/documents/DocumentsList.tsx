'use client';

import React, { useState, useEffect } from 'react';
import { FileText, Download, Trash2, MoreVertical, FileIcon, Clock, CheckCircle, XCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Document {
  id: number;
  title: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  status: 'pending' | 'processing' | 'complete' | 'failed';
  uploaded_at: string;
  processing_progress?: {
    stage: string;
    percentage: number;
  };
}

interface DocumentsListProps {
  collectionId: string;
}

export function DocumentsList({ collectionId }: DocumentsListProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState<number | null>(null);

  // Mock data for now - will be replaced with API call
  useEffect(() => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setDocuments([
        {
          id: 1,
          title: 'Project Specification.pdf',
          file_name: 'project-spec.pdf',
          file_size: 2457600,
          mime_type: 'application/pdf',
          status: 'complete',
          uploaded_at: new Date().toISOString()
        },
        {
          id: 2,
          title: 'Meeting Notes.docx',
          file_name: 'meeting-notes.docx',
          file_size: 156789,
          mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          status: 'processing',
          uploaded_at: new Date().toISOString(),
          processing_progress: {
            stage: 'embedding',
            percentage: 65
          }
        },
        {
          id: 3,
          title: 'Architecture Diagram.png',
          file_name: 'architecture.png',
          file_size: 890123,
          mime_type: 'image/png',
          status: 'failed',
          uploaded_at: new Date().toISOString()
        }
      ]);
      setIsLoading(false);
    }, 500);
  }, [collectionId]);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'processing':
        return <Clock className="w-4 h-4 text-yellow-500 animate-spin" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const getFileIcon = (mimeType: string) => {
    if (mimeType.includes('pdf')) return '📄';
    if (mimeType.includes('word')) return '📝';
    if (mimeType.includes('excel')) return '📊';
    if (mimeType.includes('image')) return '🖼️';
    return '📎';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-600 border-t-white"></div>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <FileText className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No documents in this collection</p>
          <p className="text-gray-500 text-sm mt-1">Upload documents to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-medium text-white">
          Documents ({documents.length})
        </h3>
        <div className="flex items-center space-x-2">
          <button className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors">
            Name
          </button>
          <button className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors">
            Date
          </button>
          <button className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors">
            Size
          </button>
        </div>
      </div>

      {/* Documents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 overflow-y-auto">
        {documents.map((doc) => (
          <motion.div
            key={doc.id}
            layout
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`bg-gray-800 rounded-lg p-4 cursor-pointer transition-all hover:bg-gray-750 ${
              selectedDoc === doc.id ? 'ring-2 ring-gray-600' : ''
            }`}
            onClick={() => setSelectedDoc(doc.id)}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center">
                <span className="text-2xl mr-3">{getFileIcon(doc.mime_type)}</span>
                <div className="flex-1">
                  <h4 className="text-sm font-medium text-white truncate">{doc.title}</h4>
                  <p className="text-xs text-gray-500">{formatFileSize(doc.file_size)}</p>
                </div>
              </div>
              <button className="p-1 hover:bg-gray-700 rounded transition-colors">
                <MoreVertical className="w-4 h-4 text-gray-400" />
              </button>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {getStatusIcon(doc.status)}
                <span className="text-xs text-gray-400 capitalize">{doc.status}</span>
              </div>
              <span className="text-xs text-gray-500">
                {new Date(doc.uploaded_at).toLocaleDateString()}
              </span>
            </div>

            {doc.processing_progress && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-gray-400">{doc.processing_progress.stage}</span>
                  <span className="text-gray-400">{doc.processing_progress.percentage}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-1">
                  <div 
                    className="bg-yellow-600 h-1 rounded-full transition-all"
                    style={{ width: `${doc.processing_progress.percentage}%` }}
                  />
                </div>
              </div>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}