# PrivateGPT UI - Project Documentation

## Overview

The PrivateGPT UI is a modern Next.js 15 application that provides a secure, user-friendly interface for interacting with the PrivateGPT backend services. Built with TypeScript, Tailwind CSS, and Zustand for state management, it offers a seamless chat experience with document management capabilities.

## Architecture

### Technology Stack
- **Framework**: Next.js 15.3.4 (App Router)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 3.4
- **State Management**: Zustand 5.0
- **UI Components**: Custom components with Framer Motion animations
- **Icons**: Lucide React
- **HTTP Client**: Custom API client with built-in auth and error handling
- **Development**: Turbopack, ESLint, hot reload via Docker volumes

### Key Design Decisions

1. **App Router**: Using Next.js 15's App Router for better performance and simplified routing
2. **Client Components**: Most components are client-side for real-time interactivity
3. **Zustand Stores**: Centralized state management with persistence for auth and chat data
4. **Custom API Client**: Type-safe API client with automatic token management
5. **Docker Integration**: Seamless development with volume mounts for hot reload

## Project Structure

```
src/
├── app/                      # Next.js App Router pages
│   ├── (dashboard)/         # Authenticated routes group
│   │   ├── layout.tsx       # Dashboard layout with auth protection
│   │   ├── page.tsx         # Main chat interface
│   │   ├── admin/           # Admin panel
│   │   ├── documents/       # Document management
│   │   ├── settings/        # User settings
│   │   └── test/            # Test chat interface
│   ├── layout.tsx           # Root layout
│   └── page.tsx            # Landing/login redirect
│
├── components/              # React components
│   ├── chat/               # Chat-related components
│   │   ├── ChatInput.tsx   # Message input with file upload
│   │   ├── ChatMessage.tsx # Individual message display
│   │   └── MessageList.tsx # Scrollable message container
│   ├── shell/              # App shell components
│   │   ├── AppShell.tsx    # Main application wrapper
│   │   ├── Header.tsx      # Top navigation bar
│   │   └── Sidebar.tsx     # Left navigation sidebar
│   ├── AdminPage.tsx       # Admin dashboard
│   ├── AuthWrapper.tsx     # Authentication wrapper
│   ├── ChatInterface.tsx   # Main chat UI component
│   ├── ConversationSidebar.tsx # Conversation list
│   ├── LLMSettings.tsx     # Model selection UI
│   ├── LoginPage.tsx       # Login form
│   └── LogoutButton.tsx    # Logout functionality
│
├── lib/                     # Utilities and clients
│   ├── api-client.ts       # HTTP client for backend API
│   ├── config.ts           # App configuration
│   ├── toast.ts            # Toast notification utilities
│   └── utils.ts            # Helper functions
│
├── services/               # Business logic services
│   └── chatService.ts      # Chat operations wrapper
│
├── stores/                 # Zustand state stores
│   ├── authStore.ts        # Authentication state
│   ├── chatStore.ts        # Chat conversations and messages
│   └── fileSystemStore.ts  # File management state
│
└── types/                  # TypeScript definitions
    ├── chat.ts             # Chat-related types
    └── index.ts            # Common types
```

## Core Features

### 1. Authentication
- JWT-based authentication with Keycloak integration
- Persistent sessions with automatic token refresh
- Protected routes using AuthWrapper component
- Logout functionality with proper cleanup

### 2. Chat Interface
- Real-time streaming responses using Server-Sent Events (SSE)
- Multiple conversation management
- Message history with pagination
- File upload support (prepared for future implementation)
- Model selection with dynamic loading from backend

### 3. Admin Panel
- User management interface
- System settings configuration
- Model provider management

### 4. Document Management
- Document upload and storage
- Search functionality
- Integration with chat for context-aware responses

## API Integration

### Base Configuration
```typescript
// Base URL configuration (without /api suffix)
apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```

### API Endpoints
All endpoints include the `/api` prefix:
- **Auth**: `/api/auth/login`, `/api/auth/logout`, `/api/auth/verify`
- **Chat**: `/api/chat/conversations`, `/api/chat/direct`, `/api/chat/direct/stream`
- **Models**: `/api/llm/models`, `/api/llm/providers`
- **Users**: `/api/users/me`

### Authentication Flow
1. User enters credentials in LoginPage
2. API client sends POST to `/api/auth/login`
3. JWT token stored in localStorage and Zustand
4. Token automatically included in all subsequent requests
5. Token verification on app load via `/api/auth/verify`

### Streaming Implementation
- Uses fetch-based streaming instead of EventSource for auth support
- Handles Server-Sent Events (SSE) format
- Automatic reconnection and error handling
- Progress indication during streaming

## Development Setup

### Environment Variables
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8180
NODE_ENV=development
```

### Docker Integration
The UI runs in Docker with these key configurations:
- **Port**: Internal port 3000, accessed via Traefik on port 80
- **Volumes**: Source files mounted for hot reload
- **Network**: Connected to `privategpt_default` network
- **Environment**: Variables passed from docker-compose.yml

### Running Locally
```bash
cd src/privategpt_ui/sandbox-ui
npm install
npm run dev
```

Access at `http://localhost:3000`

### Running in Docker
```bash
docker-compose up -d nextjs-ui
```

Access at `http://localhost` (via Traefik)

## Common Issues and Solutions

### 1. "Network error: Failed to fetch" on Login
**Cause**: API URL misconfiguration or CORS issues
**Solution**: 
- Ensure `NEXT_PUBLIC_API_URL` is set correctly (without `/api` suffix)
- Check that all endpoints in api-client.ts include `/api` prefix
- Verify backend CORS allows frontend origin

### 2. "Not Found" Error on API Calls
**Cause**: Incorrect endpoint paths
**Solution**: 
- Backend routes all have `/api` prefix (e.g., `/api/auth/login`)
- Don't include `/api` in the base URL
- Include `/api` in individual endpoint paths

### 3. Authentication State Lost on Refresh
**Cause**: Token not persisted or verification failing
**Solution**: 
- Check localStorage for `auth_token`
- Ensure `/api/auth/verify` endpoint is working
- Verify token hasn't expired

### 4. Docker Container Not Reflecting Changes
**Cause**: Volume mounts or caching issues
**Solution**: 
- Source is mounted as volume, changes should be immediate
- For dependency changes, rebuild: `docker-compose build --no-cache nextjs-ui`
- Check volume mounts in docker-compose.yml

## State Management

### Auth Store (authStore.ts)
```typescript
interface AuthState {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<boolean>
  logout: () => void
  verifyAuth: () => Promise<boolean>
}
```

### Chat Store (chatStore.ts)
- Manages conversations and messages
- Handles streaming state and updates
- Persists conversation history
- Supports multiple concurrent chats

## Testing

### Test Page
Access `/test` for a minimal chat interface to debug:
- Direct chat API calls
- Streaming functionality
- Error handling
- Model selection

### Debug Utilities
- Console logging in API client
- Toast notifications for errors
- Network request monitoring in browser DevTools

## Security Considerations

1. **JWT Storage**: Tokens stored in localStorage (consider httpOnly cookies for production)
2. **API Authentication**: All requests include Bearer token
3. **Route Protection**: AuthWrapper component prevents unauthorized access
4. **CORS**: Backend configured to allow only specific origins
5. **Input Validation**: Frontend validation before API calls

## Future Enhancements

1. **WebSocket Support**: Real-time updates for collaborative features
2. **File Upload**: Complete implementation for document chat
3. **Offline Support**: Service worker for offline functionality
4. **Theme System**: Dark/light mode toggle
5. **Internationalization**: Multi-language support
6. **Performance**: Implement virtual scrolling for large conversations

## Troubleshooting Commands

```bash
# Check container logs
docker logs privategpt-nextjs-ui-1 -f

# Restart container
docker-compose restart nextjs-ui

# Rebuild without cache
docker-compose build --no-cache nextjs-ui

# Check running processes
docker ps | grep nextjs

# Access container shell
docker exec -it privategpt-nextjs-ui-1 sh

# Test API endpoint
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"admin"}'
```

## Contributing

1. Follow the existing code style (Prettier + ESLint)
2. Add types for all new features
3. Update this documentation for significant changes
4. Test in both local and Docker environments
5. Ensure authentication flow remains intact

---

Last Updated: December 2024
Version: 2.0.0