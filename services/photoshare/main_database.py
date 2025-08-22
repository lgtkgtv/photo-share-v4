#!/usr/bin/env python3
"""
Photo Share Service - Database Integrated Version
=================================================

Enhanced version with real PostgreSQL database integration, JWT authentication,
and comprehensive error handling.
"""

import asyncio
import logging
import time
import hashlib
import secrets
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt

# Import our database components
from database import (
    db_manager, get_db, User, Photo, Session, EmailVerification,
    Role, Permission, RolePermission, UserRole,
    UserRepository, PhotoRepository, SessionRepository, EmailVerificationRepository,
    RoleRepository, PermissionRepository, RolePermissionRepository, UserRoleRepository
)
from models_enhanced import PhotoMetadata, PhotoTag, PhotoLike, PhotoComment, UserFollow, Album, AlbumPhoto, UserProfile, Notification, PhotoShare
from image_processing import ImageProcessor
from sqlalchemy.ext.asyncio import AsyncSession
from file_storage import FileStorageService
from service_discovery import ServiceDiscovery
from error_handling import (
    error_handler, performance_monitor,
    http_exception_handler, starlette_exception_handler,
    validation_exception_handler, general_exception_handler,
    DatabaseErrorHandler, AuthenticationErrorHandler, FileStorageErrorHandler
)
from security import (
    SecurityMiddleware, rate_limiter, input_validator, security_audit, request_validator,
    require_rate_limit, validate_file_security, JWTSecurity, SessionManager
)
from encryption import (
    get_encryption_manager, get_data_protection, get_key_manager,
    EncryptionManager, DataProtectionService, SecurityKeyManager
)
from tls_security import (
    get_tls_validator, get_tls_config_manager, validate_application_tls
)
from performance_simple import (
    performance_optimizer, cache_result, monitor_query, optimized_db_ops
)
from monitoring import (
    monitoring_dashboard, record_request_metric, record_database_metric,
    record_cache_metric, record_error_metric, record_auth_metric
)
from logging_middleware import (
    CorrelationIDMiddleware, RequestResponseLoggingMiddleware, 
    get_structured_logger, get_correlation_id, LoggingConfig
)

# Configure structured logging
LoggingConfig.setup_structured_logging()
logger = get_structured_logger(__name__)

# Security setup  
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # Keep for backward compatibility
security = HTTPBearer()

# Enhanced encryption for new password hashing
def hash_password_enhanced(password: str) -> str:
    """Hash password using enhanced bcrypt with secure settings."""
    from encryption import get_encryption_manager
    encryption_manager = get_encryption_manager()
    return encryption_manager.hash_password_secure(password)

def verify_password_enhanced(password: str, hashed: str) -> bool:
    """Verify password using enhanced verification."""
    from encryption import get_encryption_manager
    encryption_manager = get_encryption_manager()
    
    # Try new enhanced verification first
    if encryption_manager.verify_password_secure(password, hashed):
        return True
    
    # Fallback to old method for backward compatibility
    return pwd_context.verify(password, hashed)

# JWT Configuration with enhanced security validation
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable must be set for security")

# Validate JWT secret strength
if len(SECRET_KEY) < 32:
    raise ValueError("JWT_SECRET_KEY must be at least 32 characters for security")

# Check for common weak secrets
weak_secrets = [
    "your-very-secure", "generate_with_script", "change_this", 
    "secret-key", "test-secret", "dev-secret"
]
if any(weak in SECRET_KEY.lower() for weak in weak_secrets):
    raise ValueError("JWT_SECRET_KEY appears to be a template value. Generate a secure secret!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

# Additional security configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))

# Security warnings for production
if ENVIRONMENT == "production":
    if ACCESS_TOKEN_EXPIRE_MINUTES > 60:
        logger.warning("Long JWT expiration time in production (>60 min)")
    if MAX_FILE_SIZE_MB > 100:
        logger.warning("Large file upload limit in production (>100MB)")
    
    # Ensure HTTPS in production (if behind proxy)
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
    if "http://" in allowed_origins and "localhost" not in allowed_origins:
        logger.warning("HTTP origins detected in production - ensure HTTPS is used!")

# Pydantic models for API
class UserRegistration(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: EmailStr  # Using email as username
    password: str

class PhotoUpload(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = False

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: str
    is_verified: bool
    is_active: bool

class PhotoResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    title: Optional[str]
    description: Optional[str]
    is_public: bool
    created_at: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email: str

class EmailVerificationRequest(BaseModel):
    email: str

class EmailVerificationResponse(BaseModel):
    message: str
    verification_link: Optional[str] = None  # For testing purposes

class AlbumCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False

class AlbumUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    cover_photo_id: Optional[int] = None

class AlbumResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_public: bool
    photos_count: int
    cover_photo_id: Optional[int]
    created_at: str
    updated_at: str

class UserProfileCreate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    is_private: bool = False
    allow_comments: bool = True
    allow_tags: bool = True
    show_location: bool = False

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    avatar_photo_id: Optional[int] = None
    is_private: Optional[bool] = None
    allow_comments: Optional[bool] = None
    allow_tags: Optional[bool] = None
    show_location: Optional[bool] = None

class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    display_name: Optional[str]
    bio: Optional[str]
    location: Optional[str]
    website: Optional[str]
    avatar_photo_id: Optional[int]
    followers_count: int
    following_count: int
    photos_count: int
    likes_received_count: int
    is_private: bool
    allow_comments: bool
    allow_tags: bool
    show_location: bool
    created_at: str
    updated_at: str

class NotificationResponse(BaseModel):
    id: int
    type: str
    from_user_id: Optional[int]
    photo_id: Optional[int]
    album_id: Optional[int]
    comment_id: Optional[int]
    title: str
    message: Optional[str]
    is_read: bool
    created_at: str

class PhotoShareCreate(BaseModel):
    expires_hours: Optional[int] = None  # None means no expiration
    max_views: Optional[int] = None
    allow_download: bool = True
    allow_comments: bool = True
    password: Optional[str] = None

class PhotoShareResponse(BaseModel):
    id: int
    photo_id: int
    share_token: str
    share_url: str
    expires_at: Optional[str]
    max_views: Optional[int]
    current_views: int
    allow_download: bool
    allow_comments: bool
    password_protected: bool
    is_active: bool
    created_at: str
    last_accessed: Optional[str]

class PhotoShareDatabaseService:
    """
    Photo sharing service with real database integration.
    
    This service provides full database integration with PostgreSQL,
    JWT authentication, and comprehensive error handling.
    """
    
    def __init__(self):
        self.service_name = "photo-share-database"
        self.version = "2.3.0-monitoring"
        self.start_time = datetime.now(timezone.utc)
        
        # Service statistics
        self.request_count = 0
        self.error_count = 0
        
        # Initialize file storage service
        self.file_storage = FileStorageService()
        
        # Initialize service discovery
        self.service_discovery = ServiceDiscovery()
        
        # Initialize security components
        self.jwt_security = JWTSecurity(SECRET_KEY)
        self.session_manager = SessionManager(self.jwt_security)
        
        # Initialize encryption components
        self.encryption_manager = get_encryption_manager()
        self.data_protection = get_data_protection()
        self.key_manager = get_key_manager()
        
        # Initialize TLS security components
        self.tls_validator = get_tls_validator()
        self.tls_config_manager = get_tls_config_manager()
        
        # Initialize performance optimization
        self.performance_optimizer = performance_optimizer
        
        # Initialize image processing
        self.image_processor = ImageProcessor()
        
        # Initialize logging middleware
        self.request_logging_middleware = RequestResponseLoggingMiddleware(
            app=None,  # Will be set when middleware is added
            log_level="INFO",
            max_body_size=10000,
            log_request_body=True,
            log_response_body=False  # Reduce log volume
        )
        
        # FastAPI app setup
        self.app = FastAPI(
            title="Photo Share Database Service",
            description="Photo sharing application with PostgreSQL integration",
            version=self.version,
            docs_url="/docs",
            redoc_url="/redoc"
        )
        self._setup_routes()
        self._setup_middleware()
        self._setup_error_handlers()
    
    def _setup_middleware(self):
        """Setup FastAPI middleware in correct order."""
        # Order is important: later middleware wraps earlier middleware
        
        # 1. CORS middleware first (outermost)
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
        )
        
        # 2. Request/Response logging middleware
        self.app.add_middleware(
            RequestResponseLoggingMiddleware,
            log_level="INFO",
            max_body_size=10000,
            log_request_body=True,
            log_response_body=False,
            skip_paths=['/health', '/metrics', '/docs', '/redoc']
        )
        
        # 3. Correlation ID middleware
        self.app.add_middleware(CorrelationIDMiddleware)
        
        # 4. Security middleware (innermost, closest to endpoints)
        self.app.add_middleware(SecurityMiddleware, rate_limiter=rate_limiter, request_validator=request_validator)
    
    def _setup_error_handlers(self):
        """Setup comprehensive error handling."""
        from fastapi import HTTPException
        from fastapi.exceptions import RequestValidationError
        from starlette.exceptions import HTTPException as StarletteHTTPException
        
        # Register exception handlers
        self.app.add_exception_handler(HTTPException, http_exception_handler)
        self.app.add_exception_handler(StarletteHTTPException, starlette_exception_handler)
        self.app.add_exception_handler(RequestValidationError, validation_exception_handler)
        self.app.add_exception_handler(Exception, general_exception_handler)
    
    def _get_uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using enhanced bcrypt with secure settings."""
        return self.encryption_manager.hash_password_secure(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash with enhanced security."""
        return verify_password_enhanced(plain_password, hashed_password)
    
    def _create_access_token(self, user_id: int, email: str, session_id: str = None) -> str:
        """Create JWT access token with enhanced security."""
        now = datetime.utcnow()
        
        # Generate unique token ID for revocation capability
        token_id = str(uuid.uuid4())
        
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "jti": token_id,  # JWT ID for token revocation
            "iss": "photoshare-service",  # Issuer
            "aud": "photoshare-users",  # Audience
            "type": "access_token",
            "session_id": session_id or str(uuid.uuid4())
        }
        
        # Create token
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        # Store token metadata for revocation tracking
        self.jwt_security.track_token(token_id, user_id, now)
        
        return token
    
    async def _get_current_user(self, request: Request = None,
                               credentials: HTTPAuthorizationCredentials = Depends(security),
                               db: AsyncSession = Depends(get_db)) -> User:
        """Get current user from JWT token with enhanced security validation."""
        try:
            # Validate token format
            if not credentials.credentials or len(credentials.credentials) < 50:
                raise HTTPException(status_code=401, detail="Invalid token format")
            
            # Check if token is revoked
            if self.jwt_security.is_token_revoked(credentials.credentials):
                raise HTTPException(status_code=401, detail="Token has been revoked")
            
            # Decode and validate JWT
            payload = jwt.decode(
                credentials.credentials, 
                SECRET_KEY, 
                algorithms=[ALGORITHM],
                options={"verify_exp": True, "verify_iat": True, "verify_sub": True}
            )
            
            user_id: int = int(payload.get("sub"))
            email: str = payload.get("email")
            issued_at = payload.get("iat")
            
            if not user_id or not email or not issued_at:
                raise HTTPException(status_code=401, detail="Invalid token payload")
            
            # Validate token age (additional security check)
            current_time = datetime.utcnow().timestamp()
            if current_time - issued_at > (ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 300):  # 5 min grace period
                raise HTTPException(status_code=401, detail="Token expired")
                
            user_repo = UserRepository(db)
            user = await user_repo.get_user_by_id(user_id)
            
            if user is None:
                raise HTTPException(status_code=401, detail="User not found")
            
            # Validate user is still active and verified
            if not user.is_active:
                raise HTTPException(status_code=401, detail="User account disabled")
            
            if not user.is_verified:
                raise HTTPException(status_code=401, detail="Email verification required")
            
            # Check if email matches token
            if user.email != email:
                raise HTTPException(status_code=401, detail="Token user mismatch")
            
            # Enhanced session security validation
            if request:
                session_id = payload.get("jti")
                client_ip = request.client.host if hasattr(request, 'client') else "unknown"
                
                if session_id:
                    # Validate session security
                    session_validation = self.session_manager.validate_session(session_id, request, client_ip)
                    
                    if not session_validation["is_valid"]:
                        # Log security threat
                        security_audit.log_security_event(
                            "SESSION_SECURITY_VIOLATION",
                            {
                                "user_id": user.id,
                                "session_id": session_id[:8] + "...",
                                "threats": session_validation["threats_detected"],
                                "risk_score": session_validation["risk_score"]
                            },
                            "critical",
                            client_ip
                        )
                        
                        # Revoke session for security
                        self.session_manager.revoke_session(session_id)
                        raise HTTPException(status_code=401, detail="Session security violation detected")
                    
                    # Update token usage
                    self.jwt_security.update_token_usage(session_id)
                    
                    # Log warnings if detected
                    if session_validation["warnings"]:
                        logger.warning(f"Session warnings for user {user.id}: {session_validation['warnings']}")
                
            return user
            
        except JWTError as e:
            # Log security event
            self.security_audit.log_security_event(
                "authentication_failure",
                {"error": str(e), "token_preview": credentials.credentials[:20] + "..."},
                "warning"
            )
            raise HTTPException(status_code=401, detail="Invalid token")
        except ValueError as e:
            raise HTTPException(status_code=401, detail="Invalid token data")
    
    async def _check_permission(self, user: User, resource: str, action: str, db: AsyncSession) -> bool:
        """Check if user has specific permission."""
        try:
            user_role_repo = UserRoleRepository(db)
            return await user_role_repo.has_permission(user.id, resource, action)
        except Exception as e:
            logger.error(f"Permission check error: {e}")
            return False
    
    async def _require_permission(self, resource: str, action: str):
        """Decorator to require specific permission for endpoint access."""
        async def permission_dependency(
            current_user: User = Depends(lambda self: self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            if not await self._check_permission(current_user, resource, action, db):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Insufficient permissions: {resource}:{action} required"
                )
            return current_user
        return permission_dependency
    
    async def _get_user_with_permission(self, resource: str, action: str, 
                                       credentials: HTTPAuthorizationCredentials = Depends(security),
                                       db: AsyncSession = Depends(get_db)) -> User:
        """Get current user and check permissions in one step."""
        user = await self._get_current_user(credentials, db)
        if not await self._check_permission(user, resource, action, db):
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient permissions: {resource}:{action} required"
            )
        return user
    
    def _setup_routes(self):
        """Setup FastAPI routes with database integration."""
        
        @self.app.get("/health")
        async def health_check():
            """Basic health check - minimal information disclosure."""
            # Check database connectivity
            db_healthy = await db_manager.health_check()
            
            # Basic storage check (don't reveal paths)
            storage_status = await self.file_storage.health_check()
            storage_healthy = storage_status.get("local_storage", False)
            
            overall_status = "healthy" if db_healthy and storage_healthy else "degraded"
            
            return {
                "status": overall_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/health/detailed")
        async def detailed_health_check(current_user: User = Depends(self._get_current_user)):
            """Detailed health check - requires authentication."""
            uptime = self._get_uptime()
            
            # Check database connectivity
            db_healthy = await db_manager.health_check()
            
            # Check storage service
            storage_status = await self.file_storage.health_check()
            storage_healthy = storage_status.get("local_storage", False) and storage_status.get("platform_storage", False)
            
            overall_status = "healthy" if db_healthy and storage_healthy else "degraded"
            
            return {
                "service": self.service_name,
                "status": overall_status,
                "version": self.version,
                "uptime_seconds": int(uptime),
                "database": "connected" if db_healthy else "disconnected",
                "storage": {
                    "local_storage": storage_status.get("local_storage", False),
                    "platform_storage": storage_status.get("platform_storage", False)
                },
                "request_count": self.request_count,
                "error_count": self.error_count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "message": "Photo Share Database Service",
                "version": self.version,
                "status": "operational",
                "docs": "/docs",
                "api": "/api/",
                "features": [
                    "postgresql_integration",
                    "jwt_authentication",
                    "password_security",
                    "real_database_storage"
                ]
            }
        
        @self.app.get("/api/")
        async def api_root():
            """API root endpoint."""
            self.request_count += 1
            return {
                "message": "Photo Share API - Database Version",
                "version": self.version,
                "endpoints": {
                    "health": "/health",
                    "docs": "/docs",
                    "users": "/api/users/",
                    "photos": "/api/photos/",
                    "tags": "/api/tags/",
                    "search": "/api/photos/search",
                    "albums": "/api/albums/",
                    "profiles": "/api/profiles/",
                    "notifications": "/api/notifications/",
                    "sharing": "/api/photos/{id}/share",
                    "platform": "/api/platform/",
                    "logging": "/api/platform/logging"
                },
                "status": "all_endpoints_functional",
                "database": "postgresql_integrated"
            }
        
        # =======================
        # USER MANAGEMENT ENDPOINTS
        # =======================
        
        @self.app.post("/api/users/register", response_model=UserResponse)
        async def register(user_data: UserRegistration, request: Request, 
                          db: AsyncSession = Depends(get_db)):
            """Register new user with database storage."""
            self.request_count += 1
            
            try:
                # Enhanced security validation
                if not input_validator.validate_email(user_data.email):
                    security_audit.log_security_event(
                        "INVALID_EMAIL_REGISTRATION",
                        {"email": user_data.email},
                        "warning",
                        request.client.host if request.client else None
                    )
                    raise HTTPException(status_code=400, detail="Invalid email format")
                
                # Password strength validation
                is_strong, password_issues = input_validator.validate_password(user_data.password)
                if not is_strong:
                    security_audit.log_security_event(
                        "WEAK_PASSWORD_ATTEMPT",
                        {"issues": password_issues},
                        "info",
                        request.client.host if request.client else None
                    )
                    raise HTTPException(status_code=400, detail=f"Password requirements not met: {'; '.join(password_issues)}")
                
                user_repo = UserRepository(db)
                
                # Check if user already exists
                existing_user = await user_repo.get_user_by_email(user_data.email)
                if existing_user:
                    raise HTTPException(status_code=409, detail="User already exists")
                
                # Hash password and create user
                password_hash = self._hash_password(user_data.password)
                user = await user_repo.create_user(user_data.email, password_hash)
                
                logger.info("User registered successfully", 
                          user_email=user_data.email, 
                          user_id=user.id,
                          event="user_registration")
                
                return UserResponse(
                    id=user.id,
                    email=user.email,
                    created_at=user.created_at.isoformat(),
                    is_verified=user.is_verified,
                    is_active=user.is_active
                )
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Registration failed: {e}")
                raise HTTPException(status_code=500, detail="Registration failed")
        
        @self.app.post("/api/users/login", response_model=Token)
        async def login(request: Request, 
                       db: AsyncSession = Depends(get_db),
                       username: str = Form(...),
                       password: str = Form(...)):
            """Login user with database authentication."""
            self.request_count += 1
            
            try:
                user_repo = UserRepository(db)
                
                # Get client IP address
                client_ip = request.client.host
                
                # Get user by email
                user = await user_repo.get_user_by_email(username)
                
                # Check account lockout before attempting authentication
                if user and self.session_manager.is_account_locked(user.id):
                    self.error_count += 1
                    raise HTTPException(status_code=423, detail="Account temporarily locked due to excessive failed login attempts")
                
                if not user or not self._verify_password(password, user.password_hash):
                    # Track failed attempt if user exists
                    if user:
                        session_id = str(uuid.uuid4())
                        self.session_manager.track_failed_attempt(session_id, user.id)
                    
                    self.error_count += 1
                    security_audit.log_security_event(
                        "LOGIN_FAILURE", 
                        {"username": username, "ip": client_ip},
                        "warning",
                        client_ip
                    )
                    raise AuthenticationErrorHandler.handle_invalid_credentials()
                
                if not user.is_active:
                    raise HTTPException(status_code=401, detail="Account deactivated")
                
                # Check for concurrent session anomalies
                session_anomaly = self.session_manager.detect_concurrent_session_anomaly(user.id)
                if session_anomaly["risk_level"] == "high":
                    logger.warning(f"High risk session anomaly detected for user {user.id}")
                    security_audit.log_security_event(
                        "SESSION_ANOMALY",
                        {"user_id": user.id, "anomaly": session_anomaly},
                        "warning",
                        client_ip
                    )
                
                # Create JWT token with session ID
                access_token = self._create_access_token(user.id, user.email)
                
                # Extract session ID from token for tracking
                import jwt as jwt_lib
                try:
                    token_payload = jwt_lib.decode(access_token, SECRET_KEY, algorithms=["HS256"])
                    session_id = token_payload.get("jti")
                except:
                    session_id = str(uuid.uuid4())
                
                # Register session with security tracking
                self.session_manager.register_session(session_id, user.id, request, client_ip)
                
                # Store session in database
                session_repo = SessionRepository(db)
                await session_repo.create_session(user.id, access_token)
                
                logger.info("User login successful", 
                          user_email=username, 
                          user_id=user.id,
                          event="user_login")
                
                return Token(
                    access_token=access_token,
                    token_type="bearer",
                    user_id=user.id,
                    email=user.email
                )
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Login failed: {e}")
                raise HTTPException(status_code=500, detail="Login failed")
        
        @self.app.get("/api/users/me", response_model=UserResponse)
        async def get_me(current_user: User = Depends(self._get_current_user)):
            """Get current user info with JWT validation."""
            start_time = time.time()
            self.request_count += 1
            
            # Record performance metrics
            self.performance_optimizer.record_request_time(time.time() - start_time)
            
            return UserResponse(
                id=current_user.id,
                email=current_user.email,
                created_at=current_user.created_at.isoformat(),
                is_verified=current_user.is_verified,
                is_active=current_user.is_active
            )
        
        # =======================
        # EMAIL VERIFICATION ENDPOINTS
        # =======================
        
        @self.app.post("/api/users/request-verification", response_model=EmailVerificationResponse)
        async def request_email_verification(
            request_data: EmailVerificationRequest,
            db: AsyncSession = Depends(get_db)
        ):
            """Request email verification for a user."""
            self.request_count += 1
            
            try:
                user_repo = UserRepository(db)
                verification_repo = EmailVerificationRepository(db)
                
                # Check if user exists
                user = await user_repo.get_user_by_email(request_data.email)
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")
                
                if user.is_verified:
                    raise HTTPException(status_code=400, detail="User is already verified")
                
                # Generate verification secret
                verification_secret = str(uuid.uuid4())
                expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hour expiry
                
                # Create verification record
                await verification_repo.create_verification(
                    email=request_data.email,
                    secret=verification_secret,
                    expires_at=expires_at
                )
                
                # Create verification link (for testing purposes)
                verification_link = f"http://localhost:8000/api/users/verify-email?secret={verification_secret}"
                
                # In production, send this link via email
                # For testing, we return it in the response and log it
                logger.info(f"📧 Email Verification Link: {verification_link}")
                print(f"📧 Email Verification Link for {request_data.email}: {verification_link}")
                
                return EmailVerificationResponse(
                    message="Verification email sent (simulated)",
                    verification_link=verification_link  # Only for testing
                )
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Email verification request failed: {e}")
                raise HTTPException(status_code=500, detail="Verification request failed")
        
        @self.app.get("/api/users/verify-email", response_model=EmailVerificationResponse)
        async def verify_email(
            secret: str,
            db: AsyncSession = Depends(get_db)
        ):
            """Verify email using verification secret."""
            self.request_count += 1
            
            try:
                user_repo = UserRepository(db)
                verification_repo = EmailVerificationRepository(db)
                
                # Get verification record
                verification = await verification_repo.get_verification_by_secret(secret)
                if not verification:
                    raise HTTPException(status_code=400, detail="Invalid or expired verification link")
                
                # Check if expired
                if verification.expires_at < datetime.now(timezone.utc):
                    await verification_repo.delete_verification(secret)
                    raise HTTPException(status_code=400, detail="Verification link has expired")
                
                # Get user and verify
                user = await user_repo.get_user_by_email(verification.email)
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")
                
                # Update user verification status
                await user_repo.update_user_verification(user.id, True)
                
                # Clean up verification record
                await verification_repo.delete_verification(secret)
                
                logger.info(f"Email verified for user: {verification.email}")
                
                return EmailVerificationResponse(
                    message="Email successfully verified"
                )
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Email verification failed: {e}")
                raise HTTPException(status_code=500, detail="Email verification failed")
        
        # =======================
        # PHOTO ENDPOINTS
        # =======================
        
        @self.app.post("/api/photos/upload", response_model=PhotoResponse)
        async def upload_photo(
            file: UploadFile = File(...),
            title: Optional[str] = None,
            description: Optional[str] = None,
            is_public: bool = False,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Upload photo with enhanced image processing pipeline."""
            self.request_count += 1
            
            try:
                # Read file content
                file_content = await file.read()
                
                # Enhanced file security validation
                await validate_file_security(file_content, file.content_type or "application/octet-stream", file.filename)
                
                # Advanced image validation with PIL
                validation_result = self.image_processor.validate_image(file_content)
                if not validation_result["is_valid"]:
                    raise HTTPException(status_code=400, detail=f"Invalid image: {validation_result['error']}")
                
                # Extract EXIF metadata
                exif_data = self.image_processor.extract_exif_data(file_content)
                
                # Optimize image for storage (compress, format conversion)
                optimized_content = self.image_processor.optimize_image(file_content)
                
                # Generate thumbnails
                thumbnails = self.image_processor.generate_thumbnails(optimized_content)
                
                # Calculate perceptual hash for duplicate detection
                perceptual_hash = self.image_processor.calculate_perceptual_hash(optimized_content)
                
                # Sanitize filename
                safe_filename = input_validator.sanitize_filename(file.filename or "upload")
                
                # Generate unique filename
                timestamp = int(time.time())
                file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
                filename = f"photo_{current_user.id}_{timestamp}_{secrets.token_hex(8)}{file_extension}"
                
                # Store optimized file using file storage service
                storage_info = await self.file_storage.store_file(
                    user_id=current_user.id,
                    filename=filename,
                    content=optimized_content,
                    content_type="image/jpeg"  # Always store as optimized JPEG
                )
                
                # Store thumbnails
                thumbnail_paths = {}
                for size_name, thumbnail_data in thumbnails.items():
                    if size_name != "original":  # Skip original as it's the main file
                        thumb_filename = f"thumb_{size_name}_{filename}"
                        thumb_storage = await self.file_storage.store_file(
                            user_id=current_user.id,
                            filename=thumb_filename,
                            content=thumbnail_data,
                            content_type="image/jpeg"
                        )
                        thumbnail_paths[size_name] = thumb_storage["storage_path"]
                
                # Create photo record in database
                photo_repo = PhotoRepository(db)
                photo = await photo_repo.create_photo(
                    user_id=current_user.id,
                    filename=filename,
                    original_filename=file.filename or "unknown",
                    content_type="image/jpeg",  # Always store as optimized JPEG
                    file_size=len(optimized_content),
                    storage_path=storage_info["storage_path"],
                    title=title,
                    description=description,
                    is_public=is_public
                )
                
                # Store enhanced metadata in PhotoMetadata table
                metadata_record = PhotoMetadata(
                    photo_id=photo.id,
                    width=validation_result.get("width"),
                    height=validation_result.get("height"),
                    format=validation_result.get("format"),
                    mode=validation_result.get("mode"),
                    has_transparency=validation_result.get("has_transparency", False),
                    date_taken=exif_data.get("date_taken"),
                    camera_make=exif_data.get("camera_make"),
                    camera_model=exif_data.get("camera_model"),
                    lens_model=exif_data.get("lens_model"),
                    software=exif_data.get("software"),
                    exposure_time=exif_data.get("exposure_time"),
                    f_number=exif_data.get("f_number"),
                    iso_speed=exif_data.get("iso_speed"),
                    focal_length=exif_data.get("focal_length"),
                    orientation=exif_data.get("orientation"),
                    latitude=exif_data.get("latitude"),
                    longitude=exif_data.get("longitude"),
                    altitude=exif_data.get("altitude"),
                    image_hash=perceptual_hash,
                    processed_sizes=thumbnail_paths,
                    color_space=exif_data.get("color_space"),
                    dominant_colors=exif_data.get("dominant_colors")
                )
                db.add(metadata_record)
                await db.commit()
                await db.refresh(metadata_record)
                
                logger.info("Photo uploaded and processed successfully", 
                          user_id=current_user.id,
                          user_email=current_user.email,
                          photo_id=photo.id,
                          original_filename=file.filename,
                          optimized_size=len(optimized_content),
                          thumbnails_generated=list(thumbnails.keys()),
                          event="photo_upload")
                
                response_data = PhotoResponse(
                    id=photo.id,
                    filename=photo.filename,
                    original_filename=photo.original_filename,
                    content_type=photo.content_type,
                    file_size=photo.file_size,
                    title=photo.title,
                    description=photo.description,
                    is_public=photo.is_public,
                    created_at=photo.created_at.isoformat()
                )
                
                # Add processing metadata to response for debugging
                if hasattr(response_data, "processing_info"):
                    response_data.processing_info = {
                        "optimized_size": len(optimized_content),
                        "thumbnails_generated": list(thumbnails.keys()),
                        "exif_extracted": bool(exif_data),
                        "perceptual_hash": perceptual_hash[:16] + "..." if perceptual_hash else None
                    }
                
                return response_data
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Photo upload failed: {e}")
                raise HTTPException(status_code=500, detail="Upload failed")
        
        @self.app.get("/api/photos/", response_model=List[PhotoResponse])
        async def list_photos(skip: int = 0, limit: int = 20, 
                             current_user: User = Depends(self._get_current_user),
                             db: AsyncSession = Depends(get_db)):
            """List user's photos with caching."""
            start_time = time.time()
            self.request_count += 1
            
            # Use optimized cached query
            photos_data = await optimized_db_ops.get_cached_user_photos(db, current_user.id, skip, limit)
            
            # Record performance metrics
            self.performance_optimizer.record_request_time(time.time() - start_time)
            
            return [PhotoResponse(**photo) for photo in photos_data]
        
        @self.app.get("/api/photos/public", response_model=List[PhotoResponse])
        async def list_public_photos(skip: int = 0, limit: int = 20, 
                                    db: AsyncSession = Depends(get_db)):
            """List public photos with caching."""
            start_time = time.time()
            self.request_count += 1
            
            # Use optimized cached query
            photos_data = await optimized_db_ops.get_cached_public_photos(db, skip, limit)
            
            # Record performance metrics
            self.performance_optimizer.record_request_time(time.time() - start_time)
            
            return [PhotoResponse(**photo) for photo in photos_data]
        
        @self.app.get("/api/photos/{photo_id}", response_model=PhotoResponse)
        async def get_photo(photo_id: int, 
                           current_user: User = Depends(self._get_current_user),
                           db: AsyncSession = Depends(get_db)):
            """Get photo by ID."""
            self.request_count += 1
            
            photo_repo = PhotoRepository(db)
            photo = await photo_repo.get_photo_by_id(photo_id)
            
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")
            
            # Check access permissions
            if photo.user_id != current_user.id and not photo.is_public:
                raise HTTPException(status_code=403, detail="Access denied")
            
            return PhotoResponse(
                id=photo.id,
                filename=photo.filename,
                original_filename=photo.original_filename,
                content_type=photo.content_type,
                file_size=photo.file_size,
                title=photo.title,
                description=photo.description,
                is_public=photo.is_public,
                created_at=photo.created_at.isoformat()
            )
        
        @self.app.get("/api/photos/{photo_id}/download")
        async def download_photo(photo_id: int, 
                                current_user: User = Depends(self._get_current_user),
                                db: AsyncSession = Depends(get_db)):
            """Download photo file."""
            self.request_count += 1
            
            photo_repo = PhotoRepository(db)
            photo = await photo_repo.get_photo_by_id(photo_id)
            
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")
            
            # Check access permissions
            if photo.user_id != current_user.id and not photo.is_public:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Retrieve file content
            file_content = await self.file_storage.retrieve_file(photo.storage_path)
            if not file_content:
                raise HTTPException(status_code=404, detail="Photo file not found")
            
            from fastapi.responses import Response
            return Response(
                content=file_content,
                media_type=photo.content_type,
                headers={
                    "Content-Disposition": f"attachment; filename={photo.original_filename}",
                    "Content-Length": str(len(file_content))
                }
            )
        
        @self.app.get("/api/photos/{photo_id}/url")
        async def get_photo_url(photo_id: int,
                               current_user: User = Depends(self._get_current_user),
                               db: AsyncSession = Depends(get_db)):
            """Get photo access URL."""
            self.request_count += 1
            
            photo_repo = PhotoRepository(db)
            photo = await photo_repo.get_photo_by_id(photo_id)
            
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")
            
            # Check access permissions
            if photo.user_id != current_user.id and not photo.is_public:
                raise HTTPException(status_code=403, detail="Access denied")
            
            return {
                "photo_id": photo.id,
                "download_url": f"/api/photos/{photo.id}/download",
                "storage_url": self.file_storage.get_file_url(photo.storage_path),
                "filename": photo.original_filename
            }
        
        # =======================
        # PHOTO TAGGING ENDPOINTS
        # =======================
        
        @self.app.post("/api/photos/{photo_id}/tags")
        async def add_photo_tag(
            photo_id: int,
            tag: str,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Add tag to photo."""
            self.request_count += 1
            
            try:
                # Validate tag format
                if not tag or len(tag.strip()) < 2:
                    raise HTTPException(status_code=400, detail="Tag must be at least 2 characters")
                
                tag = tag.strip().lower()[:100]  # Normalize and limit length
                
                # Check if photo exists and user has access
                photo_repo = PhotoRepository(db)
                photo = await photo_repo.get_photo_by_id(photo_id)
                
                if not photo:
                    raise HTTPException(status_code=404, detail="Photo not found")
                
                # Check permission (owner or public photo)
                if photo.user_id != current_user.id and not photo.is_public:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Check if tag already exists for this photo
                from sqlalchemy import select
                existing_tag = await db.execute(
                    select(PhotoTag).where(PhotoTag.photo_id == photo_id, PhotoTag.tag == tag)
                )
                if existing_tag.scalar_one_or_none():
                    raise HTTPException(status_code=409, detail="Tag already exists for this photo")
                
                # Create tag
                photo_tag = PhotoTag(
                    photo_id=photo_id,
                    tag=tag,
                    created_by=current_user.id
                )
                db.add(photo_tag)
                await db.commit()
                await db.refresh(photo_tag)
                
                logger.info(f"Tag '{tag}' added to photo {photo_id} by user {current_user.email}")
                
                return {
                    "message": "Tag added successfully",
                    "tag": photo_tag.to_dict()
                }
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Tag addition failed: {e}")
                raise HTTPException(status_code=500, detail="Tag addition failed")
        
        @self.app.get("/api/photos/{photo_id}/tags")
        async def get_photo_tags(
            photo_id: int,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get tags for a photo."""
            self.request_count += 1
            
            try:
                # Check if photo exists and user has access
                photo_repo = PhotoRepository(db)
                photo = await photo_repo.get_photo_by_id(photo_id)
                
                if not photo:
                    raise HTTPException(status_code=404, detail="Photo not found")
                
                # Check permission
                if photo.user_id != current_user.id and not photo.is_public:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Get all tags for this photo
                from sqlalchemy import select
                result = await db.execute(
                    select(PhotoTag).where(PhotoTag.photo_id == photo_id)
                )
                tags = result.scalars().all()
                
                return {
                    "photo_id": photo_id,
                    "tags": [tag.to_dict() for tag in tags]
                }
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to get photo tags: {e}")
                raise HTTPException(status_code=500, detail="Failed to get photo tags")
        
        @self.app.delete("/api/photos/{photo_id}/tags/{tag}")
        async def remove_photo_tag(
            photo_id: int,
            tag: str,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Remove tag from photo."""
            self.request_count += 1
            
            try:
                # Check if photo exists and user has access
                photo_repo = PhotoRepository(db)
                photo = await photo_repo.get_photo_by_id(photo_id)
                
                if not photo:
                    raise HTTPException(status_code=404, detail="Photo not found")
                
                # Only photo owner can remove tags
                if photo.user_id != current_user.id:
                    raise HTTPException(status_code=403, detail="Only photo owner can remove tags")
                
                # Find and delete tag
                from sqlalchemy import select, delete
                tag_normalized = tag.strip().lower()
                
                result = await db.execute(
                    select(PhotoTag).where(PhotoTag.photo_id == photo_id, PhotoTag.tag == tag_normalized)
                )
                existing_tag = result.scalar_one_or_none()
                
                if not existing_tag:
                    raise HTTPException(status_code=404, detail="Tag not found")
                
                await db.execute(
                    delete(PhotoTag).where(PhotoTag.photo_id == photo_id, PhotoTag.tag == tag_normalized)
                )
                await db.commit()
                
                logger.info(f"Tag '{tag}' removed from photo {photo_id} by user {current_user.email}")
                
                return {"message": "Tag removed successfully"}
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Tag removal failed: {e}")
                raise HTTPException(status_code=500, detail="Tag removal failed")
        
        @self.app.get("/api/photos/search")
        async def search_photos(
            q: str = None,
            tags: str = None,
            user_id: int = None,
            skip: int = 0,
            limit: int = 20,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Search photos by title, description, tags, or user."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select, and_, or_
                
                # Base query for photos user can access (their own + public)
                query = select(Photo).where(
                    or_(
                        Photo.user_id == current_user.id,
                        Photo.is_public == True
                    )
                )
                
                # Add search filters
                conditions = []
                
                # Text search in title and description
                if q and q.strip():
                    search_term = f"%{q.strip()}%"
                    conditions.append(
                        or_(
                            Photo.title.ilike(search_term),
                            Photo.description.ilike(search_term)
                        )
                    )
                
                # Tag search
                if tags and tags.strip():
                    tag_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
                    if tag_list:
                        # Join with PhotoTag table
                        query = query.join(PhotoTag).where(
                            PhotoTag.tag.in_(tag_list)
                        )
                
                # User filter
                if user_id:
                    conditions.append(Photo.user_id == user_id)
                
                # Apply all conditions
                if conditions:
                    query = query.where(and_(*conditions))
                
                # Add pagination
                query = query.offset(skip).limit(limit).order_by(Photo.created_at.desc())
                
                # Execute query
                result = await db.execute(query)
                photos = result.scalars().all()
                
                # Convert to response format
                photo_responses = []
                for photo in photos:
                    photo_responses.append(PhotoResponse(
                        id=photo.id,
                        filename=photo.filename,
                        original_filename=photo.original_filename,
                        content_type=photo.content_type,
                        file_size=photo.file_size,
                        title=photo.title,
                        description=photo.description,
                        is_public=photo.is_public,
                        created_at=photo.created_at.isoformat()
                    ))
                
                return {
                    "photos": photo_responses,
                    "total": len(photo_responses),
                    "search_params": {
                        "query": q,
                        "tags": tags,
                        "user_id": user_id,
                        "skip": skip,
                        "limit": limit
                    }
                }
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Photo search failed: {e}")
                raise HTTPException(status_code=500, detail="Photo search failed")
        
        @self.app.get("/api/tags/popular")
        async def get_popular_tags(
            limit: int = 20,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get most popular tags across all accessible photos."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select, func, or_
                
                # Get popular tags from photos the user can access
                query = select(
                    PhotoTag.tag,
                    func.count(PhotoTag.id).label("usage_count")
                ).select_from(
                    PhotoTag.join(Photo)
                ).where(
                    or_(
                        Photo.user_id == current_user.id,
                        Photo.is_public == True
                    )
                ).group_by(PhotoTag.tag).order_by(
                    func.count(PhotoTag.id).desc()
                ).limit(limit)
                
                result = await db.execute(query)
                tags = result.all()
                
                return {
                    "popular_tags": [
                        {"tag": tag[0], "usage_count": tag[1]}
                        for tag in tags
                    ]
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to get popular tags: {e}")
                raise HTTPException(status_code=500, detail="Failed to get popular tags")
        
        # =======================
        # ALBUM/COLLECTION ENDPOINTS
        # =======================
        
        @self.app.post("/api/albums", response_model=AlbumResponse)
        async def create_album(
            album_data: AlbumCreate,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Create a new album."""
            self.request_count += 1
            
            try:
                # Validate album name
                if not album_data.name or len(album_data.name.strip()) < 1:
                    raise HTTPException(status_code=400, detail="Album name cannot be empty")
                
                if len(album_data.name) > 255:
                    raise HTTPException(status_code=400, detail="Album name too long (max 255 characters)")
                
                # Create album
                album = Album(
                    user_id=current_user.id,
                    name=album_data.name.strip(),
                    description=album_data.description,
                    is_public=album_data.is_public,
                    photos_count=0
                )
                db.add(album)
                await db.commit()
                await db.refresh(album)
                
                logger.info("Album created successfully",
                          user_id=current_user.id,
                          album_id=album.id,
                          album_name=album.name,
                          event="album_create")
                
                return AlbumResponse(
                    id=album.id,
                    name=album.name,
                    description=album.description,
                    is_public=album.is_public,
                    photos_count=album.photos_count,
                    cover_photo_id=album.cover_photo_id,
                    created_at=album.created_at.isoformat(),
                    updated_at=album.updated_at.isoformat()
                )
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Album creation failed", error=str(e))
                raise HTTPException(status_code=500, detail="Album creation failed")
        
        @self.app.get("/api/albums", response_model=List[AlbumResponse])
        async def list_albums(
            skip: int = 0,
            limit: int = 20,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """List user's albums."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                # Get user's albums
                result = await db.execute(
                    select(Album).where(Album.user_id == current_user.id)
                    .offset(skip).limit(limit).order_by(Album.created_at.desc())
                )
                albums = result.scalars().all()
                
                album_responses = []
                for album in albums:
                    album_responses.append(AlbumResponse(
                        id=album.id,
                        name=album.name,
                        description=album.description,
                        is_public=album.is_public,
                        photos_count=album.photos_count,
                        cover_photo_id=album.cover_photo_id,
                        created_at=album.created_at.isoformat(),
                        updated_at=album.updated_at.isoformat()
                    ))
                
                return album_responses
                
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to list albums", error=str(e))
                raise HTTPException(status_code=500, detail="Failed to list albums")
        
        @self.app.post("/api/albums/{album_id}/photos/{photo_id}")
        async def add_photo_to_album(
            album_id: int,
            photo_id: int,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Add photo to album."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select, func
                
                # Check album exists and user has access
                album_result = await db.execute(select(Album).where(Album.id == album_id))
                album = album_result.scalar_one_or_none()
                
                if not album:
                    raise HTTPException(status_code=404, detail="Album not found")
                
                if album.user_id != current_user.id:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Check photo exists and user has access
                photo_repo = PhotoRepository(db)
                photo = await photo_repo.get_photo_by_id(photo_id)
                
                if not photo:
                    raise HTTPException(status_code=404, detail="Photo not found")
                
                if photo.user_id != current_user.id:
                    raise HTTPException(status_code=403, detail="Cannot add other user's photo to album")
                
                # Check if photo already in album
                existing = await db.execute(
                    select(AlbumPhoto).where(
                        AlbumPhoto.album_id == album_id,
                        AlbumPhoto.photo_id == photo_id
                    )
                )
                if existing.scalar_one_or_none():
                    raise HTTPException(status_code=409, detail="Photo already in album")
                
                # Get next position
                position_result = await db.execute(
                    select(func.max(AlbumPhoto.position)).where(AlbumPhoto.album_id == album_id)
                )
                max_position = position_result.scalar() or 0
                
                # Add photo to album
                album_photo = AlbumPhoto(
                    album_id=album_id,
                    photo_id=photo_id,
                    added_by=current_user.id,
                    position=max_position + 1
                )
                db.add(album_photo)
                
                # Update album photos count
                album.photos_count += 1
                
                await db.commit()
                
                logger.info("Photo added to album",
                          user_id=current_user.id,
                          album_id=album_id,
                          photo_id=photo_id,
                          event="photo_add_to_album")
                
                return {
                    "message": "Photo added to album successfully",
                    "album_id": album_id,
                    "photo_id": photo_id,
                    "position": album_photo.position
                }
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to add photo to album", album_id=album_id, photo_id=photo_id, error=str(e))
                raise HTTPException(status_code=500, detail="Failed to add photo to album")
        
        @self.app.get("/api/albums/{album_id}/photos", response_model=List[PhotoResponse])
        async def get_album_photos(
            album_id: int,
            skip: int = 0,
            limit: int = 20,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get photos in album."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                # Check album exists and user has access
                album_result = await db.execute(select(Album).where(Album.id == album_id))
                album = album_result.scalar_one_or_none()
                
                if not album:
                    raise HTTPException(status_code=404, detail="Album not found")
                
                if album.user_id != current_user.id and not album.is_public:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Get photos in album with ordering
                photos_result = await db.execute(
                    select(Photo, AlbumPhoto.position).select_from(
                        AlbumPhoto.join(Photo)
                    ).where(
                        AlbumPhoto.album_id == album_id
                    ).order_by(AlbumPhoto.position)
                    .offset(skip).limit(limit)
                )
                photos_data = photos_result.all()
                
                photo_responses = []
                for photo, position in photos_data:
                    photo_responses.append(PhotoResponse(
                        id=photo.id,
                        filename=photo.filename,
                        original_filename=photo.original_filename,
                        content_type=photo.content_type,
                        file_size=photo.file_size,
                        title=photo.title,
                        description=photo.description,
                        is_public=photo.is_public,
                        created_at=photo.created_at.isoformat()
                    ))
                
                return photo_responses
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to get album photos", album_id=album_id, error=str(e))
                raise HTTPException(status_code=500, detail="Failed to get album photos")
        
        # =======================
        # USER PROFILE ENDPOINTS
        # =======================
        
        @self.app.post("/api/profiles", response_model=UserProfileResponse)
        async def create_user_profile(
            profile_data: UserProfileCreate,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Create user profile."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                # Check if profile already exists
                existing_profile = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == current_user.id)
                )
                if existing_profile.scalar_one_or_none():
                    raise HTTPException(status_code=409, detail="User profile already exists")
                
                # Validate website URL if provided
                if profile_data.website:
                    if not profile_data.website.startswith(('http://', 'https://')):
                        profile_data.website = 'https://' + profile_data.website
                
                # Create profile
                profile = UserProfile(
                    user_id=current_user.id,
                    display_name=profile_data.display_name,
                    bio=profile_data.bio,
                    location=profile_data.location,
                    website=profile_data.website,
                    followers_count=0,
                    following_count=0,
                    photos_count=0,
                    likes_received_count=0,
                    is_private=profile_data.is_private,
                    allow_comments=profile_data.allow_comments,
                    allow_tags=profile_data.allow_tags,
                    show_location=profile_data.show_location
                )
                db.add(profile)
                await db.commit()
                await db.refresh(profile)
                
                logger.info("User profile created",
                          user_id=current_user.id,
                          profile_id=profile.id,
                          event="profile_create")
                
                return UserProfileResponse(
                    id=profile.id,
                    user_id=profile.user_id,
                    display_name=profile.display_name,
                    bio=profile.bio,
                    location=profile.location,
                    website=profile.website,
                    avatar_photo_id=profile.avatar_photo_id,
                    followers_count=profile.followers_count,
                    following_count=profile.following_count,
                    photos_count=profile.photos_count,
                    likes_received_count=profile.likes_received_count,
                    is_private=profile.is_private,
                    allow_comments=profile.allow_comments,
                    allow_tags=profile.allow_tags,
                    show_location=profile.show_location,
                    created_at=profile.created_at.isoformat(),
                    updated_at=profile.updated_at.isoformat()
                )
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Profile creation failed", error=str(e))
                raise HTTPException(status_code=500, detail="Profile creation failed")
        
        @self.app.get("/api/profiles/{user_id}", response_model=UserProfileResponse)
        async def get_user_profile(
            user_id: int,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get user profile by user ID."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                # Get profile
                profile_result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == user_id)
                )
                profile = profile_result.scalar_one_or_none()
                
                if not profile:
                    raise HTTPException(status_code=404, detail="Profile not found")
                
                # Check privacy settings
                if profile.is_private and profile.user_id != current_user.id:
                    # Check if current user follows this user
                    from sqlalchemy import select
                    follow_result = await db.execute(
                        select(UserFollow).where(
                            UserFollow.follower_id == current_user.id,
                            UserFollow.following_id == user_id
                        )
                    )
                    if not follow_result.scalar_one_or_none():
                        raise HTTPException(status_code=403, detail="Profile is private")
                
                return UserProfileResponse(
                    id=profile.id,
                    user_id=profile.user_id,
                    display_name=profile.display_name,
                    bio=profile.bio,
                    location=profile.location if profile.show_location or profile.user_id == current_user.id else None,
                    website=profile.website,
                    avatar_photo_id=profile.avatar_photo_id,
                    followers_count=profile.followers_count,
                    following_count=profile.following_count,
                    photos_count=profile.photos_count,
                    likes_received_count=profile.likes_received_count,
                    is_private=profile.is_private,
                    allow_comments=profile.allow_comments,
                    allow_tags=profile.allow_tags,
                    show_location=profile.show_location,
                    created_at=profile.created_at.isoformat(),
                    updated_at=profile.updated_at.isoformat()
                )
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to get profile", user_id=user_id, error=str(e))
                raise HTTPException(status_code=500, detail="Failed to get profile")
        
        @self.app.get("/api/profiles/me", response_model=UserProfileResponse)
        async def get_my_profile(
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get current user's profile."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                # Get profile
                profile_result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == current_user.id)
                )
                profile = profile_result.scalar_one_or_none()
                
                if not profile:
                    raise HTTPException(status_code=404, detail="Profile not found")
                
                return UserProfileResponse(
                    id=profile.id,
                    user_id=profile.user_id,
                    display_name=profile.display_name,
                    bio=profile.bio,
                    location=profile.location,
                    website=profile.website,
                    avatar_photo_id=profile.avatar_photo_id,
                    followers_count=profile.followers_count,
                    following_count=profile.following_count,
                    photos_count=profile.photos_count,
                    likes_received_count=profile.likes_received_count,
                    is_private=profile.is_private,
                    allow_comments=profile.allow_comments,
                    allow_tags=profile.allow_tags,
                    show_location=profile.show_location,
                    created_at=profile.created_at.isoformat(),
                    updated_at=profile.updated_at.isoformat()
                )
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to get current user profile", error=str(e))
                raise HTTPException(status_code=500, detail="Failed to get current user profile")
        
        @self.app.put("/api/profiles/me", response_model=UserProfileResponse)
        async def update_my_profile(
            profile_update: UserProfileUpdate,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Update current user's profile."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                # Get profile
                profile_result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == current_user.id)
                )
                profile = profile_result.scalar_one_or_none()
                
                if not profile:
                    raise HTTPException(status_code=404, detail="Profile not found")
                
                # Update fields
                if profile_update.display_name is not None:
                    if len(profile_update.display_name) > 100:
                        raise HTTPException(status_code=400, detail="Display name too long (max 100 characters)")
                    profile.display_name = profile_update.display_name.strip() if profile_update.display_name else None
                
                if profile_update.bio is not None:
                    if len(profile_update.bio) > 2000:
                        raise HTTPException(status_code=400, detail="Bio too long (max 2000 characters)")
                    profile.bio = profile_update.bio.strip() if profile_update.bio else None
                
                if profile_update.location is not None:
                    if len(profile_update.location) > 200:
                        raise HTTPException(status_code=400, detail="Location too long (max 200 characters)")
                    profile.location = profile_update.location.strip() if profile_update.location else None
                
                if profile_update.website is not None:
                    if profile_update.website:
                        if not profile_update.website.startswith(('http://', 'https://')):
                            profile_update.website = 'https://' + profile_update.website
                        if len(profile_update.website) > 500:
                            raise HTTPException(status_code=400, detail="Website URL too long (max 500 characters)")
                    profile.website = profile_update.website
                
                if profile_update.avatar_photo_id is not None:
                    # Verify avatar photo exists and belongs to user
                    if profile_update.avatar_photo_id:
                        photo_repo = PhotoRepository(db)
                        avatar_photo = await photo_repo.get_photo_by_id(profile_update.avatar_photo_id)
                        if not avatar_photo or avatar_photo.user_id != current_user.id:
                            raise HTTPException(status_code=400, detail="Invalid avatar photo")
                    profile.avatar_photo_id = profile_update.avatar_photo_id
                
                if profile_update.is_private is not None:
                    profile.is_private = profile_update.is_private
                
                if profile_update.allow_comments is not None:
                    profile.allow_comments = profile_update.allow_comments
                
                if profile_update.allow_tags is not None:
                    profile.allow_tags = profile_update.allow_tags
                
                if profile_update.show_location is not None:
                    profile.show_location = profile_update.show_location
                
                await db.commit()
                await db.refresh(profile)
                
                logger.info("User profile updated",
                          user_id=current_user.id,
                          profile_id=profile.id,
                          event="profile_update")
                
                return UserProfileResponse(
                    id=profile.id,
                    user_id=profile.user_id,
                    display_name=profile.display_name,
                    bio=profile.bio,
                    location=profile.location,
                    website=profile.website,
                    avatar_photo_id=profile.avatar_photo_id,
                    followers_count=profile.followers_count,
                    following_count=profile.following_count,
                    photos_count=profile.photos_count,
                    likes_received_count=profile.likes_received_count,
                    is_private=profile.is_private,
                    allow_comments=profile.allow_comments,
                    allow_tags=profile.allow_tags,
                    show_location=profile.show_location,
                    created_at=profile.created_at.isoformat(),
                    updated_at=profile.updated_at.isoformat()
                )
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Profile update failed", error=str(e))
                raise HTTPException(status_code=500, detail="Profile update failed")
        
        # =======================
        # NOTIFICATION ENDPOINTS
        # =======================
        
        @self.app.get("/api/notifications", response_model=List[NotificationResponse])
        async def get_notifications(
            skip: int = 0,
            limit: int = 50,
            unread_only: bool = False,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get user notifications."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                # Build query
                query = select(Notification).where(Notification.user_id == current_user.id)
                
                if unread_only:
                    query = query.where(Notification.is_read == False)
                
                query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
                
                result = await db.execute(query)
                notifications = result.scalars().all()
                
                notification_responses = []
                for notification in notifications:
                    notification_responses.append(NotificationResponse(
                        id=notification.id,
                        type=notification.type,
                        from_user_id=notification.from_user_id,
                        photo_id=notification.photo_id,
                        album_id=notification.album_id,
                        comment_id=notification.comment_id,
                        title=notification.title,
                        message=notification.message,
                        is_read=notification.is_read,
                        created_at=notification.created_at.isoformat()
                    ))
                
                return notification_responses
                
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to get notifications", error=str(e))
                raise HTTPException(status_code=500, detail="Failed to get notifications")
        
        @self.app.put("/api/notifications/{notification_id}/read")
        async def mark_notification_read(
            notification_id: int,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Mark notification as read."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                result = await db.execute(
                    select(Notification).where(
                        Notification.id == notification_id,
                        Notification.user_id == current_user.id
                    )
                )
                notification = result.scalar_one_or_none()
                
                if not notification:
                    raise HTTPException(status_code=404, detail="Notification not found")
                
                notification.is_read = True
                await db.commit()
                
                logger.info("Notification marked as read",
                          user_id=current_user.id,
                          notification_id=notification_id,
                          event="notification_read")
                
                return {"message": "Notification marked as read"}
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to mark notification as read", notification_id=notification_id, error=str(e))
                raise HTTPException(status_code=500, detail="Failed to mark notification as read")
        
        @self.app.put("/api/notifications/read-all")
        async def mark_all_notifications_read(
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Mark all notifications as read."""
            self.request_count += 1
            
            try:
                from sqlalchemy import update
                
                await db.execute(
                    update(Notification)
                    .where(Notification.user_id == current_user.id, Notification.is_read == False)
                    .values(is_read=True)
                )
                await db.commit()
                
                logger.info("All notifications marked as read",
                          user_id=current_user.id,
                          event="notifications_read_all")
                
                return {"message": "All notifications marked as read"}
                
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to mark all notifications as read", error=str(e))
                raise HTTPException(status_code=500, detail="Failed to mark all notifications as read")
        
        @self.app.get("/api/notifications/unread-count")
        async def get_unread_notification_count(
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get count of unread notifications."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select, func
                
                result = await db.execute(
                    select(func.count(Notification.id)).where(
                        Notification.user_id == current_user.id,
                        Notification.is_read == False
                    )
                )
                unread_count = result.scalar() or 0
                
                return {
                    "unread_count": unread_count,
                    "user_id": current_user.id
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to get unread notification count", error=str(e))
                raise HTTPException(status_code=500, detail="Failed to get unread notification count")
        
        @self.app.delete("/api/notifications/{notification_id}")
        async def delete_notification(
            notification_id: int,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Delete notification."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                result = await db.execute(
                    select(Notification).where(
                        Notification.id == notification_id,
                        Notification.user_id == current_user.id
                    )
                )
                notification = result.scalar_one_or_none()
                
                if not notification:
                    raise HTTPException(status_code=404, detail="Notification not found")
                
                await db.delete(notification)
                await db.commit()
                
                logger.info("Notification deleted",
                          user_id=current_user.id,
                          notification_id=notification_id,
                          event="notification_delete")
                
                return {"message": "Notification deleted"}
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to delete notification", notification_id=notification_id, error=str(e))
                raise HTTPException(status_code=500, detail="Failed to delete notification")
        
        # Helper function to create notifications
        async def _create_notification(
            self,
            db: AsyncSession,
            user_id: int,
            notification_type: str,
            title: str,
            message: Optional[str] = None,
            from_user_id: Optional[int] = None,
            photo_id: Optional[int] = None,
            album_id: Optional[int] = None,
            comment_id: Optional[int] = None
        ):
            """Create a new notification."""
            try:
                notification = Notification(
                    user_id=user_id,
                    type=notification_type,
                    from_user_id=from_user_id,
                    photo_id=photo_id,
                    album_id=album_id,
                    comment_id=comment_id,
                    title=title,
                    message=message,
                    is_read=False
                )
                db.add(notification)
                await db.commit()
                
                logger.info("Notification created",
                          user_id=user_id,
                          notification_type=notification_type,
                          event="notification_create")
                
            except Exception as e:
                logger.error("Failed to create notification", 
                           user_id=user_id, 
                           notification_type=notification_type, 
                           error=str(e))
        
        # =======================
        # PHOTO SHARING ENDPOINTS
        # =======================
        
        @self.app.post("/api/photos/{photo_id}/share", response_model=PhotoShareResponse)
        async def create_photo_share(
            photo_id: int,
            share_data: PhotoShareCreate,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Create a shareable link for a photo."""
            self.request_count += 1
            
            try:
                # Check if photo exists and user owns it
                photo_repo = PhotoRepository(db)
                photo = await photo_repo.get_photo_by_id(photo_id)
                
                if not photo:
                    raise HTTPException(status_code=404, detail="Photo not found")
                
                if photo.user_id != current_user.id:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Generate share token
                import secrets
                share_token = secrets.token_urlsafe(32)
                
                # Calculate expiration
                expires_at = None
                if share_data.expires_hours:
                    expires_at = datetime.now(timezone.utc) + timedelta(hours=share_data.expires_hours)
                
                # Hash password if provided
                password_hash = None
                if share_data.password:
                    from passlib.context import CryptContext
                    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                    password_hash = pwd_context.hash(share_data.password)
                
                # Create photo share record
                photo_share = PhotoShare(
                    photo_id=photo_id,
                    shared_by=current_user.id,
                    share_token=share_token,
                    expires_at=expires_at,
                    max_views=share_data.max_views,
                    current_views=0,
                    allow_download=share_data.allow_download,
                    allow_comments=share_data.allow_comments,
                    password_protected=password_hash,
                    is_active=True
                )
                db.add(photo_share)
                await db.commit()
                await db.refresh(photo_share)
                
                # Generate share URL
                share_url = f"/shared/{share_token}"
                
                logger.info("Photo share created",
                          user_id=current_user.id,
                          photo_id=photo_id,
                          share_token=share_token,
                          event="photo_share_create")
                
                return PhotoShareResponse(
                    id=photo_share.id,
                    photo_id=photo_share.photo_id,
                    share_token=photo_share.share_token,
                    share_url=share_url,
                    expires_at=photo_share.expires_at.isoformat() if photo_share.expires_at else None,
                    max_views=photo_share.max_views,
                    current_views=photo_share.current_views,
                    allow_download=photo_share.allow_download,
                    allow_comments=photo_share.allow_comments,
                    password_protected=bool(photo_share.password_protected),
                    is_active=photo_share.is_active,
                    created_at=photo_share.created_at.isoformat(),
                    last_accessed=photo_share.last_accessed.isoformat() if photo_share.last_accessed else None
                )
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Photo share creation failed", photo_id=photo_id, error=str(e))
                raise HTTPException(status_code=500, detail="Photo share creation failed")
        
        @self.app.get("/api/photos/{photo_id}/shares", response_model=List[PhotoShareResponse])
        async def get_photo_shares(
            photo_id: int,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get all shares for a photo."""
            self.request_count += 1
            
            try:
                # Check if photo exists and user owns it
                photo_repo = PhotoRepository(db)
                photo = await photo_repo.get_photo_by_id(photo_id)
                
                if not photo:
                    raise HTTPException(status_code=404, detail="Photo not found")
                
                if photo.user_id != current_user.id:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Get all shares for this photo
                from sqlalchemy import select
                result = await db.execute(
                    select(PhotoShare).where(PhotoShare.photo_id == photo_id)
                    .order_by(PhotoShare.created_at.desc())
                )
                shares = result.scalars().all()
                
                share_responses = []
                for share in shares:
                    share_url = f"/shared/{share.share_token}"
                    share_responses.append(PhotoShareResponse(
                        id=share.id,
                        photo_id=share.photo_id,
                        share_token=share.share_token,
                        share_url=share_url,
                        expires_at=share.expires_at.isoformat() if share.expires_at else None,
                        max_views=share.max_views,
                        current_views=share.current_views,
                        allow_download=share.allow_download,
                        allow_comments=share.allow_comments,
                        password_protected=bool(share.password_protected),
                        is_active=share.is_active,
                        created_at=share.created_at.isoformat(),
                        last_accessed=share.last_accessed.isoformat() if share.last_accessed else None
                    ))
                
                return share_responses
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to get photo shares", photo_id=photo_id, error=str(e))
                raise HTTPException(status_code=500, detail="Failed to get photo shares")
        
        @self.app.get("/shared/{share_token}")
        async def access_shared_photo(
            share_token: str,
            password: Optional[str] = None,
            db: AsyncSession = Depends(get_db)
        ):
            """Access a shared photo via share token."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                # Get share record
                result = await db.execute(
                    select(PhotoShare).where(PhotoShare.share_token == share_token)
                )
                share = result.scalar_one_or_none()
                
                if not share:
                    raise HTTPException(status_code=404, detail="Shared photo not found")
                
                # Check if share is active
                if not share.is_active:
                    raise HTTPException(status_code=403, detail="Share link is disabled")
                
                # Check expiration
                if share.expires_at and share.expires_at < datetime.now(timezone.utc):
                    raise HTTPException(status_code=410, detail="Share link has expired")
                
                # Check view limit
                if share.max_views and share.current_views >= share.max_views:
                    raise HTTPException(status_code=403, detail="Share link view limit exceeded")
                
                # Check password if required
                if share.password_protected:
                    if not password:
                        raise HTTPException(status_code=401, detail="Password required")
                    
                    from passlib.context import CryptContext
                    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                    if not pwd_context.verify(password, share.password_protected):
                        raise HTTPException(status_code=401, detail="Invalid password")
                
                # Get photo
                photo_repo = PhotoRepository(db)
                photo = await photo_repo.get_photo_by_id(share.photo_id)
                
                if not photo:
                    raise HTTPException(status_code=404, detail="Photo not found")
                
                # Update access statistics
                share.current_views += 1
                share.last_accessed = datetime.now(timezone.utc)
                await db.commit()
                
                # Get photo metadata
                photo_data = {
                    "id": photo.id,
                    "filename": photo.original_filename,
                    "title": photo.title,
                    "description": photo.description,
                    "created_at": photo.created_at.isoformat(),
                    "share_settings": {
                        "allow_download": share.allow_download,
                        "allow_comments": share.allow_comments,
                        "views": share.current_views,
                        "max_views": share.max_views
                    }
                }
                
                logger.info("Shared photo accessed",
                          photo_id=photo.id,
                          share_token=share_token,
                          views=share.current_views,
                          event="shared_photo_access")
                
                return photo_data
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to access shared photo", share_token=share_token, error=str(e))
                raise HTTPException(status_code=500, detail="Failed to access shared photo")
        
        @self.app.delete("/api/shares/{share_id}")
        async def delete_photo_share(
            share_id: int,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Delete a photo share."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                result = await db.execute(select(PhotoShare).where(PhotoShare.id == share_id))
                share = result.scalar_one_or_none()
                
                if not share:
                    raise HTTPException(status_code=404, detail="Share not found")
                
                if share.shared_by != current_user.id:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                await db.delete(share)
                await db.commit()
                
                logger.info("Photo share deleted",
                          user_id=current_user.id,
                          share_id=share_id,
                          event="photo_share_delete")
                
                return {"message": "Photo share deleted"}
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to delete photo share", share_id=share_id, error=str(e))
                raise HTTPException(status_code=500, detail="Failed to delete photo share")
        
        @self.app.put("/api/shares/{share_id}/toggle")
        async def toggle_photo_share(
            share_id: int,
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Toggle photo share active status."""
            self.request_count += 1
            
            try:
                from sqlalchemy import select
                
                result = await db.execute(select(PhotoShare).where(PhotoShare.id == share_id))
                share = result.scalar_one_or_none()
                
                if not share:
                    raise HTTPException(status_code=404, detail="Share not found")
                
                if share.shared_by != current_user.id:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                share.is_active = not share.is_active
                await db.commit()
                
                status = "enabled" if share.is_active else "disabled"
                
                logger.info("Photo share toggled",
                          user_id=current_user.id,
                          share_id=share_id,
                          status=status,
                          event="photo_share_toggle")
                
                return {"message": f"Photo share {status}", "is_active": share.is_active}
                
            except HTTPException:
                self.error_count += 1
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("Failed to toggle photo share", share_id=share_id, error=str(e))
                raise HTTPException(status_code=500, detail="Failed to toggle photo share")
        
        # =======================
        # PLATFORM INTEGRATION ENDPOINTS
        # =======================
        
        @self.app.get("/api/platform/stats")
        async def get_platform_stats(db: AsyncSession = Depends(get_db)):
            """Get comprehensive service statistics with caching."""
            start_time = time.time()
            uptime = self._get_uptime()
            
            # Use optimized cached query for database stats
            db_stats = await optimized_db_ops.get_cached_platform_stats(db)
            
            # Record performance metrics
            self.performance_optimizer.record_request_time(time.time() - start_time)
            
            return {
                "service_name": self.service_name,
                "service_type": "media",
                "version": self.version,
                "uptime_seconds": int(uptime),
                "total_photos": db_stats["total_photos"],
                "registered_users": db_stats["total_users"],
                "active_sessions": db_stats["active_sessions"],
                "requests_processed": self.request_count,
                "errors": self.error_count,
                "platform_integration": "functional",
                "database_integration": "postgresql",
                "features": [
                    "user_registration",
                    "jwt_authentication",
                    "password_security",
                    "photo_upload",
                    "database_storage",
                    "api_endpoints",
                    "health_monitoring",
                    "performance_optimization",
                    "redis_caching"
                ],
                "database_status": await db_manager.health_check(),
                "cached_at": db_stats["cached_at"]
            }
        
        @self.app.get("/api/platform/services")
        async def get_services():
            """Get discovered services."""
            self.request_count += 1
            
            services = await self.service_discovery.list_services()
            discovery_status = await self.service_discovery.get_discovery_status()
            
            return {
                "services": services,
                "discovery_status": discovery_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/platform/services/{service_name}")
        async def get_service(service_name: str):
            """Get specific service information."""
            self.request_count += 1
            
            service = await self.service_discovery.discover_service(service_name)
            if not service:
                raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
            
            return service
        
        @self.app.get("/api/platform/health-check")
        async def platform_health_check():
            """Perform health checks on all platform services."""
            self.request_count += 1
            
            health_results = await self.service_discovery.health_check_services()
            discovery_status = await self.service_discovery.get_discovery_status()
            
            return {
                "platform_health": health_results,
                "discovery_status": discovery_status,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/platform/errors")
        async def get_error_stats():
            """Get error statistics and monitoring information."""
            self.request_count += 1
            
            error_stats = error_handler.get_error_stats()
            performance_stats = performance_monitor.get_performance_stats()
            validation_stats = request_validator.get_validation_stats()
            
            return {
                "error_statistics": error_stats,
                "performance_statistics": performance_stats,
                "validation_statistics": validation_stats,
                "service_health": {
                    "request_count": self.request_count,
                    "error_count": self.error_count,
                    "error_rate": (self.error_count / max(self.request_count, 1)) * 100
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/platform/monitoring")
        async def get_monitoring_dashboard():
            """Get comprehensive monitoring dashboard."""
            self.request_count += 1
            
            uptime = self._get_uptime()
            error_stats = error_handler.get_error_stats()
            performance_stats = performance_monitor.get_performance_stats()
            
            # Get database counts
            from sqlalchemy import select, func
            user_count = 0
            photo_count = 0
            session_count = 0
            
            try:
                async for db in get_db():
                    user_count_result = await db.execute(select(func.count(User.id)))
                    user_count = user_count_result.scalar() or 0
                    
                    photo_count_result = await db.execute(select(func.count(Photo.id)))
                    photo_count = photo_count_result.scalar() or 0
                    
                    session_count_result = await db.execute(select(func.count(Session.id)).where(Session.is_active == True))
                    session_count = session_count_result.scalar() or 0
                    break
            except Exception as e:
                error_handler.log_error("MONITORING_DB_ERROR", str(e))
            
            return {
                "service_health": {
                    "service_name": self.service_name,
                    "version": self.version,
                    "uptime_seconds": int(uptime),
                    "status": "operational"
                },
                "database_metrics": {
                    "total_users": user_count,
                    "total_photos": photo_count,
                    "active_sessions": session_count
                },
                "request_metrics": {
                    "total_requests": self.request_count,
                    "total_errors": self.error_count,
                    "error_rate": (self.error_count / max(self.request_count, 1)) * 100
                },
                "error_analysis": error_stats,
                "performance_analysis": performance_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/platform/security")
        async def get_security_status():
            """Get security monitoring information."""
            self.request_count += 1
            
            rate_limit_stats = rate_limiter.get_rate_limit_stats()
            security_summary = security_audit.get_security_summary()
            
            return {
                "rate_limiting": rate_limit_stats,
                "security_audit": security_summary,
                "jwt_security": {
                    "algorithm": ALGORITHM,
                    "token_expiry_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
                    "revoked_tokens_count": len(self.jwt_security.revoked_tokens)
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/platform/performance")
        async def get_performance_status():
            """Get performance monitoring information."""
            self.request_count += 1
            
            performance_summary = self.performance_optimizer.get_performance_summary()
            
            # Update monitoring metrics with performance data
            await monitoring_dashboard.update_metrics_from_performance_data(performance_summary)
            
            return {
                "performance_optimization": performance_summary,
                "service_version": self.version,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/platform/performance/recommendations")
        async def get_performance_recommendations(db: AsyncSession = Depends(get_db)):
            """Get database performance optimization recommendations."""
            self.request_count += 1
            
            recommendations = await optimized_db_ops.get_performance_recommendations()
            
            return {
                "database_optimization": recommendations,
                "current_performance": self.performance_optimizer.get_performance_summary(),
                "service_version": self.version,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.post("/api/platform/cache/warm")
        async def warm_cache(current_user: User = Depends(self._get_current_user),
                           db: AsyncSession = Depends(get_db)):
            """Manually trigger cache warming (requires authentication)."""
            self.request_count += 1
            
            await self.performance_optimizer.warm_application_cache(db)
            cache_analytics = self.performance_optimizer.get_cache_analytics()
            
            return {
                "message": "Cache warming completed",
                "cache_analytics": cache_analytics,
                "service_version": self.version,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/platform/cache/analytics")
        async def get_cache_analytics():
            """Get detailed cache analytics and recommendations."""
            self.request_count += 1
            
            analytics = self.performance_optimizer.get_cache_analytics()
            
            return {
                "cache_analytics": analytics,
                "service_version": self.version,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/platform/validation")
        async def get_validation_stats():
            """Get request validation statistics."""
            self.request_count += 1
            
            validation_stats = request_validator.get_validation_stats()
            security_audit_data = security_audit.get_audit_summary()
            
            return {
                "validation_statistics": validation_stats,
                "security_audit": security_audit_data,
                "service_version": self.version,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/platform/logging")
        async def get_logging_stats():
            """Get request/response logging statistics."""
            self.request_count += 1
            
            correlation_id_value = get_correlation_id()
            
            return {
                "logging_middleware": {
                    "structured_logging_enabled": True,
                    "request_response_logging_enabled": True,
                    "correlation_id_enabled": True,
                    "max_body_size": 10000,
                    "sensitive_data_filtering": True
                },
                "current_correlation_id": correlation_id_value,
                "log_levels": {
                    "root": "INFO",
                    "sqlalchemy": "WARNING",
                    "uvicorn": "INFO"
                },
                "log_destinations": ["console", "file"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.post("/api/platform/validation/clear-blocked-ips")
        async def clear_blocked_ips(current_user: User = Depends(self._get_current_user)):
            """Clear blocked IPs (admin function)."""
            self.request_count += 1
            
            request_validator.clear_blocked_ips()
            
            return {
                "message": "Blocked IPs cleared successfully",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/platform/errors/detailed")
        async def get_detailed_error_stats():
            """Get detailed error statistics with trends and patterns."""
            self.request_count += 1
            
            error_stats = error_handler.get_error_stats()
            validation_stats = request_validator.get_validation_stats()
            performance_stats = performance_monitor.get_performance_stats()
            
            return {
                "error_statistics": error_stats,
                "validation_statistics": validation_stats,
                "performance_statistics": performance_stats,
                "service_health": {
                    "total_requests": self.request_count,
                    "total_errors": self.error_count,
                    "error_rate": (self.error_count / max(self.request_count, 1)) * 100,
                    "uptime": self._get_uptime()
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # RBAC Management Endpoints
        @self.app.post("/api/admin/roles")
        async def create_role(
            role_data: dict,
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "create_role")),
            db: AsyncSession = Depends(get_db)
        ):
            """Create a new role (admin only)."""
            self.request_count += 1
            
            try:
                role_repo = RoleRepository(db)
                role = await role_repo.create_role(
                    name=role_data["name"],
                    description=role_data.get("description")
                )
                
                logger.info(f"Role '{role.name}' created by admin {current_user.email}")
                return {
                    "message": "Role created successfully",
                    "role": role.to_dict()
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Role creation failed: {e}")
                raise HTTPException(status_code=500, detail="Role creation failed")
        
        @self.app.get("/api/admin/roles")
        async def list_roles(
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "read_roles")),
            db: AsyncSession = Depends(get_db)
        ):
            """List all roles (admin only)."""
            self.request_count += 1
            
            try:
                role_repo = RoleRepository(db)
                roles = await role_repo.get_all_roles()
                
                return {
                    "roles": [role.to_dict() for role in roles],
                    "count": len(roles)
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to list roles: {e}")
                raise HTTPException(status_code=500, detail="Failed to list roles")
        
        @self.app.post("/api/admin/permissions")
        async def create_permission(
            permission_data: dict,
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "create_permission")),
            db: AsyncSession = Depends(get_db)
        ):
            """Create a new permission (admin only)."""
            self.request_count += 1
            
            try:
                permission_repo = PermissionRepository(db)
                permission = await permission_repo.create_permission(
                    name=permission_data["name"],
                    resource=permission_data["resource"],
                    action=permission_data["action"],
                    description=permission_data.get("description")
                )
                
                logger.info(f"Permission '{permission.name}' created by admin {current_user.email}")
                return {
                    "message": "Permission created successfully",
                    "permission": permission.to_dict()
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Permission creation failed: {e}")
                raise HTTPException(status_code=500, detail="Permission creation failed")
        
        @self.app.get("/api/admin/permissions")
        async def list_permissions(
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "read_permissions")),
            db: AsyncSession = Depends(get_db)
        ):
            """List all permissions (admin only)."""
            self.request_count += 1
            
            try:
                permission_repo = PermissionRepository(db)
                permissions = await permission_repo.get_all_permissions()
                
                return {
                    "permissions": [permission.to_dict() for permission in permissions],
                    "count": len(permissions)
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to list permissions: {e}")
                raise HTTPException(status_code=500, detail="Failed to list permissions")
        
        @self.app.post("/api/admin/roles/{role_id}/permissions/{permission_id}")
        async def grant_permission_to_role(
            role_id: int,
            permission_id: int,
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "manage_role_permissions")),
            db: AsyncSession = Depends(get_db)
        ):
            """Grant permission to role (admin only)."""
            self.request_count += 1
            
            try:
                role_permission_repo = RolePermissionRepository(db)
                role_permission = await role_permission_repo.grant_permission_to_role(
                    role_id, permission_id, current_user.id
                )
                
                logger.info(f"Permission {permission_id} granted to role {role_id} by admin {current_user.email}")
                return {
                    "message": "Permission granted to role successfully",
                    "role_permission": role_permission.to_dict()
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to grant permission to role: {e}")
                raise HTTPException(status_code=500, detail="Failed to grant permission to role")
        
        @self.app.post("/api/admin/users/{user_id}/roles/{role_id}")
        async def assign_role_to_user(
            user_id: int,
            role_id: int,
            assignment_data: dict = None,
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "assign_user_roles")),
            db: AsyncSession = Depends(get_db)
        ):
            """Assign role to user (admin only)."""
            self.request_count += 1
            
            try:
                expires_at = None
                if assignment_data and "expires_at" in assignment_data:
                    expires_at = datetime.fromisoformat(assignment_data["expires_at"])
                
                user_role_repo = UserRoleRepository(db)
                user_role = await user_role_repo.assign_role_to_user(
                    user_id, role_id, current_user.id, expires_at
                )
                
                logger.info(f"Role {role_id} assigned to user {user_id} by admin {current_user.email}")
                return {
                    "message": "Role assigned to user successfully",
                    "user_role": user_role.to_dict()
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to assign role to user: {e}")
                raise HTTPException(status_code=500, detail="Failed to assign role to user")
        
        @self.app.get("/api/users/me/permissions")
        async def get_my_permissions(
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get current user's permissions."""
            self.request_count += 1
            
            try:
                user_role_repo = UserRoleRepository(db)
                
                # Get user's roles
                roles = await user_role_repo.get_user_roles(current_user.id)
                
                # Get user's permissions
                permissions = await user_role_repo.get_user_permissions(current_user.id)
                
                return {
                    "user_id": current_user.id,
                    "email": current_user.email,
                    "roles": [role.to_dict() for role in roles],
                    "permissions": [permission.to_dict() for permission in permissions],
                    "role_count": len(roles),
                    "permission_count": len(permissions)
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to get user permissions: {e}")
                raise HTTPException(status_code=500, detail="Failed to get user permissions")

        # Session Management Endpoints
        @self.app.get("/api/sessions/me")
        async def get_my_sessions(
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get current user's active sessions."""
            self.request_count += 1
            
            try:
                # Get user's active sessions from JWT security
                user_sessions = []
                for session_id, data in self.jwt_security.active_tokens.items():
                    if data.get("user_id") == current_user.id:
                        session_info = {
                            "session_id": session_id[:8] + "...",
                            "issued_at": data.get("issued_at", 0),
                            "last_used": data.get("last_used", 0),
                            "access_count": data.get("access_count", 0)
                        }
                        
                        # Add session security info if available
                        if session_id in self.session_manager.session_ips:
                            session_info["ip_addresses"] = self.session_manager.session_ips[session_id]
                        
                        if session_id in self.session_manager.suspicious_sessions:
                            session_info["flagged_as_suspicious"] = True
                        
                        user_sessions.append(session_info)
                
                return {
                    "user_id": current_user.id,
                    "active_sessions": user_sessions,
                    "session_count": len(user_sessions)
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to get user sessions: {e}")
                raise HTTPException(status_code=500, detail="Failed to get user sessions")
        
        @self.app.post("/api/sessions/revoke-all")
        async def revoke_all_sessions(
            current_user: User = Depends(self._get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Revoke all sessions for current user."""
            self.request_count += 1
            
            try:
                # Count sessions before revoking
                session_count = len([s for s, d in self.jwt_security.active_tokens.items() 
                                   if d.get("user_id") == current_user.id])
                
                # Revoke all user sessions
                self.session_manager.revoke_user_sessions(current_user.id)
                
                logger.info(f"All sessions revoked for user {current_user.id}")
                
                return {
                    "message": f"Successfully revoked {session_count} sessions",
                    "user_id": current_user.id,
                    "revoked_count": session_count
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to revoke user sessions: {e}")
                raise HTTPException(status_code=500, detail="Failed to revoke user sessions")
        
        @self.app.get("/api/admin/sessions")
        async def get_all_sessions(
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "manage_sessions")),
            db: AsyncSession = Depends(get_db)
        ):
            """Get all active sessions (admin only)."""
            self.request_count += 1
            
            try:
                sessions_info = []
                for session_id, data in self.jwt_security.active_tokens.items():
                    session_info = {
                        "session_id": session_id[:8] + "...",
                        "user_id": data.get("user_id"),
                        "issued_at": data.get("issued_at", 0),
                        "last_used": data.get("last_used", 0),
                        "access_count": data.get("access_count", 0)
                    }
                    
                    # Add security info
                    if session_id in self.session_manager.session_ips:
                        session_info["ip_addresses"] = self.session_manager.session_ips[session_id]
                    
                    if session_id in self.session_manager.suspicious_sessions:
                        session_info["flagged_as_suspicious"] = True
                    
                    sessions_info.append(session_info)
                
                # Get session security statistics
                security_stats = self.session_manager.get_session_security_stats()
                
                return {
                    "total_sessions": len(sessions_info),
                    "sessions": sessions_info,
                    "security_stats": security_stats
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to get all sessions: {e}")
                raise HTTPException(status_code=500, detail="Failed to get all sessions")
        
        @self.app.post("/api/admin/sessions/{user_id}/revoke")
        async def revoke_user_sessions(
            user_id: int,
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "manage_sessions")),
            db: AsyncSession = Depends(get_db)
        ):
            """Revoke all sessions for a specific user (admin only)."""
            self.request_count += 1
            
            try:
                # Count sessions before revoking
                session_count = len([s for s, d in self.jwt_security.active_tokens.items() 
                                   if d.get("user_id") == user_id])
                
                if session_count == 0:
                    raise HTTPException(status_code=404, detail="No active sessions found for user")
                
                # Revoke all user sessions
                self.session_manager.revoke_user_sessions(user_id)
                
                logger.info(f"Admin {current_user.id} revoked {session_count} sessions for user {user_id}")
                
                return {
                    "message": f"Successfully revoked {session_count} sessions for user {user_id}",
                    "admin_user_id": current_user.id,
                    "target_user_id": user_id,
                    "revoked_count": session_count
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to revoke user sessions: {e}")
                raise HTTPException(status_code=500, detail="Failed to revoke user sessions")

        # Encryption Management Endpoints
        @self.app.get("/api/admin/encryption/stats")
        async def get_encryption_stats(
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "read_encryption_stats")),
            db: AsyncSession = Depends(get_db)
        ):
            """Get encryption statistics (admin only)."""
            self.request_count += 1
            
            try:
                encryption_stats = self.encryption_manager.get_encryption_stats()
                key_stats = self.key_manager.get_key_statistics()
                
                return {
                    "encryption_manager": encryption_stats,
                    "key_manager": key_stats,
                    "data_protection": {
                        "protected_fields": list(self.data_protection.protected_fields),
                        "protection_active": True
                    },
                    "security_level": "Enhanced AES-256 + bcrypt(12 rounds)",
                    "compliance_status": "FIPS-140-2 Level 1 equivalent"
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to get encryption stats: {e}")
                raise HTTPException(status_code=500, detail="Failed to get encryption stats")
        
        @self.app.post("/api/admin/encryption/rotate-key")
        async def rotate_encryption_key(
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "rotate_encryption_keys")),
            db: AsyncSession = Depends(get_db)
        ):
            """Rotate master encryption key (admin only)."""
            self.request_count += 1
            
            try:
                # Rotate the master key
                new_key = self.encryption_manager.rotate_encryption_key()
                
                # Log critical security event
                security_audit.log_security_event(
                    "ENCRYPTION_KEY_ROTATION",
                    {
                        "admin_user_id": current_user.id,
                        "admin_email": current_user.email,
                        "new_key_id": new_key[:8] + "...",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    "critical"
                )
                
                logger.critical(f"Master encryption key rotated by admin {current_user.email}")
                
                return {
                    "message": "Master encryption key rotated successfully",
                    "new_key_id": new_key[:8] + "...",
                    "rotated_by": current_user.email,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "warning": "All encrypted data can still be decrypted with the new key"
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to rotate encryption key: {e}")
                raise HTTPException(status_code=500, detail="Failed to rotate encryption key")
        
        @self.app.post("/api/admin/api-keys/generate")
        async def generate_api_key(
            key_request: dict,
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "generate_api_keys")),
            db: AsyncSession = Depends(get_db)
        ):
            """Generate API key for user (admin only)."""
            self.request_count += 1
            
            try:
                user_id = key_request.get("user_id")
                scope = key_request.get("scope", "default")
                
                if not user_id:
                    raise HTTPException(status_code=400, detail="user_id is required")
                
                # Verify target user exists
                user_repo = UserRepository(db)
                target_user = await user_repo.get_user_by_id(user_id)
                if not target_user:
                    raise HTTPException(status_code=404, detail="Target user not found")
                
                # Generate API key
                api_key_data = self.key_manager.generate_api_key(user_id, scope)
                
                logger.info(f"API key generated for user {user_id} by admin {current_user.email}")
                
                return {
                    "message": "API key generated successfully",
                    "api_key": api_key_data["api_key"],
                    "key_id": api_key_data["key_id"],
                    "user_id": user_id,
                    "scope": scope,
                    "created_at": api_key_data["created_at"],
                    "generated_by": current_user.email,
                    "warning": "Store this key securely. It cannot be retrieved again."
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to generate API key: {e}")
                raise HTTPException(status_code=500, detail="Failed to generate API key")
        
        @self.app.get("/api/admin/api-keys")
        async def list_api_keys(
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "read_api_keys")),
            db: AsyncSession = Depends(get_db)
        ):
            """List all API keys (admin only)."""
            self.request_count += 1
            
            try:
                key_stats = self.key_manager.get_key_statistics()
                
                # Get key metadata (without actual keys)
                key_list = []
                for key_id, metadata in self.key_manager.key_metadata.items():
                    key_info = {
                        "key_id": key_id,
                        "user_id": metadata["user_id"],
                        "scope": metadata["scope"],
                        "created_at": metadata["created_at"].isoformat(),
                        "last_used": metadata["last_used"].isoformat() if metadata["last_used"] else None,
                        "usage_count": metadata["usage_count"],
                        "is_active": metadata["is_active"]
                    }
                    key_list.append(key_info)
                
                return {
                    "api_keys": key_list,
                    "statistics": key_stats
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to list API keys: {e}")
                raise HTTPException(status_code=500, detail="Failed to list API keys")
        
        @self.app.post("/api/admin/api-keys/{key_id}/revoke")
        async def revoke_api_key(
            key_id: str,
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "revoke_api_keys")),
            db: AsyncSession = Depends(get_db)
        ):
            """Revoke an API key (admin only)."""
            self.request_count += 1
            
            try:
                success = self.key_manager.revoke_api_key(key_id)
                
                if not success:
                    raise HTTPException(status_code=404, detail="API key not found")
                
                logger.warning(f"API key {key_id} revoked by admin {current_user.email}")
                
                return {
                    "message": "API key revoked successfully",
                    "key_id": key_id,
                    "revoked_by": current_user.email,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to revoke API key: {e}")
                raise HTTPException(status_code=500, detail="Failed to revoke API key")
        
        @self.app.post("/api/admin/encryption/cleanup")
        async def cleanup_encryption_artifacts(
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "manage_encryption")),
            db: AsyncSession = Depends(get_db)
        ):
            """Clean up expired encryption artifacts (admin only)."""
            self.request_count += 1
            
            try:
                # Clean up expired JWT tokens
                self.jwt_security.cleanup_expired_tokens()
                
                # Clean up expired sessions
                self.session_manager.cleanup_expired_sessions()
                
                # Rotate expired API keys
                key_rotation_stats = self.key_manager.rotate_expired_keys()
                
                logger.info(f"Encryption cleanup performed by admin {current_user.email}")
                
                return {
                    "message": "Encryption cleanup completed successfully",
                    "jwt_tokens_cleaned": "Completed",
                    "sessions_cleaned": "Completed",
                    "api_keys_rotated": key_rotation_stats,
                    "performed_by": current_user.email,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to cleanup encryption artifacts: {e}")
                raise HTTPException(status_code=500, detail="Failed to cleanup encryption artifacts")

        # TLS Security Validation Endpoints
        @self.app.get("/api/admin/tls/validate")
        async def validate_tls_configuration(
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "validate_tls")),
            db: AsyncSession = Depends(get_db)
        ):
            """Validate TLS configuration for application endpoints (admin only)."""
            self.request_count += 1
            
            try:
                # Validate application's own TLS configuration
                app_tls_validation = validate_application_tls()
                
                # Define endpoints to validate (could be configurable)
                endpoints_to_check = [
                    ("localhost", 8000),  # Application itself
                    # Add more endpoints as needed
                ]
                
                # Create comprehensive TLS report
                tls_report = self.tls_validator.create_tls_security_report(endpoints_to_check)
                
                result = {
                    "application_tls": app_tls_validation,
                    "endpoint_validation": tls_report,
                    "overall_security_status": tls_report["overall_status"],
                    "validation_timestamp": datetime.now(timezone.utc).isoformat(),
                    "validated_by": current_user.email
                }
                
                # Log TLS validation event
                security_audit.log_security_event(
                    "TLS_VALIDATION_PERFORMED",
                    {
                        "admin_user": current_user.email,
                        "endpoints_checked": len(endpoints_to_check),
                        "overall_status": tls_report["overall_status"],
                        "issues_found": tls_report["summary"]["total_issues"]
                    },
                    "info" if tls_report["overall_status"] == "SECURE" else "warning"
                )
                
                logger.info(f"TLS validation performed by admin {current_user.email}")
                
                return result
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to validate TLS configuration: {e}")
                raise HTTPException(status_code=500, detail="Failed to validate TLS configuration")
        
        @self.app.post("/api/admin/tls/validate-endpoint")
        async def validate_external_endpoint(
            endpoint_data: dict,
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "validate_external_tls")),
            db: AsyncSession = Depends(get_db)
        ):
            """Validate TLS configuration for external endpoint (admin only)."""
            self.request_count += 1
            
            try:
                hostname = endpoint_data.get("hostname")
                port = endpoint_data.get("port", 443)
                
                if not hostname:
                    raise HTTPException(status_code=400, detail="hostname is required")
                
                # Validate the external endpoint
                validation_result = self.tls_validator.validate_tls_endpoint(hostname, port)
                
                # Log external TLS validation
                security_audit.log_security_event(
                    "EXTERNAL_TLS_VALIDATION",
                    {
                        "admin_user": current_user.email,
                        "target_hostname": hostname,
                        "target_port": port,
                        "security_grade": validation_result["overall_security_grade"],
                        "issues_count": len(validation_result["issues"])
                    },
                    "info"
                )
                
                logger.info(f"External TLS validation performed by {current_user.email} for {hostname}:{port}")
                
                return {
                    "endpoint": f"{hostname}:{port}",
                    "validation_result": validation_result,
                    "validated_by": current_user.email,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to validate external endpoint: {e}")
                raise HTTPException(status_code=500, detail="Failed to validate external endpoint")
        
        @self.app.get("/api/admin/tls/configuration")
        async def get_tls_configuration(
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "read_tls_config")),
            db: AsyncSession = Depends(get_db)
        ):
            """Get current TLS configuration details (admin only)."""
            self.request_count += 1
            
            try:
                # Get TLS configuration validation
                config_validation = self.tls_config_manager.validate_ssl_configuration()
                
                # Get configuration history
                config_history = self.tls_config_manager.config_history[-10:]  # Last 10 changes
                
                # Get TLS validator statistics
                validator_stats = self.tls_validator.validation_stats
                
                result = {
                    "configuration": config_validation,
                    "configuration_history": config_history,
                    "validator_statistics": validator_stats,
                    "security_recommendations": [
                        "Use TLS 1.2 as minimum version",
                        "Enable TLS 1.3 if possible",
                        "Use strong cipher suites with forward secrecy",
                        "Implement HSTS headers",
                        "Regular certificate rotation"
                    ],
                    "compliance_standards": {
                        "pci_dss": "Requires TLS 1.2+ with strong encryption",
                        "owasp": "Recommends TLS 1.3, HSTS, and certificate pinning",
                        "nist": "Requires FIPS 140-2 validated cryptographic modules"
                    },
                    "retrieved_by": current_user.email,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                return result
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to get TLS configuration: {e}")
                raise HTTPException(status_code=500, detail="Failed to get TLS configuration")
        
        @self.app.post("/api/admin/tls/security-report")
        async def generate_tls_security_report(
            report_request: dict,
            current_user: User = Depends(lambda: self._get_user_with_permission("admin", "generate_tls_reports")),
            db: AsyncSession = Depends(get_db)
        ):
            """Generate comprehensive TLS security report (admin only)."""
            self.request_count += 1
            
            try:
                endpoints = report_request.get("endpoints", [])
                report_type = report_request.get("type", "summary")  # summary, detailed, compliance
                
                if not endpoints:
                    # Use default application endpoints
                    endpoints = [("localhost", 8000)]
                
                # Convert endpoint data to tuples
                endpoint_tuples = []
                for endpoint in endpoints:
                    if isinstance(endpoint, dict):
                        endpoint_tuples.append((endpoint["hostname"], endpoint.get("port", 443)))
                    elif isinstance(endpoint, (list, tuple)):
                        endpoint_tuples.append(tuple(endpoint))
                    else:
                        endpoint_tuples.append((str(endpoint), 443))
                
                # Generate comprehensive report
                security_report = self.tls_validator.create_tls_security_report(endpoint_tuples)
                
                # Add report metadata
                security_report["report_metadata"] = {
                    "generated_by": current_user.email,
                    "report_type": report_type,
                    "endpoints_requested": len(endpoints),
                    "generation_timestamp": datetime.now(timezone.utc).isoformat(),
                    "report_id": f"TLS-RPT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }
                
                # Log report generation
                security_audit.log_security_event(
                    "TLS_SECURITY_REPORT_GENERATED",
                    {
                        "admin_user": current_user.email,
                        "report_type": report_type,
                        "endpoints_analyzed": len(endpoint_tuples),
                        "overall_status": security_report["overall_status"],
                        "report_id": security_report["report_metadata"]["report_id"]
                    },
                    "info"
                )
                
                logger.info(f"TLS security report generated by {current_user.email}")
                
                return security_report
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Failed to generate TLS security report: {e}")
                raise HTTPException(status_code=500, detail="Failed to generate TLS security report")

        @self.app.get("/metrics")
        async def get_prometheus_metrics():
            """Prometheus metrics endpoint."""
            return monitoring_dashboard.get_prometheus_metrics()
        

async def main():
    """Main function to run the database-integrated service."""
    service = PhotoShareDatabaseService()
    
    try:
        logger.info("Starting photo share service", 
                   service_name=service.service_name, 
                   version=service.version,
                   event="service_startup")
        
        # Initialize database
        logger.info("Initializing database connection", event="database_init_start")
        db_initialized = await db_manager.initialize()
        if not db_initialized:
            logger.error("Failed to initialize database", event="database_init_failed")
            return
        
        logger.info("Database initialized successfully", event="database_init_complete")
        
        # Initialize performance optimization
        logger.info("Initializing performance optimization...")
        await service.performance_optimizer.initialize(
            engine=db_manager.engine,
            redis_url="redis://redis-cache:6379"
        )
        
        # Warm cache with essential data
        logger.info("Warming application cache...")
        try:
            async for db in get_db():
                await service.performance_optimizer.warm_application_cache(db)
                break
        except Exception as e:
            logger.warning(f"Cache warming failed during startup: {e}")
            # Continue startup even if cache warming fails
        
        # Register service
        logger.info("Registering service with discovery...")
        await service.service_discovery.register_service()
        
        logger.info("Starting FastAPI server...")
        
        config = uvicorn.Config(
            service.app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("Shutting down photo share service...")
        await service.service_discovery.deregister_service()
        await db_manager.close()
    except Exception as e:
        logger.error(f"Service failed to start: {e}")
        await service.service_discovery.deregister_service()
        await db_manager.close()
        raise

if __name__ == "__main__":
    asyncio.run(main())