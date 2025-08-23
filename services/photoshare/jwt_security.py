#!/usr/bin/env python3
"""
JWT Security Management System
==============================

Enhanced JWT secret management with automatic rotation, secure storage,
and comprehensive security controls.
"""

import os
import secrets
import hashlib
import hmac
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import base64

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

try:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class JWTSecret:
    """JWT secret key data structure."""
    key_id: str
    secret_key: str
    algorithm: str
    created_at: float
    expires_at: Optional[float]
    active: bool
    rotation_count: int
    key_strength: int


@dataclass
class JWTSecurityMetrics:
    """JWT security metrics tracking."""
    total_keys_generated: int
    active_keys: int
    expired_keys: int
    rotation_events: int
    validation_failures: int
    compromise_detections: int
    last_rotation_time: Optional[float]


class JWTSecretManager:
    """Enhanced JWT secret management with rotation and security controls."""
    
    def __init__(self):
        # Use current directory in development, /app in production
        default_secure_dir = "./vault-like-secure-storage" if not os.path.exists("/app") else "/app/vault-like-secure-storage"
        self.secrets_file = os.getenv("JWT_SECRETS_FILE", f"{default_secure_dir}/jwt_secrets.json")
        self.master_key_file = os.getenv("JWT_MASTER_KEY_FILE", f"{default_secure_dir}/jwt_master.key")
        self.rotation_interval = int(os.getenv("JWT_ROTATION_INTERVAL_HOURS", "168"))  # 1 week
        self.max_key_age = int(os.getenv("JWT_MAX_KEY_AGE_HOURS", "720"))  # 30 days
        self.key_strength = int(os.getenv("JWT_KEY_STRENGTH", "256"))  # bits
        
        # Active secrets (key_id -> JWTSecret)
        self.active_secrets: Dict[str, JWTSecret] = {}
        self.current_key_id: Optional[str] = None
        
        # Security settings
        self.allowed_algorithms = ["HS256", "HS384", "HS512"]
        self.default_algorithm = os.getenv("JWT_DEFAULT_ALGORITHM", "HS256")
        
        # Security metrics
        self.metrics = JWTSecurityMetrics(
            total_keys_generated=0,
            active_keys=0,
            expired_keys=0,
            rotation_events=0,
            validation_failures=0,
            compromise_detections=0,
            last_rotation_time=None
        )
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Initialize master encryption key
        self.master_key = self._get_or_create_master_key()
        
        # Load existing secrets
        self._load_secrets()
        
        # Ensure we have at least one active key
        if not self.active_secrets:
            self._generate_initial_key()
        
        # Start background rotation monitor
        self.rotation_active = True
        self.rotation_thread = threading.Thread(target=self._rotation_worker, daemon=True)
        self.rotation_thread.start()
        
        logger.info(f"JWT Secret Manager initialized with {len(self.active_secrets)} active keys")
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key for secret storage."""
        
        master_key_path = Path(self.master_key_file)
        
        if master_key_path.exists():
            # Load existing master key
            with open(master_key_path, 'rb') as f:
                master_key = f.read()
            logger.info("Loaded existing master encryption key")
        else:
            # Generate new master key
            logger.info("Generating new master encryption key")
            
            # Create secure directory
            master_key_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            
            # Generate cryptographically secure key
            master_key = Fernet.generate_key()
            
            # Write with restrictive permissions
            with open(master_key_path, 'wb') as f:
                f.write(master_key)
            
            # Set file permissions (owner read-only)
            os.chmod(master_key_path, 0o600)
            
            logger.info(f"Master key saved to {master_key_path}")
        
        return master_key
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data using master key."""
        if not CRYPTO_AVAILABLE:
            logger.warning("Cryptography not available - storing data in base64")
            return base64.b64encode(data.encode()).decode()
        
        fernet = Fernet(self.master_key)
        encrypted = fernet.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data using master key."""
        if not CRYPTO_AVAILABLE:
            logger.warning("Cryptography not available - assuming base64 encoded")
            return base64.b64decode(encrypted_data.encode()).decode()
        
        try:
            fernet = Fernet(self.master_key)
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise ValueError("Invalid encrypted data")
    
    def _generate_secret_key(self, algorithm: str = "HS256") -> str:
        """Generate cryptographically secure secret key."""
        
        # Determine required key length based on algorithm
        if algorithm in ["HS256"]:
            key_length = 32  # 256 bits
        elif algorithm in ["HS384"]:
            key_length = 48  # 384 bits  
        elif algorithm in ["HS512"]:
            key_length = 64  # 512 bits
        else:
            key_length = 32  # Default to 256 bits
        
        # Generate cryptographically secure random key
        random_key = secrets.token_bytes(key_length)
        
        # Convert to URL-safe base64
        return base64.urlsafe_b64encode(random_key).decode('utf-8').rstrip('=')
    
    def _generate_key_id(self) -> str:
        """Generate unique key identifier."""
        timestamp = int(time.time())
        random_suffix = secrets.token_hex(8)
        return f"jwt_key_{timestamp}_{random_suffix}"
    
    def generate_new_secret(self, algorithm: Optional[str] = None) -> JWTSecret:
        """Generate new JWT secret with enhanced security."""
        
        algorithm = algorithm or self.default_algorithm
        
        if algorithm not in self.allowed_algorithms:
            raise ValueError(f"Algorithm {algorithm} not allowed. Use: {self.allowed_algorithms}")
        
        with self.lock:
            key_id = self._generate_key_id()
            secret_key = self._generate_secret_key(algorithm)
            current_time = time.time()
            
            # Calculate expiration time
            expires_at = current_time + (self.max_key_age * 3600)
            
            jwt_secret = JWTSecret(
                key_id=key_id,
                secret_key=secret_key,
                algorithm=algorithm,
                created_at=current_time,
                expires_at=expires_at,
                active=True,
                rotation_count=0,
                key_strength=len(secret_key) * 8  # bits
            )
            
            self.active_secrets[key_id] = jwt_secret
            self.metrics.total_keys_generated += 1
            self.metrics.active_keys += 1
            
            # Set as current key if none exists
            if not self.current_key_id:
                self.current_key_id = key_id
                logger.info(f"Set new key {key_id} as current signing key")
            
            # Save to persistent storage
            self._save_secrets()
            
            logger.info(f"Generated new JWT secret: {key_id} ({algorithm}, {jwt_secret.key_strength} bits)")
            
            return jwt_secret
    
    def rotate_secrets(self, force: bool = False) -> bool:
        """Rotate JWT secrets with overlap period."""
        
        with self.lock:
            logger.info("Starting JWT secret rotation...")
            
            current_time = time.time()
            current_secret = self.get_current_secret()
            
            if not current_secret:
                logger.error("No current secret found for rotation")
                return False
            
            # Check if rotation is needed
            if not force:
                time_since_creation = current_time - current_secret.created_at
                rotation_interval_seconds = self.rotation_interval * 3600
                
                if time_since_creation < rotation_interval_seconds:
                    logger.info(f"Rotation not needed yet. Next rotation in {rotation_interval_seconds - time_since_creation:.0f} seconds")
                    return True
            
            # Generate new secret
            try:
                new_secret = self.generate_new_secret(current_secret.algorithm)
                
                # Set new secret as current
                old_key_id = self.current_key_id
                self.current_key_id = new_secret.key_id
                
                # Keep old secret active for overlap period (allow existing tokens to validate)
                if old_key_id and old_key_id in self.active_secrets:
                    old_secret = self.active_secrets[old_key_id]
                    old_secret.rotation_count += 1
                    # Old secret will be deactivated by cleanup process
                
                self.metrics.rotation_events += 1
                self.metrics.last_rotation_time = current_time
                
                self._save_secrets()
                
                logger.info(f"JWT secret rotation completed: {old_key_id} → {new_secret.key_id}")
                
                # Log security event
                self._log_security_event("jwt_rotation", {
                    "old_key_id": old_key_id,
                    "new_key_id": new_secret.key_id,
                    "rotation_reason": "scheduled" if not force else "forced"
                })
                
                return True
                
            except Exception as e:
                logger.error(f"JWT secret rotation failed: {e}")
                return False
    
    def get_current_secret(self) -> Optional[JWTSecret]:
        """Get current active secret for token signing."""
        
        with self.lock:
            if not self.current_key_id or self.current_key_id not in self.active_secrets:
                # Find most recent active secret
                active_secrets = [s for s in self.active_secrets.values() if s.active]
                if active_secrets:
                    current = max(active_secrets, key=lambda x: x.created_at)
                    self.current_key_id = current.key_id
                    return current
                return None
            
            return self.active_secrets[self.current_key_id]
    
    def get_secret_by_id(self, key_id: str) -> Optional[JWTSecret]:
        """Get secret by key ID for token validation."""
        
        with self.lock:
            return self.active_secrets.get(key_id)
    
    def validate_token_signature(self, token: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Validate JWT token signature with multiple key support."""
        
        if not JWT_AVAILABLE:
            logger.error("JWT library not available")
            return False, None, None
        
        try:
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            key_id = unverified_header.get('kid')
            
            if not key_id:
                # Try with current secret if no key ID
                current_secret = self.get_current_secret()
                if current_secret:
                    key_id = current_secret.key_id
                else:
                    logger.warning("No key ID in token and no current secret available")
                    self.metrics.validation_failures += 1
                    return False, None, None
            
            # Get secret for validation
            jwt_secret = self.get_secret_by_id(key_id)
            if not jwt_secret or not jwt_secret.active:
                logger.warning(f"JWT validation failed: Unknown or inactive key ID {key_id}")
                self.metrics.validation_failures += 1
                return False, None, None
            
            # Check if key has expired
            current_time = time.time()
            if jwt_secret.expires_at and current_time > jwt_secret.expires_at:
                logger.warning(f"JWT validation failed: Expired key {key_id}")
                self.metrics.validation_failures += 1
                return False, None, None
            
            # Validate token with flexible audience verification
            payload = jwt.decode(
                token,
                jwt_secret.secret_key,
                algorithms=[jwt_secret.algorithm],
                audience="photoshare-app",
                issuer="photoshare-auth",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iat"]
                }
            )
            
            return True, key_id, payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT validation failed: Token expired")
            self.metrics.validation_failures += 1
            return False, None, None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT validation failed: {e}")
            self.metrics.validation_failures += 1
            return False, None, None
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            self.metrics.validation_failures += 1
            return False, None, None
    
    def generate_token(self, payload: Dict, expires_in: int = 1800) -> Optional[str]:
        """Generate JWT token with current secret."""
        
        if not JWT_AVAILABLE:
            logger.error("JWT library not available")
            return None
        
        current_secret = self.get_current_secret()
        if not current_secret:
            logger.error("No current JWT secret available for token generation")
            return None
        
        try:
            current_time = int(time.time())
            
            # Add standard claims
            token_payload = {
                **payload,
                "iat": current_time,
                "exp": current_time + expires_in,
                "iss": "photoshare-auth",
                "aud": "photoshare-app"
            }
            
            # Generate token with key ID in header
            token = jwt.encode(
                token_payload,
                current_secret.secret_key,
                algorithm=current_secret.algorithm,
                headers={"kid": current_secret.key_id}
            )
            
            return token
            
        except Exception as e:
            logger.error(f"JWT token generation failed: {e}")
            return None
    
    def _cleanup_expired_secrets(self):
        """Clean up expired and old secrets."""
        
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key_id, secret in list(self.active_secrets.items()):
                # Check if secret has expired
                if secret.expires_at and current_time > secret.expires_at:
                    expired_keys.append(key_id)
                # Check if secret is old but not current (grace period cleanup)
                elif (key_id != self.current_key_id and 
                      current_time - secret.created_at > (self.max_key_age * 3600 + 86400)):  # +1 day grace
                    expired_keys.append(key_id)
            
            for key_id in expired_keys:
                secret = self.active_secrets.pop(key_id)
                secret.active = False
                self.metrics.expired_keys += 1
                self.metrics.active_keys = len(self.active_secrets)
                logger.info(f"Cleaned up expired JWT secret: {key_id}")
            
            if expired_keys:
                self._save_secrets()
    
    def _rotation_worker(self):
        """Background worker for automatic secret rotation."""
        
        while self.rotation_active:
            try:
                # Check for rotation every hour
                time.sleep(3600)
                
                if not self.rotation_active:
                    break
                
                # Perform cleanup
                self._cleanup_expired_secrets()
                
                # Check if rotation is needed
                current_secret = self.get_current_secret()
                if current_secret:
                    current_time = time.time()
                    age_hours = (current_time - current_secret.created_at) / 3600
                    
                    if age_hours >= self.rotation_interval:
                        logger.info(f"Automatic rotation triggered: key age {age_hours:.1f} hours")
                        self.rotate_secrets()
                
            except Exception as e:
                logger.error(f"Rotation worker error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _save_secrets(self):
        """Save secrets to encrypted persistent storage."""
        
        secrets_path = Path(self.secrets_file)
        secrets_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        
        # Prepare data for storage
        storage_data = {
            "version": "1.0",
            "created_at": time.time(),
            "current_key_id": self.current_key_id,
            "metrics": asdict(self.metrics),
            "secrets": {}
        }
        
        # Encrypt each secret
        for key_id, secret in self.active_secrets.items():
            encrypted_key = self._encrypt_data(secret.secret_key)
            storage_data["secrets"][key_id] = {
                **asdict(secret),
                "secret_key": encrypted_key  # Replace with encrypted version
            }
        
        # Save to file with restrictive permissions
        temp_file = f"{secrets_path}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(storage_data, f, indent=2)
        
        os.chmod(temp_file, 0o600)
        os.rename(temp_file, secrets_path)
        
        logger.debug(f"Saved {len(self.active_secrets)} JWT secrets to {secrets_path}")
    
    def _load_secrets(self):
        """Load secrets from encrypted persistent storage."""
        
        secrets_path = Path(self.secrets_file)
        
        if not secrets_path.exists():
            logger.info("No existing JWT secrets file found")
            return
        
        try:
            with open(secrets_path, 'r') as f:
                storage_data = json.load(f)
            
            # Load current key ID
            self.current_key_id = storage_data.get("current_key_id")
            
            # Load metrics
            if "metrics" in storage_data:
                metrics_data = storage_data["metrics"]
                self.metrics = JWTSecurityMetrics(**metrics_data)
            
            # Load secrets
            for key_id, secret_data in storage_data.get("secrets", {}).items():
                try:
                    # Decrypt secret key
                    encrypted_key = secret_data["secret_key"]
                    decrypted_key = self._decrypt_data(encrypted_key)
                    
                    # Create JWTSecret object
                    secret_data["secret_key"] = decrypted_key
                    jwt_secret = JWTSecret(**secret_data)
                    
                    # Only load active, non-expired secrets
                    current_time = time.time()
                    if (jwt_secret.active and 
                        (not jwt_secret.expires_at or current_time < jwt_secret.expires_at)):
                        self.active_secrets[key_id] = jwt_secret
                    else:
                        logger.info(f"Skipped loading expired/inactive secret: {key_id}")
                
                except Exception as e:
                    logger.error(f"Failed to load JWT secret {key_id}: {e}")
            
            self.metrics.active_keys = len(self.active_secrets)
            
            logger.info(f"Loaded {len(self.active_secrets)} JWT secrets from storage")
            
        except Exception as e:
            logger.error(f"Failed to load JWT secrets: {e}")
    
    def _generate_initial_key(self):
        """Generate initial JWT secret if none exists."""
        
        logger.info("Generating initial JWT secret...")
        initial_secret = self.generate_new_secret()
        logger.info(f"Initial JWT secret generated: {initial_secret.key_id}")
    
    def _log_security_event(self, event_type: str, details: Dict):
        """Log security events for monitoring."""
        
        try:
            # Try to import security monitoring
            from security_monitoring import log_security_event, AlertSeverity, ThreatType
            
            log_security_event(
                severity="INFO",
                threat_type="anomalous_behavior",  # Generic type for admin actions
                source_ip="system",
                endpoint="/jwt/security",
                method="INTERNAL",
                description=f"JWT security event: {event_type}",
                details={"event_type": event_type, **details}
            )
        except ImportError:
            # Security monitoring not available
            logger.info(f"JWT security event: {event_type} - {details}")
    
    def detect_compromise(self, token: str, suspicious_activity: Dict) -> bool:
        """Detect potential JWT secret compromise."""
        
        # Analyze suspicious activity patterns
        compromise_indicators = []
        
        # Check for unusual validation patterns
        if suspicious_activity.get("validation_failures", 0) > 100:
            compromise_indicators.append("excessive_validation_failures")
        
        # Check for token replay attacks
        if suspicious_activity.get("duplicate_tokens", 0) > 10:
            compromise_indicators.append("token_replay_suspected")
        
        # Check for timing attacks
        if suspicious_activity.get("timing_anomalies", 0) > 5:
            compromise_indicators.append("timing_attack_patterns")
        
        if compromise_indicators:
            self.metrics.compromise_detections += 1
            
            logger.critical(f"JWT compromise detected: {compromise_indicators}")
            
            self._log_security_event("jwt_compromise_detected", {
                "indicators": compromise_indicators,
                "suspicious_activity": suspicious_activity
            })
            
            # Force rotation of all secrets
            self.rotate_secrets(force=True)
            
            return True
        
        return False
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive JWT security status."""
        
        with self.lock:
            current_time = time.time()
            current_secret = self.get_current_secret()
            
            return {
                "jwt_security_enabled": True,
                "current_key_info": {
                    "key_id": current_secret.key_id if current_secret else None,
                    "algorithm": current_secret.algorithm if current_secret else None,
                    "key_strength": current_secret.key_strength if current_secret else None,
                    "created_at": current_secret.created_at if current_secret else None,
                    "age_hours": (current_time - current_secret.created_at) / 3600 if current_secret else None,
                    "expires_at": current_secret.expires_at if current_secret else None
                },
                "rotation_settings": {
                    "rotation_interval_hours": self.rotation_interval,
                    "max_key_age_hours": self.max_key_age,
                    "allowed_algorithms": self.allowed_algorithms,
                    "default_algorithm": self.default_algorithm
                },
                "security_metrics": asdict(self.metrics),
                "dependencies": {
                    "jwt_available": JWT_AVAILABLE,
                    "crypto_available": CRYPTO_AVAILABLE
                },
                "timestamp": current_time
            }
    
    def shutdown(self):
        """Shutdown JWT secret manager."""
        
        self.rotation_active = False
        if self.rotation_thread.is_alive():
            self.rotation_thread.join(timeout=5)
        
        self._save_secrets()
        logger.info("JWT Secret Manager shutdown completed")


# Global JWT secret manager instance
jwt_secret_manager = JWTSecretManager()


def get_current_jwt_secret() -> Optional[str]:
    """Get current JWT secret for token operations."""
    current_secret = jwt_secret_manager.get_current_secret()
    return current_secret.secret_key if current_secret else None


def validate_jwt_token(token: str) -> Tuple[bool, Optional[Dict]]:
    """Validate JWT token with enhanced security."""
    valid, key_id, payload = jwt_secret_manager.validate_token_signature(token)
    return valid, payload


def generate_secure_jwt(payload: Dict, expires_in: int = 1800) -> Optional[str]:
    """Generate secure JWT token with current secret."""
    return jwt_secret_manager.generate_token(payload, expires_in)