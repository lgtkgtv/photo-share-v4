import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../services/photoshare, portable regardless of clone location

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import app_database as adb
from routers.albums import router as albums_router
from auth_integration import get_current_user, AuthenticatedUser

# --- Build a real in-memory SQLite-backed app instance ---

async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(adb.AppBase.metadata.create_all)
    adb.app_db_manager.engine = engine
    adb.app_db_manager.session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed two photos owned by our test user
    async with adb.app_db_manager.session_factory() as session:
        p1 = adb.Photo(user_uuid="user-1", user_email="u1@test.com", filename="a.jpg",
                        original_filename="a.jpg", content_type="image/jpeg", file_size=100,
                        storage_path="/tmp/a.jpg")
        p2 = adb.Photo(user_uuid="user-1", user_email="u1@test.com", filename="b.jpg",
                        original_filename="b.jpg", content_type="image/jpeg", file_size=100,
                        storage_path="/tmp/b.jpg")
        p3_other_user = adb.Photo(user_uuid="user-2", user_email="u2@test.com", filename="c.jpg",
                        original_filename="c.jpg", content_type="image/jpeg", file_size=100,
                        storage_path="/tmp/c.jpg")
        session.add_all([p1, p2, p3_other_user])
        await session.commit()
        await session.refresh(p1); await session.refresh(p2); await session.refresh(p3_other_user)
        return p1.id, p2.id, p3_other_user.id

photo1_id, photo2_id, other_users_photo_id = asyncio.run(setup_db())

app = FastAPI()
app.include_router(albums_router)

def fake_user():
    return AuthenticatedUser(
        {"uuid": "user-1", "email": "u1@test.com", "roles": ["user"],
         "permissions": ["albums:write", "albums:read", "photos:read"]},
        {"iat": 0, "exp": 9999999999},
    )

app.dependency_overrides[get_current_user] = fake_user
client = TestClient(app)

def check(cond, msg):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {msg}")
    if not cond:
        raise SystemExit(1)

# 1. Create album
r = client.post("/api/albums/", json={"name": "Vacation 2026", "description": "Trip photos", "is_public": False})
check(r.status_code == 201, f"create album -> 201 (got {r.status_code}: {r.text})")
album = r.json()
album_id = album["id"]
check(album["name"] == "Vacation 2026", "album name persisted")
check(album["photo_count"] == 0, "new album has photo_count 0")

# 2. List albums
r = client.get("/api/albums/")
check(r.status_code == 200, "list albums -> 200")
check(r.json()["total"] == 1, "list shows 1 album")

# 3. Add photos (one owned, one belonging to another user -> should partially fail)
r = client.post(f"/api/albums/{album_id}/photos", json={"photo_ids": [photo1_id, photo2_id]})
check(r.status_code == 201, f"add owned photos -> 201 (got {r.status_code}: {r.text})")
check(r.json()["photo_count"] == 2, "photo_count updated to 2")

r = client.post(f"/api/albums/{album_id}/photos", json={"photo_ids": [other_users_photo_id]})
check(r.status_code == 403, f"adding someone else's photo -> 403 (got {r.status_code})")

# 4. Get album detail with photos
r = client.get(f"/api/albums/{album_id}")
check(r.status_code == 200, "get album detail -> 200")
detail = r.json()
check(len(detail["photos"]) == 2, f"album detail contains 2 photos (got {len(detail['photos'])})")

# 5. Set cover photo
r = client.put(f"/api/albums/{album_id}", json={"cover_photo_id": photo1_id})
check(r.status_code == 200, "set cover photo -> 200")
check(r.json()["cover_photo_id"] == photo1_id, "cover_photo_id persisted")

# 6. Remove a photo
r = client.delete(f"/api/albums/{album_id}/photos/{photo2_id}")
check(r.status_code == 204, f"remove photo -> 204 (got {r.status_code})")
r = client.get(f"/api/albums/{album_id}")
check(r.json()["photo_count"] == 1, "photo_count decremented to 1")

# 7. Delete album
r = client.delete(f"/api/albums/{album_id}")
check(r.status_code == 204, "delete album -> 204")
r = client.get(f"/api/albums/{album_id}")
check(r.status_code == 404, "deleted album -> 404 on fetch")

print("\nALL ALBUM E2E CHECKS PASSED")
