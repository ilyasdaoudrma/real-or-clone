"""Clerk session verification (networkless: RS256 JWT checked against the instance's public JWKS)."""
import base64
import os

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


_jwks = jwt.PyJWKClient(f"https://{frontend_api()}/.well-known/jwks.json", cache_keys=True) if PUBLISHABLE_KEY else None


def user_id(request: Request) -> str | None:
    """Clerk user id if a valid session token is sent, else None (anonymous use stays allowed)."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer ") or _jwks is None:
        return None
    token = header.split(" ", 1)[1]
    try:
        key = _jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], options={"require": ["exp", "sub"]}, leeway=10)
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid_session")
    return claims["sub"]


def require_user(request: Request) -> str:
    uid = user_id(request)
    if uid is None:
        raise HTTPException(401, "login_required")
    return uid
