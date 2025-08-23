#!/usr/bin/env python3
"""
PhotoShare Application Service - Main Application  
=================================================

This is the main photo sharing application service for the separated architecture.
Integrates with the dedicated authentication service for user management.
"""

import os
import asyncio
import uuid
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy import select
import uvicorn

# Import service components
from app_database import AppDatabaseManager, get_app_db_manager, Photo
from auth_integration import AuthServiceClient, get_current_user, AuthenticatedUser
from file_storage import FileStorageService

# Security middleware
security = HTTPBearer()

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    print("🚀 Starting PhotoShare Application Service...")
    
    # Initialize application database
    app_db_manager = get_app_db_manager()
    await app_db_manager.initialize()
    await app_db_manager.create_tables()
    
    # Initialize auth service client
    auth_client = AuthServiceClient()
    
    # Verify connection to auth service
    try:
        health = await auth_client.health_check()
        if health.get("status") != "healthy":
            print("⚠️  Warning: Auth service is not healthy")
    except Exception as e:
        print(f"⚠️  Warning: Could not connect to auth service: {e}")
    
    print("✅ Application service initialized successfully")
    
    yield
    
    # Cleanup
    print("🔄 Shutting down Application Service...")
    await app_db_manager.close()
    print("✅ Application service stopped")

# Create FastAPI app
app = FastAPI(
    title="PhotoShare Application Service",
    description="Photo sharing application service - integrates with authentication service",
    version="2.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Initialize file storage service
file_storage = FileStorageService()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        app_db_manager = get_app_db_manager()
        app_db_healthy = await app_db_manager.health_check()
        
        # Check auth service health
        auth_healthy = True
        try:
            auth_client = AuthServiceClient()
            auth_health = await auth_client.health_check()
            auth_healthy = auth_health.get("status") == "healthy"
        except:
            auth_healthy = False
        
        overall_status = "healthy" if app_db_healthy and auth_healthy else "unhealthy"
        
        return {
            "status": overall_status,
            "service": "photoshare-app-service",
            "version": "2.3.0",
            "database": "healthy" if app_db_healthy else "unhealthy",
            "auth_service": "healthy" if auth_healthy else "unhealthy"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# API Routes
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "PhotoShare Application Service",
        "version": "2.3.0", 
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "users": "/api/users/*",
            "photos": "/api/photos/*",
            "albums": "/api/albums/*"
        }
    }

# User profile endpoints (protected)
@app.get("/api/users/me")
async def get_current_user_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get current user's profile."""
    return current_user.to_dict()

@app.get("/api/users/{user_uuid}")
async def get_user_profile(user_uuid: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get user profile (public information only unless own profile)."""
    if current_user.uuid == user_uuid or current_user.is_admin():
        # Full profile for own profile or admin
        auth_client = AuthServiceClient()
        user_info = await auth_client.get_user_info(user_uuid)
        return user_info
    else:
        # Public profile only
        return {
            "uuid": user_uuid,
            "display_name": f"User {user_uuid[:8]}",  # Placeholder
            "public_profile": True
        }

# Photo endpoints
@app.post("/api/photos/upload")
async def upload_photo(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    is_public: bool = Form(False),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Upload a new photo."""
    
    # Verify user has permission to upload photos
    if not current_user.has_permission("photos", "create"):
        raise HTTPException(status_code=403, detail="No permission to upload photos")
    
    # File validation
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Size validation (50MB max)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    # Filename validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    try:
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Generate unique filename to avoid conflicts
        file_extension = file.filename.split('.')[-1].lower()
        unique_filename = f"{secrets.token_urlsafe(16)}.{file_extension}"
        
        # Store file using file storage service
        storage_info = await file_storage.store_file(
            user_id=current_user.id or 0,  # fallback to 0 if no id
            filename=unique_filename,
            content=file_content,
            content_type=file.content_type
        )
        
        # Create database record
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            photo = Photo(
                user_uuid=current_user.uuid,
                user_email=current_user.email,
                filename=unique_filename,
                original_filename=file.filename,
                content_type=file.content_type,
                file_size=len(file_content),
                storage_path=storage_info["storage_path"],
                title=title,
                description=description,
                is_public=is_public,
                is_approved=True,  # Auto-approve for now
                moderation_status="approved"
            )
            
            session.add(photo)
            await session.commit()
            await session.refresh(photo)
            
            return {
                "id": photo.id,
                "user_uuid": photo.user_uuid,
                "filename": photo.filename,
                "original_filename": photo.original_filename,
                "title": photo.title,
                "description": photo.description,
                "content_type": photo.content_type,
                "file_size": photo.file_size,
                "is_public": photo.is_public,
                "storage_path": photo.storage_path,
                "created_at": photo.created_at.isoformat(),
                "message": "Photo uploaded successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Public photos must come before {photo_id} route to avoid conflicts
@app.get("/api/photos/public")
async def get_public_photos(page: int = 1, per_page: int = 20):
    """Get public photos (no authentication required)."""
    
    # Pagination validation
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 20
    
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            # Get total count of public photos
            count_query = select(Photo).where(
                Photo.is_public == True,
                Photo.is_approved == True
            )
            result = await session.execute(count_query)
            total = len(result.all())
            
            # Get paginated public photos
            offset = (page - 1) * per_page
            photos_query = (
                select(Photo)
                .where(
                    Photo.is_public == True,
                    Photo.is_approved == True
                )
                .order_by(Photo.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            
            result = await session.execute(photos_query)
            photos = result.scalars().all()
            
            # Return limited info for public photos (privacy protection)
            public_photos = []
            for photo in photos:
                public_photos.append({
                    "id": photo.id,
                    "title": photo.title,
                    "description": photo.description,
                    "filename": photo.filename,
                    "content_type": photo.content_type,
                    "width": photo.width,
                    "height": photo.height,
                    "is_public": photo.is_public,
                    "created_at": photo.created_at.isoformat(),
                    "view_count": photo.view_count,
                    "like_count": photo.like_count
                })
            
            return {
                "photos": public_photos,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch public photos: {str(e)}")

@app.get("/api/photos/{photo_id}")
async def get_photo(photo_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get photo metadata."""
    
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            # Fetch photo from database
            photo_query = select(Photo).where(Photo.id == photo_id)
            result = await session.execute(photo_query)
            photo = result.scalar_one_or_none()
            
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")
            
            # Check permissions
            can_access = (
                photo.user_uuid == current_user.uuid or  # Owner
                photo.is_public or  # Public photo
                current_user.is_admin()  # Admin
            )
            
            if not can_access:
                raise HTTPException(status_code=403, detail="No permission to view this photo")
            
            # Increment view count if not owner
            if photo.user_uuid != current_user.uuid:
                photo.view_count += 1
                await session.commit()
            
            return photo.to_dict()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch photo: {str(e)}")

@app.get("/api/photos/")
async def get_user_photos(
    page: int = 1,
    per_page: int = 20,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get current user's photos."""
    
    if not current_user.has_permission("photos", "read"):
        raise HTTPException(status_code=403, detail="No permission to view photos")
    
    # Pagination validation
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 20
    
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            # Get total count
            count_query = select(Photo).where(Photo.user_uuid == current_user.uuid)
            result = await session.execute(count_query)
            total = len(result.all())
            
            # Get paginated photos
            offset = (page - 1) * per_page
            photos_query = (
                select(Photo)
                .where(Photo.user_uuid == current_user.uuid)
                .order_by(Photo.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            
            result = await session.execute(photos_query)
            photos = result.scalars().all()
            
            return {
                "photos": [photo.to_dict() for photo in photos],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch photos: {str(e)}")

# System endpoints for service-to-service communication
@app.get("/api/system/auth-health")
async def check_auth_service_health():
    """Check auth service health (internal endpoint)."""
    try:
        auth_client = AuthServiceClient()
        health = await auth_client.health_check()
        return {
            "auth_service_status": health.get("status", "unknown"),
            "checked_at": "2025-01-01T00:00:00Z"  # Placeholder
        }
    except Exception as e:
        return {
            "auth_service_status": "unhealthy",
            "error": str(e),
            "checked_at": "2025-01-01T00:00:00Z"  # Placeholder
        }

if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )