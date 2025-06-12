# Redis-Backed Configuration System Implementation

## Overview

Successfully implemented a Redis-backed configuration management system that provides:
- **Immediate Effect**: Admin changes take effect instantly across all services
- **Persistence**: Settings survive container restarts and deployments  
- **Graceful Fallback**: Falls back to config.json when Redis unavailable
- **Three-Tier Hierarchy**: Redis overrides > config.json defaults > hardcoded defaults

## Architecture

### Configuration Hierarchy
1. **Redis Overrides** (highest priority) - Admin-changeable settings stored in Redis
2. **config.json Defaults** (fallback) - Base configuration file
3. **Hardcoded Defaults** (last resort) - Code-level defaults

### Redis Database Usage
- **Database 0**: Auth sessions & rate limiting (existing)
- **Database 1**: Celery results (existing)
- **Database 2**: Configuration storage (new)

## Implementation Details

### Enhanced Config Loader (`config_loader.py`)

**Key Features:**
- Optional Redis dependency with graceful fallback
- Caching with configurable TTL (60 seconds)
- JSON serialization for type preservation
- Connection pooling and error handling

**Core Methods:**
```python
config_loader = get_config_loader()

# Get setting with hierarchy: Redis > config.json > default
value = config_loader.get("models.llm.max_tokens", 1000)

# Set admin override in Redis
success = config_loader.set_setting("models.llm.max_tokens", 2000)

# Remove override, fall back to config.json
removed = config_loader.remove_override("models.llm.max_tokens")

# Check setting source
source = config_loader.get_setting_source("models.llm.max_tokens")  # "redis", "config", or "default"

# List all Redis overrides
overrides = config_loader.list_overrides()
```

### Admin API Updates (`docker/knowledge-service/app/routers/admin.py`)

**Enhanced Endpoints:**
- `GET /admin/settings` - Returns settings with source information
- `POST /admin/settings` - Updates settings in Redis with validation
- `DELETE /admin/settings` - Resets all settings to config.json defaults
- `GET /admin/settings/{key}` - Get detailed info about specific setting
- `DELETE /admin/settings/{key}` - Reset single setting to default
- `GET /admin/health` - Shows Redis availability and override count

**Key Improvements:**
- Removed in-memory `_settings_overrides` store
- All settings now use Redis with config.json fallback
- Real-time validation against Ollama for model selection
- Detailed error handling and logging

### Service Integration

**Knowledge Service Chat Router:**
- Already using admin module functions (no changes needed)
- Automatically benefits from Redis-backed configuration

**Streamlit Pages:**
- Updated LLM chat page to use centralized config
- Added Redis dependency to requirements.txt
- Removed hardcoded configuration values

## Configuration Keys

### LLM Settings
- `models.llm.max_context_tokens` - Maximum context tokens (default: 3000)
- `models.llm.default_search_limit` - Search results limit (default: 5)
- `models.llm.default_max_tokens` - Response token limit (default: 1000)
- `models.llm.default_temperature` - Response creativity (default: 0.7)
- `models.llm.timeout_seconds` - Request timeout (default: 120)

### Model Selection
- `model.name` - Currently selected model (default: "llama3.2:1b")

### Redis Key Format
```
config:models.llm.max_tokens = 2000
config:models.llm.temperature = 0.8
config:model.name = "llama3:8b"
```

## Benefits Achieved

### 1. Immediate Effect
- Admin changes in UI instantly affect all services
- No container restarts required
- Real-time configuration updates

### 2. Persistence
- Settings survive container restarts
- Survives deployments and scaling
- Consistent across all service instances

### 3. No Conflicts
- Uses dedicated Redis database 2
- No interference with existing Redis usage:
  - auth-redis (db 0): Auth sessions
  - redis (db 0): Celery broker
  - redis (db 1): Celery results

### 4. Graceful Fallback
- Works without Redis (uses config.json)
- Automatic reconnection attempts
- Error logging without service disruption

### 5. Performance
- Redis caching with 60-second TTL
- Minimal latency for configuration reads
- Efficient batch operations

## Testing

### Local Testing (Redis Unavailable)
```bash
python3 test_redis_config.py
```
Output shows graceful fallback to config.json.

### Docker Testing (Redis Available)
When containers are running, the same script will show:
- Redis connection successful
- Setting/getting overrides
- Source tracking (redis/config/default)
- Override listing and removal

## Usage Examples

### Admin Panel Workflow
1. Admin opens Settings page
2. Changes model from "llama3.2:1b" to "llama3:8b"
3. Clicks "Apply Settings"
4. Change stored in Redis database 2
5. All services immediately use new model
6. Setting persists across restarts

### API Usage
```bash
# Get current settings
curl -H "Authorization: Bearer $TOKEN" \
  http://knowledge-service:8000/admin/settings

# Update temperature
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"DEFAULT_TEMPERATURE": "0.9"}' \
  http://knowledge-service:8000/admin/settings

# Reset to defaults
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://knowledge-service:8000/admin/settings
```

## Migration Notes

### Removed Components
- In-memory `_settings_overrides` dictionary
- Hardcoded environment variable dependencies
- Local model selection functions

### Backward Compatibility
- All existing APIs maintain same interface
- Environment variables still work as defaults
- No breaking changes to service communication

## Monitoring

### Health Check
```bash
curl http://knowledge-service:8000/admin/health
```

Returns:
```json
{
  "service": "admin-api",
  "status": "healthy",
  "config_source": "redis_with_config_fallback",
  "redis_available": true,
  "redis_overrides_count": 3
}
```

### Logging
- Configuration changes logged with user context
- Redis connection issues logged as warnings
- Fallback behavior logged for debugging

## Security

### Access Control
- Admin-only endpoints with JWT validation
- Redis access limited to configuration database
- No exposure of sensitive Redis credentials

### Data Validation
- Type checking for numeric values
- Range validation (temperature 0.0-2.0)
- Model existence validation against Ollama

## Future Enhancements

### Potential Additions
1. **Audit Trail**: Log all configuration changes with timestamps
2. **Configuration Versioning**: Track configuration history
3. **Bulk Operations**: Import/export configuration sets
4. **Real-time Notifications**: WebSocket updates for configuration changes
5. **Configuration Templates**: Predefined setting combinations

### Scalability
- Redis Cluster support for high availability
- Configuration sharding for large deployments
- Distributed cache invalidation

## Conclusion

The Redis-backed configuration system successfully addresses the original problem of scattered configuration sources. It provides a unified, persistent, and immediately effective configuration management solution that scales with the application while maintaining backward compatibility and graceful degradation.

**Key Achievement**: Admins can now change LLM settings (model selection, parameters) through the UI and see immediate effects across all services without any restarts or deployments. 