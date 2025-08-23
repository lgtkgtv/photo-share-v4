#!/usr/bin/env python3
"""
SSO Provider Integration
========================

Supports multiple SSO providers with OIDC and SAML protocols.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import jwt

logger = logging.getLogger(__name__)

class SSOProvider(str, Enum):
    """Supported SSO providers."""
    GOOGLE = "google"
    MICROSOFT = "microsoft" 
    OKTA = "okta"
    AUTH0 = "auth0"
    GENERIC_OIDC = "generic_oidc"
    GENERIC_SAML = "generic_saml"

@dataclass
class SSOUserProfile:
    """Standardized user profile from SSO providers."""
    provider: str
    external_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email_verified: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "external_id": self.external_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "email_verified": self.email_verified
        }

@dataclass
class SSOConfig:
    """SSO provider configuration."""
    provider: SSOProvider
    client_id: str
    client_secret: str
    discovery_url: Optional[str] = None
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    jwks_url: Optional[str] = None
    saml_metadata_url: Optional[str] = None
    saml_certificate: Optional[str] = None
    scopes: List[str] = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["openid", "email", "profile"]

class SSOProviderManager:
    """Manages multiple SSO providers and their configurations."""
    
    def __init__(self):
        self.providers: Dict[str, SSOConfig] = {}
        self.http_client = httpx.AsyncClient(timeout=30)
        self._discovery_cache: Dict[str, Dict[str, Any]] = {}
        self._jwks_cache: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize SSO providers from environment variables."""
        await self._load_provider_configs()
        
    async def _load_provider_configs(self):
        """Load SSO provider configurations from environment."""
        
        # Google OAuth 2.0 / OIDC
        if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
            self.providers["google"] = SSOConfig(
                provider=SSOProvider.GOOGLE,
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                discovery_url="https://accounts.google.com/.well-known/openid_configuration",
                scopes=["openid", "email", "profile"]
            )
            
        # Microsoft Azure AD / OIDC
        if os.getenv("MICROSOFT_CLIENT_ID") and os.getenv("MICROSOFT_CLIENT_SECRET"):
            tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common")
            self.providers["microsoft"] = SSOConfig(
                provider=SSOProvider.MICROSOFT,
                client_id=os.getenv("MICROSOFT_CLIENT_ID"),
                client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
                discovery_url=f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid_configuration",
                scopes=["openid", "email", "profile"]
            )
            
        # Okta OIDC
        if os.getenv("OKTA_CLIENT_ID") and os.getenv("OKTA_CLIENT_SECRET"):
            okta_domain = os.getenv("OKTA_DOMAIN")
            if okta_domain:
                self.providers["okta"] = SSOConfig(
                    provider=SSOProvider.OKTA,
                    client_id=os.getenv("OKTA_CLIENT_ID"),
                    client_secret=os.getenv("OKTA_CLIENT_SECRET"),
                    discovery_url=f"https://{okta_domain}/.well-known/openid_configuration",
                    scopes=["openid", "email", "profile"]
                )
                
        # Auth0 OIDC
        if os.getenv("AUTH0_CLIENT_ID") and os.getenv("AUTH0_CLIENT_SECRET"):
            auth0_domain = os.getenv("AUTH0_DOMAIN")
            if auth0_domain:
                self.providers["auth0"] = SSOConfig(
                    provider=SSOProvider.AUTH0,
                    client_id=os.getenv("AUTH0_CLIENT_ID"),
                    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
                    discovery_url=f"https://{auth0_domain}/.well-known/openid_configuration",
                    scopes=["openid", "email", "profile"]
                )
                
        # Generic OIDC Provider
        if os.getenv("GENERIC_OIDC_CLIENT_ID") and os.getenv("GENERIC_OIDC_CLIENT_SECRET"):
            self.providers["generic_oidc"] = SSOConfig(
                provider=SSOProvider.GENERIC_OIDC,
                client_id=os.getenv("GENERIC_OIDC_CLIENT_ID"),
                client_secret=os.getenv("GENERIC_OIDC_CLIENT_SECRET"),
                discovery_url=os.getenv("GENERIC_OIDC_DISCOVERY_URL"),
                scopes=os.getenv("GENERIC_OIDC_SCOPES", "openid,email,profile").split(",")
            )
            
        logger.info(f"Initialized {len(self.providers)} SSO providers: {list(self.providers.keys())}")
        
    async def get_authorization_url(self, provider_name: str, redirect_uri: str, 
                                  state: str = None) -> str:
        """Generate authorization URL for SSO provider."""
        if provider_name not in self.providers:
            raise ValueError(f"Unknown SSO provider: {provider_name}")
            
        config = self.providers[provider_name]
        
        # Get OIDC discovery document
        discovery = await self._get_discovery_document(config)
        auth_url = discovery.get("authorization_endpoint")
        
        if not auth_url:
            raise ValueError(f"No authorization endpoint found for {provider_name}")
            
        params = {
            "client_id": config.client_id,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "redirect_uri": redirect_uri,
            "state": state or ""
        }
        
        # Add provider-specific parameters
        if config.provider == SSOProvider.MICROSOFT:
            params["response_mode"] = "query"
            params["prompt"] = "select_account"
            
        return f"{auth_url}?{urlencode(params)}"
        
    async def exchange_code_for_tokens(self, provider_name: str, code: str, 
                                     redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access and ID tokens."""
        if provider_name not in self.providers:
            raise ValueError(f"Unknown SSO provider: {provider_name}")
            
        config = self.providers[provider_name]
        discovery = await self._get_discovery_document(config)
        token_url = discovery.get("token_endpoint")
        
        if not token_url:
            raise ValueError(f"No token endpoint found for {provider_name}")
            
        token_data = {
            "grant_type": "authorization_code",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        try:
            response = await self.http_client.post(
                token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Token exchange failed for {provider_name}: {e}")
            raise ValueError(f"Token exchange failed: {e}")
            
    async def get_user_profile(self, provider_name: str, access_token: str, 
                             id_token: str = None) -> SSOUserProfile:
        """Get user profile from SSO provider."""
        if provider_name not in self.providers:
            raise ValueError(f"Unknown SSO provider: {provider_name}")
            
        config = self.providers[provider_name]
        
        # Try to get user info from ID token first
        if id_token:
            try:
                user_info = await self._decode_id_token(config, id_token)
                return self._map_user_profile(provider_name, user_info)
            except Exception as e:
                logger.warning(f"Failed to decode ID token, falling back to userinfo endpoint: {e}")
                
        # Fallback to userinfo endpoint
        discovery = await self._get_discovery_document(config)
        userinfo_url = discovery.get("userinfo_endpoint")
        
        if not userinfo_url:
            raise ValueError(f"No userinfo endpoint found for {provider_name}")
            
        try:
            response = await self.http_client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            user_info = response.json()
            
            return self._map_user_profile(provider_name, user_info)
            
        except httpx.HTTPError as e:
            logger.error(f"User info request failed for {provider_name}: {e}")
            raise ValueError(f"User info request failed: {e}")
            
    async def _get_discovery_document(self, config: SSOConfig) -> Dict[str, Any]:
        """Get and cache OIDC discovery document."""
        if config.discovery_url in self._discovery_cache:
            return self._discovery_cache[config.discovery_url]
            
        if not config.discovery_url:
            # Manual configuration
            return {
                "authorization_endpoint": config.authorization_url,
                "token_endpoint": config.token_url,
                "userinfo_endpoint": config.userinfo_url,
                "jwks_uri": config.jwks_url
            }
            
        try:
            response = await self.http_client.get(config.discovery_url)
            response.raise_for_status()
            discovery = response.json()
            
            # Cache for 1 hour
            self._discovery_cache[config.discovery_url] = discovery
            return discovery
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get discovery document from {config.discovery_url}: {e}")
            raise ValueError(f"Discovery document request failed: {e}")
            
    async def _decode_id_token(self, config: SSOConfig, id_token: str) -> Dict[str, Any]:
        """Decode and verify ID token."""
        # Get JWKS for token verification
        discovery = await self._get_discovery_document(config)
        jwks_uri = discovery.get("jwks_uri")
        
        if not jwks_uri:
            raise ValueError("No JWKS URI found for token verification")
            
        # Get JWKS
        if jwks_uri not in self._jwks_cache:
            response = await self.http_client.get(jwks_uri)
            response.raise_for_status()
            self._jwks_cache[jwks_uri] = response.json()
            
        jwks = self._jwks_cache[jwks_uri]
        
        # Decode token header to get key ID
        unverified_header = jwt.get_unverified_header(id_token)
        key_id = unverified_header.get("kid")
        
        # Find the correct key
        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == key_id:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break
                
        if not public_key:
            raise ValueError(f"Public key not found for key ID: {key_id}")
            
        # Verify and decode token
        try:
            payload = jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256"],
                audience=config.client_id,
                options={"verify_exp": True}
            )
            return payload
            
        except jwt.InvalidTokenError as e:
            logger.error(f"ID token verification failed: {e}")
            raise ValueError(f"ID token verification failed: {e}")
            
    def _map_user_profile(self, provider_name: str, user_info: Dict[str, Any]) -> SSOUserProfile:
        """Map provider-specific user info to standardized profile."""
        
        # Common OIDC claims mapping
        email = user_info.get("email", "")
        external_id = user_info.get("sub") or user_info.get("id", "")
        email_verified = user_info.get("email_verified", False)
        
        # Provider-specific mappings
        if provider_name == "google":
            return SSOUserProfile(
                provider=provider_name,
                external_id=external_id,
                email=email,
                first_name=user_info.get("given_name"),
                last_name=user_info.get("family_name"),
                display_name=user_info.get("name"),
                avatar_url=user_info.get("picture"),
                email_verified=email_verified
            )
            
        elif provider_name == "microsoft":
            return SSOUserProfile(
                provider=provider_name,
                external_id=external_id,
                email=email,
                first_name=user_info.get("given_name"),
                last_name=user_info.get("family_name"), 
                display_name=user_info.get("name"),
                avatar_url=None,  # Microsoft doesn't provide picture in userinfo
                email_verified=email_verified
            )
            
        elif provider_name in ["okta", "auth0"]:
            return SSOUserProfile(
                provider=provider_name,
                external_id=external_id,
                email=email,
                first_name=user_info.get("given_name"),
                last_name=user_info.get("family_name"),
                display_name=user_info.get("name") or user_info.get("nickname"),
                avatar_url=user_info.get("picture"),
                email_verified=email_verified
            )
            
        else:  # Generic OIDC
            return SSOUserProfile(
                provider=provider_name,
                external_id=external_id,
                email=email,
                first_name=user_info.get("given_name"),
                last_name=user_info.get("family_name"),
                display_name=user_info.get("name"),
                avatar_url=user_info.get("picture"),
                email_verified=email_verified
            )
            
    async def get_provider_list(self) -> List[Dict[str, Any]]:
        """Get list of available SSO providers."""
        return [
            {
                "name": provider_name,
                "display_name": provider_name.title(),
                "provider": config.provider.value
            }
            for provider_name, config in self.providers.items()
        ]
        
    async def health_check(self) -> Dict[str, Any]:
        """Check health of SSO provider connections."""
        health = {"status": "healthy", "providers": {}}
        
        for provider_name, config in self.providers.items():
            try:
                if config.discovery_url:
                    await self._get_discovery_document(config)
                    health["providers"][provider_name] = {"status": "healthy"}
                else:
                    health["providers"][provider_name] = {"status": "configured"}
                    
            except Exception as e:
                health["providers"][provider_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["status"] = "degraded"
                
        return health
        
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

# Global SSO provider manager instance
sso_manager = SSOProviderManager()