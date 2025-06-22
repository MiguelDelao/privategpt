"""
Custom exceptions for gateway services.
"""


class ChatContextLimitError(Exception):
    """Raised when a chat request would exceed the model's context limit."""
    
    def __init__(self, message: str, current_tokens: int, limit: int, model_name: str):
        super().__init__(message)
        self.current_tokens = current_tokens
        self.limit = limit
        self.model_name = model_name