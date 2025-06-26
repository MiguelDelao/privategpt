'use client';

import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Folder, FolderOpen, Plus, MoreVertical, Trash2, Edit2, FolderPlus } from 'lucide-react';
import { useDocumentStore } from '@/stores/documentStore';
import type { Collection } from '@/stores/documentStore';
import { motion, AnimatePresence } from 'framer-motion';
import { useDrag } from 'react-dnd';

interface CollectionTreeItemProps {
  collection: Collection;
  level: number;
  onSelect: (collection: Collection) => void;
  selectedId?: string | null;
  onCreateSubfolder: (parentId: string) => void;
  onRename: (collection: Collection) => void;
  onDelete: (collection: Collection) => void;
}

function CollectionTreeItem({ 
  collection, 
  level, 
  onSelect, 
  selectedId,
  onCreateSubfolder,
  onRename,
  onDelete
}: CollectionTreeItemProps) {
  const { toggleCollectionExpanded, expandedCollections } = useDocumentStore();
  const [showMenu, setShowMenu] = useState(false);
  const isExpanded = expandedCollections.has(collection.id);
  const hasChildren = collection.children && collection.children.length > 0;
  const isSelected = selectedId === collection.id;

  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'collection',
    item: { id: collection.id, name: collection.name, path: collection.path },
    collect: (monitor) => ({
      isDragging: !!monitor.isDragging(),
    }),
  }));

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (hasChildren) {
      toggleCollectionExpanded(collection.id);
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setShowMenu(true);
  };

  const handleMenuAction = (action: string) => {
    setShowMenu(false);
    switch (action) {
      case 'create':
        onCreateSubfolder(collection.id);
        break;
      case 'rename':
        onRename(collection);
        break;
      case 'delete':
        onDelete(collection);
        break;
    }
  };

  return (
    <>
      <motion.div
        ref={drag}
        initial={{ opacity: 0 }}
        animate={{ opacity: isDragging ? 0.5 : 1 }}
        className={`
          relative group cursor-pointer select-none
          ${isSelected ? 'bg-gray-700/50' : 'hover:bg-gray-800/50'}
          transition-colors rounded
        `}
        onClick={() => onSelect(collection)}
        onContextMenu={handleContextMenu}
        style={{ paddingLeft: `${level * 1.5 + 0.5}rem` }}
      >
        <div className="flex items-center py-1.5 px-2">
          <button
            onClick={handleToggle}
            className="p-0.5 hover:bg-gray-700 rounded transition-colors mr-1"
          >
            {hasChildren ? (
              isExpanded ? (
                <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
              )
            ) : (
              <div className="w-3.5 h-3.5" />
            )}
          </button>

          <span className="mr-2 text-lg">
            {collection.icon || (isExpanded ? '📂' : '📁')}
          </span>

          <span className={`flex-1 text-sm truncate ${level === 0 ? 'text-white font-medium' : 'text-gray-300'}`}>
            {collection.name}
          </span>

          {collection.total_document_count > 0 && (
            <span className="text-xs text-gray-500 mr-2">
              {collection.total_document_count}
            </span>
          )}

          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-gray-700 rounded transition-all"
          >
            <MoreVertical className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        <AnimatePresence>
          {showMenu && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="absolute right-2 top-8 z-50 bg-gray-800 border border-gray-700 rounded-lg shadow-lg py-1 min-w-[160px]"
              onMouseLeave={() => setShowMenu(false)}
            >
              <button
                onClick={() => handleMenuAction('create')}
                className="w-full px-3 py-2 text-sm text-left text-white hover:bg-gray-700 flex items-center space-x-2"
              >
                <FolderPlus className="w-4 h-4" />
                <span>New Subfolder</span>
              </button>
              <button
                onClick={() => handleMenuAction('rename')}
                className="w-full px-3 py-2 text-sm text-left text-white hover:bg-gray-700 flex items-center space-x-2"
              >
                <Edit2 className="w-4 h-4" />
                <span>Rename</span>
              </button>
              <div className="border-t border-gray-700 my-1" />
              <button
                onClick={() => handleMenuAction('delete')}
                className="w-full px-3 py-2 text-sm text-left text-red-400 hover:bg-gray-700 flex items-center space-x-2"
              >
                <Trash2 className="w-4 h-4" />
                <span>Delete</span>
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      <AnimatePresence>
        {isExpanded && hasChildren && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            {collection.children!.map((child) => (
              <CollectionTreeItem
                key={child.id}
                collection={child}
                level={level + 1}
                onSelect={onSelect}
                selectedId={selectedId}
                onCreateSubfolder={onCreateSubfolder}
                onRename={onRename}
                onDelete={onDelete}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

interface CollectionTreeProps {
  onSelectCollection: (collection: Collection) => void;
  selectedCollectionId?: string | null;
  onCreateCollection: () => void;
  onCreateSubfolder: (parentId: string) => void;
  onRename: (collection: Collection) => void;
  onDelete: (collection: Collection) => void;
}

export function CollectionTree({ 
  onSelectCollection, 
  selectedCollectionId,
  onCreateCollection,
  onCreateSubfolder,
  onRename,
  onDelete
}: CollectionTreeProps) {
  const { collections, isLoading, error } = useDocumentStore();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-500 border-t-white"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-sm text-red-400">
        Error loading collections: {error}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b border-gray-700">
        <button
          onClick={onCreateCollection}
          className="w-full px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors flex items-center justify-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>New Collection</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {collections.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-sm">
            <Folder className="w-12 h-12 mx-auto mb-3 text-gray-600" />
            <p>No collections yet</p>
            <p className="text-xs mt-1">Create your first collection to get started</p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {collections.map((collection) => (
              <CollectionTreeItem
                key={collection.id}
                collection={collection}
                level={0}
                onSelect={onSelectCollection}
                selectedId={selectedCollectionId}
                onCreateSubfolder={onCreateSubfolder}
                onRename={onRename}
                onDelete={onDelete}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}