"""Unit tests for chat thread authorization and user ownership checks."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.database import chats
from app.main import app

client = TestClient(app)

USER_A = AuthenticatedUser(id="user-aaa-111", email="alice@driftwood.com")
USER_B = AuthenticatedUser(id="user-bbb-222", email="bob@driftwood.com")


# ─── Database-layer ownership tests ──────────────────────────────────────────


def test_chats_get_thread_ownership():
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_eq_id = MagicMock()
    mock_select.eq.return_value = mock_eq_id
    mock_eq_user = MagicMock()
    mock_eq_id.eq.return_value = mock_eq_user
    mock_single = MagicMock()
    mock_eq_user.maybe_single.return_value = mock_single

    # Simulating thread found for owner
    mock_single.execute.return_value.data = {
        "id": "thread-1",
        "user_id": "user-aaa-111",
        "title": "Apple Analysis",
    }

    with patch("app.database.chats.get_supabase_admin_client", return_value=mock_sb):
        res = chats.get_thread("thread-1", "user-aaa-111")
        assert res is not None
        assert res["id"] == "thread-1"
        assert res["user_id"] == "user-aaa-111"

        # Verify query scoped to both thread id and user_id
        mock_select.eq.assert_called_with("id", "thread-1")
        mock_eq_id.eq.assert_called_with("user_id", "user-aaa-111")


def test_chats_get_thread_messages_ownership_enforcement():
    # If get_thread returns None (user does not own the thread), get_thread_messages returns empty list
    with patch("app.database.chats.get_thread", return_value=None):
        messages = chats.get_thread_messages("thread-999", "user-unauthorized")
        assert messages == []


# ─── API endpoint authorization tests ─────────────────────────────────────────


def test_unauthenticated_requests_fail():
    # Attempting to access threads without an Authorization header
    response = client.get("/chat/threads")
    assert response.status_code == 401

    response = client.post("/chat/threads", json={"title": "Test"})
    assert response.status_code == 401

    response = client.get("/chat/threads/thread-1/messages")
    assert response.status_code == 401

    response = client.post("/chat/stream", json={"thread_id": "thread-1", "message": "hello"})
    assert response.status_code == 401


def test_get_thread_messages_owned_by_user():
    app.dependency_overrides[get_current_user] = lambda: USER_A

    try:
        with (
            patch("app.database.chats.get_thread") as mock_get_thread,
            patch("app.database.chats.get_thread_messages") as mock_get_messages,
        ):
            mock_get_thread.return_value = {
                "id": "thread-1",
                "user_id": USER_A.id,
                "title": "Alice Thread",
            }
            mock_get_messages.return_value = [
                {
                    "id": "msg-1",
                    "thread_id": "thread-1",
                    "role": "user",
                    "content": "What is revenue?",
                    "created_at": "2026-09-08T12:00:00Z",
                }
            ]

            response = client.get("/chat/threads/thread-1/messages")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "msg-1"
            assert data[0]["content"] == "What is revenue?"
            mock_get_thread.assert_called_once_with("thread-1", USER_A.id)
            mock_get_messages.assert_called_once_with("thread-1", USER_A.id)
    finally:
        app.dependency_overrides.clear()


def test_get_thread_messages_forbidden_for_other_user():
    # User B attempts to access a thread owned by User A (get_thread returns None)
    app.dependency_overrides[get_current_user] = lambda: USER_B

    try:
        with patch("app.database.chats.get_thread", return_value=None):
            response = client.get("/chat/threads/thread-alice-private/messages")
            assert response.status_code == 404
            assert response.json()["detail"] == "Thread not found"
    finally:
        app.dependency_overrides.clear()


def test_create_thread_scoped_to_current_user():
    app.dependency_overrides[get_current_user] = lambda: USER_A

    try:
        with patch("app.database.chats.create_thread") as mock_create:
            mock_create.return_value = {
                "id": "thread-new",
                "user_id": USER_A.id,
                "title": "New Research",
                "created_at": "2026-09-08T12:00:00Z",
                "updated_at": "2026-09-08T12:00:00Z",
            }

            response = client.post("/chat/threads", json={"title": "New Research"})
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "thread-new"
            assert data["title"] == "New Research"
            mock_create.assert_called_once_with(USER_A.id, "New Research")
    finally:
        app.dependency_overrides.clear()


def test_list_threads_scoped_to_current_user():
    app.dependency_overrides[get_current_user] = lambda: USER_B

    try:
        with patch("app.database.chats.list_threads") as mock_list:
            mock_list.return_value = [
                {
                    "id": "thread-b-1",
                    "title": "Bob's Research",
                    "created_at": "2026-09-08T12:00:00Z",
                    "updated_at": "2026-09-08T12:00:00Z",
                }
            ]

            response = client.get("/chat/threads")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "thread-b-1"
            mock_list.assert_called_once_with(USER_B.id)
    finally:
        app.dependency_overrides.clear()


def test_delete_thread_success():
    app.dependency_overrides[get_current_user] = lambda: USER_A

    try:
        with patch("app.database.chats.delete_thread", return_value=True) as mock_delete:
            response = client.delete("/chat/threads/thread-alice-1")
            assert response.status_code == 204
            mock_delete.assert_called_once_with("thread-alice-1", USER_A.id)
    finally:
        app.dependency_overrides.clear()


def test_delete_thread_not_found_or_unauthorized():
    app.dependency_overrides[get_current_user] = lambda: USER_B

    try:
        with patch("app.database.chats.delete_thread", return_value=False) as mock_delete:
            response = client.delete("/chat/threads/thread-alice-private")
            assert response.status_code == 404
            assert response.json()["detail"] == "Thread not found"
            mock_delete.assert_called_once_with("thread-alice-private", USER_B.id)
    finally:
        app.dependency_overrides.clear()


def test_chats_delete_thread_ownership():
    # When get_thread returns None (user does not own the thread), delete_thread returns False
    with patch("app.database.chats.get_thread", return_value=None):
        deleted = chats.delete_thread("thread-other", "user-unauthorized")
        assert deleted is False
