# RAG Document Organization - Naming Conventions

## 📁 Hierarchical Structure Options

### Option 1: Collections & Folders (Recommended)
```
Collections (Top Level)
├── Cases
│   ├── Smith v. Jones
│   │   ├── Pleadings
│   │   ├── Discovery
│   │   └── Correspondence
│   └── Johnson v. State
│       ├── Trial Transcripts
│       └── Evidence
└── Regulations
    ├── Europe
    │   ├── GDPR
    │   └── AI Act
    └── United States
        ├── Federal
        └── State
```

**Terminology:**
- **Collection**: Top-level container (Cases, Regulations, Research)
- **Folder**: Sub-containers within collections
- **Document**: Individual files

**Why this works:**
- "Collection" implies a curated set of related content
- "Folder" is universally understood
- Natural hierarchy without inventing new terms

### Option 2: Libraries & Sections
```
Libraries
├── Case Library
│   └── Sections
│       ├── Active Cases
│       ├── Archived Cases
│       └── Precedents
└── Regulatory Library
    └── Sections
        ├── International
        ├── Federal
        └── State
```

**Terminology:**
- **Library**: Major knowledge domain
- **Section**: Organizational unit within library
- **Document**: Individual files

### Option 3: Knowledge Bases & Categories
```
Knowledge Bases
├── Legal Cases
│   └── Categories
│       ├── Criminal
│       ├── Civil
│       └── Corporate
└── Compliance
    └── Categories
        ├── Data Protection
        ├── Financial
        └── Healthcare
```

## 🏗️ Recommended Implementation

### Database Schema
```sql
-- Collections table (top-level)
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(50) DEFAULT '📁',
    color VARCHAR(7) DEFAULT '#3B82F6',
    parent_id UUID REFERENCES collections(id), -- For nested folders
    collection_type VARCHAR(50) DEFAULT 'folder', -- 'collection' or 'folder'
    path_array UUID[], -- Array of parent IDs for fast path queries
    full_path VARCHAR(1024), -- Cached full path like '/Cases/Smith v Jones'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, parent_id, name)
);

-- Documents now belong to collections
ALTER TABLE documents 
ADD COLUMN collection_id UUID REFERENCES collections(id);

-- Index for efficient path queries
CREATE INDEX idx_collections_path ON collections USING GIN(path_array);
CREATE INDEX idx_collections_parent ON collections(parent_id);
```

### API Design
```python
# Collection/Folder endpoints
POST   /api/rag/collections              # Create collection/folder
GET    /api/rag/collections              # List root collections
GET    /api/rag/collections/{id}         # Get collection details
GET    /api/rag/collections/{id}/children # List sub-folders
GET    /api/rag/collections/{id}/path    # Get full path
PATCH  /api/rag/collections/{id}         # Update collection
DELETE /api/rag/collections/{id}         # Delete collection
POST   /api/rag/collections/{id}/move    # Move to different parent

# Document operations
POST   /api/rag/collections/{id}/documents # Upload to specific folder
GET    /api/rag/collections/{id}/documents # List documents in folder
```

### Frontend Display Options

#### Option A: Tree View (File Explorer Style)
```
📚 My Collections
├── 📁 Cases
│   ├── 📂 Smith v. Jones
│   │   ├── 📄 Initial Complaint.pdf
│   │   ├── 📄 Motion to Dismiss.pdf
│   │   └── 📄 Court Order.pdf
│   └── 📂 Johnson v. State
│       └── 📄 Appeal Brief.pdf
└── 📁 Regulations
    ├── 📂 Europe
    │   └── 📄 GDPR Full Text.pdf
    └── 📂 United States
        └── 📄 Section 230.pdf
```

#### Option B: Breadcrumb Navigation
```
Cases > Smith v. Jones > Discovery
[Upload] [New Folder] [Search in Folder]

📄 Deposition_Smith.pdf     2.3 MB    Jan 15, 2024
📄 Interrogatories.pdf      1.1 MB    Jan 10, 2024
📄 Document_Request.pdf     0.8 MB    Jan 08, 2024
```

#### Option C: Column View (macOS Finder Style)
```
Collections     | Cases          | Smith v Jones  | Documents
----------------|----------------|----------------|----------------
📁 Cases        | 📂 Smith v Jones| 📂 Pleadings   | 📄 Complaint.pdf
📁 Regulations  | 📂 Johnson v State| 📂 Discovery | 📄 Motion.pdf
📁 Research     | 📂 Davis v Corp | 📂 Evidence    | 📄 Order.pdf
```

## 💡 Usage Examples

### Legal Practice
```
Collections/
├── Client Matters/
│   ├── Active Cases/
│   │   ├── Smith v. Jones (2024)/
│   │   │   ├── Pleadings/
│   │   │   ├── Discovery/
│   │   │   └── Correspondence/
│   │   └── Johnson LLC Formation/
│   └── Archived Cases/
├── Legal Research/
│   ├── Case Law/
│   ├── Statutes/
│   └── Regulations/
└── Templates/
    ├── Contracts/
    └── Litigation/
```

### Research Organization
```
Collections/
├── Projects/
│   ├── Q4 2024 Study/
│   │   ├── Literature Review/
│   │   ├── Data/
│   │   └── Drafts/
│   └── Grant Proposals/
├── References/
│   ├── Papers/
│   └── Books/
└── Lab Notes/
    ├── Experiments/
    └── Protocols/
```

### Business Use
```
Collections/
├── Operations/
│   ├── Policies/
│   │   ├── HR/
│   │   └── IT/
│   └── Procedures/
├── Projects/
│   ├── Product Launch 2024/
│   └── Market Expansion/
└── Compliance/
    ├── Financial/
    └── Data Protection/
```

## 🎯 Recommended Approach

1. **Use "Collections" for top-level containers** - It's professional and implies curation
2. **Use "Folders" for sub-organization** - Everyone understands folders
3. **Support arbitrary nesting** - Let users organize however deep they need
4. **Cache the full path** - For efficient breadcrumb display
5. **Implement move/copy operations** - Users will want to reorganize

## 🔍 @ Mention Context Examples

With this structure, @ mentions become very powerful:
- `@Cases` - Search all cases
- `@Cases/Smith` - Search only Smith v. Jones case
- `@Regulations/Europe` - Search only European regulations
- `@Collections:Patents` - Search across all patent-related folders

This gives users precise control over search scope while maintaining an intuitive folder metaphor!