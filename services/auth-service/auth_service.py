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
from sqlalchemy import select
from sso_providers import sso_manager, SSOUserProfile
from two_factor_auth import get_twofa_manager
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
    
    def __init__(self, lifespan=None):
        self.app = FastAPI(
            title="PhotoShare Authentication Service",
            description="Centralized authentication with SSO, 2FA, and RBAC",
            version="2.4.0-auth",
            lifespan=lifespan
        )
        
        # Security middleware
        self.rate_limiter = RateLimiter()
        self.security_middleware = SecurityMiddleware()
        
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
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_minutes = int(os.getenv("JWT_EXPIRATION_MINUTES", "30"))
        self.jwt_audience = os.getenv("JWT_AUDIENCE", "photoshare-app")
        self.jwt_issuer = os.getenv("JWT_ISSUER", "photoshare-auth")
        
        # Initialize database 
        self._init_database_task = None
        
        # Setup routes
        self._setup_routes()
        
    async def initialize_database(self):
        """Initialize the database connection."""
        await auth_db_manager.initialize()
        await auth_db_manager.create_tables()
        
    def _setup_routes(self):
        """Setup API routes."""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            db_healthy = await auth_db_manager.health_check()
            sso_health = await sso_manager.health_check()
            twofa_health = await get_twofa_manager().health_check()
            
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
            client_ip = req.client.host if req and req.client else "unknown"
            is_limited = self.rate_limiter.is_rate_limited(client_ip, limit=5, window=900)  # 15 minutes = 900 seconds
            if is_limited:
                raise HTTPException(status_code=429, detail="Too many registration requests")
                
            # Password validation
            if len(request.password) < 8:
                raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
                
            async with auth_db_manager.session_factory() as session:
                # Check if user already exists
                from sqlalchemy import select
                result = await session.execute(select(User).where(User.email == request.email))
                existing_user = result.scalar_one_or_none()
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
                
        # Email Verification
        @self.app.get("/api/auth/verify-email/{secret}")
        async def verify_email(secret: str, req: Request):
            """Verify user email with secret token."""
            try:
                async with auth_db_manager.session_factory() as session:
                    from sqlalchemy import select
                    
                    # Find verification record
                    verification_query = select(EmailVerification).where(
                        EmailVerification.secret == secret,
                        EmailVerification.is_used == False,
                        EmailVerification.expires_at > datetime.now(timezone.utc)
                    )
                    result = await session.execute(verification_query)
                    verification = result.scalar_one_or_none()
                    
                    if not verification:
                        raise HTTPException(
                            status_code=404, 
                            detail="Invalid or expired verification link"
                        )
                    
                    # Get and verify user
                    user_query = select(User).where(User.id == verification.user_id)
                    user_result = await session.execute(user_query)
                    user = user_result.scalar_one_or_none()
                    
                    if not user:
                        raise HTTPException(status_code=404, detail="User not found")
                    
                    if user.is_verified:
                        return {"message": "Email already verified", "status": "already_verified"}
                    
                    # Mark user as verified
                    user.is_verified = True
                    
                    # Mark verification as used
                    verification.is_used = True
                    verification.verified_at = datetime.now(timezone.utc)
                    
                    await session.commit()
                    
                    # Log audit event
                    await self._log_audit_event(
                        session, user.id, "email_verification_success", "authentication",
                        {"email": user.email}, "success", req
                    )
                    
                    return {
                        "message": "Email verified successfully", 
                        "status": "verified",
                        "user_email": user.email
                    }
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Email verification error: {e}")
                raise HTTPException(
                    status_code=500, 
                    detail="Email verification failed"
                )
        
        # Request Email Verification (for resending)
        @self.app.post("/api/auth/request-verification")
        async def request_verification(request: dict, req: Request):
            """Request new email verification link."""
            try:
                email = request.get("email")
                if not email:
                    raise HTTPException(status_code=400, detail="Email required")
                    
                # Rate limiting for verification requests
                client_ip = req.client.host if req and req.client else "unknown"
                is_limited = self.rate_limiter.is_rate_limited(client_ip, limit=3, window=3600)  # 3 per hour
                if is_limited:
                    raise HTTPException(status_code=429, detail="Too many verification requests")
                
                async with auth_db_manager.session_factory() as session:
                    from sqlalchemy import select
                    
                    # Find user
                    user_query = select(User).where(User.email == email)
                    user_result = await session.execute(user_query)
                    user = user_result.scalar_one_or_none()
                    
                    if not user:
                        # Return success even if user doesn't exist (security)
                        return {"message": "If the email exists, a verification link has been sent"}
                    
                    if user.is_verified:
                        return {"message": "Email is already verified"}
                    
                    # Deactivate old verification tokens
                    from sqlalchemy import update
                    await session.execute(
                        update(EmailVerification)
                        .where(EmailVerification.user_id == user.id)
                        .values(is_used=True)
                    )
                    
                    # Create new verification
                    await self._create_email_verification(session, user)
                    
                    return {"message": "If the email exists, a verification link has been sent"}
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Verification request error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to process verification request"
                )
                
        # User Login
        @self.app.post("/api/auth/login", response_model=AuthResponse)
        async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), req: Request = None):
            # Rate limiting
            client_ip = req.client.host if req and req.client else "unknown"
            is_limited = self.rate_limiter.is_rate_limited(client_ip, limit=10, window=900)  # 15 minutes = 900 seconds
            if is_limited:
                raise HTTPException(status_code=429, detail="Too many login attempts")
                
            async with auth_db_manager.session_factory() as session:
                # Find user
                result = await session.execute(select(User).filter(User.email == form_data.username))
                user = result.scalar_one_or_none()
                
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
                requires_2fa = await get_twofa_manager().is_2fa_enabled_for_user(str(user.id))
                
                if requires_2fa:
                    # Create 2FA challenge
                    challenge = await get_twofa_manager().create_2fa_challenge(str(user.id))
                    
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
                
                async with auth_db_manager.session_factory() as session:
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
            is_valid = await get_twofa_manager().verify_2fa_challenge(
                "user_id",  # Would get from challenge_id lookup
                request.challenge_id,
                request.method,
                request.code
            )
            
            if not is_valid:
                raise HTTPException(status_code=401, detail="Invalid 2FA code")
                
            # Complete login process
            async with auth_db_manager.session_factory() as session:
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
            
            async with auth_db_manager.session_factory() as session:
                # Find and invalidate session
                result = await session.execute(select(Session).filter(Session.jwt_token == token))
                user_session = result.scalar_one_or_none()
                
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
        
        # Service-to-service endpoints for app service integration
        @self.app.get("/api/auth/users/{user_uuid}")
        async def get_user_info(user_uuid: str):
            """Get user information by UUID (service-to-service)."""
            from sqlalchemy import select
            
            async with auth_db_manager.session_factory() as session:
                # Find user by UUID
                user_query = select(User).where(User.uuid == user_uuid)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")
                
                # Get user roles and permissions
                roles, permissions = await self._get_user_roles_and_permissions(user.id)
                
                return {
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "display_name": user.display_name,
                    "is_verified": user.is_verified,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat(),
                    "roles": roles,
                    "permissions": permissions
                }
        
        @self.app.get("/api/auth/users/{user_uuid}/permissions")
        async def get_user_permissions(user_uuid: str):
            """Get user permissions by UUID (service-to-service)."""
            from sqlalchemy import select
            
            async with auth_db_manager.session_factory() as session:
                # Find user by UUID
                user_query = select(User).where(User.uuid == user_uuid)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")
                
                # Get user permissions
                roles, permissions = await self._get_user_roles_and_permissions(user.id)
                
                return {
                    "permissions": permissions,
                    "roles": roles
                }
            
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
        from sqlalchemy import select
        
        # Find 'user' role
        role_query = select(Role).where(Role.name == "user")
        role_result = await session.execute(role_query)
        user_role = role_result.scalar_one_or_none()
        
        if not user_role:
            error_msg = "Critical Error: Default 'user' role not found. The RBAC system is not properly initialized. New users cannot be assigned permissions."
            logger.error(error_msg)
            logger.error("Solution: The RBAC system should auto-initialize on startup. If this error persists, manually run: python setup_rbac.py")
            raise Exception(error_msg)
            
        # Check if user already has this role
        existing_query = select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == user_role.id,
            UserRole.is_active == True
        )
        existing_result = await session.execute(existing_query)
        existing = existing_result.scalar_one_or_none()
        
        if not existing:
            # Assign role to user
            user_role_assignment = UserRole(
                user_id=user.id,
                role_id=user_role.id,
                is_active=True
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
            "aud": self.jwt_audience,
            "iss": self.jwt_issuer,
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
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm],
                audience=self.jwt_audience,
                issuer=self.jwt_issuer
            )
            user_id = payload.get("user_id")
            
            async with auth_db_manager.session_factory() as session:
                user = await session.get(User, user_id)
                if not user or not user.is_active:
                    raise HTTPException(status_code=401, detail="Invalid token")
                    
                return user
                
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
            
    async def _get_user_roles_and_permissions(self, user_id: int) -> tuple[List[str], List[str]]:
        """Get user roles and permissions."""
        from sqlalchemy import select
        
        async with auth_db_manager.session_factory() as session:
            roles = []
            permissions = []
            
            # Get user roles
            user_roles_query = select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.is_active == True
            )
            user_roles_result = await session.execute(user_roles_query)
            user_roles = user_roles_result.scalars().all()
            
            for user_role in user_roles:
                # Get role details
                role = await session.get(Role, user_role.role_id)
                if role and role.is_active:
                    roles.append(role.name)
                    
                    # Get role permissions
                    role_perms_query = select(RolePermission).where(
                        RolePermission.role_id == role.id
                    )
                    role_perms_result = await session.execute(role_perms_query)
                    role_perms = role_perms_result.scalars().all()
                    
                    for role_perm in role_perms:
                        perm = await session.get(Permission, role_perm.permission_id)
                        if perm:
                            permissions.append(f"{perm.resource}:{perm.action}")
                            
            return roles, list(set(permissions))  # Remove duplicates
        
    async def _find_or_create_sso_user(self, session, profile: SSOUserProfile) -> User:
        """Find existing user or create new user from SSO profile."""
        # Look for existing SSO account
        result = await session.execute(select(SSOAccount).filter(
            SSOAccount.provider == profile.provider,
            SSOAccount.external_id == profile.external_id
        ))
        sso_account = result.scalar_one_or_none()
        
        if sso_account:
            return await session.get(User, sso_account.user_id)
            
        # Look for existing user by email
        result = await session.execute(select(User).filter(User.email == profile.email))
        user = result.scalar_one_or_none()
        
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
        await get_twofa_manager().close()
        logger.info("Authentication service stopped")

# Create service instance
auth_service = AuthenticationService()

# Create router for FastAPI inclusion
from fastapi import APIRouter
router = APIRouter()

# Add auth endpoints
@router.get("/status")
async def get_auth_status():
    """Get authentication service status."""
    return {
        "service": "authentication",
        "status": "running",
        "version": "2.3.0"
    }

@router.post("/register")
async def register_user(request: RegisterRequest):
    """Register a new user."""
    try:
        # Check if user already exists
        async with auth_db_manager.session_factory() as session:
            from sqlalchemy import select
            existing_user = await session.execute(
                select(User).where(User.email == request.email)
            )
            if existing_user.scalar_one_or_none():
                raise HTTPException(
                    status_code=400, 
                    detail="User with this email already exists"
                )
            
            # Create new user
            import bcrypt
            password_hash = bcrypt.hashpw(
                request.password.encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            
            new_user = User(
                email=request.email,
                first_name=request.first_name,
                last_name=request.last_name,
                password_hash=password_hash,
                is_active=True,
                is_verified=False  # Requires email verification
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            # Assign default user role
            await self._assign_default_role(session, new_user)
            
            return {
                "message": "User registered successfully",
                "user_id": str(new_user.id),
                "email": new_user.email,
                "requires_verification": True
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login") 
async def login_user(request: LoginRequest):
    """Login user and return JWT token."""
    try:
        async with auth_db_manager.session_factory() as session:
            from sqlalchemy import select
            user = await session.execute(
                select(User).where(User.email == request.email)
            )
            user = user.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password"
                )
            
            # Verify password
            import bcrypt
            if not bcrypt.checkpw(
                request.password.encode('utf-8'), 
                user.password_hash.encode('utf-8')
            ):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=401,
                    detail="Account is disabled"
                )
            
            # Generate JWT token
            import jwt
            from datetime import datetime, timedelta
            
            payload = {
                "sub": str(user.uuid),
                "user_id": str(user.id),
                "email": user.email,
                "aud": self.jwt_audience,
                "iss": self.jwt_issuer,
                "exp": datetime.utcnow() + timedelta(hours=24),
                "iat": datetime.utcnow(),
                "is_verified": user.is_verified
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            # Create session record
            import secrets
            session_token = secrets.token_urlsafe(32)
            session_record = Session(
                user_id=user.id,
                session_token=session_token,
                jwt_token=token,
                expires_at=datetime.utcnow() + timedelta(hours=24),
                is_active=True
            )
            session.add(session_record)
            await session.commit()
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": 86400,  # 24 hours
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "is_verified": user.is_verified,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )

# Global instance for backward compatibility (will be replaced with lifespan-managed instance)
auth_service_instance = None