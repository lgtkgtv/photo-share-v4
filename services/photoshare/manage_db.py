#!/usr/bin/env python3
"""
Database Management Script for Photo Share Service
==================================================

This script provides database migration and management utilities.
"""

import asyncio
import os
import sys
from pathlib import Path
from alembic.config import Config
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine
from database import Base, db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations and migrations."""
    
    def __init__(self):
        self.alembic_cfg = Config("alembic.ini")
        
    async def init_database(self):
        """Initialize database with tables (non-Alembic method)."""
        try:
            await db_manager.initialize()
            logger.info("✅ Database initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    def run_migrations(self, target: str = "head"):
        """Run Alembic migrations."""
        try:
            logger.info(f"🔄 Running migrations to {target}...")
            command.upgrade(self.alembic_cfg, target)
            logger.info("✅ Migrations completed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def create_migration(self, message: str):
        """Create a new migration."""
        try:
            logger.info(f"📝 Creating migration: {message}")
            command.revision(self.alembic_cfg, message=message, autogenerate=True)
            logger.info("✅ Migration created successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Migration creation failed: {e}")
            return False
    
    def show_current_revision(self):
        """Show current database revision."""
        try:
            command.current(self.alembic_cfg)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to show current revision: {e}")
            return False
    
    def show_migration_history(self):
        """Show migration history."""
        try:
            command.history(self.alembic_cfg)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to show migration history: {e}")
            return False
    
    def downgrade_migration(self, target: str = "-1"):
        """Downgrade database migration."""
        try:
            logger.warning(f"⚠️  Downgrading database to {target}")
            command.downgrade(self.alembic_cfg, target)
            logger.info("✅ Downgrade completed")
            return True
        except Exception as e:
            logger.error(f"❌ Downgrade failed: {e}")
            return False
    
    async def reset_database(self):
        """Reset database (drops and recreates all tables)."""
        try:
            logger.warning("⚠️  Resetting database - ALL DATA WILL BE LOST!")
            
            # Drop all tables
            await db_manager.initialize()
            async with db_manager.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                logger.info("🗑️  Dropped all tables")
                
                # Recreate tables
                await conn.run_sync(Base.metadata.create_all)
                logger.info("🔨 Created all tables")
            
            logger.info("✅ Database reset completed")
            return True
        except Exception as e:
            logger.error(f"❌ Database reset failed: {e}")
            return False
    
    async def check_database_health(self):
        """Check database connection and health."""
        try:
            await db_manager.initialize()
            
            # Test connection
            async with db_manager.session_factory() as session:
                result = await session.execute("SELECT 1")
                test_value = result.scalar()
                
            if test_value == 1:
                logger.info("✅ Database connection healthy")
                return True
            else:
                logger.error("❌ Database connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
            return False

async def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("""
Photo Share Database Management Tool

Usage:
    python manage_db.py <command> [options]

Commands:
    init                    Initialize database (create tables)
    migrate [target]        Run migrations (default: head)
    create <message>        Create new migration
    current                 Show current revision
    history                 Show migration history  
    downgrade [target]      Downgrade migration (default: -1)
    reset                   Reset database (DANGEROUS - drops all data)
    health                  Check database health

Examples:
    python manage_db.py init
    python manage_db.py migrate
    python manage_db.py create "Add user profile table"
    python manage_db.py downgrade
    python manage_db.py reset
        """)
        return
    
    command = sys.argv[1].lower()
    db_mgr = DatabaseManager()
    
    if command == "init":
        await db_mgr.init_database()
        
    elif command == "migrate":
        target = sys.argv[2] if len(sys.argv) > 2 else "head"
        db_mgr.run_migrations(target)
        
    elif command == "create":
        if len(sys.argv) < 3:
            print("Error: Migration message required")
            return
        message = " ".join(sys.argv[2:])
        db_mgr.create_migration(message)
        
    elif command == "current":
        db_mgr.show_current_revision()
        
    elif command == "history":
        db_mgr.show_migration_history()
        
    elif command == "downgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "-1"
        db_mgr.downgrade_migration(target)
        
    elif command == "reset":
        # Confirmation for dangerous operation
        confirm = input("⚠️  This will DELETE ALL DATA. Type 'CONFIRM' to proceed: ")
        if confirm == "CONFIRM":
            await db_mgr.reset_database()
        else:
            print("❌ Reset cancelled")
            
    elif command == "health":
        await db_mgr.check_database_health()
        
    else:
        print(f"Unknown command: {command}")
        print("Use 'python manage_db.py' without arguments to see help")

if __name__ == "__main__":
    asyncio.run(main())