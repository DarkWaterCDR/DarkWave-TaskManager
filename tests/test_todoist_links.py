"""
Tests for Todoist URL construction utilities.
"""

from app.todoist_links import build_task_url


class TestBuildTaskUrl:
    """Tests for build_task_url function."""

    def test_build_url_with_url_field(self):
        """Should prefer the url field from API response."""
        task = {
            "id": "12345",
            "url": "https://app.todoist.com/app/task/12345",
            "content": "Test task",
        }

        url = build_task_url(task)

        assert url == "https://app.todoist.com/app/task/12345"

    def test_build_url_with_valid_task_id_only(self):
        """Should build correct URL with just task id."""
        task = {"id": "12345", "content": "Test task"}

        url = build_task_url(task)

        assert url == "https://app.todoist.com/app/task/12345"

    def test_build_url_missing_task_id(self):
        """Should return None when task id is missing."""
        task = {"content": "Test task"}

        url = build_task_url(task)

        assert url is None

    def test_build_url_with_none(self):
        """Should return None when task is None."""
        url = build_task_url(None)

        assert url is None

    def test_build_url_with_empty_dict(self):
        """Should return None when task dict is empty."""
        url = build_task_url({})

        assert url is None

    def test_build_url_with_empty_string_id(self):
        """Should return None when id is empty string."""
        task = {"id": "", "content": "Test task"}

        url = build_task_url(task)
        assert url is None

    def test_build_url_prefers_url_field_over_constructed(self):
        """Should prefer API url field even if id is present."""
        task = {
            "id": "12345",
            "url": "https://app.todoist.com/app/task/custom-url-format",
            "content": "Test task",
        }

        url = build_task_url(task)

        # Should use the url field, not construct from id
        assert url == "https://app.todoist.com/app/task/custom-url-format"

    def test_build_url_preserves_extra_fields(self):
        """Should work with task dicts containing extra fields."""
        task = {
            "id": "12345",
            "project_id": "67890",
            "content": "Test task",
            "due": {"date": "2024-01-15"},
            "labels": ["work", "urgent"],
            "priority": 4,
        }

        url = build_task_url(task)

        assert url == "https://app.todoist.com/app/task/12345"
