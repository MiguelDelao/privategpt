from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, AsyncIterator, Dict, Any, List, Optional
from datetime import datetime


@dataclass
class ModelInfo:
    """Information about an available model"""
    name: str
    provider: str
    type: str  # "local", "api", "hosted"
    available: bool = True
    description: Optional[str] = None
    context_length: Optional[int] = None
    parameter_size: Optional[str] = None
    capabilities: List[str] = None
    cost_per_token: Optional[float] = None
    last_checked: Optional[datetime] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class LLMPort(Protocol):
    async def get_available_models(self) -> List[ModelInfo]:
        """Get list of models available from this provider."""
        ...
    
    async def chat(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response for a conversation using specified model."""
        ...
        
    async def chat_stream(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Generate streaming response for a conversation using specified model."""
        ...
    
    async def is_enabled(self) -> bool:
        """Check if this provider is currently enabled."""
        ...
    
    async def health_check(self) -> bool:
        """Check if the LLM provider is healthy and responsive."""
        ...
    
    def get_provider_name(self) -> str:
        """Get the name of this provider (e.g., 'ollama', 'openai', 'anthropic')."""
        ...
    
    def get_provider_type(self) -> str:
        """Get the type of this provider (e.g., 'local', 'api')."""
        ...
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this provider."""
        ... 