"""
Integration tests for MCP tool discovery and registry functionality.

These tests verify that the enhanced tool registry works correctly with
caching, validation, and provider-specific formatting.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from ..enhanced_tool_registry import (
    EnhancedToolRegistry, Tool, ToolParameter, ProviderType, ProviderFormatter
)
from ..unified_mcp_client import MCPClient, MCPConfig, MCPServerConfig, TransportConfig


class TestToolValidation:
    """Test tool validation functionality."""
    
    def test_valid_tool_data(self):
        """Test validation of valid tool data."""
        registry = EnhancedToolRegistry()
        
        valid_tool = {
            "name": "search_documents",
            "description": "Search through document collection using semantic similarity",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results", "default": 10}
                },
                "required": ["query"]
            },
            "category": "search"
        }
        
        errors = registry._validate_tool_data(valid_tool)
        assert errors == []
    
    def test_invalid_tool_data(self):
        """Test validation of invalid tool data."""
        registry = EnhancedToolRegistry()
        
        # Missing required fields
        invalid_tool = {
            "name": "bad_tool"
            # Missing description
        }
        
        errors = registry._validate_tool_data(invalid_tool)
        assert len(errors) > 0
        assert any("description" in error for error in errors)
    
    def test_tool_parameter_validation(self):
        """Test tool parameter validation."""
        param = ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True
        )
        
        schema = param.to_json_schema()
        assert schema["type"] == "string"
        assert schema["description"] == "Search query"
    
    def test_tool_argument_validation(self):
        """Test tool argument validation against schema."""
        tool = Tool(
            name="test_tool",
            description="Test tool",
            parameters=[
                ToolParameter("query", "string", "Search query", required=True),
                ToolParameter("limit", "integer", "Result limit", default=10)
            ],
            server_name="test"
        )
        
        # Valid arguments
        valid_args = {"query": "test search", "limit": 5}
        errors = tool.validate_arguments(valid_args)
        assert errors == []
        
        # Invalid arguments (missing required)
        invalid_args = {"limit": 5}  # Missing query
        errors = tool.validate_arguments(invalid_args)
        assert len(errors) > 0


class TestProviderFormatting:
    """Test provider-specific tool formatting."""
    
    def setup_method(self):
        """Set up test tool."""
        self.test_tool = Tool(
            name="search_docs",
            description="Search documents",
            parameters=[
                ToolParameter("query", "string", "Search query", required=True),
                ToolParameter("limit", "integer", "Max results", default=10)
            ],
            server_name="rag",
            category="search"
        )
    
    def test_openai_formatting(self):
        """Test OpenAI function calling format."""
        formatted = ProviderFormatter.format_for_openai(self.test_tool)
        
        assert formatted["type"] == "function"
        assert "function" in formatted
        assert formatted["function"]["name"] == "search_docs"
        assert formatted["function"]["description"] == "Search documents"
        assert "parameters" in formatted["function"]
        
        # Check parameter schema
        params = formatted["function"]["parameters"]
        assert params["type"] == "object"
        assert "query" in params["properties"]
        assert "limit" in params["properties"]
        assert params["required"] == ["query"]
    
    def test_anthropic_formatting(self):
        """Test Anthropic tools format."""
        formatted = ProviderFormatter.format_for_anthropic(self.test_tool)
        
        assert formatted["name"] == "search_docs"
        assert formatted["description"] == "Search documents"
        assert "input_schema" in formatted
        
        schema = formatted["input_schema"]
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert schema["required"] == ["query"]
    
    def test_ollama_formatting(self):
        """Test Ollama function calling format."""
        formatted = ProviderFormatter.format_for_ollama(self.test_tool)
        
        assert formatted["type"] == "function"
        assert "function" in formatted
        assert formatted["function"]["name"] == "search_docs"
        
        # Ollama formatting should simplify complex schemas
        params = formatted["function"]["parameters"]
        assert params["type"] == "object"
    
    def test_provider_validation(self):
        """Test provider-specific validation."""
        # Test Ollama limitations
        long_desc_tool = Tool(
            name="test",
            description="A" * 300,  # Too long for Ollama
            parameters=[],
            server_name="test"
        )
        
        errors = ProviderFormatter.validate_for_provider(long_desc_tool, ProviderType.OLLAMA)
        assert len(errors) > 0
        assert any("too long" in error.lower() for error in errors)
        
        # Test OpenAI parameter limits
        many_params_tool = Tool(
            name="test",
            description="Test tool",
            parameters=[ToolParameter(f"param{i}", "string", f"Param {i}") for i in range(15)],
            server_name="test"
        )
        
        errors = ProviderFormatter.validate_for_provider(many_params_tool, ProviderType.OPENAI)
        assert len(errors) > 0
        assert any("many parameters" in error.lower() for error in errors)


class TestToolRegistry:
    """Test enhanced tool registry functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_redis = AsyncMock()
        mock_redis.connect = AsyncMock()
        mock_redis.redis = AsyncMock()
        return mock_redis
    
    @pytest.fixture
    def registry(self, mock_redis):
        """Create registry with mocked Redis."""
        with patch('privategpt.services.gateway.core.mcp.enhanced_tool_registry.get_redis_client', return_value=mock_redis):
            return EnhancedToolRegistry()
    
    @pytest.mark.asyncio
    async def test_register_tools(self, registry):
        """Test tool registration with validation."""
        tools_data = [
            {
                "name": "search_documents",
                "description": "Search through documents using semantic similarity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Max results", "default": 10}
                    },
                    "required": ["query"]
                },
                "category": "search"
            },
            {
                "name": "invalid_tool",
                "description": "x"  # Too short
            }
        ]
        
        valid_tools, errors = await registry.register_tools("rag", tools_data)
        
        # Should register valid tool and report error for invalid one
        assert len(valid_tools) == 1
        assert "rag.search_documents" in valid_tools
        assert len(errors) > 0
        
        # Check tool is in registry
        tool = await registry.get_tool("rag.search_documents")
        assert tool is not None
        assert tool.name == "rag.search_documents"
        assert tool.server_name == "rag"
    
    def test_get_tools_for_llm(self, registry):
        """Test getting tools formatted for LLM providers."""
        # Add a test tool
        tool = Tool(
            name="test.search",
            description="Test search",
            parameters=[
                ToolParameter("query", "string", "Search query", required=True)
            ],
            server_name="test",
            category="search"
        )
        registry.tools["test.search"] = tool
        
        # Test different providers
        openai_tools = registry.get_tools_for_llm("openai")
        assert len(openai_tools) == 1
        assert openai_tools[0]["type"] == "function"
        
        anthropic_tools = registry.get_tools_for_llm("anthropic")
        assert len(anthropic_tools) == 1
        assert "input_schema" in anthropic_tools[0]
        
        ollama_tools = registry.get_tools_for_llm("ollama")
        assert len(ollama_tools) == 1
        assert ollama_tools[0]["type"] == "function"
    
    def test_filter_by_category(self, registry):
        """Test filtering tools by category."""
        # Add tools with different categories
        search_tool = Tool("search", "Search tool", [], "test", category="search")
        calc_tool = Tool("calc", "Calculator tool", [], "test", category="calculation")
        
        registry.tools["search"] = search_tool
        registry.tools["calc"] = calc_tool
        
        # Filter by search category
        search_tools = registry.get_tools_for_llm("openai", categories=["search"])
        assert len(search_tools) == 1
        
        # Filter by calculation category  
        calc_tools = registry.get_tools_for_llm("openai", categories=["calculation"])
        assert len(calc_tools) == 1
        
        # No filter - get all
        all_tools = registry.get_tools_for_llm("openai")
        assert len(all_tools) == 2
    
    def test_get_tools_by_category(self, registry):
        """Test getting tools organized by category."""
        # Add tools with categories
        search_tool = Tool("search", "Search tool", [], "test", category="search")
        calc_tool = Tool("calc", "Calculator tool", [], "test", category="calculation")
        uncategorized_tool = Tool("other", "Other tool", [], "test")
        
        registry.tools["search"] = search_tool
        registry.tools["calc"] = calc_tool
        registry.tools["other"] = uncategorized_tool
        
        categorized = registry.get_tools_by_category()
        
        assert "search" in categorized
        assert "calculation" in categorized
        assert "uncategorized" in categorized
        
        assert len(categorized["search"]) == 1
        assert len(categorized["calculation"]) == 1
        assert len(categorized["uncategorized"]) == 1
    
    def test_registry_stats(self, registry):
        """Test registry statistics."""
        # Add test tools
        tool1 = Tool("tool1", "Tool 1", [], "server1", category="search")
        tool2 = Tool("tool2", "Tool 2", [], "server1", category="calculation")
        tool3 = Tool("tool3", "Tool 3", [], "server2", category="search")
        
        registry.tools["tool1"] = tool1
        registry.tools["tool2"] = tool2
        registry.tools["tool3"] = tool3
        
        registry.server_tools["server1"] = ["tool1", "tool2"]
        registry.server_tools["server2"] = ["tool3"]
        registry.categories = {"search", "calculation"}
        
        stats = registry.get_registry_stats()
        
        assert stats["total_tools"] == 3
        assert stats["servers"] == 2
        assert "search" in stats["categories"]
        assert "calculation" in stats["categories"]
        assert stats["tools_by_server"]["server1"] == 2
        assert stats["tools_by_server"]["server2"] == 1


class TestMCPClientIntegration:
    """Test MCP client integration with tool discovery."""
    
    @pytest.fixture
    def mock_transport(self):
        """Mock HTTP transport."""
        mock = AsyncMock()
        mock.connect = AsyncMock()
        mock.execute = AsyncMock()
        return mock
    
    @pytest.fixture
    def mcp_client(self, mock_transport):
        """Create MCP client with mocked transport."""
        config = MCPConfig(
            transport=TransportConfig(),
            servers=[
                MCPServerConfig(name="test", base_url="http://test:8000")
            ]
        )
        
        client = MCPClient(config)
        client.transport = mock_transport
        return client
    
    @pytest.mark.asyncio
    async def test_server_discovery(self, mcp_client, mock_transport):
        """Test discovering tools from MCP server."""
        # Mock server response
        mock_transport.execute.return_value = {
            "tools": [
                {
                    "name": "search_docs",
                    "description": "Search documents using semantic similarity",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            ]
        }
        
        await mcp_client.initialize()
        
        # Verify transport was called
        mock_transport.connect.assert_called_once()
        mock_transport.execute.assert_called_with(
            "http://test:8000",
            "tools/list",
            {},
            None
        )
        
        # Verify tools were registered
        tools = mcp_client.get_tools_for_llm("openai")
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "test.search_docs"
    
    @pytest.mark.asyncio
    async def test_tool_execution_flow(self, mcp_client, mock_transport):
        """Test complete tool execution flow."""
        # Set up mock responses
        mock_transport.execute.side_effect = [
            # Tool discovery response
            {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "input": {"type": "string"}
                            },
                            "required": ["input"]
                        }
                    }
                ]
            },
            # Tool execution response
            {"result": "Tool executed successfully"}
        ]
        
        await mcp_client.initialize()
        
        # Test tool execution (this would normally require approval)
        from ..unified_mcp_client import ToolCall, UserContext
        
        tool_call = ToolCall(
            id="test123",
            tool_name="test.test_tool",
            arguments={"input": "test value"},
            user_id="user1",
            conversation_id="conv1"
        )
        
        user_context = UserContext(
            user_id="user1",
            conversation_id="conv1",
            role="user",
            auto_approve_tools=True  # Skip approval for test
        )
        
        result = await mcp_client.execute_tool(tool_call, user_context)
        
        assert result.success
        assert result.result == {"result": "Tool executed successfully"}


class TestCaching:
    """Test tool registry caching functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client with data storage."""
        mock_redis = AsyncMock()
        mock_redis.connect = AsyncMock()
        mock_redis.redis = AsyncMock()
        
        # Simple in-memory storage for testing
        self.cache_data = {}
        
        async def mock_setex(key, ttl, value):
            self.cache_data[key] = value
        
        async def mock_get(key):
            return self.cache_data.get(key)
        
        mock_redis.redis.setex = mock_setex
        mock_redis.redis.get = mock_get
        
        return mock_redis
    
    @pytest.mark.asyncio
    async def test_tool_caching(self, mock_redis):
        """Test that tools are properly cached."""
        with patch('privategpt.services.gateway.core.mcp.enhanced_tool_registry.get_redis_client', return_value=mock_redis):
            registry = EnhancedToolRegistry()
            
            tools_data = [
                {
                    "name": "test_tool",
                    "description": "A test tool for caching",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        }
                    }
                }
            ]
            
            await registry.register_tools("test_server", tools_data)
            
            # Verify tool was cached
            cache_key = "mcp:tool:test_server.test_tool"
            assert cache_key in self.cache_data
            
            cached_data = json.loads(self.cache_data[cache_key])
            assert cached_data["name"] == "test_server.test_tool"
            assert cached_data["description"] == "A test tool for caching"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])