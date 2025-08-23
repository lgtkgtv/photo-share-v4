#!/usr/bin/env python3
"""
Secure Session State Management System
=====================================

Comprehensive session management with security controls, device fingerprinting,
concurrent session limits, and secure session storage.
"""

import os
import time
import json
import hashlib
import secrets
import logging
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from threading import Lock
import ipaddress

# Redis support (optional)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Cryptographic imports
try:
    from cryptography.fernet import Fernet
    import jwt
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class DeviceFingerprint:
    """Device fingerprint for session validation."""
    user_agent_hash: str
    ip_address: str
    ip_country: Optional[str]
    screen_resolution: Optional[str]
    timezone: Optional[str]
    language: Optional[str]
    platform: Optional[str]
    fingerprint_hash: str


@dataclass
class SessionState:
    """Secure session state with metadata."""
    session_id: str
    user_id: str
    created_at: float
    last_activity: float
    expires_at: float
    device_fingerprint: DeviceFingerprint
    is_active: bool
    ip_address: str
    user_agent: str
    session_data: Dict[str, Any]
    security_level: str  # basic, elevated, admin
    concurrent_session_count: int
    last_security_check: float
    anomaly_score: float


@dataclass
class SessionSecurityEvent:
    """Session security event record."""
    event_id: str
    session_id: str
    event_type: str  # login, logout, anomaly, hijack_attempt, etc.
    timestamp: float
    details: Dict[str, Any]
    risk_score: float
    action_taken: str  # allow, block, alert, force_logout


class SecureSessionManager:
    """Advanced secure session management with threat detection."""
    
    def __init__(self, secure_dir: str = None, redis_config: Dict[str, Any] = None):
        self.secure_dir = secure_dir or self._get_secure_directory()
        self.db_path = os.path.join(self.secure_dir, "session_security.db")
        self.lock = Lock()
        
        # Session storage
        self.active_sessions: Dict[str, SessionState] = {}
        self.session_events: List[SessionSecurityEvent] = []
        
        # Redis configuration
        self.redis_client = None
        if REDIS_AVAILABLE and redis_config:
            try:
                self.redis_client = redis.Redis(**redis_config)
                self.redis_client.ping()  # Test connection
                logger.info("Redis session storage connected")
            except Exception as e:
                logger.warning(f"Redis connection failed, using SQLite: {e}")
                self.redis_client = None
        
        # Create secure directory
        os.makedirs(self.secure_dir, mode=0o700, exist_ok=True)
        
        # Initialize components
        self._init_database()
        self._load_encryption_key()
        self._load_session_config()
        
        # Start background tasks
        self._start_session_cleanup_thread()
        self._start_anomaly_detection_thread()
        
        logger.info(f"Secure Session Manager initialized: {self.secure_dir}")
    
    def _get_secure_directory(self) -> str:
        """Get secure directory for session storage."""
        return "./vault-like-secure-storage/sessions" if not os.path.exists("/app") else "/app/vault-like-secure-storage/sessions"
    
    def _init_database(self):
        """Initialize SQLite database for session management."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        last_activity REAL NOT NULL,
                        expires_at REAL NOT NULL,
                        device_fingerprint TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        ip_address TEXT NOT NULL,
                        user_agent TEXT,
                        session_data TEXT,
                        security_level TEXT DEFAULT 'basic',
                        concurrent_session_count INTEGER DEFAULT 1,
                        last_security_check REAL,
                        anomaly_score REAL DEFAULT 0.0
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS session_events (
                        event_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        details TEXT,
                        risk_score REAL,
                        action_taken TEXT,
                        FOREIGN KEY (session_id) REFERENCES user_sessions (session_id)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS device_fingerprints (
                        fingerprint_hash TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        first_seen REAL NOT NULL,
                        last_seen REAL NOT NULL,
                        trust_score REAL DEFAULT 50.0,
                        device_info TEXT,
                        active BOOLEAN DEFAULT 1
                    )
                """)
                
                # Indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON session_events(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_fingerprints_user ON device_fingerprints(user_id)")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _load_encryption_key(self):
        """Load or create encryption key for session data."""
        key_file = os.path.join(self.secure_dir, "session_encryption.key")
        
        try:
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    key_data = f.read()
                self.encryption_key = key_data
            else:
                if CRYPTO_AVAILABLE:
                    self.encryption_key = Fernet.generate_key()
                    with open(key_file, 'wb') as f:
                        f.write(self.encryption_key)
                    os.chmod(key_file, 0o600)
                else:
                    self.encryption_key = os.urandom(32)
                    with open(key_file, 'wb') as f:
                        f.write(self.encryption_key)
                    os.chmod(key_file, 0o600)
            
            if CRYPTO_AVAILABLE:
                self.fernet = Fernet(self.encryption_key)
            else:
                self.fernet = None
                
        except Exception as e:
            logger.error(f"Failed to load session encryption key: {e}")
            raise
    
    def _load_session_config(self):
        """Load session security configuration."""
        self.config = {
            'session_timeout': 1800,  # 30 minutes
            'max_concurrent_sessions': 5,
            'session_renewal_threshold': 300,  # 5 minutes before expiry
            'device_fingerprint_required': True,
            'anomaly_detection_enabled': True,
            'security_check_interval': 300,  # 5 minutes
            'max_anomaly_score': 70.0,
            'session_encryption_enabled': CRYPTO_AVAILABLE,
            'geo_location_validation': True,
            'suspicious_ip_blocking': True,
        }
    
    def create_device_fingerprint(
        self,
        user_agent: str,
        ip_address: str,
        additional_data: Dict[str, Any] = None
    ) -> DeviceFingerprint:
        """Create device fingerprint for session validation."""
        try:
            # Hash user agent for privacy
            user_agent_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
            
            # Extract country from IP (basic implementation)
            ip_country = self._get_ip_country(ip_address)
            
            # Extract additional fingerprint data
            additional_data = additional_data or {}
            screen_resolution = additional_data.get('screen_resolution')
            timezone = additional_data.get('timezone')
            language = additional_data.get('language')
            platform = additional_data.get('platform')
            
            # Create composite fingerprint hash
            fingerprint_components = [
                user_agent_hash,
                ip_address,  # Include full IP address in fingerprint
                ip_country or 'unknown',
                screen_resolution or 'unknown',
                timezone or 'unknown',
                language or 'unknown',
                platform or 'unknown'
            ]
            
            fingerprint_data = '|'.join(fingerprint_components)
            fingerprint_hash = hashlib.sha256(fingerprint_data.encode()).hexdigest()
            
            return DeviceFingerprint(
                user_agent_hash=user_agent_hash,
                ip_address=ip_address,
                ip_country=ip_country,
                screen_resolution=screen_resolution,
                timezone=timezone,
                language=language,
                platform=platform,
                fingerprint_hash=fingerprint_hash
            )
            
        except Exception as e:
            logger.error(f"Failed to create device fingerprint: {e}")
            # Return basic fingerprint on error
            return DeviceFingerprint(
                user_agent_hash=hashlib.sha256(user_agent.encode()).hexdigest()[:16],
                ip_address=ip_address,
                ip_country=None,
                screen_resolution=None,
                timezone=None,
                language=None,
                platform=None,
                fingerprint_hash=hashlib.sha256(f"{user_agent}|{ip_address}".encode()).hexdigest()
            )
    
    def _get_ip_country(self, ip_address: str) -> Optional[str]:
        """Get country code from IP address (basic implementation)."""
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Local/private IPs
            if ip.is_private or ip.is_loopback:
                return "LOCAL"
            
            # Basic geolocation (would use GeoIP database in production)
            # For now, return placeholder
            return "UNKNOWN"
            
        except Exception:
            return "UNKNOWN"
    
    def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        security_level: str = "basic",
        additional_fingerprint_data: Dict[str, Any] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Create new secure session with device fingerprinting."""
        try:
            # Check concurrent session limit
            if not self._check_concurrent_session_limit(user_id):
                logger.warning(f"Concurrent session limit exceeded for user {user_id}")
                return None, "Maximum concurrent sessions exceeded"
            
            # Create device fingerprint
            device_fingerprint = self.create_device_fingerprint(
                user_agent, ip_address, additional_fingerprint_data
            )
            
            # Check device trust score
            trust_score = self._get_device_trust_score(user_id, device_fingerprint.fingerprint_hash)
            if trust_score < 30.0:  # Low trust threshold
                logger.warning(f"Low device trust score for user {user_id}: {trust_score}")
                # Could require additional authentication here
            
            # Generate secure session ID
            session_id = self._generate_session_id()
            current_time = time.time()
            expires_at = current_time + self.config['session_timeout']
            
            # Count existing active sessions
            concurrent_count = self._get_active_session_count(user_id)
            
            # Create session state
            session_state = SessionState(
                session_id=session_id,
                user_id=user_id,
                created_at=current_time,
                last_activity=current_time,
                expires_at=expires_at,
                device_fingerprint=device_fingerprint,
                is_active=True,
                ip_address=ip_address,
                user_agent=user_agent,
                session_data={},
                security_level=security_level,
                concurrent_session_count=concurrent_count + 1,
                last_security_check=current_time,
                anomaly_score=0.0
            )
            
            # Store session
            self._store_session(session_state)
            
            # Update device fingerprint record
            self._update_device_fingerprint(user_id, device_fingerprint, trust_score)
            
            # Calculate initial risk score for the session
            initial_risk = self._calculate_initial_session_risk(
                user_id, ip_address, security_level, trust_score
            )
            
            # Log session creation event
            self._log_session_event(
                session_id=session_id,
                event_type="session_created",
                details={
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "security_level": security_level,
                    "device_trust_score": trust_score
                },
                risk_score=initial_risk,
                action_taken="allow"
            )
            
            logger.info(f"Session created for user {user_id}: {session_id}")
            return session_id, None
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            return None, f"Session creation failed: {str(e)}"
    
    def validate_session(
        self,
        session_id: str,
        ip_address: str,
        user_agent: str
    ) -> Tuple[bool, Optional[SessionState], Optional[str]]:
        """Validate session with security checks."""
        try:
            # Retrieve session
            session_state = self._get_session(session_id)
            if not session_state:
                return False, None, "Session not found"
            
            # Check if session is active
            if not session_state.is_active:
                return False, None, "Session inactive"
            
            # Check expiration
            current_time = time.time()
            if current_time > session_state.expires_at:
                self._invalidate_session(session_id, "expired")
                return False, None, "Session expired"
            
            # Device fingerprint validation
            if self.config['device_fingerprint_required']:
                device_fingerprint = self.create_device_fingerprint(user_agent, ip_address)
                
                # Check for device changes (potential session hijacking)
                if not self._validate_device_fingerprint(session_state, device_fingerprint):
                    logger.warning(f"Device fingerprint mismatch for session {session_id}")
                    
                    # Log potential hijacking attempt
                    self._log_session_event(
                        session_id=session_id,
                        event_type="device_fingerprint_mismatch",
                        details={
                            "original_ip": session_state.ip_address,
                            "current_ip": ip_address,
                            "original_fingerprint": session_state.device_fingerprint.fingerprint_hash,
                            "current_fingerprint": device_fingerprint.fingerprint_hash
                        },
                        risk_score=85.0,  # High risk
                        action_taken="block"
                    )
                    
                    # Invalidate session on suspicious activity
                    self._invalidate_session(session_id, "device_fingerprint_mismatch")
                    return False, None, "Session security violation detected"
            
            # IP address validation
            if session_state.ip_address != ip_address:
                # Calculate IP change risk
                ip_risk = self._calculate_ip_change_risk(session_state.ip_address, ip_address)
                
                if ip_risk > 70.0:  # High risk threshold
                    logger.warning(f"High-risk IP change for session {session_id}: {session_state.ip_address} -> {ip_address}")
                    
                    self._log_session_event(
                        session_id=session_id,
                        event_type="suspicious_ip_change",
                        details={
                            "original_ip": session_state.ip_address,
                            "new_ip": ip_address,
                            "risk_score": ip_risk
                        },
                        risk_score=ip_risk,
                        action_taken="alert"
                    )
                    
                    # Could require re-authentication here for high-risk changes
            
            # Update session activity
            session_state.last_activity = current_time
            session_state.ip_address = ip_address  # Update current IP
            
            # Perform periodic security checks
            if current_time - session_state.last_security_check > self.config['security_check_interval']:
                self._perform_security_check(session_state)
            
            # Update anomaly score
            anomaly_score = self._calculate_anomaly_score(session_state)
            session_state.anomaly_score = anomaly_score
            
            if anomaly_score > self.config['max_anomaly_score']:
                logger.warning(f"High anomaly score for session {session_id}: {anomaly_score}")
                
                self._log_session_event(
                    session_id=session_id,
                    event_type="high_anomaly_score",
                    details={"anomaly_score": anomaly_score},
                    risk_score=anomaly_score,
                    action_taken="alert"
                )
                
                # Could force re-authentication or session invalidation
            
            # Auto-renew session if close to expiry
            time_to_expiry = session_state.expires_at - current_time
            if time_to_expiry < self.config['session_renewal_threshold']:
                session_state.expires_at = current_time + self.config['session_timeout']
                logger.debug(f"Session renewed for {session_id}")
            
            # Store updated session
            self._store_session(session_state)
            
            return True, session_state, None
            
        except Exception as e:
            logger.error(f"Session validation failed for {session_id}: {e}")
            return False, None, f"Validation error: {str(e)}"
    
    def _validate_device_fingerprint(
        self,
        session_state: SessionState,
        current_fingerprint: DeviceFingerprint
    ) -> bool:
        """Validate device fingerprint consistency."""
        original = session_state.device_fingerprint
        current = current_fingerprint
        
        # Critical components that should never change
        if original.user_agent_hash != current.user_agent_hash:
            return False
        
        # IP changes are allowed but monitored
        # Other components can change but contribute to anomaly score
        
        return True
    
    def _calculate_ip_change_risk(self, original_ip: str, new_ip: str) -> float:
        """Calculate risk score for IP address changes."""
        try:
            orig_ip = ipaddress.ip_address(original_ip)
            new_ip_obj = ipaddress.ip_address(new_ip)
            
            # Same IP = no risk
            if orig_ip == new_ip_obj:
                return 0.0
            
            # Both private IPs = low risk
            if orig_ip.is_private and new_ip_obj.is_private:
                return 20.0
            
            # Private to public or vice versa = medium risk
            if orig_ip.is_private != new_ip_obj.is_private:
                return 50.0
            
            # Different public IPs = higher risk (could check geolocation)
            return 70.0
            
        except Exception:
            return 60.0  # Default medium risk for parsing errors
    
    def _calculate_initial_session_risk(
        self,
        user_id: str,
        ip_address: str,
        security_level: str,
        device_trust_score: float
    ) -> float:
        """Calculate initial risk score for new session."""
        risk_score = 0.0
        
        try:
            # Security level risk
            security_risk = {
                "basic": 10.0,
                "elevated": 25.0,
                "admin": 40.0
            }
            risk_score += security_risk.get(security_level, 20.0)
            
            # Device trust score impact (inverted - low trust = high risk)
            if device_trust_score < 30.0:
                risk_score += 30.0
            elif device_trust_score < 50.0:
                risk_score += 15.0
            elif device_trust_score < 70.0:
                risk_score += 5.0
            
            # IP address risk
            try:
                ip = ipaddress.ip_address(ip_address)
                if not ip.is_private:
                    risk_score += 10.0  # Public IPs are riskier
            except:
                risk_score += 15.0  # Invalid IP format
            
            # Check for existing active sessions (concurrent risk)
            active_count = self._get_active_session_count(user_id)
            if active_count >= 3:
                risk_score += 20.0
            elif active_count >= 1:
                risk_score += 10.0
            
            return min(100.0, risk_score)
            
        except Exception as e:
            logger.error(f"Initial risk calculation failed: {e}")
            return 50.0  # Default medium risk
    
    def _calculate_anomaly_score(self, session_state: SessionState) -> float:
        """Calculate anomaly score based on session behavior."""
        score = 0.0
        current_time = time.time()
        
        try:
            # Session age factor
            session_age = current_time - session_state.created_at
            if session_age > 86400:  # Over 24 hours
                score += 20.0
            elif session_age > 43200:  # Over 12 hours
                score += 10.0
            
            # Activity pattern analysis
            time_since_activity = current_time - session_state.last_activity
            if time_since_activity < 60:  # Very frequent activity
                score += 5.0
            elif time_since_activity > 1800:  # Long inactivity
                score += 15.0
            
            # Security level vs activity
            if session_state.security_level == "admin":
                score += 10.0  # Admin sessions are higher risk
            
            # Concurrent sessions
            if session_state.concurrent_session_count > 3:
                score += 20.0
            elif session_state.concurrent_session_count > 1:
                score += 10.0
            
            return min(100.0, score)
            
        except Exception as e:
            logger.error(f"Anomaly score calculation failed: {e}")
            return 50.0  # Default medium risk
    
    def _perform_security_check(self, session_state: SessionState):
        """Perform comprehensive security check on session."""
        try:
            current_time = time.time()
            session_state.last_security_check = current_time
            
            # Check for suspicious patterns
            security_issues = []
            
            # Check for rapid IP changes
            recent_events = self._get_recent_session_events(
                session_state.session_id, 
                hours_back=1,
                event_types=["suspicious_ip_change"]
            )
            
            if len(recent_events) > 3:  # More than 3 IP changes in 1 hour
                security_issues.append("frequent_ip_changes")
            
            # Check session duration
            session_duration = current_time - session_state.created_at
            if session_duration > 86400:  # Over 24 hours
                security_issues.append("long_session_duration")
            
            # Log security check results
            if security_issues:
                self._log_session_event(
                    session_id=session_state.session_id,
                    event_type="security_check_issues",
                    details={"issues": security_issues},
                    risk_score=len(security_issues) * 20.0,
                    action_taken="alert"
                )
                
        except Exception as e:
            logger.error(f"Security check failed for session {session_state.session_id}: {e}")
    
    def invalidate_session(self, session_id: str, reason: str = "logout") -> bool:
        """Invalidate session (user logout or security violation)."""
        return self._invalidate_session(session_id, reason)
    
    def _invalidate_session(self, session_id: str, reason: str) -> bool:
        """Internal session invalidation."""
        try:
            session_state = self._get_session(session_id)
            if not session_state:
                return False
            
            # Mark session as inactive
            session_state.is_active = False
            self._store_session(session_state)
            
            # Remove from active sessions cache
            with self.lock:
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
            
            # Remove from Redis if available
            if self.redis_client:
                try:
                    self.redis_client.delete(f"session:{session_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove session from Redis: {e}")
            
            # Log invalidation event
            self._log_session_event(
                session_id=session_id,
                event_type="session_invalidated",
                details={"reason": reason},
                risk_score=0.0 if reason == "logout" else 50.0,
                action_taken="invalidate"
            )
            
            logger.info(f"Session invalidated: {session_id} (reason: {reason})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate session {session_id}: {e}")
            return False
    
    def invalidate_all_user_sessions(self, user_id: str, except_session: str = None) -> int:
        """Invalidate all sessions for a user (except optionally one)."""
        try:
            invalidated_count = 0
            
            # Get all active sessions for user
            user_sessions = self._get_user_sessions(user_id, active_only=True)
            
            for session_state in user_sessions:
                if except_session and session_state.session_id == except_session:
                    continue  # Skip this session
                
                if self._invalidate_session(session_state.session_id, "force_logout"):
                    invalidated_count += 1
            
            logger.info(f"Invalidated {invalidated_count} sessions for user {user_id}")
            return invalidated_count
            
        except Exception as e:
            logger.error(f"Failed to invalidate user sessions for {user_id}: {e}")
            return 0
    
    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID."""
        timestamp = int(time.time() * 1000000)  # microseconds
        random_component = secrets.token_urlsafe(32)
        return f"sess_{timestamp}_{random_component}"
    
    def _check_concurrent_session_limit(self, user_id: str) -> bool:
        """Check if user is within concurrent session limit."""
        try:
            active_count = self._get_active_session_count(user_id)
            return active_count < self.config['max_concurrent_sessions']
        except Exception as e:
            logger.error(f"Failed to check concurrent session limit: {e}")
            return False  # Err on the side of caution
    
    def _get_active_session_count(self, user_id: str) -> int:
        """Get count of active sessions for user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    SELECT COUNT(*) FROM user_sessions 
                    WHERE user_id = ? AND is_active = 1 AND expires_at > ?
                """, (user_id, time.time())).fetchone()
                
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"Failed to get active session count for {user_id}: {e}")
            return 0
    
    def _get_user_sessions(self, user_id: str, active_only: bool = True) -> List[SessionState]:
        """Get all sessions for a user."""
        try:
            query = "SELECT * FROM user_sessions WHERE user_id = ?"
            params = [user_id]
            
            if active_only:
                query += " AND is_active = 1 AND expires_at > ?"
                params.append(time.time())
            
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(query, params).fetchall()
                
                sessions = []
                for row in rows:
                    session_state = self._row_to_session_state(row)
                    if session_state:
                        sessions.append(session_state)
                
                return sessions
                
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []
    
    def _store_session(self, session_state: SessionState):
        """Store session in database and cache."""
        try:
            # Store in SQLite
            device_fingerprint_json = json.dumps(asdict(session_state.device_fingerprint))
            session_data_json = json.dumps(session_state.session_data)
            
            # Encrypt sensitive data if available
            if self.fernet:
                session_data_json = self.fernet.encrypt(session_data_json.encode()).decode()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_sessions
                    (session_id, user_id, created_at, last_activity, expires_at,
                     device_fingerprint, is_active, ip_address, user_agent,
                     session_data, security_level, concurrent_session_count,
                     last_security_check, anomaly_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_state.session_id,
                    session_state.user_id,
                    session_state.created_at,
                    session_state.last_activity,
                    session_state.expires_at,
                    device_fingerprint_json,
                    session_state.is_active,
                    session_state.ip_address,
                    session_state.user_agent,
                    session_data_json,
                    session_state.security_level,
                    session_state.concurrent_session_count,
                    session_state.last_security_check,
                    session_state.anomaly_score
                ))
            
            # Store in memory cache
            with self.lock:
                self.active_sessions[session_state.session_id] = session_state
            
            # Store in Redis if available
            if self.redis_client and session_state.is_active:
                try:
                    session_json = json.dumps(asdict(session_state), default=str)
                    ttl = int(session_state.expires_at - time.time())
                    if ttl > 0:
                        self.redis_client.setex(
                            f"session:{session_state.session_id}",
                            ttl,
                            session_json
                        )
                except Exception as e:
                    logger.warning(f"Failed to store session in Redis: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to store session {session_state.session_id}: {e}")
            raise
    
    def _get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve session from cache or database."""
        try:
            # Check memory cache first
            with self.lock:
                if session_id in self.active_sessions:
                    return self.active_sessions[session_id]
            
            # Check Redis cache
            if self.redis_client:
                try:
                    session_data = self.redis_client.get(f"session:{session_id}")
                    if session_data:
                        session_dict = json.loads(session_data)
                        return self._dict_to_session_state(session_dict)
                except Exception as e:
                    logger.warning(f"Failed to retrieve session from Redis: {e}")
            
            # Check database
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("""
                    SELECT * FROM user_sessions WHERE session_id = ?
                """, (session_id,)).fetchone()
                
                if row:
                    session_state = self._row_to_session_state(row)
                    if session_state and session_state.is_active:
                        # Update cache
                        with self.lock:
                            self.active_sessions[session_id] = session_state
                        return session_state
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve session {session_id}: {e}")
            return None
    
    def _row_to_session_state(self, row) -> Optional[SessionState]:
        """Convert database row to SessionState object."""
        try:
            (session_id, user_id, created_at, last_activity, expires_at,
             device_fingerprint_json, is_active, ip_address, user_agent,
             session_data_json, security_level, concurrent_session_count,
             last_security_check, anomaly_score) = row
            
            # Parse device fingerprint
            device_fingerprint_dict = json.loads(device_fingerprint_json)
            device_fingerprint = DeviceFingerprint(**device_fingerprint_dict)
            
            # Decrypt session data if encrypted
            if self.fernet and session_data_json:
                try:
                    decrypted_data = self.fernet.decrypt(session_data_json.encode()).decode()
                    session_data = json.loads(decrypted_data)
                except:
                    # Fallback for non-encrypted data
                    session_data = json.loads(session_data_json) if session_data_json else {}
            else:
                session_data = json.loads(session_data_json) if session_data_json else {}
            
            return SessionState(
                session_id=session_id,
                user_id=user_id,
                created_at=created_at,
                last_activity=last_activity,
                expires_at=expires_at,
                device_fingerprint=device_fingerprint,
                is_active=bool(is_active),
                ip_address=ip_address,
                user_agent=user_agent,
                session_data=session_data,
                security_level=security_level,
                concurrent_session_count=concurrent_session_count,
                last_security_check=last_security_check,
                anomaly_score=anomaly_score
            )
            
        except Exception as e:
            logger.error(f"Failed to convert row to session state: {e}")
            return None
    
    def _dict_to_session_state(self, session_dict: Dict[str, Any]) -> Optional[SessionState]:
        """Convert dictionary to SessionState object."""
        try:
            device_fingerprint_dict = session_dict['device_fingerprint']
            device_fingerprint = DeviceFingerprint(**device_fingerprint_dict)
            
            session_dict['device_fingerprint'] = device_fingerprint
            return SessionState(**session_dict)
            
        except Exception as e:
            logger.error(f"Failed to convert dict to session state: {e}")
            return None
    
    def _get_device_trust_score(self, user_id: str, fingerprint_hash: str) -> float:
        """Get trust score for device fingerprint."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    SELECT trust_score FROM device_fingerprints 
                    WHERE user_id = ? AND fingerprint_hash = ?
                """, (user_id, fingerprint_hash)).fetchone()
                
                return result[0] if result else 50.0  # Default neutral trust
                
        except Exception as e:
            logger.error(f"Failed to get device trust score: {e}")
            return 50.0
    
    def _update_device_fingerprint(
        self,
        user_id: str,
        device_fingerprint: DeviceFingerprint,
        trust_score: float
    ):
        """Update device fingerprint record."""
        try:
            current_time = time.time()
            device_info = json.dumps(asdict(device_fingerprint))
            
            with sqlite3.connect(self.db_path) as conn:
                # Check if fingerprint exists
                existing = conn.execute("""
                    SELECT fingerprint_hash FROM device_fingerprints 
                    WHERE user_id = ? AND fingerprint_hash = ?
                """, (user_id, device_fingerprint.fingerprint_hash)).fetchone()
                
                if existing:
                    # Update existing
                    conn.execute("""
                        UPDATE device_fingerprints 
                        SET last_seen = ?, trust_score = ?, device_info = ?
                        WHERE user_id = ? AND fingerprint_hash = ?
                    """, (current_time, trust_score, device_info, user_id, device_fingerprint.fingerprint_hash))
                else:
                    # Create new (use INSERT OR REPLACE to handle race conditions)
                    conn.execute("""
                        INSERT OR REPLACE INTO device_fingerprints
                        (fingerprint_hash, user_id, first_seen, last_seen, trust_score, device_info, active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (device_fingerprint.fingerprint_hash, user_id, current_time, current_time, 
                          trust_score, device_info, True))
                    
        except Exception as e:
            logger.error(f"Failed to update device fingerprint: {e}")
    
    def _log_session_event(
        self,
        session_id: str,
        event_type: str,
        details: Dict[str, Any],
        risk_score: float,
        action_taken: str
    ):
        """Log session security event."""
        try:
            event_id = f"sev_{int(time.time() * 1000000)}_{secrets.token_hex(8)}"
            current_time = time.time()
            
            event = SessionSecurityEvent(
                event_id=event_id,
                session_id=session_id,
                event_type=event_type,
                timestamp=current_time,
                details=details,
                risk_score=risk_score,
                action_taken=action_taken
            )
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO session_events
                    (event_id, session_id, event_type, timestamp, details, risk_score, action_taken)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (event_id, session_id, event_type, current_time, 
                      json.dumps(details), risk_score, action_taken))
            
            # Keep in memory (limited size)
            with self.lock:
                self.session_events.append(event)
                if len(self.session_events) > 1000:
                    self.session_events.pop(0)
                    
        except Exception as e:
            logger.error(f"Failed to log session event: {e}")
    
    def _get_recent_session_events(
        self,
        session_id: str,
        hours_back: int = 24,
        event_types: List[str] = None
    ) -> List[SessionSecurityEvent]:
        """Get recent session events."""
        try:
            query = """
                SELECT * FROM session_events 
                WHERE session_id = ? AND timestamp > ?
            """
            params = [session_id, time.time() - (hours_back * 3600)]
            
            if event_types:
                placeholders = ','.join(['?' for _ in event_types])
                query += f" AND event_type IN ({placeholders})"
                params.extend(event_types)
            
            query += " ORDER BY timestamp DESC"
            
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(query, params).fetchall()
                
                events = []
                for row in rows:
                    event_id, session_id, event_type, timestamp, details_json, risk_score, action_taken = row
                    
                    event = SessionSecurityEvent(
                        event_id=event_id,
                        session_id=session_id,
                        event_type=event_type,
                        timestamp=timestamp,
                        details=json.loads(details_json) if details_json else {},
                        risk_score=risk_score,
                        action_taken=action_taken
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to get recent session events: {e}")
            return []
    
    def _start_session_cleanup_thread(self):
        """Start background thread for session cleanup."""
        def cleanup_expired_sessions():
            while True:
                try:
                    current_time = time.time()
                    
                    # Clean up expired sessions from database
                    with sqlite3.connect(self.db_path) as conn:
                        expired_sessions = conn.execute("""
                            SELECT session_id FROM user_sessions 
                            WHERE expires_at <= ? AND is_active = 1
                        """, (current_time,)).fetchall()
                        
                        for (session_id,) in expired_sessions:
                            self._invalidate_session(session_id, "expired")
                    
                    # Clean up memory cache
                    with self.lock:
                        expired_session_ids = [
                            sid for sid, session in self.active_sessions.items()
                            if session.expires_at <= current_time
                        ]
                        
                        for session_id in expired_session_ids:
                            del self.active_sessions[session_id]
                    
                    # Sleep for 5 minutes
                    time.sleep(300)
                    
                except Exception as e:
                    logger.error(f"Session cleanup error: {e}")
                    time.sleep(60)  # Wait 1 minute on error
        
        cleanup_thread = threading.Thread(target=cleanup_expired_sessions, daemon=True)
        cleanup_thread.start()
        logger.info("Session cleanup thread started")
    
    def _start_anomaly_detection_thread(self):
        """Start background thread for anomaly detection."""
        def detect_anomalies():
            while True:
                try:
                    if not self.config['anomaly_detection_enabled']:
                        time.sleep(300)  # Check every 5 minutes
                        continue
                    
                    current_time = time.time()
                    
                    # Check active sessions for anomalies
                    with self.lock:
                        for session_state in self.active_sessions.values():
                            if not session_state.is_active:
                                continue
                            
                            # Calculate current anomaly score
                            anomaly_score = self._calculate_anomaly_score(session_state)
                            
                            if anomaly_score > self.config['max_anomaly_score']:
                                logger.warning(f"High anomaly score detected: {session_state.session_id} = {anomaly_score}")
                                
                                self._log_session_event(
                                    session_id=session_state.session_id,
                                    event_type="anomaly_detected",
                                    details={"anomaly_score": anomaly_score},
                                    risk_score=anomaly_score,
                                    action_taken="alert"
                                )
                                
                                # Could trigger additional security measures here
                    
                    time.sleep(300)  # Check every 5 minutes
                    
                except Exception as e:
                    logger.error(f"Anomaly detection error: {e}")
                    time.sleep(60)
        
        anomaly_thread = threading.Thread(target=detect_anomalies, daemon=True)
        anomaly_thread.start()
        logger.info("Anomaly detection thread started")
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get session management statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Basic session stats
                total_sessions = conn.execute("SELECT COUNT(*) FROM user_sessions").fetchone()[0]
                active_sessions = conn.execute("""
                    SELECT COUNT(*) FROM user_sessions WHERE is_active = 1 AND expires_at > ?
                """, (time.time(),)).fetchone()[0]
                
                # Recent activity (last 24 hours)
                recent_sessions = conn.execute("""
                    SELECT COUNT(*) FROM user_sessions WHERE created_at > ?
                """, (time.time() - 86400,)).fetchone()[0]
                
                # Security events (last 24 hours)
                security_events = conn.execute("""
                    SELECT COUNT(*) FROM session_events WHERE timestamp > ?
                """, (time.time() - 86400,)).fetchone()[0]
                
                high_risk_events = conn.execute("""
                    SELECT COUNT(*) FROM session_events 
                    WHERE timestamp > ? AND risk_score > 70
                """, (time.time() - 86400,)).fetchone()[0]
                
                # Device fingerprints
                trusted_devices = conn.execute("""
                    SELECT COUNT(*) FROM device_fingerprints WHERE active = 1 AND trust_score > 70
                """).fetchone()[0]
                
                # Average session duration
                avg_duration = conn.execute("""
                    SELECT AVG(last_activity - created_at) FROM user_sessions 
                    WHERE is_active = 0 AND last_activity > created_at
                """).fetchone()[0] or 0
                
                return {
                    'session_security_enabled': True,
                    'total_sessions': total_sessions,
                    'active_sessions': active_sessions,
                    'recent_sessions_24h': recent_sessions,
                    'security_events_24h': security_events,
                    'high_risk_events_24h': high_risk_events,
                    'trusted_devices': trusted_devices,
                    'average_session_duration': avg_duration,
                    'configuration': {
                        'session_timeout': self.config['session_timeout'],
                        'max_concurrent_sessions': self.config['max_concurrent_sessions'],
                        'device_fingerprint_required': self.config['device_fingerprint_required'],
                        'anomaly_detection_enabled': self.config['anomaly_detection_enabled']
                    },
                    'security_features': {
                        'device_fingerprinting': True,
                        'concurrent_session_limits': True,
                        'session_encryption': self.config['session_encryption_enabled'],
                        'anomaly_detection': self.config['anomaly_detection_enabled'],
                        'redis_support': self.redis_client is not None
                    },
                    'timestamp': time.time()
                }
                
        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            return {
                'session_security_enabled': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_user_session_info(self, user_id: str) -> Dict[str, Any]:
        """Get session information for a specific user."""
        try:
            user_sessions = self._get_user_sessions(user_id, active_only=True)
            
            session_info = []
            for session in user_sessions:
                session_info.append({
                    'session_id': session.session_id,
                    'created_at': session.created_at,
                    'last_activity': session.last_activity,
                    'expires_at': session.expires_at,
                    'ip_address': session.ip_address,
                    'security_level': session.security_level,
                    'anomaly_score': session.anomaly_score,
                    'device_info': {
                        'fingerprint_hash': session.device_fingerprint.fingerprint_hash[:16],
                        'ip_country': session.device_fingerprint.ip_country,
                        'platform': session.device_fingerprint.platform
                    }
                })
            
            return {
                'user_id': user_id,
                'active_session_count': len(session_info),
                'max_concurrent_sessions': self.config['max_concurrent_sessions'],
                'sessions': session_info,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user session info for {user_id}: {e}")
            return {'error': str(e)}
    
    def shutdown(self):
        """Clean shutdown of session security manager."""
        logger.info("Session Security Manager shutting down...")
        
        # Close Redis connection
        if self.redis_client:
            try:
                self.redis_client.close()
            except Exception:
                pass


# Global session security manager instance
session_security_manager = None


def get_session_manager() -> SecureSessionManager:
    """Get or create global session manager instance."""
    global session_security_manager
    if session_security_manager is None:
        session_security_manager = SecureSessionManager()
    return session_security_manager


def create_secure_session(
    user_id: str,
    ip_address: str,
    user_agent: str,
    security_level: str = "basic",
    additional_data: Dict[str, Any] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Convenience function for secure session creation."""
    return get_session_manager().create_session(
        user_id, ip_address, user_agent, security_level, additional_data
    )


def validate_secure_session(
    session_id: str,
    ip_address: str,
    user_agent: str
) -> Tuple[bool, Optional[SessionState], Optional[str]]:
    """Convenience function for session validation."""
    return get_session_manager().validate_session(session_id, ip_address, user_agent)


def get_session_security_stats() -> Dict[str, Any]:
    """Convenience function for session statistics."""
    return get_session_manager().get_session_statistics()