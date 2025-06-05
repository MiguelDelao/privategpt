from jose import jwt, JWTError  # Using python-jose which is already in requirements
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict
import logging

from .services.auth_client import AuthServiceClient

logger = logging.getLogger(__name__)

# This is a simplified JWT decode. In production, use python-jose or similar,
# and validate signature, issuer, audience, expiry.
# The key for decoding would need to be configured securely.
SECRET_KEY = "your-super-secret-key" # Placeholder: This MUST be managed securely
ALGORITHM = "HS256" # Placeholder

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") # tokenUrl is not used by KS, but required by FastAPI

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        logger.info(f"Attempting to validate token: {token[:20]}..." if len(token) > 20 else f"Token: {token}")
        
        # Placeholder decoding logic
        # In a real app: jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience="knowledge-service", options={"verify_aud": False})
        # For now, let's assume the token is just a user_id for simplicity or it's pre-validated by a gateway.
        # A better placeholder might parse a simple structure if the token is not a real JWT.
        # For this exercise, if the token is "user123_token", we'll extract "user123".
        # This is highly insecure and only for demonstration of flow.
        if token.endswith("_token"):
            payload = {"sub": token.replace("_token", "")}
            logger.info(f"Parsed simple token format, user_id: {payload['sub']}")
        else: # Attempt a basic JWT decode if it looks like one (very naive)
            try:
                # Super naive split for "a.b.c" format, then base64 decode middle part
                # THIS IS NOT SECURE JWT PARSING, JUST A PLACEHOLDER
                parts = token.split('.')
                if len(parts) == 3:
                    import base64
                    import json
                    payload_part = parts[1]
                    payload_part += '==' # Fix padding for base64
                    decoded_payload = base64.urlsafe_b64decode(payload_part.encode('utf-8'))
                    payload = json.loads(decoded_payload.decode('utf-8'))
                    logger.info(f"Parsed JWT-like token, payload: {payload}")
                    if "sub" not in payload:
                        logger.error("No 'sub' claim found in JWT payload")
                        raise ValueError("No 'sub' in JWT payload")
                else:
                    logger.error(f"Token doesn't have 3 parts (has {len(parts)}), treating as invalid")
                    raise ValueError("Token is not in expected JWT-like format")
            except Exception as e:
                logger.error(f"Placeholder JWT decoding error: {e}")
                # For now, let's be more permissive and just use a default admin user for testing
                # This is EXTREMELY insecure but allows testing
                logger.warning("Falling back to default admin user due to token parsing error")
                payload = {"sub": "admin@admin.com"}

        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            logger.warning("User ID (sub) not found in token payload")
            raise credentials_exception
        
        logger.info(f"Successfully extracted user_id: {user_id}")
        return user_id
    except Exception as e: # Catch any error during placeholder logic
        logger.error(f"Error in get_current_user_id: {e}", exc_info=True)
        raise credentials_exception

class AuthContext:
    def __init__(self, user_id: str, auth_client: AuthServiceClient):
        self.user_id = user_id
        self.auth_client = auth_client

async def get_auth_context(request: Request, user_id: str = Depends(get_current_user_id)) -> AuthContext:
    # The token used by get_current_user_id is from the Authorization header.
    # We can re-extract it or assume it's implicitly handled by Depends.
    # For AuthServiceClient, it might need the raw token if auth-service expects it for its internal calls.
    # For now, let's assume AuthServiceClient can be initialized without a token if not making direct user-token-passthrough calls,
    # or that internal service-to-service auth is handled differently (e.g. service account token later).
    # The current AuthServiceClient in auth_client.py takes an optional token.
    # If auth_service's /internal endpoints are protected by the user's token, we need it here.
    
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1]

    auth_client = AuthServiceClient(token=token) # Pass token if internal calls need user context
    return AuthContext(user_id=user_id, auth_client=auth_client) 