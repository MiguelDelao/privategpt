# Fixes Applied

## Issue 1: Conversation history not loading when switching between chats

**Fix:** Modified `setActiveSession` in `chatStore.ts` to:
1. Made it async
2. Check if session already has messages loaded
3. If not, call `loadConversation` to fetch messages from backend
4. Updated all callers to handle async function

## Issue 2: Sidebar not scrollable when conversation list overflows

**Fix:** Modified the sidebar layout in `Sidebar.tsx`:
1. Added `flex flex-col min-h-0` to container
2. Added `min-h-0` and `sidebar-scroll` class to scrollable area
3. Set a max-height using calc() to ensure proper scrolling
4. The sidebar already had the correct CSS classes in globals.css

## Testing Instructions

1. Create multiple conversations (more than can fit in sidebar)
2. Switch between conversations - they should load previous messages
3. Verify sidebar scrolls when conversations overflow
4. Check that conversation switching is smooth and loads data correctly

## Code Changes

1. **chatStore.ts**:
   - `setActiveSession` now async and loads conversation if needed
   - Updated interface to reflect async nature

2. **Sidebar.tsx**:
   - Updated all `setActiveSession` calls to be async
   - Improved layout classes for proper scrolling
   - Added max-height calculation

The fixes ensure that:
- When switching conversations, the full conversation data is loaded from backend
- The sidebar properly scrolls when there are many conversations
- All type errors are resolved