#!/usr/bin/env python3
"""
PhotoShare Authentication Service - Main Application
===================================================

This is the dedicated authentication service for the separated architecture.
Handles user registration, login, 2FA, SSO, and permission management.
"""

import os
import uvicorn
from contextlib import asynccontextmanager
from auth_service import AuthenticationService
from auth_database import get_db_manager
from sso_providers import SSOProviderManager

# Application lifespan management
@asynccontextmanager
async def lifespan(app):
    """Manage application startup and shutdown."""
    print("🚀 Starting PhotoShare Authentication Service...")
    
    # Initialize database
    db_manager = get_db_manager()
    await db_manager.initialize()
    await db_manager.create_tables()
    
    # Note: Database initialization is handled by the auth_service itself
    
    # Initialize SSO providers
    sso_manager = SSOProviderManager()
    await sso_manager.initialize()
    
    print("✅ Authentication service initialized successfully")
    
    yield
    
    # Cleanup
    print("🔄 Shutting down Authentication Service...")
    await db_manager.close()
    print("✅ Authentication service stopped")

# Create the AuthenticationService with lifespan management
auth_service = AuthenticationService(lifespan=lifespan)
app = auth_service.app

if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )