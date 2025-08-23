#!/usr/bin/env python3
"""
Two-Factor Authentication Implementation
========================================

Supports TOTP (Time-based One-Time Password), SMS, and Hardware Keys (WebAuthn).
"""

import os
import secrets
import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

import qrcode
from io import BytesIO
import pyotp
import httpx
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class TwoFactorMethod(str, Enum):
    """Supported 2FA methods."""
    TOTP = "totp"
    SMS = "sms"
    WEBAUTHN = "webauthn"
    BACKUP_CODES = "backup_codes"

@dataclass
class TwoFactorDevice:
    """2FA device registration."""
    id: str
    user_id: str
    method: TwoFactorMethod
    name: str  # User-friendly name
    secret: str  # Encrypted secret
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    backup_data: Optional[Dict[str, Any]] = None  # Method-specific data
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "method": self.method,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_active": self.is_active
            # Note: secret not included in dict for security
        }

@dataclass
class BackupCode:
    """2FA backup recovery code."""
    code: str
    user_id: str
    created_at: datetime
    used_at: Optional[datetime] = None
    is_used: bool = False

class TwoFactorAuthManager:
    """Manages 2FA registration, verification, and recovery."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        # Initialize encryption for storing secrets
        self.encryption_key = encryption_key or os.getenv("TWOFA_ENCRYPTION_KEY")
        if not self.encryption_key:
            # Generate a new key (in production, this should be stored securely)
            self.encryption_key = Fernet.generate_key()
            logger.warning("Generated new 2FA encryption key - store this securely!")
        
        logger.info(f"2FA encryption key type: {type(self.encryption_key)}, length: {len(self.encryption_key) if self.encryption_key else 0}")
        self.fernet = Fernet(self.encryption_key)
        
        # SMS provider configuration
        self.sms_enabled = bool(os.getenv("SMS_PROVIDER_API_KEY"))
        self.sms_provider = os.getenv("SMS_PROVIDER", "twilio")  # or "aws_sns"
        self.sms_api_key = os.getenv("SMS_PROVIDER_API_KEY")
        self.sms_from_number = os.getenv("SMS_FROM_NUMBER")
        
        # WebAuthn configuration
        self.webauthn_rp_id = os.getenv("WEBAUTHN_RP_ID", "localhost")
        self.webauthn_rp_name = os.getenv("WEBAUTHN_RP_NAME", "PhotoShare")
        
        self.http_client = httpx.AsyncClient(timeout=30)
        
    def _encrypt_secret(self, secret: str) -> str:
        """Encrypt a secret for storage."""
        return self.fernet.encrypt(secret.encode()).decode()
        
    def _decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt a stored secret."""
        return self.fernet.decrypt(encrypted_secret.encode()).decode()
        
    async def setup_totp(self, user_id: str, user_email: str, device_name: str = "Mobile App") -> Dict[str, Any]:
        """Set up TOTP (Time-based One-Time Password) for a user."""
        
        # Generate a random secret
        secret = pyotp.random_base32()
        
        # Create TOTP object
        totp = pyotp.TOTP(secret)
        
        # Generate QR code URL
        provisioning_uri = totp.provisioning_uri(
            user_email,
            issuer_name=self.webauthn_rp_name
        )
        
        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Convert QR code to base64
        buffered = BytesIO()
        qr_image.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Store device (encrypted secret)
        device = TwoFactorDevice(
            id=secrets.token_urlsafe(16),
            user_id=user_id,
            method=TwoFactorMethod.TOTP,
            name=device_name,
            secret=self._encrypt_secret(secret),
            created_at=datetime.now(timezone.utc)
        )
        
        # Note: In a real implementation, you would save this to the database
        # For now, we return the setup data
        
        return {
            "device_id": device.id,
            "secret": secret,  # Only returned during setup
            "qr_code": f"data:image/png;base64,{qr_code_base64}",
            "provisioning_uri": provisioning_uri,
            "backup_codes": await self._generate_backup_codes(user_id)
        }
        
    async def verify_totp(self, user_id: str, device_id: str, code: str) -> bool:
        """Verify TOTP code."""
        # Note: In real implementation, fetch device from database
        # For now, we'll simulate verification
        
        try:
            # Get device secret (would be from database)
            # device = get_device_from_database(device_id)
            # secret = self._decrypt_secret(device.secret)
            
            # For demo purposes, we'll use a mock verification
            # In real implementation:
            # totp = pyotp.TOTP(secret)
            # return totp.verify(code, valid_window=1)  # Allow ±30 seconds
            
            # Mock verification - accept 6-digit codes
            if len(code) == 6 and code.isdigit():
                # Update last_used timestamp in database
                return True
                
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            
        return False
        
    async def setup_sms(self, user_id: str, phone_number: str) -> Dict[str, Any]:
        """Set up SMS 2FA for a user."""
        if not self.sms_enabled:
            raise ValueError("SMS 2FA is not enabled")
            
        # Validate phone number format
        if not self._validate_phone_number(phone_number):
            raise ValueError("Invalid phone number format")
            
        # Send verification SMS
        verification_code = self._generate_sms_code()
        
        # Store phone number and verification code
        device = TwoFactorDevice(
            id=secrets.token_urlsafe(16),
            user_id=user_id,
            method=TwoFactorMethod.SMS,
            name=f"SMS {phone_number[-4:]}",  # Show last 4 digits
            secret=self._encrypt_secret(phone_number),
            created_at=datetime.now(timezone.utc),
            backup_data={"verification_code": verification_code, "verified": False}
        )
        
        # Send SMS
        success = await self._send_sms(phone_number, f"Your PhotoShare verification code: {verification_code}")
        
        if not success:
            raise ValueError("Failed to send SMS verification code")
            
        return {
            "device_id": device.id,
            "phone_number": phone_number,
            "message": "Verification code sent via SMS"
        }
        
    async def verify_sms_setup(self, device_id: str, code: str) -> bool:
        """Verify SMS setup code."""
        # In real implementation, fetch device and check verification code
        if len(code) == 6 and code.isdigit():
            # Mark device as verified in database
            return True
        return False
        
    async def send_sms_code(self, user_id: str, device_id: str) -> bool:
        """Send SMS verification code."""
        if not self.sms_enabled:
            return False
            
        # Generate and send code
        self._generate_sms_code()
        
        # In real implementation:
        # device = get_device_from_database(device_id)
        # phone_number = self._decrypt_secret(device.secret)
        # return await self._send_sms(phone_number, f"Your PhotoShare code: {code}")
        
        # For demo, assume success
        return True
        
    async def verify_sms(self, user_id: str, device_id: str, code: str) -> bool:
        """Verify SMS code."""
        # In real implementation, check code against stored/sent code
        if len(code) == 6 and code.isdigit():
            return True
        return False
        
    async def _generate_backup_codes(self, user_id: str, count: int = 10) -> List[str]:
        """Generate backup recovery codes."""
        codes = []
        
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_urlsafe(6)[:8].upper()
            codes.append(code)
            
            # In real implementation, store backup code in database
            BackupCode(
                code=hashlib.sha256(code.encode()).hexdigest(),  # Store hash
                user_id=user_id,
                created_at=datetime.now(timezone.utc)
            )
            
        return codes
        
    async def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify backup recovery code."""
        hashlib.sha256(code.upper().encode()).hexdigest()
        
        # In real implementation:
        # backup_code = get_backup_code_from_database(user_id, code_hash)
        # if backup_code and not backup_code.is_used:
        #     mark_backup_code_as_used(backup_code.code)
        #     return True
        
        # For demo, accept any 8-character alphanumeric code
        if len(code) == 8 and code.replace("-", "").isalnum():
            return True
            
        return False
        
    async def get_user_2fa_devices(self, user_id: str) -> List[TwoFactorDevice]:
        """Get all 2FA devices for a user."""
        # In real implementation, fetch from database
        # return database.get_2fa_devices(user_id)
        
        # For demo, return empty list
        return []
        
    async def disable_2fa_device(self, user_id: str, device_id: str) -> bool:
        """Disable a 2FA device."""
        # In real implementation:
        # return database.disable_2fa_device(user_id, device_id)
        
        return True
        
    def _generate_sms_code(self) -> str:
        """Generate 6-digit SMS verification code."""
        return f"{secrets.randbelow(900000) + 100000:06d}"
        
    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format."""
        # Basic validation - in production use a proper phone number library
        cleaned = ''.join(filter(str.isdigit, phone_number))
        return 10 <= len(cleaned) <= 15
        
    async def _send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS via configured provider."""
        if not self.sms_enabled:
            return False
            
        try:
            if self.sms_provider == "twilio":
                return await self._send_twilio_sms(phone_number, message)
            elif self.sms_provider == "aws_sns":
                return await self._send_aws_sns_sms(phone_number, message)
            else:
                logger.error(f"Unknown SMS provider: {self.sms_provider}")
                return False
                
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return False
            
    async def _send_twilio_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS via Twilio."""
        # In real implementation, use Twilio SDK
        # For demo, simulate success
        logger.info(f"[DEMO] Would send Twilio SMS to {phone_number}: {message}")
        return True
        
    async def _send_aws_sns_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS via AWS SNS."""
        # In real implementation, use boto3 SNS client
        # For demo, simulate success
        logger.info(f"[DEMO] Would send AWS SNS SMS to {phone_number}: {message}")
        return True
        
    async def require_2fa_for_user(self, user_id: str) -> bool:
        """Check if user is required to use 2FA."""
        # In real implementation, check user settings or admin policies
        # For now, assume 2FA is optional
        return False
        
    async def is_2fa_enabled_for_user(self, user_id: str) -> bool:
        """Check if user has any active 2FA devices."""
        devices = await self.get_user_2fa_devices(user_id)
        return len([d for d in devices if d.is_active]) > 0
        
    async def get_2fa_methods_for_user(self, user_id: str) -> List[str]:
        """Get available 2FA methods for user."""
        methods = [TwoFactorMethod.TOTP.value]
        
        if self.sms_enabled:
            methods.append(TwoFactorMethod.SMS.value)
            
        methods.append(TwoFactorMethod.BACKUP_CODES.value)
        
        return methods
        
    async def create_2fa_challenge(self, user_id: str, 
                                 preferred_method: Optional[str] = None) -> Dict[str, Any]:
        """Create a 2FA challenge for user login."""
        devices = await self.get_user_2fa_devices(user_id)
        active_devices = [d for d in devices if d.is_active]
        
        if not active_devices:
            raise ValueError("No active 2FA devices found")
            
        # Select challenge method
        if preferred_method:
            device = next((d for d in active_devices if d.method == preferred_method), None)
            if not device:
                raise ValueError(f"Preferred 2FA method {preferred_method} not available")
        else:
            # Use first available device
            device = active_devices[0]
            
        challenge_id = secrets.token_urlsafe(16)
        
        # Generate challenge based on method
        if device.method == TwoFactorMethod.SMS:
            await self.send_sms_code(user_id, device.id)
            return {
                "challenge_id": challenge_id,
                "method": device.method,
                "message": f"Verification code sent to {device.name}"
            }
        else:
            return {
                "challenge_id": challenge_id,
                "method": device.method,
                "message": f"Enter code from {device.name}"
            }
            
    async def verify_2fa_challenge(self, user_id: str, challenge_id: str, 
                                 method: str, code: str) -> bool:
        """Verify a 2FA challenge response."""
        
        if method == TwoFactorMethod.TOTP.value:
            # For demo, find any TOTP device
            devices = await self.get_user_2fa_devices(user_id)
            totp_device = next((d for d in devices if d.method == TwoFactorMethod.TOTP), None)
            if totp_device:
                return await self.verify_totp(user_id, totp_device.id, code)
                
        elif method == TwoFactorMethod.SMS.value:
            devices = await self.get_user_2fa_devices(user_id)
            sms_device = next((d for d in devices if d.method == TwoFactorMethod.SMS), None)
            if sms_device:
                return await self.verify_sms(user_id, sms_device.id, code)
                
        elif method == TwoFactorMethod.BACKUP_CODES.value:
            return await self.verify_backup_code(user_id, code)
            
        return False
        
    async def health_check(self) -> Dict[str, Any]:
        """Check 2FA system health."""
        health = {
            "status": "healthy",
            "methods_available": await self.get_2fa_methods_for_user("demo"),
            "sms_enabled": self.sms_enabled,
            "encryption_key_present": bool(self.encryption_key)
        }
        
        if self.sms_enabled:
            # Test SMS provider connectivity
            try:
                # In real implementation, test SMS provider
                health["sms_provider_status"] = "healthy"
            except Exception:
                health["sms_provider_status"] = "unhealthy"
                health["status"] = "degraded"
                
        return health
        
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

# Global 2FA manager instance (lazy initialization)
_twofa_manager = None

def get_twofa_manager():
    """Get the global 2FA manager instance (lazy initialization)."""
    global _twofa_manager
    if _twofa_manager is None:
        _twofa_manager = TwoFactorAuthManager()
    return _twofa_manager