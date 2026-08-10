import asyncio
import shutil
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../services/photoshare, portable regardless of clone location

# Point file storage at a throwaway local dir *before* anything imports
# routers.shares (which instantiates FileStorageService() at import time,
# and defaults to /app/storage -- not writable without root on a real machine).
TEST_STORAGE_DIR = "/tmp/photoshare_test_storage_shares_comments_tags_analytics_e2e"
shutil.rmtree(TEST_STORAGE_DIR, ignore_errors=True)
os.environ["STORAGE_PATH"] = TEST_STORAGE_DIR

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import app_database as adb
from routers.shares import router as shares_router
from routers.comments import router as comments_router
from routers.tags import router as tags_router
from routers.analytics import router as analytics_router
from auth_integration import get_current_user, get_optional_user, AuthenticatedUser

async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(adb.AppBase.metadata.create_all)
    adb.app_db_manager.engine = engine
    adb.app_db_manager.session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with adb.app_db_manager.session_factory() as session:
        mine = adb.Photo(user_uuid="user-1", user_email="u1@test.com", filename="mine.jpg",
                          original_filename="mine.jpg", content_type="image/jpeg", file_size=100,
                          storage_path="/tmp/mine.jpg", is_public=False)
        public = adb.Photo(user_uuid="user-2", user_email="u2@test.com", filename="pub.jpg",
                            original_filename="pub.jpg", content_type="image/jpeg", file_size=100,
                            storage_path="/tmp/pub.jpg", is_public=True)
        session.add_all([mine, public])
        await session.commit()
        await session.refresh(mine); await session.refresh(public)
        return mine.id, public.id

my_photo_id, public_photo_id = asyncio.run(setup_db())

app = FastAPI()
for r in (shares_router, comments_router, tags_router, analytics_router):
    app.include_router(r)

def fake_user():
    return AuthenticatedUser(
        {"uuid": "user-1", "email": "u1@test.com", "roles": ["user"],
         "permissions": ["albums:write", "albums:read", "photos:read", "photos:write", "comments:write"], "display_name": "Test User"},
        {"iat": 0, "exp": 9999999999},
    )

app.dependency_overrides[get_current_user] = fake_user
app.dependency_overrides[get_optional_user] = lambda: None  # anonymous by default; override per-test if needed
client = TestClient(app)

results = {"pass": 0, "fail": 0}
def check(cond, msg):
    if cond:
        results["pass"] += 1
        print(f"[PASS] {msg}")
    else:
        results["fail"] += 1
        print(f"[FAIL] {msg}")

# ---------------- SHARES ----------------
r = client.post(f"/api/photos/{my_photo_id}/share", json={"share_type": "password", "password": "hunter22"})
check(r.status_code == 201, f"create password share -> 201 (got {r.status_code}: {r.text})")
share = r.json()
token = share["share_token"]
check("share_url" in share, "share response includes share_url")

r = client.get(f"/api/shares/{token}")
check(r.status_code == 401, f"resolve share w/o password -> 401 (got {r.status_code})")

r = client.get(f"/api/shares/{token}", params={"password": "wrong"})
check(r.status_code == 401, "resolve share w/ wrong password -> 401")

r = client.get(f"/api/shares/{token}", params={"password": "hunter22"})
check(r.status_code == 200, f"resolve share w/ correct password -> 200 (got {r.status_code}: {r.text})")
check(r.json()["photo"]["id"] == my_photo_id, "resolved share returns correct photo")
check("password_hash" not in r.json()["share"], "password_hash not leaked in response")

r = client.get("/api/shares")
check(r.json()["total"] == 1, "list my shares shows 1")

share_id = share["id"]
r = client.delete(f"/api/shares/{share_id}")
check(r.status_code == 204, "revoke share -> 204")
r = client.get(f"/api/shares/{token}", params={"password": "hunter22"})
check(r.status_code == 404, "resolving revoked share -> 404")

# someone else's photo -> can't share it
r = client.post(f"/api/photos/{public_photo_id}/share", json={"share_type": "public"})
check(r.status_code == 403, f"sharing someone else's photo -> 403 (got {r.status_code})")

# ---------------- COMMENTS ----------------
r = client.post(f"/api/photos/{public_photo_id}/comments", json={"comment": "Nice shot!"})
check(r.status_code == 201, f"comment on public photo -> 201 (got {r.status_code}: {r.text})")
comment_id = r.json()["id"]
check(r.json()["commenter_name"] == "Test User", "commenter_name captured")

r = client.get(f"/api/photos/{public_photo_id}/comments")
check(r.json()["total"] == 1, "list comments shows 1")

r = client.delete(f"/api/comments/{comment_id}")
check(r.status_code == 204, "delete own comment -> 204")

# ---------------- TAGS ----------------
r = client.post(f"/api/photos/{my_photo_id}/tags", json={"tags": ["Sunset", "Beach", "sunset"]})
check(r.status_code == 201, f"add tags -> 201 (got {r.status_code}: {r.text})")
check(sorted(r.json()["added_tags"]) == ["beach", "sunset"], f"tags normalized+deduped (got {r.json()['added_tags']})")

r = client.get(f"/api/photos/{my_photo_id}/tags")
check(len(r.json()["tags"]) == 2, "list tags shows 2")

r = client.get("/api/tags/search", params={"q": "sunset"})
check(r.status_code == 200 and r.json()["total"] == 1, f"tag search finds photo (got {r.json()})")

r = client.delete(f"/api/photos/{my_photo_id}/tags/beach")
check(r.status_code == 204, "remove tag -> 204")
r = client.get(f"/api/photos/{my_photo_id}/tags")
check(len(r.json()["tags"]) == 1, "tag removed, 1 remains")

# can't tag someone else's photo
r = client.post(f"/api/photos/{public_photo_id}/tags", json={"tags": ["x"]})
check(r.status_code == 403, f"tagging someone else's photo -> 403 (got {r.status_code})")

# ---------------- ANALYTICS ----------------
r = client.post(f"/api/photos/{public_photo_id}/analytics/event", json={"event_type": "view"})
check(r.status_code == 201, f"record view event (anon) -> 201 (got {r.status_code}: {r.text})")

r = client.post(f"/api/photos/{my_photo_id}/analytics/event", json={"event_type": "bogus"})
check(r.status_code == 400, f"invalid event_type -> 400 (got {r.status_code})")

r = client.get(f"/api/photos/{my_photo_id}/analytics")
check(r.status_code == 200, f"owner reads own photo analytics -> 200 (got {r.status_code}: {r.text})")

r = client.get(f"/api/photos/{public_photo_id}/analytics")
check(r.status_code == 403, f"non-owner reads photo analytics -> 403 (got {r.status_code})")

r = client.get("/api/analytics/summary")
check(r.status_code == 200 and r.json()["photo_count"] == 1, f"account analytics summary -> 200, 1 photo (got {r.json()})")

print(f"\n{results['pass']} passed, {results['fail']} failed")
if results["fail"]:
    raise SystemExit(1)
print("ALL SHARES/COMMENTS/TAGS/ANALYTICS E2E CHECKS PASSED")
