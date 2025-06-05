"""
Admin router for system configuration and settings
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging
import os
import json
import httpx
from datetime import datetime

from ..dependencies import get_auth_context, AuthContext

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory settings store (in production, use Redis or database)
_settings_store = {}

# Default settings
DEFAULT_SETTINGS = {
    "MAX_CONTEXT_TOKENS": "3000",
    "DEFAULT_SEARCH_LIMIT": "5", 
    "LLM_TIMEOUT_SECONDS": "120",
    "DEFAULT_MAX_TOKENS": "1000",
    "DEFAULT_TEMPERATURE": "0.7",
    "SELECTED_MODEL": "llama3:8b"
}


def get_current_settings() -> Dict[str, str]:
    """Get current effective settings from environment and overrides"""
    settings = {}
    
    # Start with defaults
    for key, default_value in DEFAULT_SETTINGS.items():
        # Environment takes precedence
        env_value = os.getenv(key, default_value)
        # In-memory override takes precedence over environment
        settings[key] = _settings_store.get(key, env_value)
    
    return settings


async def get_available_models() -> List[Dict[str, Any]]:
    """Get available models from Ollama service"""
    try:
        ollama_url = os.getenv("OLLAMA_URL", "http://ollama-service:11434")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                
                # Simplify model info
                simplified_models = []
                for model in models:
                    simplified_models.append({
                        "name": model.get("name", "unknown"),
                        "size": model.get("size", 0),
                        "modified_at": model.get("modified_at", ""),
                        "available": True
                    })
                
                return simplified_models
            else:
                logger.error(f"Failed to get models from Ollama: {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"Error fetching models from Ollama: {e}")
        return []


async def validate_model_exists(model_name: str) -> bool:
    """Check if a model exists in Ollama"""
    try:
        available_models = await get_available_models()
        return any(model["name"] == model_name for model in available_models)
    except Exception as e:
        logger.error(f"Error validating model {model_name}: {e}")
        return False


@router.get("/models/available")
async def list_available_models(auth_context: AuthContext = Depends(get_auth_context)):
    """
    Get available models from Ollama
    
    Returns list of models available for selection.
    Admin access required.
    """
    try:
        # Get user info from auth service to check admin status
        user_info = await auth_context.auth_client._get_user_info()
        if user_info.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        models = await get_available_models()
        current_settings = get_current_settings()
        selected_model = current_settings.get("SELECTED_MODEL", "llama3:8b")
        
        return {
            "models": models,
            "selected_model": selected_model,
            "total_models": len(models),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.get("/settings")
async def get_llm_settings(auth_context: AuthContext = Depends(get_auth_context)):
    """
    Get current LLM settings
    
    Returns the current configuration values for LLM parameters.
    Admin access required.
    """
    try:
        # Get user info from auth service to check admin status
        user_info = await auth_context.auth_client._get_user_info()
        if user_info.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        current_settings = get_current_settings()
        
        return {
            "settings": current_settings,
            "source": "environment_and_overrides",
            "timestamp": datetime.utcnow().isoformat(),
            "defaults": DEFAULT_SETTINGS
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")


@router.post("/settings")
async def update_llm_settings(
    settings: Dict[str, str],
    auth_context: AuthContext = Depends(get_auth_context)
):
    """
    Update LLM settings
    
    Updates configuration values for LLM parameters.
    Admin access required.
    """
    try:
        # Get user info from auth service to check admin status
        user_info = await auth_context.auth_client._get_user_info()
        if user_info.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Validate settings
        valid_keys = set(DEFAULT_SETTINGS.keys())
        provided_keys = set(settings.keys())
        
        invalid_keys = provided_keys - valid_keys
        if invalid_keys:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid setting keys: {list(invalid_keys)}"
            )
        
        # Validate values
        for key, value in settings.items():
            if key in ["MAX_CONTEXT_TOKENS", "DEFAULT_SEARCH_LIMIT", "LLM_TIMEOUT_SECONDS", "DEFAULT_MAX_TOKENS"]:
                try:
                    int_val = int(value)
                    if int_val <= 0:
                        raise ValueError("Must be positive")
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Setting {key} must be a positive integer, got: {value}"
                    )
            
            elif key == "DEFAULT_TEMPERATURE":
                try:
                    float_val = float(value)
                    if not (0.0 <= float_val <= 2.0):
                        raise ValueError("Must be between 0.0 and 2.0")
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Setting {key} must be a float between 0.0 and 2.0, got: {value}"
                    )
            
            elif key == "SELECTED_MODEL":
                if not value or not value.strip():
                    raise HTTPException(
                        status_code=400,
                        detail="Model name cannot be empty"
                    )
                
                # Validate model exists in Ollama
                model_exists = await validate_model_exists(value.strip())
                if not model_exists:
                    available_models = await get_available_models()
                    model_names = [m["name"] for m in available_models]
                    raise HTTPException(
                        status_code=400,
                        detail=f"Model '{value}' not found in Ollama. Available models: {model_names}"
                    )
        
        # Update in-memory settings store
        _settings_store.update(settings)
        
        logger.info(f"🔧 Settings updated by {user_info.get('email', 'unknown')}: {settings}")
        
        return {
            "message": "Settings updated successfully",
            "updated_settings": settings,
            "timestamp": datetime.utcnow().isoformat(),
            "effective_settings": get_current_settings()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.delete("/settings")
async def reset_llm_settings(auth_context: AuthContext = Depends(get_auth_context)):
    """
    Reset LLM settings to defaults
    
    Clears all custom settings and reverts to environment defaults.
    Admin access required.
    """
    try:
        # Get user info from auth service to check admin status
        user_info = await auth_context.auth_client._get_user_info()
        if user_info.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Clear in-memory overrides
        _settings_store.clear()
        
        logger.info(f"🔄 Settings reset to defaults by {user_info.get('email', 'unknown')}")
        
        return {
            "message": "Settings reset to defaults",
            "timestamp": datetime.utcnow().isoformat(),
            "effective_settings": get_current_settings()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to reset settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset settings: {str(e)}")


@router.get("/health")
async def admin_health():
    """Admin endpoint health check"""
    return {
        "service": "admin-api",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "settings_count": len(_settings_store)
    } 