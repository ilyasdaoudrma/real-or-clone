"""Clerk session verification (networkless: RS256 JWT checked against the instance's public JWKS)."""
import base64
import os
import threading
import time

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, Request

load_dotenv()
PUBLISHABLE_KEY = os.environ.get("CLERK_PUBLISHABLE_KEY", "").strip()


def frontend_api() -> str:
    """pk_test_<base64("xxx.clerk.accounts.dev$")> -> xxx.clerk.accounts.dev"""
    if not PUBLISHABLE_KEY:
        return ""
    b64 = PUBLISHABLE_KEY.split("_", 2)[2]
    return base64.b64decode(b64 + "=" * (-len(b64) % 4)).decode().rstrip("$")


JWKS_URL = f"https://{frontend_api()}/.well-known/jwks.json" if PUBLISHABLE_KEY else ""
REFRESH_EVERY_S = 60
_keys: dict = {}
_fetched_at = 0.0
_lock = threading.Lock()


def _signing_key(kid: str | None):
    """Known key for this kid; unknown kids trigger at most one JWKS download per minute (no amplification)."""
    global _fetched_at
    with _lock:
        if kid not in _keys and time.time() - _fetched_at > REFRESH_EVERY_S:
            _fetched_at = time.time()
            try:
                _keys.update({k.key_id: k.key for k in jwt.PyJWKClient(JWKS_URL, timeout=5).get_jwk_set().keys})
            except jwt.PyJWKClientError:
                pass
        return _keys.get(kid)


def user_id(request: Request) -> str | None:
    """Clerk user id if a valid session token is sent, else None (anonymous use stays allowed)."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer ") or not JWKS_URL:
        return None
    token = header.split(" ", 1)[1][:4096]
    try:
        key = _signing_key(jwt.get_unverified_header(token).get("kid"))
        if key is None:
            raise jwt.InvalidTokenError("unknown kid")
        claims = jwt.decode(token, key, algorithms=["RS256"], options={"require": ["exp", "sub"]}, leeway=10)
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid_session")
    return claims["sub"]


def require_user(request: Request) -> str:
    uid = user_id(request)
    if uid is None:
        raise HTTPException(401, "login_required")
    return uid
