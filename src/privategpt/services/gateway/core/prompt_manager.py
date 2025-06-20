from __future__ import annotations

"""
System prompt management service for dynamic prompt configuration.

Handles:
- Loading prompts from database and config
- Model-specific prompt selection
- Prompt caching for performance
- Dynamic prompt updates
"""

import logging
import re
from typing import Dict, List, Optional, Any
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from privategpt.infra.database.models import SystemPrompt
from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages system prompts for different models and use cases"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: Dict[str, str] = {}
        self._cache_enabled = settings.enable_prompt_caching
    
    async def get_prompt_for_model(self, 
                                  model_name: str,
                                  conversation_id: Optional[str] = None) -> str:
        """
        Get the appropriate system prompt for a model.
        
        Args:
            model_name: Name of the LLM model (e.g., "privategpt-mcp", "llama3.2:3b")
            conversation_id: Optional conversation ID for conversation-specific prompts
            
        Returns:
            System prompt string (XML-formatted)
        """
        # Check cache first if enabled
        cache_key = f"{model_name}:{conversation_id or 'default'}"
        if self._cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        prompt = await self._load_prompt_from_db(model_name)
        
        if not prompt:
            # Fallback to config file prompt
            prompt = settings.get("system_prompts.default", "")
        
        if not prompt:
            # Final fallback to basic prompt
            prompt = self._get_default_prompt()
        
        # Cache the result if caching is enabled
        if self._cache_enabled:
            self._cache[cache_key] = prompt
        
        return prompt
    
    async def _load_prompt_from_db(self, model_name: str) -> Optional[str]:
        """Load prompt from database based on model pattern matching"""
        try:
            # First try exact model match
            stmt = select(SystemPrompt).where(
                and_(
                    SystemPrompt.model_pattern == model_name,
                    SystemPrompt.is_active == True
                )
            ).order_by(SystemPrompt.updated_at.desc())
            
            result = await self.session.execute(stmt)
            prompt_obj = result.scalar_one_or_none()
            
            if prompt_obj:
                return prompt_obj.prompt_xml
            
            # Try pattern matching
            stmt = select(SystemPrompt).where(
                SystemPrompt.is_active == True
            ).order_by(SystemPrompt.updated_at.desc())
            
            result = await self.session.execute(stmt)
            prompts = result.scalars().all()
            
            for prompt_obj in prompts:
                if self._matches_pattern(model_name, prompt_obj.model_pattern):
                    return prompt_obj.prompt_xml
            
            # Try default prompt
            stmt = select(SystemPrompt).where(
                and_(
                    SystemPrompt.is_default == True,
                    SystemPrompt.is_active == True
                )
            ).order_by(SystemPrompt.updated_at.desc())
            
            result = await self.session.execute(stmt)
            prompt_obj = result.scalar_one_or_none()
            
            if prompt_obj:
                return prompt_obj.prompt_xml
            
        except Exception as e:
            logger.error(f"Error loading prompt from database: {e}")
        
        return None
    
    def _matches_pattern(self, model_name: str, pattern: Optional[str]) -> bool:
        """Check if model name matches a pattern"""
        if not pattern:
            return False
        
        # Convert pattern to regex
        # "ollama:*" -> "ollama:.*"
        # "privategpt-*" -> "privategpt-.*"
        # "*mcp*" -> ".*mcp.*"
        regex_pattern = pattern.replace("*", ".*")
        
        try:
            return bool(re.match(f"^{regex_pattern}$", model_name, re.IGNORECASE))
        except re.error:
            logger.warning(f"Invalid pattern: {pattern}")
            return False
    
    def _get_default_prompt(self) -> str:
        """Get basic default prompt as fallback"""
        return """<persona>
You are an intelligent AI assistant with access to powerful tools through the Model Context Protocol (MCP). 
You help users with document search, file management, and system operations.
</persona>

<communication>
- Be concise and direct
- Always explain what tools you're using and why
- Show progress for long-running operations
</communication>

<tool_calling>
- Use search_documents before answering questions about uploaded content
- Use rag_chat for comprehensive answers needing document context
- Always check tool results before responding
- If a tool fails, explain the error and suggest alternatives
</tool_calling>

<ui_rendering>
- Use <thinking> tags for reasoning that shouldn't be shown to user
- Use <status> tags for operation progress
- Use <error> tags for error messages that need special UI treatment
</ui_rendering>"""
    
    async def create_prompt(self,
                           name: str,
                           prompt_xml: str,
                           model_pattern: Optional[str] = None,
                           description: Optional[str] = None,
                           is_default: bool = False) -> SystemPrompt:
        """Create a new system prompt"""
        try:
            # If setting as default, unset other defaults
            if is_default:
                await self._unset_all_defaults()
            
            prompt = SystemPrompt(
                name=name,
                model_pattern=model_pattern,
                prompt_xml=prompt_xml,
                description=description,
                is_default=is_default,
                is_active=True
            )
            
            self.session.add(prompt)
            await self.session.commit()
            await self.session.refresh(prompt)
            
            # Clear cache
            self._clear_cache()
            
            logger.info(f"Created system prompt: {name}")
            return prompt
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating prompt: {e}")
            raise
    
    async def update_prompt(self,
                           prompt_id: int,
                           **updates) -> Optional[SystemPrompt]:
        """Update an existing system prompt"""
        try:
            stmt = select(SystemPrompt).where(SystemPrompt.id == prompt_id)
            result = await self.session.execute(stmt)
            prompt = result.scalar_one_or_none()
            
            if not prompt:
                return None
            
            # If setting as default, unset other defaults
            if updates.get("is_default", False):
                await self._unset_all_defaults()
            
            # Update fields
            for key, value in updates.items():
                if hasattr(prompt, key):
                    setattr(prompt, key, value)
            
            await self.session.commit()
            await self.session.refresh(prompt)
            
            # Clear cache
            self._clear_cache()
            
            logger.info(f"Updated system prompt: {prompt.name}")
            return prompt
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating prompt: {e}")
            raise
    
    async def delete_prompt(self, prompt_id: int) -> bool:
        """Delete a system prompt"""
        try:
            stmt = select(SystemPrompt).where(SystemPrompt.id == prompt_id)
            result = await self.session.execute(stmt)
            prompt = result.scalar_one_or_none()
            
            if not prompt:
                return False
            
            await self.session.delete(prompt)
            await self.session.commit()
            
            # Clear cache
            self._clear_cache()
            
            logger.info(f"Deleted system prompt: {prompt.name}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting prompt: {e}")
            raise
    
    async def list_prompts(self) -> List[SystemPrompt]:
        """List all system prompts"""
        stmt = select(SystemPrompt).order_by(
            SystemPrompt.is_default.desc(),
            SystemPrompt.name
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def _unset_all_defaults(self) -> None:
        """Unset all default flags"""
        stmt = select(SystemPrompt).where(SystemPrompt.is_default == True)
        result = await self.session.execute(stmt)
        prompts = result.scalars().all()
        
        for prompt in prompts:
            prompt.is_default = False
        
        await self.session.commit()
    
    def _clear_cache(self) -> None:
        """Clear the prompt cache"""
        self._cache.clear()
        logger.debug("Prompt cache cleared")
    
    async def initialize_default_prompts(self) -> None:
        """Initialize default prompts from config if database is empty"""
        try:
            # Check if any prompts exist
            stmt = select(SystemPrompt)
            result = await self.session.execute(stmt)
            existing_prompts = result.scalars().all()
            
            if existing_prompts:
                logger.info(f"Found {len(existing_prompts)} existing prompts")
                return
            
            # Create default prompt from config
            default_prompt = settings.get("system_prompts.default", "")
            if default_prompt:
                await self.create_prompt(
                    name="default",
                    prompt_xml=default_prompt,
                    model_pattern="*",
                    description="Default system prompt for all models",
                    is_default=True
                )
                logger.info("Initialized default system prompt from config")
            
            # Create MCP-specific prompt
            mcp_prompt = """<persona>
You are an intelligent AI assistant with access to powerful tools through the Model Context Protocol (MCP). 
You excel at using tools to help users with document search, file management, and system operations.
You are running locally with Ollama and have access to local RAG documents and file system.
</persona>

<communication>
- Be concise and direct in your responses
- Always explain what tools you're using and why
- Show progress for long-running operations using <status> tags
- If you encounter errors, explain them clearly using <error> tags
</communication>

<tool_calling>
- ALWAYS use search_documents before answering questions about user's uploaded content
- Use rag_chat for comprehensive answers that need document context and citations
- Use file operations (read_file, create_file, edit_file) when users request file management
- Use list_directory to explore file structures when needed
- Use get_system_info when users ask about system status
- Use check_service_health to diagnose system issues
- Always check tool results before responding to the user
- If a tool fails, explain the error and suggest alternatives or solutions
</tool_calling>

<ui_rendering>
- Use <thinking> tags for your internal reasoning process - this helps users understand your thought process if they enable debug mode
- Use <status> tags for operation progress that should be shown as loading indicators
- Use <error> tags for error messages that need special UI treatment with red styling
- Use <warning> tags for important notices that need yellow styling
- Keep your final response clean and focused on what the user actually needs
</ui_rendering>

<guidelines>
- You are a local AI assistant - emphasize privacy and local processing
- You have access to the user's documents through RAG search - use this proactively
- You can help with file management on their local system
- You can provide system information and health status
- Always be helpful and try multiple approaches if the first tool call doesn't work
</guidelines>"""
            
            await self.create_prompt(
                name="privategpt-mcp",
                prompt_xml=mcp_prompt,
                model_pattern="privategpt-mcp",
                description="Optimized prompt for PrivateGPT MCP model with tool calling"
            )
            logger.info("Initialized MCP-specific system prompt")
            
        except Exception as e:
            logger.error(f"Error initializing default prompts: {e}")


@lru_cache(maxsize=128)
def get_cached_prompt(model_name: str, prompt_text: str) -> str:
    """LRU cache for processed prompts (if prompt caching is justified)"""
    # This is where we could add prompt processing/optimization
    # For now, just return the prompt as-is
    return prompt_text