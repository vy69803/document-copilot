from functools import lru_cache

from supabase import Client, ClientOptions, create_client

from app.config import settings


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """Returns a cached Supabase client with service-role privileges.

    Used by the backend for privileged database operations and ingestion writes
    that bypass Row Level Security (RLS). Never expose this client to the frontend.
    """
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_role_key,
    )


@lru_cache(maxsize=1)
def get_supabase_anon_client() -> Client:
    """Returns a cached Supabase client initialized with the anonymous public key."""
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_anon_key,
    )


def get_supabase_user_client(access_token: str) -> Client:
    """Creates a user-scoped Supabase client that respects Row Level Security (RLS).

    Args:
        access_token: The Supabase JWT token received from the user's Authorization header.

    Returns:
        A Client configured with the user's bearer token header.
    """
    options = ClientOptions(headers={"Authorization": f"Bearer {access_token}"})
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_anon_key,
        options=options,
    )
