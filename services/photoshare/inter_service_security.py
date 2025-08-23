#!/usr/bin/env python3
"""
Inter-Service Communication Security System
==========================================

Comprehensive security for service-to-service communication with mTLS, API key management,
service mesh integration, and secure service discovery.
"""

import os
import ssl
import time
import json
import hashlib
import hmac
import secrets
import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from threading import Lock
import aiohttp

# Cryptographic imports
try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
    from cryptography.fernet import Fernet
    import jwt
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ServiceCredential:
    """Service authentication credential."""
    service_id: str
    credential_type: str  # api_key, certificate, jwt
    credential_data: str
    metadata: Dict[str, Any]
    created_at: float
    expires_at: Optional[float]
    active: bool


@dataclass
class ServiceIdentity:
    """Service identity and configuration."""
    service_id: str
    service_name: str
    service_type: str  # internal, external, gateway
    trust_level: str  # high, medium, low
    allowed_operations: List[str]
    network_policy: Dict[str, Any]
    created_at: float
    last_seen: Optional[float]
    active: bool


@dataclass
class CommunicationAttempt:
    """Inter-service communication attempt record."""
    attempt_id: str
    source_service: str
    target_service: str
    operation: str
    timestamp: float
    success: bool
    auth_method: str
    risk_score: float
    metadata: Dict[str, Any]


class InterServiceSecurityManager:
    """Manages secure inter-service communication."""
    
    def __init__(self, secure_dir: str = None):
        self.secure_dir = secure_dir or self._get_secure_directory()
        self.db_path = os.path.join(self.secure_dir, "inter_service_security.db")
        self.certificates_dir = os.path.join(self.secure_dir, "certificates")
        self.keys_dir = os.path.join(self.secure_dir, "keys")
        self.lock = Lock()
        
        # Create directories
        for directory in [self.secure_dir, self.certificates_dir, self.keys_dir]:
            os.makedirs(directory, mode=0o700, exist_ok=True)
        
        # Service tracking - Initialize first
        self.active_services: Dict[str, ServiceIdentity] = {}
        self.service_credentials: Dict[str, List[ServiceCredential]] = {}
        self.communication_log: List[CommunicationAttempt] = []
        
        # Initialize components after service tracking setup
        self._init_database()
        self._load_encryption_key()
        self._init_service_registry()
        
        logger.info(f"Inter-Service Security Manager initialized: {self.secure_dir}")
    
    def _get_secure_directory(self) -> str:
        """Get secure directory for inter-service security."""
        return "./vault-like-secure-storage/inter_service" if not os.path.exists("/app") else "/app/vault-like-secure-storage/inter_service"
    
    def _init_database(self):
        """Initialize SQLite database for service security."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS service_identities (
                        service_id TEXT PRIMARY KEY,
                        service_name TEXT NOT NULL,
                        service_type TEXT NOT NULL,
                        trust_level TEXT NOT NULL,
                        allowed_operations TEXT,
                        network_policy TEXT,
                        created_at REAL NOT NULL,
                        last_seen REAL,
                        active BOOLEAN DEFAULT 1
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS service_credentials (
                        credential_id TEXT PRIMARY KEY,
                        service_id TEXT NOT NULL,
                        credential_type TEXT NOT NULL,
                        credential_data TEXT NOT NULL,
                        metadata TEXT,
                        created_at REAL NOT NULL,
                        expires_at REAL,
                        active BOOLEAN DEFAULT 1,
                        FOREIGN KEY (service_id) REFERENCES service_identities (service_id)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS communication_log (
                        attempt_id TEXT PRIMARY KEY,
                        source_service TEXT NOT NULL,
                        target_service TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        success BOOLEAN NOT NULL,
                        auth_method TEXT NOT NULL,
                        risk_score REAL,
                        metadata TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_keys (
                        key_id TEXT PRIMARY KEY,
                        service_id TEXT NOT NULL,
                        key_hash TEXT NOT NULL,
                        key_prefix TEXT NOT NULL,
                        permissions TEXT,
                        created_at REAL NOT NULL,
                        expires_at REAL,
                        last_used REAL,
                        usage_count INTEGER DEFAULT 0,
                        active BOOLEAN DEFAULT 1
                    )
                """)
                
                # Indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_comm_log_timestamp ON communication_log(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_comm_log_source ON communication_log(source_service)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_service ON api_keys(service_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix)")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _load_encryption_key(self):
        """Load or create encryption key for sensitive data."""
        key_file = os.path.join(self.secure_dir, "encryption.key")
        
        try:
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    key_data = f.read()
                self.encryption_key = key_data
            else:
                # Generate new key
                if CRYPTO_AVAILABLE:
                    self.encryption_key = Fernet.generate_key()
                    with open(key_file, 'wb') as f:
                        f.write(self.encryption_key)
                    os.chmod(key_file, 0o600)
                else:
                    # Fallback key
                    self.encryption_key = os.urandom(32)
                    with open(key_file, 'wb') as f:
                        f.write(self.encryption_key)
                    os.chmod(key_file, 0o600)
                    
            if CRYPTO_AVAILABLE:
                self.fernet = Fernet(self.encryption_key)
            else:
                self.fernet = None
                
        except Exception as e:
            logger.error(f"Failed to load encryption key: {e}")
            raise
    
    def _init_service_registry(self):
        """Initialize service registry with default services."""
        default_services = [
            {
                "service_id": "photoshare-app",
                "service_name": "PhotoShare Application",
                "service_type": "internal",
                "trust_level": "high",
                "allowed_operations": ["photo:upload", "photo:download", "user:auth"],
                "network_policy": {
                    "allowed_ips": ["127.0.0.1", "::1"],
                    "allowed_ports": [8000, 8001],
                    "require_tls": True
                }
            },
            {
                "service_id": "auth-service",
                "service_name": "Authentication Service",
                "service_type": "internal",
                "trust_level": "high",
                "allowed_operations": ["user:validate", "token:verify"],
                "network_policy": {
                    "allowed_ips": ["127.0.0.1", "::1"],
                    "allowed_ports": [8080, 8443],
                    "require_tls": True
                }
            },
            {
                "service_id": "gateway-service",
                "service_name": "API Gateway",
                "service_type": "gateway",
                "trust_level": "medium",
                "allowed_operations": ["proxy:*"],
                "network_policy": {
                    "allowed_ips": ["0.0.0.0/0"],
                    "allowed_ports": [80, 443],
                    "require_tls": True
                }
            }
        ]
        
        for service_config in default_services:
            self.register_service(
                service_id=service_config["service_id"],
                service_name=service_config["service_name"],
                service_type=service_config["service_type"],
                trust_level=service_config["trust_level"],
                allowed_operations=service_config["allowed_operations"],
                network_policy=service_config["network_policy"]
            )
    
    def register_service(
        self,
        service_id: str,
        service_name: str,
        service_type: str,
        trust_level: str,
        allowed_operations: List[str],
        network_policy: Dict[str, Any]
    ) -> bool:
        """Register a new service in the security registry."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO service_identities
                        (service_id, service_name, service_type, trust_level, 
                         allowed_operations, network_policy, created_at, active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        service_id, service_name, service_type, trust_level,
                        json.dumps(allowed_operations), json.dumps(network_policy),
                        time.time(), True
                    ))
                
                # Create service identity object
                service_identity = ServiceIdentity(
                    service_id=service_id,
                    service_name=service_name,
                    service_type=service_type,
                    trust_level=trust_level,
                    allowed_operations=allowed_operations,
                    network_policy=network_policy,
                    created_at=time.time(),
                    last_seen=None,
                    active=True
                )
                
                self.active_services[service_id] = service_identity
                logger.info(f"Service registered: {service_id} ({service_name})")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register service {service_id}: {e}")
            return False
    
    def generate_api_key(
        self,
        service_id: str,
        permissions: List[str],
        expires_in: int = 86400 * 30  # 30 days default
    ) -> Optional[str]:
        """Generate secure API key for service authentication."""
        try:
            if service_id not in self.active_services:
                logger.error(f"Cannot generate API key for unknown service: {service_id}")
                return None
            
            # Generate API key
            key_id = f"key_{int(time.time() * 1000000)}_{secrets.token_hex(8)}"
            api_key = f"pss_{service_id}_{secrets.token_urlsafe(32)}"
            key_prefix = api_key[:20]  # For lookup
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            expires_at = time.time() + expires_in if expires_in > 0 else None
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO api_keys
                        (key_id, service_id, key_hash, key_prefix, permissions,
                         created_at, expires_at, active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        key_id, service_id, key_hash, key_prefix,
                        json.dumps(permissions), time.time(), expires_at, True
                    ))
            
            # Store credential
            credential = ServiceCredential(
                service_id=service_id,
                credential_type="api_key",
                credential_data=key_hash,  # Store hash, not raw key
                metadata={
                    "key_id": key_id,
                    "permissions": permissions,
                    "key_prefix": key_prefix
                },
                created_at=time.time(),
                expires_at=expires_at,
                active=True
            )
            
            if service_id not in self.service_credentials:
                self.service_credentials[service_id] = []
            self.service_credentials[service_id].append(credential)
            
            logger.info(f"API key generated for service {service_id}: {key_id}")
            return api_key
            
        except Exception as e:
            logger.error(f"Failed to generate API key for {service_id}: {e}")
            return None
    
    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        """Validate API key and return service ID and permissions."""
        try:
            if not api_key or not api_key.startswith("pss_"):
                return False, None, None
            
            key_prefix = api_key[:20]
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    SELECT service_id, permissions, expires_at, active, key_id
                    FROM api_keys 
                    WHERE key_prefix = ? AND key_hash = ?
                """, (key_prefix, key_hash)).fetchone()
                
                if not result:
                    return False, None, None
                
                service_id, permissions_json, expires_at, active, key_id = result
                
                # Check if key is active
                if not active:
                    return False, None, None
                
                # Check expiration
                if expires_at and time.time() > expires_at:
                    # Deactivate expired key
                    conn.execute("""
                        UPDATE api_keys SET active = 0 WHERE key_id = ?
                    """, (key_id,))
                    return False, None, None
                
                # Update usage statistics
                conn.execute("""
                    UPDATE api_keys 
                    SET last_used = ?, usage_count = usage_count + 1
                    WHERE key_id = ?
                """, (time.time(), key_id))
                
                permissions = json.loads(permissions_json) if permissions_json else []
                return True, service_id, permissions
                
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False, None, None
    
    def generate_service_certificate(
        self,
        service_id: str,
        common_name: str,
        san_list: List[str] = None,
        validity_days: int = 365
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate TLS certificate for service mTLS authentication."""
        if not CRYPTO_AVAILABLE:
            logger.error("Certificate generation requires cryptography library")
            return None, None
        
        try:
            if service_id not in self.active_services:
                logger.error(f"Cannot generate certificate for unknown service: {service_id}")
                return None, None
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Create certificate subject
            subject = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PhotoShare Services"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, service_id),
            ])
            
            # Create certificate
            builder = x509.CertificateBuilder()
            builder = builder.subject_name(subject)
            builder = builder.issuer_name(subject)  # Self-signed for now
            builder = builder.public_key(private_key.public_key())
            builder = builder.serial_number(x509.random_serial_number())
            builder = builder.not_valid_before(datetime.utcnow())
            builder = builder.not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
            
            # Add SAN extension
            if san_list:
                san_names = [x509.DNSName(name) for name in san_list]
                builder = builder.add_extension(
                    x509.SubjectAlternativeName(san_names),
                    critical=False,
                )
            
            # Add key usage
            builder = builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            
            # Add extended key usage
            builder = builder.add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=True,
            )
            
            # Sign certificate
            certificate = builder.sign(private_key, hashes.SHA256())
            
            # Save certificate and key
            cert_file = os.path.join(self.certificates_dir, f"{service_id}.crt")
            key_file = os.path.join(self.keys_dir, f"{service_id}.key")
            
            # Write certificate
            with open(cert_file, "wb") as f:
                f.write(certificate.public_bytes(Encoding.PEM))
            os.chmod(cert_file, 0o644)
            
            # Write private key
            with open(key_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=Encoding.PEM,
                    format=PrivateFormat.PKCS8,
                    encryption_algorithm=NoEncryption()
                ))
            os.chmod(key_file, 0o600)
            
            # Store credential
            credential = ServiceCredential(
                service_id=service_id,
                credential_type="certificate",
                credential_data=cert_file,
                metadata={
                    "common_name": common_name,
                    "san_list": san_list or [],
                    "key_file": key_file,
                    "validity_days": validity_days
                },
                created_at=time.time(),
                expires_at=time.time() + (validity_days * 86400),
                active=True
            )
            
            if service_id not in self.service_credentials:
                self.service_credentials[service_id] = []
            self.service_credentials[service_id].append(credential)
            
            logger.info(f"Certificate generated for service {service_id}: {cert_file}")
            return cert_file, key_file
            
        except Exception as e:
            logger.error(f"Failed to generate certificate for {service_id}: {e}")
            return None, None
    
    def create_secure_http_session(
        self,
        service_id: str,
        verify_certs: bool = True
    ) -> Optional[aiohttp.ClientSession]:
        """Create HTTP session with mTLS configuration."""
        try:
            if service_id not in self.active_services:
                logger.error(f"Unknown service: {service_id}")
                return None
            
            # Find certificate credentials
            cert_credential = None
            if service_id in self.service_credentials:
                for cred in self.service_credentials[service_id]:
                    if cred.credential_type == "certificate" and cred.active:
                        cert_credential = cred
                        break
            
            if not cert_credential:
                logger.warning(f"No certificate found for service {service_id}")
                return aiohttp.ClientSession()
            
            # Create SSL context
            ssl_context = ssl.create_default_context()
            
            if verify_certs:
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
            else:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            # Load client certificate
            cert_file = cert_credential.credential_data
            key_file = cert_credential.metadata.get("key_file")
            
            if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
                ssl_context.load_cert_chain(cert_file, key_file)
            
            # Create connector with SSL context
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            return aiohttp.ClientSession(connector=connector)
            
        except Exception as e:
            logger.error(f"Failed to create secure session for {service_id}: {e}")
            return None
    
    def log_communication_attempt(
        self,
        source_service: str,
        target_service: str,
        operation: str,
        success: bool,
        auth_method: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Log inter-service communication attempt."""
        try:
            attempt_id = f"comm_{int(time.time() * 1000000)}_{secrets.token_hex(8)}"
            timestamp = time.time()
            
            # Calculate risk score
            risk_score = self._calculate_communication_risk(
                source_service, target_service, operation, success, auth_method
            )
            
            # Create communication attempt record
            attempt = CommunicationAttempt(
                attempt_id=attempt_id,
                source_service=source_service,
                target_service=target_service,
                operation=operation,
                timestamp=timestamp,
                success=success,
                auth_method=auth_method,
                risk_score=risk_score,
                metadata=metadata or {}
            )
            
            # Store in database
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO communication_log
                        (attempt_id, source_service, target_service, operation,
                         timestamp, success, auth_method, risk_score, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        attempt_id, source_service, target_service, operation,
                        timestamp, success, auth_method, risk_score,
                        json.dumps(metadata or {})
                    ))
            
            # Keep in-memory log (limited size)
            self.communication_log.append(attempt)
            if len(self.communication_log) > 1000:
                self.communication_log.pop(0)
            
            # Update service last seen
            if source_service in self.active_services:
                self.active_services[source_service].last_seen = timestamp
            
            logger.debug(f"Communication logged: {source_service} -> {target_service} ({operation})")
            return attempt_id
            
        except Exception as e:
            logger.error(f"Failed to log communication attempt: {e}")
            return ""
    
    def _calculate_communication_risk(
        self,
        source_service: str,
        target_service: str,
        operation: str,
        success: bool,
        auth_method: str
    ) -> float:
        """Calculate risk score for communication attempt."""
        risk_score = 0.0
        
        try:
            # Base risk factors
            if not success:
                risk_score += 30.0  # Failed attempts are suspicious
            
            # Authentication method risk
            auth_risk = {
                "certificate": 0.0,   # Most secure
                "api_key": 10.0,      # Moderate risk
                "jwt": 15.0,          # Higher risk
                "none": 50.0          # Very high risk
            }
            risk_score += auth_risk.get(auth_method, 25.0)
            
            # Service trust level
            source_service_info = self.active_services.get(source_service)
            if source_service_info:
                trust_risk = {
                    "high": 0.0,
                    "medium": 10.0,
                    "low": 25.0
                }
                risk_score += trust_risk.get(source_service_info.trust_level, 20.0)
            else:
                risk_score += 40.0  # Unknown service
            
            # Operation risk
            if "*" in operation:
                risk_score += 15.0  # Wildcard operations
            
            if "admin" in operation.lower():
                risk_score += 20.0  # Admin operations
            
            # Frequency analysis (basic implementation)
            recent_attempts = [
                attempt for attempt in self.communication_log
                if (attempt.source_service == source_service and
                    attempt.timestamp > time.time() - 300)  # Last 5 minutes
            ]
            
            if len(recent_attempts) > 100:
                risk_score += 25.0  # High frequency
            elif len(recent_attempts) > 50:
                risk_score += 15.0  # Moderate frequency
            
            return min(100.0, risk_score)
            
        except Exception as e:
            logger.error(f"Risk calculation failed: {e}")
            return 50.0  # Default moderate risk
    
    def validate_service_communication(
        self,
        source_service: str,
        target_service: str,
        operation: str,
        auth_method: str,
        source_ip: str = None
    ) -> Tuple[bool, str, float]:
        """Validate if service communication should be allowed."""
        try:
            # Check if source service is registered
            if source_service not in self.active_services:
                return False, f"Unknown source service: {source_service}", 100.0
            
            source_info = self.active_services[source_service]
            
            # Check if service is active
            if not source_info.active:
                return False, f"Source service inactive: {source_service}", 90.0
            
            # Check operation permissions
            allowed_operations = source_info.allowed_operations
            operation_allowed = False
            
            for allowed_op in allowed_operations:
                if allowed_op == operation or allowed_op.endswith("*") and operation.startswith(allowed_op[:-1]):
                    operation_allowed = True
                    break
            
            if not operation_allowed:
                return False, f"Operation not allowed: {operation}", 80.0
            
            # Check network policy
            if source_ip:
                network_policy = source_info.network_policy
                allowed_ips = network_policy.get("allowed_ips", [])
                
                # Simple IP check (could be enhanced with CIDR support)
                if allowed_ips and "0.0.0.0/0" not in allowed_ips:
                    ip_allowed = any(
                        source_ip == allowed_ip or allowed_ip in ["127.0.0.1", "::1"]
                        for allowed_ip in allowed_ips
                    )
                    
                    if not ip_allowed:
                        return False, f"IP not allowed: {source_ip}", 85.0
            
            # Calculate risk score
            risk_score = self._calculate_communication_risk(
                source_service, target_service, operation, True, auth_method
            )
            
            # Allow based on risk threshold
            risk_threshold = 70.0  # Configurable threshold
            if risk_score > risk_threshold:
                return False, f"Risk score too high: {risk_score:.1f}", risk_score
            
            return True, "Communication allowed", risk_score
            
        except Exception as e:
            logger.error(f"Communication validation failed: {e}")
            return False, f"Validation error: {str(e)}", 100.0
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get inter-service communication statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Basic counts
                total_services = conn.execute("""
                    SELECT COUNT(*) FROM service_identities WHERE active = 1
                """).fetchone()[0]
                
                total_communications = conn.execute("""
                    SELECT COUNT(*) FROM communication_log
                """).fetchone()[0]
                
                successful_communications = conn.execute("""
                    SELECT COUNT(*) FROM communication_log WHERE success = 1
                """).fetchone()[0]
                
                # Recent activity (last 24 hours)
                recent_communications = conn.execute("""
                    SELECT COUNT(*) FROM communication_log 
                    WHERE timestamp > ?
                """, (time.time() - 86400,)).fetchone()[0]
                
                # Active API keys
                active_api_keys = conn.execute("""
                    SELECT COUNT(*) FROM api_keys WHERE active = 1
                """).fetchone()[0]
                
                # High risk communications (last 24 hours)
                high_risk_communications = conn.execute("""
                    SELECT COUNT(*) FROM communication_log 
                    WHERE timestamp > ? AND risk_score > 60
                """, (time.time() - 86400,)).fetchone()[0]
                
                # Service type distribution
                service_types = conn.execute("""
                    SELECT service_type, COUNT(*) as count
                    FROM service_identities WHERE active = 1
                    GROUP BY service_type
                """).fetchall()
                
                # Authentication method distribution (last 24 hours)
                auth_methods = conn.execute("""
                    SELECT auth_method, COUNT(*) as count
                    FROM communication_log 
                    WHERE timestamp > ?
                    GROUP BY auth_method
                """, (time.time() - 86400,)).fetchall()
                
                return {
                    'inter_service_security_enabled': True,
                    'total_registered_services': total_services,
                    'total_communications': total_communications,
                    'successful_communications': successful_communications,
                    'success_rate': (successful_communications / max(total_communications, 1)) * 100,
                    'recent_communications_24h': recent_communications,
                    'active_api_keys': active_api_keys,
                    'high_risk_communications_24h': high_risk_communications,
                    'service_type_distribution': dict(service_types),
                    'auth_method_distribution': dict(auth_methods),
                    'security_features': {
                        'mtls_certificates': CRYPTO_AVAILABLE,
                        'api_key_authentication': True,
                        'service_registry': True,
                        'network_policies': True,
                        'risk_scoring': True,
                        'communication_logging': True
                    },
                    'timestamp': time.time()
                }
                
        except Exception as e:
            logger.error(f"Failed to get service statistics: {e}")
            return {
                'inter_service_security_enabled': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_recent_communications(
        self,
        limit: int = 100,
        hours_back: int = 24,
        service_filter: str = None,
        risk_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Get recent inter-service communications."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT attempt_id, source_service, target_service, operation,
                           timestamp, success, auth_method, risk_score, metadata
                    FROM communication_log
                    WHERE timestamp > ?
                """
                
                params = [time.time() - (hours_back * 3600)]
                
                if service_filter:
                    query += " AND (source_service = ? OR target_service = ?)"
                    params.extend([service_filter, service_filter])
                
                if risk_threshold is not None:
                    query += " AND risk_score >= ?"
                    params.append(risk_threshold)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                communications = conn.execute(query, params).fetchall()
                
                return [
                    {
                        'attempt_id': row[0],
                        'source_service': row[1],
                        'target_service': row[2],
                        'operation': row[3],
                        'timestamp': row[4],
                        'success': bool(row[5]),
                        'auth_method': row[6],
                        'risk_score': row[7],
                        'metadata': json.loads(row[8]) if row[8] else {}
                    } for row in communications
                ]
                
        except Exception as e:
            logger.error(f"Failed to get recent communications: {e}")
            return []
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    result = conn.execute("""
                        UPDATE api_keys SET active = 0 WHERE key_id = ?
                    """, (key_id,))
                    
                    if result.rowcount > 0:
                        logger.info(f"API key revoked: {key_id}")
                        return True
                    else:
                        logger.warning(f"API key not found: {key_id}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to revoke API key {key_id}: {e}")
            return False
    
    def shutdown(self):
        """Clean shutdown of inter-service security manager."""
        logger.info("Inter-Service Security Manager shutting down...")
        # Any cleanup tasks would go here


# Global inter-service security manager instance
inter_service_security_manager = None


def get_inter_service_manager() -> InterServiceSecurityManager:
    """Get or create global inter-service security manager instance."""
    global inter_service_security_manager
    if inter_service_security_manager is None:
        inter_service_security_manager = InterServiceSecurityManager()
    return inter_service_security_manager


def validate_service_request(
    source_service: str,
    target_service: str, 
    operation: str,
    auth_method: str,
    source_ip: str = None
) -> Tuple[bool, str, float]:
    """Convenience function for service request validation."""
    return get_inter_service_manager().validate_service_communication(
        source_service, target_service, operation, auth_method, source_ip
    )


def log_service_communication(
    source_service: str,
    target_service: str,
    operation: str,
    success: bool,
    auth_method: str,
    metadata: Dict[str, Any] = None
) -> str:
    """Convenience function for logging service communication."""
    return get_inter_service_manager().log_communication_attempt(
        source_service, target_service, operation, success, auth_method, metadata
    )


def get_service_security_stats() -> Dict[str, Any]:
    """Convenience function for service security statistics."""
    return get_inter_service_manager().get_service_statistics()