# Document Organization - Folder Structure Implementation

## 🎯 Chosen Naming Convention

After considering various options, here's the recommended approach:

### **Collections & Folders**
- **Collection**: Top-level organizational unit (like "Cases" or "Regulations")
- **Folder**: Sub-folders within collections (like "Smith v. Jones" or "Europe")
- **Document**: Individual files within folders

This is essentially a traditional folder/directory structure with a slightly more elegant name at the top level.

## 📐 Technical Implementation

### 1. Self-Referential Hierarchy
```python
@dataclass
class Collection:
    id: UUID
    user_id: int
    name: str
    parent_id: Optional[UUID]  # None for root collections
    collection_type: Literal["collection", "folder"]
    icon: str = "📁"
    color: str = "#3B82F6"
    path: str  # Cached path like "/Cases/Smith v Jones"
    depth: int  # 0 for root, increments down
    
    # Computed properties
    is_root: bool = field(init=False)
    
    def __post_init__(self):
        self.is_root = self.parent_id is None
```

### 2. Path Management
```python
class CollectionService:
    async def create_collection(
        self, 
        name: str, 
        parent_id: Optional[UUID] = None,
        user_id: int
    ) -> Collection:
        # Build the full path
        if parent_id:
            parent = await self.get_collection(parent_id)
            full_path = f"{parent.path}/{name}"
            depth = parent.depth + 1
            collection_type = "folder"
        else:
            full_path = f"/{name}"
            depth = 0
            collection_type = "collection"
        
        # Create the collection
        collection = Collection(
            name=name,
            parent_id=parent_id,
            path=full_path,
            depth=depth,
            collection_type=collection_type,
            user_id=user_id
        )
        
        return await self.repository.create(collection)
    
    async def get_breadcrumb(self, collection_id: UUID) -> List[Collection]:
        """Get the full path as a list of collections"""
        collection = await self.get_collection(collection_id)
        breadcrumb = [collection]
        
        while collection.parent_id:
            collection = await self.get_collection(collection.parent_id)
            breadcrumb.insert(0, collection)
        
        return breadcrumb
```

### 3. Efficient Queries
```sql
-- Get all descendants of a collection
WITH RECURSIVE collection_tree AS (
    SELECT * FROM collections WHERE id = :collection_id
    UNION ALL
    SELECT c.* FROM collections c
    INNER JOIN collection_tree ct ON c.parent_id = ct.id
)
SELECT * FROM collection_tree;

-- Get full path using path_array
SELECT * FROM collections 
WHERE :collection_id = ANY(path_array)
ORDER BY depth;
```

## 🎨 UI Components

### 1. Collection Browser
```typescript
interface CollectionBrowser {
  // Current location
  currentCollection: Collection | null;
  breadcrumb: Collection[];
  
  // Contents
  subFolders: Collection[];
  documents: Document[];
  
  // Actions
  onNavigate: (collection: Collection) => void;
  onCreateFolder: (name: string) => void;
  onUploadDocument: (files: File[]) => void;
}
```

### 2. Collection Picker (for @ mentions)
```typescript
interface CollectionPicker {
  collections: Collection[];
  selectedPaths: string[];
  
  onSelect: (path: string) => void;
  onRemove: (path: string) => void;
  
  // Display selected as badges
  renderBadges: () => JSX.Element[];
}
```

### 3. Path Display Component
```typescript
const PathDisplay: React.FC<{ path: string }> = ({ path }) => {
  const segments = path.split('/').filter(Boolean);
  
  return (
    <div className="flex items-center space-x-2">
      {segments.map((segment, index) => (
        <React.Fragment key={index}>
          {index > 0 && <ChevronRight className="w-4 h-4" />}
          <span className="text-sm">{segment}</span>
        </React.Fragment>
      ))}
    </div>
  );
};
```

## 💬 @ Mention Syntax

### Basic Syntax
- `@Cases` - Search in the entire Cases collection
- `@Cases/Smith` - Search in Smith v. Jones folder
- `@Regulations/Europe/GDPR` - Search in specific nested folder

### Advanced Syntax (Future)
- `@Cases/*` - Search in all subfolders of Cases
- `@*/GDPR` - Search for GDPR in any folder
- `@recent:7d` - Search documents added in last 7 days
- `@type:pdf` - Search only PDF documents

### Context Display in Chat
```
User: @Cases/Smith What was the initial complaint about?
      ╰─ 📁 Cases > Smith v. Jones

AI: Based on the documents in the Smith v. Jones case folder, 
    the initial complaint filed on January 15, 2024 alleges...
```

## 🚀 Migration from "Workspaces"

Since you already started with "workspaces", here's a simple migration path:

1. **Keep the same database structure** - Just rename in UI
2. **Update API endpoints** gradually:
   - Keep `/workspaces` working but deprecated
   - Add new `/collections` endpoints
   - Frontend can switch immediately

3. **Database migration** (optional):
   ```sql
   -- Just rename the table if you want
   ALTER TABLE workspaces RENAME TO collections;
   
   -- Or keep it as-is and map in code
   -- The table name doesn't matter to users
   ```

## 📊 Example Structure

Here's how a law firm might organize their documents:

```
My Collections
├── 📚 Client Matters
│   ├── 📁 Active Cases
│   │   ├── 📂 Smith v. Jones (2024-001)
│   │   │   ├── 📂 Pleadings
│   │   │   │   ├── 📄 Initial_Complaint.pdf
│   │   │   │   └── 📄 Answer_to_Complaint.pdf
│   │   │   ├── 📂 Discovery
│   │   │   │   ├── 📄 Interrogatories_Set1.pdf
│   │   │   │   └── 📄 Document_Requests.pdf
│   │   │   └── 📂 Correspondence
│   │   │       └── 📄 Letter_to_OpposingCounsel.pdf
│   │   └── 📂 Johnson LLC Formation
│   │       ├── 📄 Articles_of_Incorporation.pdf
│   │       └── 📄 Operating_Agreement.pdf
│   └── 📁 Archived Cases
│       └── 📂 Davis v. State (2023-015)
├── 📚 Legal Research  
│   ├── 📁 Case Law
│   │   ├── 📂 Supreme Court
│   │   └── 📂 Circuit Courts
│   └── 📁 Statutes & Regulations
│       ├── 📂 Federal
│       └── 📂 State
└── 📚 Templates & Forms
    ├── 📁 Litigation
    └── 📁 Transactional
```

This gives users a familiar, flexible way to organize their documents while maintaining the powerful search and AI capabilities you're building!