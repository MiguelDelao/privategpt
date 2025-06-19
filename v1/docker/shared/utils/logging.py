"""
Centralized logging configuration
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Setup logging configuration
    
    Args:
        level: Logging level (default: INFO)
        
    Returns:
        Logger: Configured logger instance
    """
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    
    return logger

def log_json(message: str, **kwargs) -> None:
    """Log structured JSON data
    
    Args:
        message: Log message
        **kwargs: Additional fields to include in log
    """
    # Create log entry
    log_entry: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "message": message,
        **kwargs
    }
    
    # Convert to JSON and print
    print(json.dumps(log_entry))

def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module
    
    Args:
        name: Module name
        
    Returns:
        Logger: Configured logger instance
    """
    return logging.getLogger(name) 