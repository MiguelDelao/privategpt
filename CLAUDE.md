# Claude AI Instructions

## Primary Directive
**Read PROJECT.md first** - it contains everything you need to understand this codebase at a senior engineering level.

## Key Guidelines
1. **Always read PROJECT.md** before starting any work to understand the architecture
2. **Make frequent small commits** - commit after completing discrete changes or fixes
3. **Track progress in TASKS.md** - update task status as you work
4. **Follow existing patterns** - this is a well-architected microservices system

## Commit Strategy 
- Commit after each logical change (bug fix, feature addition, refactor), but only after you or the user can confirmed it was successful.
- Use conventional commit format: `type(scope): description`

## File Locations
- **PROJECT.md** - Complete system documentation and architecture
- **TASKS.md** - Current task tracking and status
- **docker-compose.yml** - Service orchestration
- **src/privategpt/services/** - Microservice implementations
- **src/privategpt/shared/** - Common utilities and authentication

## Current System Status
✅ Authentication working (Keycloak + JWT)  
✅ API Gateway routing requests  
✅ UI login functional with admin@admin.com/admin  
✅ Microservices architecture established

That's it. Read PROJECT.md for everything else.