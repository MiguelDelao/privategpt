'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileText, AlertCircle } from 'lucide-react';
import { useDocumentStore } from '@/stores/documentStore';
import { motion, AnimatePresence } from 'framer-motion';

interface DocumentUploaderProps {
  collectionId: string;
  onClose?: () => void;
  embedded?: boolean;
}

export function DocumentUploader({ collectionId, onClose, embedded = false }: DocumentUploaderProps) {
  const { uploadDocument, getCollectionById } = useDocumentStore();
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const collection = getCollectionById(collectionId);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploadErrors([]);
    const errors: string[] = [];

    for (const file of acceptedFiles) {
      try {
        // Check file size (max 50MB)
        if (file.size > 50 * 1024 * 1024) {
          errors.push(`${file.name}: File size exceeds 50MB limit`);
          continue;
        }

        // Check file type
        const allowedTypes = [
          'application/pdf',
          'text/plain',
          'text/markdown',
          'application/msword',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'application/vnd.ms-excel',
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ];

        if (!allowedTypes.includes(file.type) && !file.name.endsWith('.md')) {
          errors.push(`${file.name}: Unsupported file type`);
          continue;
        }

        await uploadDocument(file, collectionId);
      } catch (error) {
        errors.push(`${file.name}: ${error.message}`);
      }
    }

    if (errors.length > 0) {
      setUploadErrors(errors);
    }
  }, [collectionId, uploadDocument]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    multiple: true,
  });

  return (
    <div className={embedded ? "w-full" : "w-full max-w-2xl mx-auto p-4"}>
      {!embedded && (
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Upload Documents</h3>
            <p className="text-sm text-gray-400 mt-1">
              Upload to: {collection?.icon} {collection?.name}
            </p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-700 rounded transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          )}
        </div>
      )}

      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg ${embedded ? 'p-6' : 'p-8'} transition-all cursor-pointer
          ${isDragActive 
            ? 'border-gray-500 bg-gray-700/50' 
            : 'border-gray-600 hover:border-gray-500 hover:bg-gray-800/50'
          }
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center space-y-4">
          <motion.div
            animate={{ scale: isDragActive ? 1.1 : 1 }}
            transition={{ duration: 0.2 }}
          >
            <Upload className={`w-12 h-12 ${isDragActive ? 'text-gray-300' : 'text-gray-400'}`} />
          </motion.div>
          
          <div className="text-center">
            <p className="text-white font-medium">
              {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
            </p>
            <p className="text-sm text-gray-400 mt-1">
              or click to browse
            </p>
          </div>

          <div className="text-xs text-gray-500 text-center">
            <p>Supported formats: PDF, TXT, MD, DOC, DOCX, XLS, XLSX</p>
            <p>Maximum file size: 50MB</p>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {uploadErrors.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg"
          >
            <div className="flex items-start space-x-2">
              <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-500 mb-1">Upload Errors</p>
                <ul className="text-xs text-red-400 space-y-0.5">
                  {uploadErrors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}