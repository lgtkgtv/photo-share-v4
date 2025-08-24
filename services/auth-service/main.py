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
    
    # Initialize RBAC system - CRITICAL for proper permissions
    print("🔐 Initializing RBAC system...")
    try:
        from setup_rbac import setup_default_permissions, setup_default_roles, assign_role_permissions, assign_default_role_to_users
        
        # Setup permissions
        print("  📋 Setting up permissions...")
        await setup_default_permissions()
        
        # Setup roles  
        print("  👥 Setting up roles...")
        await setup_default_roles()
        
        # Assign permissions to roles
        print("  🔗 Assigning permissions to roles...")
        await assign_role_permissions()
        
        # Assign default roles to existing users
        print("  👤 Assigning default roles to existing users...")
        await assign_default_role_to_users()
        
        print("✅ RBAC system initialized successfully")
        
    except Exception as e:
        print(f"❌ RBAC initialization failed: {e}")
        print("⚠️  Authentication service will start but user registration may fail")
        print("   Run 'python setup_rbac.py' manually to fix this issue")
    
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