"""
End-to-end checks for the signed share-download flow added on top of
routers/shares.py: 1-hour signed download URLs, the reactive expiry signal
(HTTP 410 signed_url_expired), tamper detection, live re-validation of the
share record at download time (revocation and max_downloads), and the
download_count increment bug fix.

Uses a real FastAPI app dispatching real HTTP requests via TestClient against
a real (in-memory SQLite) database -- same pattern as the other e2e scripts
in this folder. Run standalone: python tests/test_share_download_e2e.py
"""

import asyncio
import os
import shutil
import sys
import time

# Point file storage at a throwaway local dir *before* anything imports
# routers.shares (which instantiates FileStorageService() at import time).
TEST_STORAGE_DIR = "/tmp/photoshare_test_storage_download_e2e"
shutil.rmtree(TEST_STORAGE_DIR, ignore_errors=True)
os.environ["STORAGE_PATH"] = TEST_STORAGE_DIR

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../services/photoshare, portable regardless of clone location

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import app_database as adb
from routers.shares import router as shares_router, storage_service
from auth_integration import get_current_user, AuthenticatedUser

STORAGE_REL_PATH = "owner1/photo.jpg"
FILE_BYTES = b"fake-jpeg-bytes-for-e2e-test"


async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(adb.AppBase.metadata.create_all)
    adb.app_db_manager.engine = engine
    adb.app_db_manager.session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with adb.app_db_manager.session_factory() as session:
        photo = adb.Photo(
            user_uuid="owner-1", user_email="owner@test.com", filename="photo.jpg",
            original_filename="photo.jpg", content_type="image/jpeg", file_size=len(FILE_BYTES),
            storage_path=STORAGE_REL_PATH, is_public=False,
        )
        session.add(photo)
        await session.commit()
        await session.refresh(photo)
        return photo.id


photo_id = asyncio.run(setup_db())

# Write the actual file bytes where retrieve_file() will look for them.
full_path = os.path.join(TEST_STORAGE_DIR, STORAGE_REL_PATH)
os.makedirs(os.path.dirname(full_path), exist_ok=True)
with open(full_path, "wb") as f:
    f.write(FILE_BYTES)

app = FastAPI()
app.include_router(shares_router)


def fake_owner():
    return AuthenticatedUser(
        {"uuid": "owner-1", "email": "owner@test.com", "roles": ["user"],
         "permissions": ["photos:read", "photos:write"], "display_name": "Owner"},
        {"iat": 0, "exp": 9999999999},
    )


app.dependency_overrides[get_current_user] = fake_owner
client = TestClient(app)

results = {"pass": 0, "fail": 0}


def check(cond, msg):
    if cond:
        results["pass"] += 1
        print(f"[PASS] {msg}")
    else:
        results["fail"] += 1
        print(f"[FAIL] {msg}")


def create_share(max_downloads=None):
    payload = {"share_type": "public"}
    if max_downloads is not None:
        payload["max_downloads"] = max_downloads
    r = client.post(f"/api/photos/{photo_id}/share", json=payload)
    check(r.status_code == 201, f"create share -> 201 (got {r.status_code}: {r.text})")
    return r.json()


# ---------------- resolve_share returns a 1-hour signed download URL ----------------
share = create_share()
token = share["share_token"]

r = client.get(f"/api/shares/{token}")
check(r.status_code == 200, f"resolve share -> 200 (got {r.status_code}: {r.text})")
body = r.json()
check("download" in body, "resolve response includes a download block")
check(body["download"]["expires_in_seconds"] == 3600, "download URL TTL is exactly 3600 seconds (1 hour)")
check("expires_at" in body["download"], "download block includes an explicit expires_at timestamp")
download_url = body["download"]["url"]
check("/download?expires=" in download_url and "&signature=" in download_url, "download URL carries expires+signature params")

# ---------------- happy path: download succeeds and content matches ----------------
r = client.get(download_url)
check(r.status_code == 200, f"download with fresh signed URL -> 200 (got {r.status_code}: {getattr(r, 'text', '')[:200]})")
check(r.content == FILE_BYTES, "downloaded bytes match stored file content")
check(r.headers.get("cache-control") == "no-store", "download response sets Cache-Control: no-store")

# download_count increments (bug fix: previously never incremented anywhere)
r = client.get("/api/shares")
share_after = next(s for s in r.json()["shares"] if s["share_token"] == token)
check(share_after["download_count"] == 1, f"share.download_count incremented after download (got {share_after['download_count']})")

# ---------------- reactive expiry signal: client can detect an expired URL ----------------
expired_signed = storage_service.sign_payload(token, expires_in=-10)  # already-expired on purpose
expired_url = f"/api/shares/{token}/download?expires={expired_signed['expires_at']}&signature={expired_signed['signature']}"
r = client.get(expired_url)
check(r.status_code == 410, f"expired signed URL -> 410 (got {r.status_code})")
check(r.json().get("error") == "signed_url_expired", f"expired signed URL error code is 'signed_url_expired' (got {r.json()})")

# ---------------- tamper detection ----------------
valid_signed = storage_service.sign_payload(token, expires_in=3600)
tampered_url = f"/api/shares/{token}/download?expires={valid_signed['expires_at']}&signature=deadbeef" * 1
tampered_url = f"/api/shares/{token}/download?expires={valid_signed['expires_at']}&signature=deadbeef"
r = client.get(tampered_url)
check(r.status_code == 403, f"tampered signature -> 403 (got {r.status_code})")
check(r.json().get("error") == "invalid_signature", f"tampered signature error code is 'invalid_signature' (got {r.json()})")

# ---------------- malformed params ----------------
r = client.get(f"/api/shares/{token}/download?expires=not-a-number&signature=whatever")
check(r.status_code == 400, f"malformed expires param -> 400 (got {r.status_code})")
check(r.json().get("error") == "malformed_signature", f"malformed param error code is 'malformed_signature' (got {r.json()})")

# ---------------- live re-validation: revoking a share invalidates an already-issued, still-time-valid URL ----------------
share2 = create_share()
token2 = share2["share_token"]
r = client.get(f"/api/shares/{token2}")
still_fresh_download_url = r.json()["download"]["url"]

r = client.delete(f"/api/shares/{share2['id']}")
check(r.status_code == 204, "revoke second share -> 204")

r = client.get(still_fresh_download_url)
check(r.status_code == 404, f"download via a still-time-valid URL for a revoked share -> 404 (got {r.status_code})")
check(r.json().get("error") == "share_not_found", f"revoked-share download error code is 'share_not_found' (got {r.json()})")

# ---------------- live re-validation: max_downloads enforced at download time, not issue time ----------------
share3 = create_share(max_downloads=1)
token3 = share3["share_token"]

r = client.get(f"/api/shares/{token3}")
url_a = r.json()["download"]["url"]
r = client.get(f"/api/shares/{token3}")
url_b = r.json()["download"]["url"]  # a second, independently-issued signed URL for the same share

r = client.get(url_a)
check(r.status_code == 200, f"first download against max_downloads=1 share -> 200 (got {r.status_code})")

r = client.get(url_b)
check(r.status_code == 410, f"second download against max_downloads=1 share -> 410 (got {r.status_code})")
check(r.json().get("error") == "download_limit_reached", f"over-limit error code is 'download_limit_reached' (got {r.json()})")

print(f"\n{results['pass']} passed, {results['fail']} failed")
if results["fail"]:
    raise SystemExit(1)
print("ALL SHARE-DOWNLOAD E2E CHECKS PASSED")
