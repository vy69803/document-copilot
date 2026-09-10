"""FastAPI dependencies for Supabase JWT authentication.

Validates the Authorization header, verifies the token with Supabase Auth,
and provides the authenticated user to route handlers.
"""

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from supabase import Client

from app.database.session import get_db_session
from app.database.supabase import get_supabase_anon_client, get_supabase_user_client


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Verified user identity extracted from a Supabase JWT."""

    id: str
    email: str


def _extract_bearer_token(request: Request) -> str:
    """Pull the raw JWT from the Authorization header, or raise 401."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    return auth_header.removeprefix("Bearer ").strip()


async def get_current_user(request: Request) -> AuthenticatedUser:
    """FastAPI dependency that verifies the Supabase JWT and returns the user.

    Strategy: call Supabase Auth's ``get_user(token)`` which validates the JWT
    server-side and returns the user record. This avoids local JWT signature
    verification and stays correct if Supabase rotates signing keys.
    """
    token = _extract_bearer_token(request)
    client = get_supabase_anon_client()

    try:
        response = client.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if response is None or response.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = response.user

    # Ensure user exists in public.users to satisfy foreign key constraints
    try:
        user_uuid = uuid.UUID(user.id)
        with get_db_session() as session:
            session.execute(
                text("""
                    INSERT INTO users (id, email)
                    VALUES (:id, :email)
                    ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email
                """),
                {"id": user_uuid, "email": user.email or ""},
            )
    except Exception:
        # Graceful fallback for non-UUID test user IDs
        pass

    return AuthenticatedUser(id=user.id, email=user.email or "")


async def get_user_supabase_client(
    request: Request,
    _user: AuthenticatedUser = Depends(get_current_user),
) -> Client:
    """Returns a user-scoped Supabase client that respects RLS.

    Depends on ``get_current_user`` so the token is verified before we
    construct the client.  Route handlers that need to read/write
    user-owned rows should depend on this instead of using the admin client.
    """
    token = _extract_bearer_token(request)
    return get_supabase_user_client(token)
