"""
Tests for the settings and configuration system.

Tests config file loading, environment variable overrides, validation,
and the complete configuration hierarchy for all LLM providers and services.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest

from privategpt.shared.settings import (
    _read_config_file,
    _CoreSettings,
    _LazySettings,
    settings,
    _instance,
    _CONFIG_ENV,
    _DEFAULT_CONFIG_FILE
)


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_data = {
            "log_level": "DEBUG",
            "database_url": "postgresql://test:test@localhost:5432/test",
            "ollama_enabled": True,
            "ollama_model": "test-model",
            "openai_enabled": False,
            "keycloak_url": "http://test-keycloak:8080",
            "default_admin_email": "test@example.com",
            "system_prompts": {
                "default": "Test system prompt"
            }
        }
        json.dump(config_data, f)
        f.flush()
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def temp_invalid_config_file():
    """Create a temporary invalid JSON config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"invalid": json content}')  # Invalid JSON
        f.flush()
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def clear_settings_cache():
    """Clear the settings cache before and after test."""
    # Clear cache before test
    _instance.cache_clear()
    yield
    # Clear cache after test
    _instance.cache_clear()


class TestConfigFileLoading:
    """Test configuration file loading functionality."""
    
    def test_read_config_file_valid(self, temp_config_file, clear_settings_cache):
        """Test reading a valid config file."""
        with patch.dict(os.environ, {_CONFIG_ENV: temp_config_file}):
            config = _read_config_file()
            
            assert config["log_level"] == "DEBUG"
            assert config["database_url"] == "postgresql://test:test@localhost:5432/test"
            assert config["ollama_enabled"] is True
            assert config["system_prompts"]["default"] == "Test system prompt"
    
    def test_read_config_file_nonexistent(self, clear_settings_cache):
        """Test reading a non-existent config file."""
        with patch.dict(os.environ, {_CONFIG_ENV: "/nonexistent/config.json"}):
            config = _read_config_file()
            assert config == {}
    
    def test_read_config_file_invalid_json(self, temp_invalid_config_file, clear_settings_cache):
        """Test reading an invalid JSON config file."""
        with patch.dict(os.environ, {_CONFIG_ENV: temp_invalid_config_file}):
            config = _read_config_file()
            assert config == {}  # Should return empty dict on parse error
    
    def test_read_config_file_default_location(self, clear_settings_cache):
        """Test reading config from default location."""
        # Create a temporary config.json in current directory
        default_config = {
            "log_level": "WARNING",
            "test_setting": "default_value"
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            with open(config_path, 'w') as f:
                json.dump(default_config, f)
            
            with patch('privategpt.shared.settings.Path') as mock_path:
                mock_path.return_value.expanduser.return_value.resolve.return_value = config_path
                mock_path.return_value.expanduser.return_value.resolve.return_value.exists.return_value = True
                
                config = _read_config_file()
                assert config["log_level"] == "WARNING"
                assert config["test_setting"] == "default_value"
    
    def test_config_file_key_case_normalization(self, clear_settings_cache):
        """Test that config file keys are normalized to lowercase."""
        config_data = {
            "LOG_LEVEL": "ERROR",
            "Database_URL": "test://db",
            "Keycloak": {
                "URL": "http://keycloak",
                "Realm": "test"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            try:
                with patch.dict(os.environ, {_CONFIG_ENV: f.name}):
                    config = _read_config_file()
                    
                    assert config["log_level"] == "ERROR"
                    assert config["database_url"] == "test://db"
                    assert config["keycloak"]["url"] == "http://keycloak"
                    assert config["keycloak"]["realm"] == "test"
            finally:
                os.unlink(f.name)


class TestCoreSettings:
    """Test the _CoreSettings Pydantic model."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        settings_obj = _CoreSettings()
        
        # Test default values
        assert settings_obj.log_level == "INFO"
        assert settings_obj.database_url == "sqlite+aiosqlite:///./privategpt.db"
        assert settings_obj.redis_url == "redis://redis:6379/0"
        assert settings_obj.ollama_enabled is True
        assert settings_obj.openai_enabled is False
        assert settings_obj.anthropic_enabled is False
        assert settings_obj.keycloak_url == "http://keycloak:8080"
        assert settings_obj.default_admin_email == "admin@admin.com"
        assert settings_obj.mcp_enabled is True
    
    def test_initialization_with_values(self):
        """Test initialization with custom values."""
        custom_values = {
            "log_level": "DEBUG",
            "database_url": "postgresql://custom:db@localhost/test",
            "ollama_enabled": False,
            "openai_enabled": True,
            "openai_api_key": "test-key",
            "keycloak_url": "http://custom-keycloak:9090",
            "default_admin_email": "custom@example.com"
        }
        
        settings_obj = _CoreSettings(**custom_values)
        
        assert settings_obj.log_level == "DEBUG"
        assert settings_obj.database_url == "postgresql://custom:db@localhost/test"
        assert settings_obj.ollama_enabled is False
        assert settings_obj.openai_enabled is True
        assert settings_obj.openai_api_key == "test-key"
        assert settings_obj.keycloak_url == "http://custom-keycloak:9090"
        assert settings_obj.default_admin_email == "custom@example.com"
    
    def test_field_validation_stripping(self):
        """Test that string fields are properly stripped of whitespace."""
        settings_obj = _CoreSettings(
            database_url="  postgresql://test  ",
            redis_url="  redis://localhost  ",
            llm_base_url="  http://ollama:11434  "
        )
        
        assert settings_obj.database_url == "postgresql://test"
        assert settings_obj.redis_url == "redis://localhost"
        assert settings_obj.llm_base_url == "http://ollama:11434"
    
    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed due to model config."""
        custom_values = {
            "custom_field": "custom_value",
            "another_field": 123
        }
        
        settings_obj = _CoreSettings(**custom_values)
        
        # Extra fields should be accessible
        assert settings_obj.custom_field == "custom_value"
        assert settings_obj.another_field == 123


class TestEnvironmentVariableOverrides:
    """Test environment variable override functionality."""
    
    def test_env_var_overrides_config_file(self, temp_config_file, clear_settings_cache):
        """Test that environment variables override config file values."""
        with patch.dict(os.environ, {
            _CONFIG_ENV: temp_config_file,
            "LOG_LEVEL": "ERROR",  # Should override config file DEBUG
            "OLLAMA_ENABLED": "false",  # Should override config file true
            "OPENAI_API_KEY": "env-override-key"
        }):
            settings_obj = _LazySettings()
            
            assert settings_obj.log_level == "ERROR"  # From env var
            assert settings_obj.ollama_enabled is False  # From env var
            assert settings_obj.openai_api_key == "env-override-key"  # From env var
            assert settings_obj.database_url == "postgresql://test:test@localhost:5432/test"  # From config file
    
    def test_env_var_only(self, clear_settings_cache):
        """Test settings with only environment variables (no config file)."""
        with patch.dict(os.environ, {
            "LOG_LEVEL": "WARNING",
            "DATABASE_URL": "sqlite:///env-test.db",
            "OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "env-key",
            "KEYCLOAK_URL": "http://env-keycloak:8080"
        }, clear=True):
            settings_obj = _LazySettings()
            
            assert settings_obj.log_level == "WARNING"
            assert settings_obj.database_url == "sqlite:///env-test.db"
            assert settings_obj.openai_enabled is True
            assert settings_obj.openai_api_key == "env-key"
            assert settings_obj.keycloak_url == "http://env-keycloak:8080"
    
    def test_boolean_env_var_parsing(self, clear_settings_cache):
        """Test that boolean environment variables are parsed correctly."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("", False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"OLLAMA_ENABLED": env_value}, clear=True):
                settings_obj = _LazySettings()
                assert settings_obj.ollama_enabled is expected, f"Failed for env_value: {env_value}"


class TestLazySettings:
    """Test the _LazySettings wrapper class."""
    
    def test_dotted_key_access(self, temp_config_file, clear_settings_cache):
        """Test accessing config values using dotted key notation."""
        with patch.dict(os.environ, {_CONFIG_ENV: temp_config_file}):
            settings_obj = _LazySettings()
            
            # Test basic dotted access
            assert settings_obj.get("log_level") == "DEBUG"
            assert settings_obj.get("database_url") == "postgresql://test:test@localhost:5432/test"
            
            # Test nested dotted access
            assert settings_obj.get("system_prompts.default") == "Test system prompt"
            
            # Test default values
            assert settings_obj.get("nonexistent.key", "default_value") == "default_value"
            assert settings_obj.get("nonexistent.key") is None
    
    def test_dotted_key_env_var_override(self, temp_config_file, clear_settings_cache):
        """Test that environment variables override dotted key access."""
        with patch.dict(os.environ, {
            _CONFIG_ENV: temp_config_file,
            "SYSTEM_PROMPTS_DEFAULT": "Env override prompt"
        }):
            settings_obj = _LazySettings()
            
            # Environment variable should override config file
            assert settings_obj.get("system_prompts.default") == "Env override prompt"
    
    def test_attribute_access(self, clear_settings_cache):
        """Test accessing settings as attributes."""
        with patch.dict(os.environ, {
            "LOG_LEVEL": "DEBUG",
            "OLLAMA_ENABLED": "true"
        }, clear=True):
            settings_obj = _LazySettings()
            
            assert settings_obj.log_level == "DEBUG"
            assert settings_obj.ollama_enabled is True
    
    def test_attribute_access_missing(self, clear_settings_cache):
        """Test accessing non-existent attributes raises AttributeError."""
        settings_obj = _LazySettings()
        
        with pytest.raises(AttributeError):
            _ = settings_obj.nonexistent_attribute
    
    def test_case_insensitive_dotted_access(self, clear_settings_cache):
        """Test that dotted key access is case insensitive."""
        config_data = {
            "TestSection": {
                "TestKey": "test_value"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            try:
                with patch.dict(os.environ, {_CONFIG_ENV: f.name}):
                    settings_obj = _LazySettings()
                    
                    # All these should work due to case insensitive access
                    assert settings_obj.get("testsection.testkey") == "test_value"
                    assert settings_obj.get("TestSection.TestKey") == "test_value"
                    assert settings_obj.get("TESTSECTION.TESTKEY") == "test_value"
            finally:
                os.unlink(f.name)


class TestProviderConfiguration:
    """Test LLM provider specific configuration."""
    
    def test_ollama_configuration(self, clear_settings_cache):
        """Test Ollama provider configuration."""
        with patch.dict(os.environ, {
            "OLLAMA_ENABLED": "true",
            "OLLAMA_BASE_URL": "http://custom-ollama:11434",
            "OLLAMA_MODEL": "custom-model"
        }, clear=True):
            settings_obj = _LazySettings()
            
            assert settings_obj.ollama_enabled is True
            assert settings_obj.ollama_base_url == "http://custom-ollama:11434"
            assert settings_obj.ollama_model == "custom-model"
    
    def test_openai_configuration(self, clear_settings_cache):
        """Test OpenAI provider configuration."""
        with patch.dict(os.environ, {
            "OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "test-openai-key",
            "OPENAI_BASE_URL": "https://custom-openai-api.com/v1",
            "OPENAI_MODEL": "gpt-4-custom"
        }, clear=True):
            settings_obj = _LazySettings()
            
            assert settings_obj.openai_enabled is True
            assert settings_obj.openai_api_key == "test-openai-key"
            assert settings_obj.openai_base_url == "https://custom-openai-api.com/v1"
            assert settings_obj.openai_model == "gpt-4-custom"
    
    def test_anthropic_configuration(self, clear_settings_cache):
        """Test Anthropic provider configuration."""
        with patch.dict(os.environ, {
            "ANTHROPIC_ENABLED": "true",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "ANTHROPIC_BASE_URL": "https://custom-anthropic-api.com",
            "ANTHROPIC_MODEL": "claude-3-opus"
        }, clear=True):
            settings_obj = _LazySettings()
            
            assert settings_obj.anthropic_enabled is True
            assert settings_obj.anthropic_api_key == "test-anthropic-key"
            assert settings_obj.anthropic_base_url == "https://custom-anthropic-api.com"
            assert settings_obj.anthropic_model == "claude-3-opus"
    
    def test_multi_provider_configuration(self, clear_settings_cache):
        """Test configuration with multiple providers enabled."""
        with patch.dict(os.environ, {
            "OLLAMA_ENABLED": "true",
            "OPENAI_ENABLED": "true",
            "ANTHROPIC_ENABLED": "true",
            "OPENAI_API_KEY": "openai-key",
            "ANTHROPIC_API_KEY": "anthropic-key"
        }, clear=True):
            settings_obj = _LazySettings()
            
            assert settings_obj.ollama_enabled is True
            assert settings_obj.openai_enabled is True
            assert settings_obj.anthropic_enabled is True
            assert settings_obj.openai_api_key == "openai-key"
            assert settings_obj.anthropic_api_key == "anthropic-key"


class TestServiceConfiguration:
    """Test service-specific configuration."""
    
    def test_keycloak_configuration(self, clear_settings_cache):
        """Test Keycloak authentication configuration."""
        with patch.dict(os.environ, {
            "KEYCLOAK_URL": "http://custom-keycloak:9090",
            "KEYCLOAK_REALM": "custom-realm",
            "KEYCLOAK_CLIENT_ID": "custom-client"
        }, clear=True):
            settings_obj = _LazySettings()
            
            assert settings_obj.keycloak_url == "http://custom-keycloak:9090"
            assert settings_obj.keycloak_realm == "custom-realm"
            assert settings_obj.keycloak_client_id == "custom-client"
    
    def test_admin_user_configuration(self, clear_settings_cache):
        """Test default admin user configuration."""
        with patch.dict(os.environ, {
            "DEFAULT_ADMIN_EMAIL": "custom@admin.com",
            "DEFAULT_ADMIN_USERNAME": "customadmin",
            "DEFAULT_ADMIN_PASSWORD": "custompass",
            "DEFAULT_ADMIN_FIRST_NAME": "Custom",
            "DEFAULT_ADMIN_LAST_NAME": "Admin"
        }, clear=True):
            settings_obj = _LazySettings()
            
            assert settings_obj.default_admin_email == "custom@admin.com"
            assert settings_obj.default_admin_username == "customadmin"
            assert settings_obj.default_admin_password == "custompass"
            assert settings_obj.default_admin_first_name == "Custom"
            assert settings_obj.default_admin_last_name == "Admin"
    
    def test_service_urls_configuration(self, clear_settings_cache):
        """Test service URL configuration."""
        with patch.dict(os.environ, {
            "RAG_SERVICE_URL": "http://custom-rag:8080",
            "LLM_SERVICE_URL": "http://custom-llm:8080",
            "MCP_SERVICE_URL": "http://custom-mcp:8080"
        }, clear=True):
            settings_obj = _LazySettings()
            
            assert settings_obj.rag_service_url == "http://custom-rag:8080"
            assert settings_obj.llm_service_url == "http://custom-llm:8080"
            assert settings_obj.mcp_service_url == "http://custom-mcp:8080"
    
    def test_mcp_configuration(self, clear_settings_cache):
        """Test MCP (Model Context Protocol) configuration."""
        with patch.dict(os.environ, {
            "MCP_ENABLED": "false",
            "MCP_TRANSPORT": "http",
            "MCP_AVAILABLE_TOOLS": "search,file_ops"
        }, clear=True):
            settings_obj = _LazySettings()
            
            assert settings_obj.mcp_enabled is False
            assert settings_obj.mcp_transport == "http"
            assert settings_obj.mcp_available_tools == "search,file_ops"


class TestGlobalSettingsInstance:
    """Test the global settings singleton."""
    
    def test_settings_singleton(self, clear_settings_cache):
        """Test that settings is a singleton instance."""
        # Multiple calls should return the same instance
        settings1 = _instance()
        settings2 = _instance()
        
        assert settings1 is settings2
    
    def test_global_settings_instance(self, clear_settings_cache):
        """Test the global settings instance."""
        # The global settings object should be accessible
        assert hasattr(settings, 'log_level')
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'ollama_enabled')
    
    def test_settings_caching(self, clear_settings_cache):
        """Test that settings are cached properly."""
        # First access
        log_level1 = settings.log_level
        
        # Second access should use cached value
        log_level2 = settings.log_level
        
        assert log_level1 == log_level2


class TestConfigurationHierarchy:
    """Test the complete configuration hierarchy."""
    
    def test_hierarchy_precedence(self, temp_config_file, clear_settings_cache):
        """Test that environment variables take precedence over config file."""
        # Config file has log_level: "DEBUG"
        # Environment variable should override
        with patch.dict(os.environ, {
            _CONFIG_ENV: temp_config_file,
            "LOG_LEVEL": "ERROR"  # This should win
        }):
            settings_obj = _LazySettings()
            
            # Environment variable should take precedence
            assert settings_obj.log_level == "ERROR"
            
            # Dotted access should also respect environment variable
            assert settings_obj.get("log_level") == "ERROR"
    
    def test_fallback_to_defaults(self, clear_settings_cache):
        """Test fallback to default values when no config file or env vars."""
        # Clear all relevant environment variables
        env_to_clear = [
            "LOG_LEVEL", "DATABASE_URL", "OLLAMA_ENABLED", "OPENAI_ENABLED",
            "KEYCLOAK_URL", "DEFAULT_ADMIN_EMAIL", _CONFIG_ENV
        ]
        
        with patch.dict(os.environ, {}, clear=True):
            # Mock config file as non-existent
            with patch('privategpt.shared.settings.Path') as mock_path:
                mock_path.return_value.expanduser.return_value.resolve.return_value.exists.return_value = False
                
                settings_obj = _LazySettings()
                
                # Should use default values
                assert settings_obj.log_level == "INFO"
                assert settings_obj.database_url == "sqlite+aiosqlite:///./privategpt.db"
                assert settings_obj.ollama_enabled is True
                assert settings_obj.openai_enabled is False
    
    def test_partial_override(self, temp_config_file, clear_settings_cache):
        """Test partial override where some values come from config, others from env."""
        with patch.dict(os.environ, {
            _CONFIG_ENV: temp_config_file,
            "OPENAI_ENABLED": "true",  # Override config file
            "OPENAI_API_KEY": "env-key"  # New value not in config
        }):
            settings_obj = _LazySettings()
            
            # From config file
            assert settings_obj.log_level == "DEBUG"
            assert settings_obj.ollama_enabled is True
            
            # From environment variable (override)
            assert settings_obj.openai_enabled is True
            
            # From environment variable (new)
            assert settings_obj.openai_api_key == "env-key"


class TestErrorHandling:
    """Test error handling in configuration system."""
    
    def test_missing_config_file_graceful(self, clear_settings_cache):
        """Test that missing config file is handled gracefully."""
        with patch.dict(os.environ, {_CONFIG_ENV: "/completely/nonexistent/path.json"}):
            # Should not raise exception
            config = _read_config_file()
            assert config == {}
            
            # Settings should still work with defaults
            settings_obj = _LazySettings()
            assert settings_obj.log_level == "INFO"  # Default value
    
    def test_permission_denied_config_file(self, clear_settings_cache):
        """Test handling of config file with permission issues."""
        # This simulates a permission denied error when reading config
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            config = _read_config_file()
            assert config == {}
    
    def test_invalid_json_graceful(self, temp_invalid_config_file, clear_settings_cache):
        """Test that invalid JSON is handled gracefully."""
        with patch.dict(os.environ, {_CONFIG_ENV: temp_invalid_config_file}):
            config = _read_config_file()
            assert config == {}
            
            # Settings should still work
            settings_obj = _LazySettings()
            assert settings_obj.log_level == "INFO"


class TestSpecialCases:
    """Test special cases and edge conditions."""
    
    def test_empty_config_file(self, clear_settings_cache):
        """Test handling of empty config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({}, f)  # Empty JSON object
            f.flush()
            
            try:
                with patch.dict(os.environ, {_CONFIG_ENV: f.name}):
                    config = _read_config_file()
                    assert config == {}
                    
                    settings_obj = _LazySettings()
                    assert settings_obj.log_level == "INFO"  # Should use defaults
            finally:
                os.unlink(f.name)
    
    def test_null_values_in_config(self, clear_settings_cache):
        """Test handling of null values in config file."""
        config_data = {
            "log_level": None,
            "database_url": "postgresql://test",
            "openai_api_key": None
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            try:
                with patch.dict(os.environ, {_CONFIG_ENV: f.name}):
                    settings_obj = _LazySettings()
                    
                    # Should handle null values appropriately
                    assert settings_obj.database_url == "postgresql://test"
            finally:
                os.unlink(f.name)
    
    def test_deeply_nested_config_access(self, clear_settings_cache):
        """Test accessing deeply nested configuration values."""
        config_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "deep_value": "found_it"
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            try:
                with patch.dict(os.environ, {_CONFIG_ENV: f.name}):
                    settings_obj = _LazySettings()
                    
                    assert settings_obj.get("level1.level2.level3.deep_value") == "found_it"
                    assert settings_obj.get("level1.level2.nonexistent", "default") == "default"
            finally:
                os.unlink(f.name)