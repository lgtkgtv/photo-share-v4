#!/usr/bin/env python3
"""
Unit tests for SSO provider integration.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import httpx

from services.auth_service.sso_providers import (
    SSOProvider, SSOUserProfile, SSOConfig, SSOProviderManager
)

class TestSSOUserProfile:
    """Test SSO User Profile data class."""
    
    def test_profile_creation(self):
        """Test SSO user profile creation."""
        profile = SSOUserProfile(
            provider="google",
            external_id="google123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            email_verified=True
        )
        
        assert profile.provider == "google"
        assert profile.external_id == "google123"
        assert profile.email == "test@example.com"
        assert profile.first_name == "Test"
        assert profile.last_name == "User"
        assert profile.display_name == "Test User"
        assert profile.avatar_url == "https://example.com/avatar.jpg"
        assert profile.email_verified is True
    
    def test_profile_to_dict(self):
        """Test profile serialization to dictionary."""
        profile = SSOUserProfile(
            provider="google",
            external_id="google123",
            email="test@example.com",
            email_verified=True
        )
        
        profile_dict = profile.to_dict()
        
        assert profile_dict["provider"] == "google"
        assert profile_dict["external_id"] == "google123"
        assert profile_dict["email"] == "test@example.com"
        assert profile_dict["email_verified"] is True

class TestSSOConfig:
    """Test SSO Configuration."""
    
    def test_config_creation(self):
        """Test SSO config creation."""
        config = SSOConfig(
            provider=SSOProvider.GOOGLE,
            client_id="test_client_id",
            client_secret="test_client_secret",
            discovery_url="https://accounts.google.com/.well-known/openid_configuration"
        )
        
        assert config.provider == SSOProvider.GOOGLE
        assert config.client_id == "test_client_id"
        assert config.client_secret == "test_client_secret"
        assert config.discovery_url == "https://accounts.google.com/.well-known/openid_configuration"
        assert config.scopes == ["openid", "email", "profile"]  # Default scopes
    
    def test_config_custom_scopes(self):
        """Test SSO config with custom scopes."""
        config = SSOConfig(
            provider=SSOProvider.MICROSOFT,
            client_id="test_client_id",
            client_secret="test_client_secret",
            scopes=["openid", "email", "profile", "offline_access"]
        )
        
        assert config.scopes == ["openid", "email", "profile", "offline_access"]

class TestSSOProviderManager:
    """Test SSO Provider Manager."""
    
    @pytest.fixture
    def manager(self):
        """Create SSO provider manager."""
        return SSOProviderManager()
    
    @pytest.mark.asyncio
    async def test_initialize_with_google(self, manager):
        """Test initialization with Google SSO provider."""
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': 'test_google_id',
            'GOOGLE_CLIENT_SECRET': 'test_google_secret'
        }):
            await manager.initialize()
            
            assert "google" in manager.providers
            google_config = manager.providers["google"]
            assert google_config.provider == SSOProvider.GOOGLE
            assert google_config.client_id == "test_google_id"
            assert google_config.client_secret == "test_google_secret"
    
    @pytest.mark.asyncio
    async def test_initialize_with_microsoft(self, manager):
        """Test initialization with Microsoft SSO provider."""
        with patch.dict('os.environ', {
            'MICROSOFT_CLIENT_ID': 'test_ms_id',
            'MICROSOFT_CLIENT_SECRET': 'test_ms_secret',
            'MICROSOFT_TENANT_ID': 'test_tenant'
        }):
            await manager.initialize()
            
            assert "microsoft" in manager.providers
            ms_config = manager.providers["microsoft"]
            assert ms_config.provider == SSOProvider.MICROSOFT
            assert ms_config.client_id == "test_ms_id"
    
    @pytest.mark.asyncio
    async def test_get_authorization_url(self, manager):
        """Test authorization URL generation."""
        # Setup mock provider
        manager.providers["google"] = SSOConfig(
            provider=SSOProvider.GOOGLE,
            client_id="test_client_id",
            client_secret="test_client_secret",
            discovery_url="https://accounts.google.com/.well-known/openid_configuration"
        )
        
        # Mock discovery document
        mock_discovery = {
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth"
        }
        
        with patch.object(manager, '_get_discovery_document', return_value=mock_discovery):
            auth_url = await manager.get_authorization_url(
                "google", 
                "http://localhost:8000/callback",
                "test_state"
            )
            
            assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
            assert "client_id=test_client_id" in auth_url
            # URL encoding converts : to %3A and / to %2F
            assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback" in auth_url
            assert "state=test_state" in auth_url
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self, manager):
        """Test code exchange for tokens."""
        # Setup mock provider
        manager.providers["google"] = SSOConfig(
            provider=SSOProvider.GOOGLE,
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        # Mock discovery document
        mock_discovery = {
            "token_endpoint": "https://oauth2.googleapis.com/token"
        }
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "id_token": "test_id_token",
            "token_type": "Bearer"
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(manager, '_get_discovery_document', return_value=mock_discovery):
            with patch.object(manager.http_client, 'post', return_value=mock_response):
                tokens = await manager.exchange_code_for_tokens(
                    "google",
                    "test_code",
                    "http://localhost:8000/callback"
                )
                
                assert tokens["access_token"] == "test_access_token"
                assert tokens["id_token"] == "test_id_token"
    
    @pytest.mark.asyncio
    async def test_get_user_profile(self, manager):
        """Test getting user profile from SSO provider."""
        # Setup mock provider
        manager.providers["google"] = SSOConfig(
            provider=SSOProvider.GOOGLE,
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        # Mock discovery document
        mock_discovery = {
            "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo"
        }
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {
            "sub": "google123",
            "email": "test@example.com",
            "given_name": "Test",
            "family_name": "User",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "email_verified": True
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(manager, '_get_discovery_document', return_value=mock_discovery):
            with patch.object(manager.http_client, 'get', return_value=mock_response):
                profile = await manager.get_user_profile("google", "test_access_token")
                
                assert profile.provider == "google"
                assert profile.external_id == "google123"
                assert profile.email == "test@example.com"
                assert profile.first_name == "Test"
                assert profile.last_name == "User"
                assert profile.email_verified is True
    
    @pytest.mark.asyncio
    async def test_get_provider_list(self, manager):
        """Test getting list of available providers."""
        # Setup mock providers
        manager.providers = {
            "google": SSOConfig(
                provider=SSOProvider.GOOGLE,
                client_id="test_id",
                client_secret="test_secret"
            ),
            "microsoft": SSOConfig(
                provider=SSOProvider.MICROSOFT,
                client_id="test_id",
                client_secret="test_secret"
            )
        }
        
        providers = await manager.get_provider_list()
        
        assert len(providers) == 2
        assert any(p["name"] == "google" for p in providers)
        assert any(p["name"] == "microsoft" for p in providers)
    
    def test_map_user_profile_google(self, manager):
        """Test mapping Google user info to profile."""
        user_info = {
            "sub": "google123",
            "email": "test@example.com",
            "given_name": "Test",
            "family_name": "User",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "email_verified": True
        }
        
        profile = manager._map_user_profile("google", user_info)
        
        assert profile.provider == "google"
        assert profile.external_id == "google123"
        assert profile.email == "test@example.com"
        assert profile.first_name == "Test"
        assert profile.last_name == "User"
        assert profile.display_name == "Test User"
        assert profile.avatar_url == "https://example.com/avatar.jpg"
        assert profile.email_verified is True
    
    def test_map_user_profile_microsoft(self, manager):
        """Test mapping Microsoft user info to profile."""
        user_info = {
            "sub": "microsoft123",
            "email": "test@example.com",
            "given_name": "Test",
            "family_name": "User",
            "name": "Test User",
            "email_verified": True
        }
        
        profile = manager._map_user_profile("microsoft", user_info)
        
        assert profile.provider == "microsoft"
        assert profile.external_id == "microsoft123"
        assert profile.email == "test@example.com"
        assert profile.first_name == "Test"
        assert profile.last_name == "User"
        assert profile.display_name == "Test User"
        assert profile.avatar_url is None  # Microsoft doesn't provide picture
        assert profile.email_verified is True