from __future__ import annotations
import collections
import json
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import HTTPException, Request, status

from app.core.config import settings
import logging

logger = logging.getLogger("screensaver")


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------

def load_users() -> dict[str, str]:
    path = settings.htpasswd_path
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as exc:
        logger.error(f"Failed to read users from {path}: {exc}")
        return {}


def save_users(users: dict[str, str]) -> None:
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    path = settings.htpasswd_path
    with open(path, "w") as f:
        json.dump(users, f, indent=2)
    os.chmod(path, 0o600)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"
_ACCESS_TYPE = "access"
_REFRESH_TYPE = "refresh"


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.ACCESS_TOKEN_TTL)
    return jwt.encode(
        {"sub": username, "exp": expire, "type": _ACCESS_TYPE},
        settings.JWT_SECRET,
        algorithm=_ALGORITHM,
    )


def create_refresh_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.REFRESH_TOKEN_TTL)
    return jwt.encode(
        {"sub": username, "exp": expire, "type": _REFRESH_TYPE},
        settings.JWT_SECRET,
        algorithm=_ALGORITHM,
    )


def decode_token(token: str, expected_type: str = _ACCESS_TYPE) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
        if payload.get("type") != expected_type:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_username_from_request(request: Request) -> Optional[str]:
    """Extract username from access token cookie. Returns None if missing/invalid."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_token(token, _ACCESS_TYPE)
        return payload.get("sub")
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Sliding-window rate limiter with exponential backoff tracking."""

    def __init__(self, max_attempts: int = 5, window: int = 60):
        self._attempts: dict[str, collections.deque] = collections.defaultdict(collections.deque)
        self._backoff_until: dict[str, float] = {}
        self._lock = threading.Lock()
        self._max = max_attempts
        self._window = window

    def is_allowed(self, ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            # Check backoff
            if self._backoff_until.get(ip, 0) > now:
                return False

            dq = self._attempts[ip]
            # Evict old entries
            while dq and now - dq[0] > self._window:
                dq.popleft()

            if len(dq) >= self._max:
                # Exponential backoff: 2^(failures/5) capped at 10 min
                failures = len(dq)
                backoff = min(2 ** (failures // 5), 600)
                self._backoff_until[ip] = now + backoff
                return False

            dq.append(now)
            return True

    def reset(self, ip: str) -> None:
        with self._lock:
            self._attempts.pop(ip, None)
            self._backoff_until.pop(ip, None)


# Global rate limiter instance
login_limiter = RateLimiter(max_attempts=5, window=60)
