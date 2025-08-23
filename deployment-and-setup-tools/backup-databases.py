#!/usr/bin/env python3
"""
Encrypted Database Backup System
================================

Creates encrypted backups of PostgreSQL databases with proper security.
"""

import os
import subprocess
import sys
import json
import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
import logging


# Setup logging
log_dir = os.getenv("LOG_DIR", "/app/logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "backup.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class EncryptedDatabaseBackup:
    """Encrypted database backup manager."""
    
    def __init__(self):
        # Use current directory in development, /app in production
        default_backup_dir = "./backups" if not os.path.exists("/app") else "/app/backups"
        default_key_file = "./secure/backup_key.txt" if not os.path.exists("/secure") else "/secure/backup_key.txt"
        
        self.backup_dir = Path(os.getenv("BACKUP_DIR", default_backup_dir))
        self.retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        self.encryption_key_file = os.getenv("BACKUP_ENCRYPTION_KEY_FILE", default_key_file)
        
        # Database configurations
        self.databases = {
            "auth": {
                "host": os.getenv("AUTH_DB_HOST", "auth-db"),
                "port": os.getenv("AUTH_DB_PORT", "5432"),
                "name": os.getenv("AUTH_DB_NAME", "photo_share_auth"),
                "user": os.getenv("AUTH_DB_USER", "auth_user"),
                "password": os.getenv("AUTH_DB_PASSWORD", "auth_secure_password_here")
            },
            "app": {
                "host": os.getenv("APP_DB_HOST", "app-db"),
                "port": os.getenv("APP_DB_PORT", "5432"),
                "name": os.getenv("APP_DB_NAME", "photo_share_app"),
                "user": os.getenv("APP_DB_USER", "app_user"),
                "password": os.getenv("APP_DB_PASSWORD", "app_secure_password_here")
            }
        }
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption
        self._ensure_encryption_key()
    
    def _ensure_encryption_key(self):
        """Ensure encryption key exists or create it."""
        key_path = Path(self.encryption_key_file)
        
        if not key_path.exists():
            logger.info("Generating new backup encryption key...")
            
            # Create secure key directory
            key_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            
            # Generate 256-bit encryption key
            encryption_key = secrets.token_urlsafe(32)
            
            # Write key with restrictive permissions
            with open(key_path, 'w') as f:
                f.write(encryption_key)
            
            # Set restrictive permissions (owner read-only)
            os.chmod(key_path, 0o600)
            logger.info(f"Backup encryption key generated and saved to {key_path}")
        else:
            logger.info(f"Using existing backup encryption key from {key_path}")
    
    def _get_encryption_key(self) -> str:
        """Get the encryption key."""
        try:
            with open(self.encryption_key_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Backup encryption key not found at {self.encryption_key_file}")
            raise
        except PermissionError:
            logger.error(f"Cannot read backup encryption key at {self.encryption_key_file}")
            raise
    
    def _run_command(self, cmd: str, env: Optional[Dict] = None) -> tuple:
        """Run shell command securely."""
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=300,  # 5 minutes timeout
                env=env
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {cmd}")
            return 1, "", "Command timed out"
        except Exception as e:
            logger.error(f"Command failed: {cmd}, Error: {e}")
            return 1, "", str(e)
    
    def backup_database(self, db_name: str, db_config: Dict) -> Optional[str]:
        """Create encrypted backup of a database."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{db_name}_backup_{timestamp}.sql.gpg"
        backup_path = self.backup_dir / backup_filename
        
        logger.info(f"Starting backup of {db_name} database...")
        
        # Create PostgreSQL environment
        pg_env = os.environ.copy()
        pg_env.update({
            'PGHOST': db_config['host'],
            'PGPORT': db_config['port'],
            'PGUSER': db_config['user'],
            'PGPASSWORD': db_config['password'],
            'PGDATABASE': db_config['name']
        })
        
        # Test database connection first
        test_cmd = f"pg_isready -h {db_config['host']} -p {db_config['port']} -U {db_config['user']}"
        code, stdout, stderr = self._run_command(test_cmd, pg_env)
        
        if code != 0:
            logger.error(f"Database connection test failed for {db_name}: {stderr}")
            return None
        
        # Create encrypted backup using pg_dump and GPG
        encryption_key = self._get_encryption_key()
        
        backup_cmd = (
            f"pg_dump {db_config['name']} "
            f"--no-password --clean --if-exists --create "
            f"| gpg --symmetric --cipher-algo AES256 --compress-algo 2 "
            f"--batch --quiet --passphrase '{encryption_key}' "
            f"--output {backup_path}"
        )
        
        logger.info(f"Creating encrypted backup: {backup_filename}")
        code, stdout, stderr = self._run_command(backup_cmd, pg_env)
        
        if code != 0:
            logger.error(f"Backup failed for {db_name}: {stderr}")
            # Clean up partial backup file
            if backup_path.exists():
                backup_path.unlink()
            return None
        
        # Verify backup file was created and has content
        if not backup_path.exists() or backup_path.stat().st_size == 0:
            logger.error(f"Backup file {backup_filename} is empty or missing")
            return None
        
        # Generate backup metadata
        file_size = backup_path.stat().st_size
        file_hash = self._calculate_file_hash(backup_path)
        
        metadata = {
            "database": db_name,
            "filename": backup_filename,
            "timestamp": timestamp,
            "file_size": file_size,
            "file_hash": file_hash,
            "encrypted": True,
            "compression": "gzip",
            "cipher": "AES256"
        }
        
        # Save metadata
        metadata_path = backup_path.with_suffix('.sql.gpg.meta')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Backup completed successfully: {backup_filename} ({file_size} bytes)")
        return str(backup_path)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def verify_backup(self, backup_path: str) -> bool:
        """Verify backup file integrity and decryption."""
        backup_file = Path(backup_path)
        metadata_file = backup_file.with_suffix('.sql.gpg.meta')
        
        if not backup_file.exists():
            logger.error(f"Backup file does not exist: {backup_path}")
            return False
        
        if not metadata_file.exists():
            logger.error(f"Metadata file does not exist: {metadata_file}")
            return False
        
        # Load metadata
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        except Exception as e:
            logger.error(f"Cannot read metadata file: {e}")
            return False
        
        # Verify file hash
        current_hash = self._calculate_file_hash(backup_file)
        if current_hash != metadata['file_hash']:
            logger.error(f"Backup file hash mismatch: expected {metadata['file_hash']}, got {current_hash}")
            return False
        
        # Test decryption (first 100 bytes to verify key works)
        encryption_key = self._get_encryption_key()
        test_cmd = (
            f"gpg --decrypt --cipher-algo AES256 --batch --quiet "
            f"--passphrase '{encryption_key}' {backup_path} | head -c 100"
        )
        
        code, stdout, stderr = self._run_command(test_cmd)
        
        if code != 0:
            logger.error(f"Backup decryption test failed: {stderr}")
            return False
        
        if "CREATE DATABASE" not in stdout and "PostgreSQL" not in stdout:
            logger.error("Backup decryption successful but content appears invalid")
            return False
        
        logger.info(f"Backup verification successful: {backup_path}")
        return True
    
    def restore_backup(self, backup_path: str, target_db: str) -> bool:
        """Restore from encrypted backup."""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            logger.error(f"Backup file does not exist: {backup_path}")
            return False
        
        # Determine which database config to use
        if target_db not in self.databases:
            logger.error(f"Unknown target database: {target_db}")
            return False
        
        db_config = self.databases[target_db]
        
        # Create PostgreSQL environment
        pg_env = os.environ.copy()
        pg_env.update({
            'PGHOST': db_config['host'],
            'PGPORT': db_config['port'],
            'PGUSER': db_config['user'],
            'PGPASSWORD': db_config['password']
        })
        
        # Restore from encrypted backup
        encryption_key = self._get_encryption_key()
        
        restore_cmd = (
            f"gpg --decrypt --cipher-algo AES256 --batch --quiet "
            f"--passphrase '{encryption_key}' {backup_path} "
            f"| psql --no-password"
        )
        
        logger.info(f"Restoring backup {backup_path} to {target_db} database...")
        code, stdout, stderr = self._run_command(restore_cmd, pg_env)
        
        if code != 0:
            logger.error(f"Restore failed: {stderr}")
            return False
        
        logger.info(f"Backup restored successfully from {backup_path}")
        return True
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period."""
        logger.info(f"Cleaning up backups older than {self.retention_days} days...")
        
        current_time = datetime.now(timezone.utc)
        deleted_count = 0
        
        for backup_file in self.backup_dir.glob("*.sql.gpg"):
            # Get file modification time
            file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime, tz=timezone.utc)
            age_days = (current_time - file_mtime).days
            
            if age_days > self.retention_days:
                # Remove backup file and metadata
                backup_file.unlink()
                metadata_file = backup_file.with_suffix('.sql.gpg.meta')
                if metadata_file.exists():
                    metadata_file.unlink()
                
                logger.info(f"Deleted old backup: {backup_file.name} (age: {age_days} days)")
                deleted_count += 1
        
        logger.info(f"Cleanup completed: {deleted_count} old backups removed")
    
    def list_backups(self) -> Dict:
        """List all available backups."""
        backups = {
            "auth": [],
            "app": []
        }
        
        for backup_file in sorted(self.backup_dir.glob("*.sql.gpg")):
            metadata_file = backup_file.with_suffix('.sql.gpg.meta')
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    db_name = metadata['database']
                    if db_name in backups:
                        metadata['path'] = str(backup_file)
                        backups[db_name].append(metadata)
                except Exception as e:
                    logger.warning(f"Cannot read metadata for {backup_file}: {e}")
        
        return backups
    
    def run_backup_cycle(self) -> bool:
        """Run complete backup cycle for all databases."""
        logger.info("Starting backup cycle...")
        
        success_count = 0
        total_databases = len(self.databases)
        
        for db_name, db_config in self.databases.items():
            backup_path = self.backup_database(db_name, db_config)
            
            if backup_path and self.verify_backup(backup_path):
                success_count += 1
                logger.info(f"✅ {db_name} database backup successful")
            else:
                logger.error(f"❌ {db_name} database backup failed")
        
        # Cleanup old backups
        self.cleanup_old_backups()
        
        logger.info(f"Backup cycle completed: {success_count}/{total_databases} databases backed up successfully")
        
        return success_count == total_databases


def main():
    """Main backup function."""
    backup_manager = EncryptedDatabaseBackup()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  backup-databases.py backup              - Run backup cycle")
        print("  backup-databases.py verify <file>       - Verify backup file")
        print("  backup-databases.py restore <file> <db> - Restore backup")
        print("  backup-databases.py list                - List backups")
        print("  backup-databases.py cleanup             - Clean old backups")
        return 1
    
    command = sys.argv[1]
    
    try:
        if command == "backup":
            success = backup_manager.run_backup_cycle()
            return 0 if success else 1
        
        elif command == "verify":
            if len(sys.argv) < 3:
                print("Error: backup file path required")
                return 1
            
            backup_path = sys.argv[2]
            success = backup_manager.verify_backup(backup_path)
            return 0 if success else 1
        
        elif command == "restore":
            if len(sys.argv) < 4:
                print("Error: backup file path and target database required")
                return 1
            
            backup_path = sys.argv[2]
            target_db = sys.argv[3]
            success = backup_manager.restore_backup(backup_path, target_db)
            return 0 if success else 1
        
        elif command == "list":
            backups = backup_manager.list_backups()
            print(json.dumps(backups, indent=2))
            return 0
        
        elif command == "cleanup":
            backup_manager.cleanup_old_backups()
            return 0
        
        else:
            print(f"Unknown command: {command}")
            return 1
    
    except Exception as e:
        logger.error(f"Backup operation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())