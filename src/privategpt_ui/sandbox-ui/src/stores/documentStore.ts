import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { config } from '@/lib/config';

// Types
export interface Collection {
  id: string;
  name: string;
  description?: string;
  parent_id?: string;
  collection_type: 'collection' | 'folder';
  icon: string;
  color: string;
  path: string;
  depth: number;
  document_count: number;
  total_document_count: number;
  created_at: string;
  updated_at: string;
  children?: Collection[];
  isExpanded?: boolean;
}

export interface Document {
  id: number;
  collection_id?: string;
  title: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  status: 'pending' | 'processing' | 'complete' | 'failed';
  error?: string;
  task_id?: string;
  processing_progress?: ProcessingProgress;
  uploaded_at: string;
}

export interface ProcessingProgress {
  stage: 'pending' | 'splitting' | 'embedding' | 'storing' | 'finalizing' | 'complete';
  percentage: number;
  message?: string;
}

export interface UploadingFile {
  id: string;
  file: File;
  collection_id: string;
  progress: number;
  status: 'uploading' | 'processing' | 'complete' | 'failed';
  error?: string;
  document_id?: number;
  task_id?: string;
}

interface DocumentStore {
  // State
  collections: Collection[];
  documents: Document[];
  uploadingFiles: UploadingFile[];
  selectedCollectionId: string | null;
  expandedCollections: Set<string>;
  isLoading: boolean;
  error: string | null;

  // Collection actions
  fetchCollections: () => Promise<void>;
  createCollection: (collection: Partial<Collection>) => Promise<Collection>;
  updateCollection: (id: string, updates: Partial<Collection>) => Promise<void>;
  deleteCollection: (id: string, hardDelete?: boolean) => Promise<void>;
  toggleCollectionExpanded: (id: string) => void;
  selectCollection: (id: string | null) => void;

  // Document actions
  uploadDocument: (file: File, collectionId: string) => Promise<void>;
  fetchDocumentStatus: (documentId: number) => Promise<void>;
  trackUploadProgress: (taskId: string) => Promise<void>;
  removeUploadingFile: (id: string) => void;

  // Utility actions
  getCollectionById: (id: string) => Collection | undefined;
  getCollectionPath: (id: string) => string[];
  refreshCollectionCounts: () => Promise<void>;
  clearError: () => void;
}

export const useDocumentStore = create<DocumentStore>()(
  persist(
    (set, get) => ({
      // Initial state
      collections: [],
      documents: [],
      uploadingFiles: [],
      selectedCollectionId: null,
      expandedCollections: new Set<string>(),
      isLoading: false,
      error: null,

      // Collection actions
      fetchCollections: async () => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetch(`${config.apiUrl}/api/rag/collections`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            },
          });

          if (!response.ok) throw new Error('Failed to fetch collections');
          
          const data = await response.json();
          // API returns array directly, not wrapped in object
          const collections = buildCollectionTree(Array.isArray(data) ? data : []);
          set({ collections, isLoading: false });
        } catch (error) {
          set({ error: error.message, isLoading: false });
        }
      },

      createCollection: async (collection) => {
        set({ error: null });
        try {
          const response = await fetch(`${config.apiUrl}/api/rag/collections`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            },
            body: JSON.stringify({
              name: collection.name,
              description: collection.description,
              parent_id: collection.parent_id,
              collection_type: collection.collection_type || 'collection',
              icon: collection.icon || '📁',
              color: collection.color || '#3B82F6',
            }),
          });

          if (!response.ok) throw new Error('Failed to create collection');
          
          const newCollection = await response.json();
          await get().fetchCollections(); // Refresh the tree
          return newCollection;
        } catch (error) {
          set({ error: error.message });
          throw error;
        }
      },

      updateCollection: async (id, updates) => {
        set({ error: null });
        try {
          const response = await fetch(`${config.apiUrl}/api/rag/collections/${id}`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            },
            body: JSON.stringify(updates),
          });

          if (!response.ok) throw new Error('Failed to update collection');
          
          await get().fetchCollections(); // Refresh the tree
        } catch (error) {
          set({ error: error.message });
          throw error;
        }
      },

      deleteCollection: async (id, hardDelete = false) => {
        set({ error: null });
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          const response = await fetch(`${apiUrl}/api/rag/collections/${id}?hard_delete=${hardDelete}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            },
          });

          if (!response.ok) throw new Error('Failed to delete collection');
          
          await get().fetchCollections(); // Refresh the tree
        } catch (error) {
          set({ error: error.message });
          throw error;
        }
      },

      toggleCollectionExpanded: (id) => {
        set((state) => {
          const expanded = new Set(state.expandedCollections);
          if (expanded.has(id)) {
            expanded.delete(id);
          } else {
            expanded.add(id);
          }
          return { expandedCollections: expanded };
        });
      },

      selectCollection: (id) => {
        set({ selectedCollectionId: id });
      },

      // Document actions
      uploadDocument: async (file, collectionId) => {
        const uploadId = `${Date.now()}-${file.name}`;
        const uploadingFile: UploadingFile = {
          id: uploadId,
          file,
          collection_id: collectionId,
          progress: 0,
          status: 'uploading',
        };

        set((state) => ({
          uploadingFiles: [...state.uploadingFiles, uploadingFile],
        }));

        try {
          const formData = new FormData();
          formData.append('file', file);

          const response = await fetch(`${config.apiUrl}/api/rag/collections/${collectionId}/documents`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            },
            body: formData,
          });

          if (!response.ok) throw new Error('Failed to upload document');

          const result = await response.json();
          
          // Update the uploading file with document info
          set((state) => ({
            uploadingFiles: state.uploadingFiles.map((f) =>
              f.id === uploadId
                ? { ...f, status: 'processing', document_id: result.document_id, task_id: result.task_id, progress: 5 }
                : f
            ),
          }));

          // Start tracking progress
          if (result.task_id) {
            await get().trackUploadProgress(result.task_id);
          }

          // Refresh collections to update counts
          await get().fetchCollections();
        } catch (error) {
          set((state) => ({
            uploadingFiles: state.uploadingFiles.map((f) =>
              f.id === uploadId
                ? { ...f, status: 'failed', error: error.message }
                : f
            ),
          }));
        }
      },

      fetchDocumentStatus: async (documentId) => {
        try {
          const response = await fetch(`${config.apiUrl}/api/rag/documents/${documentId}/status`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            },
          });

          if (!response.ok) throw new Error('Failed to fetch document status');

          const document = await response.json();
          set((state) => ({
            documents: state.documents.map((d) =>
              d.id === documentId ? document : d
            ),
          }));
        } catch (error) {
          console.error('Failed to fetch document status:', error);
        }
      },

      trackUploadProgress: async (taskId) => {
        const checkProgress = async () => {
          try {
            const response = await fetch(`${config.apiUrl}/api/rag/progress/${taskId}`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
              },
            });

            if (!response.ok) {
              console.error('Failed to fetch progress');
              return;
            }

            const progress = await response.json();
            const uploadingFile = get().uploadingFiles.find(f => f.task_id === taskId);
            
            if (!uploadingFile) return;

            // Update progress based on stage
            let percentage = 0;
            switch (progress.stage) {
              case 'pending': percentage = 5; break;
              case 'splitting': percentage = 15; break;
              case 'embedding': percentage = 50; break;
              case 'storing': percentage = 80; break;
              case 'finalizing': percentage = 95; break;
              case 'complete': percentage = 100; break;
              default: percentage = progress.percentage || 0;
            }

            set((state) => ({
              uploadingFiles: state.uploadingFiles.map((f) =>
                f.task_id === taskId
                  ? { 
                      ...f, 
                      progress: percentage, 
                      status: progress.stage === 'complete' ? 'complete' : 
                              progress.stage === 'failed' ? 'failed' : 'processing',
                      error: progress.error
                    }
                  : f
              ),
            }));

            // Continue polling if not complete
            if (progress.stage !== 'complete' && progress.stage !== 'failed') {
              setTimeout(() => checkProgress(), 1000); // Poll every second
            } else {
              // Refresh collections to update counts
              await get().fetchCollections();
            }
          } catch (error) {
            console.error('Error tracking progress:', error);
          }
        };

        checkProgress();
      },

      removeUploadingFile: (id) => {
        set((state) => ({
          uploadingFiles: state.uploadingFiles.filter((f) => f.id !== id),
        }));
      },

      // Utility actions
      getCollectionById: (id) => {
        const findCollection = (collections: Collection[]): Collection | undefined => {
          for (const col of collections) {
            if (col.id === id) return col;
            if (col.children) {
              const found = findCollection(col.children);
              if (found) return found;
            }
          }
          return undefined;
        };
        return findCollection(get().collections);
      },

      getCollectionPath: (id) => {
        const path: string[] = [];
        const collection = get().getCollectionById(id);
        if (!collection) return path;

        let current = collection;
        path.unshift(current.name);

        while (current.parent_id) {
          const parent = get().getCollectionById(current.parent_id);
          if (!parent) break;
          path.unshift(parent.name);
          current = parent;
        }

        return path;
      },

      refreshCollectionCounts: async () => {
        await get().fetchCollections();
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'document-store',
      partialize: (state) => ({
        selectedCollectionId: state.selectedCollectionId,
        expandedCollections: Array.from(state.expandedCollections),
      }),
      // Custom storage to handle Set serialization
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name);
          if (!str) return null;
          const data = JSON.parse(str);
          return {
            state: {
              ...data.state,
              expandedCollections: new Set(data.state.expandedCollections || [])
            },
            version: data.version
          };
        },
        setItem: (name, value) => {
          localStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: (name) => {
          localStorage.removeItem(name);
        }
      }
    }
  )
);

// Helper function to build collection tree
function buildCollectionTree(collections: Collection[]): Collection[] {
  const map = new Map<string, Collection>();
  const roots: Collection[] = [];

  // First pass: create map
  collections.forEach(col => {
    map.set(col.id, { ...col, children: [] });
  });

  // Second pass: build tree
  collections.forEach(col => {
    const node = map.get(col.id)!;
    if (col.parent_id) {
      const parent = map.get(col.parent_id);
      if (parent) {
        parent.children = parent.children || [];
        parent.children.push(node);
      } else {
        roots.push(node);
      }
    } else {
      roots.push(node);
    }
  });

  // Sort children by name
  const sortTree = (nodes: Collection[]) => {
    nodes.sort((a, b) => a.name.localeCompare(b.name));
    nodes.forEach(node => {
      if (node.children) sortTree(node.children);
    });
  };

  sortTree(roots);
  return roots;
}