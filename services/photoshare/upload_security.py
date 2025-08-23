#!/usr/bin/env python3
"""
Enhanced Upload Security Validation System
==========================================

Comprehensive security validation for file uploads with advanced threat detection.
"""

import os
import hashlib
import magic
import mimetypes
import re
import subprocess
import tempfile
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from threading import Lock

# Security imports
try:
    import yara
    YARA_AVAILABLE = True
except ImportError:
    YARA_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SecurityThreat:
    """Represents a detected security threat in uploaded file."""
    threat_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    details: Dict[str, Any]
    confidence: float  # 0.0 to 1.0


@dataclass 
class ValidationResult:
    """Result of upload security validation."""
    is_safe: bool
    threats: List[SecurityThreat]
    sanitized: bool
    metadata: Dict[str, Any]
    processing_time: float


class UploadSecurityValidator:
    """Advanced security validator for file uploads."""
    
    def __init__(self, secure_dir: str = None):
        self.secure_dir = secure_dir or self._get_secure_directory()
        self.db_path = os.path.join(self.secure_dir, "upload_security.db")
        self.lock = Lock()
        
        # Create secure directory
        os.makedirs(self.secure_dir, mode=0o700, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Load security rules
        self._load_security_rules()
        
        logger.info(f"Upload Security Validator initialized: {self.secure_dir}")
    
    def _get_secure_directory(self) -> str:
        """Get secure directory for storage."""
        return "./vault-like-secure-storage/upload_security" if not os.path.exists("/app") else "/app/vault-like-secure-storage/upload_security"
    
    def _init_database(self):
        """Initialize SQLite database for validation tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS upload_validations (
                        validation_id TEXT PRIMARY KEY,
                        timestamp REAL NOT NULL,
                        filename TEXT NOT NULL,
                        file_hash TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        mime_type TEXT,
                        validation_result TEXT NOT NULL,
                        threats_detected INTEGER DEFAULT 0,
                        processing_time REAL,
                        user_id TEXT,
                        source_ip TEXT,
                        metadata TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS threat_signatures (
                        signature_id TEXT PRIMARY KEY,
                        threat_type TEXT NOT NULL,
                        signature_data TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        last_seen REAL,
                        active BOOLEAN DEFAULT 1
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_validations_timestamp
                    ON upload_validations(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_validations_hash  
                    ON upload_validations(file_hash)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_threats_type
                    ON threat_signatures(threat_type)
                """)
                
                # Initialize default threat signatures
                self._init_default_signatures(conn)
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _init_default_signatures(self, conn):
        """Initialize default threat signatures."""
        default_signatures = [
            # Executable file signatures
            ("exe_header", "malware", "4d5a", "HIGH"),  # PE header
            ("elf_header", "malware", "7f454c46", "HIGH"),  # ELF header
            ("script_embed", "code_injection", r"<script[^>]*>.*</script>", "MEDIUM"),
            
            # Archive bombs
            ("zip_bomb", "resource_exhaustion", "compression_ratio_high", "HIGH"),
            
            # Suspicious metadata
            ("suspicious_exif", "privacy_leak", "gps_coordinates", "MEDIUM"),
            ("macro_enabled", "malware", "macro_detected", "HIGH"),
            
            # File type confusion
            ("double_extension", "social_engineering", r"\.(jpg|png|gif)\.exe$", "HIGH"),
            
            # Path traversal attempts  
            ("directory_traversal", "path_traversal", r"\.\.[/\\]", "HIGH"),
            ("absolute_path", "path_traversal", r"^[/\\]", "MEDIUM"),
        ]
        
        for sig_id, threat_type, signature, severity in default_signatures:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO threat_signatures 
                    (signature_id, threat_type, signature_data, severity, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (sig_id, threat_type, signature, severity, time.time()))
            except Exception as e:
                logger.warning(f"Failed to insert signature {sig_id}: {e}")
    
    def _load_security_rules(self):
        """Load and compile security rules."""
        self.yara_rules = None
        
        if YARA_AVAILABLE:
            try:
                # Create YARA rules for common threats
                yara_source = """
                rule SuspiciousExecutable {
                    strings:
                        $pe = { 4D 5A }
                        $elf = { 7F 45 4C 46 }
                    condition:
                        $pe at 0 or $elf at 0
                }
                
                rule EmbeddedScript {
                    strings:
                        $script1 = /<script.*?>.*?<\/script>/
                        $script2 = /javascript:/
                        $script3 = /vbscript:/
                    condition:
                        any of them
                }
                
                rule MacroDocument {
                    strings:
                        $macro1 = "macros"
                        $macro2 = "VBA"
                        $macro3 = "_VBA_PROJECT"
                    condition:
                        any of them
                }
                """
                
                self.yara_rules = yara.compile(source=yara_source)
                logger.info("YARA security rules loaded")
                
            except Exception as e:
                logger.warning(f"Failed to compile YARA rules: {e}")
    
    def validate_upload(
        self,
        filename: str,
        file_content: bytes,
        user_id: str = None,
        source_ip: str = None
    ) -> ValidationResult:
        """Comprehensive security validation of uploaded file."""
        
        start_time = time.time()
        validation_id = self._generate_validation_id()
        file_hash = hashlib.sha256(file_content).hexdigest()
        threats = []
        metadata = {}
        
        try:
            # Basic file validation
            threats.extend(self._validate_filename(filename))
            threats.extend(self._validate_file_content(file_content))
            threats.extend(self._validate_mime_type(filename, file_content))
            
            # Advanced threat detection
            if YARA_AVAILABLE and self.yara_rules:
                threats.extend(self._yara_scan(file_content))
            
            # Signature-based detection  
            threats.extend(self._signature_scan(filename, file_content))
            
            # Image-specific validation
            if self._is_image_file(filename):
                img_threats, img_metadata = self._validate_image(file_content)
                threats.extend(img_threats)
                metadata.update(img_metadata)
            
            # Archive validation
            if self._is_archive_file(filename):
                threats.extend(self._validate_archive(file_content))
            
            # Document validation
            if self._is_document_file(filename):
                threats.extend(self._validate_document(file_content))
            
            # Determine overall safety
            critical_threats = [t for t in threats if t.severity == 'CRITICAL']
            high_threats = [t for t in threats if t.severity == 'HIGH']
            
            is_safe = len(critical_threats) == 0 and len(high_threats) == 0
            
            # Additional metadata
            metadata.update({
                'file_size': len(file_content),
                'file_hash': file_hash,
                'mime_type': self._detect_mime_type(file_content),
                'validation_id': validation_id,
                'threats_count': len(threats),
                'security_score': self._calculate_security_score(threats)
            })
            
            processing_time = time.time() - start_time
            
            # Log validation result
            self._log_validation(
                validation_id, filename, file_hash, len(file_content),
                metadata.get('mime_type'), is_safe, threats, 
                processing_time, user_id, source_ip, metadata
            )
            
            return ValidationResult(
                is_safe=is_safe,
                threats=threats,
                sanitized=False,  # No automatic sanitization yet
                metadata=metadata,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Upload validation failed: {e}")
            processing_time = time.time() - start_time
            
            # Create critical threat for validation failure
            validation_threat = SecurityThreat(
                threat_type="validation_failure",
                severity="CRITICAL", 
                description="Upload validation system failure",
                details={"error": str(e), "validation_id": validation_id},
                confidence=1.0
            )
            
            return ValidationResult(
                is_safe=False,
                threats=[validation_threat],
                sanitized=False,
                metadata={"error": str(e), "validation_id": validation_id},
                processing_time=processing_time
            )
    
    def _generate_validation_id(self) -> str:
        """Generate unique validation ID."""
        timestamp = int(time.time() * 1000000)  # microseconds
        random_component = os.urandom(8).hex()
        return f"upload_{timestamp}_{random_component}"
    
    def _validate_filename(self, filename: str) -> List[SecurityThreat]:
        """Validate filename for security threats."""
        threats = []
        
        # Null byte injection
        if '\x00' in filename:
            threats.append(SecurityThreat(
                threat_type="null_byte_injection",
                severity="CRITICAL",
                description="Null byte detected in filename",
                details={"filename": filename},
                confidence=1.0
            ))
        
        # Directory traversal
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            threats.append(SecurityThreat(
                threat_type="path_traversal",
                severity="HIGH",
                description="Directory traversal attempt detected",
                details={"filename": filename},
                confidence=0.9
            ))
        
        # Double extensions (social engineering)
        if re.search(r'\.(jpg|png|gif|pdf)\.exe$', filename.lower()):
            threats.append(SecurityThreat(
                threat_type="double_extension",
                severity="HIGH", 
                description="Double extension detected (possible social engineering)",
                details={"filename": filename},
                confidence=0.8
            ))
        
        # Suspicious characters
        suspicious_chars = ['<', '>', '|', ':', '*', '?', '"']
        if any(char in filename for char in suspicious_chars):
            threats.append(SecurityThreat(
                threat_type="suspicious_filename",
                severity="MEDIUM",
                description="Suspicious characters in filename",
                details={"filename": filename, "suspicious_chars": suspicious_chars},
                confidence=0.6
            ))
        
        # Excessively long filename
        if len(filename) > 255:
            threats.append(SecurityThreat(
                threat_type="filename_overflow",
                severity="MEDIUM",
                description="Excessively long filename",
                details={"filename": filename, "length": len(filename)},
                confidence=0.7
            ))
        
        return threats
    
    def _validate_file_content(self, file_content: bytes) -> List[SecurityThreat]:
        """Validate file content for security threats."""
        threats = []
        
        # Empty file
        if len(file_content) == 0:
            threats.append(SecurityThreat(
                threat_type="empty_file",
                severity="MEDIUM",
                description="Empty file detected",
                details={"size": 0},
                confidence=1.0
            ))
            return threats
        
        # Excessively large file (bomb attempt)
        max_size = 100 * 1024 * 1024  # 100MB
        if len(file_content) > max_size:
            threats.append(SecurityThreat(
                threat_type="oversized_file",
                severity="HIGH",
                description=f"File exceeds maximum size ({max_size} bytes)",
                details={"actual_size": len(file_content), "max_size": max_size},
                confidence=1.0
            ))
        
        # Executable headers
        if file_content[:2] == b'MZ':  # PE header
            threats.append(SecurityThreat(
                threat_type="executable_content",
                severity="HIGH",
                description="PE executable header detected",
                details={"header": "PE"},
                confidence=1.0
            ))
        
        if file_content[:4] == b'\x7fELF':  # ELF header
            threats.append(SecurityThreat(
                threat_type="executable_content", 
                severity="HIGH",
                description="ELF executable header detected",
                details={"header": "ELF"},
                confidence=1.0
            ))
        
        # Script content detection
        script_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'<?php',
            b'<%',
            b'#!/bin/',
            b'#!/usr/bin/'
        ]
        
        for pattern in script_patterns:
            if pattern in file_content.lower():
                threats.append(SecurityThreat(
                    threat_type="embedded_script",
                    severity="MEDIUM",
                    description=f"Embedded script detected: {pattern.decode('utf-8', errors='ignore')}",
                    details={"pattern": pattern.decode('utf-8', errors='ignore')},
                    confidence=0.8
                ))
        
        return threats
    
    def _validate_mime_type(self, filename: str, file_content: bytes) -> List[SecurityThreat]:
        """Validate MIME type consistency."""
        threats = []
        
        try:
            # Detect MIME type from content
            if magic:
                detected_mime = magic.from_buffer(file_content, mime=True)
            else:
                detected_mime = self._detect_mime_type(file_content)
            
            # Get expected MIME type from filename
            expected_mime, _ = mimetypes.guess_type(filename)
            
            # Check for MIME type mismatch
            if expected_mime and detected_mime:
                if not self._mime_types_compatible(expected_mime, detected_mime):
                    threats.append(SecurityThreat(
                        threat_type="mime_type_mismatch",
                        severity="MEDIUM", 
                        description="File content doesn't match filename extension",
                        details={
                            "filename": filename,
                            "expected_mime": expected_mime,
                            "detected_mime": detected_mime
                        },
                        confidence=0.7
                    ))
            
        except Exception as e:
            logger.warning(f"MIME type validation failed: {e}")
        
        return threats
    
    def _mime_types_compatible(self, expected: str, detected: str) -> bool:
        """Check if MIME types are compatible."""
        # Handle common variations
        compatible_types = {
            'image/jpeg': ['image/jpeg', 'image/pjpeg'],
            'image/png': ['image/png', 'image/x-png'],
            'image/gif': ['image/gif'],
            'application/pdf': ['application/pdf', 'application/x-pdf'],
            'text/plain': ['text/plain', 'text/x-python', 'text/x-script'],
        }
        
        return detected in compatible_types.get(expected, [expected])
    
    def _detect_mime_type(self, file_content: bytes) -> str:
        """Detect MIME type from file content."""
        # Basic detection based on file headers
        headers = {
            b'\xff\xd8\xff': 'image/jpeg',
            b'\x89PNG\r\n\x1a\n': 'image/png', 
            b'GIF87a': 'image/gif',
            b'GIF89a': 'image/gif',
            b'%PDF': 'application/pdf',
            b'PK\x03\x04': 'application/zip',
            b'Rar!\x1a\x07': 'application/x-rar-compressed',
        }
        
        for header, mime_type in headers.items():
            if file_content.startswith(header):
                return mime_type
        
        return 'application/octet-stream'
    
    def _yara_scan(self, file_content: bytes) -> List[SecurityThreat]:
        """Scan file content with YARA rules."""
        threats = []
        
        try:
            matches = self.yara_rules.match(data=file_content)
            
            for match in matches:
                severity = "HIGH" if "Executable" in match.rule else "MEDIUM"
                
                threats.append(SecurityThreat(
                    threat_type="yara_detection",
                    severity=severity,
                    description=f"YARA rule triggered: {match.rule}",
                    details={
                        "rule": match.rule,
                        "matches": [str(m) for m in match.strings]
                    },
                    confidence=0.9
                ))
                
        except Exception as e:
            logger.warning(f"YARA scan failed: {e}")
        
        return threats
    
    def _signature_scan(self, filename: str, file_content: bytes) -> List[SecurityThreat]:
        """Scan against threat signature database."""
        threats = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                signatures = conn.execute("""
                    SELECT signature_id, threat_type, signature_data, severity
                    FROM threat_signatures WHERE active = 1
                """).fetchall()
                
                for sig_id, threat_type, sig_data, severity in signatures:
                    if self._matches_signature(filename, file_content, sig_data):
                        threats.append(SecurityThreat(
                            threat_type=threat_type,
                            severity=severity,
                            description=f"Threat signature match: {sig_id}",
                            details={"signature_id": sig_id, "signature": sig_data},
                            confidence=0.8
                        ))
                        
                        # Update last seen timestamp
                        conn.execute("""
                            UPDATE threat_signatures 
                            SET last_seen = ? WHERE signature_id = ?
                        """, (time.time(), sig_id))
                        
        except Exception as e:
            logger.warning(f"Signature scan failed: {e}")
        
        return threats
    
    def _matches_signature(self, filename: str, file_content: bytes, signature: str) -> bool:
        """Check if file matches threat signature."""
        try:
            # Hex signature matching
            if signature.startswith('0x') or all(c in '0123456789abcdefABCDEF' for c in signature):
                sig_bytes = bytes.fromhex(signature.replace('0x', ''))
                return sig_bytes in file_content
            
            # Regex pattern matching
            if signature.startswith('r"') or '\\' in signature:
                pattern = re.compile(signature.strip('r"'), re.IGNORECASE)
                return bool(pattern.search(filename)) or bool(pattern.search(file_content.decode('utf-8', errors='ignore')))
            
            # String matching 
            return signature in filename or signature.encode() in file_content
            
        except Exception:
            return False
    
    def _is_image_file(self, filename: str) -> bool:
        """Check if file is an image."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        return Path(filename).suffix.lower() in image_extensions
    
    def _is_archive_file(self, filename: str) -> bool:
        """Check if file is an archive."""
        archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
        return Path(filename).suffix.lower() in archive_extensions
    
    def _is_document_file(self, filename: str) -> bool:
        """Check if file is a document."""
        doc_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp'}
        return Path(filename).suffix.lower() in doc_extensions
    
    def _validate_image(self, file_content: bytes) -> Tuple[List[SecurityThreat], Dict[str, Any]]:
        """Validate image files for security threats."""
        threats = []
        metadata = {}
        
        if not PIL_AVAILABLE:
            return threats, metadata
        
        try:
            with tempfile.NamedTemporaryFile() as tmp_file:
                tmp_file.write(file_content)
                tmp_file.flush()
                
                with Image.open(tmp_file.name) as img:
                    metadata['image_format'] = img.format
                    metadata['image_size'] = img.size
                    metadata['image_mode'] = img.mode
                    
                    # Check for suspicious dimensions (potential zip bomb)
                    width, height = img.size
                    if width * height > 50000 * 50000:  # > 50k x 50k pixels
                        threats.append(SecurityThreat(
                            threat_type="image_bomb",
                            severity="HIGH",
                            description="Image dimensions potentially dangerous",
                            details={"width": width, "height": height},
                            confidence=0.8
                        ))
                    
                    # Check EXIF data for privacy risks
                    if hasattr(img, '_getexif') and img._getexif():
                        exif_data = img._getexif()
                        if exif_data:
                            # Check for GPS coordinates
                            gps_tags = [34853]  # GPS IFD
                            if any(tag in exif_data for tag in gps_tags):
                                threats.append(SecurityThreat(
                                    threat_type="privacy_leak",
                                    severity="MEDIUM", 
                                    description="GPS coordinates found in EXIF data",
                                    details={"exif_gps": True},
                                    confidence=0.9
                                ))
                    
        except Exception as e:
            logger.warning(f"Image validation failed: {e}")
            threats.append(SecurityThreat(
                threat_type="image_processing_error",
                severity="MEDIUM",
                description="Failed to process image file",
                details={"error": str(e)},
                confidence=0.5
            ))
        
        return threats, metadata
    
    def _validate_archive(self, file_content: bytes) -> List[SecurityThreat]:
        """Validate archive files for security threats."""
        threats = []
        
        # Check for zip bombs (high compression ratio)
        if file_content[:4] == b'PK\x03\x04':  # ZIP file
            try:
                # Basic zip bomb detection - if file is very small but claims large content
                if len(file_content) < 1000:  # Very small zip file
                    threats.append(SecurityThreat(
                        threat_type="potential_zip_bomb",
                        severity="MEDIUM",
                        description="Suspiciously small zip file (potential zip bomb)",
                        details={"compressed_size": len(file_content)},
                        confidence=0.6
                    ))
                        
            except Exception as e:
                logger.warning(f"Archive validation failed: {e}")
        
        return threats
    
    def _validate_document(self, file_content: bytes) -> List[SecurityThreat]:
        """Validate document files for security threats."""
        threats = []
        
        # PDF validation
        if file_content.startswith(b'%PDF'):
            # Check for JavaScript in PDF
            if b'/JavaScript' in file_content or b'/JS' in file_content:
                threats.append(SecurityThreat(
                    threat_type="pdf_javascript",
                    severity="HIGH",
                    description="JavaScript detected in PDF file",
                    details={"pdf_javascript": True},
                    confidence=0.8
                ))
        
        # Office document validation (ZIP-based formats)
        if file_content[:4] == b'PK\x03\x04':
            # Check for macros in Office documents
            macro_indicators = [b'vbaProject.bin', b'macros/', b'_VBA_PROJECT']
            if any(indicator in file_content for indicator in macro_indicators):
                threats.append(SecurityThreat(
                    threat_type="office_macro",
                    severity="HIGH", 
                    description="Macros detected in Office document",
                    details={"office_macros": True},
                    confidence=0.9
                ))
        
        return threats
    
    def _calculate_security_score(self, threats: List[SecurityThreat]) -> float:
        """Calculate security score based on detected threats."""
        if not threats:
            return 100.0
        
        severity_weights = {
            'LOW': 5,
            'MEDIUM': 15,
            'HIGH': 40,
            'CRITICAL': 100
        }
        
        total_deduction = sum(
            severity_weights.get(threat.severity, 0) * threat.confidence
            for threat in threats
        )
        
        return max(0.0, 100.0 - total_deduction)
    
    def _log_validation(
        self, validation_id: str, filename: str, file_hash: str,
        file_size: int, mime_type: str, is_safe: bool,
        threats: List[SecurityThreat], processing_time: float,
        user_id: str, source_ip: str, metadata: Dict[str, Any]
    ):
        """Log validation result to database."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO upload_validations
                        (validation_id, timestamp, filename, file_hash, file_size,
                         mime_type, validation_result, threats_detected, processing_time,
                         user_id, source_ip, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        validation_id, time.time(), filename, file_hash, file_size,
                        mime_type, "SAFE" if is_safe else "THREAT", len(threats),
                        processing_time, user_id, source_ip, str(metadata)
                    ))
                    
        except Exception as e:
            logger.error(f"Failed to log validation: {e}")
    
    def add_threat_signature(
        self, signature_id: str, threat_type: str,
        signature_data: str, severity: str
    ) -> bool:
        """Add new threat signature."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO threat_signatures
                        (signature_id, threat_type, signature_data, severity, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (signature_id, threat_type, signature_data, severity, time.time()))
                    
                    logger.info(f"Added threat signature: {signature_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to add threat signature: {e}")
            return False
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get upload validation statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Basic statistics
                total_validations = conn.execute("""
                    SELECT COUNT(*) FROM upload_validations
                """).fetchone()[0]
                
                safe_uploads = conn.execute("""
                    SELECT COUNT(*) FROM upload_validations WHERE validation_result = 'SAFE'
                """).fetchone()[0]
                
                threat_uploads = conn.execute("""
                    SELECT COUNT(*) FROM upload_validations WHERE validation_result = 'THREAT'
                """).fetchone()[0]
                
                # Recent activity (last 24 hours)
                recent_validations = conn.execute("""
                    SELECT COUNT(*) FROM upload_validations 
                    WHERE timestamp > ?
                """, (time.time() - 86400,)).fetchone()[0]
                
                # Average processing time
                avg_processing_time = conn.execute("""
                    SELECT AVG(processing_time) FROM upload_validations
                    WHERE processing_time IS NOT NULL
                """).fetchone()[0] or 0
                
                # Threat type distribution
                threat_types = conn.execute("""
                    SELECT threat_type, COUNT(*) as count
                    FROM threat_signatures
                    WHERE active = 1
                    GROUP BY threat_type
                    ORDER BY count DESC
                """).fetchall()
                
                return {
                    'upload_security_enabled': True,
                    'total_validations': total_validations,
                    'safe_uploads': safe_uploads,
                    'threat_uploads': threat_uploads,
                    'safety_rate': (safe_uploads / max(total_validations, 1)) * 100,
                    'recent_validations_24h': recent_validations,
                    'average_processing_time': avg_processing_time,
                    'active_signatures': len(threat_types),
                    'threat_type_distribution': dict(threat_types),
                    'security_features': {
                        'yara_scanning': YARA_AVAILABLE,
                        'magic_mime_detection': magic is not None,
                        'image_analysis': PIL_AVAILABLE,
                        'signature_based_detection': True,
                        'content_validation': True,
                        'filename_validation': True
                    },
                    'timestamp': time.time()
                }
                
        except Exception as e:
            logger.error(f"Failed to get validation statistics: {e}")
            return {
                'upload_security_enabled': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_recent_validations(
        self, limit: int = 100, hours_back: int = 24,
        threat_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get recent upload validations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT validation_id, timestamp, filename, file_hash,
                           file_size, validation_result, threats_detected,
                           processing_time, user_id, source_ip
                    FROM upload_validations
                    WHERE timestamp > ?
                """
                
                params = [time.time() - (hours_back * 3600)]
                
                if threat_only:
                    query += " AND validation_result = 'THREAT'"
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                validations = conn.execute(query, params).fetchall()
                
                return [
                    {
                        'validation_id': row[0],
                        'timestamp': row[1], 
                        'filename': row[2],
                        'file_hash': row[3],
                        'file_size': row[4],
                        'validation_result': row[5],
                        'threats_detected': row[6],
                        'processing_time': row[7],
                        'user_id': row[8],
                        'source_ip': row[9]
                    } for row in validations
                ]
                
        except Exception as e:
            logger.error(f"Failed to get recent validations: {e}")
            return []
    
    def shutdown(self):
        """Clean shutdown of upload security validator."""
        logger.info("Upload Security Validator shutting down...")
        # Any cleanup tasks would go here


# Global upload security validator instance  
upload_security_validator = None


def get_upload_validator() -> UploadSecurityValidator:
    """Get or create global upload validator instance."""
    global upload_security_validator
    if upload_security_validator is None:
        upload_security_validator = UploadSecurityValidator()
    return upload_security_validator


def validate_upload_security(
    filename: str, file_content: bytes,
    user_id: str = None, source_ip: str = None
) -> ValidationResult:
    """Convenience function for upload security validation."""
    return get_upload_validator().validate_upload(filename, file_content, user_id, source_ip)


def get_upload_security_stats() -> Dict[str, Any]:
    """Convenience function for upload security statistics."""
    return get_upload_validator().get_validation_statistics()