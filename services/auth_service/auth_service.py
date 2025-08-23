#!/usr/bin/env python3
"""
Authentication Service
======================

Centralized authentication service with SSO, 2FA, and RBAC.
Completely separated from application logic.
"""

import os
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import logging

from auth_database import auth_db_manager, User, Session, SSOAccount, Role, Permission, UserRole, RolePermission, EmailVerification, AuditLog
from sso_providers import sso_manager, SSOUserProfile
from two_factor_auth import twofa_manager
from security import SecurityMiddleware, RateLimiter

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SSOLoginRequest(BaseModel):
    provider: str
    redirect_uri: str

class TwoFactorChallengeRequest(BaseModel):
    challenge_id: str
    method: str
    code: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: Dict[str, Any]
    requires_2fa: bool = False
    challenge_id: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    uuid: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    display_name: Optional[str]
    is_verified: bool
    is_active: bool
    created_at: str
    roles: List[str] = []
    permissions: List[str] = []

class AuthenticationService:
    """Centralized authentication service."""
    
    def __init__(self):
        self.app = FastAPI(
            title="PhotoShare Authentication Service",
            description="Centralized authentication with SSO, 2FA, and RBAC",
            version="2.4.0-auth"
        )
        
        # Security middleware
        self.rate_limiter = RateLimiter(requests_per_minute=120, burst_limit=30)
        self.security_middleware = SecurityMiddleware(
            rate_limiter=self.rate_limiter
        )
        
        # Add middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(","),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # JWT configuration
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "your-secret-key")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_minutes = 30
        
        # Setup routes
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup API routes."""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            db_healthy = await auth_db_manager.health_check()
            sso_health = await sso_manager.health_check()
            twofa_health = await twofa_manager.health_check()
            
            return {
                "status": "healthy" if db_healthy else "unhealthy",
                "service": "PhotoShare Authentication Service",
                "version": "2.4.0-auth",
                "database": "healthy" if db_healthy else "unhealthy",
                "sso": sso_health,
                "twofa": twofa_health
            }
            
        # User Registration
        @self.app.post("/api/auth/register", response_model=UserResponse)
        async def register_user(request: RegisterRequest, req: Request):
            # Rate limiting
            is_limited, rate_info = self.rate_limiter.is_rate_limited(req, max_requests=5, window_minutes=15)
            if is_limited:
                raise HTTPException(status_code=429, detail=rate_info)
                
            # Password validation
            if len(request.password) < 8:
                raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
                
            async with auth_db_manager.get_session() as session:
                # Check if user already exists
                existing_user = await session.get(User, {"email": request.email})
                if existing_user:
                    raise HTTPException(status_code=409, detail="User already exists")
                    
                # Hash password
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                password_hash = pwd_context.hash(request.password)
                
                # Create user
                user = User(
                    email=request.email,
                    password_hash=password_hash,
                    first_name=request.first_name,
                    last_name=request.last_name,
                    display_name=f"{request.first_name or ''} {request.last_name or ''}".strip() or None,
                    is_verified=False  # Requires email verification
                )
                
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                # Create email verification
                await self._create_email_verification(session, user)
                
                # Assign default role
                await self._assign_default_role(session, user)
                
                # Audit log
                await self._log_audit_event(
                    session, user.id, "user_registration", "authentication",
                    {"email": user.email}, "success", req
                )
                
                return UserResponse(
                    id=user.id,
                    uuid=str(user.uuid),
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    display_name=user.display_name,
                    is_verified=user.is_verified,
                    is_active=user.is_active,
                    created_at=user.created_at.isoformat(),
                    roles=["user"]  # Default role
                )
                
        # User Login
        @self.app.post("/api/auth/login", response_model=AuthResponse)
        async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), req: Request = None):
            # Rate limiting
            is_limited, rate_info = self.rate_limiter.is_rate_limited(req, max_requests=10, window_minutes=15)
            if is_limited:
                raise HTTPException(status_code=429, detail=rate_info)
                
            async with auth_db_manager.get_session() as session:
                # Find user
                user = await session.query(User).filter(User.email == form_data.username).first()
                
                if not user or user.is_locked:
                    await self._log_failed_login(session, form_data.username, req)
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                    
                # Verify password
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                
                if not pwd_context.verify(form_data.password, user.password_hash):
                    await self._log_failed_login(session, form_data.username, req)
                    user.failed_login_attempts += 1
                    user.last_login_attempt = datetime.now(timezone.utc)
                    
                    # Lock account after 5 failed attempts
                    if user.failed_login_attempts >= 5:
                        user.is_locked = True
                        await self._log_audit_event(
                            session, user.id, "account_locked", "security",
                            {"reason": "too_many_failed_attempts"}, "success", req
                        )
                        
                    await session.commit()
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                    
                # Reset failed attempts on successful login
                user.failed_login_attempts = 0
                user.last_login = datetime.now(timezone.utc)
                await session.commit()
                
                # Check if 2FA is enabled
                requires_2fa = await twofa_manager.is_2fa_enabled_for_user(str(user.id))
                
                if requires_2fa:
                    # Create 2FA challenge
                    challenge = await twofa_manager.create_2fa_challenge(str(user.id))
                    
                    await self._log_audit_event(
                        session, user.id, "2fa_challenge_created", "authentication",
                        {"challenge_id": challenge["challenge_id"]}, "success", req
                    )
                    
                    return AuthResponse(
                        access_token="",  # No token until 2FA complete
                        expires_in=0,
                        user=user.to_dict(),
                        requires_2fa=True,
                        challenge_id=challenge["challenge_id"]
                    )
                    
                # Create session and JWT
                session_token, jwt_token = await self._create_user_session(session, user, req)
                
                await self._log_audit_event(
                    session, user.id, "login_success", "authentication",
                    {"method": "password"}, "success", req
                )
                
                return AuthResponse(
                    access_token=jwt_token,
                    expires_in=self.jwt_expiration_minutes * 60,
                    user=user.to_dict(),
                    requires_2fa=False
                )
                
        # SSO Provider List
        @self.app.get("/api/auth/sso/providers")
        async def get_sso_providers():
            return await sso_manager.get_provider_list()
            
        # SSO Login Initiation
        @self.app.post("/api/auth/sso/login")
        async def sso_login_init(request: SSOLoginRequest, req: Request):
            try:
                state = secrets.token_urlsafe(16)
                auth_url = await sso_manager.get_authorization_url(
                    request.provider, request.redirect_uri, state
                )
                
                return {
                    "authorization_url": auth_url,
                    "state": state
                }
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
                
        # SSO Callback
        @self.app.get("/api/auth/sso/callback/{provider}")
        async def sso_callback(provider: str, code: str, state: str, req: Request):
            try:
                # Exchange code for tokens
                tokens = await sso_manager.exchange_code_for_tokens(
                    provider, code, req.url.replace(query="")  # Remove query params
                )
                
                # Get user profile
                user_profile = await sso_manager.get_user_profile(
                    provider, tokens["access_token"], tokens.get("id_token")
                )
                
                async with auth_db_manager.get_session() as session:
                    # Find or create user
                    user = await self._find_or_create_sso_user(session, user_profile)
                    
                    # Create session
                    session_token, jwt_token = await self._create_user_session(session, user, req)
                    
                    await self._log_audit_event(
                        session, user.id, "sso_login_success", "authentication",
                        {"provider": provider, "external_id": user_profile.external_id}, "success", req
                    )
                    
                    return AuthResponse(
                        access_token=jwt_token,
                        expires_in=self.jwt_expiration_minutes * 60,
                        user=user.to_dict(),
                        requires_2fa=False
                    )
                    
            except Exception as e:
                logger.error(f"SSO callback error: {e}")
                raise HTTPException(status_code=400, detail="SSO authentication failed")
                
        # 2FA Challenge Verification
        @self.app.post("/api/auth/2fa/verify", response_model=AuthResponse)
        async def verify_2fa_challenge(request: TwoFactorChallengeRequest, req: Request):
            # Verify 2FA challenge
            is_valid = await twofa_manager.verify_2fa_challenge(
                "user_id",  # Would get from challenge_id lookup
                request.challenge_id,
                request.method,
                request.code
            )
            
            if not is_valid:
                raise HTTPException(status_code=401, detail="Invalid 2FA code")
                
            # Complete login process
            async with auth_db_manager.get_session() as session:
                # Get user from challenge (simplified for demo)
                user = await session.get(User, 1)  # Would lookup by challenge_id
                
                # Create session
                session_token, jwt_token = await self._create_user_session(session, user, req)
                
                await self._log_audit_event(
                    session, user.id, "2fa_verification_success", "authentication",
                    {"method": request.method, "challenge_id": request.challenge_id}, "success", req
                )
                
                return AuthResponse(
                    access_token=jwt_token,
                    expires_in=self.jwt_expiration_minutes * 60,
                    user=user.to_dict(),
                    requires_2fa=False
                )
                
        # Logout
        @self.app.post("/api/auth/logout")
        async def logout_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()), req: Request = None):
            token = credentials.credentials
            
            async with auth_db_manager.get_session() as session:
                # Find and invalidate session
                user_session = await session.query(Session).filter(Session.jwt_token == token).first()
                
                if user_session:
                    user_session.is_active = False
                    user_session.logout_at = datetime.now(timezone.utc)
                    user_session.logout_reason = "manual"
                    await session.commit()
                    
                    await self._log_audit_event(
                        session, user_session.user_id, "logout", "authentication",
                        {"session_id": user_session.session_token}, "success", req
                    )
                    
            return {"message": "Logged out successfully"}
            
        # User Profile
        @self.app.get("/api/auth/me", response_model=UserResponse)
        async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
            user = await self._get_user_from_token(credentials.credentials)
            
            # Get user roles and permissions
            roles, permissions = await self._get_user_roles_and_permissions(user.id)
            
            return UserResponse(
                id=user.id,
                uuid=str(user.uuid),
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                display_name=user.display_name,
                is_verified=user.is_verified,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                roles=roles,
                permissions=permissions
            )
            
    async def _create_email_verification(self, session, user: User):
        """Create email verification record."""
        secret = secrets.token_urlsafe(32)
        verification = EmailVerification(
            email=user.email,
            secret=secret,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        
        session.add(verification)
        await session.commit()
        
        # In production, send email here
        logger.info(f"📧 Email verification link: /api/auth/verify-email/{secret}")
        
    async def _assign_default_role(self, session, user: User):
        """Assign default user role."""
        # Find or create 'user' role
        user_role = await session.query(Role).filter(Role.name == "user").first()
        
        if not user_role:
            user_role = Role(
                name="user",
                description="Standard user role",
                level=0,
                is_system_role=True
            )
            session.add(user_role)
            await session.commit()
            
        # Assign role to user
        user_role_assignment = UserRole(
            user_id=user.id,
            role_id=user_role.id
        )
        
        session.add(user_role_assignment)
        await session.commit()
        
    async def _create_user_session(self, session, user: User, req: Request) -> tuple[str, str]:
        """Create user session and JWT token."""
        import jwt
        
        # Create session record
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.jwt_expiration_minutes)
        
        # JWT payload
        jwt_payload = {
            "sub": str(user.uuid),
            "user_id": user.id,
            "email": user.email,
            "iat": datetime.now(timezone.utc),
            "exp": expires_at
        }
        
        jwt_token = jwt.encode(jwt_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Store session
        user_session = Session(
            user_id=user.id,
            session_token=session_token,
            jwt_token=jwt_token,
            expires_at=expires_at,
            ip_address=req.client.host if req.client else None,
            user_agent_hash=hashlib.md5(req.headers.get("user-agent", "").encode()).hexdigest()
        )
        
        session.add(user_session)
        await session.commit()
        
        return session_token, jwt_token
        
    async def _get_user_from_token(self, token: str) -> User:
        """Get user from JWT token."""
        import jwt
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            user_id = payload.get("user_id")
            
            async with auth_db_manager.get_session() as session:
                user = await session.get(User, user_id)
                if not user or not user.is_active:
                    raise HTTPException(status_code=401, detail="Invalid token")
                    
                return user
                
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
            
    async def _get_user_roles_and_permissions(self, user_id: int) -> tuple[List[str], List[str]]:
        """Get user roles and permissions."""
        async with auth_db_manager.get_session() as session:
            # Get user roles
            user_roles = await session.query(UserRole).filter(
                UserRole.user_id == user_id,
                UserRole.is_active
            ).all()
            
            roles = []
            permissions = []
            
            for user_role in user_roles:
                role = await session.get(Role, user_role.role_id)
                if role and role.is_active:
                    roles.append(role.name)
                    
                    # Get role permissions
                    role_perms = await session.query(RolePermission).filter(
                        RolePermission.role_id == role.id
                    ).all()
                    
                    for role_perm in role_perms:
                        perm = await session.get(Permission, role_perm.permission_id)
                        if perm:
                            permissions.append(f"{perm.resource}:{perm.action}")
                            
        return roles, list(set(permissions))  # Remove duplicates
        
    async def _find_or_create_sso_user(self, session, profile: SSOUserProfile) -> User:
        """Find existing user or create new user from SSO profile."""
        # Look for existing SSO account
        sso_account = await session.query(SSOAccount).filter(
            SSOAccount.provider == profile.provider,
            SSOAccount.external_id == profile.external_id
        ).first()
        
        if sso_account:
            return await session.get(User, sso_account.user_id)
            
        # Look for existing user by email
        user = await session.query(User).filter(User.email == profile.email).first()
        
        if not user:
            # Create new user
            user = User(
                email=profile.email,
                first_name=profile.first_name,
                last_name=profile.last_name,
                display_name=profile.display_name,
                avatar_url=profile.avatar_url,
                is_verified=profile.email_verified,
                password_hash=None  # SSO-only user
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Assign default role
            await self._assign_default_role(session, user)
            
        # Create SSO account linkage
        sso_account = SSOAccount(
            user_id=user.id,
            provider=profile.provider,
            external_id=profile.external_id,
            email=profile.email,
            profile_data=profile.to_dict(),
            is_email_verified=profile.email_verified
        )
        
        session.add(sso_account)
        await session.commit()
        
        return user
        
    async def _log_audit_event(self, session, user_id: Optional[int], event_type: str,
                             category: str, event_data: Dict[str, Any], result: str, req: Request):
        """Log security audit event."""
        audit_log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            event_category=category,
            event_data=event_data,
            result=result,
            ip_address=req.client.host if req.client else None,
            user_agent=req.headers.get("user-agent", "")[:500]
        )
        
        session.add(audit_log)
        await session.commit()
        
    async def _log_failed_login(self, session, email: str, req: Request):
        """Log failed login attempt."""
        await self._log_audit_event(
            session, None, "login_failed", "authentication",
            {"email": email}, "failure", req
        )
        
    async def startup(self):
        """Initialize the authentication service."""
        await auth_db_manager.initialize()
        await auth_db_manager.create_tables()
        await sso_manager.initialize()
        logger.info("Authentication service started successfully")
        
    async def shutdown(self):
        """Cleanup on shutdown."""
        await auth_db_manager.close()
        await sso_manager.close()
        await twofa_manager.close()
        logger.info("Authentication service stopped")

# Create service instance
auth_service = AuthenticationService()