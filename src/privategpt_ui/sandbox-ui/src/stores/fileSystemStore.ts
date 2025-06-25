import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'

export interface FileSystemItem {
  id: string
  name: string
  type: 'file' | 'folder'
  parentId?: string
  children?: string[]
  content?: string
  created: Date
  modified: Date
  size?: number
  isExpanded?: boolean
}

interface FileSystemStore {
  items: Record<string, FileSystemItem>
  
  // Folder operations
  createFolder: (name: string, parentId?: string) => void
  deleteItem: (id: string) => void
  renameItem: (id: string, newName: string) => void
  moveItem: (id: string, newParentId?: string) => void
  
  // File operations
  createFile: (name: string, content: string, parentId?: string) => void
  updateFileContent: (id: string, content: string) => void
  
  // Tree operations
  toggleFolder: (id: string) => void
  getChildren: (parentId?: string) => FileSystemItem[]
  getRootItems: () => FileSystemItem[]
  
  // Search
  searchItems: (query: string) => FileSystemItem[]
}

export const useFileSystemStore = create<FileSystemStore>()((set, get) => ({
  // Start with empty file system
  items: {},
  
  createFolder: (name, parentId) => {
    const id = uuidv4()
    const now = new Date()
    
    const newFolder: FileSystemItem = {
      id,
      name,
      type: 'folder',
      parentId,
      children: [],
      created: now,
      modified: now,
      isExpanded: false
    }
    
    set(state => {
      const newItems = { ...state.items, [id]: newFolder }
      
      if (parentId) {
        const parent = newItems[parentId]
        if (parent && parent.children) {
          parent.children.push(id)
          parent.modified = now
        }
      }
      
      return { items: newItems }
    })
  },
  
  createFile: (name, content = '', parentId) => {
    const id = uuidv4()
    const now = new Date()
    
    const newFile: FileSystemItem = {
      id,
      name,
      type: 'file',
      parentId,
      content,
      created: now,
      modified: now,
      size: content.length
    }
    
    set(state => {
      const newItems = { ...state.items, [id]: newFile }
      
      if (parentId) {
        const parent = newItems[parentId]
        if (parent && parent.children) {
          parent.children.push(id)
          parent.modified = now
        }
      }
      
      return { items: newItems }
    })
  },
  
  deleteItem: (id) => {
    set(state => {
      const newItems = { ...state.items }
      const item = newItems[id]
      
      if (!item) return state
      
      // Remove from parent's children
      if (item.parentId) {
        const parent = newItems[item.parentId]
        if (parent && parent.children) {
          parent.children = parent.children.filter(childId => childId !== id)
          parent.modified = new Date()
        }
      }
      
      // Recursively delete children
      const deleteRecursive = (itemId: string) => {
        const currentItem = newItems[itemId]
        if (currentItem && currentItem.children) {
          currentItem.children.forEach(deleteRecursive)
        }
        delete newItems[itemId]
      }
      
      deleteRecursive(id)
      
      return { items: newItems }
    })
  },
  
  renameItem: (id, newName) => {
    set(state => ({
      items: {
        ...state.items,
        [id]: {
          ...state.items[id],
          name: newName,
          modified: new Date()
        }
      }
    }))
  },
  
  moveItem: (id, newParentId) => {
    set(state => {
      const newItems = { ...state.items }
      const item = newItems[id]
      
      if (!item) return state
      
      // Remove from old parent
      if (item.parentId) {
        const oldParent = newItems[item.parentId]
        if (oldParent && oldParent.children) {
          oldParent.children = oldParent.children.filter(childId => childId !== id)
          oldParent.modified = new Date()
        }
      }
      
      // Add to new parent
      if (newParentId) {
        const newParent = newItems[newParentId]
        if (newParent && newParent.children) {
          newParent.children.push(id)
          newParent.modified = new Date()
        }
      }
      
      // Update item
      newItems[id] = {
        ...item,
        parentId: newParentId,
        modified: new Date()
      }
      
      return { items: newItems }
    })
  },
  
  updateFileContent: (id, content) => {
    set(state => ({
      items: {
        ...state.items,
        [id]: {
          ...state.items[id],
          content,
          size: content.length,
          modified: new Date()
        }
      }
    }))
  },
  
  toggleFolder: (id) => {
    set(state => ({
      items: {
        ...state.items,
        [id]: {
          ...state.items[id],
          isExpanded: !state.items[id].isExpanded
        }
      }
    }))
  },
  
  getChildren: (parentId) => {
    const items = get().items
    return Object.values(items)
      .filter(item => item.parentId === parentId)
      .sort((a, b) => {
        // Folders first, then files
        if (a.type !== b.type) {
          return a.type === 'folder' ? -1 : 1
        }
        return a.name.localeCompare(b.name)
      })
  },
  
  getRootItems: () => {
    return get().getChildren(undefined)
  },
  
  searchItems: (query) => {
    const items = get().items
    const lowerQuery = query.toLowerCase()
    
    return Object.values(items).filter(item =>
      item.name.toLowerCase().includes(lowerQuery) ||
      (item.content && item.content.toLowerCase().includes(lowerQuery))
    )
  }
}))