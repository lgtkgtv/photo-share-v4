#!/usr/bin/env python3
"""
RBAC Initialization Script
========================

Initialize default roles and permissions for the PhotoShare service.
This script sets up basic security roles and permissions required for
the Role-Based Access Control system.
"""

import asyncio
import logging
from datetime import datetime, timezone

from database import (
    db_manager, 
    RoleRepository, PermissionRepository, RolePermissionRepository, UserRoleRepository,
    UserRepository
)

logger = logging.getLogger(__name__)

# Default roles to create
DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "System administrator with full access"
    },
    {
        "name": "moderator", 
        "description": "Content moderator with limited admin access"
    },
    {
        "name": "user",
        "description": "Standard user with basic photo sharing permissions"
    },
    {
        "name": "viewer",
        "description": "Read-only access to public content"
    }
]

# Default permissions to create
DEFAULT_PERMISSIONS = [
    # Admin permissions
    {"name": "admin:create_role", "resource": "admin", "action": "create_role", "description": "Create new roles"},
    {"name": "admin:read_roles", "resource": "admin", "action": "read_roles", "description": "View all roles"},
    {"name": "admin:update_role", "resource": "admin", "action": "update_role", "description": "Modify existing roles"},
    {"name": "admin:delete_role", "resource": "admin", "action": "delete_role", "description": "Remove roles"},
    {"name": "admin:create_permission", "resource": "admin", "action": "create_permission", "description": "Create new permissions"},
    {"name": "admin:read_permissions", "resource": "admin", "action": "read_permissions", "description": "View all permissions"},
    {"name": "admin:manage_role_permissions", "resource": "admin", "action": "manage_role_permissions", "description": "Grant/revoke permissions to roles"},
    {"name": "admin:assign_user_roles", "resource": "admin", "action": "assign_user_roles", "description": "Assign roles to users"},
    {"name": "admin:manage_users", "resource": "admin", "action": "manage_users", "description": "Manage user accounts"},
    
    # Photo permissions
    {"name": "photos:read", "resource": "photos", "action": "read", "description": "View photos"},
    {"name": "photos:write", "resource": "photos", "action": "write", "description": "Upload and edit photos"},
    {"name": "photos:delete", "resource": "photos", "action": "delete", "description": "Delete photos"},
    {"name": "photos:moderate", "resource": "photos", "action": "moderate", "description": "Moderate photo content"},
    {"name": "photos:read_all", "resource": "photos", "action": "read_all", "description": "View all photos including private"},
    
    # User permissions  
    {"name": "users:read_profile", "resource": "users", "action": "read_profile", "description": "View user profiles"},
    {"name": "users:update_profile", "resource": "users", "action": "update_profile", "description": "Update own profile"},
    {"name": "users:read_all_profiles", "resource": "users", "action": "read_all_profiles", "description": "View all user profiles"},
    
    # Comment permissions
    {"name": "comments:read", "resource": "comments", "action": "read", "description": "View comments"},
    {"name": "comments:write", "resource": "comments", "action": "write", "description": "Post comments"},
    {"name": "comments:delete", "resource": "comments", "action": "delete", "description": "Delete own comments"},
    {"name": "comments:moderate", "resource": "comments", "action": "moderate", "description": "Moderate all comments"},
    
    # System permissions
    {"name": "system:read_stats", "resource": "system", "action": "read_stats", "description": "View system statistics"},
    {"name": "system:read_logs", "resource": "system", "action": "read_logs", "description": "View system logs"},
]

# Role-Permission mappings
ROLE_PERMISSIONS = {
    "admin": [
        # Full admin access
        "admin:create_role", "admin:read_roles", "admin:update_role", "admin:delete_role",
        "admin:create_permission", "admin:read_permissions", "admin:manage_role_permissions",
        "admin:assign_user_roles", "admin:manage_users",
        # Full photo access
        "photos:read", "photos:write", "photos:delete", "photos:moderate", "photos:read_all",
        # Full user access
        "users:read_profile", "users:update_profile", "users:read_all_profiles",
        # Full comment access
        "comments:read", "comments:write", "comments:delete", "comments:moderate",
        # System access
        "system:read_stats", "system:read_logs"
    ],
    "moderator": [
        # Limited admin access
        "admin:read_roles", "admin:read_permissions",
        # Photo moderation
        "photos:read", "photos:moderate", "photos:read_all",
        # User profile access
        "users:read_profile", "users:read_all_profiles",
        # Comment moderation
        "comments:read", "comments:moderate",
        # System stats
        "system:read_stats"
    ],
    "user": [
        # Basic photo access
        "photos:read", "photos:write", "photos:delete",
        # Profile management
        "users:read_profile", "users:update_profile", 
        # Comments
        "comments:read", "comments:write", "comments:delete"
    ],
    "viewer": [
        # Read-only access
        "photos:read",
        "users:read_profile",
        "comments:read"
    ]
}

async def init_rbac_system():
    """Initialize the RBAC system with default roles and permissions."""
    try:
        # Initialize database connection
        if not await db_manager.initialize():
            logger.error("Failed to initialize database")
            return False
        
        async for db in db_manager.get_session():
            role_repo = RoleRepository(db)
            permission_repo = PermissionRepository(db)
            role_permission_repo = RolePermissionRepository(db)
            
            logger.info("Starting RBAC initialization...")
            
            # Create default roles
            created_roles = {}
            for role_data in DEFAULT_ROLES:
                try:
                    # Check if role already exists
                    existing_role = await role_repo.get_role_by_name(role_data["name"])
                    if existing_role:
                        logger.info(f"Role '{role_data['name']}' already exists")
                        created_roles[role_data["name"]] = existing_role
                    else:
                        role = await role_repo.create_role(
                            name=role_data["name"],
                            description=role_data["description"]
                        )
                        created_roles[role_data["name"]] = role
                        logger.info(f"Created role: {role.name}")
                except Exception as e:
                    logger.error(f"Failed to create role {role_data['name']}: {e}")
            
            # Create default permissions  
            created_permissions = {}
            for perm_data in DEFAULT_PERMISSIONS:
                try:
                    # Check if permission already exists
                    existing_perm = await permission_repo.get_permission_by_name(perm_data["name"])
                    if existing_perm:
                        logger.info(f"Permission '{perm_data['name']}' already exists")
                        created_permissions[perm_data["name"]] = existing_perm
                    else:
                        permission = await permission_repo.create_permission(
                            name=perm_data["name"],
                            resource=perm_data["resource"],
                            action=perm_data["action"],
                            description=perm_data.get("description")
                        )
                        created_permissions[perm_data["name"]] = permission
                        logger.info(f"Created permission: {permission.name}")
                except Exception as e:
                    logger.error(f"Failed to create permission {perm_data['name']}: {e}")
            
            # Assign permissions to roles
            for role_name, permission_names in ROLE_PERMISSIONS.items():
                if role_name in created_roles:
                    role = created_roles[role_name]
                    
                    # Get existing permissions for this role
                    existing_perms = await role_permission_repo.get_role_permissions(role.id)
                    existing_perm_names = {perm.name for perm in existing_perms}
                    
                    for perm_name in permission_names:
                        if perm_name in created_permissions and perm_name not in existing_perm_names:
                            try:
                                permission = created_permissions[perm_name]
                                await role_permission_repo.grant_permission_to_role(
                                    role.id, permission.id
                                )
                                logger.info(f"Granted '{perm_name}' to role '{role_name}'")
                            except Exception as e:
                                logger.error(f"Failed to grant permission {perm_name} to role {role_name}: {e}")
                        elif perm_name in existing_perm_names:
                            logger.info(f"Permission '{perm_name}' already granted to role '{role_name}'")
            
            logger.info("RBAC initialization completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"RBAC initialization failed: {e}")
        return False
    finally:
        await db_manager.close()

async def assign_admin_role_to_user(email: str):
    """Assign admin role to a specific user by email."""
    try:
        if not await db_manager.initialize():
            logger.error("Failed to initialize database") 
            return False
            
        async for db in db_manager.get_session():
            user_repo = UserRepository(db)
            role_repo = RoleRepository(db)
            user_role_repo = UserRoleRepository(db)
            
            # Find user
            user = await user_repo.get_user_by_email(email)
            if not user:
                logger.error(f"User with email {email} not found")
                return False
            
            # Find admin role
            admin_role = await role_repo.get_role_by_name("admin")
            if not admin_role:
                logger.error("Admin role not found")
                return False
            
            # Check if user already has admin role
            user_roles = await user_role_repo.get_user_roles(user.id)
            if any(role.name == "admin" for role in user_roles):
                logger.info(f"User {email} already has admin role")
                return True
            
            # Assign admin role
            await user_role_repo.assign_role_to_user(user.id, admin_role.id)
            logger.info(f"Admin role assigned to user {email}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to assign admin role: {e}")
        return False
    finally:
        await db_manager.close()

async def main():
    """Main function to run RBAC initialization."""
    logging.basicConfig(level=logging.INFO)
    
    print("PhotoShare RBAC Initialization")
    print("==============================")
    
    # Initialize RBAC system
    success = await init_rbac_system()
    
    if success:
        print("✓ RBAC system initialized successfully")
        
        # Optional: Assign admin role to first user
        admin_email = input("Enter email to assign admin role (or press Enter to skip): ").strip()
        if admin_email:
            admin_success = await assign_admin_role_to_user(admin_email)
            if admin_success:
                print(f"✓ Admin role assigned to {admin_email}")
            else:
                print(f"✗ Failed to assign admin role to {admin_email}")
        
        print("\nRBAC Setup Complete!")
        print("Available roles: admin, moderator, user, viewer")
        print("Admin endpoints available at /api/admin/*")
    else:
        print("✗ RBAC initialization failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))