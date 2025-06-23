# Frontend Issues Response

## 1. Login Endpoint Issue

The `/api/auth/login` endpoint is **working correctly**:

- ✅ Auth router is properly mounted at `/api/auth/*`
- ✅ Keycloak service is running and accessible
- ✅ CORS is properly configured for `http://localhost:3000`
- ✅ Login endpoint returns valid JWT tokens

### Test Results:
```bash
# Login works and returns JWT
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@admin.com", "password": "admin"}'

# Returns: {"access_token": "...", "expires_in": 3600, ...}
```

### CORS Headers Confirmed:
```
access-control-allow-credentials: true
access-control-allow-origin: http://localhost:3000
```

If you're still getting network errors, please check:
1. Frontend is using `http://localhost:8000/api/auth/login` (not port 80)
2. Request includes `Content-Type: application/json` header
3. Body is JSON: `{"email": "...", "password": "..."}`

## 2. Streaming Authentication

✅ **Already implemented** - All streaming endpoints use JWT authentication:

```python
@router.post("/conversations/{conversation_id}/chat/stream")
async def stream_chat_with_conversation(
    conversation_id: str,
    chat_request: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user),  # ← Auth required
    session: AsyncSession = Depends(get_async_session)
):
```

The backend correctly reads the `Authorization` header from the initial request (not EventSource).

## 3. Model Parameter

✅ **Fixed** - Updated `ChatRequest` to use `model` instead of `model_name` for consistency:

```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    stream: bool = Field(default=False)
    model: Optional[str] = None  # Changed from model_name
    # ... other fields
```

All endpoints now accept `model` parameter consistently:
- `/api/chat/direct` - ✅ uses `model`
- `/api/chat/conversations/{id}/chat` - ✅ uses `model`
- `/api/chat/conversations/{id}/chat/stream` - ✅ uses `model`

## Working Example

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    email: 'admin@admin.com', 
    password: 'admin' 
  })
});
const { access_token } = await loginResponse.json();

// Chat with streaming
const response = await fetch('http://localhost:8000/api/chat/direct/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    message: 'Hello!',
    model: 'tinyllama:1.1b'  // Note: using 'model' not 'model_name'
  })
});

// Read stream
const reader = response.body.getReader();
// ... process SSE stream
```

## Notes

- The gateway service shows as "unhealthy" due to missing `curl` in Docker container (cosmetic issue)
- Use `tinyllama:1.1b` model - larger models may cause memory errors
- All protected endpoints require `Authorization: Bearer <token>` header