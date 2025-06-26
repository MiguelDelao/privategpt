'use client';

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Collection, useDocumentStore } from '@/stores/documentStore';
import { motion, AnimatePresence } from 'framer-motion';

interface CollectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  collection?: Collection | null;
  parentId?: string | null;
  mode: 'create' | 'edit';
}

const COLLECTION_ICONS = ['📁', '📂', '📚', '📖', '📄', '📋', '🗂️', '🗃️', '📦', '💼'];
const COLLECTION_COLORS = [
  '#6B7280', // gray-500
  '#10B981', // emerald
  '#8B5CF6', // violet
  '#F59E0B', // amber
  '#EF4444', // red
  '#EC4899', // pink
  '#14B8A6', // teal
  '#9CA3AF', // gray-400
  '#84CC16', // lime
  '#F97316', // orange
];

export function CollectionModal({ isOpen, onClose, collection, parentId, mode }: CollectionModalProps) {
  const { createCollection, updateCollection, getCollectionById } = useDocumentStore();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [icon, setIcon] = useState('📁');
  const [color, setColor] = useState('#6B7280');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const parentCollection = parentId ? getCollectionById(parentId) : null;

  useEffect(() => {
    if (mode === 'edit' && collection) {
      setName(collection.name);
      setDescription(collection.description || '');
      setIcon(collection.icon || '📁');
      setColor(collection.color || '#6B7280');
    } else {
      setName('');
      setDescription('');
      setIcon('📁');
      setColor('#6B7280');
    }
  }, [mode, collection]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      if (mode === 'create') {
        await createCollection({
          name,
          description,
          icon,
          color,
          parent_id: parentId || undefined,
          collection_type: parentId ? 'folder' : 'collection',
        });
      } else if (collection) {
        await updateCollection(collection.id, {
          name,
          description,
          icon,
          color,
        });
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-gray-800 rounded-lg p-6 max-w-md w-full"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white">
              {mode === 'create' ? 'Create' : 'Edit'} {parentId ? 'Subfolder' : 'Collection'}
            </h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-700 rounded transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>

          {parentCollection && (
            <div className="mb-4 p-2 bg-gray-700/50 rounded">
              <p className="text-sm text-gray-400">Parent folder:</p>
              <p className="text-sm text-white">
                {parentCollection.icon} {parentCollection.path}
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-gray-500 focus:outline-none transition-colors"
                placeholder="Enter collection name"
                required
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Description (optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-gray-500 focus:outline-none transition-colors resize-none"
                placeholder="Enter description"
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Icon
              </label>
              <div className="grid grid-cols-10 gap-2">
                {COLLECTION_ICONS.map((emoji) => (
                  <button
                    key={emoji}
                    type="button"
                    onClick={() => setIcon(emoji)}
                    className={`
                      p-2 rounded text-xl transition-all
                      ${icon === emoji 
                        ? 'bg-gray-600 shadow-lg' 
                        : 'bg-gray-700 hover:bg-gray-600'
                      }
                    `}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Color
              </label>
              <div className="grid grid-cols-10 gap-2">
                {COLLECTION_COLORS.map((hexColor) => (
                  <button
                    key={hexColor}
                    type="button"
                    onClick={() => setColor(hexColor)}
                    className={`
                      w-full h-8 rounded transition-all
                      ${color === hexColor 
                        ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-800' 
                        : 'hover:scale-110'
                      }
                    `}
                    style={{ backgroundColor: hexColor }}
                  />
                ))}
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Saving...' : mode === 'create' ? 'Create' : 'Save'}
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}