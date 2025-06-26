'use client';

import React from 'react';
import { X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useDocumentStore } from '@/stores/documentStore';
import { motion, AnimatePresence } from 'framer-motion';

export function UploadProgress() {
  const { uploadingFiles, removeUploadingFile } = useDocumentStore();

  if (uploadingFiles.length === 0) return null;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />;
    }
  };

  const getStatusText = (file: any) => {
    if (file.status === 'uploading') return 'Uploading...';
    if (file.status === 'processing') {
      if (file.progress <= 20) return 'Splitting text...';
      if (file.progress <= 70) return 'Generating embeddings...';
      if (file.progress <= 85) return 'Storing vectors...';
      if (file.progress <= 95) return 'Finalizing...';
      return 'Processing...';
    }
    if (file.status === 'complete') return 'Complete';
    if (file.status === 'failed') return file.error || 'Failed';
    return 'Unknown';
  };

  return (
    <div className="fixed bottom-4 right-4 max-w-md w-full z-50">
      <div className="bg-gray-800 border border-gray-700 rounded-lg shadow-lg overflow-hidden">
        <div className="p-3 border-b border-gray-700">
          <h4 className="text-sm font-medium text-white">Upload Progress</h4>
        </div>
        
        <div className="max-h-64 overflow-y-auto">
          <AnimatePresence>
            {uploadingFiles.map((file) => (
              <motion.div
                key={file.id}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="p-3 border-b border-gray-700 last:border-b-0"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-start space-x-2 flex-1 min-w-0">
                    {getStatusIcon(file.status)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{file.file.name}</p>
                      <p className="text-xs text-gray-400">{getStatusText(file)}</p>
                    </div>
                  </div>
                  {(file.status === 'complete' || file.status === 'failed') && (
                    <button
                      onClick={() => removeUploadingFile(file.id)}
                      className="ml-2 p-1 hover:bg-gray-700 rounded transition-colors"
                    >
                      <X className="w-4 h-4 text-gray-400" />
                    </button>
                  )}
                </div>
                
                {file.status !== 'complete' && file.status !== 'failed' && (
                  <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-gray-500 to-gray-600"
                      initial={{ width: '0%' }}
                      animate={{ width: `${file.progress}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                )}
                
                {file.progress > 0 && file.status !== 'failed' && (
                  <p className="text-xs text-gray-500 mt-1 text-right">{file.progress}%</p>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}