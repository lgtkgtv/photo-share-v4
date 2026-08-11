#!/usr/bin/env python3
"""
Unit tests for two-factor authentication.
"""
import sys
from pathlib import Path
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

# services/auth-service is a standalone deployable unit (own Dockerfile,
# flat internal imports), not a `services.auth_service` Python package --
# import it the way the container does, via sys.path + flat module name.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "services" / "auth-service"))

from two_factor_auth import (
    TwoFactorMethod, TwoFactorDevice, BackupCode, TwoFactorAuthManager
)

class TestTwoFactorDevice:
    """Test Two-Factor Device data class."""
    
    def test_device_creation(self):
        """Test 2FA device creation."""
        created_at = datetime.now(timezone.utc)
        
        device = TwoFactorDevice(
            id="device123",
            user_id="user123",
            method=TwoFactorMethod.TOTP,
            name="Mobile App",
            secret="encrypted_secret",
            created_at=created_at,
            is_active=True
        )
        
        assert device.id == "device123"
        assert device.user_id == "user123"
        assert device.method == TwoFactorMethod.TOTP
        assert device.name == "Mobile App"
        assert device.secret == "encrypted_secret"
        assert device.created_at == created_at
        assert device.is_active is True
    
    def test_device_to_dict(self):
        """Test device serialization to dictionary."""
        created_at = datetime.now(timezone.utc)
        
        device = TwoFactorDevice(
            id="device123",
            user_id="user123",
            method=TwoFactorMethod.TOTP,
            name="Mobile App",
            secret="encrypted_secret",
            created_at=created_at
        )
        
        device_dict = device.to_dict()
        
        assert device_dict["id"] == "device123"
        assert device_dict["user_id"] == "user123"
        assert device_dict["method"] == TwoFactorMethod.TOTP
        assert device_dict["name"] == "Mobile App"
        assert "secret" not in device_dict  # Should not be serialized

class TestBackupCode:
    """Test Backup Code data class."""
    
    def test_backup_code_creation(self):
        """Test backup code creation."""
        created_at = datetime.now(timezone.utc)
        
        backup_code = BackupCode(
            code="12345678",
            user_id="user123",
            created_at=created_at,
            is_used=False
        )
        
        assert backup_code.code == "12345678"
        assert backup_code.user_id == "user123"
        assert backup_code.created_at == created_at
        assert backup_code.is_used is False

class TestTwoFactorAuthManager:
    """Test Two-Factor Authentication Manager."""
    
    @pytest.fixture
    def manager(self):
        """Create 2FA manager with test configuration."""
        with patch.dict('os.environ', {
            'TWOFA_ENCRYPTION_KEY': '4SimbvVNZ3lFGeJLcn1y0pBOCXgVrwmaMGHY1VvyxMs=',
            'SMS_PROVIDER_API_KEY': 'test_sms_key',
            'SMS_FROM_NUMBER': '+1234567890',
            'WEBAUTHN_RP_ID': 'localhost',
            'WEBAUTHN_RP_NAME': 'PhotoShare Test'
        }):
            return TwoFactorAuthManager()
    
    @pytest.mark.asyncio
    async def test_setup_totp(self, manager):
        """Test TOTP setup."""
        with patch('pyotp.random_base32', return_value='TESTTOTP123456789012'):
            with patch('pyotp.TOTP') as mock_totp_class:
                mock_totp = Mock()
                mock_totp.provisioning_uri.return_value = "otpauth://totp/test"
                mock_totp_class.return_value = mock_totp
                
                with patch('qrcode.QRCode') as mock_qr_class:
                    mock_qr = Mock()
                    mock_qr_image = Mock()
                    mock_qr.make_image.return_value = mock_qr_image
                    mock_qr_class.return_value = mock_qr
                    
                    with patch('two_factor_auth.BytesIO'):
                        with patch('base64.b64encode', return_value=b'test_qr_code'):
                            result = await manager.setup_totp("user123", "test@example.com", "Test App")
                            
                            assert "device_id" in result
                            assert result["secret"] == "TESTTOTP123456789012"
                            assert "qr_code" in result
                            assert "backup_codes" in result
                            assert len(result["backup_codes"]) == 10
    
    @pytest.mark.asyncio
    async def test_verify_totp_success(self, manager):
        """Test successful TOTP verification."""
        # For demo purposes, the verify_totp method accepts any 6-digit code
        result = await manager.verify_totp("user123", "device123", "123456")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_totp_failure(self, manager):
        """Test failed TOTP verification."""
        # Invalid code format
        result = await manager.verify_totp("user123", "device123", "12345")
        assert result is False
        
        # Non-digit code
        result = await manager.verify_totp("user123", "device123", "abcdef")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_setup_sms_enabled(self, manager):
        """Test SMS setup when SMS is enabled."""
        manager.sms_enabled = True
        
        with patch.object(manager, '_validate_phone_number', return_value=True):
            with patch.object(manager, '_send_sms', return_value=True):
                result = await manager.setup_sms("user123", "+1234567890")
                
                assert "device_id" in result
                assert result["phone_number"] == "+1234567890"
                assert "message" in result
    
    @pytest.mark.asyncio
    async def test_setup_sms_disabled(self, manager):
        """Test SMS setup when SMS is disabled."""
        manager.sms_enabled = False
        
        with pytest.raises(ValueError, match="SMS 2FA is not enabled"):
            await manager.setup_sms("user123", "+1234567890")
    
    @pytest.mark.asyncio
    async def test_setup_sms_invalid_phone(self, manager):
        """Test SMS setup with invalid phone number."""
        manager.sms_enabled = True
        
        with patch.object(manager, '_validate_phone_number', return_value=False):
            with pytest.raises(ValueError, match="Invalid phone number format"):
                await manager.setup_sms("user123", "invalid_phone")
    
    @pytest.mark.asyncio
    async def test_verify_sms_setup_success(self, manager):
        """Test successful SMS setup verification."""
        result = await manager.verify_sms_setup("device123", "123456")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_sms_setup_failure(self, manager):
        """Test failed SMS setup verification."""
        result = await manager.verify_sms_setup("device123", "12345")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_sms_code_enabled(self, manager):
        """Test sending SMS code when SMS is enabled."""
        manager.sms_enabled = True
        result = await manager.send_sms_code("user123", "device123")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_sms_code_disabled(self, manager):
        """Test sending SMS code when SMS is disabled."""
        manager.sms_enabled = False
        result = await manager.send_sms_code("user123", "device123")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_sms_success(self, manager):
        """Test successful SMS verification."""
        result = await manager.verify_sms("user123", "device123", "123456")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_sms_failure(self, manager):
        """Test failed SMS verification."""
        result = await manager.verify_sms("user123", "device123", "12345")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_generate_backup_codes(self, manager):
        """Test backup code generation."""
        with patch('secrets.token_urlsafe', side_effect=lambda x: 'TESTCODE'):
            codes = await manager._generate_backup_codes("user123", count=5)
            
            assert len(codes) == 5
            assert all(len(code) == 8 for code in codes)
            assert all(code == "TESTCODE" for code in codes)
    
    @pytest.mark.asyncio
    async def test_verify_backup_code_success(self, manager):
        """Test successful backup code verification."""
        result = await manager.verify_backup_code("user123", "ABCD1234")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_backup_code_failure(self, manager):
        """Test failed backup code verification."""
        result = await manager.verify_backup_code("user123", "ABC123")  # Too short
        assert result is False
        
        result = await manager.verify_backup_code("user123", "ABC!@#$%")  # Invalid characters
        assert result is False
    
    def test_generate_sms_code(self, manager):
        """Test SMS code generation."""
        code = manager._generate_sms_code()
        assert len(code) == 6
        assert code.isdigit()
        assert 100000 <= int(code) <= 999999
    
    def test_validate_phone_number_valid(self, manager):
        """Test phone number validation with valid numbers."""
        assert manager._validate_phone_number("+1234567890") is True
        assert manager._validate_phone_number("1234567890") is True
        assert manager._validate_phone_number("+44 20 7123 4567") is True
    
    def test_validate_phone_number_invalid(self, manager):
        """Test phone number validation with invalid numbers."""
        assert manager._validate_phone_number("123") is False  # Too short
        assert manager._validate_phone_number("123456789012345678") is False  # Too long
        assert manager._validate_phone_number("abcdefghij") is False  # Non-digits
    
    @pytest.mark.asyncio
    async def test_get_user_2fa_devices(self, manager):
        """Test getting user's 2FA devices."""
        devices = await manager.get_user_2fa_devices("user123")
        assert isinstance(devices, list)
        assert len(devices) == 0  # Demo implementation returns empty list
    
    @pytest.mark.asyncio
    async def test_disable_2fa_device(self, manager):
        """Test disabling a 2FA device."""
        result = await manager.disable_2fa_device("user123", "device123")
        assert result is True  # Demo implementation always returns True
    
    @pytest.mark.asyncio
    async def test_require_2fa_for_user(self, manager):
        """Test checking if user is required to use 2FA."""
        result = await manager.require_2fa_for_user("user123")
        assert result is False  # Demo implementation returns False (optional)
    
    @pytest.mark.asyncio
    async def test_is_2fa_enabled_for_user(self, manager):
        """Test checking if user has 2FA enabled."""
        result = await manager.is_2fa_enabled_for_user("user123")
        assert result is False  # Demo implementation returns False
    
    @pytest.mark.asyncio
    async def test_get_2fa_methods_for_user(self, manager):
        """Test getting available 2FA methods for user."""
        manager.sms_enabled = True
        methods = await manager.get_2fa_methods_for_user("user123")
        
        assert TwoFactorMethod.TOTP.value in methods
        assert TwoFactorMethod.SMS.value in methods
        assert TwoFactorMethod.BACKUP_CODES.value in methods
    
    @pytest.mark.asyncio
    async def test_create_2fa_challenge(self, manager):
        """Test creating a 2FA challenge."""
        with patch.object(manager, 'get_user_2fa_devices') as mock_get_devices:
            mock_device = TwoFactorDevice(
                id="device123",
                user_id="user123",
                method=TwoFactorMethod.TOTP,
                name="Test Device",
                secret="encrypted_secret",
                created_at=datetime.now(timezone.utc),
                is_active=True
            )
            mock_get_devices.return_value = [mock_device]
            
            challenge = await manager.create_2fa_challenge("user123")
            
            assert "challenge_id" in challenge
            assert challenge["method"] == TwoFactorMethod.TOTP
            assert "message" in challenge
    
    @pytest.mark.asyncio
    async def test_verify_2fa_challenge_totp(self, manager):
        """Test verifying a TOTP 2FA challenge."""
        with patch.object(manager, 'get_user_2fa_devices') as mock_get_devices:
            with patch.object(manager, 'verify_totp', return_value=True):
                mock_device = TwoFactorDevice(
                    id="device123",
                    user_id="user123",
                    method=TwoFactorMethod.TOTP,
                    name="Test Device",
                    secret="encrypted_secret",
                    created_at=datetime.now(timezone.utc),
                    is_active=True
                )
                mock_get_devices.return_value = [mock_device]
                
                result = await manager.verify_2fa_challenge(
                    "user123", "challenge123", TwoFactorMethod.TOTP.value, "123456"
                )
                
                assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_2fa_challenge_backup_codes(self, manager):
        """Test verifying a backup code 2FA challenge."""
        with patch.object(manager, 'verify_backup_code', return_value=True):
            result = await manager.verify_2fa_challenge(
                "user123", "challenge123", TwoFactorMethod.BACKUP_CODES.value, "ABCD1234"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check(self, manager):
        """Test 2FA system health check."""
        manager.sms_enabled = True
        
        health = await manager.health_check()
        
        assert health["status"] == "healthy"
        assert "methods_available" in health
        assert health["sms_enabled"] is True
        assert health["encryption_key_present"] is True