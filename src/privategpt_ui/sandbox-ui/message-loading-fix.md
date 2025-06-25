# Assistant Messages Not Loading - Fix Summary

## Issue
When switching between conversations, user messages were loading but assistant messages were not appearing.

## Root Cause
The backend API was returning the `MessageRole` enum object directly instead of its string value when fetching messages. This caused the frontend to receive the enum object which couldn't be properly parsed.

## Fix Applied

### Backend Changes (chat_router.py)
Updated all `MessageResponse` creation to convert enum to string value:

```python
# Before
role=msg.role

# After  
role=msg.role.value if hasattr(msg.role, 'value') else msg.role
```

Applied to:
1. `list_messages` endpoint (line 458)
2. `create_message` endpoint (line 512)
3. `conversation_chat` endpoint (lines 560, 571)

### Frontend Changes

1. **Made setActiveSession async** in chatStore.ts:
   - Now automatically loads conversation messages when switching chats
   - Checks if messages are already loaded to avoid duplicate API calls
   
2. **Fixed sidebar scrolling**:
   - Added proper flex container classes
   - Set max-height with calc() for proper overflow
   - Added min-h-0 to enable scrolling

## Testing
1. Restart gateway service: `docker-compose restart gateway-service`
2. Switch between conversations - both user and assistant messages should load
3. Create new conversations and verify messages persist
4. Check sidebar scrolls properly with many conversations

## Result
- Assistant messages now load correctly when switching conversations
- Sidebar scrolls properly when conversation list overflows
- Conversation switching is smooth with automatic message loading