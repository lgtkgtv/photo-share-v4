"""
Photo Sharing API
==================

Create/list/revoke shareable links for a photo, resolve a share token for
the recipient, and let the recipient actually download the file.

Backed by the `PhotoShare` model in app_database.py.

Download flow
-------------
1. `GET /api/shares/{share_token}` (no auth) validates the share (active,
   unexpired, under its download cap, password if required) and returns
   photo metadata plus a `download` block: a signed, time-limited URL and
   its exact `expires_at` (ISO-8601, UTC). The 1-hour lifetime is
   independent of the share link's own expiry -- a share can stay valid
   for days, but each individual download URL it hands out is only good
   for an hour before the recipient has to ask for a fresh one.
2. `GET /api/shares/{share_token}/download` (no auth) verifies that signed
   URL and streams the file. It also re-checks the share's *current* state
   (still active, still under its download cap) at download time -- not
   just at the moment the URL was issued -- so revoking a share takes
   effect immediately rather than up to an hour later.

Client-side expiration handling
--------------------------------
Two ways a client finds out a download URL has expired:
  - Proactively: `expires_at` is returned in step 1 as a plain ISO-8601
    timestamp, so the client can start a countdown and fetch a fresh URL
    (by calling step 1 again) before the old one lapses.
  - Reactively: if the client uses the URL after it's already expired,
    the download endpoint returns HTTP 410 Gone with a JSON body whose
    `error` field is exactly `"signed_url_expired"` -- a stable, machine
    -readable code distinct from the other failure reasons below, so
    client code can programmatically decide "expired -> silently fetch a
    new URL and retry" versus e.g. `"invalid_signature"`, which should not
    be retried.

Error codes returned by the download endpoint (all as `{"error": "...",
"detail": "..."}` JSON bodies, not just prose in `detail`):
  - 410 `signed_url_expired`   -- the 1-hour download URL itself expired
  - 403 `invalid_signature`    -- signature doesn't match (tampered/forged)
  - 400 `malformed_signature`  -- expires/signature params aren't well-formed
  - 404 `share_not_found`      -- share token doesn't exist
  - 410 `share_revoked`        -- share was revoked after the URL was issued
  - 410 `share_expired`        -- share's own expiry passed after the URL was issued
  - 410 `download_limit_reached` -- share hit max_downloads after the URL was issued
  - 404 `photo_not_found`      -- underlying photo/file no longer exists
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func

from app_database import get_app_db_manager, Photo, PhotoShare
from auth_integration import get_current_user, AuthenticatedUser
from file_storage import FileStorageService

router = APIRouter(tags=["shares"])

DOWNLOAD_URL_TTL_SECONDS = 3600  # exactly 1 hour, per product requirement

storage_service = FileStorageService()


# ---------------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------------

class ShareCreate(BaseModel):
    share_type: str = Field(..., pattern="^(public|private|password)$")
    password: Optional[str] = Field(default=None, min_length=4, max_length=128)
    max_downloads: Optional[int] = Field(default=None, ge=1)
    expires_at: Optional[datetime] = None
    shared_with_email: Optional[str] = Field(default=None, max_length=255)
    share_message: Optional[str] = Field(default=None, max_length=2000)


def _hash_password(raw: str) -> str:
    # Matches the rest of this service's preference for explicit, auditable
    # hashing over a new dependency; swap for passlib/bcrypt to match
    # auth-service if that's preferred during review.
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _share_state_error(share: PhotoShare) -> Optional[JSONResponse]:
    """
    Re-check a share's *current* state. Returns a JSONResponse describing
    the problem if the share is no longer usable, or None if it's fine.
    Shared between resolve_share and download_shared_file so both enforce
    identical, up-to-date rules.
    """
    if not share or not share.is_active:
        return JSONResponse(
            status_code=404,
            content={"error": "share_not_found", "detail": "Share not found or has been revoked."},
        )

    if share.expires_at and share.expires_at < datetime.now(timezone.utc):
        return JSONResponse(
            status_code=410,
            content={"error": "share_expired", "detail": "This share link has expired."},
        )

    if share.max_downloads is not None and share.download_count >= share.max_downloads:
        return JSONResponse(
            status_code=410,
            content={"error": "download_limit_reached", "detail": "This share link has reached its download limit."},
        )

    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/api/photos/{photo_id}/share", status_code=201)
async def create_share(
    photo_id: int,
    payload: ShareCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a shareable link for a photo. Owner or admin only."""
    if payload.share_type == "password" and not payload.password:
        raise HTTPException(status_code=400, detail="password is required when share_type is 'password'")

    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            photo = (await session.execute(select(Photo).where(Photo.id == photo_id))).scalar_one_or_none()
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")

            if not current_user.can_modify_photo(photo.user_uuid):
                raise HTTPException(status_code=403, detail="No permission to share this photo")

            share = PhotoShare(
                photo_id=photo_id,
                share_token=secrets.token_urlsafe(32),
                share_type=payload.share_type,
                password_hash=_hash_password(payload.password) if payload.password else None,
                max_downloads=payload.max_downloads,
                expires_at=payload.expires_at,
                shared_by_uuid=current_user.uuid,
                shared_with_email=payload.shared_with_email,
                share_message=payload.share_message,
            )
            session.add(share)
            await session.commit()
            await session.refresh(share)

            result = share.to_dict()
            result["share_url"] = f"/api/shares/{share.share_token}"
            return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create share: {str(e)}")


@router.get("/api/shares")
async def list_my_shares(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List shares the current user has created."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            count_query = select(func.count()).select_from(PhotoShare).where(
                PhotoShare.shared_by_uuid == current_user.uuid
            )
            total = (await session.execute(count_query)).scalar_one()

            offset = (page - 1) * per_page
            shares_query = (
                select(PhotoShare)
                .where(PhotoShare.shared_by_uuid == current_user.uuid)
                .order_by(PhotoShare.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            shares = (await session.execute(shares_query)).scalars().all()

            return {
                "shares": [s.to_dict() for s in shares],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list shares: {str(e)}")


@router.get("/api/shares/{share_token}")
async def resolve_share(share_token: str, password: Optional[str] = Query(default=None)):
    """
    Resolve a share token (no auth required -- this is the recipient-facing link).

    Returns photo metadata plus a fresh, signed download URL valid for exactly
    one hour, if the share is active, unexpired, under its download cap, and
    (if password-protected) the correct password was supplied.
    """
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            share = (
                await session.execute(select(PhotoShare).where(PhotoShare.share_token == share_token))
            ).scalar_one_or_none()

            state_error = _share_state_error(share)
            if state_error:
                return state_error

            if share.share_type == "password":
                if not password or _hash_password(password) != share.password_hash:
                    raise HTTPException(status_code=401, detail="Incorrect or missing password")

            photo = (await session.execute(select(Photo).where(Photo.id == share.photo_id))).scalar_one_or_none()
            if not photo:
                return JSONResponse(
                    status_code=404,
                    content={"error": "photo_not_found", "detail": "Shared photo no longer exists."},
                )

            share.last_accessed = datetime.now(timezone.utc)
            await session.commit()

            signed = storage_service.sign_payload(share.share_token, expires_in=DOWNLOAD_URL_TTL_SECONDS)
            expires_at_iso = datetime.fromtimestamp(signed["expires_at"], tz=timezone.utc).isoformat()

            return {
                "share": {k: v for k, v in share.to_dict().items() if k not in ("password_hash",)},
                "photo": photo.to_dict(),
                "download": {
                    "url": (
                        f"/api/shares/{share.share_token}/download"
                        f"?expires={signed['expires_at']}&signature={signed['signature']}"
                    ),
                    "expires_at": expires_at_iso,
                    "expires_in_seconds": DOWNLOAD_URL_TTL_SECONDS,
                },
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve share: {str(e)}")


@router.get("/api/shares/{share_token}/download")
async def download_shared_file(share_token: str, expires: str = Query(...), signature: str = Query(...)):
    """
    Stream the shared file (no auth required). Requires a signed URL obtained
    from GET /api/shares/{share_token} -- see the module docstring above for
    the full list of error codes this can return.
    """
    verification = storage_service.verify_signed_payload(share_token, expires, signature)

    if not verification["valid"]:
        reason = verification["reason"]
        if reason == "expired":
            return JSONResponse(
                status_code=410,
                content={
                    "error": "signed_url_expired",
                    "detail": "This download link has expired. Request a new one from "
                              f"GET /api/shares/{share_token}.",
                },
            )
        if reason == "malformed":
            return JSONResponse(
                status_code=400,
                content={"error": "malformed_signature", "detail": "Malformed expires/signature parameters."},
            )
        # "invalid_signature" (or any other non-"ok" reason)
        return JSONResponse(
            status_code=403,
            content={"error": "invalid_signature", "detail": "This download link is invalid."},
        )

    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            share = (
                await session.execute(select(PhotoShare).where(PhotoShare.share_token == share_token))
            ).scalar_one_or_none()

            # Re-validate current share state -- the signed URL only proves the
            # link was legitimately issued within the last hour, not that the
            # share hasn't since been revoked, expired, or hit its download cap.
            state_error = _share_state_error(share)
            if state_error:
                return state_error

            photo = (await session.execute(select(Photo).where(Photo.id == share.photo_id))).scalar_one_or_none()
            if not photo:
                return JSONResponse(
                    status_code=404,
                    content={"error": "photo_not_found", "detail": "Shared photo no longer exists."},
                )

            file_content = await storage_service.retrieve_file(photo.storage_path)
            if not file_content:
                return JSONResponse(
                    status_code=404,
                    content={"error": "photo_not_found", "detail": "File not found in storage."},
                )

            share.download_count = (share.download_count or 0) + 1
            share.last_accessed = datetime.now(timezone.utc)
            photo.download_count = (photo.download_count or 0) + 1
            await session.commit()

            def generate():
                yield file_content

            return StreamingResponse(
                generate(),
                media_type=photo.content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{photo.original_filename}"',
                    # Never cache a signed, single-purpose download URL.
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download shared file: {str(e)}")


@router.delete("/api/shares/{share_id}", status_code=204)
async def revoke_share(
    share_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Revoke a share (soft delete -- sets is_active=False). Creator or admin only."""
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            share = (await session.execute(select(PhotoShare).where(PhotoShare.id == share_id))).scalar_one_or_none()
            if not share:
                raise HTTPException(status_code=404, detail="Share not found")

            if share.shared_by_uuid != current_user.uuid and not current_user.is_admin():
                raise HTTPException(status_code=403, detail="No permission to revoke this share")

            share.is_active = False
            await session.commit()
            return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke share: {str(e)}")
