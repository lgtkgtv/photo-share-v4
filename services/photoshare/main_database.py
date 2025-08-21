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
    UserRepository, PhotoRepository, SessionRepository, EmailVerificationRepository
)
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
    require_rate_limit, validate_file_security, JWTSecurity
)
from performance_simple import (
    performance_optimizer, cache_result, monitor_query, optimized_db_ops
)
from monitoring import (
    monitoring_dashboard, record_request_metric, record_database_metric,
    record_cache_metric, record_error_metric, record_auth_metric
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

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
        
        # Initialize performance optimization
        self.performance_optimizer = performance_optimizer
        
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
        """Setup FastAPI middleware."""
        # Add security middleware first with enhanced validation
        self.app.add_middleware(SecurityMiddleware, rate_limiter=rate_limiter, request_validator=request_validator)
        
        # Then CORS middleware with secure configuration
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    
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
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def _create_access_token(self, user_id: int, email: str) -> str:
        """Create JWT access token."""
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    async def _get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security),
                               db: AsyncSession = Depends(get_db)) -> User:
        """Get current user from JWT token."""
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: int = int(payload.get("sub"))
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
                
            user_repo = UserRepository(db)
            user = await user_repo.get_user_by_id(user_id)
            if user is None:
                raise HTTPException(status_code=401, detail="User not found")
                
            return user
            
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
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
                    "platform": "/api/platform/"
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
                
                logger.info(f"User registered: {user_data.email}")
                
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
                
                # Get user by email
                user = await user_repo.get_user_by_email(username)
                if not user or not self._verify_password(password, user.password_hash):
                    raise AuthenticationErrorHandler.handle_invalid_credentials()
                
                if not user.is_active:
                    raise HTTPException(status_code=401, detail="Account deactivated")
                
                # Create JWT token
                access_token = self._create_access_token(user.id, user.email)
                
                # Store session in database
                session_repo = SessionRepository(db)
                await session_repo.create_session(user.id, access_token)
                
                logger.info(f"User logged in: {username}")
                
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
            """Upload photo with file storage service."""
            self.request_count += 1
            
            try:
                # Read file content
                file_content = await file.read()
                
                # Enhanced file security validation
                await validate_file_security(file_content, file.content_type or "application/octet-stream", file.filename)
                
                # Sanitize filename
                safe_filename = input_validator.sanitize_filename(file.filename or "upload")
                
                # Generate unique filename
                timestamp = int(time.time())
                file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
                filename = f"photo_{current_user.id}_{timestamp}_{secrets.token_hex(8)}{file_extension}"
                
                # Store file using file storage service
                storage_info = await self.file_storage.store_file(
                    user_id=current_user.id,
                    filename=filename,
                    content=file_content,
                    content_type=file.content_type or "application/octet-stream"
                )
                
                # Create photo record in database
                photo_repo = PhotoRepository(db)
                photo = await photo_repo.create_photo(
                    user_id=current_user.id,
                    filename=filename,
                    original_filename=file.filename or "unknown",
                    content_type=file.content_type or "application/octet-stream",
                    file_size=storage_info["file_size"],
                    storage_path=storage_info["storage_path"],
                    title=title,
                    description=description,
                    is_public=is_public
                )
                
                logger.info(f"Photo uploaded and stored: {file.filename} for user {current_user.email}")
                
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
        
        @self.app.get("/metrics")
        async def get_prometheus_metrics():
            """Prometheus metrics endpoint."""
            return monitoring_dashboard.get_prometheus_metrics()
        

async def main():
    """Main function to run the database-integrated service."""
    service = PhotoShareDatabaseService()
    
    try:
        logger.info(f"Starting {service.service_name} v{service.version}")
        
        # Initialize database
        logger.info("Initializing database connection...")
        db_initialized = await db_manager.initialize()
        if not db_initialized:
            logger.error("Failed to initialize database")
            return
        
        logger.info("Database initialized successfully")
        
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