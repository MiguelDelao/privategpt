"""
Enhanced Tool Registry with caching, validation, and provider-specific formatting.

This registry provides:
- Redis-based caching for tool definitions
- Tool schema validation
- Provider-specific formatting with validation
- Category management for UI organization
- Health checking for tool availability
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

import jsonschema
from jsonschema import ValidationError

from privategpt.infra.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GENERIC = "generic"


@dataclass
class ToolParameter:
    """Tool parameter definition with validation."""
    name: str
    type: str  # JSON Schema type
    description: str
    required: bool = False
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema property."""
        schema = {
            "type": self.type,
            "description": self.description
        }
        
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
            
        return schema


@dataclass
class Tool:
    """Enhanced tool definition with metadata."""
    name: str
    description: str
    parameters: List[ToolParameter]
    server_name: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    examples: Optional[List[Dict[str, Any]]] = None
    last_updated: Optional[datetime] = None
    health_status: str = "unknown"  # "healthy", "unhealthy", "unknown"
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert tool to JSON Schema format."""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> List[str]:
        """Validate tool arguments against schema. Returns list of errors."""
        try:
            schema = self.to_json_schema()
            jsonschema.validate(arguments, schema)
            return []
        except ValidationError as e:
            return [str(e)]
        except Exception as e:
            return [f"Validation error: {e}"]


class ProviderFormatter:
    """Provider-specific tool formatting and validation."""
    
    @staticmethod
    def format_for_openai(tool: Tool) -> Dict[str, Any]:
        """Format tool for OpenAI function calling."""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.to_json_schema()
            }
        }
    
    @staticmethod
    def format_for_anthropic(tool: Tool) -> Dict[str, Any]:
        """Format tool for Anthropic tools."""
        # Anthropic requires tool names to match pattern '^[a-zA-Z0-9_-]{1,128}$'
        # Replace dots with underscores
        sanitized_name = tool.name.replace(".", "_")
        
        return {
            "name": sanitized_name,
            "description": tool.description,
            "input_schema": tool.to_json_schema()
        }
    
    @staticmethod
    def format_for_ollama(tool: Tool) -> Dict[str, Any]:
        """Format tool for Ollama function calling."""
        # Ollama has some limitations, simplify complex schemas
        schema = tool.to_json_schema()
        
        # Simplify nested objects for Ollama
        simplified_props = {}
        for prop_name, prop_schema in schema.get("properties", {}).items():
            if prop_schema.get("type") == "object":
                # Flatten complex objects to string for Ollama
                simplified_props[prop_name] = {
                    "type": "string",
                    "description": f"{prop_schema.get('description', '')} (JSON format)"
                }
            else:
                simplified_props[prop_name] = prop_schema
        
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": simplified_props,
                    "required": schema.get("required", [])
                }
            }
        }
    
    @staticmethod
    def format_for_generic(tool: Tool) -> Dict[str, Any]:
        """Generic tool format."""
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.to_json_schema(),
            "category": tool.category,
            "tags": tool.tags or []
        }
    
    @staticmethod
    def validate_for_provider(tool: Tool, provider: ProviderType) -> List[str]:
        """Validate tool compatibility with provider."""
        errors = []
        
        if provider == ProviderType.OLLAMA:
            # Ollama has stricter limits
            if len(tool.description) > 200:
                errors.append("Description too long for Ollama (max 200 chars)")
            
            # Check for complex nested objects
            for param in tool.parameters:
                if param.type == "object":
                    errors.append(f"Parameter '{param.name}': Ollama has limited object support")
        
        elif provider == ProviderType.OPENAI:
            # OpenAI function calling limits
            if len(tool.parameters) > 10:
                errors.append("Too many parameters for OpenAI (max 10)")
        
        elif provider == ProviderType.ANTHROPIC:
            # Anthropic tools limits
            if len(tool.name) > 64:
                errors.append("Tool name too long for Anthropic (max 64 chars)")
        
        return errors


class EnhancedToolRegistry:
    """Enhanced tool registry with caching and validation."""
    
    def __init__(self, cache_ttl: int = 3600):
        self.tools: Dict[str, Tool] = {}
        self.server_tools: Dict[str, List[str]] = {}
        self.categories: Set[str] = set()
        self.redis = get_redis_client()
        self.cache_ttl = cache_ttl
        self.formatter = ProviderFormatter()
        
        # Tool validation schema
        self.tool_schema = {
            "type": "object",
            "required": ["name", "description"],
            "properties": {
                "name": {"type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$"},
                "description": {"type": "string", "minLength": 10, "maxLength": 500},
                "inputSchema": {"type": "object"},
                "category": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}}
            }
        }
    
    async def register_tools(self, server_name: str, tools_data: List[Dict[str, Any]]):
        """Register tools from an MCP server with validation and caching."""
        valid_tools = []
        errors = []
        
        for tool_data in tools_data:
            try:
                # Validate tool data
                validation_errors = self._validate_tool_data(tool_data)
                if validation_errors:
                    errors.extend([f"Tool {tool_data.get('name', 'unknown')}: {err}" for err in validation_errors])
                    continue
                
                # Create tool instance
                tool = self._create_tool_from_data(server_name, tool_data)
                
                # Add server prefix to avoid conflicts
                full_name = f"{server_name}.{tool.name}"
                tool.name = full_name
                
                # Cache tool definition
                await self._cache_tool(tool)
                
                # Register in memory
                self.tools[full_name] = tool
                valid_tools.append(full_name)
                
                # Track categories
                if tool.category:
                    self.categories.add(tool.category)
                
            except Exception as e:
                errors.append(f"Tool {tool_data.get('name', 'unknown')}: {e}")
        
        # Update server tools mapping
        self.server_tools[server_name] = valid_tools
        
        # Cache server tools list
        await self._cache_server_tools(server_name, valid_tools)
        
        if errors:
            logger.warning(f"Tool registration errors for {server_name}: {errors}")
        
        logger.info(f"Registered {len(valid_tools)} tools from server {server_name}")
        return valid_tools, errors
    
    def _validate_tool_data(self, tool_data: Dict[str, Any]) -> List[str]:
        """Validate raw tool data from MCP server."""
        try:
            jsonschema.validate(tool_data, self.tool_schema)
            return []
        except ValidationError as e:
            return [str(e)]
        except Exception as e:
            return [f"Validation error: {e}"]
    
    def _create_tool_from_data(self, server_name: str, tool_data: Dict[str, Any]) -> Tool:
        """Create Tool instance from MCP server data."""
        # Parse parameters from inputSchema
        parameters = []
        input_schema = tool_data.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        for param_name, param_schema in properties.items():
            parameters.append(ToolParameter(
                name=param_name,
                type=param_schema.get("type", "string"),
                description=param_schema.get("description", ""),
                required=param_name in required,
                enum=param_schema.get("enum"),
                default=param_schema.get("default")
            ))
        
        return Tool(
            name=tool_data["name"],
            description=tool_data["description"],
            parameters=parameters,
            server_name=server_name,
            category=tool_data.get("category"),
            tags=tool_data.get("tags"),
            examples=tool_data.get("examples"),
            last_updated=datetime.utcnow(),
            health_status="healthy"
        )
    
    async def _cache_tool(self, tool: Tool):
        """Cache tool definition in Redis."""
        try:
            await self.redis.connect()
            cache_key = f"mcp:tool:{tool.name}"
            tool_data = asdict(tool)
            # Convert datetime to string for JSON serialization
            tool_data["last_updated"] = tool.last_updated.isoformat() if tool.last_updated else None
            
            await self.redis.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(tool_data, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to cache tool {tool.name}: {e}")
    
    async def _cache_server_tools(self, server_name: str, tool_names: List[str]):
        """Cache server tools list in Redis."""
        try:
            await self.redis.connect()
            cache_key = f"mcp:server:{server_name}:tools"
            await self.redis.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(tool_names)
            )
        except Exception as e:
            logger.warning(f"Failed to cache server tools for {server_name}: {e}")
    
    async def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get tool definition with cache fallback."""
        # Check memory first
        if tool_name in self.tools:
            return self.tools[tool_name]
        
        # Check cache
        try:
            await self.redis.connect()
            cache_key = f"mcp:tool:{tool_name}"
            cached_data = await self.redis.redis.get(cache_key)
            
            if cached_data:
                tool_data = json.loads(cached_data)
                # Reconstruct Tool object
                # This is simplified - in production you'd have proper deserialization
                return self._deserialize_tool(tool_data)
                
        except Exception as e:
            logger.warning(f"Failed to get tool from cache {tool_name}: {e}")
        
        return None
    
    def _deserialize_tool(self, tool_data: Dict[str, Any]) -> Tool:
        """Deserialize tool from cached data."""
        # Convert parameter data back to ToolParameter objects
        parameters = []
        for param_data in tool_data.get("parameters", []):
            if isinstance(param_data, dict):
                parameters.append(ToolParameter(**param_data))
        
        # Convert datetime string back
        last_updated = None
        if tool_data.get("last_updated"):
            last_updated = datetime.fromisoformat(tool_data["last_updated"])
        
        return Tool(
            name=tool_data["name"],
            description=tool_data["description"],
            parameters=parameters,
            server_name=tool_data["server_name"],
            category=tool_data.get("category"),
            tags=tool_data.get("tags"),
            examples=tool_data.get("examples"),
            last_updated=last_updated,
            health_status=tool_data.get("health_status", "unknown")
        )
    
    def get_tools_for_llm(self, provider: str, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get tools formatted for specific LLM provider with optional filtering."""
        provider_type = ProviderType(provider.lower()) if provider.lower() in [p.value for p in ProviderType] else ProviderType.GENERIC
        
        formatted_tools = []
        validation_errors = []
        
        for tool in self.tools.values():
            # Filter by categories if specified
            if categories and tool.category not in categories:
                continue
            
            # Validate tool for provider
            errors = self.formatter.validate_for_provider(tool, provider_type)
            if errors:
                validation_errors.extend([f"{tool.name}: {err}" for err in errors])
                continue
            
            # Format tool for provider
            try:
                if provider_type == ProviderType.OPENAI:
                    formatted_tool = self.formatter.format_for_openai(tool)
                elif provider_type == ProviderType.ANTHROPIC:
                    formatted_tool = self.formatter.format_for_anthropic(tool)
                elif provider_type == ProviderType.OLLAMA:
                    formatted_tool = self.formatter.format_for_ollama(tool)
                else:
                    formatted_tool = self.formatter.format_for_generic(tool)
                
                formatted_tools.append(formatted_tool)
                
            except Exception as e:
                validation_errors.append(f"{tool.name}: formatting error - {e}")
        
        if validation_errors:
            logger.warning(f"Tool formatting errors for {provider}: {validation_errors}")
        
        logger.info(f"Formatted {len(formatted_tools)} tools for {provider}")
        return formatted_tools
    
    def get_tools_by_category(self) -> Dict[str, List[Tool]]:
        """Get tools organized by category."""
        categorized = {}
        
        for tool in self.tools.values():
            category = tool.category or "uncategorized"
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(tool)
        
        return categorized
    
    def get_server_tools(self, server_name: str) -> List[Tool]:
        """Get all tools from a specific server."""
        tool_names = self.server_tools.get(server_name, [])
        return [self.tools[name] for name in tool_names if name in self.tools]
    
    async def health_check_tools(self) -> Dict[str, str]:
        """Check health status of all tools/servers."""
        health_status = {}
        
        for server_name in self.server_tools:
            try:
                # This would ping the actual MCP server
                # For now, just mark as healthy if we have tools
                tools = self.get_server_tools(server_name)
                health_status[server_name] = "healthy" if tools else "no_tools"
            except Exception as e:
                health_status[server_name] = f"unhealthy: {e}"
        
        return health_status
    
    async def clear_cache(self, server_name: Optional[str] = None):
        """Clear tool cache for server or all servers."""
        try:
            await self.redis.connect()
            
            if server_name:
                # Clear specific server
                tool_names = self.server_tools.get(server_name, [])
                keys_to_delete = [f"mcp:tool:{name}" for name in tool_names]
                keys_to_delete.append(f"mcp:server:{server_name}:tools")
            else:
                # Clear all MCP cache
                keys_pattern = "mcp:*"
                keys_to_delete = await self.redis.redis.keys(keys_pattern)
            
            if keys_to_delete:
                await self.redis.redis.delete(*keys_to_delete)
                logger.info(f"Cleared {len(keys_to_delete)} cache entries")
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_tools": len(self.tools),
            "servers": len(self.server_tools),
            "categories": list(self.categories),
            "tools_by_server": {
                server: len(tools) for server, tools in self.server_tools.items()
            },
            "tools_by_category": {
                category: len(tools) for category, tools in self.get_tools_by_category().items()
            }
        }