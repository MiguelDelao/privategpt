"""
Centralized Configuration Loader for PrivateGPT Legal AI
Replaces scattered environment variables with single source of truth
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Centralized configuration loader"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from JSON file"""
        try:
            # Try current directory first
            config_path = Path(self.config_file)
            
            # If not found, try parent directory (for services in subdirectories)
            if not config_path.exists():
                config_path = Path("..") / self.config_file
            
            # If still not found, try project root
            if not config_path.exists():
                config_path = Path("../../") / self.config_file
            
            if not config_path.exists():
                raise FileNotFoundError(f"Config file {self.config_file} not found")
            
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            
            logger.info(f"Configuration loaded from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Fallback to minimal default config
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Fallback default configuration"""
        return {
            "admin": {
                "email": "admin@admin.com",
                "password": "admin",
                "role": "admin"
            },
            "security": {
                "jwt": {
                    "secret_key": "admin123456789abcdef",
                    "algorithm": "HS256",
                    "expiry_hours": 24
                },
                "password_policy": {
                    "min_length": 8,
                    "require_uppercase": False,
                    "require_lowercase": False,
                    "require_numbers": False,
                    "require_special_chars": False
                }
            },
            "logging": {
                "level": "INFO"
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        Example: get("admin.email") returns "admin@admin.com"
        """
        try:
            keys = key_path.split('.')
            value = self._config
            
            for key in keys:
                value = value[key]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self._config.get(section, {})
    
    def get_admin_config(self) -> Dict[str, Any]:
        """Get admin account configuration"""
        return self.get_section("admin")
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return self.get_section("security")
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.get_section("database")
    
    def get_service_urls(self) -> Dict[str, str]:
        """Get service URLs"""
        return self.get_section("services")
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration"""
        return self.get_section("models")
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.get_section("logging")
    
    def get_embedding_model(self) -> str:
        """Get embedding model"""
        return self.get("models.embedding_model", "bge-base-en-v1.5")
    
    def get_admin_role(self) -> str:
        """Get admin account role"""
        return self.get("admin.role", "admin")
    
    def get_jwt_secret(self) -> str:
        """Get JWT secret key"""
        return self.get("security.jwt.secret_key", "admin123456789abcdef")
    
    def get_password_min_length(self) -> int:
        """Get minimum password length"""
        return self.get("security.password_policy.min_length", 8)
    
    def should_require_password_complexity(self) -> bool:
        """Check if password complexity is required"""
        return any([
            self.get("security.password_policy.require_uppercase", False),
            self.get("security.password_policy.require_lowercase", False),
            self.get("security.password_policy.require_numbers", False),
            self.get("security.password_policy.require_special_chars", False)
        ])
    
    def reload(self):
        """Reload configuration from file"""
        self._load_config()

# Global configuration instance
config = ConfigLoader()

# Convenience functions for easy access
def get_config(key_path: str, default: Any = None):
    """Get configuration value using dot notation"""
    return config.get(key_path, default)

def get_admin_email() -> str:
    """Get default admin email"""
    return config.get("admin.email", "admin@admin.com")

def get_admin_password() -> str:
    """Get default admin password"""
    return config.get("admin.password", "admin")

def get_jwt_secret() -> str:
    """Get JWT secret key"""
    return config.get_jwt_secret()

def get_service_url(service: str) -> str:
    """Get service URL"""
    return config.get(f"services.{service}", "")

def get_embedding_model() -> str:
    """Get embedding model"""
    return config.get_embedding_model()

def get_admin_role() -> str:
    """Get admin account role"""
    return config.get_admin_role()

def get_llm_settings() -> Dict[str, Any]:
    """Get LLM configuration settings"""
    return config.get_section("models").get("llm", {}) 