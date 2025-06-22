"""
Integration tests for the LLM multi-provider system.

Tests complete end-to-end functionality including provider registration,
model discovery, request routing, error handling, and real-world scenarios.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncIterator

from privategpt.services.llm.core import LLMPort, ModelInfo
from privategpt.services.llm.core.model_registry import ModelRegistry, get_model_registry, set_model_registry
from privategpt.services.llm.core.provider_factory import LLMProviderFactory


@pytest.fixture
def mock_ollama_adapter():
    """Create a realistic mock Ollama adapter."""
    adapter = AsyncMock(spec=LLMPort)
    adapter.get_provider_name.return_value = "ollama"
    adapter.get_provider_type.return_value = "local"
    adapter.is_enabled.return_value = True
    adapter.health_check.return_value = True
    
    adapter.get_available_models.return_value = [
        ModelInfo(
            name="llama3.2:3b",
            provider="ollama",
            type="local",
            description="Llama 3.2 3B parameter model",
            context_length=4096,
            parameter_size="3B",
            capabilities=["chat", "completion"]
        ),
        ModelInfo(
            name="mistral:7b", 
            provider="ollama",
            type="local",
            description="Mistral 7B parameter model",
            context_length=8192,
            parameter_size="7B",
            capabilities=["chat", "completion"]
        ),
        ModelInfo(
            name="codellama:7b",
            provider="ollama",
            type="local",
            description="Code Llama 7B for code generation",
            context_length=4096,
            parameter_size="7B",
            capabilities=["chat", "completion", "code"]
        )
    ]
    
    adapter.chat.return_value = "Hello! I'm an Ollama model response."
    
    async def mock_chat_stream(*args, **kwargs):
        yield "Hello"
        yield " from"
        yield " Ollama"
        yield "!"
    
    adapter.chat_stream.return_value = mock_chat_stream()
    return adapter


@pytest.fixture
def mock_openai_adapter():
    """Create a realistic mock OpenAI adapter."""
    adapter = AsyncMock(spec=LLMPort)
    adapter.get_provider_name.return_value = "openai"
    adapter.get_provider_type.return_value = "api"
    adapter.is_enabled.return_value = True
    adapter.health_check.return_value = True
    
    adapter.get_available_models.return_value = [
        ModelInfo(
            name="gpt-4",
            provider="openai", 
            type="api",
            description="GPT-4 model",
            context_length=8192,
            cost_per_token=0.00003,
            capabilities=["chat", "completion", "reasoning"]
        ),
        ModelInfo(
            name="gpt-3.5-turbo",
            provider="openai",
            type="api",
            description="GPT-3.5 Turbo model",
            context_length=4096,
            cost_per_token=0.000002,
            capabilities=["chat", "completion"]
        ),
        ModelInfo(
            name="gpt-4-turbo",
            provider="openai",
            type="api", 
            description="GPT-4 Turbo model",
            context_length=128000,
            cost_per_token=0.00001,
            capabilities=["chat", "completion", "reasoning", "vision"]
        )
    ]
    
    adapter.chat.return_value = "This is a GPT-4 response with advanced reasoning capabilities."
    
    async def mock_chat_stream(*args, **kwargs):
        yield "This"
        yield " is"
        yield " OpenAI"
        yield " streaming"
    
    adapter.chat_stream.return_value = mock_chat_stream()
    return adapter


@pytest.fixture
def mock_anthropic_adapter():
    """Create a realistic mock Anthropic adapter."""
    adapter = AsyncMock(spec=LLMPort)
    adapter.get_provider_name.return_value = "anthropic"
    adapter.get_provider_type.return_value = "api"
    adapter.is_enabled.return_value = True
    adapter.health_check.return_value = True
    
    adapter.get_available_models.return_value = [
        ModelInfo(
            name="claude-3-5-sonnet",
            provider="anthropic",
            type="api",
            description="Claude 3.5 Sonnet model",
            context_length=200000,
            cost_per_token=0.000015,
            capabilities=["chat", "completion", "reasoning", "analysis"]
        ),
        ModelInfo(
            name="claude-3-opus",
            provider="anthropic", 
            type="api",
            description="Claude 3 Opus model",
            context_length=200000,
            cost_per_token=0.000075,
            capabilities=["chat", "completion", "reasoning", "analysis", "creative"]
        )
    ]
    
    adapter.chat.return_value = "Claude here! I'm designed to be helpful, harmless, and honest."
    
    async def mock_chat_stream(*args, **kwargs):
        yield "Claude"
        yield " streaming"
        yield " response"
    
    adapter.chat_stream.return_value = mock_chat_stream()
    return adapter


@pytest.fixture
def fresh_registry():
    """Create a fresh registry for each test."""
    registry = ModelRegistry()
    set_model_registry(registry)
    yield registry
    set_model_registry(None)


@pytest.fixture
def sample_chat_messages():
    """Sample chat messages for testing."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you today?"}
    ]


class TestMultiProviderSetup:
    """Test multi-provider system setup and configuration."""
    
    @patch('privategpt.services.llm.core.provider_factory.settings')
    @patch('privategpt.services.llm.core.provider_factory.OllamaAdapter')
    @patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter')
    @patch('privategpt.services.llm.core.provider_factory.AnthropicAdapter')
    def test_setup_all_providers(
        self, 
        mock_anthropic, 
        mock_openai, 
        mock_ollama,
        mock_settings,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter,
        mock_anthropic_adapter
    ):
        """Test setting up all providers from configuration."""
        # Configure settings
        mock_settings.ollama_enabled = True
        mock_settings.ollama_base_url = "http://ollama:11434"
        mock_settings.ollama_model = "llama3.2"
        
        mock_settings.openai_enabled = True
        mock_settings.openai_api_key = "sk-test123"
        mock_settings.openai_base_url = "https://api.openai.com/v1"
        mock_settings.openai_model = "gpt-4"
        
        mock_settings.anthropic_enabled = True
        mock_settings.anthropic_api_key = "ak-test123"
        mock_settings.anthropic_base_url = "https://api.anthropic.com"
        mock_settings.anthropic_model = "claude-3-5-sonnet"
        
        # Configure adapters
        mock_ollama.return_value = mock_ollama_adapter
        mock_openai.return_value = mock_openai_adapter
        mock_anthropic.return_value = mock_anthropic_adapter
        
        # Setup providers
        registry = LLMProviderFactory.setup_providers_from_config()
        
        # Verify all providers are registered
        assert len(registry.providers) == 3
        assert "ollama" in registry.providers
        assert "openai" in registry.providers
        assert "anthropic" in registry.providers
        
        # Verify adapters were created with correct parameters
        mock_ollama.assert_called_once()
        mock_openai.assert_called_once()
        mock_anthropic.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('privategpt.services.llm.core.provider_factory.settings')
    @patch('privategpt.services.llm.core.provider_factory.OllamaAdapter')
    @patch('privategpt.services.llm.core.provider_factory.OpenAIAdapter')
    async def test_initialize_and_refresh_models(
        self, 
        mock_openai, 
        mock_ollama,
        mock_settings,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter
    ):
        """Test complete initialization and model refresh."""
        # Configure settings
        mock_settings.ollama_enabled = True
        mock_settings.ollama_base_url = "http://ollama:11434"
        mock_settings.ollama_model = "llama3.2"
        
        mock_settings.openai_enabled = True
        mock_settings.openai_api_key = "sk-test123"
        mock_settings.openai_base_url = "https://api.openai.com/v1"
        mock_settings.openai_model = "gpt-4"
        
        mock_settings.anthropic_enabled = False
        mock_settings.anthropic_api_key = ""
        
        # Configure adapters
        mock_ollama.return_value = mock_ollama_adapter
        mock_openai.return_value = mock_openai_adapter
        
        # Initialize registry
        registry = await LLMProviderFactory.initialize_model_registry()
        
        # Verify models were refreshed
        assert len(registry.model_to_provider) == 6  # 3 Ollama + 3 OpenAI
        assert registry.model_to_provider["llama3.2:3b"] == "ollama"
        assert registry.model_to_provider["gpt-4"] == "openai"
        assert registry.last_refresh is not None


class TestModelDiscoveryAndRouting:
    """Test model discovery and request routing."""
    
    @pytest.mark.asyncio
    async def test_model_discovery_all_providers(
        self, 
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter,
        mock_anthropic_adapter
    ):
        """Test model discovery from all providers."""
        # Register all providers
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        fresh_registry.register_provider("openai", mock_openai_adapter)
        fresh_registry.register_provider("anthropic", mock_anthropic_adapter)
        
        # Get all models
        models = await fresh_registry.get_all_models()
        
        # Should have models from all providers
        assert len(models) == 8  # 3 + 3 + 2
        
        # Verify model types
        ollama_models = [m for m in models if m.provider == "ollama"]
        openai_models = [m for m in models if m.provider == "openai"]
        anthropic_models = [m for m in models if m.provider == "anthropic"]
        
        assert len(ollama_models) == 3
        assert len(openai_models) == 3
        assert len(anthropic_models) == 2
        
        # Verify specific models
        model_names = [m.name for m in models]
        assert "llama3.2:3b" in model_names
        assert "gpt-4" in model_names
        assert "claude-3-5-sonnet" in model_names
    
    @pytest.mark.asyncio
    async def test_chat_routing_to_correct_provider(
        self,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter,
        sample_chat_messages
    ):
        """Test that chat requests are routed to the correct provider."""
        # Register providers
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        fresh_registry.register_provider("openai", mock_openai_adapter)
        
        # Refresh models
        await fresh_registry.refresh_models()
        
        # Test Ollama routing
        ollama_response = await fresh_registry.chat("llama3.2:3b", sample_chat_messages, temperature=0.7)
        assert ollama_response == "Hello! I'm an Ollama model response."
        mock_ollama_adapter.chat.assert_called_with("llama3.2:3b", sample_chat_messages, temperature=0.7)
        
        # Test OpenAI routing
        openai_response = await fresh_registry.chat("gpt-4", sample_chat_messages, max_tokens=100)
        assert openai_response == "This is a GPT-4 response with advanced reasoning capabilities."
        mock_openai_adapter.chat.assert_called_with("gpt-4", sample_chat_messages, max_tokens=100)
    
    @pytest.mark.asyncio
    async def test_streaming_chat_routing(
        self,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter,
        sample_chat_messages
    ):
        """Test that streaming chat requests are routed correctly."""
        # Register providers
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        fresh_registry.register_provider("openai", mock_openai_adapter)
        
        # Refresh models
        await fresh_registry.refresh_models()
        
        # Test Ollama streaming
        ollama_chunks = []
        async for chunk in fresh_registry.chat_stream("mistral:7b", sample_chat_messages):
            ollama_chunks.append(chunk)
        assert ollama_chunks == ["Hello", " from", " Ollama", "!"]
        
        # Test OpenAI streaming
        openai_chunks = []
        async for chunk in fresh_registry.chat_stream("gpt-3.5-turbo", sample_chat_messages):
            openai_chunks.append(chunk)
        assert openai_chunks == ["This", " is", " OpenAI", " streaming"]


class TestModelConflictResolution:
    """Test model name conflict resolution between providers."""
    
    @pytest.mark.asyncio
    async def test_model_name_conflicts(self, fresh_registry):
        """Test handling of model name conflicts between providers."""
        # Create two providers with conflicting model names
        provider1 = AsyncMock(spec=LLMPort)
        provider1.get_provider_name.return_value = "provider1"
        provider1.is_enabled.return_value = True
        provider1.get_available_models.return_value = [
            ModelInfo(name="shared-model", provider="provider1", type="local"),
            ModelInfo(name="unique-model-1", provider="provider1", type="local")
        ]
        
        provider2 = AsyncMock(spec=LLMPort)
        provider2.get_provider_name.return_value = "provider2"
        provider2.is_enabled.return_value = True
        provider2.get_available_models.return_value = [
            ModelInfo(name="shared-model", provider="provider2", type="api"),
            ModelInfo(name="unique-model-2", provider="provider2", type="api")
        ]
        
        # Register providers (provider1 first)
        fresh_registry.register_provider("provider1", provider1)
        fresh_registry.register_provider("provider2", provider2)
        
        # Refresh models
        await fresh_registry.refresh_models()
        
        # First provider should win for conflicting model
        assert fresh_registry.get_provider_for_model("shared-model") == "provider1"
        assert fresh_registry.get_provider_for_model("unique-model-1") == "provider1"
        assert fresh_registry.get_provider_for_model("unique-model-2") == "provider2"
        
        # Total models should be 3 (not 4 due to conflict)
        assert len(fresh_registry.model_to_provider) == 3


class TestProviderFailover:
    """Test provider failover and error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_provider_disabled_fallback(
        self,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter,
        sample_chat_messages
    ):
        """Test fallback when a provider is disabled."""
        # Register providers
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        fresh_registry.register_provider("openai", mock_openai_adapter)
        
        # Refresh models initially
        await fresh_registry.refresh_models()
        
        # Disable Ollama
        mock_ollama_adapter.is_enabled.return_value = False
        
        # Try to use Ollama model - should fail gracefully
        with pytest.raises(ValueError, match="Provider ollama is currently disabled"):
            await fresh_registry.chat("llama3.2:3b", sample_chat_messages)
        
        # OpenAI should still work
        response = await fresh_registry.chat("gpt-4", sample_chat_messages)
        assert response == "This is a GPT-4 response with advanced reasoning capabilities."
    
    @pytest.mark.asyncio
    async def test_provider_error_handling(
        self,
        fresh_registry,
        mock_ollama_adapter,
        sample_chat_messages
    ):
        """Test handling of provider errors during chat."""
        # Register provider
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        await fresh_registry.refresh_models()
        
        # Make provider throw an error
        mock_ollama_adapter.chat.side_effect = Exception("Model overloaded")
        
        # Should propagate the error
        with pytest.raises(Exception, match="Model overloaded"):
            await fresh_registry.chat("llama3.2:3b", sample_chat_messages)
    
    @pytest.mark.asyncio
    async def test_model_refresh_on_unknown_model(
        self,
        fresh_registry,
        mock_ollama_adapter,
        sample_chat_messages
    ):
        """Test that unknown models trigger a model refresh."""
        # Register provider but don't refresh initially
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        
        # Try to use a model - should trigger refresh
        response = await fresh_registry.chat("llama3.2:3b", sample_chat_messages)
        assert response == "Hello! I'm an Ollama model response."
        
        # Verify models were refreshed
        assert len(fresh_registry.model_to_provider) > 0
        assert fresh_registry.last_refresh is not None


class TestHealthMonitoring:
    """Test health monitoring across multiple providers."""
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(
        self,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter,
        mock_anthropic_adapter
    ):
        """Test health check when all providers are healthy."""
        # Register all providers
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        fresh_registry.register_provider("openai", mock_openai_adapter)
        fresh_registry.register_provider("anthropic", mock_anthropic_adapter)
        
        # Refresh models for model count
        await fresh_registry.refresh_models()
        
        # Check health
        health = await fresh_registry.health_check()
        
        assert health["overall_status"] == "healthy"
        assert len(health["providers"]) == 3
        assert health["total_models"] == 8
        
        # All providers should be healthy
        for provider_name, status in health["providers"].items():
            assert status["enabled"] is True
            assert status["healthy"] is True
            assert status["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_mixed_status(
        self,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter
    ):
        """Test health check with mixed provider status."""
        # Configure providers with different health
        mock_ollama_adapter.health_check.return_value = True
        mock_openai_adapter.health_check.return_value = False
        
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        fresh_registry.register_provider("openai", mock_openai_adapter)
        
        health = await fresh_registry.health_check()
        
        # Overall should be healthy if at least one is healthy
        assert health["overall_status"] == "healthy"
        
        assert health["providers"]["ollama"]["status"] == "healthy"
        assert health["providers"]["openai"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_all_unhealthy(
        self,
        fresh_registry,
        mock_ollama_adapter
    ):
        """Test health check when all providers are unhealthy."""
        mock_ollama_adapter.is_enabled.return_value = False
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        
        health = await fresh_registry.health_check()
        
        assert health["overall_status"] == "unhealthy"
        assert health["providers"]["ollama"]["status"] == "unhealthy"


class TestRealWorldScenarios:
    """Test realistic multi-provider scenarios."""
    
    @pytest.mark.asyncio
    async def test_local_and_cloud_hybrid_setup(
        self,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter,
        sample_chat_messages
    ):
        """Test hybrid setup with local and cloud providers."""
        # Register local and cloud providers
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        fresh_registry.register_provider("openai", mock_openai_adapter)
        
        await fresh_registry.refresh_models()
        
        # Test using local model for development/privacy
        local_response = await fresh_registry.chat("llama3.2:3b", sample_chat_messages)
        assert "Ollama" in local_response
        
        # Test using cloud model for better quality
        cloud_response = await fresh_registry.chat("gpt-4", sample_chat_messages)
        assert "GPT-4" in cloud_response
        
        # Verify model categorization
        models = await fresh_registry.get_all_models()
        local_models = [m for m in models if m.type == "local"]
        api_models = [m for m in models if m.type == "api"]
        
        assert len(local_models) == 3  # Ollama models
        assert len(api_models) == 3   # OpenAI models
    
    @pytest.mark.asyncio
    async def test_cost_optimization_scenario(
        self,
        fresh_registry,
        mock_openai_adapter,
        mock_anthropic_adapter
    ):
        """Test cost optimization with different cloud providers."""
        fresh_registry.register_provider("openai", mock_openai_adapter)
        fresh_registry.register_provider("anthropic", mock_anthropic_adapter)
        
        models = await fresh_registry.get_all_models()
        
        # Find lowest cost model
        cost_models = [m for m in models if m.cost_per_token is not None]
        lowest_cost = min(cost_models, key=lambda m: m.cost_per_token)
        
        # Should be gpt-3.5-turbo at 0.000002
        assert lowest_cost.name == "gpt-3.5-turbo"
        assert lowest_cost.cost_per_token == 0.000002
    
    @pytest.mark.asyncio
    async def test_capability_based_routing(
        self,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter
    ):
        """Test routing based on model capabilities."""
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        fresh_registry.register_provider("openai", mock_openai_adapter)
        
        models = await fresh_registry.get_all_models()
        
        # Find models with specific capabilities
        code_models = [m for m in models if "code" in m.capabilities]
        reasoning_models = [m for m in models if "reasoning" in m.capabilities]
        vision_models = [m for m in models if "vision" in m.capabilities]
        
        assert len(code_models) == 1  # codellama:7b
        assert code_models[0].name == "codellama:7b"
        
        assert len(reasoning_models) == 2  # gpt-4, gpt-4-turbo
        assert all("gpt-4" in m.name for m in reasoning_models)
        
        assert len(vision_models) == 1  # gpt-4-turbo
        assert vision_models[0].name == "gpt-4-turbo"
    
    @pytest.mark.asyncio
    async def test_dynamic_provider_management(
        self,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter,
        sample_chat_messages
    ):
        """Test dynamic addition and removal of providers."""
        # Start with just Ollama
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        await fresh_registry.refresh_models()
        
        initial_models = len(fresh_registry.model_to_provider)
        assert initial_models == 3  # Ollama models only
        
        # Add OpenAI provider dynamically
        fresh_registry.register_provider("openai", mock_openai_adapter)
        await fresh_registry.refresh_models()
        
        expanded_models = len(fresh_registry.model_to_provider)
        assert expanded_models == 6  # Ollama + OpenAI models
        
        # Test using newly added provider
        response = await fresh_registry.chat("gpt-4", sample_chat_messages)
        assert "GPT-4" in response
        
        # Remove OpenAI provider
        fresh_registry.unregister_provider("openai")
        
        # OpenAI models should be removed from registry
        assert "gpt-4" not in fresh_registry.model_to_provider
        assert "llama3.2:3b" in fresh_registry.model_to_provider  # Ollama still there
    
    @pytest.mark.asyncio
    async def test_load_balancing_simulation(
        self,
        fresh_registry,
        sample_chat_messages
    ):
        """Test load balancing between multiple instances of same provider type."""
        # Create multiple Ollama instances
        ollama1 = AsyncMock(spec=LLMPort)
        ollama1.get_provider_name.return_value = "ollama1"
        ollama1.is_enabled.return_value = True
        ollama1.get_available_models.return_value = [
            ModelInfo(name="llama3.2:3b", provider="ollama1", type="local")
        ]
        ollama1.chat.return_value = "Response from Ollama 1"
        
        ollama2 = AsyncMock(spec=LLMPort)
        ollama2.get_provider_name.return_value = "ollama2"
        ollama2.is_enabled.return_value = True
        ollama2.get_available_models.return_value = [
            ModelInfo(name="mistral:7b", provider="ollama2", type="local")
        ]
        ollama2.chat.return_value = "Response from Ollama 2"
        
        # Register both instances
        fresh_registry.register_provider("ollama1", ollama1)
        fresh_registry.register_provider("ollama2", ollama2)
        await fresh_registry.refresh_models()
        
        # Both models should be available
        assert fresh_registry.get_provider_for_model("llama3.2:3b") == "ollama1"
        assert fresh_registry.get_provider_for_model("mistral:7b") == "ollama2"
        
        # Test routing to different instances
        response1 = await fresh_registry.chat("llama3.2:3b", sample_chat_messages)
        response2 = await fresh_registry.chat("mistral:7b", sample_chat_messages)
        
        assert response1 == "Response from Ollama 1"
        assert response2 == "Response from Ollama 2"


class TestPerformanceAndConcurrency:
    """Test performance and concurrency scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_model_refresh(
        self,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter
    ):
        """Test concurrent model refresh operations."""
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        fresh_registry.register_provider("openai", mock_openai_adapter)
        
        # Run multiple refresh operations concurrently
        import asyncio
        refresh_tasks = [fresh_registry.refresh_models() for _ in range(5)]
        await asyncio.gather(*refresh_tasks)
        
        # Should end up with consistent state
        assert len(fresh_registry.model_to_provider) == 6
        assert fresh_registry.last_refresh is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_chat_requests(
        self,
        fresh_registry,
        mock_ollama_adapter,
        mock_openai_adapter,
        sample_chat_messages
    ):
        """Test concurrent chat requests to different providers."""
        fresh_registry.register_provider("ollama", mock_ollama_adapter)
        fresh_registry.register_provider("openai", mock_openai_adapter)
        await fresh_registry.refresh_models()
        
        # Run concurrent chat requests
        import asyncio
        
        async def chat_ollama():
            return await fresh_registry.chat("llama3.2:3b", sample_chat_messages)
        
        async def chat_openai():
            return await fresh_registry.chat("gpt-4", sample_chat_messages)
        
        # Run multiple concurrent requests
        tasks = [chat_ollama(), chat_openai(), chat_ollama(), chat_openai()]
        responses = await asyncio.gather(*tasks)
        
        # All requests should complete successfully
        assert len(responses) == 4
        assert all(response for response in responses)  # No empty responses