"""
Admin router for system configuration and settings
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging
import os
import json
import httpx
import sys
from datetime import datetime

# Add project root to path for config loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from config_loader import get_llm_settings, get_model_name, get_service_url, get_config_loader

from ..dependencies import get_auth_context, AuthContext

logger = logging.getLogger(__name__)

router = APIRouter()

def get_current_settings() -> Dict[str, str]:
    """Get current effective settings from Redis overrides + config.json defaults"""
    config_loader = get_config_loader()
    
    # Get settings with Redis overrides taking precedence
    settings = {
        "MAX_CONTEXT_TOKENS": str(config_loader.get("models.llm.max_context_tokens", 3000)),
        "DEFAULT_SEARCH_LIMIT": str(config_loader.get("models.llm.default_search_limit", 5)),
        "LLM_TIMEOUT_SECONDS": str(config_loader.get("models.llm.timeout_seconds", 120)),
        "DEFAULT_MAX_TOKENS": str(config_loader.get("models.llm.default_max_tokens", 1000)),
        "DEFAULT_TEMPERATURE": str(config_loader.get("models.llm.default_temperature", 0.7)),
        "SELECTED_MODEL": config_loader.get("model.name", "llama3.2:1b")
    }
    
    return settings

def get_selected_model() -> str:
    """Get the currently selected model (Redis override or config default)"""
    config_loader = get_config_loader()
    return config_loader.get("model.name", "llama3.2:1b")

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
        selected_model = get_selected_model()
        
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
async def get_llm_settings_endpoint(auth_context: AuthContext = Depends(get_auth_context)):
    """
    Get current LLM settings
    
    Returns the current configuration values for LLM parameters with source information.
    Admin access required.
    """
    try:
        # Get user info from auth service to check admin status
        user_info = await auth_context.auth_client._get_user_info()
        if user_info.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        config_loader = get_config_loader()
        current_settings = get_current_settings()
        
        # Get source information for each setting
        setting_sources = {}
        for key in ["models.llm.max_context_tokens", "models.llm.default_search_limit", 
                   "models.llm.timeout_seconds", "models.llm.default_max_tokens", 
                   "models.llm.default_temperature", "model.name"]:
            setting_sources[key] = config_loader.get_setting_source(key)
        
        return {
            "settings": current_settings,
            "sources": setting_sources,
            "redis_overrides": config_loader.list_overrides(),
            "timestamp": datetime.utcnow().isoformat(),
            "defaults": get_llm_settings()
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
    
    Updates configuration values for LLM parameters in Redis.
    Changes take effect immediately across all services.
    Admin access required.
    """
    try:
        # Get user info from auth service to check admin status
        user_info = await auth_context.auth_client._get_user_info()
        if user_info.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        config_loader = get_config_loader()
        
        # Map API keys to config keys
        key_mapping = {
            "MAX_CONTEXT_TOKENS": "models.llm.max_context_tokens",
            "DEFAULT_SEARCH_LIMIT": "models.llm.default_search_limit",
            "LLM_TIMEOUT_SECONDS": "models.llm.timeout_seconds",
            "DEFAULT_MAX_TOKENS": "models.llm.default_max_tokens",
            "DEFAULT_TEMPERATURE": "models.llm.default_temperature",
            "SELECTED_MODEL": "model.name"
        }
        
        # Validate settings against known LLM setting keys
        valid_keys = set(key_mapping.keys())
        provided_keys = set(settings.keys())
        
        invalid_keys = provided_keys - valid_keys
        if invalid_keys:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid setting keys: {list(invalid_keys)}"
            )
        
        # Validate and convert values
        validated_settings = {}
        for api_key, value in settings.items():
            config_key = key_mapping[api_key]
            
            if api_key in ["MAX_CONTEXT_TOKENS", "DEFAULT_SEARCH_LIMIT", "LLM_TIMEOUT_SECONDS", "DEFAULT_MAX_TOKENS"]:
                try:
                    int_val = int(value)
                    if int_val <= 0:
                        raise ValueError("Must be positive")
                    validated_settings[config_key] = int_val
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Setting {api_key} must be a positive integer, got: {value}"
                    )
            
            elif api_key == "DEFAULT_TEMPERATURE":
                try:
                    float_val = float(value)
                    if not (0.0 <= float_val <= 2.0):
                        raise ValueError("Must be between 0.0 and 2.0")
                    validated_settings[config_key] = float_val
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Setting {api_key} must be a float between 0.0 and 2.0, got: {value}"
                    )
            
            elif api_key == "SELECTED_MODEL":
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
                validated_settings[config_key] = value.strip()
        
        # Update settings in Redis
        failed_updates = []
        successful_updates = []
        
        for config_key, validated_value in validated_settings.items():
            success = config_loader.set_setting(config_key, validated_value)
            if success:
                successful_updates.append(config_key)
            else:
                failed_updates.append(config_key)
        
        if failed_updates:
            logger.error(f"Failed to update settings: {failed_updates}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update some settings: {failed_updates}"
            )
        
        return {
            "message": "Settings updated successfully in Redis",
            "updated_settings": successful_updates,
            "current_settings": get_current_settings(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.delete("/settings")
async def reset_llm_settings(auth_context: AuthContext = Depends(get_auth_context)):
    """
    Reset LLM settings to config.json defaults
    
    Removes all Redis overrides and reverts to config.json defaults.
    Admin access required.
    """
    try:
        # Get user info from auth service to check admin status
        user_info = await auth_context.auth_client._get_user_info()
        if user_info.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        config_loader = get_config_loader()
        
        # Remove all LLM-related Redis overrides
        settings_to_reset = [
            "models.llm.max_context_tokens",
            "models.llm.default_search_limit", 
            "models.llm.timeout_seconds",
            "models.llm.default_max_tokens",
            "models.llm.default_temperature",
            "model.name"
        ]
        
        reset_count = 0
        for setting_key in settings_to_reset:
            if config_loader.remove_override(setting_key):
                reset_count += 1
        
        return {
            "message": f"Settings reset to config.json defaults ({reset_count} overrides removed)",
            "current_settings": get_current_settings(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to reset settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset settings: {str(e)}")


@router.get("/settings/{key}")
async def get_setting_detail(key: str, auth_context: AuthContext = Depends(get_auth_context)):
    """
    Get detailed information about a specific setting
    
    Returns the value, source, and metadata for a configuration setting.
    Admin access required.
    """
    try:
        # Get user info from auth service to check admin status
        user_info = await auth_context.auth_client._get_user_info()
        if user_info.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        config_loader = get_config_loader()
        
        # Map API key to config key if needed
        key_mapping = {
            "MAX_CONTEXT_TOKENS": "models.llm.max_context_tokens",
            "DEFAULT_SEARCH_LIMIT": "models.llm.default_search_limit",
            "LLM_TIMEOUT_SECONDS": "models.llm.timeout_seconds",
            "DEFAULT_MAX_TOKENS": "models.llm.default_max_tokens",
            "DEFAULT_TEMPERATURE": "models.llm.default_temperature",
            "SELECTED_MODEL": "model.name"
        }
        
        config_key = key_mapping.get(key, key)
        
        return {
            "key": key,
            "config_key": config_key,
            "value": config_loader.get(config_key),
            "source": config_loader.get_setting_source(config_key),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get setting detail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get setting detail: {str(e)}")


@router.delete("/settings/{key}")
async def reset_single_setting(key: str, auth_context: AuthContext = Depends(get_auth_context)):
    """
    Reset a single setting to its config.json default
    
    Removes the Redis override for a specific setting.
    Admin access required.
    """
    try:
        # Get user info from auth service to check admin status
        user_info = await auth_context.auth_client._get_user_info()
        if user_info.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        config_loader = get_config_loader()
        
        # Map API key to config key if needed
        key_mapping = {
            "MAX_CONTEXT_TOKENS": "models.llm.max_context_tokens",
            "DEFAULT_SEARCH_LIMIT": "models.llm.default_search_limit",
            "LLM_TIMEOUT_SECONDS": "models.llm.timeout_seconds",
            "DEFAULT_MAX_TOKENS": "models.llm.default_max_tokens",
            "DEFAULT_TEMPERATURE": "models.llm.default_temperature",
            "SELECTED_MODEL": "model.name"
        }
        
        config_key = key_mapping.get(key, key)
        
        success = config_loader.remove_override(config_key)
        
        if success:
            return {
                "message": f"Setting {key} reset to config.json default",
                "key": key,
                "config_key": config_key,
                "new_value": config_loader.get(config_key),
                "source": config_loader.get_setting_source(config_key),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "message": f"No Redis override found for {key}",
                "key": key,
                "config_key": config_key,
                "value": config_loader.get(config_key),
                "source": config_loader.get_setting_source(config_key),
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to reset setting: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset setting: {str(e)}")


@router.get("/health")
async def admin_health():
    """Admin endpoint health check"""
    config_loader = get_config_loader()
    
    return {
        "service": "admin-api",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "config_source": "redis_with_config_fallback",
        "redis_available": config_loader._redis_client is not None,
        "redis_overrides_count": len(config_loader.list_overrides())
    } 