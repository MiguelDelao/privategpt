from __future__ import annotations

"""
HTTP proxy service for routing requests to backend services.
"""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin

import httpx
from fastapi import Request, Response, HTTPException, status

from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


class ServiceProxy:
    """Proxy for routing requests to backend services."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Service endpoint mapping
        self.service_urls = {
            "rag": getattr(settings, 'rag_service_url', 'http://rag-service:8000'),
            "llm": getattr(settings, 'llm_service_url', 'http://llm-service:8000'),
        }
    
    async def proxy_request(
        self,
        service: str,
        request: Request,
        path: str,
        **kwargs
    ) -> Response:
        """
        Proxy HTTP request to backend service.
        
        Args:
            service: Target service name (auth, rag, llm)
            request: FastAPI request object
            path: Target path on backend service
            **kwargs: Additional httpx request parameters
            
        Returns:
            FastAPI Response object
        """
        if service not in self.service_urls:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service}' not found"
            )
        
        target_url = urljoin(self.service_urls[service], path.lstrip('/'))
        
        # Prepare request headers (exclude hop-by-hop headers)
        headers = self._filter_headers(dict(request.headers))
        
        # Get request body
        body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
        
        try:
            # Make request to backend service
            response = await self.client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
                **kwargs
            )
            
            # Log the proxy request
            logger.info(
                "Proxied request",
                extra={
                    "service": service,
                    "method": request.method,
                    "path": path,
                    "status_code": response.status_code,
                    "target_url": target_url
                }
            )
            
            # Filter response headers
            response_headers = self._filter_response_headers(dict(response.headers))
            
            # Return FastAPI response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type")
            )
            
        except httpx.RequestError as e:
            logger.error(f"Request to {service} service failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to {service} service"
            )
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error from {service} service: {e}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from {service} service"
            )
    
    def _filter_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter out hop-by-hop headers that shouldn't be forwarded."""
        hop_by_hop_headers = {
            'connection', 'keep-alive', 'proxy-authenticate',
            'proxy-authorization', 'te', 'trailers', 'transfer-encoding',
            'upgrade', 'host'
        }
        
        return {
            key: value for key, value in headers.items()
            if key.lower() not in hop_by_hop_headers
        }
    
    def _filter_response_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter response headers before sending to client."""
        filtered_headers = self._filter_headers(headers)
        
        # Remove server-specific headers
        server_headers = {'server', 'date'}
        return {
            key: value for key, value in filtered_headers.items()
            if key.lower() not in server_headers
        }
    
    async def health_check(self, service: str) -> Dict[str, Any]:
        """Check health of a backend service."""
        if service not in self.service_urls:
            return {"status": "unknown", "error": "Service not configured"}
        
        try:
            response = await self.client.get(f"{self.service_urls[service]}/health")
            if response.status_code == 200:
                return {"status": "healthy", "response": response.json()}
            else:
                return {"status": "unhealthy", "status_code": response.status_code}
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global proxy instance
_proxy: Optional[ServiceProxy] = None


def get_proxy() -> ServiceProxy:
    """Get or create global proxy instance."""
    global _proxy
    if _proxy is None:
        _proxy = ServiceProxy()
    return _proxy