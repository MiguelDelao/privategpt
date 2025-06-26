"""
Tool Registry for managing MCP tools.

This module handles tool discovery, caching, and access control for MCP tools.
It maintains a registry of available tools and their approval requirements.
"""

import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

from .base import Tool, ToolParameter, ToolApprovalStatus

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Manages the registry of available MCP tools.
    
    This class is responsible for:
    - Storing discovered tools from MCP servers
    - Providing tool schemas to the LLM
    - Managing tool approval requirements
    - Caching tool definitions
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._tool_categories: Dict[str, Set[str]] = {}
        self._last_discovery: Optional[datetime] = None
        self._discovery_ttl = timedelta(minutes=5)  # Refresh tools every 5 minutes
        
        # Define which tools require approval (can be configured)
        self._approval_required_tools = {
            "create_file", 
            "edit_file", 
            "delete_file",
            "execute_command",
            "modify_system_settings"
        }
        
        # Define which tools can be auto-approved for certain roles
        self._auto_approve_rules = {
            "admin": ["*"],  # Admins can use all tools
            "developer": ["calculator", "get_current_time", "search_documents", "read_file"],
            "user": ["calculator", "get_current_time", "search_documents"]
        }
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool in the registry."""
        # Set approval requirements based on tool name
        if tool.name in self._approval_required_tools:
            tool.requires_approval = True
            
        # Set auto-approval roles
        for role, allowed_tools in self._auto_approve_rules.items():
            if "*" in allowed_tools or tool.name in allowed_tools:
                if tool.auto_approve_for is None:
                    tool.auto_approve_for = []
                tool.auto_approve_for.append(role)
        
        self._tools[tool.name] = tool
        
        # Categorize tool
        if tool.category:
            if tool.category not in self._tool_categories:
                self._tool_categories[tool.category] = set()
            self._tool_categories[tool.category].add(tool.name)
            
        logger.info(f"Registered tool: {tool.name} (requires_approval={tool.requires_approval})")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a specific category."""
        tool_names = self._tool_categories.get(category, set())
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def get_tools_for_user(self, user_role: str) -> List[Tool]:
        """Get tools available for a specific user role."""
        available_tools = []
        allowed_tools = self._auto_approve_rules.get(user_role, [])
        
        for tool in self._tools.values():
            # Include tool if:
            # 1. User role has wildcard access
            # 2. Tool is in user's allowed list
            # 3. Tool doesn't require approval
            if ("*" in allowed_tools or 
                tool.name in allowed_tools or 
                not tool.requires_approval):
                available_tools.append(tool)
                
        return available_tools
    
    def get_tools_for_llm(self, user_role: str, include_approval_required: bool = True) -> List[Dict]:
        """
        Get tool schemas formatted for LLM consumption.
        
        Args:
            user_role: The role of the current user
            include_approval_required: Whether to include tools that require approval
            
        Returns:
            List of tool schemas in JSON format
        """
        tools = []
        
        for tool in self._tools.values():
            # Skip tools that require approval if not requested
            if tool.requires_approval and not include_approval_required:
                continue
                
            # Skip tools user doesn't have any access to
            if user_role not in tool.auto_approve_for and tool.requires_approval:
                continue
                
            tool_schema = tool.to_json_schema()
            
            # Add metadata about approval requirements
            tool_schema["requires_approval"] = tool.requires_approval
            tool_schema["auto_approved_for_user"] = user_role in (tool.auto_approve_for or [])
            
            tools.append(tool_schema)
            
        return tools
    
    def should_refresh(self) -> bool:
        """Check if tool discovery should be refreshed."""
        if self._last_discovery is None:
            return True
        return datetime.now() - self._last_discovery > self._discovery_ttl
    
    def mark_discovery_complete(self) -> None:
        """Mark that tool discovery has been completed."""
        self._last_discovery = datetime.now()
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._tool_categories.clear()
        self._last_discovery = None
        
    def validate_tool_call(self, tool_name: str, arguments: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate that a tool call has the correct arguments.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return False, f"Unknown tool: {tool_name}"
            
        # Check required parameters
        for param in tool.parameters:
            if param.required and param.name not in arguments:
                return False, f"Missing required parameter: {param.name}"
                
        # Check parameter types (basic validation)
        for param in tool.parameters:
            if param.name in arguments:
                value = arguments[param.name]
                expected_type = param.type
                
                # Basic type checking
                if expected_type == "string" and not isinstance(value, str):
                    return False, f"Parameter {param.name} must be a string"
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return False, f"Parameter {param.name} must be a number"
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return False, f"Parameter {param.name} must be a boolean"
                    
                # Check enum values
                if param.enum and value not in param.enum:
                    return False, f"Parameter {param.name} must be one of: {param.enum}"
                    
        return True, None


# Example tool definitions for testing
def create_example_tools() -> List[Tool]:
    """Create example tool definitions."""
    return [
        Tool(
            name="calculator",
            description="Perform basic mathematical operations",
            category="calculation",
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description="The operation to perform",
                    required=True,
                    enum=["add", "subtract", "multiply", "divide", "power"]
                ),
                ToolParameter(
                    name="a",
                    type="number",
                    description="First number",
                    required=True
                ),
                ToolParameter(
                    name="b",
                    type="number",
                    description="Second number",
                    required=True
                )
            ]
        ),
        Tool(
            name="get_current_time",
            description="Get the current date and time",
            category="utility",
            parameters=[
                ToolParameter(
                    name="timezone",
                    type="string",
                    description="Timezone (e.g., 'UTC', 'US/Eastern')",
                    required=False,
                    default="UTC"
                ),
                ToolParameter(
                    name="format",
                    type="string",
                    description="Output format",
                    required=False,
                    enum=["iso", "human", "unix"],
                    default="iso"
                )
            ]
        ),
        Tool(
            name="search_documents",
            description="Search through uploaded documents using semantic similarity",
            category="search",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query",
                    required=True
                ),
                ToolParameter(
                    name="context",
                    type="string",
                    description="Optional search context (e.g., '@collection:reports')",
                    required=False
                ),
                ToolParameter(
                    name="limit",
                    type="number",
                    description="Maximum number of results",
                    required=False,
                    default=10
                )
            ]
        )
    ]