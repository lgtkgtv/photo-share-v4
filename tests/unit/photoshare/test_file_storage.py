#!/usr/bin/env python3
"""
Unit tests for file storage functionality.

Rewritten to match the actual FileStorageService implementation
(services/photoshare/file_storage.py). The class this file used to test
(StorageManager, with save_file/get_file_info/cleanup_old_files/etc.) does
not exist in the codebase -- the real service is FileStorageService, with
a different, bytes-based API (store_file/retrieve_file/delete_file) plus
HMAC-signed URL helpers used by the share-download flow.
"""
import hashlib
import hmac
import time
from urllib.parse import urlparse, parse_qs

import pytest
from unittest.mock import patch, AsyncMock

from services.photoshare.file_storage import FileStorageService


@pytest.fixture
def storage_service(tmp_path, monkeypatch):
    """Create a FileStorageService instance backed by a temp directory."""
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "1")
    monkeypatch.setenv("STORAGE_SECRET_KEY", "test-secret-key")
    return FileStorageService()


class TestFileHashing:
    """Test internal SHA-256 content hashing."""

    def test_generate_file_hash_is_sha256(self, storage_service):
        content = b"hello world"
        assert storage_service._generate_file_hash(content) == hashlib.sha256(content).hexdigest()

    def test_generate_file_hash_differs_for_different_content(self, storage_service):
        assert storage_service._generate_file_hash(b"a") != storage_service._generate_file_hash(b"b")


class TestStoragePath:
    """Test storage path layout."""

    def test_get_storage_path_format(self, storage_service):
        assert storage_service._get_storage_path(42, "photo.jpg") == "users/42/photos/photo.jpg"


class TestStoreRetrieveDelete:
    """Test the store_file/retrieve_file/delete_file lifecycle."""

    @pytest.mark.asyncio
    async def test_store_file_writes_to_disk_and_returns_metadata(self, storage_service, tmp_path):
        content = b"fake image bytes"
        result = await storage_service.store_file(1, "test.jpg", content, "image/jpeg")

        assert result["file_size"] == len(content)
        assert result["content_type"] == "image/jpeg"
        assert result["platform_stored"] is True
        assert result["storage_path"] == "users/1/photos/test.jpg"
        assert result["file_hash"] == hashlib.sha256(content).hexdigest()

        stored_file = tmp_path / "users" / "1" / "photos" / "test.jpg"
        assert stored_file.read_bytes() == content

    @pytest.mark.asyncio
    async def test_store_file_rejects_oversized_content(self, storage_service):
        too_big = b"x" * (2 * 1024 * 1024)  # exceeds the 1MB limit set in the fixture
        with pytest.raises(ValueError):
            await storage_service.store_file(1, "big.jpg", too_big, "image/jpeg")

    @pytest.mark.asyncio
    async def test_retrieve_file_returns_stored_content(self, storage_service):
        content = b"round trip bytes"
        stored = await storage_service.store_file(2, "roundtrip.jpg", content, "image/jpeg")

        assert await storage_service.retrieve_file(stored["storage_path"]) == content

    @pytest.mark.asyncio
    async def test_retrieve_file_missing_locally_falls_back_to_platform(self, storage_service):
        with patch.object(storage_service, "_download_from_platform_storage", AsyncMock(return_value=None)) as mock_dl:
            result = await storage_service.retrieve_file("users/9/photos/nope.jpg")

        assert result is None
        mock_dl.assert_awaited_once_with("users/9/photos/nope.jpg")

    @pytest.mark.asyncio
    async def test_delete_file_removes_local_file(self, storage_service, tmp_path):
        content = b"to be deleted"
        stored = await storage_service.store_file(3, "delete_me.jpg", content, "image/jpeg")
        stored_file = tmp_path / "users" / "3" / "photos" / "delete_me.jpg"
        assert stored_file.exists()

        assert await storage_service.delete_file(stored["storage_path"]) is True
        assert not stored_file.exists()


class TestSignedUrls:
    """Test the storage_path-scoped signed URL helpers."""

    def test_generate_and_verify_signed_url_round_trip(self, storage_service):
        url = storage_service.generate_signed_url("users/1/photos/a.jpg", expires_in=60)
        assert url.startswith("/api/photos/secure/users/1/photos/a.jpg?")

        query = parse_qs(urlparse(url).query)
        assert storage_service.verify_signed_url(
            "users/1/photos/a.jpg", query["expires"][0], query["signature"][0]
        ) is True

    def test_verify_signed_url_rejects_expired(self, storage_service):
        expired_ts = int(time.time()) - 10
        payload = f"users/1/photos/a.jpg:{expired_ts}"
        signature = hmac.new(storage_service.storage_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

        assert storage_service.verify_signed_url("users/1/photos/a.jpg", str(expired_ts), signature) is False

    def test_verify_signed_url_rejects_tampered_signature(self, storage_service):
        url = storage_service.generate_signed_url("users/1/photos/a.jpg", expires_in=60)
        expires = parse_qs(urlparse(url).query)["expires"][0]

        assert storage_service.verify_signed_url("users/1/photos/a.jpg", expires, "tampered") is False


class TestPayloadSigning:
    """Test the generic HMAC payload signer used by the share-download flow."""

    def test_sign_and_verify_payload_round_trip(self, storage_service):
        signed = storage_service.sign_payload("share-token-abc", expires_in=3600)
        result = storage_service.verify_signed_payload(
            "share-token-abc", str(signed["expires_at"]), signed["signature"]
        )
        assert result == {"valid": True, "reason": "ok"}

    def test_verify_signed_payload_expired(self, storage_service):
        signed = storage_service.sign_payload("share-token-abc", expires_in=-10)
        result = storage_service.verify_signed_payload(
            "share-token-abc", str(signed["expires_at"]), signed["signature"]
        )
        assert result == {"valid": False, "reason": "expired"}

    def test_verify_signed_payload_invalid_signature(self, storage_service):
        signed = storage_service.sign_payload("share-token-abc", expires_in=3600)
        result = storage_service.verify_signed_payload(
            "share-token-abc", str(signed["expires_at"]), "bad-signature"
        )
        assert result == {"valid": False, "reason": "invalid_signature"}

    def test_verify_signed_payload_malformed_expires(self, storage_service):
        result = storage_service.verify_signed_payload("share-token-abc", "not-a-number", "whatever")
        assert result == {"valid": False, "reason": "malformed"}


class TestHealthCheck:
    """Test the storage health check."""

    @pytest.mark.asyncio
    async def test_health_check_reports_local_storage_writable(self, storage_service):
        with patch("services.photoshare.file_storage.aiohttp.ClientSession", side_effect=Exception("no network")):
            result = await storage_service.health_check()

        assert result["local_storage"] is True
        assert result["platform_storage"] is False
