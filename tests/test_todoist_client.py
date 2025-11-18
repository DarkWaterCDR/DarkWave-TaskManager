"""
Unit tests for Todoist client.

Tests API interactions, error handling, and retry logic using mocked responses.
"""

from unittest.mock import patch

import pytest
import requests
import responses
from app.todoist_client import (
    AuthenticationError,
    RateLimitError,
    TodoistClient,
    TodoistError,
    ValidationError,
)


@pytest.fixture
def todoist_client():
    """Fixture providing a TodoistClient instance."""
    return TodoistClient(api_token="test_token_12345")


class TestTodoistClient:
    """Test suite for TodoistClient."""

    @responses.activate
    def test_create_task_success(self, todoist_client):
        """Test successful task creation."""
        responses.add(
            responses.POST,
            "https://api.todoist.com/rest/v2/tasks",
            json={"id": "123", "content": "Test task", "priority": 3},
            status=200,
        )

        task_data = {"content": "Test task", "priority": 3}
        result = todoist_client.create_task(task_data)

        assert result["id"] == "123"
        assert result["content"] == "Test task"
        assert len(responses.calls) == 1
        assert (
            responses.calls[0].request.headers["Authorization"]
            == "Bearer test_token_12345"
        )

    @responses.activate
    def test_create_task_with_full_details(self, todoist_client):
        """Test task creation with all optional fields."""
        responses.add(
            responses.POST,
            "https://api.todoist.com/rest/v2/tasks",
            json={
                "id": "456",
                "content": "Complete task",
                "description": "Task details",
                "priority": 4,
                "due_string": "tomorrow",
                "labels": ["work", "urgent"],
            },
            status=200,
        )

        task_data = {
            "content": "Complete task",
            "description": "Task details",
            "priority": 4,
            "due_string": "tomorrow",
            "labels": ["work", "urgent"],
        }
        result = todoist_client.create_task(task_data)

        assert result["id"] == "456"
        assert result["priority"] == 4
        assert result["labels"] == ["work", "urgent"]

    @responses.activate
    def test_create_task_validation_error(self, todoist_client):
        """Test handling of 400 validation error."""
        responses.add(
            responses.POST,
            "https://api.todoist.com/rest/v2/tasks",
            json={"error": "Invalid task data"},
            status=400,
        )

        with pytest.raises(ValidationError) as exc_info:
            todoist_client.create_task({"content": ""})

        assert "Invalid task data" in str(exc_info.value)

    @responses.activate
    def test_create_task_auth_error(self, todoist_client):
        """Test handling of 401 authentication error."""
        responses.add(
            responses.POST,
            "https://api.todoist.com/rest/v2/tasks",
            json={"error": "Unauthorized"},
            status=401,
        )

        with pytest.raises(AuthenticationError) as exc_info:
            todoist_client.create_task({"content": "Test"})

        assert "Invalid Todoist API token" in str(exc_info.value)

    @responses.activate
    def test_create_task_rate_limit_error(self, todoist_client):
        """Test handling of 429 rate limit error."""
        # Disable retries for this test to avoid MaxRetryError
        with patch("app.todoist_client.Retry") as mock_retry:
            mock_retry.return_value = None
            # Recreate client with no retries
            todoist_client.session.mount("https://", requests.adapters.HTTPAdapter())

            responses.add(
                responses.POST,
                "https://api.todoist.com/rest/v2/tasks",
                json={"error": "Rate limit exceeded"},
                status=429,
            )

            with pytest.raises(RateLimitError) as exc_info:
                todoist_client.create_task({"content": "Test"})

            assert "rate limit" in str(exc_info.value).lower()

    @responses.activate
    def test_create_task_not_found_error(self, todoist_client):
        """Test handling of 404 not found error."""
        responses.add(
            responses.POST,
            "https://api.todoist.com/rest/v2/tasks",
            json={"error": "Not found"},
            status=404,
        )

        with pytest.raises(TodoistError) as exc_info:
            todoist_client.create_task({"content": "Test"})

        assert "not found" in str(exc_info.value).lower()

    @responses.activate
    def test_get_tasks_success(self, todoist_client):
        """Test successful task retrieval."""
        responses.add(
            responses.GET,
            "https://api.todoist.com/rest/v2/tasks",
            json=[{"id": "1", "content": "Task 1"}, {"id": "2", "content": "Task 2"}],
            status=200,
        )

        tasks = todoist_client.get_tasks()

        assert len(tasks) == 2
        assert tasks[0]["content"] == "Task 1"
        assert tasks[1]["content"] == "Task 2"

    @responses.activate
    def test_get_tasks_with_filters(self, todoist_client):
        """Test task retrieval with filters."""
        responses.add(
            responses.GET,
            "https://api.todoist.com/rest/v2/tasks",
            json=[{"id": "1", "content": "Filtered task"}],
            status=200,
        )

        tasks = todoist_client.get_tasks(
            project_id="12345", label="work", filter_query="today"
        )

        assert len(tasks) == 1
        # Verify query parameters were sent
        assert "project_id=12345" in responses.calls[0].request.url
        assert "label=work" in responses.calls[0].request.url
        assert "filter=today" in responses.calls[0].request.url

    @responses.activate
    def test_get_tasks_with_due_date_today(self, todoist_client):
        """Test task retrieval with due_date='today' convenience parameter."""
        responses.add(
            responses.GET,
            "https://api.todoist.com/rest/v2/tasks",
            json=[{"id": "1", "content": "Task due today"}],
            status=200,
        )

        tasks = todoist_client.get_tasks(due_date="today")

        assert len(tasks) == 1
        assert "filter=today" in responses.calls[0].request.url

    @responses.activate
    def test_get_tasks_with_due_date_iso(self, todoist_client):
        """Test task retrieval with due_date in ISO format."""
        responses.add(
            responses.GET,
            "https://api.todoist.com/rest/v2/tasks",
            json=[{"id": "1", "content": "Task due specific date"}],
            status=200,
        )

        tasks = todoist_client.get_tasks(due_date="2024-12-31")

        assert len(tasks) == 1
        assert "filter=2024-12-31" in responses.calls[0].request.url

    @responses.activate
    def test_get_projects_success(self, todoist_client):
        """Test successful project retrieval."""
        responses.add(
            responses.GET,
            "https://api.todoist.com/rest/v2/projects",
            json=[{"id": "1", "name": "Inbox"}, {"id": "2", "name": "Work"}],
            status=200,
        )

        projects = todoist_client.get_projects()

        assert len(projects) == 2
        assert projects[0]["name"] == "Inbox"
        assert projects[1]["name"] == "Work"

    def test_connection_error(self, todoist_client):
        """Test handling of connection errors."""
        # Mock the session to raise ConnectionError (from requests library)
        import requests

        with patch.object(
            todoist_client.session,
            "post",
            side_effect=requests.exceptions.ConnectionError("Connection error"),
        ):
            with pytest.raises(TodoistError) as exc_info:
                todoist_client.create_task({"content": "Test"})

            # Should be caught and re-raised as TodoistError with helpful message
            assert (
                "connect" in str(exc_info.value).lower()
                or "internet" in str(exc_info.value).lower()
            )

    def test_session_has_auth_header(self, todoist_client):
        """Test that session includes correct authorization header."""
        assert "Authorization" in todoist_client.session.headers
        assert (
            todoist_client.session.headers["Authorization"] == "Bearer test_token_12345"
        )
        assert todoist_client.session.headers["Content-Type"] == "application/json"
