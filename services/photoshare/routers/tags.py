"""
Photo Tags API
===============

Add/remove/list tags on a photo, plus tag-based search across photos.
Backed by the `PhotoTag` model in app_database.py.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, or_

from app_database import get_app_db_manager, Photo, PhotoTag
from auth_integration import get_current_user, AuthenticatedUser

router = APIRouter(tags=["tags"])


class TagsAdd(BaseModel):
    tags: List[str] = Field(..., min_length=1, max_length=50)

    @field_validator("tags")
    @classmethod
    def normalize(cls, values: List[str]) -> List[str]:
        cleaned = {v.strip().lower() for v in values if v.strip()}
        if not cleaned:
            raise ValueError("at least one non-empty tag is required")
        for tag in cleaned:
            if len(tag) > 50:
                raise ValueError(f"tag too long (max 50 chars): {tag}")
        return sorted(cleaned)


async def _get_visible_photo(session, photo_id: int, current_user: AuthenticatedUser) -> Photo:
    photo = (await session.execute(select(Photo).where(Photo.id == photo_id))).scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    if not current_user.can_access_photo(photo.user_uuid, photo.is_public):
        raise HTTPException(status_code=403, detail="No permission to view this photo")
    return photo


@router.post("/api/photos/{photo_id}/tags", status_code=201)
async def add_tags(
    photo_id: int,
    payload: TagsAdd,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Add one or more tags to a photo. Owner or admin only. Duplicate tags are ignored."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            photo = await _get_visible_photo(session, photo_id, current_user)

            if not current_user.can_modify_photo(photo.user_uuid):
                raise HTTPException(status_code=403, detail="No permission to tag this photo")

            existing_query = select(PhotoTag.tag).where(PhotoTag.photo_id == photo_id)
            existing = {row[0] for row in (await session.execute(existing_query)).all()}

            added = []
            for tag in payload.tags:
                if tag in existing:
                    continue
                session.add(PhotoTag(photo_id=photo_id, tag=tag, tag_type="user"))
                added.append(tag)

            await session.commit()
            return {"photo_id": photo_id, "added_tags": added, "skipped_duplicates": sorted(set(payload.tags) - set(added))}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add tags: {str(e)}")


@router.get("/api/photos/{photo_id}/tags")
async def list_tags(
    photo_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List all tags on a photo."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            await _get_visible_photo(session, photo_id, current_user)

            tags_query = select(PhotoTag).where(PhotoTag.photo_id == photo_id).order_by(PhotoTag.tag.asc())
            tags = (await session.execute(tags_query)).scalars().all()
            return {"photo_id": photo_id, "tags": [t.to_dict() for t in tags]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tags: {str(e)}")


@router.delete("/api/photos/{photo_id}/tags/{tag}", status_code=204)
async def remove_tag(
    photo_id: int,
    tag: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Remove a tag from a photo. Owner or admin only."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            photo = await _get_visible_photo(session, photo_id, current_user)

            if not current_user.can_modify_photo(photo.user_uuid):
                raise HTTPException(status_code=403, detail="No permission to modify tags on this photo")

            tag_row = (
                await session.execute(
                    select(PhotoTag).where(PhotoTag.photo_id == photo_id, PhotoTag.tag == tag.strip().lower())
                )
            ).scalar_one_or_none()
            if not tag_row:
                raise HTTPException(status_code=404, detail="Tag not found on this photo")

            await session.delete(tag_row)
            await session.commit()
            return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove tag: {str(e)}")


@router.get("/api/tags/search")
async def search_by_tag(
    q: str = Query(..., min_length=1, max_length=50),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Search photos by tag. Returns the current user's own matches plus public matches."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            search_term = q.strip().lower()

            matches_query = (
                select(Photo)
                .join(PhotoTag, PhotoTag.photo_id == Photo.id)
                .where(
                    PhotoTag.tag == search_term,
                    or_(Photo.user_uuid == current_user.uuid, Photo.is_public == True),  # noqa: E712
                )
                .order_by(Photo.created_at.desc())
                .distinct()
            )

            all_matches = (await session.execute(matches_query)).scalars().all()
            total = len(all_matches)
            offset = (page - 1) * per_page
            page_slice = all_matches[offset: offset + per_page]

            return {
                "tag": search_term,
                "photos": [p.to_dict() for p in page_slice],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search by tag: {str(e)}")
