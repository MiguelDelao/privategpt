"""
HTTP Transport implementation for MCP.

This module implements the HTTP transport layer for MCP communication,
allowing the gateway to communicate with MCP servers over HTTP.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
import httpx

from ..base import TransportType, MCPServerConfig
from ..protocol import JSONRPCProtocol, ProtocolError, JSONRPCError

logger = logging.getLogger(__name__)


class HTTPTransport:
    """
    HTTP transport implementation for MCP.
    
    This transport communicates with MCP servers using HTTP POST requests
    with JSON-RPC payloads.
    """
    
    def __init__(self, config: MCPServerConfig):
        """
        Initialize HTTP transport.
        
        Args:
            config: Server configuration with HTTP settings
        """
        if config.transport_type != TransportType.HTTP:
            raise ValueError(f"Invalid transport type: {config.transport_type}")
            
        if not config.base_url:
            raise ValueError("HTTP transport requires base_url")
            
        self.config = config
        self.protocol = JSONRPCProtocol()
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        
    async def connect(self) -> None:
        """Connect to the MCP server (initialize HTTP client)."""
        if self._connected:
            return
            
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(self.config.timeout_seconds),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "PrivateGPT-Gateway/1.0"
            }
        )
        
        # Test connection with a ping
        try:
            await self.send_request("ping", {})
            self._connected = True
            logger.info(f"Connected to MCP server at {self.config.base_url}")
        except Exception as e:
            await self.disconnect()
            raise ConnectionError(f"Failed to connect to MCP server: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server (close HTTP client)."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        logger.info(f"Disconnected from MCP server at {self.config.base_url}")
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Send a request to the MCP server.
        
        Args:
            method: JSON-RPC method name
            params: Optional parameters
            
        Returns:
            Response result
            
        Raises:
            ConnectionError: If not connected
            ProtocolError: If protocol error occurs
            JSONRPCError: If server returns an error
        """
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to MCP server")
            
        # Create JSON-RPC request
        request_data = self.protocol.create_request(method, params)
        
        # Send HTTP request with retries
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = await self._client.post(
                    "/",  # JSON-RPC typically uses root path
                    content=request_data,
                )
                response.raise_for_status()
                
                # Parse JSON-RPC response
                mcp_response = self.protocol.parse_response(response.text)
                return mcp_response.result
                
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500:
                    # Server error, retry
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
                        continue
                # Client error, don't retry
                raise ProtocolError(f"HTTP error {e.response.status_code}: {e.response.text}")
                
            except httpx.RequestError as e:
                last_error = e
                # Network error, retry
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
                    continue
                    
            except JSONRPCError:
                # Protocol error from server, don't retry
                raise
                
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error in HTTP transport: {e}")
                raise ProtocolError(f"Transport error: {e}")
        
        # All retries failed
        raise ConnectionError(f"Failed after {self.config.max_retries} attempts: {last_error}")
    
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Send a notification to the MCP server (no response expected).
        
        Args:
            method: JSON-RPC method name
            params: Optional parameters
        """
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to MCP server")
            
        # Create JSON-RPC notification
        notification_data = self.protocol.create_notification(method, params)
        
        try:
            # Send HTTP request (fire and forget)
            response = await self._client.post(
                "/",
                content=notification_data,
            )
            # We don't care about the response for notifications
            logger.debug(f"Sent notification: {method}")
        except Exception as e:
            # Log but don't raise for notifications
            logger.warning(f"Failed to send notification {method}: {e}")
    
    async def send_batch_request(self, requests: list[tuple[str, Optional[Dict[str, Any]]]]) -> list[Any]:
        """
        Send a batch of requests to the MCP server.
        
        Args:
            requests: List of (method, params) tuples
            
        Returns:
            List of response results
        """
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to MCP server")
            
        # Create batch JSON-RPC request
        batch_data = self.protocol.create_batch_request(requests)
        
        try:
            response = await self._client.post(
                "/",
                content=batch_data,
            )
            response.raise_for_status()
            
            # Parse batch response
            mcp_responses = self.protocol.parse_batch_response(response.text)
            
            # Extract results, handling any errors
            results = []
            for mcp_response in mcp_responses:
                if mcp_response.error:
                    # Convert to exception but continue processing
                    error = JSONRPCError(
                        code=mcp_response.error.get("code", -32603),
                        message=mcp_response.error.get("message", "Unknown error"),
                        data=mcp_response.error.get("data")
                    )
                    results.append(error)
                else:
                    results.append(mcp_response.result)
                    
            return results
            
        except httpx.HTTPStatusError as e:
            raise ProtocolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in batch request: {e}")
            raise ProtocolError(f"Transport error: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self._connected
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()