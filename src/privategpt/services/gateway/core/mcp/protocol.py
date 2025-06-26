"""
JSON-RPC 2.0 Protocol implementation for MCP.

This module implements the JSON-RPC 2.0 protocol used by MCP for communication
between clients and servers.
"""

import json
import logging
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict
import uuid

from .base import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)


class ProtocolError(Exception):
    """Base exception for protocol-related errors."""
    pass


class JSONRPCError(ProtocolError):
    """JSON-RPC specific error."""
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"JSON-RPC Error {code}: {message}")


# Standard JSON-RPC error codes
class ErrorCodes:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific error codes (custom range)
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002
    AUTHENTICATION_ERROR = -32003
    AUTHORIZATION_ERROR = -32004
    TIMEOUT_ERROR = -32005


class JSONRPCProtocol:
    """
    Implements JSON-RPC 2.0 protocol for MCP communication.
    
    This class handles:
    - Message formatting and parsing
    - Request/response correlation
    - Error handling
    - Batch requests
    """
    
    def __init__(self):
        self._pending_requests: Dict[Union[str, int], MCPRequest] = {}
        
    def create_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Optional[Union[str, int]] = None) -> str:
        """
        Create a JSON-RPC request.
        
        Args:
            method: The RPC method to call
            params: Optional parameters for the method
            request_id: Optional request ID (generated if not provided)
            
        Returns:
            JSON-encoded request string
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
            
        request = MCPRequest(
            jsonrpc="2.0",
            method=method,
            params=params,
            id=request_id
        )
        
        # Store pending request for correlation
        self._pending_requests[request_id] = request
        
        # Convert to dict and serialize
        request_dict = {
            "jsonrpc": request.jsonrpc,
            "method": request.method,
            "id": request.id
        }
        if request.params is not None:
            request_dict["params"] = request.params
            
        return json.dumps(request_dict)
    
    def create_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a JSON-RPC notification (no response expected).
        
        Args:
            method: The RPC method to call
            params: Optional parameters for the method
            
        Returns:
            JSON-encoded notification string
        """
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params is not None:
            notification["params"] = params
            
        return json.dumps(notification)
    
    def parse_response(self, response_str: str) -> MCPResponse:
        """
        Parse a JSON-RPC response.
        
        Args:
            response_str: JSON-encoded response string
            
        Returns:
            MCPResponse object
            
        Raises:
            JSONRPCError: If response contains an error
            ProtocolError: If response is malformed
        """
        try:
            response_data = json.loads(response_str)
        except json.JSONDecodeError as e:
            raise ProtocolError(f"Invalid JSON response: {e}")
        
        # Validate response structure
        if not isinstance(response_data, dict):
            raise ProtocolError("Response must be a JSON object")
            
        if response_data.get("jsonrpc") != "2.0":
            raise ProtocolError("Invalid JSON-RPC version")
            
        response = MCPResponse(
            jsonrpc=response_data.get("jsonrpc", "2.0"),
            result=response_data.get("result"),
            error=response_data.get("error"),
            id=response_data.get("id")
        )
        
        # Check if this is an error response
        if response.error:
            error_code = response.error.get("code", ErrorCodes.INTERNAL_ERROR)
            error_message = response.error.get("message", "Unknown error")
            error_data = response.error.get("data")
            raise JSONRPCError(error_code, error_message, error_data)
        
        # Remove from pending requests
        if response.id in self._pending_requests:
            del self._pending_requests[response.id]
            
        return response
    
    def create_batch_request(self, requests: List[tuple[str, Optional[Dict[str, Any]]]]) -> str:
        """
        Create a batch JSON-RPC request.
        
        Args:
            requests: List of (method, params) tuples
            
        Returns:
            JSON-encoded batch request string
        """
        batch = []
        
        for method, params in requests:
            request_id = str(uuid.uuid4())
            request = {
                "jsonrpc": "2.0",
                "method": method,
                "id": request_id
            }
            if params is not None:
                request["params"] = params
                
            batch.append(request)
            
            # Track pending request
            self._pending_requests[request_id] = MCPRequest(
                jsonrpc="2.0",
                method=method,
                params=params,
                id=request_id
            )
            
        return json.dumps(batch)
    
    def parse_batch_response(self, response_str: str) -> List[MCPResponse]:
        """
        Parse a batch JSON-RPC response.
        
        Args:
            response_str: JSON-encoded response string
            
        Returns:
            List of MCPResponse objects
        """
        try:
            response_data = json.loads(response_str)
        except json.JSONDecodeError as e:
            raise ProtocolError(f"Invalid JSON response: {e}")
        
        if not isinstance(response_data, list):
            raise ProtocolError("Batch response must be a JSON array")
            
        responses = []
        for item in response_data:
            response = MCPResponse(
                jsonrpc=item.get("jsonrpc", "2.0"),
                result=item.get("result"),
                error=item.get("error"),
                id=item.get("id")
            )
            responses.append(response)
            
            # Remove from pending requests
            if response.id in self._pending_requests:
                del self._pending_requests[response.id]
                
        return responses
    
    def create_error_response(self, request_id: Optional[Union[str, int]], code: int, message: str, data: Optional[Any] = None) -> str:
        """
        Create a JSON-RPC error response.
        
        Args:
            request_id: ID of the request that caused the error
            code: Error code
            message: Error message
            data: Optional additional error data
            
        Returns:
            JSON-encoded error response string
        """
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": request_id
        }
        
        if data is not None:
            error_response["error"]["data"] = data
            
        return json.dumps(error_response)
    
    def is_request_pending(self, request_id: Union[str, int]) -> bool:
        """Check if a request is still pending."""
        return request_id in self._pending_requests
    
    def get_pending_request_count(self) -> int:
        """Get the number of pending requests."""
        return len(self._pending_requests)
    
    def clear_pending_requests(self) -> None:
        """Clear all pending requests (use with caution)."""
        self._pending_requests.clear()


# MCP-specific protocol methods
class MCPMethods:
    """Standard MCP method names."""
    
    # Tool methods
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    
    # Resource methods
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_WRITE = "resources/write"
    
    # Prompt methods
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    
    # Server methods
    INITIALIZE = "initialize"
    SHUTDOWN = "shutdown"
    PING = "ping"


def format_tool_call_params(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format parameters for a tool call request.
    
    Args:
        tool_name: Name of the tool to call
        arguments: Arguments to pass to the tool
        
    Returns:
        Formatted parameters dict
    """
    return {
        "name": tool_name,
        "arguments": arguments
    }


def format_resource_read_params(uri: str) -> Dict[str, Any]:
    """
    Format parameters for a resource read request.
    
    Args:
        uri: URI of the resource to read
        
    Returns:
        Formatted parameters dict
    """
    return {
        "uri": uri
    }