"""
Album API
=========

CRUD for albums plus adding/removing photos from an album.

Backed by the `Album` and `AlbumPhoto` models in app_database.py, which have
existed since the initial schema but had no API surface. This router is the
first thing that actually reads/writes them.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func

from app_database import get_app_db_manager, Album, AlbumPhoto, Photo
from auth_integration import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/api/albums", tags=["albums"])


# ---------------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------------

class AlbumCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    is_public: bool = False


class AlbumUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    is_public: Optional[bool] = None
    cover_photo_id: Optional[int] = None


class AlbumAddPhotos(BaseModel):
    photo_ids: List[int] = Field(..., min_length=1, max_length=200)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_owned_album(session, album_id: int, current_user: AuthenticatedUser) -> Album:
    """Fetch an album and raise 404/403 if it doesn't exist or isn't accessible."""
    result = await session.execute(select(Album).where(Album.id == album_id))
    album = result.scalar_one_or_none()

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    can_access = (
        album.user_uuid == current_user.uuid
        or album.is_public
        or current_user.is_admin()
    )
    if not can_access:
        raise HTTPException(status_code=403, detail="No permission to view this album")

    return album


def _can_modify_album(album: Album, current_user: AuthenticatedUser) -> bool:
    return album.user_uuid == current_user.uuid or current_user.is_admin()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/", status_code=201)
async def create_album(
    payload: AlbumCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new album owned by the current user."""
    if not current_user.has_permission("albums", "write"):
        raise HTTPException(status_code=403, detail="No permission to create albums")

    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            album = Album(
                user_uuid=current_user.uuid,
                user_email=current_user.email,
                name=payload.name,
                description=payload.description,
                is_public=payload.is_public,
            )
            session.add(album)
            await session.commit()
            await session.refresh(album)
            return album.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create album: {str(e)}")


@router.get("/")
async def list_albums(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List the current user's albums (owned only -- use /public for others' public albums)."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            count_query = select(func.count()).select_from(Album).where(Album.user_uuid == current_user.uuid)
            total = (await session.execute(count_query)).scalar_one()

            offset = (page - 1) * per_page
            albums_query = (
                select(Album)
                .where(Album.user_uuid == current_user.uuid)
                .order_by(Album.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            albums = (await session.execute(albums_query)).scalars().all()

            return {
                "albums": [a.to_dict() for a in albums],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list albums: {str(e)}")


@router.get("/public")
async def list_public_albums(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List public albums across all users -- no auth required, mirrors /api/photos/public."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            count_query = select(func.count()).select_from(Album).where(Album.is_public == True)  # noqa: E712
            total = (await session.execute(count_query)).scalar_one()

            offset = (page - 1) * per_page
            albums_query = (
                select(Album)
                .where(Album.is_public == True)  # noqa: E712
                .order_by(Album.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            albums = (await session.execute(albums_query)).scalars().all()

            return {
                "albums": [a.to_dict() for a in albums],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list public albums: {str(e)}")


@router.get("/{album_id}")
async def get_album(
    album_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get an album's details plus the photos in it, in sort order."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            album = await _get_owned_album(session, album_id, current_user)

            photos_query = (
                select(Photo, AlbumPhoto.sort_order)
                .join(AlbumPhoto, AlbumPhoto.photo_id == Photo.id)
                .where(AlbumPhoto.album_id == album_id)
                .order_by(AlbumPhoto.sort_order.asc(), AlbumPhoto.added_at.asc())
            )
            rows = (await session.execute(photos_query)).all()

            album_dict = album.to_dict()
            album_dict["photos"] = [photo.to_dict() for photo, _sort_order in rows]
            return album_dict

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch album: {str(e)}")


@router.put("/{album_id}")
async def update_album(
    album_id: int,
    payload: AlbumUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update album name/description/visibility/cover photo. Owner or admin only."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            album = await _get_owned_album(session, album_id, current_user)

            if not _can_modify_album(album, current_user):
                raise HTTPException(status_code=403, detail="No permission to modify this album")

            if payload.name is not None:
                album.name = payload.name
            if payload.description is not None:
                album.description = payload.description
            if payload.is_public is not None:
                album.is_public = payload.is_public
            if payload.cover_photo_id is not None:
                # Cover photo must actually be in the album.
                membership = await session.execute(
                    select(AlbumPhoto).where(
                        AlbumPhoto.album_id == album_id,
                        AlbumPhoto.photo_id == payload.cover_photo_id,
                    )
                )
                if not membership.scalar_one_or_none():
                    raise HTTPException(
                        status_code=400,
                        detail="cover_photo_id must reference a photo already in this album",
                    )
                album.cover_photo_id = payload.cover_photo_id

            album.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(album)
            return album.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update album: {str(e)}")


@router.delete("/{album_id}", status_code=204)
async def delete_album(
    album_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete an album. Owner or admin only. Photos themselves are untouched."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            album = await _get_owned_album(session, album_id, current_user)

            if not _can_modify_album(album, current_user):
                raise HTTPException(status_code=403, detail="No permission to delete this album")

            await session.delete(album)  # AlbumPhoto rows cascade via ondelete="CASCADE"
            await session.commit()
            return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete album: {str(e)}")


@router.post("/{album_id}/photos", status_code=201)
async def add_photos_to_album(
    album_id: int,
    payload: AlbumAddPhotos,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Add one or more photos to an album. Caller must own the album and each photo."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            album = await _get_owned_album(session, album_id, current_user)

            if not _can_modify_album(album, current_user):
                raise HTTPException(status_code=403, detail="No permission to modify this album")

            photos_query = select(Photo).where(Photo.id.in_(payload.photo_ids))
            photos = (await session.execute(photos_query)).scalars().all()
            found_ids = {p.id for p in photos}

            missing = set(payload.photo_ids) - found_ids
            if missing:
                raise HTTPException(status_code=404, detail=f"Photo(s) not found: {sorted(missing)}")

            unauthorized = [
                p.id for p in photos
                if not current_user.can_modify_photo(p.user_uuid) and not current_user.is_admin()
            ]
            if unauthorized:
                raise HTTPException(
                    status_code=403,
                    detail=f"No permission to add photo(s) to album: {sorted(unauthorized)}",
                )

            existing_query = select(AlbumPhoto.photo_id).where(AlbumPhoto.album_id == album_id)
            already_in_album = {row[0] for row in (await session.execute(existing_query)).all()}

            max_sort = (
                await session.execute(
                    select(func.coalesce(func.max(AlbumPhoto.sort_order), -1)).where(
                        AlbumPhoto.album_id == album_id
                    )
                )
            ).scalar_one()

            added = []
            next_sort = max_sort + 1
            for photo_id in payload.photo_ids:
                if photo_id in already_in_album:
                    continue
                session.add(AlbumPhoto(album_id=album_id, photo_id=photo_id, sort_order=next_sort))
                added.append(photo_id)
                next_sort += 1

            album.photo_count = (album.photo_count or 0) + len(added)
            album.updated_at = datetime.now(timezone.utc)
            await session.commit()

            return {"album_id": album_id, "added_photo_ids": added, "photo_count": album.photo_count}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add photos to album: {str(e)}")


@router.delete("/{album_id}/photos/{photo_id}", status_code=204)
async def remove_photo_from_album(
    album_id: int,
    photo_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Remove a photo from an album. Does not delete the photo itself."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            album = await _get_owned_album(session, album_id, current_user)

            if not _can_modify_album(album, current_user):
                raise HTTPException(status_code=403, detail="No permission to modify this album")

            membership_query = select(AlbumPhoto).where(
                AlbumPhoto.album_id == album_id, AlbumPhoto.photo_id == photo_id
            )
            membership = (await session.execute(membership_query)).scalar_one_or_none()
            if not membership:
                raise HTTPException(status_code=404, detail="Photo is not in this album")

            await session.delete(membership)

            if album.cover_photo_id == photo_id:
                album.cover_photo_id = None

            album.photo_count = max((album.photo_count or 1) - 1, 0)
            album.updated_at = datetime.now(timezone.utc)
            await session.commit()
            return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove photo from album: {str(e)}")
