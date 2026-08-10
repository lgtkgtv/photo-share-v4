"""
Photo Analytics API
=====================

Records view/download/share/like events and surfaces basic aggregates.
Backed by the `PhotoAnalytics` model in app_database.py, which existed but
had no writer or reader before this.

Note: `Media`/`Photo` already carry running counters (view_count,
download_count, like_count) that other endpoints increment directly. This
router additionally logs each event as its own row for time-series/referrer
analysis, and reads both sources back out.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func

from app_database import get_app_db_manager, Photo, PhotoAnalytics
from auth_integration import get_current_user, get_optional_user, AuthenticatedUser

router = APIRouter(tags=["analytics"])

VALID_EVENT_TYPES = {"view", "download", "share", "like"}


class AnalyticsEventCreate(BaseModel):
    event_type: str = Field(..., description="one of: view, download, share, like")


@router.post("/api/photos/{photo_id}/analytics/event", status_code=201)
async def record_event(
    photo_id: int,
    payload: AnalyticsEventCreate,
    request: Request,
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
):
    """
    Record an analytics event for a photo. Works for both authenticated and
    anonymous viewers (anonymous events are logged by IP only), matching how
    public photo views already work elsewhere in this service.
    """
    if payload.event_type not in VALID_EVENT_TYPES:
        raise HTTPException(status_code=400, detail=f"event_type must be one of {sorted(VALID_EVENT_TYPES)}")

    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            photo = (await session.execute(select(Photo).where(Photo.id == photo_id))).scalar_one_or_none()
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")

            if current_user is None and not photo.is_public:
                raise HTTPException(status_code=403, detail="No permission to view this photo")
            if current_user is not None and not current_user.can_access_photo(photo.user_uuid, photo.is_public):
                raise HTTPException(status_code=403, detail="No permission to view this photo")

            event = PhotoAnalytics(
                photo_id=photo_id,
                event_type=payload.event_type,
                viewer_uuid=current_user.uuid if current_user else None,
                viewer_ip=request.client.host if request.client else None,
                referrer=request.headers.get("referer"),
                user_agent=request.headers.get("user-agent"),
            )
            session.add(event)

            if payload.event_type == "view":
                photo.view_count = (photo.view_count or 0) + 1
            elif payload.event_type == "download":
                photo.download_count = (photo.download_count or 0) + 1
            elif payload.event_type == "like":
                photo.like_count = (photo.like_count or 0) + 1

            await session.commit()
            return event.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record analytics event: {str(e)}")


@router.get("/api/photos/{photo_id}/analytics")
async def get_photo_analytics(
    photo_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Analytics summary for one photo. Owner or admin only."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            photo = (await session.execute(select(Photo).where(Photo.id == photo_id))).scalar_one_or_none()
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")

            if not current_user.can_modify_photo(photo.user_uuid):
                raise HTTPException(status_code=403, detail="No permission to view analytics for this photo")

            counts_query = (
                select(PhotoAnalytics.event_type, func.count())
                .where(PhotoAnalytics.photo_id == photo_id)
                .group_by(PhotoAnalytics.event_type)
            )
            counts = dict((await session.execute(counts_query)).all())

            return {
                "photo_id": photo_id,
                "view_count": photo.view_count,
                "download_count": photo.download_count,
                "like_count": photo.like_count,
                "event_counts": {event_type: counts.get(event_type, 0) for event_type in VALID_EVENT_TYPES},
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@router.get("/api/analytics/summary")
async def get_account_analytics_summary(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Aggregate analytics across all of the current user's photos."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            totals_query = select(
                func.coalesce(func.sum(Photo.view_count), 0),
                func.coalesce(func.sum(Photo.download_count), 0),
                func.coalesce(func.sum(Photo.like_count), 0),
                func.count(),
            ).where(Photo.user_uuid == current_user.uuid)
            total_views, total_downloads, total_likes, photo_count = (
                await session.execute(totals_query)
            ).one()

            top_photos_query = (
                select(Photo)
                .where(Photo.user_uuid == current_user.uuid)
                .order_by(Photo.view_count.desc())
                .limit(5)
            )
            top_photos = (await session.execute(top_photos_query)).scalars().all()

            return {
                "photo_count": photo_count,
                "total_views": total_views,
                "total_downloads": total_downloads,
                "total_likes": total_likes,
                "top_photos": [p.to_dict() for p in top_photos],
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics summary: {str(e)}")
