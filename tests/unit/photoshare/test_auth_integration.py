#!/usr/bin/env python3
"""
Unit tests for authentication service integration.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
import jwt

from services.photoshare.auth_integration import (
    AuthServiceClient, AuthenticatedUser, get_current_user, get_optional_user
)

class TestAuthServiceClient:
    """Test Authentication Service Client."""
    
    @pytest.fixture
    def auth_client(self):
        """Create auth service client."""
        with patch.dict('os.environ', {
            'AUTH_SERVICE_URL': 'http://auth-service:8000',
            'AUTH_SERVICE_API_KEY': 'test_api_key',
            'JWT_ALGORITHM': 'HS256',
            'JWT_AUDIENCE': 'photoshare-app'
        }):
            return AuthServiceClient()
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_success(self, auth_client):
        """Test successful JWT token verification.

        AuthServiceClient verifies tokens with a shared HS256 secret
        (JWT_SECRET_KEY), not RSA public keys fetched from the auth service --
        there's no _get_public_key method or public-key cache on this class.
        """
        test_payload = {
            "sub": "user-uuid-123",
            "user_id": 1,
            "email": "test@example.com",
            "iat": 1234567890,
            "exp": 1234567890 + 1800
        }

        with patch('jwt.decode', return_value=test_payload) as mock_jwt_decode:
            result = await auth_client.verify_jwt_token('test_token')

            assert result == test_payload
            assert result["sub"] == "user-uuid-123"
            assert result["user_id"] == 1
            mock_jwt_decode.assert_called_once_with(
                'test_token',
                auth_client.jwt_secret_key,
                algorithms=[auth_client.jwt_algorithm],
                audience=auth_client.jwt_audience,
                issuer=auth_client.jwt_issuer
            )

    @pytest.mark.asyncio
    async def test_verify_jwt_token_invalid(self, auth_client):
        """Test JWT token verification with invalid token."""
        with patch('jwt.decode', side_effect=jwt.InvalidTokenError("Invalid token")):
            with pytest.raises(Exception):  # Should raise HTTPException
                await auth_client.verify_jwt_token('invalid_token')
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(self, auth_client):
        """Test successful user info retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "uuid": "user-uuid-123",
            "id": 1,
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_verified": True,
            "is_active": True
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(auth_client.http_client, 'get', return_value=mock_response):
            result = await auth_client.get_user_info('user-uuid-123')
            
            assert result["uuid"] == "user-uuid-123"
            assert result["email"] == "test@example.com"
            assert result["first_name"] == "Test"
    
    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self, auth_client):
        """Test user info retrieval with non-existent user."""
        mock_response = Mock()
        mock_response.status_code = 404
        
        with patch.object(auth_client.http_client, 'get') as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError("Not found", request=None, response=mock_response)
            
            with pytest.raises(Exception):  # Should raise HTTPException
                await auth_client.get_user_info('non-existent-uuid')
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_success(self, auth_client):
        """Test successful user permissions retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "permissions": ["photos:read", "photos:write", "albums:read"]
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(auth_client.http_client, 'get', return_value=mock_response):
            result = await auth_client.get_user_permissions('user-uuid-123')
            
            assert result == ["photos:read", "photos:write", "albums:read"]
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_failure(self, auth_client):
        """Test user permissions retrieval failure."""
        with patch.object(auth_client.http_client, 'get', side_effect=Exception("Service error")):
            result = await auth_client.get_user_permissions('user-uuid-123')
            
            assert result == []  # Should return empty list on failure
    
    @pytest.mark.asyncio
    async def test_validate_user_permission_success(self, auth_client):
        """Test successful permission validation."""
        with patch.object(auth_client, 'get_user_permissions', return_value=['photos:read', 'photos:write']):
            result = await auth_client.validate_user_permission('user-uuid-123', 'photos', 'read')
            assert result is True
            
            result = await auth_client.validate_user_permission('user-uuid-123', 'photos', 'write')
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_user_permission_failure(self, auth_client):
        """Test permission validation failure."""
        with patch.object(auth_client, 'get_user_permissions', return_value=['photos:read']):
            result = await auth_client.validate_user_permission('user-uuid-123', 'photos', 'delete')
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_user_permission_wildcard(self, auth_client):
        """Test permission validation with wildcards."""
        with patch.object(auth_client, 'get_user_permissions', return_value=['photos:*']):
            result = await auth_client.validate_user_permission('user-uuid-123', 'photos', 'read')
            assert result is True
            
            result = await auth_client.validate_user_permission('user-uuid-123', 'photos', 'write')
            assert result is True
            
            result = await auth_client.validate_user_permission('user-uuid-123', 'albums', 'read')
            assert result is False
    
    @pytest.mark.asyncio
    async def test_invalidate_user_session_success(self, auth_client):
        """Test successful session invalidation."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch.object(auth_client.http_client, 'post', return_value=mock_response):
            result = await auth_client.invalidate_user_session('test_token')
            assert result is True
    
    @pytest.mark.asyncio
    async def test_invalidate_user_session_failure(self, auth_client):
        """Test session invalidation failure."""
        with patch.object(auth_client.http_client, 'post', side_effect=Exception("Service error")):
            result = await auth_client.invalidate_user_session('test_token')
            assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, auth_client):
        """Test successful auth service health check."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status = Mock()
        
        with patch.object(auth_client.http_client, 'get', return_value=mock_response):
            result = await auth_client.health_check()
            assert result["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, auth_client):
        """Test auth service health check failure."""
        with patch.object(auth_client.http_client, 'get', side_effect=Exception("Service error")):
            result = await auth_client.health_check()
            assert result["status"] == "unhealthy"
    
    def test_clear_cache(self, auth_client):
        """Test cache clearing.

        No public-keys cache to clear here -- this client validates JWTs
        against a shared secret, not fetched RSA public keys.
        """
        # Add some mock data to caches
        auth_client._user_cache['user123'] = ({'data': 'test'}, 1234567890)
        auth_client._permissions_cache['user123'] = (['perm1'], 1234567890)

        auth_client.clear_cache()

        assert len(auth_client._user_cache) == 0
        assert len(auth_client._permissions_cache) == 0

class TestAuthenticatedUser:
    """Test Authenticated User class."""
    
    @pytest.fixture
    def user_data(self):
        """Sample user data."""
        return {
            "uuid": "user-uuid-123",
            "id": 1,
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "display_name": "Test User",
            "is_verified": True,
            "is_active": True,
            "roles": ["user", "photographer"],
            "permissions": ["photos:read", "photos:write", "albums:read"]
        }
    
    @pytest.fixture
    def token_payload(self):
        """Sample JWT token payload."""
        return {
            "sub": "user-uuid-123",
            "user_id": 1,
            "email": "test@example.com",
            "iat": 1234567890,
            "exp": 1234567890 + 1800
        }
    
    def test_authenticated_user_creation(self, user_data, token_payload):
        """Test authenticated user creation."""
        user = AuthenticatedUser(user_data, token_payload)
        
        assert user.uuid == "user-uuid-123"
        assert user.id == 1
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.display_name == "Test User"
        assert user.is_verified is True
        assert user.is_active is True
        assert user.roles == ["user", "photographer"]
        assert user.permissions == ["photos:read", "photos:write", "albums:read"]
    
    def test_has_permission_direct(self, user_data, token_payload):
        """Test direct permission checking."""
        user = AuthenticatedUser(user_data, token_payload)
        
        assert user.has_permission("photos", "read") is True
        assert user.has_permission("photos", "write") is True
        assert user.has_permission("albums", "read") is True
        assert user.has_permission("photos", "delete") is False
    
    def test_has_permission_wildcard(self, user_data, token_payload):
        """Test wildcard permission checking."""
        user_data["permissions"] = ["photos:*", "albums:read"]
        user = AuthenticatedUser(user_data, token_payload)
        
        assert user.has_permission("photos", "read") is True
        assert user.has_permission("photos", "write") is True
        assert user.has_permission("photos", "delete") is True
        assert user.has_permission("albums", "read") is True
        assert user.has_permission("albums", "write") is False
    
    def test_has_role(self, user_data, token_payload):
        """Test role checking."""
        user = AuthenticatedUser(user_data, token_payload)
        
        assert user.has_role("user") is True
        assert user.has_role("photographer") is True
        assert user.has_role("admin") is False
    
    def test_is_admin(self, user_data, token_payload):
        """Test admin role checking."""
        user = AuthenticatedUser(user_data, token_payload)
        assert user.is_admin() is False
        
        user_data["roles"] = ["user", "admin"]
        user = AuthenticatedUser(user_data, token_payload)
        assert user.is_admin() is True
        
        user_data["roles"] = ["superadmin"]
        user = AuthenticatedUser(user_data, token_payload)
        assert user.is_admin() is True
    
    def test_can_access_photo_owner(self, user_data, token_payload):
        """Test photo access for photo owner."""
        user = AuthenticatedUser(user_data, token_payload)
        
        # User can access their own photos
        assert user.can_access_photo("user-uuid-123", False) is True
        assert user.can_access_photo("user-uuid-123", True) is True
    
    def test_can_access_photo_public(self, user_data, token_payload):
        """Test public photo access."""
        user = AuthenticatedUser(user_data, token_payload)
        
        # Anyone can access public photos
        assert user.can_access_photo("other-user-uuid", True) is True
        assert user.can_access_photo("other-user-uuid", False) is False
    
    def test_can_access_photo_admin(self, user_data, token_payload):
        """Test photo access for admin users."""
        user_data["roles"] = ["admin"]
        user = AuthenticatedUser(user_data, token_payload)
        
        # Admins can access all photos
        assert user.can_access_photo("other-user-uuid", False) is True
        assert user.can_access_photo("other-user-uuid", True) is True
    
    def test_can_modify_photo_owner(self, user_data, token_payload):
        """Test photo modification for photo owner."""
        user = AuthenticatedUser(user_data, token_payload)
        
        # User can modify their own photos
        assert user.can_modify_photo("user-uuid-123") is True
        assert user.can_modify_photo("other-user-uuid") is False
    
    def test_can_modify_photo_admin(self, user_data, token_payload):
        """Test photo modification for admin users."""
        user_data["roles"] = ["admin"]
        user = AuthenticatedUser(user_data, token_payload)
        
        # Admins can modify all photos
        assert user.can_modify_photo("user-uuid-123") is True
        assert user.can_modify_photo("other-user-uuid") is True
    
    def test_to_dict(self, user_data, token_payload):
        """Test user serialization to dictionary."""
        user = AuthenticatedUser(user_data, token_payload)
        
        user_dict = user.to_dict()
        
        assert user_dict["uuid"] == "user-uuid-123"
        assert user_dict["email"] == "test@example.com"
        assert user_dict["first_name"] == "Test"
        assert user_dict["roles"] == ["user", "photographer"]
        assert user_dict["permissions"] == ["photos:read", "photos:write", "albums:read"]