from __future__ import annotations

"""
Redis client for caching and session management.
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

import redis.asyncio as aioredis
from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client for caching stream sessions and other data"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.redis_url = settings.redis_url or "redis://redis:6379/2"
    
    async def connect(self):
        """Connect to Redis"""
        if not self.redis:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Connected to Redis")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self.redis = None
    
    async def set_stream_session(
        self, 
        token: str, 
        data: Dict[str, Any], 
        ttl: int = 300
    ) -> None:
        """Store stream session data with TTL (default 5 minutes)"""
        await self.connect()
        if self.redis:
            await self.redis.setex(
                f"stream_session:{token}",
                ttl,
                json.dumps(data)
            )
    
    async def get_stream_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Retrieve stream session data"""
        await self.connect()
        if self.redis:
            data = await self.redis.get(f"stream_session:{token}")
            if data:
                return json.loads(data)
        return None
    
    async def delete_stream_session(self, token: str) -> None:
        """Delete stream session data"""
        await self.connect()
        if self.redis:
            await self.redis.delete(f"stream_session:{token}")
    
    async def extend_stream_session(self, token: str, ttl: int = 300) -> bool:
        """Extend TTL for stream session"""
        await self.connect()
        if self.redis:
            return await self.redis.expire(f"stream_session:{token}", ttl)
        return False


# Global instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get global Redis client instance"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client