"""
Tests for the LLM model registry system.

Tests model registration, provider routing, conflict resolution, 
health checking, and all multi-provider coordination functionality.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import AsyncIterator, List

from privategpt.services.llm.core import LLMPort, ModelInfo
from privategpt.services.llm.core.model_registry import (
    ModelRegistry,
    get_model_registry,
    set_model_registry
)


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = AsyncMock(spec=LLMPort)
    provider.get_provider_name.return_value = "test_provider"
    provider.get_provider_type.return_value = "api"
    provider.is_enabled.return_value = True
    provider.health_check.return_value = True
    return provider


@pytest.fixture
def mock_ollama_provider():
    """Create a mock Ollama provider."""
    provider = AsyncMock(spec=LLMPort)
    provider.get_provider_name.return_value = "ollama"
    provider.get_provider_type.return_value = "local"
    provider.is_enabled.return_value = True
    provider.health_check.return_value = True
    provider.get_available_models.return_value = [
        ModelInfo(
            name="llama3.2:3b",
            provider="ollama",
            type="local",
            description="Llama 3.2 3B model",
            context_length=4096,
            parameter_size="3B"
        ),
        ModelInfo(
            name="mistral:7b",
            provider="ollama", 
            type="local",
            description="Mistral 7B model",
            context_length=8192,
            parameter_size="7B"
        )
    ]
    return provider


@pytest.fixture
def mock_openai_provider():
    """Create a mock OpenAI provider."""
    provider = AsyncMock(spec=LLMPort)
    provider.get_provider_name.return_value = "openai"
    provider.get_provider_type.return_value = "api"
    provider.is_enabled.return_value = True
    provider.health_check.return_value = True
    provider.get_available_models.return_value = [
        ModelInfo(
            name="gpt-4",
            provider="openai",
            type="api",
            description="GPT-4 model",
            context_length=8192,
            cost_per_token=0.00003
        ),
        ModelInfo(
            name="gpt-3.5-turbo",
            provider="openai",
            type="api", 
            description="GPT-3.5 Turbo model",
            context_length=4096,
            cost_per_token=0.000002
        )
    ]
    return provider


@pytest.fixture
def mock_anthropic_provider():
    """Create a mock Anthropic provider."""
    provider = AsyncMock(spec=LLMPort)
    provider.get_provider_name.return_value = "anthropic"
    provider.get_provider_type.return_value = "api"
    provider.is_enabled.return_value = True
    provider.health_check.return_value = True
    provider.get_available_models.return_value = [
        ModelInfo(
            name="claude-3-5-sonnet",
            provider="anthropic",
            type="api",
            description="Claude 3.5 Sonnet model",
            context_length=200000,
            cost_per_token=0.000015
        )
    ]
    return provider


@pytest.fixture
def registry():
    """Create a fresh model registry for testing."""
    return ModelRegistry()


@pytest.fixture
def sample_messages():
    """Sample chat messages for testing."""
    return [
        {"role": "user", "content": "Hello, how are you?"}
    ]


class TestModelRegistryBasics:
    """Test basic model registry functionality."""
    
    def test_registry_initialization(self, registry):
        """Test that registry initializes correctly."""
        assert isinstance(registry.providers, dict)
        assert isinstance(registry.model_to_provider, dict)
        assert len(registry.providers) == 0
        assert len(registry.model_to_provider) == 0
        assert registry.last_refresh is None
    
    def test_register_provider(self, registry, mock_provider):
        """Test registering a provider."""
        registry.register_provider("test", mock_provider)
        
        assert "test" in registry.providers
        assert registry.providers["test"] is mock_provider
        assert len(registry.model_to_provider) == 0  # Models not loaded yet
        assert registry.last_refresh is None
    
    def test_register_multiple_providers(self, registry, mock_ollama_provider, mock_openai_provider):
        """Test registering multiple providers."""
        registry.register_provider("ollama", mock_ollama_provider)
        registry.register_provider("openai", mock_openai_provider)
        
        assert len(registry.providers) == 2
        assert "ollama" in registry.providers
        assert "openai" in registry.providers
    
    def test_unregister_provider(self, registry, mock_provider):
        """Test unregistering a provider."""
        registry.register_provider("test", mock_provider)
        assert "test" in registry.providers
        
        result = registry.unregister_provider("test")
        assert result is True
        assert "test" not in registry.providers
    
    def test_unregister_nonexistent_provider(self, registry):
        """Test unregistering a provider that doesn't exist."""
        result = registry.unregister_provider("nonexistent")
        assert result is False
    
    def test_get_registered_providers(self, registry, mock_ollama_provider, mock_openai_provider):
        """Test getting list of registered providers."""
        assert registry.get_registered_providers() == []
        
        registry.register_provider("ollama", mock_ollama_provider)
        registry.register_provider("openai", mock_openai_provider)
        
        providers = registry.get_registered_providers()
        assert len(providers) == 2
        assert "ollama" in providers
        assert "openai" in providers


class TestProviderEnabling:
    """Test provider enabling and disabling functionality."""
    
    @pytest.mark.asyncio
    async def test_get_enabled_providers_all_enabled(self, registry, mock_ollama_provider, mock_openai_provider):
        """Test getting enabled providers when all are enabled."""
        registry.register_provider("ollama", mock_ollama_provider)
        registry.register_provider("openai", mock_openai_provider)
        
        enabled = await registry.get_enabled_providers()
        assert len(enabled) == 2
        assert "ollama" in enabled
        assert "openai" in enabled
    
    @pytest.mark.asyncio
    async def test_get_enabled_providers_some_disabled(self, registry, mock_ollama_provider, mock_openai_provider):
        """Test getting enabled providers when some are disabled."""
        mock_ollama_provider.is_enabled.return_value = True
        mock_openai_provider.is_enabled.return_value = False
        
        registry.register_provider("ollama", mock_ollama_provider)
        registry.register_provider("openai", mock_openai_provider)
        
        enabled = await registry.get_enabled_providers()
        assert len(enabled) == 1
        assert "ollama" in enabled
        assert "openai" not in enabled
    
    @pytest.mark.asyncio
    async def test_get_enabled_providers_with_errors(self, registry, mock_provider):
        """Test getting enabled providers when some providers throw errors."""
        mock_provider.is_enabled.side_effect = Exception("Provider error")
        registry.register_provider("error_provider", mock_provider)
        
        enabled = await registry.get_enabled_providers()
        assert len(enabled) == 0


class TestModelRefresh:
    """Test model refresh functionality."""
    
    @pytest.mark.asyncio
    async def test_refresh_models_single_provider(self, registry, mock_ollama_provider):
        """Test refreshing models from a single provider."""
        registry.register_provider("ollama", mock_ollama_provider)
        
        await registry.refresh_models()
        
        assert len(registry.model_to_provider) == 2
        assert registry.model_to_provider["llama3.2:3b"] == "ollama"
        assert registry.model_to_provider["mistral:7b"] == "ollama"
        assert registry.last_refresh is not None
    
    @pytest.mark.asyncio
    async def test_refresh_models_multiple_providers(self, registry, mock_ollama_provider, mock_openai_provider):
        """Test refreshing models from multiple providers."""
        registry.register_provider("ollama", mock_ollama_provider)
        registry.register_provider("openai", mock_openai_provider)
        
        await registry.refresh_models()
        
        assert len(registry.model_to_provider) == 4
        assert registry.model_to_provider["llama3.2:3b"] == "ollama"
        assert registry.model_to_provider["mistral:7b"] == "ollama"
        assert registry.model_to_provider["gpt-4"] == "openai"
        assert registry.model_to_provider["gpt-3.5-turbo"] == "openai"
    
    @pytest.mark.asyncio
    async def test_refresh_models_with_conflicts(self, registry):
        """Test model refresh with conflicting model names from different providers."""
        # Create two providers with the same model name
        provider1 = AsyncMock(spec=LLMPort)
        provider1.is_enabled.return_value = True
        provider1.get_available_models.return_value = [
            ModelInfo(name="common-model", provider="provider1", type="local")
        ]
        
        provider2 = AsyncMock(spec=LLMPort)
        provider2.is_enabled.return_value = True  
        provider2.get_available_models.return_value = [
            ModelInfo(name="common-model", provider="provider2", type="api")
        ]
        
        registry.register_provider("provider1", provider1)
        registry.register_provider("provider2", provider2)
        
        await registry.refresh_models()
        
        # First provider should win
        assert len(registry.model_to_provider) == 1
        assert registry.model_to_provider["common-model"] == "provider1"
    
    @pytest.mark.asyncio
    async def test_refresh_models_skip_disabled_providers(self, registry, mock_ollama_provider):
        """Test that disabled providers are skipped during refresh."""
        mock_ollama_provider.is_enabled.return_value = False
        registry.register_provider("ollama", mock_ollama_provider)
        
        await registry.refresh_models()
        
        assert len(registry.model_to_provider) == 0
        mock_ollama_provider.get_available_models.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_refresh_models_handle_provider_errors(self, registry, mock_provider):
        """Test handling errors during model refresh."""
        mock_provider.is_enabled.return_value = True
        mock_provider.get_available_models.side_effect = Exception("Provider error")
        registry.register_provider("error_provider", mock_provider)
        
        # Should not raise exception
        await registry.refresh_models()
        
        assert len(registry.model_to_provider) == 0
        assert registry.last_refresh is not None


class TestModelRetrieval:
    """Test model retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_get_all_models(self, registry, mock_ollama_provider, mock_openai_provider):
        """Test getting all models from all providers."""
        registry.register_provider("ollama", mock_ollama_provider)
        registry.register_provider("openai", mock_openai_provider)
        
        models = await registry.get_all_models()
        
        assert len(models) == 4
        model_names = [model.name for model in models]
        assert "llama3.2:3b" in model_names
        assert "mistral:7b" in model_names
        assert "gpt-4" in model_names
        assert "gpt-3.5-turbo" in model_names
    
    @pytest.mark.asyncio
    async def test_get_all_models_auto_refresh(self, registry, mock_ollama_provider):
        """Test that get_all_models automatically refreshes if needed."""
        registry.register_provider("ollama", mock_ollama_provider)
        
        # First call should trigger refresh
        models = await registry.get_all_models()
        assert len(models) == 2
        assert registry.last_refresh is not None
        
        # Clear the cache manually to test refresh logic
        registry.model_to_provider.clear()
        
        # Second call should refresh again
        models = await registry.get_all_models()
        assert len(models) == 2
    
    @pytest.mark.asyncio
    async def test_get_models_by_provider(self, registry, mock_ollama_provider, mock_openai_provider):
        """Test getting models from a specific provider."""
        registry.register_provider("ollama", mock_ollama_provider)
        registry.register_provider("openai", mock_openai_provider)
        
        ollama_models = await registry.get_models_by_provider("ollama")
        assert len(ollama_models) == 2
        assert all(model.provider == "ollama" for model in ollama_models)
        
        openai_models = await registry.get_models_by_provider("openai")
        assert len(openai_models) == 2
        assert all(model.provider == "openai" for model in openai_models)
    
    @pytest.mark.asyncio
    async def test_get_models_by_nonexistent_provider(self, registry):
        """Test getting models from a provider that doesn't exist."""
        with pytest.raises(ValueError, match="Provider nonexistent not registered"):
            await registry.get_models_by_provider("nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_models_by_disabled_provider(self, registry, mock_provider):
        """Test getting models from a disabled provider."""
        mock_provider.is_enabled.return_value = False
        registry.register_provider("disabled", mock_provider)
        
        models = await registry.get_models_by_provider("disabled")
        assert len(models) == 0
    
    def test_get_provider_for_model(self, registry, mock_ollama_provider):
        """Test getting the provider for a specific model."""
        registry.register_provider("ollama", mock_ollama_provider)
        registry.model_to_provider["llama3.2:3b"] = "ollama"
        
        provider = registry.get_provider_for_model("llama3.2:3b")
        assert provider == "ollama"
        
        provider = registry.get_provider_for_model("nonexistent")
        assert provider is None


class TestChatRouting:
    """Test chat request routing functionality."""
    
    @pytest.mark.asyncio
    async def test_chat_routing_success(self, registry, mock_ollama_provider, sample_messages):
        """Test successful chat routing to the correct provider."""
        mock_ollama_provider.chat.return_value = "Hello! I'm doing well."
        registry.register_provider("ollama", mock_ollama_provider)
        registry.model_to_provider["llama3.2:3b"] = "ollama"
        
        response = await registry.chat("llama3.2:3b", sample_messages, temperature=0.7)
        
        assert response == "Hello! I'm doing well."
        mock_ollama_provider.chat.assert_called_once_with(
            "llama3.2:3b", sample_messages, temperature=0.7
        )
    
    @pytest.mark.asyncio
    async def test_chat_routing_with_refresh(self, registry, mock_ollama_provider, sample_messages):
        """Test chat routing that triggers model refresh."""
        mock_ollama_provider.chat.return_value = "Response"
        registry.register_provider("ollama", mock_ollama_provider)
        
        # Model not in cache, should trigger refresh
        response = await registry.chat("llama3.2:3b", sample_messages)
        
        assert response == "Response"
        mock_ollama_provider.get_available_models.assert_called()
    
    @pytest.mark.asyncio
    async def test_chat_routing_model_not_found(self, registry, sample_messages):
        """Test chat routing when model is not available from any provider."""
        with pytest.raises(ValueError, match="Model nonexistent not available"):
            await registry.chat("nonexistent", sample_messages)
    
    @pytest.mark.asyncio
    async def test_chat_routing_provider_disabled(self, registry, mock_provider, sample_messages):
        """Test chat routing when provider is disabled."""
        mock_provider.is_enabled.return_value = False
        registry.register_provider("test", mock_provider)
        registry.model_to_provider["test-model"] = "test"
        
        with pytest.raises(ValueError, match="Provider test is currently disabled"):
            await registry.chat("test-model", sample_messages)
    
    @pytest.mark.asyncio
    async def test_chat_routing_provider_error(self, registry, mock_provider, sample_messages):
        """Test chat routing when provider throws an error."""
        mock_provider.chat.side_effect = Exception("Provider error")
        registry.register_provider("test", mock_provider)
        registry.model_to_provider["test-model"] = "test"
        
        with pytest.raises(Exception, match="Provider error"):
            await registry.chat("test-model", sample_messages)


class TestStreamingChat:
    """Test streaming chat functionality."""
    
    @pytest.mark.asyncio
    async def test_chat_stream_routing_success(self, registry, mock_ollama_provider, sample_messages):
        """Test successful streaming chat routing."""
        async def mock_stream():
            yield "Hello"
            yield " world"
            yield "!"
        
        mock_ollama_provider.chat_stream.return_value = mock_stream()
        registry.register_provider("ollama", mock_ollama_provider)
        registry.model_to_provider["llama3.2:3b"] = "ollama"
        
        chunks = []
        async for chunk in registry.chat_stream("llama3.2:3b", sample_messages, temperature=0.7):
            chunks.append(chunk)
        
        assert chunks == ["Hello", " world", "!"]
        mock_ollama_provider.chat_stream.assert_called_once_with(
            "llama3.2:3b", sample_messages, temperature=0.7
        )
    
    @pytest.mark.asyncio
    async def test_chat_stream_routing_with_refresh(self, registry, mock_ollama_provider, sample_messages):
        """Test streaming chat routing that triggers model refresh."""
        async def mock_stream():
            yield "Response"
        
        mock_ollama_provider.chat_stream.return_value = mock_stream()
        registry.register_provider("ollama", mock_ollama_provider)
        
        chunks = []
        async for chunk in registry.chat_stream("llama3.2:3b", sample_messages):
            chunks.append(chunk)
        
        assert chunks == ["Response"]
        mock_ollama_provider.get_available_models.assert_called()
    
    @pytest.mark.asyncio
    async def test_chat_stream_routing_model_not_found(self, registry, sample_messages):
        """Test streaming chat when model is not available."""
        with pytest.raises(ValueError, match="Model nonexistent not available"):
            async for _ in registry.chat_stream("nonexistent", sample_messages):
                pass
    
    @pytest.mark.asyncio
    async def test_chat_stream_routing_provider_error(self, registry, mock_provider, sample_messages):
        """Test streaming chat when provider throws an error."""
        async def error_stream():
            raise Exception("Stream error")
            yield  # This will never be reached
        
        mock_provider.chat_stream.return_value = error_stream()
        registry.register_provider("test", mock_provider)
        registry.model_to_provider["test-model"] = "test"
        
        with pytest.raises(Exception, match="Stream error"):
            async for _ in registry.chat_stream("test-model", sample_messages):
                pass


class TestHealthChecking:
    """Test health checking functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, registry, mock_ollama_provider, mock_openai_provider):
        """Test health check when all providers are healthy."""
        registry.register_provider("ollama", mock_ollama_provider)
        registry.register_provider("openai", mock_openai_provider)
        registry.model_to_provider = {"model1": "ollama", "model2": "openai"}
        
        health = await registry.health_check()
        
        assert health["overall_status"] == "healthy"
        assert len(health["providers"]) == 2
        assert health["total_models"] == 2
        
        assert health["providers"]["ollama"]["enabled"] is True
        assert health["providers"]["ollama"]["healthy"] is True
        assert health["providers"]["ollama"]["status"] == "healthy"
        
        assert health["providers"]["openai"]["enabled"] is True
        assert health["providers"]["openai"]["healthy"] is True
        assert health["providers"]["openai"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_some_unhealthy(self, registry, mock_ollama_provider, mock_openai_provider):
        """Test health check when some providers are unhealthy."""
        mock_ollama_provider.health_check.return_value = True
        mock_openai_provider.health_check.return_value = False
        
        registry.register_provider("ollama", mock_ollama_provider)
        registry.register_provider("openai", mock_openai_provider)
        
        health = await registry.health_check()
        
        assert health["overall_status"] == "healthy"  # At least one healthy
        assert health["providers"]["ollama"]["status"] == "healthy"
        assert health["providers"]["openai"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_all_disabled(self, registry, mock_provider):
        """Test health check when all providers are disabled."""
        mock_provider.is_enabled.return_value = False
        registry.register_provider("test", mock_provider)
        
        health = await registry.health_check()
        
        assert health["overall_status"] == "unhealthy"
        assert health["providers"]["test"]["enabled"] is False
        assert health["providers"]["test"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_with_errors(self, registry, mock_provider):
        """Test health check when providers throw errors."""
        mock_provider.is_enabled.side_effect = Exception("Provider error")
        registry.register_provider("error_provider", mock_provider)
        
        health = await registry.health_check()
        
        assert health["overall_status"] == "unhealthy"
        assert health["providers"]["error_provider"]["status"] == "error"
        assert health["providers"]["error_provider"]["error"] == "Provider error"


class TestGlobalRegistry:
    """Test global registry instance management."""
    
    def test_get_model_registry_singleton(self):
        """Test that get_model_registry returns a singleton."""
        registry1 = get_model_registry()
        registry2 = get_model_registry()
        
        assert registry1 is registry2
        assert isinstance(registry1, ModelRegistry)
    
    def test_set_model_registry(self):
        """Test setting a custom model registry."""
        custom_registry = ModelRegistry()
        set_model_registry(custom_registry)
        
        current_registry = get_model_registry()
        assert current_registry is custom_registry
    
    def teardown_method(self):
        """Reset global registry after each test."""
        set_model_registry(None)


class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    @pytest.mark.asyncio
    async def test_provider_lifecycle(self, registry, mock_ollama_provider, mock_openai_provider):
        """Test complete provider lifecycle: register, use, unregister."""
        # Register providers
        registry.register_provider("ollama", mock_ollama_provider)
        registry.register_provider("openai", mock_openai_provider)
        
        # Refresh models
        await registry.refresh_models()
        assert len(registry.model_to_provider) == 4
        
        # Use a model
        mock_ollama_provider.chat.return_value = "Response"
        response = await registry.chat("llama3.2:3b", [{"role": "user", "content": "test"}])
        assert response == "Response"
        
        # Unregister provider
        registry.unregister_provider("ollama")
        assert "ollama" not in registry.providers
        assert "llama3.2:3b" not in registry.model_to_provider
        assert "mistral:7b" not in registry.model_to_provider
        # OpenAI models should still be there
        assert "gpt-4" in registry.model_to_provider
    
    @pytest.mark.asyncio
    async def test_failover_scenario(self, registry):
        """Test failover when primary provider fails."""
        # Create two providers with same model
        provider1 = AsyncMock(spec=LLMPort)
        provider1.is_enabled.return_value = True
        provider1.get_available_models.return_value = [
            ModelInfo(name="common-model", provider="provider1", type="local")
        ]
        provider1.chat.side_effect = Exception("Provider 1 failed")
        
        provider2 = AsyncMock(spec=LLMPort)
        provider2.is_enabled.return_value = True
        provider2.get_available_models.return_value = [
            ModelInfo(name="backup-model", provider="provider2", type="api")
        ]
        provider2.chat.return_value = "Backup response"
        
        registry.register_provider("provider1", provider1)
        registry.register_provider("provider2", provider2)
        await registry.refresh_models()
        
        # First provider should be chosen for common-model
        assert registry.model_to_provider["common-model"] == "provider1"
        
        # Chat with common-model should fail
        with pytest.raises(Exception, match="Provider 1 failed"):
            await registry.chat("common-model", [{"role": "user", "content": "test"}])
        
        # But backup-model should work
        response = await registry.chat("backup-model", [{"role": "user", "content": "test"}])
        assert response == "Backup response"
    
    @pytest.mark.asyncio
    async def test_dynamic_provider_enabling(self, registry, mock_provider):
        """Test dynamic enabling/disabling of providers."""
        registry.register_provider("dynamic", mock_provider)
        
        # Initially enabled
        mock_provider.is_enabled.return_value = True
        enabled = await registry.get_enabled_providers()
        assert "dynamic" in enabled
        
        # Dynamically disable
        mock_provider.is_enabled.return_value = False
        enabled = await registry.get_enabled_providers()
        assert "dynamic" not in enabled
        
        # Re-enable
        mock_provider.is_enabled.return_value = True
        enabled = await registry.get_enabled_providers()
        assert "dynamic" in enabled