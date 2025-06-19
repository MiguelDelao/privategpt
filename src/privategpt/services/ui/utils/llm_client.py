from __future__ import annotations

"""
LLM client for PrivateGPT UI (v2).
Handles communication with the LLM service for chat and generation.
"""

import json
import os
import requests
from typing import Dict, List, Optional, Iterator


class LLMClient:
    """Client for interacting with the LLM service."""
    
    def __init__(self, llm_url: str | None = None):
        base = llm_url or os.getenv("LLM_URL", "http://llm-service:8000")
        self.llm_url = base.rstrip("/")
        self.session = requests.Session()
        
    def get_models(self) -> List[Dict]:
        """Get available models from the LLM service."""
        try:
            resp = self.session.get(f"{self.llm_url}/models", timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise Exception(f"Failed to get models: {str(e)}")
    
    def generate(self, prompt: str, model: str = None, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate a single response to a prompt."""
        try:
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            if model:
                payload["model"] = model
                
            resp = self.session.post(
                f"{self.llm_url}/generate", 
                json=payload, 
                timeout=180
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("text", "")
        except Exception as e:
            raise Exception(f"Failed to generate response: {str(e)}")
    
    def generate_stream(self, prompt: str, model: str = None, max_tokens: int = 500, temperature: float = 0.7) -> Iterator[str]:
        """Generate a streaming response to a prompt."""
        try:
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            if model:
                payload["model"] = model
                
            resp = self.session.post(
                f"{self.llm_url}/generate/stream",
                json=payload,
                stream=True,
                timeout=180
            )
            resp.raise_for_status()
            
            for line in resp.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        content = line_str[6:]  # Remove 'data: ' prefix
                        if content.strip() == '[DONE]':
                            break
                        if content.strip():
                            yield content
        except Exception as e:
            raise Exception(f"Failed to stream response: {str(e)}")
    
    def chat(self, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate response for a conversation."""
        try:
            payload = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            if model:
                payload["model"] = model
                
            resp = self.session.post(
                f"{self.llm_url}/chat", 
                json=payload, 
                timeout=180
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("text", "")
        except Exception as e:
            raise Exception(f"Failed to generate chat response: {str(e)}")
    
    def health_check(self) -> bool:
        """Check if the LLM service is healthy."""
        try:
            resp = self.session.get(f"{self.llm_url}/health", timeout=10)
            return resp.status_code == 200
        except Exception:
            return False