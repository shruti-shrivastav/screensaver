from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Response
from app.api.deps import require_auth
from app.services.capture import take_screenshot

router = APIRouter(tags=["capture"])


@router.get("/api/frame", dependencies=[Depends(require_auth)])
async def get_frame():
    """Capture the current screen and return as JPEG."""
    try:
        data = take_screenshot()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Capture failed: {exc}")
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store, no-cache"},
    )
