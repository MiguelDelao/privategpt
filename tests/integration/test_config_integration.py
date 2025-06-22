"""
Integration tests for configuration system.

Tests the complete configuration system including real config.json loading,
environment variable integration, and interaction with actual services.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from privategpt.shared.settings import settings, _instance, _CONFIG_ENV


@pytest.fixture
def sample_production_config():
    """Sample production-like configuration."""
    return {
        "log_level": "INFO",
        "database_url": "postgresql://privategpt:secret@db:5432/privategpt",
        "redis_url": "redis://redis:6379/0",
        "weaviate_url": "http://weaviate:8080",
        
        "llm_provider": "ollama",
        "embed_model": "BAAI/bge-small-en-v1.5",
        
        "ollama_enabled": True,
        "ollama_base_url": "http://ollama:11434",
        "ollama_model": "llama3.2",
        
        "openai_enabled": False,
        "openai_api_key": "",
        "openai_model": "gpt-4",
        
        "anthropic_enabled": False,
        "anthropic_api_key": "",
        "anthropic_model": "claude-3-5-sonnet-20241022",
        
        "keycloak_url": "http://keycloak:8080",
        "keycloak_realm": "privategpt",
        "keycloak_client_id": "privategpt-ui",
        
        "default_admin_email": "admin@admin.com",
        "default_admin_password": "admin",
        
        "rag_service_url": "http://rag-service:8000",
        "llm_service_url": "http://llm-service:8000",
        "mcp_service_url": "http://mcp-service:8000",
        
        "mcp_enabled": True,
        "mcp_transport": "stdio",
        "mcp_available_tools": "*",
        
        "default_system_prompt": "You are a helpful AI assistant.",
        "enable_prompt_caching": True,
        "enable_thinking_mode": False
    }


@pytest.fixture
def temp_production_config(sample_production_config):
    """Create a temporary production-like config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_production_config, f, indent=2)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def clear_settings_cache():
    """Clear settings cache before and after test."""
    _instance.cache_clear()
    yield
    _instance.cache_clear()


class TestProductionConfigLoading:
    """Test loading production-like configurations."""
    
    def test_load_complete_production_config(self, temp_production_config, clear_settings_cache):
        """Test loading a complete production configuration."""
        with patch.dict(os.environ, {_CONFIG_ENV: temp_production_config}):
            # Test that all values are loaded correctly
            assert settings.log_level == "INFO"
            assert settings.database_url == "postgresql://privategpt:secret@db:5432/privategpt"
            assert settings.redis_url == "redis://redis:6379/0"
            assert settings.weaviate_url == "http://weaviate:8080"
            
            # LLM Configuration
            assert settings.llm_provider == "ollama"
            assert settings.embed_model == "BAAI/bge-small-en-v1.5"
            
            # Provider specific configs
            assert settings.ollama_enabled is True
            assert settings.ollama_base_url == "http://ollama:11434"
            assert settings.ollama_model == "llama3.2"
            
            assert settings.openai_enabled is False
            assert settings.openai_api_key == ""
            
            assert settings.anthropic_enabled is False
            assert settings.anthropic_api_key == ""
            
            # Authentication
            assert settings.keycloak_url == "http://keycloak:8080"
            assert settings.keycloak_realm == "privategpt"
            assert settings.keycloak_client_id == "privategpt-ui"
            
            # Admin user
            assert settings.default_admin_email == "admin@admin.com"
            assert settings.default_admin_password == "admin"
            
            # Services
            assert settings.rag_service_url == "http://rag-service:8000"
            assert settings.llm_service_url == "http://llm-service:8000"
            assert settings.mcp_service_url == "http://mcp-service:8000"
            
            # MCP
            assert settings.mcp_enabled is True
            assert settings.mcp_transport == "stdio"
            assert settings.mcp_available_tools == "*"
    
    def test_production_config_with_env_overrides(self, temp_production_config, clear_settings_cache):
        """Test production config with environment variable overrides."""
        with patch.dict(os.environ, {
            _CONFIG_ENV: temp_production_config,
            # Override some production values for different environments
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "postgresql://dev:dev@localhost:5432/privategpt_dev",
            "OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "dev-openai-key",
            "KEYCLOAK_URL": "http://localhost:8180",
            "DEFAULT_ADMIN_EMAIL": "dev@example.com",
            "MCP_ENABLED": "false"
        }):
            # Environment variables should override config file
            assert settings.log_level == "DEBUG"
            assert settings.database_url == "postgresql://dev:dev@localhost:5432/privategpt_dev"
            assert settings.openai_enabled is True
            assert settings.openai_api_key == "dev-openai-key"
            assert settings.keycloak_url == "http://localhost:8180"
            assert settings.default_admin_email == "dev@example.com"
            assert settings.mcp_enabled is False
            
            # Values not overridden should come from config file
            assert settings.ollama_enabled is True
            assert settings.ollama_model == "llama3.2"
            assert settings.keycloak_realm == "privategpt"


class TestDevelopmentConfigScenarios:
    """Test development environment configuration scenarios."""
    
    def test_local_development_config(self, clear_settings_cache):
        """Test configuration for local development environment."""
        dev_config = {
            "log_level": "DEBUG",
            "database_url": "sqlite+aiosqlite:///./dev.db",
            "redis_url": "redis://localhost:6379/0",
            
            "ollama_enabled": True,
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "tinydolphin:latest",
            
            "openai_enabled": True,
            "openai_api_key": "dev-test-key",
            
            "keycloak_url": "http://localhost:8180",
            "default_admin_email": "dev@localhost.com",
            
            "mcp_enabled": True,
            "enable_thinking_mode": True,
            "enable_prompt_caching": False
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(dev_config, f)
            f.flush()
            
            try:
                with patch.dict(os.environ, {_CONFIG_ENV: f.name}):
                    assert settings.log_level == "DEBUG"
                    assert "dev.db" in settings.database_url
                    assert settings.ollama_model == "tinydolphin:latest"
                    assert settings.openai_enabled is True
                    assert settings.enable_thinking_mode is True
                    assert settings.enable_prompt_caching is False
            finally:
                os.unlink(f.name)
    
    def test_docker_development_config(self, clear_settings_cache):
        """Test configuration for Docker development environment."""
        with patch.dict(os.environ, {
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "postgresql://privategpt:secret@db:5432/privategpt",
            "REDIS_URL": "redis://redis:6379/0",
            "WEAVIATE_URL": "http://weaviate:8080",
            
            "OLLAMA_BASE_URL": "http://ollama:11434",
            "KEYCLOAK_URL": "http://keycloak:8080",
            
            "RAG_SERVICE_URL": "http://rag-service:8000",
            "LLM_SERVICE_URL": "http://llm-service:8000",
            
            "ENABLE_THINKING_MODE": "true",
            "ENABLE_PROMPT_CACHING": "false"
        }, clear=True):
            # All URLs should use Docker service names
            assert settings.database_url == "postgresql://privategpt:secret@db:5432/privategpt"
            assert settings.redis_url == "redis://redis:6379/0"
            assert settings.weaviate_url == "http://weaviate:8080"
            assert settings.ollama_base_url == "http://ollama:11434"
            assert settings.keycloak_url == "http://keycloak:8080"
            assert settings.rag_service_url == "http://rag-service:8000"
            assert settings.llm_service_url == "http://llm-service:8000"


class TestMultiProviderConfiguration:
    """Test multi-provider LLM configuration scenarios."""
    
    def test_ollama_only_config(self, clear_settings_cache):
        """Test configuration with only Ollama enabled."""
        with patch.dict(os.environ, {
            "OLLAMA_ENABLED": "true",
            "OLLAMA_MODEL": "llama3.2:7b",
            "OPENAI_ENABLED": "false",
            "ANTHROPIC_ENABLED": "false"
        }, clear=True):
            assert settings.ollama_enabled is True
            assert settings.ollama_model == "llama3.2:7b"
            assert settings.openai_enabled is False
            assert settings.anthropic_enabled is False
    
    def test_cloud_providers_only_config(self, clear_settings_cache):
        """Test configuration with only cloud providers enabled."""
        with patch.dict(os.environ, {
            "OLLAMA_ENABLED": "false",
            "OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "openai-prod-key",
            "OPENAI_MODEL": "gpt-4-turbo",
            "ANTHROPIC_ENABLED": "true",
            "ANTHROPIC_API_KEY": "anthropic-prod-key",
            "ANTHROPIC_MODEL": "claude-3-opus"
        }, clear=True):
            assert settings.ollama_enabled is False
            assert settings.openai_enabled is True
            assert settings.openai_api_key == "openai-prod-key"
            assert settings.openai_model == "gpt-4-turbo"
            assert settings.anthropic_enabled is True
            assert settings.anthropic_api_key == "anthropic-prod-key"
            assert settings.anthropic_model == "claude-3-opus"
    
    def test_all_providers_enabled_config(self, clear_settings_cache):
        """Test configuration with all providers enabled."""
        with patch.dict(os.environ, {
            "OLLAMA_ENABLED": "true",
            "OLLAMA_MODEL": "llama3.2:3b",
            "OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "openai-key",
            "OPENAI_MODEL": "gpt-4",
            "ANTHROPIC_ENABLED": "true",
            "ANTHROPIC_API_KEY": "anthropic-key",
            "ANTHROPIC_MODEL": "claude-3-5-sonnet"
        }, clear=True):
            assert settings.ollama_enabled is True
            assert settings.openai_enabled is True
            assert settings.anthropic_enabled is True
            assert settings.ollama_model == "llama3.2:3b"
            assert settings.openai_model == "gpt-4"
            assert settings.anthropic_model == "claude-3-5-sonnet"


class TestSecurityConfiguration:
    """Test security-related configuration scenarios."""
    
    def test_production_security_config(self, clear_settings_cache):
        """Test production security configuration."""
        with patch.dict(os.environ, {
            "DEFAULT_ADMIN_EMAIL": "admin@company.com",
            "DEFAULT_ADMIN_PASSWORD": "complex-secure-password",
            "KEYCLOAK_URL": "https://auth.company.com",
            "KEYCLOAK_REALM": "production",
            "KEYCLOAK_CLIENT_ID": "privategpt-prod"
        }, clear=True):
            assert settings.default_admin_email == "admin@company.com"
            assert settings.default_admin_password == "complex-secure-password"
            assert settings.keycloak_url == "https://auth.company.com"
            assert settings.keycloak_realm == "production"
            assert settings.keycloak_client_id == "privategpt-prod"
    
    def test_api_key_security_config(self, clear_settings_cache):
        """Test API key configuration for external services."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-1234567890abcdef",
            "ANTHROPIC_API_KEY": "ak-ant-1234567890abcdef"
        }, clear=True):
            assert settings.openai_api_key == "sk-1234567890abcdef"
            assert settings.anthropic_api_key == "ak-ant-1234567890abcdef"
            
            # Ensure keys are not empty when providers are enabled
            if settings.openai_enabled:
                assert len(settings.openai_api_key) > 0
            if settings.anthropic_enabled:
                assert len(settings.anthropic_api_key) > 0


class TestServiceDiscoveryConfiguration:
    """Test service discovery and URL configuration."""
    
    def test_internal_service_urls(self, clear_settings_cache):
        """Test internal service URL configuration."""
        with patch.dict(os.environ, {
            "RAG_SERVICE_URL": "http://rag-service:8000",
            "LLM_SERVICE_URL": "http://llm-service:8000",
            "MCP_SERVICE_URL": "http://mcp-service:8000"
        }, clear=True):
            assert settings.rag_service_url == "http://rag-service:8000"
            assert settings.llm_service_url == "http://llm-service:8000"
            assert settings.mcp_service_url == "http://mcp-service:8000"
    
    def test_external_service_urls(self, clear_settings_cache):
        """Test external service URL configuration."""
        with patch.dict(os.environ, {
            "RAG_SERVICE_URL": "https://rag.company.com",
            "LLM_SERVICE_URL": "https://llm.company.com",
            "KEYCLOAK_URL": "https://auth.company.com",
            "WEAVIATE_URL": "https://vector.company.com"
        }, clear=True):
            assert settings.rag_service_url == "https://rag.company.com"
            assert settings.llm_service_url == "https://llm.company.com"
            assert settings.keycloak_url == "https://auth.company.com"
            assert settings.weaviate_url == "https://vector.company.com"


class TestMCPConfiguration:
    """Test MCP (Model Context Protocol) configuration scenarios."""
    
    def test_mcp_stdio_config(self, clear_settings_cache):
        """Test MCP configuration with STDIO transport."""
        with patch.dict(os.environ, {
            "MCP_ENABLED": "true",
            "MCP_TRANSPORT": "stdio",
            "MCP_AVAILABLE_TOOLS": "*"
        }, clear=True):
            assert settings.mcp_enabled is True
            assert settings.mcp_transport == "stdio"
            assert settings.mcp_available_tools == "*"
    
    def test_mcp_http_config(self, clear_settings_cache):
        """Test MCP configuration with HTTP transport."""
        with patch.dict(os.environ, {
            "MCP_ENABLED": "true",
            "MCP_TRANSPORT": "http",
            "MCP_SERVICE_URL": "http://mcp-server:8080",
            "MCP_AVAILABLE_TOOLS": "search,file_ops,system"
        }, clear=True):
            assert settings.mcp_enabled is True
            assert settings.mcp_transport == "http"
            assert settings.mcp_service_url == "http://mcp-server:8080"
            assert settings.mcp_available_tools == "search,file_ops,system"
    
    def test_mcp_disabled_config(self, clear_settings_cache):
        """Test MCP disabled configuration."""
        with patch.dict(os.environ, {
            "MCP_ENABLED": "false"
        }, clear=True):
            assert settings.mcp_enabled is False


class TestSystemPromptConfiguration:
    """Test system prompt configuration scenarios."""
    
    def test_default_system_prompt_config(self, clear_settings_cache):
        """Test default system prompt configuration."""
        with patch.dict(os.environ, {
            "DEFAULT_SYSTEM_PROMPT": "You are a helpful AI assistant for enterprise use.",
            "ENABLE_PROMPT_CACHING": "true",
            "ENABLE_THINKING_MODE": "false"
        }, clear=True):
            assert settings.default_system_prompt == "You are a helpful AI assistant for enterprise use."
            assert settings.enable_prompt_caching is True
            assert settings.enable_thinking_mode is False
    
    def test_advanced_prompt_config(self, clear_settings_cache):
        """Test advanced prompt configuration."""
        with patch.dict(os.environ, {
            "ENABLE_THINKING_MODE": "true",
            "ENABLE_PROMPT_CACHING": "false"
        }, clear=True):
            assert settings.enable_thinking_mode is True
            assert settings.enable_prompt_caching is False


class TestDatabaseConfiguration:
    """Test database configuration scenarios."""
    
    def test_postgresql_config(self, clear_settings_cache):
        """Test PostgreSQL database configuration."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/privategpt",
            "REDIS_URL": "redis://localhost:6379/0"
        }, clear=True):
            assert "postgresql" in settings.database_url
            assert "5432" in settings.database_url
            assert "redis://localhost:6379/0" == settings.redis_url
    
    def test_sqlite_config(self, clear_settings_cache):
        """Test SQLite database configuration."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "sqlite+aiosqlite:///./test.db"
        }, clear=True):
            assert "sqlite" in settings.database_url
            assert "test.db" in settings.database_url


class TestConfigurationValidation:
    """Test configuration validation scenarios."""
    
    def test_required_fields_present(self, temp_production_config, clear_settings_cache):
        """Test that required configuration fields are present."""
        with patch.dict(os.environ, {_CONFIG_ENV: temp_production_config}):
            # Essential fields should be present
            assert settings.database_url is not None
            assert settings.log_level is not None
            assert settings.keycloak_url is not None
            assert settings.default_admin_email is not None
    
    def test_url_field_validation(self, clear_settings_cache):
        """Test URL field validation and normalization."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "  postgresql://test@localhost/db  ",
            "REDIS_URL": "  redis://localhost:6379  ",
            "KEYCLOAK_URL": "  http://keycloak:8080  "
        }, clear=True):
            # URLs should be stripped of whitespace
            assert settings.database_url == "postgresql://test@localhost/db"
            assert settings.redis_url == "redis://localhost:6379"
            assert settings.keycloak_url == "http://keycloak:8080"


class TestRealWorldScenarios:
    """Test real-world deployment scenarios."""
    
    def test_kubernetes_deployment_config(self, clear_settings_cache):
        """Test configuration for Kubernetes deployment."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://privategpt:secret@postgres-service:5432/privategpt",
            "REDIS_URL": "redis://redis-service:6379/0",
            "WEAVIATE_URL": "http://weaviate-service:8080",
            
            "OLLAMA_BASE_URL": "http://ollama-service:11434",
            "KEYCLOAK_URL": "http://keycloak-service:8080",
            
            "RAG_SERVICE_URL": "http://rag-service:8000",
            "LLM_SERVICE_URL": "http://llm-service:8000",
            
            "LOG_LEVEL": "INFO"
        }, clear=True):
            # All services should use Kubernetes service names
            assert "postgres-service" in settings.database_url
            assert "redis-service" in settings.redis_url
            assert "weaviate-service" in settings.weaviate_url
            assert "ollama-service" in settings.ollama_base_url
            assert "keycloak-service" in settings.keycloak_url
    
    def test_cloud_deployment_config(self, clear_settings_cache):
        """Test configuration for cloud deployment."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@rds.amazonaws.com:5432/privategpt",
            "REDIS_URL": "redis://elasticache.amazonaws.com:6379/0",
            
            "OLLAMA_ENABLED": "false",
            "OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-production-key",
            "ANTHROPIC_ENABLED": "true",
            "ANTHROPIC_API_KEY": "ak-production-key",
            
            "KEYCLOAK_URL": "https://auth.company.com",
            
            "LOG_LEVEL": "WARNING"
        }, clear=True):
            # Should use cloud services
            assert "rds.amazonaws.com" in settings.database_url
            assert "elasticache.amazonaws.com" in settings.redis_url
            assert settings.ollama_enabled is False
            assert settings.openai_enabled is True
            assert settings.anthropic_enabled is True
            assert "https://auth.company.com" == settings.keycloak_url
    
    def test_hybrid_deployment_config(self, clear_settings_cache):
        """Test configuration for hybrid deployment (local + cloud)."""
        with patch.dict(os.environ, {
            "OLLAMA_ENABLED": "true",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            
            "OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-cloud-key",
            
            "DATABASE_URL": "postgresql://local:pass@localhost:5432/privategpt",
            "KEYCLOAK_URL": "https://auth.company.com"
        }, clear=True):
            # Mix of local and cloud services
            assert settings.ollama_enabled is True
            assert "localhost" in settings.ollama_base_url
            assert settings.openai_enabled is True
            assert "localhost" in settings.database_url
            assert "auth.company.com" in settings.keycloak_url