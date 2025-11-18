"""
Unit tests for task formatting utilities.

Tests cover all formatting scenarios from the FW-2.3 specification.
"""

from app.task_formatter import format_task_list


class TestFormatTaskList:
    """Test suite for format_task_list() function."""

    def test_format_empty_list(self):
        """Empty task list should show helpful empty state message."""
        result = format_task_list([])

        assert "You don't have any active tasks right now" in result
        assert "Try creating a task like:" in result
        assert "Buy groceries tomorrow" in result

    def test_format_empty_list_with_filter(self):
        """Empty list with filter should mention the filter."""
        result = format_task_list([], filter_description="due today")

        assert "No tasks found due today" in result
        assert "You don't have any active tasks right now" in result

    def test_format_single_task_minimal(self):
        """Single task with just content."""
        tasks = [{"id": "1", "content": "Buy milk"}]
        result = format_task_list(tasks)

        assert "### Your Tasks (1 item)" in result
        assert "- **Buy milk**" in result

    def test_format_single_task_with_due_date(self):
        """Single task with due date shows date emoji."""
        tasks = [{"id": "1", "content": "Dentist appointment", "due": {"date": "2024-01-15"}}]
        result = format_task_list(tasks)

        assert "- **Dentist appointment** · 📅 2024-01-15" in result

    def test_format_single_task_with_labels(self):
        """Single task with labels shows italicized labels."""
        tasks = [{"id": "1", "content": "Review code", "labels": ["work", "urgent"]}]
        result = format_task_list(tasks)

        assert "- **Review code** · _work_, _urgent_" in result

    def test_format_single_task_full(self):
        """Task with all fields (content, due date, labels)."""
        tasks = [
            {
                "id": "1",
                "content": "Buy groceries",
                "due": {"date": "2024-01-15"},
                "labels": ["personal", "health"],
            }
        ]
        result = format_task_list(tasks)

        assert "- **Buy groceries** · 📅 2024-01-15 · _personal_, _health_" in result

    def test_format_multiple_tasks(self):
        """Multiple tasks should show correct count and all items."""
        tasks = [
            {"id": "1", "content": "Task one", "labels": ["work"]},
            {"id": "2", "content": "Task two", "due": {"date": "2024-01-20"}},
            {"id": "3", "content": "Task three"},
        ]
        result = format_task_list(tasks)

        assert "### Your Tasks (3 items)" in result
        assert "- **Task one** · _work_" in result
        assert "- **Task two** · 📅 2024-01-20" in result
        assert "- **Task three**" in result

    def test_format_with_filter_description(self):
        """Filter description should appear in header."""
        tasks = [{"id": "1", "content": "Work task", "labels": ["work"]}]
        result = format_task_list(tasks, filter_description="labeled 'work'")

        assert "### Tasks labeled 'work' (1 item)" in result

    def test_format_due_datetime_extracts_date(self):
        """Datetime in due field should extract just the date part."""
        tasks = [
            {
                "id": "1",
                "content": "Meeting",
                "due": {"datetime": "2024-01-15T14:30:00"},
            }
        ]
        result = format_task_list(tasks)

        assert "📅 2024-01-15" in result
        assert "T14:30:00" not in result  # Time portion stripped

    def test_format_task_with_no_labels(self):
        """Task with empty labels list should not show label section."""
        tasks = [{"id": "1", "content": "Simple task", "labels": []}]
        result = format_task_list(tasks)

        # Task should have content and link, but no labels
        assert "- **Simple task**" in result
        assert "[View in Todoist](https://app.todoist.com/app/task/1)" in result
        assert "_" not in result  # No italicized labels

    def test_format_preserves_task_order(self):
        """Tasks should appear in the order provided."""
        tasks = [
            {"id": "1", "content": "First"},
            {"id": "2", "content": "Second"},
            {"id": "3", "content": "Third"},
        ]
        result = format_task_list(tasks)

        # Check order by finding positions
        first_pos = result.find("**First**")
        second_pos = result.find("**Second**")
        third_pos = result.find("**Third**")

        assert first_pos < second_pos < third_pos

    def test_format_task_with_todoist_link(self):
        """Task with id should include View in Todoist link."""
        tasks = [{"id": "12345", "content": "Task with link"}]
        result = format_task_list(tasks)

        assert (
            "- **Task with link** · [View in Todoist](https://app.todoist.com/app/task/12345)"
            in result
        )

    def test_format_task_with_url_field(self):
        """Task with url field should use that URL."""
        tasks = [
            {
                "id": "12345",
                "url": "https://app.todoist.com/app/task/12345",
                "content": "Task with API URL",
            }
        ]
        result = format_task_list(tasks)

        assert "[View in Todoist](https://app.todoist.com/app/task/12345)" in result

    def test_format_task_with_full_fields_and_link(self):
        """Task with all fields should include link at the end."""
        tasks = [
            {
                "id": "12345",
                "content": "Complete task",
                "due": {"date": "2024-01-15"},
                "labels": ["work"],
            }
        ]
        result = format_task_list(tasks)

        expected = "- **Complete task** · 📅 2024-01-15 · _work_ · [View in Todoist](https://app.todoist.com/app/task/12345)"
        assert expected in result

    def test_format_task_without_id_no_link(self):
        """Task missing id should not include link."""
        tasks = [{"content": "Task without id"}]
        result = format_task_list(tasks)

        assert "- **Task without id**" in result
        assert "View in Todoist" not in result

    def test_format_multiple_tasks_with_mixed_links(self):
        """Some tasks with links, some without should render correctly."""
        tasks = [
            {"id": "1", "content": "Task with link"},
            {"content": "Task without link"},
            {"id": "3", "content": "Another with link"},
        ]
        result = format_task_list(tasks)

        assert "[View in Todoist](https://app.todoist.com/app/task/1)" in result
        assert "- **Task without link**" in result
        assert "[View in Todoist](https://app.todoist.com/app/task/3)" in result
