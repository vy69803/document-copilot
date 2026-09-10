"""Unit tests for Supabase JWT token extraction and authentication dependencies."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.auth.dependencies import (
    AuthenticatedUser,
    _extract_bearer_token,
    get_current_user,
    get_user_supabase_client,
)


def _build_request(headers: dict[str, str] | None = None) -> Request:
    """Helper to build a mock Starlette Request with given headers."""
    scope = {
        "type": "http",
        "headers": [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in (headers or {}).items()
        ],
    }
    return Request(scope)


def test_extract_bearer_token_missing_header():
    request = _build_request()
    with pytest.raises(HTTPException) as exc_info:
        _extract_bearer_token(request)
    assert exc_info.value.status_code == 401
    assert "Missing or malformed Authorization header" in exc_info.value.detail


def test_extract_bearer_token_malformed_header():
    request = _build_request({"Authorization": "Basic dXNlcjpwYXNz"})
    with pytest.raises(HTTPException) as exc_info:
        _extract_bearer_token(request)
    assert exc_info.value.status_code == 401
    assert "Missing or malformed Authorization header" in exc_info.value.detail


def test_extract_bearer_token_valid():
    request = _build_request({"Authorization": "Bearer test-jwt-token-123"})
    token = _extract_bearer_token(request)
    assert token == "test-jwt-token-123"


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    request = _build_request({"Authorization": "Bearer valid-user-token"})

    mock_user = MagicMock()
    mock_user.id = "user-abc-123"
    mock_user.email = "analyst@driftwood.com"

    mock_response = MagicMock()
    mock_response.user = mock_user

    mock_client = MagicMock()
    mock_client.auth.get_user.return_value = mock_response

    with patch("app.auth.dependencies.get_supabase_anon_client", return_value=mock_client):
        user = await get_current_user(request)

        assert isinstance(user, AuthenticatedUser)
        assert user.id == "user-abc-123"
        assert user.email == "analyst@driftwood.com"
        mock_client.auth.get_user.assert_called_once_with("valid-user-token")


@pytest.mark.asyncio
async def test_get_current_user_expired_or_invalid_token():
    request = _build_request({"Authorization": "Bearer expired-token"})

    mock_client = MagicMock()
    mock_client.auth.get_user.side_effect = Exception("JWT expired")

    with patch("app.auth.dependencies.get_supabase_anon_client", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_null_user_response():
    request = _build_request({"Authorization": "Bearer null-user-token"})

    mock_response = MagicMock()
    mock_response.user = None

    mock_client = MagicMock()
    mock_client.auth.get_user.return_value = mock_response

    with patch("app.auth.dependencies.get_supabase_anon_client", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_user_supabase_client():
    request = _build_request({"Authorization": "Bearer scoped-token"})
    mock_user = AuthenticatedUser(id="user-1", email="user1@example.com")

    with patch("app.auth.dependencies.get_supabase_user_client") as mock_factory:
        mock_factory.return_value = MagicMock()
        client = await get_user_supabase_client(request, _user=mock_user)

        mock_factory.assert_called_once_with("scoped-token")
        assert client is not None
