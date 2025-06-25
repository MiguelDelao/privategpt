# Service Dependencies and Health Check Analysis

## Executive Summary

The PrivateGPT microservices system has a well-structured dependency chain with proper health checks for most critical services. However, there are several areas that need improvement to ensure robust service startup and dependency management.

## Service Dependency Graph

```
┌─────────────────┐
│   PostgreSQL    │ (db)
│  Health: ✅     │
└────────┬────────┘
         │
┌────────▼────────┐
│   Keycloak DB   │ (keycloak-db)
│  Health: ✅     │
└────────┬────────┘
         │
┌────────▼────────┐     ┌─────────────────┐
│    Keycloak     │────►│     Ollama      │
│  Health: ✅     │     │  Health: ✅     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │              ┌────────▼────────┐
         │              │   LLM Service   │
         │              │  Health: ✅     │
         │              └────────┬────────┘
         │                       │
┌────────▼────────┐     ┌────────▼────────┐     ┌─────────────────┐
│     Redis       │     │   RAG Service   │────►│    Weaviate     │
│  Health: ❌     │     │  Health: ✅     │     │  Health: ❌     │
└────────┬────────┘     └────────┬────────┘     └─────────────────┘
         │                       │
         └──────────┬────────────┘
                    │
         ┌──────────▼──────────┐
         │   Gateway Service    │
         │    Health: ✅        │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │    MCP Service      │
         │    Health: ❌        │
         └─────────────────────┘
```

## Health Check Status

### Services WITH Health Checks ✅

1. **PostgreSQL (db)**
   - Test: `pg_isready -U $POSTGRES_USER`
   - Interval: 5s, Timeout: 5s, Retries: 5
   - **Good Practice**: Using database-specific health command

2. **Keycloak PostgreSQL (keycloak-db)**
   - Test: `pg_isready -U keycloak`
   - Interval: 5s, Timeout: 5s, Retries: 5
   - **Good Practice**: Consistent with main DB health check

3. **Keycloak**
   - Test: TCP connection check on port 8080
   - Interval: 15s, Timeout: 5s, Retries: 10
   - **Note**: Longer intervals appropriate for slower startup

4. **Ollama**
   - Test: `curl -f http://localhost:11434/api/tags`
   - Interval: 30s, Timeout: 10s, Retries: 3, Start Period: 60s
   - **Good Practice**: API endpoint check with long start period

5. **LLM Service**
   - Test: `curl -f http://localhost:8000/health`
   - Interval: 30s, Timeout: 10s, Retries: 3, Start Period: 30s
   - Implementation: Returns provider status and model count

6. **Gateway Service**
   - Endpoint: `/health`
   - Implementation: Simple status return
   - Can check backend service health via `/health/{service}`

7. **RAG Service**
   - Endpoint: `/health`
   - Implementation: Simple status return

### Services WITHOUT Health Checks ❌

1. **Redis** - No health check defined
2. **Weaviate** - No health check defined
3. **MCP Service** - Has internal health check tool but no Docker health check
4. **UI Services** (nextjs-ui, ui-service) - No health checks
5. **Elasticsearch** - No health check defined
6. **Kibana** - No health check (but has wait script)
7. **N8N** - No health check defined
8. **Traefik** - No health check needed (infrastructure component)

## Dependency Declaration Analysis

### Proper Dependencies ✅

1. **Keycloak** → keycloak-db (with condition: service_healthy)
2. **Gateway Service** → keycloak, db (with health conditions)
3. **Keycloak Setup** → keycloak (with health condition)

### Weak Dependencies ⚠️

1. **Gateway Service** → llm-service, redis (only service_started)
2. **RAG Service** → db, redis, weaviate (no conditions)
3. **MCP Service** → gateway, rag, llm (no conditions)
4. **UI Services** → gateway (only service_started)

### Missing Dependencies ❌

1. **LLM Service** should wait for Ollama to be healthy
2. **RAG Service** should wait for Weaviate to be ready
3. **Gateway Service** should wait for Redis to be ready

## Identified Issues

### 1. Circular Dependency Risk
- No circular dependencies detected ✅

### 2. Race Conditions
- **RAG Service** may start before Weaviate is ready
- **Gateway Service** may start before all backend services are ready
- **MCP Service** has no startup conditions

### 3. Health Check Quality
- Gateway health check is too simple (doesn't verify dependencies)
- No composite health checks that verify all dependencies

### 4. Timeout Issues
- Some services have short timeouts that may cause false failures
- No exponential backoff for retries

## Recommendations

### 1. Add Missing Health Checks

**Redis Health Check:**
```yaml
redis:
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5
```

**Weaviate Health Check:**
```yaml
weaviate:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/v1/.well-known/ready"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s
```

**MCP Service Health Check:**
```yaml
mcp-service:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 20s
```

### 2. Improve Dependency Conditions

```yaml
# LLM Service should wait for Ollama
llm-service:
  depends_on:
    ollama:
      condition: service_healthy

# RAG Service should use health conditions
rag-service:
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
    weaviate:
      condition: service_healthy

# Gateway should wait for all dependencies
gateway-service:
  depends_on:
    keycloak:
      condition: service_healthy
    db:
      condition: service_healthy
    llm-service:
      condition: service_healthy
    rag-service:
      condition: service_healthy
    redis:
      condition: service_healthy
```

### 3. Implement Comprehensive Health Endpoints

**Enhanced Gateway Health Check:**
```python
@router.get("/health")
async def health_check(proxy: ServiceProxy = Depends(get_proxy)):
    """Comprehensive gateway health check."""
    checks = {
        "gateway": "healthy",
        "database": await check_database(),
        "redis": await check_redis(),
        "backends": {}
    }
    
    # Check all backend services
    for service in ["rag", "llm"]:
        checks["backends"][service] = await proxy.health_check(service)
    
    # Determine overall health
    all_healthy = all(
        check.get("status") == "healthy" 
        for check in checks["backends"].values()
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "service": "gateway",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### 4. Add Service Readiness Probes

In addition to health checks, implement readiness probes that verify:
- Database migrations are complete
- Initial data is loaded
- All required connections are established
- Service is ready to handle requests

### 5. Implement Startup Ordering Script

Create a wait-for-dependencies script similar to the Kibana wait script:

```bash
#!/bin/bash
# scripts/wait-for-services.sh

wait_for_service() {
    local name=$1
    local url=$2
    local timeout=${3:-60}
    
    echo -n "Waiting for $name..."
    for i in $(seq 1 $timeout); do
        if curl -sf "$url" > /dev/null; then
            echo " Ready!"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    echo " Timeout!"
    return 1
}

# Wait for all dependencies
wait_for_service "Database" "http://db:5432" 30
wait_for_service "Redis" "http://redis:6379" 30
wait_for_service "Keycloak" "http://keycloak:8080/health" 120
```

## Conclusion

The current health check and dependency setup is functional but has room for improvement. The main issues are:

1. Missing health checks for Redis, Weaviate, and MCP services
2. Weak dependency conditions using only `service_started`
3. Simple health endpoints that don't verify actual service readiness

Implementing the recommended improvements will make the system more robust and reduce startup failures due to race conditions.