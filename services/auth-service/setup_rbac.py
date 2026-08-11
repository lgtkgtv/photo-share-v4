#!/usr/bin/env python3
"""
RBAC Setup Script
=================

Initialize the authentication service with default roles and permissions
for the PhotoShare application.
"""

import asyncio
from auth_database import auth_db_manager, Role, Permission, RolePermission, UserRole, User
from sqlalchemy import select

async def setup_default_permissions():
    """Create default permissions for PhotoShare."""
    
    default_permissions = [
        # Photo permissions
        ("photos:create", "photos", "create", "Upload and create photos"),
        ("photos:read", "photos", "read", "View own photos"),
        ("photos:read_all", "photos", "read_all", "View all photos (admin)"),
        ("photos:update", "photos", "update", "Edit own photos"),
        ("photos:update_all", "photos", "update_all", "Edit any photos (admin)"),
        ("photos:delete", "photos", "delete", "Delete own photos"),
        ("photos:delete_all", "photos", "delete_all", "Delete any photos (admin)"),
        ("photos:manage", "photos", "manage", "Full photo management"),

        # Album permissions (routers/albums.py) -- added when the Phase 1 product
        # API shipped; without these, no real user (not even admin) can create an
        # album, since AuthenticatedUser.has_permission("albums", "write") checks
        # this exact permission string against the roles seeded here.
        ("albums:write", "albums", "write", "Create and manage own albums"),
        ("albums:read", "albums", "read", "View albums"),

        # User permissions
        ("users:read", "users", "read", "View user profiles"),
        ("users:update", "users", "update", "Update own profile"),
        ("users:update_all", "users", "update_all", "Update any user profile (admin)"),
        ("users:delete", "users", "delete", "Delete own account"),
        ("users:delete_all", "users", "delete_all", "Delete any user account (admin)"),
        ("users:manage", "users", "manage", "Full user management"),
        
        # Admin permissions
        ("admin:users", "admin", "users", "User administration"),
        ("admin:content", "admin", "content", "Content moderation"),
        ("admin:system", "admin", "system", "System administration"),
        ("admin:roles", "admin", "roles", "Role and permission management"),
        
        # System permissions
        ("system:health", "system", "health", "View system health"),
        ("system:metrics", "system", "metrics", "View system metrics"),
        ("system:logs", "system", "logs", "View system logs"),
    ]
    
    async with auth_db_manager.session_factory() as session:
        created_permissions = []
        
        for perm_name, resource, action, description in default_permissions:
            # Check if permission already exists
            result = await session.execute(select(Permission).where(Permission.name == perm_name))
            existing = result.scalar_one_or_none()
            
            if not existing:
                permission = Permission(
                    name=perm_name,
                    resource=resource,
                    action=action,
                    description=description,
                    category="user" if resource == "users" else 
                            "content" if resource == "photos" else
                            "admin" if resource == "admin" else "system",
                    is_sensitive=resource in ["admin", "system"] or action.endswith("_all")
                )
                session.add(permission)
                created_permissions.append(perm_name)
        
        await session.commit()
        print(f"✅ Created {len(created_permissions)} permissions")
        return created_permissions

async def setup_default_roles():
    """Create default roles for PhotoShare."""
    
    default_roles = [
        ("user", "Standard User", "Regular user with basic permissions", 0, False),
        ("premium", "Premium User", "Premium user with enhanced permissions", 1, False),
        ("moderator", "Content Moderator", "Can moderate content and manage users", 2, False),
        ("admin", "Administrator", "Full system administration", 3, True),
        ("superadmin", "Super Administrator", "Ultimate system control", 4, True),
    ]
    
    async with auth_db_manager.session_factory() as session:
        created_roles = []
        
        for role_name, display_name, description, level, is_system in default_roles:
            # Check if role already exists
            result = await session.execute(select(Role).where(Role.name == role_name))
            existing = result.scalar_one_or_none()
            
            if not existing:
                role = Role(
                    name=role_name,
                    description=f"{display_name}: {description}",
                    level=level,
                    is_active=True,
                    is_system_role=is_system
                )
                session.add(role)
                created_roles.append(role_name)
        
        await session.commit()
        print(f"✅ Created {len(created_roles)} roles")
        return created_roles

async def assign_role_permissions():
    """Assign permissions to roles based on hierarchy."""
    
    role_permissions_map = {
        "user": [
            "photos:create", "photos:read", "photos:update", "photos:delete",
            "albums:write", "albums:read",
            "users:read", "users:update", "users:delete",
            "system:health"
        ],
        "premium": [
            # All user permissions plus enhanced features
            "photos:create", "photos:read", "photos:update", "photos:delete",
            "albums:write", "albums:read",
            "users:read", "users:update", "users:delete",
            "system:health", "system:metrics"
        ],
        "moderator": [
            # All premium permissions plus content moderation
            "photos:create", "photos:read", "photos:update", "photos:delete",
            "photos:read_all", "photos:update_all",
            "albums:write", "albums:read",
            "users:read", "users:update", "users:delete", "users:update_all",
            "admin:content", "system:health", "system:metrics"
        ],
        "admin": [
            # All permissions except super admin functions
            "photos:create", "photos:read", "photos:update", "photos:delete",
            "photos:read_all", "photos:update_all", "photos:delete_all", "photos:manage",
            "albums:write", "albums:read",
            "users:read", "users:update", "users:delete",
            "users:update_all", "users:delete_all", "users:manage",
            "admin:users", "admin:content", "admin:system", "admin:roles",
            "system:health", "system:metrics", "system:logs"
        ],
        "superadmin": [
            # All permissions (will be assigned all existing permissions)
            "*"  # Special marker for all permissions
        ]
    }
    
    async with auth_db_manager.session_factory() as session:
        assigned_count = 0
        
        for role_name, permission_names in role_permissions_map.items():
            # Get role
            role_result = await session.execute(select(Role).where(Role.name == role_name))
            role = role_result.scalar_one_or_none()
            
            if not role:
                print(f"⚠️  Role {role_name} not found, skipping...")
                continue
            
            # Get all permissions if superadmin
            if "*" in permission_names:
                perm_result = await session.execute(select(Permission))
                permissions = perm_result.scalars().all()
            else:
                # Get specific permissions
                permissions = []
                for perm_name in permission_names:
                    perm_result = await session.execute(
                        select(Permission).where(Permission.name == perm_name)
                    )
                    permission = perm_result.scalar_one_or_none()
                    if permission:
                        permissions.append(permission)
                    else:
                        print(f"⚠️  Permission {perm_name} not found")
            
            # Assign permissions to role
            for permission in permissions:
                # Check if already assigned
                rp_result = await session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == permission.id
                    )
                )
                existing = rp_result.scalar_one_or_none()
                
                if not existing:
                    role_permission = RolePermission(
                        role_id=role.id,
                        permission_id=permission.id
                    )
                    session.add(role_permission)
                    assigned_count += 1
        
        await session.commit()
        print(f"✅ Assigned {assigned_count} role-permission mappings")

async def assign_default_role_to_users():
    """Assign default 'user' role to existing users without roles."""
    
    async with auth_db_manager.session_factory() as session:
        # Get the 'user' role
        role_result = await session.execute(select(Role).where(Role.name == "user"))
        user_role = role_result.scalar_one_or_none()
        
        if not user_role:
            print("⚠️  Default 'user' role not found")
            return
        
        # Get all users without roles
        users_result = await session.execute(select(User))
        all_users = users_result.scalars().all()
        
        assigned_count = 0
        for user in all_users:
            # Check if user has any roles
            ur_result = await session.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.is_active == True
                )
            )
            has_roles = ur_result.scalar_one_or_none() is not None
            
            if not has_roles:
                user_role_assignment = UserRole(
                    user_id=user.id,
                    role_id=user_role.id,
                    is_active=True
                )
                session.add(user_role_assignment)
                assigned_count += 1
        
        await session.commit()
        print(f"✅ Assigned default role to {assigned_count} users")

async def main():
    """Main setup function."""
    print("🚀 Setting up RBAC for PhotoShare Authentication Service")
    print("=" * 60)
    
    try:
        # Initialize database if needed
        await auth_db_manager.initialize()
        await auth_db_manager.create_tables()
        
        # Setup permissions
        print("\n📋 Creating default permissions...")
        await setup_default_permissions()
        
        # Setup roles  
        print("\n👥 Creating default roles...")
        await setup_default_roles()
        
        # Assign permissions to roles
        print("\n🔗 Assigning permissions to roles...")
        await assign_role_permissions()
        
        # Assign default roles to existing users
        print("\n👤 Assigning default roles to existing users...")
        await assign_default_role_to_users()
        
        print("\n" + "=" * 60)
        print("✅ RBAC setup completed successfully!")
        print("\nDefault roles created:")
        print("  • user: Basic photo sharing permissions")
        print("  • premium: Enhanced user features")
        print("  • moderator: Content moderation capabilities")
        print("  • admin: Full system administration")  
        print("  • superadmin: Ultimate system control")
        
    except Exception as e:
        print(f"❌ RBAC setup failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())