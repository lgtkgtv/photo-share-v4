#!/usr/bin/env python3
"""
Audit Trail Integrity System
=============================

Comprehensive audit logging with tamper-proof trail integrity,
digital signatures, and immutable record keeping.
"""

import os
import time
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from collections import deque
import sqlite3

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    from security_monitoring import log_security_event, AlertSeverity, ThreatType
    SECURITY_MONITORING_AVAILABLE = True
except ImportError:
    SECURITY_MONITORING_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    """Immutable audit record structure."""
    record_id: str
    timestamp: float
    user_id: Optional[str]
    session_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    source_ip: str
    user_agent: str
    request_method: str
    endpoint: str
    status_code: int
    details: Dict[str, Any]
    risk_level: str
    chain_hash: str  # Hash linking to previous record
    signature: Optional[str]  # Digital signature for integrity


@dataclass
class AuditMetrics:
    """Audit trail metrics and statistics."""
    total_records: int
    records_by_action: Dict[str, int]
    records_by_user: Dict[str, int]
    records_by_risk: Dict[str, int]
    integrity_checks_passed: int
    integrity_violations: int
    signature_verifications: int
    chain_breaks_detected: int
    last_integrity_check: Optional[float]


class AuditTrailManager:
    """Tamper-proof audit trail management system."""
    
    def __init__(self):
        # Configuration
        self.audit_db_path = os.getenv("AUDIT_DB_PATH", "./tamper-proof-audit-storage/audit_trail.db")
        self.signing_key_path = os.getenv("AUDIT_SIGNING_KEY", "./tamper-proof-audit-storage/audit_signing.key")
        self.verify_key_path = os.getenv("AUDIT_VERIFY_KEY", "./tamper-proof-audit-storage/audit_verify.pub")
        self.integrity_check_interval = int(os.getenv("AUDIT_INTEGRITY_CHECK_INTERVAL", "3600"))  # 1 hour
        
        # Audit trail state
        self.last_chain_hash = ""
        self.record_count = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Metrics
        self.metrics = AuditMetrics(
            total_records=0,
            records_by_action={},
            records_by_user={},
            records_by_risk={},
            integrity_checks_passed=0,
            integrity_violations=0,
            signature_verifications=0,
            chain_breaks_detected=0,
            last_integrity_check=None
        )
        
        # Initialize components
        self._setup_database()
        self._setup_signing_keys()
        
        # Load existing audit state
        self._load_audit_state()
        
        # Start background integrity monitoring
        self.integrity_monitor_active = True
        self.integrity_thread = threading.Thread(target=self._integrity_monitor, daemon=True)
        self.integrity_thread.start()
        
        logger.info(f"Audit Trail Manager initialized with {self.record_count} existing records")
    
    def _setup_database(self):
        """Set up SQLite database for audit records."""
        
        audit_db_dir = Path(self.audit_db_path).parent
        audit_db_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        
        # Create database connection
        self.db_conn = sqlite3.connect(
            self.audit_db_path, 
            check_same_thread=False,
            isolation_level='IMMEDIATE'
        )
        self.db_conn.row_factory = sqlite3.Row
        
        # Create audit records table
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_records (
                record_id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                user_id TEXT,
                session_id TEXT,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                source_ip TEXT NOT NULL,
                user_agent TEXT,
                request_method TEXT,
                endpoint TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                details TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                chain_hash TEXT NOT NULL,
                signature TEXT,
                created_at REAL DEFAULT (julianday('now'))
            )
        """)
        
        # Create indexes for performance
        self.db_conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_records(timestamp)")
        self.db_conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON audit_records(user_id)")
        self.db_conn.execute("CREATE INDEX IF NOT EXISTS idx_action ON audit_records(action)")
        self.db_conn.execute("CREATE INDEX IF NOT EXISTS idx_risk_level ON audit_records(risk_level)")
        
        # Create integrity verification table
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_integrity (
                check_id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_timestamp REAL NOT NULL,
                records_verified INTEGER NOT NULL,
                integrity_status TEXT NOT NULL,
                violations_found INTEGER DEFAULT 0,
                chain_breaks INTEGER DEFAULT 0,
                signature_failures INTEGER DEFAULT 0,
                details TEXT
            )
        """)
        
        self.db_conn.commit()
        
        # Set restrictive file permissions
        os.chmod(self.audit_db_path, 0o600)
        
        logger.info(f"Audit database initialized: {self.audit_db_path}")
    
    def _setup_signing_keys(self):
        """Set up RSA signing keys for audit record integrity."""
        
        signing_key_file = Path(self.signing_key_path)
        verify_key_file = Path(self.verify_key_path)
        
        # Create keys directory
        signing_key_file.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        
        if not CRYPTO_AVAILABLE:
            logger.warning("Cryptography not available - audit signatures disabled")
            self.signing_key = None
            self.verify_key = None
            return
        
        # Generate or load signing key
        if signing_key_file.exists():
            # Load existing private key
            with open(signing_key_file, 'rb') as f:
                private_key_data = f.read()
            
            self.signing_key = load_pem_private_key(private_key_data, password=None)
            logger.info("Loaded existing audit signing key")
        else:
            # Generate new RSA key pair
            logger.info("Generating new audit signing key pair...")
            
            self.signing_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Save private key
            private_key_pem = self.signing_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            with open(signing_key_file, 'wb') as f:
                f.write(private_key_pem)
            
            os.chmod(signing_key_file, 0o600)
            
            # Save public key
            public_key = self.signing_key.public_key()
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            with open(verify_key_file, 'wb') as f:
                f.write(public_key_pem)
            
            os.chmod(verify_key_file, 0o644)
            
            logger.info(f"Generated new audit key pair: {signing_key_file}")
        
        # Load public key for verification
        if verify_key_file.exists():
            with open(verify_key_file, 'rb') as f:
                public_key_data = f.read()
            
            self.verify_key = load_pem_public_key(public_key_data)
        else:
            # Extract public key from private key
            self.verify_key = self.signing_key.public_key()
    
    def _generate_record_id(self) -> str:
        """Generate unique audit record ID."""
        import secrets
        timestamp = int(time.time() * 1000000)  # microsecond precision
        random_suffix = secrets.token_hex(8)
        return f"audit_{timestamp}_{random_suffix}"
    
    def _calculate_chain_hash(self, record: AuditRecord, previous_hash: str) -> str:
        """Calculate hash for audit chain integrity."""
        
        # Create deterministic record representation
        record_data = {
            "record_id": record.record_id,
            "timestamp": record.timestamp,
            "user_id": record.user_id,
            "action": record.action,
            "resource_type": record.resource_type,
            "resource_id": record.resource_id,
            "source_ip": record.source_ip,
            "endpoint": record.endpoint,
            "status_code": record.status_code,
            "previous_hash": previous_hash
        }
        
        # Create canonical JSON representation
        canonical_json = json.dumps(record_data, sort_keys=True, separators=(',', ':'))
        
        # Calculate SHA-256 hash
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    def _sign_record(self, record: AuditRecord) -> Optional[str]:
        """Create digital signature for audit record."""
        
        if not CRYPTO_AVAILABLE or not self.signing_key:
            return None
        
        try:
            # Create signable content
            signable_content = {
                "record_id": record.record_id,
                "timestamp": record.timestamp,
                "chain_hash": record.chain_hash,
                "action": record.action,
                "user_id": record.user_id,
                "resource_type": record.resource_type,
                "source_ip": record.source_ip
            }
            
            canonical_json = json.dumps(signable_content, sort_keys=True, separators=(',', ':'))
            content_bytes = canonical_json.encode('utf-8')
            
            # Create RSA signature
            signature = self.signing_key.sign(
                content_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Return base64-encoded signature
            import base64
            return base64.b64encode(signature).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to sign audit record: {e}")
            return None
    
    def _verify_record_signature(self, record: AuditRecord) -> bool:
        """Verify audit record digital signature."""
        
        if not CRYPTO_AVAILABLE or not self.verify_key or not record.signature:
            return True  # Skip verification if crypto not available
        
        try:
            # Reconstruct signable content
            signable_content = {
                "record_id": record.record_id,
                "timestamp": record.timestamp,
                "chain_hash": record.chain_hash,
                "action": record.action,
                "user_id": record.user_id,
                "resource_type": record.resource_type,
                "source_ip": record.source_ip
            }
            
            canonical_json = json.dumps(signable_content, sort_keys=True, separators=(',', ':'))
            content_bytes = canonical_json.encode('utf-8')
            
            # Decode signature
            import base64
            signature_bytes = base64.b64decode(record.signature.encode('utf-8'))
            
            # Verify signature
            self.verify_key.verify(
                signature_bytes,
                content_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            self.metrics.signature_verifications += 1
            return True
            
        except InvalidSignature:
            logger.error(f"Invalid signature for audit record {record.record_id}")
            return False
        except Exception as e:
            logger.error(f"Signature verification error for record {record.record_id}: {e}")
            return False
    
    def log_audit_event(self, 
                       action: str,
                       resource_type: str,
                       user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       resource_id: Optional[str] = None,
                       source_ip: str = "unknown",
                       user_agent: str = "",
                       request_method: str = "UNKNOWN",
                       endpoint: str = "/unknown",
                       status_code: int = 200,
                       details: Optional[Dict[str, Any]] = None,
                       risk_level: str = "LOW") -> str:
        """Log an audit event with integrity protection."""
        
        with self.lock:
            # Generate record ID
            record_id = self._generate_record_id()
            current_time = time.time()
            
            # Prepare details
            audit_details = details or {}
            
            # Calculate chain hash
            chain_hash = self._calculate_chain_hash(
                AuditRecord(
                    record_id=record_id,
                    timestamp=current_time,
                    user_id=user_id,
                    session_id=session_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    source_ip=source_ip,
                    user_agent=user_agent,
                    request_method=request_method,
                    endpoint=endpoint,
                    status_code=status_code,
                    details=audit_details,
                    risk_level=risk_level,
                    chain_hash="",  # Will be calculated
                    signature=None
                ),
                self.last_chain_hash
            )
            
            # Create audit record
            audit_record = AuditRecord(
                record_id=record_id,
                timestamp=current_time,
                user_id=user_id,
                session_id=session_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                source_ip=source_ip,
                user_agent=user_agent,
                request_method=request_method,
                endpoint=endpoint,
                status_code=status_code,
                details=audit_details,
                risk_level=risk_level,
                chain_hash=chain_hash,
                signature=None
            )
            
            # Sign the record
            signature = self._sign_record(audit_record)
            audit_record.signature = signature
            
            # Store in database
            try:
                self.db_conn.execute("""
                    INSERT INTO audit_records (
                        record_id, timestamp, user_id, session_id, action, 
                        resource_type, resource_id, source_ip, user_agent,
                        request_method, endpoint, status_code, details,
                        risk_level, chain_hash, signature
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    audit_record.record_id,
                    audit_record.timestamp,
                    audit_record.user_id,
                    audit_record.session_id,
                    audit_record.action,
                    audit_record.resource_type,
                    audit_record.resource_id,
                    audit_record.source_ip,
                    audit_record.user_agent,
                    audit_record.request_method,
                    audit_record.endpoint,
                    audit_record.status_code,
                    json.dumps(audit_record.details),
                    audit_record.risk_level,
                    audit_record.chain_hash,
                    audit_record.signature
                ))
                
                self.db_conn.commit()
                
                # Update chain state
                self.last_chain_hash = chain_hash
                self.record_count += 1
                
                # Update metrics
                self.metrics.total_records += 1
                self.metrics.records_by_action[action] = self.metrics.records_by_action.get(action, 0) + 1
                if user_id:
                    self.metrics.records_by_user[user_id] = self.metrics.records_by_user.get(user_id, 0) + 1
                self.metrics.records_by_risk[risk_level] = self.metrics.records_by_risk.get(risk_level, 0) + 1
                
                logger.debug(f"Audit record logged: {record_id} - {action}")
                
                # Log security events for high-risk audit records
                if risk_level in ["HIGH", "CRITICAL"] and SECURITY_MONITORING_AVAILABLE:
                    log_security_event(
                        severity="MEDIUM",
                        threat_type="anomalous_behavior",
                        source_ip=source_ip,
                        endpoint=endpoint,
                        method=request_method,
                        description=f"High-risk audit event: {action}",
                        details={
                            "audit_record_id": record_id,
                            "action": action,
                            "resource_type": resource_type,
                            "risk_level": risk_level
                        },
                        user_agent=user_agent,
                        user_id=user_id
                    )
                
                return record_id
                
            except Exception as e:
                logger.error(f"Failed to store audit record: {e}")
                raise
    
    def verify_audit_integrity(self, start_record: Optional[str] = None, 
                              end_record: Optional[str] = None) -> Dict[str, Any]:
        """Verify integrity of audit trail chain."""
        
        logger.info("Starting audit trail integrity verification...")
        
        with self.lock:
            integrity_result = {
                "verification_timestamp": time.time(),
                "records_verified": 0,
                "chain_integrity": True,
                "signature_integrity": True,
                "violations_found": [],
                "chain_breaks": 0,
                "signature_failures": 0,
                "start_record": start_record,
                "end_record": end_record
            }
            
            try:
                # Build query for record range
                query = "SELECT * FROM audit_records ORDER BY timestamp ASC"
                params = []
                
                if start_record:
                    query += " WHERE timestamp >= (SELECT timestamp FROM audit_records WHERE record_id = ?)"
                    params.append(start_record)
                    
                    if end_record:
                        query += " AND timestamp <= (SELECT timestamp FROM audit_records WHERE record_id = ?)"
                        params.append(end_record)
                elif end_record:
                    query += " WHERE timestamp <= (SELECT timestamp FROM audit_records WHERE record_id = ?)"
                    params.append(end_record)
                
                cursor = self.db_conn.execute(query, params)
                records = cursor.fetchall()
                
                if not records:
                    logger.warning("No audit records found for verification")
                    return integrity_result
                
                previous_hash = "" if not start_record else None
                
                for row in records:
                    record = AuditRecord(
                        record_id=row['record_id'],
                        timestamp=row['timestamp'],
                        user_id=row['user_id'],
                        session_id=row['session_id'],
                        action=row['action'],
                        resource_type=row['resource_type'],
                        resource_id=row['resource_id'],
                        source_ip=row['source_ip'],
                        user_agent=row['user_agent'],
                        request_method=row['request_method'],
                        endpoint=row['endpoint'],
                        status_code=row['status_code'],
                        details=json.loads(row['details']),
                        risk_level=row['risk_level'],
                        chain_hash=row['chain_hash'],
                        signature=row['signature']
                    )
                    
                    # Verify chain integrity
                    if previous_hash is not None:
                        expected_hash = self._calculate_chain_hash(record, previous_hash)
                        
                        if expected_hash != record.chain_hash:
                            integrity_result["chain_integrity"] = False
                            integrity_result["chain_breaks"] += 1
                            integrity_result["violations_found"].append({
                                "type": "chain_break",
                                "record_id": record.record_id,
                                "expected_hash": expected_hash,
                                "actual_hash": record.chain_hash,
                                "timestamp": record.timestamp
                            })
                    
                    # Verify digital signature
                    if not self._verify_record_signature(record):
                        integrity_result["signature_integrity"] = False
                        integrity_result["signature_failures"] += 1
                        integrity_result["violations_found"].append({
                            "type": "signature_failure",
                            "record_id": record.record_id,
                            "timestamp": record.timestamp
                        })
                    
                    previous_hash = record.chain_hash
                    integrity_result["records_verified"] += 1
                
                # Update metrics
                if integrity_result["chain_integrity"] and integrity_result["signature_integrity"]:
                    self.metrics.integrity_checks_passed += 1
                else:
                    self.metrics.integrity_violations += 1
                
                self.metrics.chain_breaks_detected += integrity_result["chain_breaks"]
                self.metrics.last_integrity_check = time.time()
                
                # Store integrity check result
                self._store_integrity_check(integrity_result)
                
                logger.info(f"Audit integrity verification completed: "
                          f"{integrity_result['records_verified']} records, "
                          f"{integrity_result['chain_breaks']} chain breaks, "
                          f"{integrity_result['signature_failures']} signature failures")
                
                return integrity_result
                
            except Exception as e:
                logger.error(f"Audit integrity verification failed: {e}")
                integrity_result["error"] = str(e)
                return integrity_result
    
    def _store_integrity_check(self, result: Dict[str, Any]):
        """Store integrity check results."""
        
        try:
            self.db_conn.execute("""
                INSERT INTO audit_integrity (
                    check_timestamp, records_verified, integrity_status,
                    violations_found, chain_breaks, signature_failures, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result["verification_timestamp"],
                result["records_verified"],
                "PASS" if result["chain_integrity"] and result["signature_integrity"] else "FAIL",
                len(result["violations_found"]),
                result["chain_breaks"],
                result["signature_failures"],
                json.dumps(result["violations_found"])
            ))
            
            self.db_conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to store integrity check result: {e}")
    
    def _load_audit_state(self):
        """Load existing audit trail state."""
        
        try:
            # Get latest record for chain hash
            cursor = self.db_conn.execute(
                "SELECT chain_hash FROM audit_records ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            
            if row:
                self.last_chain_hash = row['chain_hash']
            
            # Get total record count
            cursor = self.db_conn.execute("SELECT COUNT(*) as count FROM audit_records")
            row = cursor.fetchone()
            self.record_count = row['count'] if row else 0
            
            # Load metrics
            cursor = self.db_conn.execute("""
                SELECT action, COUNT(*) as count 
                FROM audit_records 
                GROUP BY action
            """)
            for row in cursor.fetchall():
                self.metrics.records_by_action[row['action']] = row['count']
            
            cursor = self.db_conn.execute("""
                SELECT risk_level, COUNT(*) as count 
                FROM audit_records 
                GROUP BY risk_level
            """)
            for row in cursor.fetchall():
                self.metrics.records_by_risk[row['risk_level']] = row['count']
            
            self.metrics.total_records = self.record_count
            
        except Exception as e:
            logger.error(f"Failed to load audit state: {e}")
    
    def _integrity_monitor(self):
        """Background integrity monitoring worker."""
        
        while self.integrity_monitor_active:
            try:
                time.sleep(self.integrity_check_interval)
                
                if not self.integrity_monitor_active:
                    break
                
                # Perform periodic integrity check
                logger.info("Performing scheduled audit integrity check...")
                integrity_result = self.verify_audit_integrity()
                
                # Alert on integrity violations
                if not integrity_result["chain_integrity"] or not integrity_result["signature_integrity"]:
                    logger.critical(f"AUDIT INTEGRITY VIOLATION DETECTED: "
                                  f"{integrity_result['chain_breaks']} chain breaks, "
                                  f"{integrity_result['signature_failures']} signature failures")
                    
                    if SECURITY_MONITORING_AVAILABLE:
                        log_security_event(
                            severity="CRITICAL",
                            threat_type="anomalous_behavior",
                            source_ip="system",
                            endpoint="/audit/integrity",
                            method="INTERNAL",
                            description="Audit trail integrity violation detected",
                            details={
                                "chain_breaks": integrity_result["chain_breaks"],
                                "signature_failures": integrity_result["signature_failures"],
                                "violations": integrity_result["violations_found"]
                            }
                        )
                
            except Exception as e:
                logger.error(f"Integrity monitor error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def get_audit_records(self, 
                         limit: int = 100,
                         offset: int = 0,
                         user_id: Optional[str] = None,
                         action: Optional[str] = None,
                         risk_level: Optional[str] = None,
                         start_time: Optional[float] = None,
                         end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve audit records with filtering."""
        
        query = "SELECT * FROM audit_records WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if action:
            query += " AND action = ?"
            params.append(action)
        
        if risk_level:
            query += " AND risk_level = ?"
            params.append(risk_level)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self.db_conn.execute(query, params)
        records = []
        
        for row in cursor.fetchall():
            records.append({
                "record_id": row['record_id'],
                "timestamp": row['timestamp'],
                "user_id": row['user_id'],
                "session_id": row['session_id'],
                "action": row['action'],
                "resource_type": row['resource_type'],
                "resource_id": row['resource_id'],
                "source_ip": row['source_ip'],
                "user_agent": row['user_agent'],
                "request_method": row['request_method'],
                "endpoint": row['endpoint'],
                "status_code": row['status_code'],
                "details": json.loads(row['details']),
                "risk_level": row['risk_level'],
                "has_signature": bool(row['signature']),
                "formatted_timestamp": datetime.fromtimestamp(row['timestamp'], tz=timezone.utc).isoformat()
            })
        
        return records
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get comprehensive audit trail statistics."""
        
        return {
            "audit_enabled": True,
            "total_records": self.metrics.total_records,
            "chain_hash_current": self.last_chain_hash,
            "metrics": {
                "records_by_action": dict(self.metrics.records_by_action),
                "records_by_risk": dict(self.metrics.records_by_risk),
                "integrity_checks_passed": self.metrics.integrity_checks_passed,
                "integrity_violations": self.metrics.integrity_violations,
                "chain_breaks_detected": self.metrics.chain_breaks_detected,
                "signature_verifications": self.metrics.signature_verifications,
                "last_integrity_check": self.metrics.last_integrity_check
            },
            "security_features": {
                "digital_signatures": CRYPTO_AVAILABLE,
                "chain_integrity": True,
                "tamper_detection": True,
                "background_monitoring": self.integrity_monitor_active
            },
            "timestamp": time.time()
        }
    
    def shutdown(self):
        """Shutdown audit trail manager."""
        
        self.integrity_monitor_active = False
        if hasattr(self, 'integrity_thread') and self.integrity_thread.is_alive():
            self.integrity_thread.join(timeout=5)
        
        if hasattr(self, 'db_conn'):
            self.db_conn.close()
        
        logger.info("Audit Trail Manager shutdown completed")


# Global audit trail manager instance
audit_manager = None


def get_audit_manager() -> AuditTrailManager:
    """Get or create global audit manager instance."""
    global audit_manager
    if audit_manager is None:
        audit_manager = AuditTrailManager()
    return audit_manager


def log_audit(action: str, resource_type: str, **kwargs) -> str:
    """Convenience function for logging audit events."""
    return get_audit_manager().log_audit_event(action, resource_type, **kwargs)


def verify_audit_integrity() -> Dict[str, Any]:
    """Convenience function for integrity verification."""
    return get_audit_manager().verify_audit_integrity()