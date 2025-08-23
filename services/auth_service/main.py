#!/usr/bin/env python3
"""
PhotoShare Authentication Service - Main Application
===================================================

This is the dedicated authentication service for the separated architecture.
Handles user registration, login, 2FA, SSO, and permission management.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn

# Import service components
from auth_database import AuthDatabaseManager, get_db_manager
from auth_service import AuthServiceManager
from sso_providers import SSOProviderManager
from two_factor_auth import get_twofa_manager

# Security middleware
security = HTTPBearer()

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    print("🚀 Starting PhotoShare Authentication Service...")
    
    # Initialize database
    db_manager = get_db_manager()
    await db_manager.initialize()
    await db_manager.create_tables()
    
    # Initialize SSO providers
    sso_manager = SSOProviderManager()
    await sso_manager.initialize()
    
    print("✅ Authentication service initialized successfully")
    
    yield
    
    # Cleanup
    print("🔄 Shutting down Authentication Service...")
    await db_manager.close()
    print("✅ Authentication service stopped")

# Create FastAPI app
app = FastAPI(
    title="PhotoShare Authentication Service",
    description="Dedicated authentication service for PhotoShare - handles SSO, 2FA, and RBAC",
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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db_manager = get_db_manager()
        db_healthy = await db_manager.health_check()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "service": "photoshare-auth-service",
            "version": "2.3.0",
            "database": "healthy" if db_healthy else "unhealthy"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# API Routes
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "PhotoShare Authentication Service",
        "version": "2.3.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "auth": "/api/auth/*",
            "sso": "/api/sso/*",
            "2fa": "/api/2fa/*"
        }
    }

# Include auth service routes
from auth_service import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])

# Include SSO routes  
@app.get("/api/sso/providers")
async def get_sso_providers():
    """Get available SSO providers."""
    sso_manager = SSOProviderManager()
    providers = await sso_manager.get_provider_list()
    return providers

# Include 2FA routes
@app.get("/api/2fa/methods")
async def get_2fa_methods():
    """Get available 2FA methods."""
    twofa_manager = get_twofa_manager()
    methods = await twofa_manager.get_2fa_methods_for_user("demo")  # Demo endpoint
    return {"methods": methods}

if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )