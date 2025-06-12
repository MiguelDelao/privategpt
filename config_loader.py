"""
Centralized Configuration Loader for PrivateGPT Legal AI
Replaces scattered environment variables with single source of truth
Supports Redis-backed admin-changeable settings with config.json fallbacks
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)

# Try to import redis, but make it optional for graceful fallback
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - configuration will be read-only from config.json")

class ConfigLoader:
    """Centralized configuration loader with Redis-backed admin overrides"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self._config = None
        self._redis_client = None
        self._cache = {}
        self._cache_ttl = 60  # Cache for 1 minute
        self._last_cache_time = {}
        
        self._load_config()
        self._init_redis()
    
    def _load_config(self):
        """Load configuration from JSON file"""
        try:
            # Try current directory first
            config_path = Path(self.config_file)
            
            # If not found, try parent directory (for services in subdirectories)
            if not config_path.exists():
                config_path = Path("..") / self.config_file
            
            # If still not found, try project root
            if not config_path.exists():
                config_path = Path("../../") / self.config_file
            
            if not config_path.exists():
                raise FileNotFoundError(f"Config file {self.config_file} not found")
            
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            
            logger.info(f"Configuration loaded from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Fallback to minimal default config
            self._config = self._get_default_config()
    
    def _init_redis(self):
        """Initialize Redis client for configuration overrides"""
        if not REDIS_AVAILABLE:
            return
            
        try:
            # Use the main redis instance, database 2 for configuration
            redis_host = os.getenv('REDIS_HOST', 'redis')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            
            self._redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=2,  # Dedicated database for configuration
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self._redis_client.ping()
            logger.info(f"Redis configuration store connected: {redis_host}:{redis_port}/2")
            
        except Exception as e:
            logger.warning(f"Redis configuration store unavailable: {e}")
            self._redis_client = None
    
    def _get_from_redis(self, key: str) -> Any:
        """Get setting from Redis with caching"""
        if not self._redis_client:
            return None
            
        # Check cache first
        cache_key = f"redis:{key}"
        if cache_key in self._cache:
            cache_time = self._last_cache_time.get(cache_key, 0)
            if time.time() - cache_time < self._cache_ttl:
                return self._cache[cache_key]
        
        try:
            redis_key = f"config:{key}"
            value = self._redis_client.get(redis_key)
            
            if value is not None:
                # Try to parse as JSON, fall back to string
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed_value = value
                
                # Cache the result
                self._cache[cache_key] = parsed_value
                self._last_cache_time[cache_key] = time.time()
                
                return parsed_value
                
        except Exception as e:
            logger.warning(f"Failed to get Redis config for {key}: {e}")
            
        return None
    
    def _get_from_config_file(self, key_path: str) -> Any:
        """Get setting from config.json file"""
        try:
            keys = key_path.split('.')
            value = self._config
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return None
    
    def _invalidate_cache(self, key: str):
        """Invalidate cache for a specific key"""
        cache_key = f"redis:{key}"
        self._cache.pop(cache_key, None)
        self._last_cache_time.pop(cache_key, None)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation with three-tier hierarchy:
        1. Redis overrides (highest priority)
        2. config.json defaults (fallback)
        3. Provided default (last resort)
        """
        # 1. Try Redis first (admin overrides)
        redis_value = self._get_from_redis(key_path)
        if redis_value is not None:
            return redis_value
            
        # 2. Fall back to config.json
        config_value = self._get_from_config_file(key_path)
        if config_value is not None:
            return config_value
            
        # 3. Use provided default
        return default
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Set configuration setting in Redis (admin override)"""
        if not self._redis_client:
            logger.error("Cannot set configuration: Redis not available")
            return False
            
        try:
            redis_key = f"config:{key}"
            # Store as JSON to preserve type information
            json_value = json.dumps(value)
            self._redis_client.set(redis_key, json_value)
            
            # Invalidate cache
            self._invalidate_cache(key)
            
            logger.info(f"Configuration setting updated: {key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Redis config for {key}: {e}")
            return False
    
    def remove_override(self, key: str) -> bool:
        """Remove Redis override, falling back to config.json default"""
        if not self._redis_client:
            logger.error("Cannot remove override: Redis not available")
            return False
            
        try:
            redis_key = f"config:{key}"
            result = self._redis_client.delete(redis_key)
            
            # Invalidate cache
            self._invalidate_cache(key)
            
            if result:
                logger.info(f"Configuration override removed: {key}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to remove Redis override for {key}: {e}")
            return False
    
    def get_setting_source(self, key: str) -> str:
        """Get the source of a configuration setting (redis/config/default)"""
        if self._get_from_redis(key) is not None:
            return "redis"
        elif self._get_from_config_file(key) is not None:
            return "config"
        else:
            return "default"
    
    def list_overrides(self) -> Dict[str, Any]:
        """List all Redis configuration overrides"""
        if not self._redis_client:
            return {}
            
        try:
            overrides = {}
            for key in self._redis_client.scan_iter(match="config:*"):
                config_key = key.replace("config:", "")
                value = self._redis_client.get(key)
                try:
                    overrides[config_key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    overrides[config_key] = value
            return overrides
        except Exception as e:
            logger.error(f"Failed to list Redis overrides: {e}")
            return {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Fallback default configuration"""
        return {
            "app": {
                "name": "PrivateGPT Legal AI",
                "version": "2.5.0",
                "environment": "production"
            },
            "admin": {
                "email": "admin@admin.com",
                "password": "admin",
                "role": "admin"
            },
            "services": {
                "auth_service": "http://auth-service:8000",
                "knowledge_service": "http://knowledge-service:8000",
                "ollama": "http://ollama-service:11434",
                "weaviate": "http://weaviate-db:8080"
            },
            "model": {
                "name": "llama3.2:1b"
            },
            "models": {
                "llm": {
                    "max_context_tokens": 3000,
                    "default_search_limit": 5,
                    "default_max_tokens": 1000,
                    "default_temperature": 0.7,
                    "timeout_seconds": 120
                }
            }
        }

# Global config instance
_config_loader = None

def get_config_loader() -> ConfigLoader:
    """Get global config loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader

# Convenience functions for common configurations

def get_admin_email() -> str:
    """Get admin email from config"""
    return get_config_loader().get("admin.email", "admin@admin.com")

def get_admin_password() -> str:
    """Get admin password from config"""
    return get_config_loader().get("admin.password", "admin")

def get_admin_role() -> str:
    """Get admin role from config"""
    return get_config_loader().get("admin.role", "admin")

def get_model_name() -> str:
    """Get current model name from config"""
    return get_config_loader().get("model.name", "llama3.2:1b")

def get_service_url(service_name: str) -> str:
    """Get service URL from config"""
    service_urls = {
        "auth": get_config_loader().get("services.auth_service", "http://auth-service:8000"),
        "knowledge": get_config_loader().get("services.knowledge_service", "http://knowledge-service:8000"),
        "ollama": get_config_loader().get("services.ollama", "http://ollama-service:11434"),
        "weaviate": get_config_loader().get("services.weaviate", "http://weaviate-db:8080"),
        "elasticsearch": get_config_loader().get("services.elasticsearch", "http://elasticsearch:9200"),
        "redis": get_config_loader().get("services.redis", "http://redis:6379")
    }
    return service_urls.get(service_name, "")

def get_llm_settings() -> Dict[str, Any]:
    """Get LLM configuration settings"""
    return {
        "max_context_tokens": get_config_loader().get("models.llm.max_context_tokens", 3000),
        "default_search_limit": get_config_loader().get("models.llm.default_search_limit", 5),
        "default_max_tokens": get_config_loader().get("models.llm.default_max_tokens", 1000),
        "default_temperature": get_config_loader().get("models.llm.default_temperature", 0.7),
        "timeout_seconds": get_config_loader().get("models.llm.timeout_seconds", 120),
        "selected_model": get_model_name()
    }

def get_database_config() -> Dict[str, Any]:
    """Get database configuration"""
    return {
        "auth_url": get_config_loader().get("database.auth.url", "postgresql://privategpt:secure_password_change_me@auth-postgres:5432/privategpt_auth"),
        "redis_url": get_config_loader().get("database.redis.url", "redis://:secure_redis_password@auth-redis:6379/0")
    }

def get_security_config() -> Dict[str, Any]:
    """Get security configuration"""
    return {
        "jwt_secret": get_config_loader().get("security.jwt.secret_key", "admin123456789abcdef"),
        "jwt_algorithm": get_config_loader().get("security.jwt.algorithm", "HS256"),
        "jwt_expiry_hours": get_config_loader().get("security.jwt.expiry_hours", 24),
        "bcrypt_rounds": get_config_loader().get("security.auth.bcrypt_rounds", 12)
    }

def get_app_info() -> Dict[str, Any]:
    """Get application information"""
    return {
        "name": get_config_loader().get("app.name", "PrivateGPT Legal AI"),
        "version": get_config_loader().get("app.version", "2.5.0"),
        "environment": get_config_loader().get("app.environment", "production")
    } 