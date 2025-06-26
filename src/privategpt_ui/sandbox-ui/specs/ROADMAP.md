# PrivateGPT UI Feature Roadmap

## Overview
This roadmap outlines the key features to be implemented in the Next.js UI for PrivateGPT, focusing on document management with RAG integration, enhanced chat interactions, and future MCP tool visualization.

## Feature 1: Document Management System (Priority 1)
**Priority**: High  
**Status**: Ready to Start

### Description
Complete UI integration with the existing RAG service backend for document upload, collection management, and real-time processing visualization.

### Requirements
- [ ] Document upload with drag & drop support
- [ ] Collection/folder creation and management UI
- [ ] Hierarchical folder structure display (backend already supports this)
- [ ] Real-time processing status with percentage display
- [ ] Progress visualization for document processing stages:
  - Uploading (0%)
  - Splitting text (10-20%)
  - Generating embeddings (30-70%)
  - Storing vectors (70-85%)
  - Finalizing (95%)
  - Complete (100%)
- [ ] File metadata display (size, type, upload date)
- [ ] Batch upload support
- [ ] Error handling with retry mechanisms
- [ ] Collection actions (create, rename, delete, move)

### Backend Integration Points
- `POST /api/rag/collections` - Create collection
- `GET /api/rag/collections` - List collections with document counts
- `POST /api/rag/collections/{id}/documents` - Upload document
- `GET /api/rag/documents/{id}/status` - Get document status
- `GET /api/rag/progress/{task_id}` - Poll for real-time progress (returns percentage)
- `DELETE /api/rag/collections/{id}?hard_delete=true` - Delete collection

### Implementation Notes
- Create `DocumentUploader` component with react-dropzone
- Implement `CollectionTree` component for folder hierarchy
- Use polling on `/api/rag/progress/{task_id}` for percentage updates
- Store upload state in new `documentStore` (Zustand)
- Show progress bar with percentage for each uploading document

## Feature 2: Data Sources Sidebar Tab (Priority 1)
**Priority**: High  
**Status**: Ready to Start

### Description
Add a "Data Sources" tab in the sidebar next to Files and History tabs to display available collections and folders with drag support for chat context.

### Requirements
- [ ] New "Data Sources" tab in sidebar navigation
- [ ] Tree view of collections and folders
- [ ] Visual indicators for:
  - Collection type icons (📁 for folders, 📚 for root collections)
  - Document count badges per collection
  - Processing status indicators
- [ ] Real-time updates when documents are added/processed
- [ ] Expandable/collapsible tree nodes
- [ ] Drag support for entire collections (not individual documents)
- [ ] Search/filter collections by name
- [ ] Collection context menu:
  - Add new subfolder
  - Rename collection
  - Delete (with confirmation)
  - View details

### Backend Integration Points
- `GET /api/rag/collections` - Fetch user's collection tree
- `GET /api/rag/collections/{id}/breadcrumb` - Get collection path
- Collections include: id, name, parent_id, document_count, total_document_count

### Implementation Notes
- Extend existing `Sidebar` component with new tab
- Create `DataSourcesPanel` component
- Implement `CollectionTreeItem` with drag source functionality
- Use React DnD for drag capabilities
- Auto-refresh collection counts when documents finish processing
- Store collections in `documentStore`

## Feature 3: Context-Aware Chat Bar (Priority 1)
**Priority**: High  
**Status**: Ready to Start

### Description
Enable drag & drop of collections into the chat input area to add entire collections as context for RAG-powered responses.

### Requirements
- [ ] Drop zone indicator in chat input area
- [ ] Visual feedback during drag operations (highlight drop area)
- [ ] Context chips showing active collections
- [ ] @ symbol trigger for context selection:
  - Type @ to show collection dropdown
  - Search/filter available collections in real-time
  - Select to add entire collection to context
  - Show as highlighted chips with collection name and icon
- [ ] Context management:
  - Click X to remove individual collections
  - "Clear all" button for multiple contexts
  - Show collection document count in chip tooltip
- [ ] Maximum 5 collections at once (configurable)
- [ ] Context persistence:
  - Store selected collection IDs with each message
  - Pass collection_ids array to backend with chat requests
  - Visual indicator on messages that used collection context

### Backend Integration
- Modify chat request to include: `{ message: string, collection_ids: string[] }`
- Backend will search only within specified collections
- Note: RAG search within collections needs backend completion

### Implementation Notes
- Enhance `ChatInput` component with React DnD drop target
- Create `ContextSelector` dropdown with collection search
- Implement `CollectionChip` component with remove button
- Add `selectedCollections` to `chatStore`
- Update chat API calls to include collection_ids

## Feature 4: Interactive Command System (Priority 2)
**Priority**: Medium  
**Status**: Planning

### Description
Implement slash commands in the chat input for quick actions and enhanced interactivity.

### Requirements
- [ ] Command recognition with / prefix
- [ ] Auto-complete suggestions dropdown
- [ ] Built-in commands:
  - `/clear` - Clear current conversation
  - `/new` - Start new conversation
  - `/model [name]` - Switch AI model
  - `/context` - Show current collection context
  - `/context clear` - Clear all context
  - `/help` - Display available commands
  - `/export` - Export conversation
- [ ] Command syntax highlighting
- [ ] Tab completion for commands
- [ ] Command history (up/down arrows)

### Implementation Notes
- Create `CommandParser` utility
- Implement `CommandSuggestions` dropdown component
- Add command handling to `ChatInput` keydown events
- Store command history in localStorage
- Commands should work alongside @ mentions

## Feature 5: Enhanced Visual Feedback (Priority 2)
**Priority**: Medium  
**Status**: Planning

### Description
Improve visual feedback and interactivity throughout the chat interface.

### Requirements
- [ ] Syntax highlighting for:
  - @ mentions (blue highlight)
  - / commands (purple highlight)
  - Collection context chips
- [ ] Animation effects:
  - Smooth transitions when adding/removing context
  - Progress bar animations
  - Loading skeleton for collections
- [ ] Interactive elements:
  - Hover tooltips on context chips (show document count)
  - Drag preview when dragging collections
  - Drop zone glow effect
- [ ] Status indicators:
  - Active collection count in chat input
  - Processing indicator for documents
  - Upload queue visualization

### Implementation Notes
- Use Framer Motion for animations
- Create consistent color scheme for highlights
- Add visual feedback utilities
- Ensure accessibility with ARIA labels

## Feature 6: MCP Tool Visualization (Future)
**Priority**: Low  
**Status**: Deferred - Backend Implementation Pending

### Description
Once MCP tool execution is fully implemented in the backend, add visual feedback for AI tool calls.

### Requirements
- [ ] Display tool calls in chat messages
- [ ] Show tool names, parameters, and results
- [ ] Collapsible tool call details
- [ ] Visual indicators for tool execution status
- [ ] Support for MCP tools:
  - `search_documents` - Show documents found
  - `rag_chat` - Display RAG context used
  - Other tools as implemented

### Backend Dependencies
- MCP tool execution needs to be completed in gateway
- Tool calls need to be included in message responses
- Streaming support for tool execution updates

### Implementation Notes
- Will integrate with existing `MessageRenderer`
- Create `ToolCallDisplay` component
- Parse tool calls from message metadata
- Design deferred until backend is ready

## Technical Implementation Plan

### Phase 1: Foundation (Week 1-2)
1. Create `documentStore` for state management
2. Implement document upload UI with drag & drop
3. Add Data Sources tab to sidebar
4. Basic collection tree display
5. Progress polling for uploads

### Phase 2: Context Integration (Week 3-4)
1. Implement drag from sidebar to chat
2. Add @ mention collection selector
3. Create context chip components
4. Integrate collection context with chat API
5. Visual feedback for drag operations

### Phase 3: Commands & Polish (Week 5-6)
1. Implement slash command system
2. Add syntax highlighting
3. Enhance animations and transitions
4. Complete error handling
5. Testing and refinement

### Dependencies & Blockers
- **Backend RAG Search**: Collection-scoped search needs to be implemented
- **MCP Tool Execution**: Currently has TODOs in backend, needed for Feature 6
- **API Integration**: Some endpoints may need modification for collection context

### Success Metrics
- Users can upload documents and see real-time progress percentages
- Collections are displayed in hierarchical tree structure
- Drag & drop from sidebar to chat works smoothly
- @ mentions provide quick collection selection
- Visual feedback is clear and responsive
- Commands enhance productivity
- Overall UX is intuitive and efficient