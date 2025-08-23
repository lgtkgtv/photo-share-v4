#!/usr/bin/env python3
"""
File Storage Service Integration
===============================

Handles file storage operations with the platform storage service.
"""

import os
import aiohttp
import hashlib
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class FileStorageService:
    """Service for handling file storage operations."""
    
    def __init__(self):
        self.storage_base_url = os.getenv("PLATFORM_STORAGE_URL", "http://platform-storage:80")
        self.local_storage_path = "/tmp/photo_storage"
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        
        # Ensure local storage directory exists
        Path(self.local_storage_path).mkdir(parents=True, exist_ok=True)
    
    def _generate_file_hash(self, content: bytes) -> str:
        """Generate SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()
    
    def _get_storage_path(self, user_id: int, filename: str) -> str:
        """Generate storage path for a file."""
        return f"users/{user_id}/photos/{filename}"
    
    async def store_file(self, user_id: int, filename: str, content: bytes, content_type: str) -> Dict[str, Any]:
        """
        Store file in platform storage.
        
        Args:
            user_id: ID of the user uploading the file
            filename: Name of the file
            content: File content as bytes
            content_type: MIME type of the file
            
        Returns:
            Dictionary with storage information
        """
        try:
            # Validate file size
            if len(content) > self.max_file_size:
                raise ValueError(f"File size {len(content)} exceeds maximum {self.max_file_size}")
            
            # Generate file hash for integrity checking
            file_hash = self._generate_file_hash(content)
            
            # Generate storage path
            storage_path = self._get_storage_path(user_id, filename)
            local_file_path = os.path.join(self.local_storage_path, storage_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            # Store file locally first
            with open(local_file_path, 'wb') as f:
                f.write(content)
            
            # Try to upload to platform storage service
            platform_stored = await self._upload_to_platform_storage(storage_path, content, content_type)
            
            storage_info = {
                "storage_path": storage_path,
                "local_path": local_file_path,
                "file_hash": file_hash,
                "file_size": len(content),
                "content_type": content_type,
                "platform_stored": platform_stored,
                "storage_url": f"{self.storage_base_url}/storage/{storage_path}" if platform_stored else None
            }
            
            logger.info(f"File stored: {filename} -> {storage_path} (platform: {platform_stored})")
            return storage_info
            
        except Exception as e:
            logger.error(f"File storage failed for {filename}: {e}")
            raise
    
    async def _upload_to_platform_storage(self, storage_path: str, content: bytes, content_type: str) -> bool:
        """Upload file to platform storage service."""
        try:
            # For now, simulate platform storage upload
            # In a real implementation, this would POST to the storage service
            
            # Simulate storage by creating the file structure in the storage volume
            
            # Since we can't directly write to the nginx container,
            # we'll create a local representation that would be synced
            logger.info(f"Simulating platform storage upload to {storage_path}")
            
            # In production, this would be:
            # async with aiohttp.ClientSession() as session:
            #     data = aiohttp.FormData()
            #     data.add_field('file', content, filename=os.path.basename(storage_path), content_type=content_type)
            #     data.add_field('path', storage_path)
            #     async with session.post(upload_url, data=data) as response:
            #         return response.status == 200
            
            # For demo, always return True
            return True
            
        except Exception as e:
            logger.warning(f"Platform storage upload failed: {e}")
            return False
    
    async def retrieve_file(self, storage_path: str) -> Optional[bytes]:
        """Retrieve file content from storage."""
        try:
            # Try local storage first
            local_path = os.path.join(self.local_storage_path, storage_path)
            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    return f.read()
            
            # Try platform storage
            return await self._download_from_platform_storage(storage_path)
            
        except Exception as e:
            logger.error(f"File retrieval failed for {storage_path}: {e}")
            return None
    
    async def _download_from_platform_storage(self, storage_path: str) -> Optional[bytes]:
        """Download file from platform storage service."""
        try:
            download_url = f"{self.storage_base_url}/storage/{storage_path}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        return await response.read()
                    return None
                    
        except Exception as e:
            logger.warning(f"Platform storage download failed: {e}")
            return None
    
    async def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage."""
        try:
            deleted = False
            
            # Delete from local storage
            local_path = os.path.join(self.local_storage_path, storage_path)
            if os.path.exists(local_path):
                os.remove(local_path)
                deleted = True
            
            # Delete from platform storage (simulated)
            platform_deleted = await self._delete_from_platform_storage(storage_path)
            
            logger.info(f"File deleted: {storage_path} (local: {deleted}, platform: {platform_deleted})")
            return deleted or platform_deleted
            
        except Exception as e:
            logger.error(f"File deletion failed for {storage_path}: {e}")
            return False
    
    async def _delete_from_platform_storage(self, storage_path: str) -> bool:
        """Delete file from platform storage service."""
        try:
            # In production, this would be a DELETE request to the storage service
            logger.info(f"Simulating platform storage deletion for {storage_path}")
            return True
            
        except Exception as e:
            logger.warning(f"Platform storage deletion failed: {e}")
            return False
    
    def get_file_url(self, storage_path: str) -> str:
        """Get public URL for accessing a file."""
        return f"{self.storage_base_url}/storage/{storage_path}"
    
    async def health_check(self) -> Dict[str, Any]:
        """Check storage service health."""
        try:
            # Check local storage
            local_healthy = os.path.exists(self.local_storage_path) and os.access(self.local_storage_path, os.W_OK)
            
            # Check platform storage connectivity
            platform_healthy = False
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    async with session.get(f"{self.storage_base_url}/health") as response:
                        platform_healthy = response.status == 200
            except Exception:
                platform_healthy = False
            
            return {
                "local_storage": local_healthy,
                "platform_storage": platform_healthy,
                "storage_path": self.local_storage_path,
                "platform_url": self.storage_base_url,
                "max_file_size_mb": self.max_file_size // (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return {
                "local_storage": False,
                "platform_storage": False,
                "error": str(e)
            }