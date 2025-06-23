from __future__ import annotations

"""
Keycloak integration for PrivateGPT.
Handles OIDC token validation and user information extraction.
"""

import json
import logging
from typing import Dict, Optional, Any
from urllib.parse import urljoin

import httpx
from jose import jwt, jwk, JWTError
from jose.utils import base64url_decode

from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


class KeycloakClient:
    """Client for validating Keycloak OIDC tokens and retrieving user info."""
    
    def __init__(
        self, 
        keycloak_url: str | None = None,
        realm: str = "privategpt",
        client_id: str | None = None
    ):
        self.keycloak_url = keycloak_url or getattr(settings, 'keycloak_url', 'http://keycloak:8080')
        self.realm = realm
        self.client_id = client_id or getattr(settings, 'keycloak_client_id', 'privategpt-ui')
        self.realm_url = f"{self.keycloak_url.rstrip('/')}/realms/{realm}"
        self._jwks_cache: Optional[Dict] = None
        self._client = httpx.AsyncClient(timeout=30.0)
        
        # External issuer URL (what appears in tokens)
        self.external_issuer = f"http://localhost:8180/realms/{realm}"
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Fetch and cache JSON Web Key Set from Keycloak."""
        if self._jwks_cache:
            return self._jwks_cache
            
        try:
            response = await self._client.get(f"{self.realm_url}/protocol/openid-connect/certs")
            response.raise_for_status()
            self._jwks_cache = response.json()
            return self._jwks_cache
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Keycloak: {e}")
            raise
    
    async def get_realm_config(self) -> Dict[str, Any]:
        """Get realm configuration from Keycloak."""
        try:
            response = await self._client.get(f"{self.realm_url}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch realm config: {e}")
            raise
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token and return decoded claims.
        
        Args:
            token: JWT access token from Keycloak
            
        Returns:
            Decoded token claims if valid, None if invalid
        """
        try:
            logger.info(f"Starting token validation for token length: {len(token)}")
            logger.info(f"Token starts with: {token[:100]}...")
            logger.info(f"Token ends with: ...{token[-20:]}")
            
            # Get the key ID from token header
            logger.info(f"About to call jwt.get_unverified_header")
            unverified_header = jwt.get_unverified_header(token)
            logger.info(f"Token header: {unverified_header}")
            kid = unverified_header.get('kid')
            
            if not kid:
                logger.warning("Token missing key ID")
                return None
            
            logger.info(f"Token kid: {kid}")
            
            # Get JWKS and find matching key
            jwks = await self.get_jwks()
            logger.info(f"Available JWK kids: {[k.get('kid') for k in jwks.get('keys', [])]}")
            
            key = None
            for jwk_key in jwks.get('keys', []):
                if jwk_key.get('kid') == kid:
                    key = jwk.construct(jwk_key)
                    break
            
            if not key:
                logger.warning(f"No matching key found for kid: {kid}")
                return None
            
            logger.info(f"Found matching key for kid: {kid}")
            
            # Verify and decode token using external issuer URL
            # Note: Keycloak tokens use "account" as audience, not the client_id
            logger.info(f"Decoding with issuer: {self.external_issuer}")
            claims = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience="account",
                issuer=self.external_issuer
            )
            
            logger.info(f"Token validation successful. Claims: {claims}")
            return claims
            
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    async def get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Keycloak userinfo endpoint.
        
        Args:
            token: Valid JWT access token
            
        Returns:
            User information if successful, None otherwise
        """
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = await self._client.get(
                f"{self.realm_url}/protocol/openid-connect/userinfo",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    def extract_user_claims(self, token_claims: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standardized user information from token claims.
        
        Args:
            token_claims: Decoded JWT claims
            
        Returns:
            Standardized user information
        """
        roles = token_claims.get('realm_access', {}).get('roles', [])
        
        # Determine primary role (admin takes precedence)
        if 'admin' in roles:
            primary_role = 'admin'
        elif 'user' in roles:
            primary_role = 'user'
        else:
            primary_role = 'user'  # default
        
        return {
            'user_id': token_claims.get('sub'),
            'username': token_claims.get('preferred_username'),
            'email': token_claims.get('email'),
            'first_name': token_claims.get('given_name'),
            'last_name': token_claims.get('family_name'),
            'roles': roles,
            'primary_role': primary_role,
            'email_verified': token_claims.get('email_verified', False),
            'token_issued_at': token_claims.get('iat'),
            'token_expires_at': token_claims.get('exp'),
        }
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Global instance for dependency injection
_keycloak_client: Optional[KeycloakClient] = None


def get_keycloak_client() -> KeycloakClient:
    """Get or create global Keycloak client instance."""
    global _keycloak_client
    if _keycloak_client is None:
        _keycloak_client = KeycloakClient()
    return _keycloak_client


async def validate_bearer_token(authorization: str) -> Optional[Dict[str, Any]]:
    """
    Validate Bearer token from Authorization header.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
        
    Returns:
        User claims if valid, None if invalid
    """
    if not authorization or not authorization.startswith('Bearer '):
        return None
    
    token = authorization[7:]  # Remove "Bearer " prefix
    client = get_keycloak_client()
    
    token_claims = await client.validate_token(token)
    if not token_claims:
        return None
    
    return client.extract_user_claims(token_claims)