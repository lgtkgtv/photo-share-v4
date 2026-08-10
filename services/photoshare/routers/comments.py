"""
Photo Comments API
===================

Basic CRUD for comments on a photo. Backed by the `PhotoComment` model in
app_database.py.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func

from app_database import get_app_db_manager, Photo, PhotoComment
from auth_integration import get_current_user, AuthenticatedUser

router = APIRouter(tags=["comments"])


class CommentCreate(BaseModel):
    comment: str = Field(..., min_length=1, max_length=2000)


async def _get_visible_photo(session, photo_id: int, current_user: AuthenticatedUser) -> Photo:
    photo = (await session.execute(select(Photo).where(Photo.id == photo_id))).scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    if not current_user.can_access_photo(photo.user_uuid, photo.is_public):
        raise HTTPException(status_code=403, detail="No permission to view this photo")
    return photo


@router.post("/api/photos/{photo_id}/comments", status_code=201)
async def create_comment(
    photo_id: int,
    payload: CommentCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Add a comment to a photo. Requires read access to the photo."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            await _get_visible_photo(session, photo_id, current_user)

            commenter_name = current_user.display_name or " ".join(
                filter(None, [current_user.first_name, current_user.last_name])
            ) or None

            comment = PhotoComment(
                photo_id=photo_id,
                commenter_uuid=current_user.uuid,
                commenter_email=current_user.email,
                commenter_name=commenter_name,
                comment=payload.comment,
            )
            session.add(comment)
            await session.commit()
            await session.refresh(comment)
            return comment.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")


@router.get("/api/photos/{photo_id}/comments")
async def list_comments(
    photo_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List comments on a photo. Non-owners see only approved, non-flagged comments."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            photo = await _get_visible_photo(session, photo_id, current_user)

            is_moderator = current_user.uuid == photo.user_uuid or current_user.is_admin()

            base_filter = [PhotoComment.photo_id == photo_id]
            if not is_moderator:
                base_filter += [PhotoComment.is_approved == True, PhotoComment.is_flagged == False]  # noqa: E712

            count_query = select(func.count()).select_from(PhotoComment).where(*base_filter)
            total = (await session.execute(count_query)).scalar_one()

            offset = (page - 1) * per_page
            comments_query = (
                select(PhotoComment)
                .where(*base_filter)
                .order_by(PhotoComment.created_at.asc())
                .offset(offset)
                .limit(per_page)
            )
            comments = (await session.execute(comments_query)).scalars().all()

            return {
                "comments": [c.to_dict() for c in comments],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list comments: {str(e)}")


@router.delete("/api/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a comment. Allowed for the comment's author, the photo's owner, or an admin."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            comment = (
                await session.execute(select(PhotoComment).where(PhotoComment.id == comment_id))
            ).scalar_one_or_none()
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")

            photo = (await session.execute(select(Photo).where(Photo.id == comment.photo_id))).scalar_one_or_none()
            photo_owner_uuid = photo.user_uuid if photo else None

            can_delete = (
                comment.commenter_uuid == current_user.uuid
                or photo_owner_uuid == current_user.uuid
                or current_user.is_admin()
            )
            if not can_delete:
                raise HTTPException(status_code=403, detail="No permission to delete this comment")

            await session.delete(comment)
            await session.commit()
            return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete comment: {str(e)}")
