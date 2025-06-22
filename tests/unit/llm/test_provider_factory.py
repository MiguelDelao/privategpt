"""
Tests for the LLM provider factory system.

Tests provider creation, configuration loading, registry setup,
and initialization of the complete multi-provider system.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from privategpt.services.llm.core import LLMPort, ModelInfo
from privategpt.services.llm.core.provider_factory import LLMProviderFactory
from privategpt.services.llm.core.model_registry import ModelRegistry


@pytest.fixture
def mock_settings():
    """Mock settings for provider configuration."""
    settings = MagicMock()
    settings.ollama_enabled = True
    settings.ollama_base_url = "http://ollama:11434"
    settings.ollama_model = "llama3.2"
    
    settings.openai_enabled = True
    settings.openai_api_key = "test-openai-key"
    settings.openai_base_url = "https://api.openai.com/v1"
    settings.openai_model = "gpt-4"
    
    settings.anthropic_enabled = True
    settings.anthropic_api_key = "test-anthropic-key"
    settings.anthropic_base_url = "https://api.anthropic.com"
    settings.anthropic_model = "claude-3-5-sonnet"
    
    return settings


@pytest.fixture
def ollama_config():
    """Sample Ollama provider configuration."""
    return {
        "enabled": True,
        "base_url": "http://localhost:11434",
        "default_model": "llama3.2:3b",
        "timeout": 600.0
    }


@pytest.fixture
def openai_config():
    """Sample OpenAI provider configuration."""
    return {
        "enabled": True,
        "api_key": "sk-test1234567890",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4",
        "timeout": 30.0
    }


@pytest.fixture
def anthropic_config():
    """Sample Anthropic provider configuration."""
    return {
        "enabled": True,
        "api_key": "ak-test1234567890",
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-3-5-sonnet-20241022",
        "timeout": 30.0
    }


class TestOllamaProviderCreation:
    """Test Ollama provider creation."""
    
    @patch('privategpt.services.llm.core.provider_factory.OllamaAdapter')
    def test_create_ollama_provider_success(self, mock_adapter_class, ollama_config):
        """Test successful Ollama provider creation."""
        mock_adapter = AsyncMock(spec=LLMPort)
        mock_adapter_class.return_value = mock_adapter
        
        provider = LLMProviderFactory.create_ollama_provider(ollama_config)
        
        assert provider is mock_adapter
        mock_adapter_class.assert_called_once_with(
            base_url="http://localhost:11434",
            default_model="llama3.2:3b",
            timeout=600.0,
            enabled=True
        )
    
    @patch('privategpt.services.llm.core.provider_factory.OllamaAdapter')
    def test_create_ollama_provider_with_defaults(self, mock_adapter_class):
        """Test Ollama provider creation with default values."""
        mock_adapter = AsyncMock(spec=LLMPort)
        mock_adapter_class.return_value = mock_adapter
        
        provider = LLMProviderFactory.create_ollama_provider({})
        
        assert provider is mock_adapter
        mock_adapter_class.assert_called_once_with(
            base_url="http://localhost:11434",
            default_model="llama3.2",
            timeout=600.0,
            enabled=True
        )
    
    @patch('privategpt.services.llm.core.provider_factory.OllamaAdapter')
    def test_create_ollama_provider_custom_config(self, mock_adapter_class):
        """Test Ollama provider creation with custom configuration."""
        custom_config = {
            "base_url": "http://custom-ollama:9999",
            "default_model": "custom-model",
            "timeout": 300.0,
            "enabled": False
        }
        
        mock_adapter = AsyncMock(spec=LLMPort)
        mock_adapter_class.return_value = mock_adapter
        
        provider = LLMProviderFactory.create_ollama_provider(custom_config)
        
        assert provider is mock_adapter
        mock_adapter_class.assert_called_once_with(
            base_url="http://custom-ollama:9999",
            default_model="custom-model",
            timeout=300.0,
            enabled=False
        )
    
    @patch('privategpt.services.llm.core.provider_factory.OllamaAdapter')
    def test_create_ollama_provider_error(self, mock_adapter_class, ollama_config):
        """Test Ollama provider creation when adapter creation fails."""
        mock_adapter_class.side_effect = Exception("Adapter creation failed")
        
        provider = LLMProviderFactory.create_ollama_provider(ollama_config)
        
        assert provider is None


class TestOpenAIProviderCreation:
    """Test OpenAI provider creation."""
    
    @patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter')
    def test_create_openai_provider_success(self, mock_adapter_class, openai_config):
        """Test successful OpenAI provider creation."""
        mock_adapter = AsyncMock(spec=LLMPort)
        mock_adapter_class.return_value = mock_adapter
        
        provider = LLMProviderFactory.create_openai_provider(openai_config)
        
        assert provider is mock_adapter
        mock_adapter_class.assert_called_once_with(
            api_key="sk-test1234567890",
            base_url="https://api.openai.com/v1",
            default_model="gpt-4",
            timeout=30.0,
            enabled=True
        )
    
    @patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter')
    def test_create_openai_provider_with_defaults(self, mock_adapter_class):
        """Test OpenAI provider creation with default values."""
        config = {"api_key": "test-key"}
        mock_adapter = AsyncMock(spec=LLMPort)
        mock_adapter_class.return_value = mock_adapter
        
        provider = LLMProviderFactory.create_openai_provider(config)
        
        assert provider is mock_adapter
        mock_adapter_class.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            default_model="gpt-4",
            timeout=30.0,
            enabled=True
        )
    
    def test_create_openai_provider_missing_api_key(self):
        """Test OpenAI provider creation without API key."""
        config = {"enabled": True}
        
        provider = LLMProviderFactory.create_openai_provider(config)
        
        assert provider is None
    
    def test_create_openai_provider_empty_api_key(self):
        """Test OpenAI provider creation with empty API key."""
        config = {"api_key": "", "enabled": True}
        
        provider = LLMProviderFactory.create_openai_provider(config)
        
        assert provider is None
    
    @patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter')
    def test_create_openai_provider_custom_config(self, mock_adapter_class):
        """Test OpenAI provider creation with custom configuration."""
        custom_config = {
            "api_key": "custom-key",
            "base_url": "https://custom-openai.com/v1",
            "default_model": "gpt-3.5-turbo",
            "timeout": 60.0,
            "enabled": False
        }
        
        mock_adapter = AsyncMock(spec=LLMPort)
        mock_adapter_class.return_value = mock_adapter
        
        provider = LLMProviderFactory.create_openai_provider(custom_config)
        
        assert provider is mock_adapter
        mock_adapter_class.assert_called_once_with(
            api_key="custom-key",
            base_url="https://custom-openai.com/v1",
            default_model="gpt-3.5-turbo",
            timeout=60.0,
            enabled=False
        )
    
    @patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter')
    def test_create_openai_provider_error(self, mock_adapter_class, openai_config):
        """Test OpenAI provider creation when adapter creation fails."""
        mock_adapter_class.side_effect = Exception("Adapter creation failed")
        
        provider = LLMProviderFactory.create_openai_provider(openai_config)
        
        assert provider is None


class TestAnthropicProviderCreation:
    """Test Anthropic provider creation."""
    
    @patch('privategpt.services.llm.core.provider_factory.AnthropicAdapter')
    def test_create_anthropic_provider_success(self, mock_adapter_class, anthropic_config):
        """Test successful Anthropic provider creation."""
        mock_adapter = AsyncMock(spec=LLMPort)
        mock_adapter_class.return_value = mock_adapter
        
        provider = LLMProviderFactory.create_anthropic_provider(anthropic_config)
        
        assert provider is mock_adapter
        mock_adapter_class.assert_called_once_with(
            api_key="ak-test1234567890",
            base_url="https://api.anthropic.com",
            default_model="claude-3-5-sonnet-20241022",
            timeout=30.0,
            enabled=True
        )
    
    @patch('privategpt.services.llm.core.provider_factory.AnthropicAdapter')
    def test_create_anthropic_provider_with_defaults(self, mock_adapter_class):
        """Test Anthropic provider creation with default values."""
        config = {"api_key": "test-key"}
        mock_adapter = AsyncMock(spec=LLMPort)
        mock_adapter_class.return_value = mock_adapter
        
        provider = LLMProviderFactory.create_anthropic_provider(config)
        
        assert provider is mock_adapter
        mock_adapter_class.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.anthropic.com",
            default_model="claude-3-5-sonnet-20241022",
            timeout=30.0,
            enabled=True
        )
    
    def test_create_anthropic_provider_missing_api_key(self):
        """Test Anthropic provider creation without API key."""
        config = {"enabled": True}
        
        provider = LLMProviderFactory.create_anthropic_provider(config)
        
        assert provider is None
    
    def test_create_anthropic_provider_empty_api_key(self):
        """Test Anthropic provider creation with empty API key."""
        config = {"api_key": "", "enabled": True}
        
        provider = LLMProviderFactory.create_anthropic_provider(config)
        
        assert provider is None
    
    @patch('privategpt.services.llm.core.provider_factory.AnthropicAdapter')
    def test_create_anthropic_provider_custom_config(self, mock_adapter_class):
        """Test Anthropic provider creation with custom configuration."""
        custom_config = {
            "api_key": "custom-anthropic-key",
            "base_url": "https://custom-anthropic.com",
            "default_model": "claude-3-opus",
            "timeout": 45.0,
            "enabled": False
        }
        
        mock_adapter = AsyncMock(spec=LLMPort)
        mock_adapter_class.return_value = mock_adapter
        
        provider = LLMProviderFactory.create_anthropic_provider(custom_config)
        
        assert provider is mock_adapter
        mock_adapter_class.assert_called_once_with(
            api_key="custom-anthropic-key",
            base_url="https://custom-anthropic.com",
            default_model="claude-3-opus",
            timeout=45.0,
            enabled=False
        )
    
    @patch('privategpt.services.llm.core.provider_factory.AnthropicAdapter')
    def test_create_anthropic_provider_error(self, mock_adapter_class, anthropic_config):
        """Test Anthropic provider creation when adapter creation fails."""
        mock_adapter_class.side_effect = Exception("Adapter creation failed")
        
        provider = LLMProviderFactory.create_anthropic_provider(anthropic_config)
        
        assert provider is None


class TestProviderConfigurationFromSettings:
    """Test provider configuration loading from settings."""
    
    @patch('privategpt.services.llm.core.provider_factory.get_model_registry')
    @patch('privategpt.services.llm.core.provider_factory.settings')
    @patch('privategpt.services.llm.core.provider_factory.OllamaAdapter')
    @patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter')
    @patch('privategpt.services.llm.core.provider_factory.AnthropicAdapter')
    def test_setup_providers_from_config_all_enabled(
        self, 
        mock_anthropic_adapter,
        mock_openai_adapter,
        mock_ollama_adapter,
        mock_settings,
        mock_get_registry
    ):
        """Test setting up all providers from configuration."""
        # Mock settings
        mock_settings.ollama_enabled = True
        mock_settings.ollama_base_url = "http://ollama:11434"
        mock_settings.ollama_model = "llama3.2"
        
        mock_settings.openai_enabled = True
        mock_settings.openai_api_key = "openai-key"
        mock_settings.openai_base_url = "https://api.openai.com/v1"
        mock_settings.openai_model = "gpt-4"
        
        mock_settings.anthropic_enabled = True
        mock_settings.anthropic_api_key = "anthropic-key"
        mock_settings.anthropic_base_url = "https://api.anthropic.com"
        mock_settings.anthropic_model = "claude-3-5-sonnet"
        
        # Mock adapters
        mock_ollama_adapter.return_value = AsyncMock(spec=LLMPort)
        mock_openai_adapter.return_value = AsyncMock(spec=LLMPort)
        mock_anthropic_adapter.return_value = AsyncMock(spec=LLMPort)
        
        # Mock registry
        mock_registry = MagicMock(spec=ModelRegistry)
        mock_get_registry.return_value = mock_registry
        
        # Execute
        registry = LLMProviderFactory.setup_providers_from_config()
        
        # Verify all providers were created and registered
        assert mock_ollama_adapter.called
        assert mock_openai_adapter.called
        assert mock_anthropic_adapter.called
        assert mock_registry.register_provider.call_count == 3
        assert registry is mock_registry
    
    @patch('privategpt.services.llm.core.provider_factory.get_model_registry')
    @patch('privategpt.services.llm.core.provider_factory.settings')
    @patch('privategpt.services.llm.core.provider_factory.OllamaAdapter')
    def test_setup_providers_from_config_ollama_only(
        self, 
        mock_ollama_adapter,
        mock_settings,
        mock_get_registry
    ):
        """Test setting up only Ollama provider."""
        # Mock settings - only Ollama enabled
        mock_settings.ollama_enabled = True
        mock_settings.ollama_base_url = "http://ollama:11434"
        mock_settings.ollama_model = "llama3.2"
        
        mock_settings.openai_enabled = False
        mock_settings.openai_api_key = ""
        
        mock_settings.anthropic_enabled = False
        mock_settings.anthropic_api_key = ""
        
        # Mock adapter
        mock_ollama_adapter.return_value = AsyncMock(spec=LLMPort)
        
        # Mock registry
        mock_registry = MagicMock(spec=ModelRegistry)
        mock_get_registry.return_value = mock_registry
        
        # Execute
        registry = LLMProviderFactory.setup_providers_from_config()
        
        # Verify only Ollama was registered
        assert mock_ollama_adapter.called
        assert mock_registry.register_provider.call_count == 1
        mock_registry.register_provider.assert_called_with("ollama", mock_ollama_adapter.return_value)
    
    @patch('privategpt.services.llm.core.provider_factory.get_model_registry')
    @patch('privategpt.services.llm.core.provider_factory.settings')
    def test_setup_providers_from_config_api_key_requirements(self, mock_settings, mock_get_registry):
        """Test that API providers require API keys."""
        # Mock settings - cloud providers enabled but no API keys
        mock_settings.ollama_enabled = False
        
        mock_settings.openai_enabled = True
        mock_settings.openai_api_key = ""  # Empty API key
        
        mock_settings.anthropic_enabled = True
        mock_settings.anthropic_api_key = ""  # Empty API key
        
        # Mock registry
        mock_registry = MagicMock(spec=ModelRegistry)
        mock_get_registry.return_value = mock_registry
        
        # Execute
        registry = LLMProviderFactory.setup_providers_from_config()
        
        # Verify no providers were registered due to missing API keys
        assert mock_registry.register_provider.call_count == 0
    
    @patch('privategpt.services.llm.core.provider_factory.get_model_registry')
    @patch('privategpt.services.llm.core.provider_factory.settings')
    @patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter')
    def test_setup_providers_from_config_provider_creation_error(
        self, 
        mock_openai_adapter,
        mock_settings,
        mock_get_registry
    ):
        """Test handling of provider creation errors."""
        # Mock settings
        mock_settings.ollama_enabled = False
        mock_settings.openai_enabled = True
        mock_settings.openai_api_key = "valid-key"
        mock_settings.openai_base_url = "https://api.openai.com/v1"
        mock_settings.openai_model = "gpt-4"
        mock_settings.anthropic_enabled = False
        mock_settings.anthropic_api_key = ""
        
        # Mock adapter creation to fail
        mock_openai_adapter.side_effect = Exception("Creation failed")
        
        # Mock registry
        mock_registry = MagicMock(spec=ModelRegistry)
        mock_get_registry.return_value = mock_registry
        
        # Execute - should not raise exception
        registry = LLMProviderFactory.setup_providers_from_config()
        
        # Verify no providers were registered due to creation error
        assert mock_registry.register_provider.call_count == 0
        assert registry is mock_registry


class TestRegistryInitialization:
    """Test complete registry initialization."""
    
    @pytest.mark.asyncio
    @patch('privategpt.services.llm.core.provider_factory.LLMProviderFactory.setup_providers_from_config')
    async def test_initialize_model_registry_success(self, mock_setup):
        """Test successful registry initialization."""
        mock_registry = AsyncMock(spec=ModelRegistry)
        mock_setup.return_value = mock_registry
        
        result = await LLMProviderFactory.initialize_model_registry()
        
        assert result is mock_registry
        mock_registry.refresh_models.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('privategpt.services.llm.core.provider_factory.LLMProviderFactory.setup_providers_from_config')
    async def test_initialize_model_registry_refresh_error(self, mock_setup):
        """Test registry initialization when refresh fails."""
        mock_registry = AsyncMock(spec=ModelRegistry)
        mock_registry.refresh_models.side_effect = Exception("Refresh failed")
        mock_setup.return_value = mock_registry
        
        # Should not raise exception
        result = await LLMProviderFactory.initialize_model_registry()
        
        assert result is mock_registry
        mock_registry.refresh_models.assert_called_once()


class TestConfigurationScenarios:
    """Test various configuration scenarios."""
    
    @patch('privategpt.services.llm.core.provider_factory.get_model_registry')
    @patch('privategpt.services.llm.core.provider_factory.settings')
    @patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter')
    @patch('privategpt.services.llm.core.provider_factory.AnthropicAdapter')
    def test_cloud_only_configuration(
        self, 
        mock_anthropic_adapter,
        mock_openai_adapter,
        mock_settings,
        mock_get_registry
    ):
        """Test configuration with only cloud providers."""
        # Mock settings - only cloud providers
        mock_settings.ollama_enabled = False
        
        mock_settings.openai_enabled = True
        mock_settings.openai_api_key = "openai-key"
        mock_settings.openai_base_url = "https://api.openai.com/v1"
        mock_settings.openai_model = "gpt-4"
        
        mock_settings.anthropic_enabled = True
        mock_settings.anthropic_api_key = "anthropic-key"
        mock_settings.anthropic_base_url = "https://api.anthropic.com"
        mock_settings.anthropic_model = "claude-3-5-sonnet"
        
        # Mock adapters
        mock_openai_adapter.return_value = AsyncMock(spec=LLMPort)
        mock_anthropic_adapter.return_value = AsyncMock(spec=LLMPort)
        
        # Mock registry
        mock_registry = MagicMock(spec=ModelRegistry)
        mock_get_registry.return_value = mock_registry
        
        # Execute
        LLMProviderFactory.setup_providers_from_config()
        
        # Verify only cloud providers were registered
        assert mock_registry.register_provider.call_count == 2
        calls = mock_registry.register_provider.call_args_list
        provider_names = [call[0][0] for call in calls]
        assert "openai" in provider_names
        assert "anthropic" in provider_names
        assert "ollama" not in provider_names
    
    @patch('privategpt.services.llm.core.provider_factory.get_model_registry')
    @patch('privategpt.services.llm.core.provider_factory.settings')
    def test_no_providers_enabled(self, mock_settings, mock_get_registry):
        """Test configuration with no providers enabled."""
        # Mock settings - all providers disabled
        mock_settings.ollama_enabled = False
        mock_settings.openai_enabled = False
        mock_settings.openai_api_key = ""
        mock_settings.anthropic_enabled = False
        mock_settings.anthropic_api_key = ""
        
        # Mock registry
        mock_registry = MagicMock(spec=ModelRegistry)
        mock_get_registry.return_value = mock_registry
        
        # Execute
        LLMProviderFactory.setup_providers_from_config()
        
        # Verify no providers were registered
        assert mock_registry.register_provider.call_count == 0
    
    @patch('privategpt.services.llm.core.provider_factory.get_model_registry')
    @patch('privategpt.services.llm.core.provider_factory.settings')
    @patch('privategpt.services.llm.core.provider_factory.OllamaAdapter')
    @patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter')
    def test_mixed_success_failure_configuration(
        self, 
        mock_openai_adapter,
        mock_ollama_adapter,
        mock_settings,
        mock_get_registry
    ):
        """Test configuration where some providers succeed and others fail."""
        # Mock settings
        mock_settings.ollama_enabled = True
        mock_settings.ollama_base_url = "http://ollama:11434"
        mock_settings.ollama_model = "llama3.2"
        
        mock_settings.openai_enabled = True
        mock_settings.openai_api_key = "openai-key"
        mock_settings.openai_base_url = "https://api.openai.com/v1"
        mock_settings.openai_model = "gpt-4"
        
        mock_settings.anthropic_enabled = False
        mock_settings.anthropic_api_key = ""
        
        # Mock adapters - Ollama succeeds, OpenAI fails
        mock_ollama_adapter.return_value = AsyncMock(spec=LLMPort)
        mock_openai_adapter.return_value = None  # Simulate creation failure
        
        # Mock registry
        mock_registry = MagicMock(spec=ModelRegistry)
        mock_get_registry.return_value = mock_registry
        
        # Execute
        LLMProviderFactory.setup_providers_from_config()
        
        # Verify only successful provider was registered
        assert mock_registry.register_provider.call_count == 1
        mock_registry.register_provider.assert_called_with("ollama", mock_ollama_adapter.return_value)


class TestProviderConfigurationValidation:
    """Test validation of provider configurations."""
    
    def test_ollama_config_validation(self):
        """Test Ollama configuration validation."""
        # Valid config
        valid_config = {
            "enabled": True,
            "base_url": "http://localhost:11434",
            "default_model": "llama3.2",
            "timeout": 600.0
        }
        
        with patch('privategpt.services.llm.core.provider_factory.OllamaAdapter') as mock_adapter:
            mock_adapter.return_value = AsyncMock(spec=LLMPort)
            provider = LLMProviderFactory.create_ollama_provider(valid_config)
            assert provider is not None
    
    def test_openai_config_validation(self):
        """Test OpenAI configuration validation."""
        # Valid config
        valid_config = {
            "enabled": True,
            "api_key": "sk-valid-key",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4",
            "timeout": 30.0
        }
        
        with patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter') as mock_adapter:
            mock_adapter.return_value = AsyncMock(spec=LLMPort)
            provider = LLMProviderFactory.create_openai_provider(valid_config)
            assert provider is not None
        
        # Invalid config - missing API key
        invalid_config = {
            "enabled": True,
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4"
        }
        
        provider = LLMProviderFactory.create_openai_provider(invalid_config)
        assert provider is None
    
    def test_anthropic_config_validation(self):
        """Test Anthropic configuration validation."""
        # Valid config
        valid_config = {
            "enabled": True,
            "api_key": "ak-valid-key",
            "base_url": "https://api.anthropic.com",
            "default_model": "claude-3-5-sonnet",
            "timeout": 30.0
        }
        
        with patch('privategpt.services.llm.core.provider_factory.AnthropicAdapter') as mock_adapter:
            mock_adapter.return_value = AsyncMock(spec=LLMPort)
            provider = LLMProviderFactory.create_anthropic_provider(valid_config)
            assert provider is not None
        
        # Invalid config - missing API key
        invalid_config = {
            "enabled": True,
            "base_url": "https://api.anthropic.com",
            "default_model": "claude-3-5-sonnet"
        }
        
        provider = LLMProviderFactory.create_anthropic_provider(invalid_config)
        assert provider is None


class TestFactoryErrorHandling:
    """Test error handling in the factory."""
    
    def test_create_provider_with_invalid_config_type(self):
        """Test factory with invalid configuration types."""
        # Should handle None config gracefully
        provider = LLMProviderFactory.create_ollama_provider(None)
        assert provider is None
        
        # Should handle non-dict config gracefully
        provider = LLMProviderFactory.create_openai_provider("invalid")
        assert provider is None
    
    @patch('privategpt.services.llm.core.provider_factory.OllamaAdapter')
    def test_adapter_import_error(self, mock_adapter_class):
        """Test handling of adapter import/creation errors."""
        mock_adapter_class.side_effect = ImportError("Adapter not available")
        
        config = {"enabled": True, "base_url": "http://localhost:11434"}
        provider = LLMProviderFactory.create_ollama_provider(config)
        
        assert provider is None
    
    @patch('privategpt.services.llm.core.provider_factory.get_model_registry')
    def test_registry_access_error(self, mock_get_registry):
        """Test handling of registry access errors."""
        mock_get_registry.side_effect = Exception("Registry error")
        
        # Should handle registry errors gracefully
        with pytest.raises(Exception, match="Registry error"):
            LLMProviderFactory.setup_providers_from_config()