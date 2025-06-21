from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from privategpt.services.llm.core import LLMPort
from privategpt.services.llm.core.model_registry import ModelRegistry, get_model_registry
from privategpt.services.llm.adapters.ollama_adapter import OllamaAdapter
from privategpt.services.llm.adapters.openai_adapter import OpenAIAdapter
from privategpt.services.llm.adapters.anthropic_adapter import AnthropicAdapter
from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for creating and registering LLM providers based on configuration."""
    
    @staticmethod
    def create_ollama_provider(config: Dict[str, Any]) -> Optional[LLMPort]:
        """Create an Ollama provider from configuration."""
        try:
            return OllamaAdapter(
                base_url=config.get("base_url", settings.ollama_base_url),
                default_model=config.get("default_model", settings.ollama_model),
                timeout=config.get("timeout", 600.0),
                enabled=config.get("enabled", True)
            )
        except Exception as e:
            logger.error(f"Failed to create Ollama provider: {e}")
            return None
    
    @staticmethod
    def create_openai_provider(config: Dict[str, Any]) -> Optional[LLMPort]:
        """Create an OpenAI provider from configuration."""
        api_key = config.get("api_key")
        if not api_key:
            logger.error("OpenAI API key not provided")
            return None
            
        try:
            return OpenAIAdapter(
                api_key=api_key,
                base_url=config.get("base_url", "https://api.openai.com/v1"),
                default_model=config.get("default_model", "gpt-4"),
                timeout=config.get("timeout", 30.0),
                enabled=config.get("enabled", True)
            )
        except Exception as e:
            logger.error(f"Failed to create OpenAI provider: {e}")
            return None
    
    @staticmethod
    def create_anthropic_provider(config: Dict[str, Any]) -> Optional[LLMPort]:
        """Create an Anthropic (Claude) provider from configuration."""
        api_key = config.get("api_key")
        if not api_key:
            logger.error("Anthropic API key not provided")
            return None
            
        try:
            return AnthropicAdapter(
                api_key=api_key,
                base_url=config.get("base_url", "https://api.anthropic.com"),
                default_model=config.get("default_model", "claude-3-5-sonnet-20241022"),
                timeout=config.get("timeout", 30.0),
                enabled=config.get("enabled", True)
            )
        except Exception as e:
            logger.error(f"Failed to create Anthropic provider: {e}")
            return None
    
    @staticmethod
    def setup_providers_from_config() -> ModelRegistry:
        """Setup all providers from configuration and return configured registry."""
        registry = get_model_registry()
        
        # Provider configurations - in a real app this would come from settings/config file
        provider_configs = {
            "ollama": {
                "enabled": getattr(settings, "ollama_enabled", True),
                "base_url": getattr(settings, "ollama_base_url", "http://localhost:11434"),
                "default_model": getattr(settings, "ollama_model", "llama3.2"),
                "timeout": 600.0
            },
            "openai": {
                "enabled": getattr(settings, "openai_enabled", False),
                "api_key": getattr(settings, "openai_api_key", None),
                "base_url": getattr(settings, "openai_base_url", "https://api.openai.com/v1"),
                "default_model": getattr(settings, "openai_model", "gpt-4"),
                "timeout": 30.0
            },
            "anthropic": {
                "enabled": getattr(settings, "anthropic_enabled", False),
                "api_key": getattr(settings, "anthropic_api_key", None),
                "base_url": getattr(settings, "anthropic_base_url", "https://api.anthropic.com"),
                "default_model": getattr(settings, "anthropic_model", "claude-3-5-sonnet-20241022"),
                "timeout": 30.0
            }
        }
        
        # Factory methods mapping
        factory_methods = {
            "ollama": LLMProviderFactory.create_ollama_provider,
            "openai": LLMProviderFactory.create_openai_provider,
            "anthropic": LLMProviderFactory.create_anthropic_provider
        }
        
        # Create and register enabled providers
        for provider_name, config in provider_configs.items():
            if not config.get("enabled", False):
                logger.info(f"Provider {provider_name} is disabled, skipping")
                continue
                
            factory_method = factory_methods.get(provider_name)
            if not factory_method:
                logger.warning(f"No factory method for provider {provider_name}")
                continue
                
            try:
                provider = factory_method(config)
                if provider:
                    registry.register_provider(provider_name, provider)
                    logger.info(f"Successfully registered provider: {provider_name}")
                else:
                    logger.warning(f"Failed to create provider: {provider_name}")
            except Exception as e:
                logger.error(f"Error setting up provider {provider_name}: {e}")
        
        return registry
    
    @staticmethod
    async def initialize_model_registry() -> ModelRegistry:
        """Initialize and refresh the model registry with all providers."""
        registry = LLMProviderFactory.setup_providers_from_config()
        
        # Refresh models from all providers
        try:
            await registry.refresh_models()
            logger.info("Model registry initialized and refreshed successfully")
        except Exception as e:
            logger.error(f"Failed to refresh model registry: {e}")
        
        return registry