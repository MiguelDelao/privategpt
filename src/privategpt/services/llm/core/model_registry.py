from __future__ import annotations

import logging
from typing import Dict, List, Optional, AsyncIterator, Any
from datetime import datetime

from privategpt.services.llm.core import LLMPort, ModelInfo, ChatResponse

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Central registry for managing multiple LLM providers and routing requests
    to the appropriate provider based on model names.
    """
    
    def __init__(self):
        self.providers: Dict[str, LLMPort] = {}
        self.model_to_provider: Dict[str, str] = {}
        self.last_refresh: Optional[datetime] = None
    
    def register_provider(self, name: str, provider: LLMPort) -> None:
        """Register a new LLM provider with the registry."""
        logger.info(f"Registering LLM provider: {name}")
        self.providers[name] = provider
        # Clear model cache to force refresh
        self.model_to_provider.clear()
        self.last_refresh = None
    
    def unregister_provider(self, name: str) -> bool:
        """Remove a provider from the registry."""
        if name in self.providers:
            logger.info(f"Unregistering LLM provider: {name}")
            del self.providers[name]
            # Remove models from this provider from the cache
            models_to_remove = [
                model for model, provider in self.model_to_provider.items() 
                if provider == name
            ]
            for model in models_to_remove:
                del self.model_to_provider[model]
            return True
        return False
    
    def get_registered_providers(self) -> List[str]:
        """Get list of all registered provider names."""
        return list(self.providers.keys())
    
    async def get_enabled_providers(self) -> List[str]:
        """Get list of currently enabled provider names."""
        enabled = []
        for name, provider in self.providers.items():
            try:
                if await provider.is_enabled():
                    enabled.append(name)
            except Exception as e:
                logger.warning(f"Failed to check if provider {name} is enabled: {e}")
        return enabled
    
    async def refresh_models(self) -> None:
        """Refresh the model list from all enabled providers."""
        logger.info("Refreshing model registry from all providers")
        self.model_to_provider.clear()
        
        for provider_name, provider in self.providers.items():
            try:
                if not await provider.is_enabled():
                    logger.debug(f"Provider {provider_name} is disabled, skipping")
                    continue
                
                models = await provider.get_available_models()
                for model in models:
                    if model.name in self.model_to_provider:
                        logger.warning(
                            f"Model {model.name} is available from multiple providers. "
                            f"Using {self.model_to_provider[model.name]}, ignoring {provider_name}"
                        )
                        continue
                    
                    self.model_to_provider[model.name] = provider_name
                    logger.debug(f"Registered model {model.name} from provider {provider_name}")
                
            except Exception as e:
                logger.error(f"Failed to get models from provider {provider_name}: {e}")
        
        self.last_refresh = datetime.utcnow()
        logger.info(f"Model registry refreshed. {len(self.model_to_provider)} models available.")
    
    async def get_all_models(self) -> List[ModelInfo]:
        """Get all available models from all enabled providers."""
        # Refresh if we haven't done so recently
        if not self.last_refresh or not self.model_to_provider:
            await self.refresh_models()
        
        all_models = []
        
        for provider_name, provider in self.providers.items():
            try:
                if not await provider.is_enabled():
                    continue
                
                models = await provider.get_available_models()
                for model in models:
                    # Only include models that we have in our registry
                    # (to avoid duplicates from multiple providers)
                    if self.model_to_provider.get(model.name) == provider_name:
                        all_models.append(model)
                        
            except Exception as e:
                logger.error(f"Failed to get models from provider {provider_name}: {e}")
        
        return all_models
    
    async def get_models_by_provider(self, provider_name: str) -> List[ModelInfo]:
        """Get models available from a specific provider."""
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not registered")
        
        provider = self.providers[provider_name]
        try:
            if not await provider.is_enabled():
                return []
            return await provider.get_available_models()
        except Exception as e:
            logger.error(f"Failed to get models from provider {provider_name}: {e}")
            return []
    
    def get_provider_for_model(self, model_name: str) -> Optional[str]:
        """Get the provider name that handles the specified model."""
        return self.model_to_provider.get(model_name)
    
    async def chat(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> ChatResponse:
        """Route a chat request to the appropriate provider."""
        provider_name = self.get_provider_for_model(model_name)
        if not provider_name:
            # Try refreshing models in case it's a new model
            await self.refresh_models()
            provider_name = self.get_provider_for_model(model_name)
            
        if not provider_name:
            raise ValueError(f"Model {model_name} not available from any registered provider")
        
        provider = self.providers[provider_name]
        
        try:
            if not await provider.is_enabled():
                raise ValueError(f"Provider {provider_name} is currently disabled")
            
            logger.debug(f"Routing chat request for model {model_name} to provider {provider_name}")
            return await provider.chat(model_name, messages, **kwargs)
            
        except Exception as e:
            logger.error(f"Chat request failed for model {model_name} via {provider_name}: {e}")
            raise
    
    async def chat_stream(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Route a streaming chat request to the appropriate provider."""
        provider_name = self.get_provider_for_model(model_name)
        if not provider_name:
            # Try refreshing models in case it's a new model
            await self.refresh_models()
            provider_name = self.get_provider_for_model(model_name)
            
        if not provider_name:
            raise ValueError(f"Model {model_name} not available from any registered provider")
        
        provider = self.providers[provider_name]
        
        try:
            if not await provider.is_enabled():
                raise ValueError(f"Provider {provider_name} is currently disabled")
            
            logger.debug(f"Routing streaming chat request for model {model_name} to provider {provider_name}")
            async for chunk in provider.chat_stream(model_name, messages, **kwargs):
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming chat request failed for model {model_name} via {provider_name}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all registered providers."""
        health_status = {}
        
        for provider_name, provider in self.providers.items():
            try:
                is_enabled = await provider.is_enabled()
                is_healthy = await provider.health_check() if is_enabled else False
                
                health_status[provider_name] = {
                    "enabled": is_enabled,
                    "healthy": is_healthy,
                    "status": "healthy" if (is_enabled and is_healthy) else "unhealthy",
                    "provider_type": provider.get_provider_type(),
                    "checked_at": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                health_status[provider_name] = {
                    "enabled": False,
                    "healthy": False,
                    "status": "error",
                    "error": str(e),
                    "checked_at": datetime.utcnow().isoformat()
                }
        
        overall_healthy = any(
            status["status"] == "healthy" for status in health_status.values()
        )
        
        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "providers": health_status,
            "total_models": len(self.model_to_provider),
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None
        }
    
    async def get_context_limit(self, model_name: str) -> int:
        """Get context limit for a specific model."""
        provider_name = self.get_provider_for_model(model_name)
        if not provider_name:
            # Try refreshing models in case it's a new model
            await self.refresh_models()
            provider_name = self.get_provider_for_model(model_name)
            
        if not provider_name:
            # Fallback to conservative default
            return 4096
            
        provider = self.providers[provider_name]
        try:
            return await provider.get_context_limit(model_name)
        except Exception as e:
            logger.warning(f"Failed to get context limit for {model_name}: {e}")
            return 4096


# Global registry instance
_model_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get the global model registry instance."""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry


def set_model_registry(registry: ModelRegistry) -> None:
    """Set the global model registry instance (for testing)."""
    global _model_registry
    _model_registry = registry