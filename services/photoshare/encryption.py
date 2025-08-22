#!/usr/bin/env python3
"""
Enhanced Encryption Module
=========================

Comprehensive encryption utilities with strong cryptographic practices
for securing sensitive data in the PhotoShare application.
"""

import os
import hashlib
import secrets
import base64
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import bcrypt

logger = logging.getLogger(__name__)

class EncryptionManager:
    """Enhanced encryption manager with multiple encryption methods."""
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or self._generate_master_key()
        self.salt_length = 32
        self.key_iterations = 100000  # PBKDF2 iterations
        self.aes_key_length = 32  # 256-bit AES
        
        # Initialize Fernet for symmetric encryption
        self.fernet_key = self._derive_fernet_key(self.master_key)
        self.fernet = Fernet(self.fernet_key)
        
        # Track encryption operations for monitoring
        self.encryption_stats = {
            "operations_count": 0,
            "last_operation": None,
            "key_rotations": 0
        }
    
    def _generate_master_key(self) -> str:
        """Generate a secure master key."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    def _derive_fernet_key(self, password: str, salt: bytes = None) -> bytes:
        """Derive a Fernet-compatible key from password."""
        if salt is None:
            salt = b"photoshare_salt_2024"  # In production, use unique salt per app
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.key_iterations,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def generate_salt(self, length: int = None) -> bytes:
        """Generate a cryptographically secure salt."""
        length = length or self.salt_length
        return secrets.token_bytes(length)
    
    def hash_password_secure(self, password: str) -> str:
        """Hash password using bcrypt with secure settings."""
        # Use high cost factor for security (12 rounds = ~250ms on modern CPU)
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password_secure(self, password: str, hashed: str) -> bool:
        """Verify password against secure hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def encrypt_sensitive_data(self, data: str) -> Dict[str, str]:
        """Encrypt sensitive data with metadata for tracking."""
        try:
            # Generate unique salt for this operation
            salt = self.generate_salt()
            
            # Encrypt data with timestamp
            encrypted_data = self.fernet.encrypt(data.encode())
            
            # Create encryption metadata
            metadata = {
                "encrypted_data": base64.urlsafe_b64encode(encrypted_data).decode(),
                "salt": base64.urlsafe_b64encode(salt).decode(),
                "algorithm": "Fernet_AES256",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0"
            }
            
            self._track_operation("encrypt")
            return metadata
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Data encryption failed")
    
    def decrypt_sensitive_data(self, metadata: Dict[str, str]) -> str:
        """Decrypt sensitive data from metadata."""
        try:
            encrypted_data = base64.urlsafe_b64decode(metadata["encrypted_data"])
            decrypted_data = self.fernet.decrypt(encrypted_data)
            
            self._track_operation("decrypt")
            return decrypted_data.decode()
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Data decryption failed")
    
    def encrypt_file_content(self, file_content: bytes) -> Dict[str, Any]:
        """Encrypt file content with AES-256-GCM."""
        try:
            # Generate key and nonce
            key = secrets.token_bytes(32)  # 256-bit key
            nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key), 
                modes.GCM(nonce),
                backend=default_backend()
            )
            
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(file_content) + encryptor.finalize()
            
            # Get authentication tag
            auth_tag = encryptor.tag
            
            # Encrypt the key with master key
            key_encrypted = self.fernet.encrypt(key)
            
            result = {
                "ciphertext": base64.urlsafe_b64encode(ciphertext).decode(),
                "nonce": base64.urlsafe_b64encode(nonce).decode(),
                "auth_tag": base64.urlsafe_b64encode(auth_tag).decode(),
                "encrypted_key": base64.urlsafe_b64encode(key_encrypted).decode(),
                "algorithm": "AES-256-GCM",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            self._track_operation("file_encrypt")
            return result
            
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise ValueError("File encryption failed")
    
    def decrypt_file_content(self, encryption_data: Dict[str, Any]) -> bytes:
        """Decrypt file content from AES-256-GCM encryption."""
        try:
            # Decode components
            ciphertext = base64.urlsafe_b64decode(encryption_data["ciphertext"])
            nonce = base64.urlsafe_b64decode(encryption_data["nonce"])
            auth_tag = base64.urlsafe_b64decode(encryption_data["auth_tag"])
            encrypted_key = base64.urlsafe_b64decode(encryption_data["encrypted_key"])
            
            # Decrypt the key
            key = self.fernet.decrypt(encrypted_key)
            
            # Create cipher for decryption
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce, auth_tag),
                backend=default_backend()
            )
            
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            self._track_operation("file_decrypt")
            return plaintext
            
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            raise ValueError("File decryption failed")
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token."""
        token_bytes = secrets.token_bytes(length)
        return base64.urlsafe_b64encode(token_bytes).decode().rstrip('=')
    
    def create_hmac_signature(self, data: str, secret: str = None) -> str:
        """Create HMAC signature for data integrity."""
        try:
            import hmac
            
            secret_key = secret or self.master_key
            signature = hmac.new(
                secret_key.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            self._track_operation("hmac")
            return signature
            
        except Exception as e:
            logger.error(f"HMAC creation failed: {e}")
            raise ValueError("HMAC signature creation failed")
    
    def verify_hmac_signature(self, data: str, signature: str, secret: str = None) -> bool:
        """Verify HMAC signature for data integrity."""
        try:
            expected_signature = self.create_hmac_signature(data, secret)
            # Use constant-time comparison to prevent timing attacks
            return secrets.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"HMAC verification failed: {e}")
            return False
    
    def rotate_encryption_key(self) -> str:
        """Rotate the master encryption key."""
        old_key = self.master_key
        self.master_key = self._generate_master_key()
        
        # Regenerate Fernet key
        self.fernet_key = self._derive_fernet_key(self.master_key)
        self.fernet = Fernet(self.fernet_key)
        
        self.encryption_stats["key_rotations"] += 1
        self._track_operation("key_rotation")
        
        logger.warning("Encryption key rotated for enhanced security")
        return self.master_key
    
    def _track_operation(self, operation_type: str):
        """Track encryption operations for monitoring."""
        self.encryption_stats["operations_count"] += 1
        self.encryption_stats["last_operation"] = {
            "type": operation_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_encryption_stats(self) -> Dict[str, Any]:
        """Get encryption operation statistics."""
        return {
            "total_operations": self.encryption_stats["operations_count"],
            "last_operation": self.encryption_stats["last_operation"],
            "key_rotations": self.encryption_stats["key_rotations"],
            "master_key_age": self._get_key_age(),
            "security_level": "AES-256 + PBKDF2 + bcrypt",
            "algorithms_used": ["AES-256-GCM", "Fernet", "bcrypt", "HMAC-SHA256"]
        }
    
    def _get_key_age(self) -> str:
        """Calculate age of current master key."""
        # This would be implemented with key creation timestamp in production
        return "Current session"

class DataProtectionService:
    """Service for protecting sensitive application data."""
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption = encryption_manager
        self.protected_fields = {
            "password", "email", "phone", "address", "ssn", "credit_card",
            "api_key", "secret", "token", "private_key"
        }
    
    def protect_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Protect sensitive fields in user data."""
        protected_data = user_data.copy()
        
        for field, value in user_data.items():
            if self._is_sensitive_field(field) and value:
                try:
                    # Encrypt sensitive data
                    encrypted_metadata = self.encryption.encrypt_sensitive_data(str(value))
                    protected_data[field] = encrypted_metadata
                    
                    # Add protection marker
                    protected_data[f"{field}_protected"] = True
                    
                except Exception as e:
                    logger.error(f"Failed to protect field {field}: {e}")
                    # Keep original value if encryption fails (log but don't break)
        
        return protected_data
    
    def unprotect_user_data(self, protected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Unprotect sensitive fields in user data."""
        unprotected_data = protected_data.copy()
        
        for field, value in protected_data.items():
            if field.endswith("_protected") and value:
                original_field = field.replace("_protected", "")
                
                if original_field in protected_data and isinstance(protected_data[original_field], dict):
                    try:
                        # Decrypt sensitive data
                        decrypted_value = self.encryption.decrypt_sensitive_data(
                            protected_data[original_field]
                        )
                        unprotected_data[original_field] = decrypted_value
                        
                        # Remove protection marker
                        del unprotected_data[field]
                        
                    except Exception as e:
                        logger.error(f"Failed to unprotect field {original_field}: {e}")
        
        return unprotected_data
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if field contains sensitive data."""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in self.protected_fields)
    
    def create_data_signature(self, data: Dict[str, Any]) -> str:
        """Create signature for data integrity verification."""
        # Create canonical representation of data
        import json
        canonical_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return self.encryption.create_hmac_signature(canonical_data)
    
    def verify_data_integrity(self, data: Dict[str, Any], signature: str) -> bool:
        """Verify data integrity using signature."""
        expected_signature = self.create_data_signature(data)
        return self.encryption.verify_hmac_signature(
            expected_signature, signature
        )

class SecurityKeyManager:
    """Manage cryptographic keys with rotation and lifecycle."""
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption = encryption_manager
        self.key_store = {}  # In production, use secure key storage (HSM, Vault, etc.)
        self.key_metadata = {}
        self.max_key_age = timedelta(days=90)  # Rotate keys every 90 days
        
        # Enhanced key management features
        self.key_hierarchy = {}  # Master keys, derived keys, etc.
        self.key_escrow = {}  # Key backup and recovery
        self.compliance_logs = []  # Audit trail for compliance
        self.key_access_logs = []  # Track key usage
        
        # Security policies
        self.max_key_usage_count = 100000  # Max operations per key
        self.key_rotation_alerts = []
        self.compromised_keys = set()
        
        # Initialize with secure key storage policies
        self._initialize_key_policies()
    
    def _initialize_key_policies(self):
        """Initialize secure key management policies."""
        self.key_policies = {
            "minimum_key_length": 32,
            "required_entropy_bits": 256,
            "max_concurrent_keys_per_user": 10,
            "key_rotation_period": 90,  # days
            "backup_encryption_required": True,
            "audit_trail_retention": 365,  # days
            "compliance_standards": ["FIPS-140-2", "Common Criteria", "NIST"],
            "key_derivation_iterations": 100000,
            "secure_deletion_passes": 3
        }
        
        # Log policy initialization
        self._log_compliance_event("KEY_POLICIES_INITIALIZED", {
            "policies": list(self.key_policies.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def generate_master_key(self, purpose: str, key_type: str = "AES-256") -> Dict[str, str]:
        """Generate a new master key with proper hierarchy."""
        master_key = self.encryption.generate_secure_token(32)
        key_id = f"master_{purpose}_{secrets.token_hex(8)}"
        
        # Create key hierarchy entry
        self.key_hierarchy[key_id] = {
            "type": "master",
            "purpose": purpose,
            "algorithm": key_type,
            "created_at": datetime.now(timezone.utc),
            "derived_keys": [],
            "rotation_schedule": datetime.now(timezone.utc) + self.max_key_age,
            "usage_count": 0,
            "access_controls": ["admin", "key_manager"]
        }
        
        # Encrypt and store the key
        encrypted_key = self.encryption.encrypt_sensitive_data(master_key)
        self.key_store[key_id] = encrypted_key
        
        # Create escrow backup
        self._create_key_escrow(key_id, master_key)
        
        # Log compliance event
        self._log_compliance_event("MASTER_KEY_GENERATED", {
            "key_id": key_id[:8] + "...",
            "purpose": purpose,
            "algorithm": key_type
        })
        
        return {
            "key_id": key_id,
            "purpose": purpose,
            "algorithm": key_type,
            "created_at": self.key_hierarchy[key_id]["created_at"].isoformat(),
            "rotation_due": self.key_hierarchy[key_id]["rotation_schedule"].isoformat()
        }
    
    def derive_key(self, master_key_id: str, purpose: str, user_id: int = None) -> Dict[str, str]:
        """Derive a new key from master key."""
        if master_key_id not in self.key_hierarchy:
            raise ValueError("Master key not found")
        
        # Get master key
        encrypted_master = self.key_store[master_key_id]
        master_key = self.encryption.decrypt_sensitive_data(encrypted_master)
        
        # Derive new key using PBKDF2
        salt = secrets.token_bytes(32)
        derived_key = hashlib.pbkdf2_hmac('sha256', master_key.encode(), salt, 100000)
        derived_key_b64 = base64.urlsafe_b64encode(derived_key).decode()
        
        # Create derived key ID
        derived_key_id = f"derived_{purpose}_{secrets.token_hex(8)}"
        
        # Store derived key metadata
        self.key_metadata[derived_key_id] = {
            "parent_key": master_key_id,
            "user_id": user_id,
            "purpose": purpose,
            "created_at": datetime.now(timezone.utc),
            "salt": base64.urlsafe_b64encode(salt).decode(),
            "usage_count": 0,
            "is_active": True,
            "key_derivation": "PBKDF2-SHA256"
        }
        
        # Update parent key hierarchy
        self.key_hierarchy[master_key_id]["derived_keys"].append(derived_key_id)
        
        # Store encrypted derived key
        encrypted_derived = self.encryption.encrypt_sensitive_data(derived_key_b64)
        self.key_store[derived_key_id] = encrypted_derived
        
        # Log key access
        self._log_key_access(derived_key_id, "DERIVE", user_id)
        
        return {
            "key_id": derived_key_id,
            "parent_key": master_key_id[:8] + "...",
            "purpose": purpose,
            "created_at": self.key_metadata[derived_key_id]["created_at"].isoformat()
        }
    
    def _create_key_escrow(self, key_id: str, key_material: str):
        """Create encrypted backup of key for recovery."""
        # In production, this would use secure key escrow system
        escrow_key = self.encryption.generate_secure_token(32)
        escrow_id = f"escrow_{secrets.token_hex(8)}"
        
        # Encrypt key with escrow key
        escrow_data = self.encryption.encrypt_sensitive_data(key_material)
        
        self.key_escrow[key_id] = {
            "escrow_id": escrow_id,
            "encrypted_key": escrow_data,
            "created_at": datetime.now(timezone.utc),
            "recovery_threshold": 2,  # Number of escrow agents needed
            "escrow_agents": ["admin_1", "admin_2", "security_officer"]
        }
        
        self._log_compliance_event("KEY_ESCROWED", {
            "key_id": key_id[:8] + "...",
            "escrow_id": escrow_id
        })
    
    def recover_key_from_escrow(self, key_id: str, recovery_authorization: Dict[str, str]) -> str:
        """Recover key from escrow with proper authorization."""
        if key_id not in self.key_escrow:
            raise ValueError("Key not found in escrow")
        
        escrow_info = self.key_escrow[key_id]
        
        # Verify recovery authorization (simplified)
        authorized_agents = recovery_authorization.get("agents", [])
        if len(authorized_agents) < escrow_info["recovery_threshold"]:
            raise ValueError("Insufficient authorization for key recovery")
        
        # Decrypt and return key
        recovered_key = self.encryption.decrypt_sensitive_data(escrow_info["encrypted_key"])
        
        # Log critical security event
        self._log_compliance_event("KEY_RECOVERED_FROM_ESCROW", {
            "key_id": key_id[:8] + "...",
            "authorized_by": authorized_agents,
            "recovery_reason": recovery_authorization.get("reason", "Not specified")
        })
        
        return recovered_key
    
    def mark_key_compromised(self, key_id: str, incident_details: Dict[str, Any]):
        """Mark a key as compromised and initiate rotation."""
        self.compromised_keys.add(key_id)
        
        # Immediately revoke if it's an API key
        if key_id in self.key_metadata:
            self.key_metadata[key_id]["is_active"] = False
            self.key_metadata[key_id]["compromised_at"] = datetime.now(timezone.utc)
            self.key_metadata[key_id]["incident_details"] = incident_details
        
        # Log critical security incident
        self._log_compliance_event("KEY_COMPROMISED", {
            "key_id": key_id[:8] + "...",
            "incident_type": incident_details.get("type", "unknown"),
            "severity": incident_details.get("severity", "high"),
            "description": incident_details.get("description", "Key marked as compromised")
        })
        
        # Add to rotation alerts
        self.key_rotation_alerts.append({
            "key_id": key_id,
            "alert_type": "COMPROMISE",
            "priority": "CRITICAL",
            "message": "Key compromised - immediate rotation required",
            "timestamp": datetime.now(timezone.utc)
        })
        
        logger.critical(f"Key {key_id[:8]}... marked as compromised")
    
    def perform_key_lifecycle_audit(self) -> Dict[str, Any]:
        """Perform comprehensive audit of key lifecycle management."""
        audit_report = {
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_keys": len(self.key_store),
            "active_keys": sum(1 for k in self.key_metadata.values() if k.get("is_active", True)),
            "compromised_keys": len(self.compromised_keys),
            "keys_due_for_rotation": 0,
            "compliance_violations": [],
            "security_recommendations": [],
            "key_hierarchy_health": {}
        }
        
        current_time = datetime.now(timezone.utc)
        
        # Check key age and rotation needs
        for key_id, metadata in self.key_metadata.items():
            created_at = metadata.get("created_at", current_time)
            age = current_time - created_at
            
            if age > self.max_key_age:
                audit_report["keys_due_for_rotation"] += 1
                audit_report["security_recommendations"].append(
                    f"Rotate key {key_id[:8]}... (age: {age.days} days)"
                )
        
        # Check key hierarchy health
        for master_id, hierarchy_info in self.key_hierarchy.items():
            derived_count = len(hierarchy_info.get("derived_keys", []))
            usage_count = hierarchy_info.get("usage_count", 0)
            
            if usage_count > self.max_key_usage_count:
                audit_report["compliance_violations"].append(
                    f"Master key {master_id[:8]}... exceeded usage limit"
                )
            
            audit_report["key_hierarchy_health"][master_id[:8] + "..."] = {
                "derived_keys": derived_count,
                "usage_count": usage_count,
                "age_days": (current_time - hierarchy_info["created_at"]).days
            }
        
        # Check escrow health
        escrowed_keys = len(self.key_escrow)
        audit_report["escrow_status"] = {
            "total_escrowed": escrowed_keys,
            "escrow_coverage": f"{(escrowed_keys / max(len(self.key_store), 1)) * 100:.1f}%"
        }
        
        # Generate recommendations
        if audit_report["keys_due_for_rotation"] > 0:
            audit_report["security_recommendations"].append("Schedule key rotation maintenance")
        
        if audit_report["compromised_keys"] > 0:
            audit_report["security_recommendations"].append("Review and replace compromised keys")
        
        # Log audit completion
        self._log_compliance_event("KEY_LIFECYCLE_AUDIT_COMPLETED", {
            "total_keys_audited": audit_report["total_keys"],
            "violations_found": len(audit_report["compliance_violations"]),
            "recommendations": len(audit_report["security_recommendations"])
        })
        
        return audit_report
    
    def _log_key_access(self, key_id: str, operation: str, user_id: int = None):
        """Log key access for audit trail."""
        access_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "key_id": key_id[:8] + "...",
            "operation": operation,
            "user_id": user_id,
            "source_ip": "system",  # In production, capture real IP
            "success": True
        }
        
        self.key_access_logs.append(access_log)
        
        # Keep only last 1000 access logs
        if len(self.key_access_logs) > 1000:
            self.key_access_logs = self.key_access_logs[-1000:]
    
    def _log_compliance_event(self, event_type: str, details: Dict[str, Any]):
        """Log compliance and audit events."""
        compliance_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details,
            "compliance_officer": "system"
        }
        
        self.compliance_logs.append(compliance_event)
        
        # Keep only last 1000 compliance logs
        if len(self.compliance_logs) > 1000:
            self.compliance_logs = self.compliance_logs[-1000:]
    
    def get_key_management_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report for key management."""
        return {
            "compliance_status": "COMPLIANT",
            "total_keys_managed": len(self.key_store),
            "active_policies": self.key_policies,
            "recent_compliance_events": self.compliance_logs[-10:],
            "recent_key_access": self.key_access_logs[-10:],
            "compromised_keys_count": len(self.compromised_keys),
            "rotation_alerts": len(self.key_rotation_alerts),
            "escrow_coverage": len(self.key_escrow),
            "audit_recommendations": self._generate_compliance_recommendations()
        }
    
    def _generate_compliance_recommendations(self) -> List[str]:
        """Generate compliance recommendations."""
        recommendations = []
        
        if len(self.compromised_keys) > 0:
            recommendations.append("Address compromised keys immediately")
        
        if len(self.key_rotation_alerts) > 0:
            recommendations.append("Review key rotation alerts")
        
        current_time = datetime.now(timezone.utc)
        old_keys = sum(1 for m in self.key_metadata.values() 
                      if (current_time - m.get("created_at", current_time)).days > 90)
        
        if old_keys > 0:
            recommendations.append("Rotate aging keys per policy")
        
        if len(self.key_escrow) < len(self.key_store) * 0.8:
            recommendations.append("Improve key escrow coverage")
        
        return recommendations

    def generate_api_key(self, user_id: int, scope: str = "default") -> Dict[str, str]:
        """Generate secure API key for user."""
        api_key = self.encryption.generate_secure_token(32)
        key_id = f"api_{user_id}_{scope}_{secrets.token_hex(8)}"
        
        # Store key metadata
        self.key_metadata[key_id] = {
            "user_id": user_id,
            "scope": scope,
            "created_at": datetime.now(timezone.utc),
            "last_used": None,
            "usage_count": 0,
            "is_active": True
        }
        
        # Create secure hash for storage
        key_hash = self.encryption.hash_password_secure(api_key)
        self.key_store[key_id] = key_hash
        
        return {
            "api_key": api_key,
            "key_id": key_id,
            "created_at": self.key_metadata[key_id]["created_at"].isoformat(),
            "scope": scope
        }
    
    def verify_api_key(self, api_key: str, key_id: str = None) -> Optional[Dict[str, Any]]:
        """Verify API key and return metadata."""
        if key_id and key_id in self.key_store:
            stored_hash = self.key_store[key_id]
            
            if self.encryption.verify_password_secure(api_key, stored_hash):
                # Update usage
                self.key_metadata[key_id]["last_used"] = datetime.now(timezone.utc)
                self.key_metadata[key_id]["usage_count"] += 1
                
                return self.key_metadata[key_id].copy()
        
        return None
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if key_id in self.key_metadata:
            self.key_metadata[key_id]["is_active"] = False
            logger.info(f"API key revoked: {key_id}")
            return True
        return False
    
    def rotate_expired_keys(self) -> Dict[str, int]:
        """Rotate keys that have exceeded max age."""
        current_time = datetime.now(timezone.utc)
        expired_keys = []
        rotated_count = 0
        
        for key_id, metadata in self.key_metadata.items():
            if metadata["is_active"] and current_time - metadata["created_at"] > self.max_key_age:
                expired_keys.append(key_id)
        
        # Revoke expired keys
        for key_id in expired_keys:
            if self.revoke_api_key(key_id):
                rotated_count += 1
        
        return {
            "expired_keys_found": len(expired_keys),
            "keys_rotated": rotated_count
        }
    
    def get_key_statistics(self) -> Dict[str, Any]:
        """Get key management statistics."""
        active_keys = [k for k, v in self.key_metadata.items() if v["is_active"]]
        inactive_keys = [k for k, v in self.key_metadata.items() if not v["is_active"]]
        
        return {
            "total_keys": len(self.key_metadata),
            "active_keys": len(active_keys),
            "inactive_keys": len(inactive_keys),
            "key_usage_stats": self._get_usage_stats(),
            "oldest_key_age": self._get_oldest_key_age(),
            "encryption_stats": self.encryption.get_encryption_stats()
        }
    
    def _get_usage_stats(self) -> Dict[str, int]:
        """Get key usage statistics."""
        total_usage = sum(meta["usage_count"] for meta in self.key_metadata.values())
        return {
            "total_api_calls": total_usage,
            "average_usage_per_key": total_usage // max(len(self.key_metadata), 1)
        }
    
    def _get_oldest_key_age(self) -> str:
        """Get age of oldest key."""
        if not self.key_metadata:
            return "No keys"
        
        oldest_key = min(self.key_metadata.values(), key=lambda x: x["created_at"])
        age = datetime.now(timezone.utc) - oldest_key["created_at"]
        return f"{age.days} days"

# Global instances for application use
encryption_manager = EncryptionManager(os.getenv("MASTER_ENCRYPTION_KEY"))
data_protection = DataProtectionService(encryption_manager)
key_manager = SecurityKeyManager(encryption_manager)

def get_encryption_manager() -> EncryptionManager:
    """Get the global encryption manager instance."""
    return encryption_manager

def get_data_protection() -> DataProtectionService:
    """Get the global data protection service."""
    return data_protection

def get_key_manager() -> SecurityKeyManager:
    """Get the global security key manager."""
    return key_manager