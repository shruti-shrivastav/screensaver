from __future__ import annotations
from fastapi import Depends, HTTPException, Request, status
from app.core.security import decode_token, get_username_from_request


def require_auth(request: Request) -> str:
    """FastAPI dependency — returns username or raises 401."""
    username = get_username_from_request(request)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return username
