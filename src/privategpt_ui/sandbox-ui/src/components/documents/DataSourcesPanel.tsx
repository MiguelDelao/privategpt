'use client';

import React, { useState, useEffect } from 'react';
import { Search, Upload } from 'lucide-react';
import { Collection, useDocumentStore } from '@/stores/documentStore';
import { CollectionTree } from './CollectionTree';
import { CollectionModal } from './CollectionModal';
import { DocumentUploader } from './DocumentUploader';
import { motion, AnimatePresence } from 'framer-motion';

export function DataSourcesPanel() {
  const { 
    fetchCollections, 
    selectedCollectionId, 
    selectCollection,
    deleteCollection 
  } = useDocumentStore();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [showCollectionModal, setShowCollectionModal] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [editingCollection, setEditingCollection] = useState<Collection | null>(null);
  const [parentIdForNew, setParentIdForNew] = useState<string | null>(null);
  const [showUploader, setShowUploader] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<Collection | null>(null);

  useEffect(() => {
    fetchCollections();
    // Refresh collections every 30 seconds to catch updates
    const interval = setInterval(fetchCollections, 30000);
    return () => clearInterval(interval);
  }, [fetchCollections]);

  const handleCreateCollection = () => {
    setModalMode('create');
    setEditingCollection(null);
    setParentIdForNew(null);
    setShowCollectionModal(true);
  };

  const handleCreateSubfolder = (parentId: string) => {
    setModalMode('create');
    setEditingCollection(null);
    setParentIdForNew(parentId);
    setShowCollectionModal(true);
  };

  const handleRenameCollection = (collection: Collection) => {
    setModalMode('edit');
    setEditingCollection(collection);
    setParentIdForNew(null);
    setShowCollectionModal(true);
  };

  const handleDeleteCollection = async (collection: Collection) => {
    setShowDeleteConfirm(collection);
  };

  const confirmDelete = async (hardDelete: boolean) => {
    if (showDeleteConfirm) {
      try {
        await deleteCollection(showDeleteConfirm.id, hardDelete);
        if (selectedCollectionId === showDeleteConfirm.id) {
          selectCollection(null);
        }
      } catch (error) {
        console.error('Failed to delete collection:', error);
      }
      setShowDeleteConfirm(null);
    }
  };

  const handleSelectCollection = (collection: Collection) => {
    selectCollection(collection.id);
  };

  const handleUploadClick = () => {
    if (selectedCollectionId) {
      setShowUploader(true);
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Search Bar */}
      <div className="p-3 border-b border-gray-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search collections..."
            className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-gray-600 focus:outline-none transition-colors"
          />
        </div>
      </div>

      {/* Collection Tree */}
      <div className="flex-1 overflow-hidden">
        <CollectionTree
          onSelectCollection={handleSelectCollection}
          selectedCollectionId={selectedCollectionId}
          onCreateCollection={handleCreateCollection}
          onCreateSubfolder={handleCreateSubfolder}
          onRename={handleRenameCollection}
          onDelete={handleDeleteCollection}
        />
      </div>


      {/* Collection Modal */}
      <CollectionModal
        isOpen={showCollectionModal}
        onClose={() => setShowCollectionModal(false)}
        collection={editingCollection}
        parentId={parentIdForNew}
        mode={modalMode}
      />

      {/* Upload Modal */}
      <AnimatePresence>
        {showUploader && selectedCollectionId && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowUploader(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <DocumentUploader
                collectionId={selectedCollectionId}
                onClose={() => setShowUploader(false)}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {showDeleteConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowDeleteConfirm(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-gray-800 rounded-lg p-6 max-w-md w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-white mb-2">
                Delete {showDeleteConfirm.collection_type === 'folder' ? 'Folder' : 'Collection'}
              </h3>
              <p className="text-gray-300 mb-4">
                Are you sure you want to delete "{showDeleteConfirm.icon} {showDeleteConfirm.name}"?
              </p>
              {showDeleteConfirm.total_document_count > 0 && (
                <p className="text-yellow-400 text-sm mb-4">
                  This collection contains {showDeleteConfirm.total_document_count} document(s).
                </p>
              )}
              <div className="space-y-2">
                <button
                  onClick={() => confirmDelete(false)}
                  className="w-full px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors"
                >
                  Soft Delete (can be restored)
                </button>
                <button
                  onClick={() => confirmDelete(true)}
                  className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                >
                  Hard Delete (permanent)
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(null)}
                  className="w-full px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}