#!/usr/bin/env python3
"""
Performance Optimization (Simplified)
=====================================

Performance features with in-memory caching, connection pooling,
and async database operations optimization.
"""

import asyncio
import time
import json
import logging
import os
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime, timezone, timedelta
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import QueuePool
from sqlalchemy import select, func
import hashlib

# Redis imports with fallback
try:
    import redis.asyncio as redis
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - using memory cache only")

logger = logging.getLogger(__name__)

class RedisCacheManager:
    """Production Redis cache manager with fallback to memory cache."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = os.getenv("REDIS_URL", "redis://redis-cache:6379/0")
        self.memory_fallback = None
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "redis_errors": 0,
            "fallback_usage": 0
        }
        self.default_ttl = 300  # 5 minutes
        
    async def initialize(self, **kwargs):
        """Initialize Redis connection with fallback."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - initializing memory fallback")
            self.memory_fallback = MemoryCacheManager()
            await self.memory_fallback.initialize()
            return False
            
        try:
            # Create Redis connection
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info(f"Redis cache initialized successfully: {self.redis_url}")
            return True
            
        except Exception as e:
            logger.error(f"Redis initialization failed: {e}")
            logger.info("Falling back to memory cache")
            self.memory_fallback = MemoryCacheManager()
            await self.memory_fallback.initialize()
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with fallback."""
        self.cache_stats["total_requests"] += 1
        
        # Use Redis if available
        if self.redis_client:
            try:
                result = await self.redis_client.get(key)
                if result:
                    self.cache_stats["hits"] += 1
                    return json.loads(result)
                else:
                    self.cache_stats["misses"] += 1
                    return None
            except Exception as e:
                logger.error(f"Redis get error for key {key}: {e}")
                self.cache_stats["redis_errors"] += 1
        
        # Fallback to memory cache
        if self.memory_fallback:
            self.cache_stats["fallback_usage"] += 1
            return await self.memory_fallback.get(key)
        
        self.cache_stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with fallback."""
        ttl = ttl or self.default_ttl
        
        # Use Redis if available
        if self.redis_client:
            try:
                serialized = json.dumps(value, default=str)
                await self.redis_client.setex(key, ttl, serialized)
                return True
            except Exception as e:
                logger.error(f"Redis set error for key {key}: {e}")
                self.cache_stats["redis_errors"] += 1
        
        # Fallback to memory cache
        if self.memory_fallback:
            await self.memory_fallback.set(key, value, ttl)
            return True
        
        return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis with fallback."""
        # Use Redis if available
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis delete error for key {key}: {e}")
                self.cache_stats["redis_errors"] += 1
        
        # Fallback to memory cache
        if self.memory_fallback:
            await self.memory_fallback.delete(key)
            return True
        
        return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    return len(keys)
            except Exception as e:
                logger.error(f"Redis clear pattern error for {pattern}: {e}")
                self.cache_stats["redis_errors"] += 1
        
        # Memory fallback doesn't support patterns easily
        return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        hit_rate = (self.cache_stats["hits"] / max(self.cache_stats["total_requests"], 1)) * 100
        
        stats = {
            "cache_type": "redis_with_memory_fallback",
            "redis_available": self.redis_client is not None,
            "cache_hits": self.cache_stats["hits"],
            "cache_misses": self.cache_stats["misses"],
            "total_requests": self.cache_stats["total_requests"],
            "hit_rate_percentage": round(hit_rate, 2),
            "redis_errors": self.cache_stats["redis_errors"],
            "fallback_usage": self.cache_stats["fallback_usage"],
            "redis_url": self.redis_url if self.redis_client else "not_connected"
        }
        
        # Add memory fallback stats if available
        if self.memory_fallback:
            memory_stats = self.memory_fallback.get_cache_stats()
            stats["memory_fallback_stats"] = memory_stats
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for Redis connection."""
        if self.redis_client:
            try:
                await self.redis_client.ping()
                return {"redis_healthy": True, "connection_status": "connected"}
            except Exception as e:
                return {"redis_healthy": False, "connection_status": f"error: {e}"}
        
        return {"redis_healthy": False, "connection_status": "not_initialized"}

class MemoryCacheManager:
    """Enhanced in-memory caching manager with intelligent expiration and warming."""
    
    def __init__(self):
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.max_memory_cache_size = 2000  # Increased for better performance
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "evictions": 0,
            "cache_warming_hits": 0
        }
        self.cache_warming_enabled = True
        self.cache_access_frequency: Dict[str, int] = {}  # Track access patterns
        
    async def initialize(self, **kwargs):
        """Initialize cache manager."""
        logger.info("Memory cache manager initialized")
        return True
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key from prefix and parameters."""
        # Filter out object instances and focus on data values
        filtered_args = []
        for arg in args:
            if hasattr(arg, '__dict__'):
                # Skip object instances - use class name or identifier instead
                continue
            elif isinstance(arg, (str, int, float, bool, type(None))):
                filtered_args.append(str(arg))
        
        key_data = f"{prefix}:{':'.join(filtered_args)}"
        
        if kwargs:
            # Filter kwargs to only include serializable values
            filtered_kwargs = {k: v for k, v in kwargs.items() 
                             if isinstance(v, (str, int, float, bool, type(None)))}
            if filtered_kwargs:
                sorted_kwargs = sorted(filtered_kwargs.items())
                key_data += f":{':'.join(f'{k}={v}' for k, v in sorted_kwargs)}"
        
        # Hash long keys to keep them manageable
        if len(key_data) > 200:
            key_data = f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
        
        return key_data
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with frequency tracking."""
        self.cache_stats["total_requests"] += 1
        
        if key in self.memory_cache:
            cached_item = self.memory_cache[key]
            if cached_item["expires"] > time.time():
                self.cache_stats["hits"] += 1
                # Track access frequency for intelligent eviction
                self.cache_access_frequency[key] = self.cache_access_frequency.get(key, 0) + 1
                
                # Update last accessed time for LRU eviction
                cached_item["last_accessed"] = time.time()
                return cached_item["value"]
            else:
                del self.memory_cache[key]
                if key in self.cache_access_frequency:
                    del self.cache_access_frequency[key]
        
        self.cache_stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL and access tracking."""
        try:
            self._cleanup_memory_cache()
            current_time = time.time()
            self.memory_cache[key] = {
                "value": value,
                "expires": current_time + ttl,
                "created": current_time,
                "last_accessed": current_time,
                "ttl": ttl
            }
            # Initialize access frequency
            self.cache_access_frequency[key] = 0
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self.memory_cache:
            del self.memory_cache[key]
            return True
        return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache keys matching pattern."""
        keys_to_delete = [key for key in self.memory_cache.keys() 
                         if self._matches_pattern(key, pattern)]
        for key in keys_to_delete:
            del self.memory_cache[key]
        return len(keys_to_delete)
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for memory cache."""
        if '*' in pattern:
            pattern_parts = pattern.split('*')
            if len(pattern_parts) == 2:
                prefix, suffix = pattern_parts
                return key.startswith(prefix) and key.endswith(suffix)
        return key == pattern
    
    def _cleanup_memory_cache(self):
        """Intelligent cache cleanup with LRU and frequency-based eviction."""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, item in self.memory_cache.items()
            if item["expires"] <= current_time
        ]
        for key in expired_keys:
            del self.memory_cache[key]
            if key in self.cache_access_frequency:
                del self.cache_access_frequency[key]
        
        # Enforce size limit with intelligent eviction
        if len(self.memory_cache) >= self.max_memory_cache_size:
            entries_to_remove = max(100, len(self.memory_cache) // 10)
            
            # Score entries based on access frequency and recency
            scored_keys = []
            for key, item in self.memory_cache.items():
                frequency = self.cache_access_frequency.get(key, 0)
                recency_score = current_time - item.get("last_accessed", item.get("created", current_time))
                age_score = current_time - item.get("created", current_time)
                
                # Lower score = higher priority for eviction
                # Higher frequency and recent access = lower eviction score
                score = recency_score + age_score - (frequency * 10)
                scored_keys.append((score, key))
            
            # Sort by score (highest score first = most suitable for eviction)
            scored_keys.sort(reverse=True)
            
            # Remove entries with highest eviction scores
            for _, key in scored_keys[:entries_to_remove]:
                del self.memory_cache[key]
                if key in self.cache_access_frequency:
                    del self.cache_access_frequency[key]
                self.cache_stats["evictions"] += 1
    
    async def warm_cache(self, db_session=None):
        """Warm cache with frequently accessed data."""
        if not self.cache_warming_enabled or not db_session:
            return
        
        try:
            # Import here to avoid circular dependency
            from database import User, Photo
            from sqlalchemy import select, func
            
            logger.info("Starting cache warming...")
            
            # Warm platform stats (most frequently accessed)
            await optimized_db_ops.get_cached_platform_stats(db_session)
            
            # Warm public photos (high traffic)
            await optimized_db_ops.get_cached_public_photos(db_session, 0, 10)
            
            # Get top active users and warm their photo lists
            user_activity_query = select(Photo.user_id, func.count(Photo.id).label('photo_count')).group_by(Photo.user_id).order_by(func.count(Photo.id).desc()).limit(5)
            result = await db_session.execute(user_activity_query)
            top_users = result.fetchall()
            
            for user_row in top_users:
                user_id = user_row[0]
                await optimized_db_ops.get_cached_user_photos(db_session, user_id, 0, 10)
            
            self.cache_stats["cache_warming_hits"] = len(self.memory_cache)
            logger.info(f"Cache warming completed. Warmed {len(self.memory_cache)} entries")
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get enhanced cache performance statistics."""
        hit_rate = (self.cache_stats["hits"] / max(self.cache_stats["total_requests"], 1)) * 100
        
        # Calculate cache efficiency metrics
        most_accessed_keys = sorted(
            self.cache_access_frequency.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return {
            "cache_hits": self.cache_stats["hits"],
            "cache_misses": self.cache_stats["misses"],
            "total_requests": self.cache_stats["total_requests"],
            "hit_rate_percentage": round(hit_rate, 2),
            "memory_cache_size": len(self.memory_cache),
            "max_cache_size": self.max_memory_cache_size,
            "cache_evictions": self.cache_stats["evictions"],
            "cache_warming_entries": self.cache_stats["cache_warming_hits"],
            "most_accessed_keys": [key for key, count in most_accessed_keys],
            "cache_type": "enhanced_memory",
            "features": ["lru_eviction", "frequency_tracking", "cache_warming", "intelligent_cleanup"]
        }

class ConnectionPoolManager:
    """Database connection pool manager."""
    
    def __init__(self):
        self.pool_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "connection_errors": 0
        }
    
    def configure_pool(self, engine):
        """Configure connection pool settings."""
        pool_settings = {
            "pool_size": 20,
            "max_overflow": 30,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "pool_timeout": 30,
        }
        
        logger.info(f"Database connection pool configured: {pool_settings}")
        return pool_settings
    
    async def get_pool_stats(self, engine=None) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return self.pool_stats.copy()

class QueryOptimizer:
    """Database query optimization and monitoring."""
    
    def __init__(self):
        self.query_stats = {}
        self.slow_queries = []
        self.slow_query_threshold = 1.0
        self.max_slow_queries = 50
    
    def monitor_query(self, query_name: str):
        """Decorator to monitor query performance."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Record query statistics
                    if query_name not in self.query_stats:
                        self.query_stats[query_name] = {
                            "count": 0,
                            "total_time": 0.0,
                            "min_time": float('inf'),
                            "max_time": 0.0,
                            "errors": 0
                        }
                    
                    stats = self.query_stats[query_name]
                    stats["count"] += 1
                    stats["total_time"] += duration
                    stats["min_time"] = min(stats["min_time"], duration)
                    stats["max_time"] = max(stats["max_time"], duration)
                    
                    # Track slow queries
                    if duration > self.slow_query_threshold:
                        slow_query = {
                            "query_name": query_name,
                            "duration": duration,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        self.slow_queries.append(slow_query)
                        if len(self.slow_queries) > self.max_slow_queries:
                            self.slow_queries.pop(0)
                        
                        logger.warning(f"Slow query detected: {query_name} took {duration:.2f}s")
                    
                    return result
                    
                except Exception as e:
                    if query_name in self.query_stats:
                        self.query_stats[query_name]["errors"] += 1
                    logger.error(f"Query error in {query_name}: {e}")
                    raise
                    
            return wrapper
        return decorator
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get query performance statistics."""
        stats_summary = {}
        for query_name, stats in self.query_stats.items():
            avg_time = stats["total_time"] / max(stats["count"], 1)
            stats_summary[query_name] = {
                "count": stats["count"],
                "average_time": round(avg_time, 4),
                "min_time": round(stats["min_time"], 4),
                "max_time": round(stats["max_time"], 4),
                "total_time": round(stats["total_time"], 4),
                "errors": stats["errors"],
                "error_rate": round((stats["errors"] / max(stats["count"], 1)) * 100, 2)
            }
        
        return {
            "query_statistics": stats_summary,
            "slow_queries_count": len(self.slow_queries),
            "recent_slow_queries": self.slow_queries[-5:] if self.slow_queries else []
        }

class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self):
        # Use Redis cache in production, memory cache as fallback
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production" or os.getenv("USE_REDIS_CACHE", "false").lower() == "true":
            self.cache_manager = RedisCacheManager()
            logger.info("Using Redis cache manager for production performance")
        else:
            self.cache_manager = MemoryCacheManager()
            logger.info("Using memory cache manager for development")
            
        self.pool_manager = ConnectionPoolManager()
        self.query_optimizer = QueryOptimizer()
        self.request_times = []
        self.max_request_history = 1000
    
    async def initialize(self, engine=None, **kwargs):
        """Initialize performance optimization components."""
        logger.info("Initializing performance optimization...")
        
        # Initialize cache
        await self.cache_manager.initialize(**kwargs)
        
        # Configure connection pool
        if engine:
            self.pool_manager.configure_pool(engine)
        
        logger.info("Performance optimization initialized with enhanced memory cache")
        return True
    
    async def warm_application_cache(self, db_session):
        """Warm application cache during startup."""
        await self.cache_manager.warm_cache(db_session)
    
    def get_cache_analytics(self) -> Dict[str, Any]:
        """Get detailed cache analytics for optimization."""
        cache_stats = self.cache_manager.get_cache_stats()
        
        return {
            "cache_performance": cache_stats,
            "recommendations": self._get_cache_recommendations(cache_stats),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_cache_recommendations(self, cache_stats: Dict[str, Any]) -> List[str]:
        """Generate cache optimization recommendations."""
        recommendations = []
        
        hit_rate = cache_stats.get("hit_rate_percentage", 0)
        if hit_rate < 50:
            recommendations.append("Consider increasing cache TTL for frequently accessed data")
        if hit_rate < 30:
            recommendations.append("Enable cache warming for better performance")
        
        evictions = cache_stats.get("cache_evictions", 0)
        if evictions > cache_stats.get("cache_hits", 0) * 0.1:
            recommendations.append("Consider increasing cache size to reduce evictions")
        
        cache_size = cache_stats.get("memory_cache_size", 0)
        max_size = cache_stats.get("max_cache_size", 1000)
        if cache_size > max_size * 0.9:
            recommendations.append("Cache approaching maximum size - consider optimization")
        
        if not recommendations:
            recommendations.append("Cache performance is optimal")
        
        return recommendations
    
    def cache_result(self, cache_key_prefix: str, ttl: int = 300):
        """Decorator to cache function results."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self.cache_manager._generate_cache_key(cache_key_prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.cache_manager.set(cache_key, result, ttl)
                
                return result
            return wrapper
        return decorator
    
    def record_request_time(self, duration: float):
        """Record request processing time."""
        self.request_times.append({
            "duration": duration,
            "timestamp": time.time()
        })
        
        if len(self.request_times) > self.max_request_history:
            self.request_times.pop(0)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        try:
            # Calculate request metrics
            recent_requests = [
                req for req in self.request_times
                if time.time() - req["timestamp"] < 60  # Last minute
            ]
            
            if recent_requests:
                avg_response_time = sum(req["duration"] for req in recent_requests) / len(recent_requests)
                requests_per_second = len(recent_requests) / 60
            else:
                avg_response_time = 0.0
                requests_per_second = 0.0
            
            # Get cache stats
            cache_stats = self.cache_manager.get_cache_stats()
            
            # Get query stats
            query_stats = self.query_optimizer.get_query_stats()
            
            return {
                "performance_metrics": {
                    "requests_per_second": round(requests_per_second, 2),
                    "average_response_time_ms": round(avg_response_time * 1000, 2),
                    "total_requests_tracked": len(self.request_times),
                    "recent_requests_count": len(recent_requests)
                },
                "cache_performance": cache_stats,
                "query_performance": query_stats,
                "optimization_status": {
                    "cache_enabled": True,
                    "cache_type": "memory_only",
                    "query_monitoring_enabled": True,
                    "connection_pooling_enabled": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {e}")
            return {"error": str(e)}

# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()

# Convenience decorators
def cache_result(cache_key_prefix: str, ttl: int = 300):
    """Cache function result decorator."""
    return performance_optimizer.cache_result(cache_key_prefix, ttl)

def monitor_query(query_name: str):
    """Monitor query performance decorator."""
    return performance_optimizer.query_optimizer.monitor_query(query_name)

# Optimized database operations
class OptimizedDatabaseOperations:
    """Optimized database operations with caching and monitoring."""
    
    def __init__(self, performance_optimizer: PerformanceOptimizer):
        self.perf = performance_optimizer
    
    @monitor_query("get_user_by_id")
    async def get_cached_user_by_id(self, db: AsyncSession, user_id: int):
        """Get user by ID with manual caching."""
        cache_key = f"user_by_id:{user_id}"
        
        # Try cache first
        cached_user = await self.perf.cache_manager.get(cache_key)
        if cached_user is not None:
            return cached_user
        
        # Query database
        from database import User
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user:
            user_data = {
                "id": user.id,
                "email": user.email,
                "is_verified": user.is_verified,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat()
            }
            # Cache for 10 minutes
            await self.perf.cache_manager.set(cache_key, user_data, ttl=600)
            return user_data
        return None
    
    @monitor_query("get_user_photos")
    async def get_cached_user_photos(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20):
        """Get user photos with manual caching."""
        cache_key = f"user_photos:{user_id}:{skip}:{limit}"
        
        # Try cache first
        cached_photos = await self.perf.cache_manager.get(cache_key)
        if cached_photos is not None:
            return cached_photos
        
        # Query database
        from database import Photo
        result = await db.execute(
            select(Photo)
            .where(Photo.user_id == user_id)
            .order_by(Photo.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        photos = result.scalars().all()
        
        photo_data = [
            {
                "id": photo.id,
                "filename": photo.filename,
                "original_filename": photo.original_filename,
                "content_type": photo.content_type,
                "file_size": photo.file_size,
                "title": photo.title,
                "description": photo.description,
                "is_public": photo.is_public,
                "created_at": photo.created_at.isoformat()
            }
            for photo in photos
        ]
        
        # Cache for 5 minutes
        await self.perf.cache_manager.set(cache_key, photo_data, ttl=300)
        return photo_data
    
    @monitor_query("get_public_photos")
    async def get_cached_public_photos(self, db: AsyncSession, skip: int = 0, limit: int = 20):
        """Get public photos with manual caching."""
        cache_key = f"public_photos:{skip}:{limit}"
        
        # Try cache first
        cached_photos = await self.perf.cache_manager.get(cache_key)
        if cached_photos is not None:
            return cached_photos
        
        # Query database
        from database import Photo
        result = await db.execute(
            select(Photo)
            .where(Photo.is_public == True)
            .order_by(Photo.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        photos = result.scalars().all()
        
        photo_data = [
            {
                "id": photo.id,
                "filename": photo.filename,
                "original_filename": photo.original_filename,
                "content_type": photo.content_type,
                "file_size": photo.file_size,
                "title": photo.title,
                "description": photo.description,
                "is_public": photo.is_public,
                "created_at": photo.created_at.isoformat()
            }
            for photo in photos
        ]
        
        # Cache for 3 minutes (public photos change less frequently)
        await self.perf.cache_manager.set(cache_key, photo_data, ttl=180)
        return photo_data
    
    @monitor_query("get_platform_stats")
    async def get_cached_platform_stats(self, db: AsyncSession):
        """Get platform statistics with optimized single query and manual caching."""
        cache_key = "platform_stats"
        
        # Try cache first
        cached_stats = await self.perf.cache_manager.get(cache_key)
        if cached_stats is not None:
            return cached_stats
        
        # Query database with optimized single query
        from database import User, Photo, Session
        from sqlalchemy import text
        
        # Single optimized query using CTEs for better performance
        query = text("""
            WITH user_stats AS (
                SELECT COUNT(*) as total_users FROM users
            ),
            photo_stats AS (
                SELECT COUNT(*) as total_photos FROM photos
            ),
            session_stats AS (
                SELECT COUNT(*) as active_sessions FROM sessions WHERE is_active = true
            )
            SELECT 
                user_stats.total_users,
                photo_stats.total_photos,
                session_stats.active_sessions
            FROM user_stats, photo_stats, session_stats
        """)
        
        result = await db.execute(query)
        row = result.fetchone()
        
        stats_data = {
            "total_users": row[0] if row else 0,
            "total_photos": row[1] if row else 0,
            "active_sessions": row[2] if row else 0,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Cache for 1 minute (stats change frequently)
        await self.perf.cache_manager.set(cache_key, stats_data, ttl=60)
        return stats_data
    
    async def invalidate_user_cache(self, user_id: int):
        """Invalidate user-related cache entries."""
        await self.perf.cache_manager.clear_pattern(f"user_by_id:{user_id}:*")
        await self.perf.cache_manager.clear_pattern(f"user_photos:{user_id}:*")
    
    async def invalidate_photo_cache(self):
        """Invalidate photo-related cache entries."""
        await self.perf.cache_manager.clear_pattern("public_photos:*")
        await self.perf.cache_manager.clear_pattern("platform_stats:*")
    
    @monitor_query("batch_photo_operations")
    async def get_photos_with_user_data(self, db: AsyncSession, photo_ids: List[int]):
        """Get photos with user data in a single optimized query."""
        from database import Photo, User
        from sqlalchemy.orm import selectinload
        
        # Use join to get photos with user data in one query
        result = await db.execute(
            select(Photo, User)
            .join(User, Photo.user_id == User.id)
            .where(Photo.id.in_(photo_ids))
            .order_by(Photo.created_at.desc())
        )
        
        return [
            {
                "photo": {
                    "id": photo.id,
                    "filename": photo.filename,
                    "original_filename": photo.original_filename,
                    "content_type": photo.content_type,
                    "file_size": photo.file_size,
                    "title": photo.title,
                    "description": photo.description,
                    "is_public": photo.is_public,
                    "created_at": photo.created_at.isoformat()
                },
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "is_verified": user.is_verified
                }
            }
            for photo, user in result.all()
        ]
    
    @monitor_query("optimized_photo_search")
    async def search_photos_optimized(self, db: AsyncSession, user_id: Optional[int] = None, 
                                     is_public: Optional[bool] = None, title_contains: Optional[str] = None,
                                     skip: int = 0, limit: int = 20):
        """Optimized photo search with multiple filters."""
        from database import Photo
        
        query = select(Photo)
        
        # Apply filters efficiently
        conditions = []
        if user_id is not None:
            conditions.append(Photo.user_id == user_id)
        if is_public is not None:
            conditions.append(Photo.is_public == is_public)
        if title_contains:
            conditions.append(Photo.title.ilike(f"%{title_contains}%"))
        
        if conditions:
            query = query.where(*conditions)
        
        # Use efficient ordering and pagination
        query = query.order_by(Photo.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        photos = result.scalars().all()
        
        return [
            {
                "id": photo.id,
                "filename": photo.filename,
                "original_filename": photo.original_filename,
                "content_type": photo.content_type,
                "file_size": photo.file_size,
                "title": photo.title,
                "description": photo.description,
                "is_public": photo.is_public,
                "created_at": photo.created_at.isoformat()
            }
            for photo in photos
        ]
    
    async def get_performance_recommendations(self) -> Dict[str, Any]:
        """Get database performance optimization recommendations."""
        return {
            "recommended_indexes": [
                {
                    "table": "photos",
                    "index": "CREATE INDEX CONCURRENTLY idx_photos_user_created ON photos(user_id, created_at DESC);",
                    "reason": "Optimize user photo listing queries"
                },
                {
                    "table": "photos", 
                    "index": "CREATE INDEX CONCURRENTLY idx_photos_public_created ON photos(is_public, created_at DESC) WHERE is_public = true;",
                    "reason": "Optimize public photo queries with partial index"
                },
                {
                    "table": "photos",
                    "index": "CREATE INDEX CONCURRENTLY idx_photos_title_gin ON photos USING gin(to_tsvector('english', title)) WHERE title IS NOT NULL;",
                    "reason": "Enable full-text search on photo titles"
                },
                {
                    "table": "sessions",
                    "index": "CREATE INDEX CONCURRENTLY idx_sessions_active_user ON sessions(user_id, is_active) WHERE is_active = true;",
                    "reason": "Optimize active session lookups"
                },
                {
                    "table": "users",
                    "index": "CREATE INDEX CONCURRENTLY idx_users_email_hash ON users USING hash(email);",
                    "reason": "Optimize login email lookups"
                }
            ],
            "query_optimizations": [
                "Use CTEs for complex aggregate queries",
                "Implement connection pooling with proper sizing",
                "Enable query plan caching", 
                "Use EXPLAIN ANALYZE for slow query identification",
                "Consider read replicas for reporting queries"
            ],
            "cache_strategy": [
                "Implement Redis for distributed caching",
                "Use cache invalidation patterns on data updates",
                "Cache expensive aggregation queries longer (5-10 minutes)",
                "Implement cache warming for frequently accessed data"
            ]
        }

# Global optimized database operations
optimized_db_ops = OptimizedDatabaseOperations(performance_optimizer)