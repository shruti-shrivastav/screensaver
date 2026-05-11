from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    load_users,
    login_limiter,
    verify_password,
)
from app.core.config import settings
from app.api.deps import require_auth

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_OPTS = dict(
    httponly=True,
    secure=False,   # set True behind HTTPS/tunnel
    samesite="strict",
    path="/",
)


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response):
    ip = request.client.host  # type: ignore

    if not login_limiter.is_allowed(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts — please wait before retrying.",
        )

    users = load_users()
    stored_hash = users.get(body.username)

    if not stored_hash or not verify_password(body.password, stored_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Successful login — reset rate limiter for this IP
    login_limiter.reset(ip)

    access  = create_access_token(body.username)
    refresh = create_refresh_token(body.username)

    response.set_cookie("access_token",  access,  max_age=settings.ACCESS_TOKEN_TTL,  **_COOKIE_OPTS)
    response.set_cookie("refresh_token", refresh, max_age=settings.REFRESH_TOKEN_TTL, **_COOKIE_OPTS)
    return {"ok": True, "username": body.username}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token",  path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    payload = decode_token(token, expected_type="refresh")
    username = payload.get("sub", "")

    new_access = create_access_token(username)
    response.set_cookie("access_token", new_access, max_age=settings.ACCESS_TOKEN_TTL, **_COOKIE_OPTS)
    return {"ok": True}


@router.get("/me", dependencies=[Depends(require_auth)])
async def me(request: Request):
    from app.core.security import get_username_from_request
    return {"username": get_username_from_request(request)}
