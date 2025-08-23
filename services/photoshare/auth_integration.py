#!/usr/bin/env python3
"""
Authentication Service Integration
==================================

Integration layer for the photo sharing application to communicate with
the dedicated authentication service.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import httpx
import jwt
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import wraps
import time

logger = logging.getLogger(__name__)

class AuthServiceClient:
    """Client for communicating with the authentication service."""
    
    def __init__(self):
        self.auth_service_url = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
        self.service_api_key = os.getenv("AUTH_SERVICE_API_KEY", "")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_audience = os.getenv("JWT_AUDIENCE", "photoshare-app")
        
        # HTTP client for service-to-service communication
        self.http_client = httpx.AsyncClient(
            base_url=self.auth_service_url,
            timeout=30.0,
            headers={"X-Service-API-Key": self.service_api_key} if self.service_api_key else {}
        )
        
        # Cache for JWT public keys and user info
        self._public_keys_cache = {}
        self._user_cache = {}
        self._permissions_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
    async def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token with the authentication service."""
        try:
            # First, try to decode without verification to get header info
            jwt.decode(token, options={"verify_signature": False})
            
            # Get public key for verification
            public_key = await self._get_public_key()
            
            # Verify the token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[self.jwt_algorithm],
                audience=self.jwt_audience
            )
            
            return payload
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(status_code=401, detail="Token verification failed")
            
    async def get_user_info(self, user_uuid: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get user information from authentication service."""
        
        # Check cache first
        if use_cache and user_uuid in self._user_cache:
            cached_data, cache_time = self._user_cache[user_uuid]
            if time.time() - cache_time < self._cache_ttl:
                return cached_data
        
        try:
            response = await self.http_client.get(f"/api/auth/users/{user_uuid}")
            response.raise_for_status()
            
            user_data = response.json()
            
            # Cache the result
            if use_cache:
                self._user_cache[user_uuid] = (user_data, time.time())
            
            return user_data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="User not found")
            else:
                logger.error(f"Auth service error: {e}")
                raise HTTPException(status_code=503, detail="Authentication service unavailable")
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise HTTPException(status_code=503, detail="Authentication service error")
            
    async def get_user_permissions(self, user_uuid: str, use_cache: bool = True) -> List[str]:
        """Get user permissions from authentication service."""
        
        # Check cache first
        if use_cache and user_uuid in self._permissions_cache:
            cached_data, cache_time = self._permissions_cache[user_uuid]
            if time.time() - cache_time < self._cache_ttl:
                return cached_data
        
        try:
            response = await self.http_client.get(f"/api/auth/users/{user_uuid}/permissions")
            response.raise_for_status()
            
            permissions_data = response.json()
            permissions = permissions_data.get("permissions", [])
            
            # Cache the result
            if use_cache:
                self._permissions_cache[user_uuid] = (permissions, time.time())
            
            return permissions
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user permissions: {e}")
            return []  # Fail-safe: no permissions
        except Exception as e:
            logger.error(f"Permissions service error: {e}")
            return []  # Fail-safe: no permissions
            
    async def validate_user_permission(self, user_uuid: str, resource: str, action: str) -> bool:
        """Check if user has specific permission."""
        permissions = await self.get_user_permissions(user_uuid)
        required_permission = f"{resource}:{action}"
        
        # Check direct permission
        if required_permission in permissions:
            return True
        
        # Check wildcard permissions
        wildcard_resource = f"{resource}:*"
        wildcard_action = f"*:{action}"
        wildcard_all = "*:*"
        
        return any(perm in permissions for perm in [wildcard_resource, wildcard_action, wildcard_all])
        
    async def invalidate_user_session(self, token: str) -> bool:
        """Invalidate user session in authentication service."""
        try:
            response = await self.http_client.post(
                "/api/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to invalidate session: {e}")
            return False
            
    async def _get_public_key(self):
        """Get JWT public key from authentication service."""
        public_key_url = os.getenv("JWT_PUBLIC_KEY_URL", f"{self.auth_service_url}/api/auth/public-key")
        
        # Check cache
        if public_key_url in self._public_keys_cache:
            cached_key, cache_time = self._public_keys_cache[public_key_url]
            if time.time() - cache_time < 3600:  # Cache for 1 hour
                return cached_key
        
        try:
            response = await self.http_client.get(public_key_url)
            response.raise_for_status()
            
            key_data = response.json()
            public_key = key_data.get("public_key")
            
            if not public_key:
                raise ValueError("No public key in response")
            
            # Cache the key
            self._public_keys_cache[public_key_url] = (public_key, time.time())
            
            return public_key
            
        except Exception as e:
            logger.error(f"Failed to get public key: {e}")
            # Fallback: use shared secret (less secure)
            return os.getenv("JWT_SECRET_KEY", "fallback-key")
            
    async def health_check(self) -> Dict[str, Any]:
        """Check authentication service health."""
        try:
            response = await self.http_client.get("/health")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Auth service health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
            
    def clear_cache(self):
        """Clear all caches."""
        self._user_cache.clear()
        self._permissions_cache.clear()
        self._public_keys_cache.clear()
        
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

# Global auth service client
auth_client = AuthServiceClient()

class AuthenticatedUser:
    """Represents an authenticated user with their context."""
    
    def __init__(self, user_data: Dict[str, Any], token_payload: Dict[str, Any]):
        self.uuid = user_data.get("uuid")
        self.id = user_data.get("id") 
        self.email = user_data.get("email")
        self.first_name = user_data.get("first_name")
        self.last_name = user_data.get("last_name")
        self.display_name = user_data.get("display_name")
        self.is_verified = user_data.get("is_verified", False)
        self.is_active = user_data.get("is_active", True)
        self.roles = user_data.get("roles", [])
        self.permissions = user_data.get("permissions", [])
        
        # Token information
        self.token_payload = token_payload
        self.token_issued_at = token_payload.get("iat")
        self.token_expires_at = token_payload.get("exp")
        
    def has_permission(self, resource: str, action: str) -> bool:
        """Check if user has specific permission."""
        required_permission = f"{resource}:{action}"
        
        # Check direct permission
        if required_permission in self.permissions:
            return True
        
        # Check wildcard permissions
        wildcard_resource = f"{resource}:*"
        wildcard_action = f"*:{action}"
        wildcard_all = "*:*"
        
        return any(perm in self.permissions for perm in [wildcard_resource, wildcard_action, wildcard_all])
        
    def has_role(self, role_name: str) -> bool:
        """Check if user has specific role."""
        return role_name in self.roles
        
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.has_role("admin") or self.has_role("superadmin")
        
    def can_access_photo(self, photo_owner_uuid: str, photo_is_public: bool = False) -> bool:
        """Check if user can access a specific photo."""
        # User can access their own photos
        if self.uuid == photo_owner_uuid:
            return True
            
        # Anyone can access public photos
        if photo_is_public:
            return True
            
        # Admins can access all photos
        if self.is_admin():
            return True
            
        # Check specific photo permissions
        return self.has_permission("photos", "read_all")
        
    def can_modify_photo(self, photo_owner_uuid: str) -> bool:
        """Check if user can modify a specific photo."""
        # User can modify their own photos
        if self.uuid == photo_owner_uuid:
            return True
            
        # Admins can modify all photos
        if self.is_admin():
            return True
            
        # Check specific photo permissions
        return self.has_permission("photos", "write_all")
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uuid": self.uuid,
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "roles": self.roles,
            "permissions": self.permissions
        }

# FastAPI Dependencies

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthenticatedUser:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    
    try:
        # Verify token with auth service
        token_payload = await auth_client.verify_jwt_token(token)
        
        # Get user information
        user_uuid = token_payload.get("sub")
        if not user_uuid:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        user_data = await auth_client.get_user_info(user_uuid)
        
        # Get user permissions
        permissions = await auth_client.get_user_permissions(user_uuid)
        user_data["permissions"] = permissions
        
        return AuthenticatedUser(user_data, token_payload)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

async def get_optional_user(request: Request) -> Optional[AuthenticatedUser]:
    """Get current user if authenticated, None otherwise."""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
        
    try:
        token = auth_header.split(" ", 1)[1]
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        return await get_current_user(credentials)
    except Exception:
        return None

def require_permission(resource: str, action: str):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the current_user parameter
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, AuthenticatedUser):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if not current_user.has_permission(resource, action):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role_name: str):
    """Decorator to require specific role."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the current_user parameter
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, AuthenticatedUser):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if not current_user.has_role(role_name):
                raise HTTPException(status_code=403, detail=f"Role '{role_name}' required")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_verified_user(func):
    """Decorator to require verified user."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find the current_user parameter
        current_user = None
        for key, value in kwargs.items():
            if isinstance(value, AuthenticatedUser):
                current_user = value
                break
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if not current_user.is_verified:
            raise HTTPException(status_code=403, detail="Email verification required")
        
        return await func(*args, **kwargs)
    return wrapper