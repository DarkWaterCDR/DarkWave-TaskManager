"""
Unit tests for LLM service.

Tests task parsing, prompt engineering, and Pydantic validation.
"""

from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.llm_service import LLMService, TodoistTask


@pytest.fixture
def mock_llm_response():
    """Fixture providing a mock LLM response."""

    def _create_response(content: str):
        mock_response = Mock()
        mock_response.content = content
        return mock_response

    return _create_response


@pytest.fixture
def llm_service():
    """Fixture providing an LLMService instance with mocked LLM."""
    with patch("app.llm_service.ChatGoogleGenerativeAI") as mock_llm_class:
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        service = LLMService(api_key="test_key", model="gemini-2.5-flash", temperature=0.3)
        service.model = mock_llm
        yield service


class TestTodoistTask:
    """Test suite for TodoistTask Pydantic model."""

    def test_minimal_task(self):
        """Test task with only required field."""
        task = TodoistTask(content="Test task")

        assert task.content == "Test task"
        assert task.description == ""
        assert task.priority == 3
        assert task.due_string is None
        assert task.labels == []
        assert task.project_id is None

    def test_full_task(self):
        """Test task with all fields populated."""
        task = TodoistTask(
            content="Complete report",
            description="Quarterly sales report",
            priority=4,
            due_string="tomorrow",
            labels=["work", "urgent"],
            project_id="12345",
        )

        assert task.content == "Complete report"
        assert task.description == "Quarterly sales report"
        assert task.priority == 4
        assert task.due_string == "tomorrow"
        assert task.labels == ["work", "urgent"]
        assert task.project_id == "12345"

    def test_priority_validation(self):
        """Test priority field validation (must be 1-4)."""
        # Valid priorities
        for priority in [1, 2, 3, 4]:
            task = TodoistTask(content="Test", priority=priority)
            assert task.priority == priority

        # Invalid priorities
        with pytest.raises(PydanticValidationError):
            TodoistTask(content="Test", priority=0)

        with pytest.raises(PydanticValidationError):
            TodoistTask(content="Test", priority=5)

    def test_model_dump_excludes_none(self):
        """Test that model_dump can exclude None values."""
        task = TodoistTask(content="Test task", priority=2)

        data = task.model_dump(exclude_none=True)

        assert "content" in data
        assert "priority" in data
        assert "due_string" not in data  # Should be excluded (None)
        assert "project_id" not in data  # Should be excluded (None)


class TestLLMService:
    """Test suite for LLMService."""

    def test_initialization(self):
        """Test LLMService initialization."""
        with patch("app.llm_service.ChatGoogleGenerativeAI") as mock_llm_class:
            _ = LLMService(api_key="test_key", model="gemini-pro", temperature=0.5)

            # Verify LLM was initialized with correct parameters
            mock_llm_class.assert_called_once_with(
                model="gemini-pro",
                google_api_key="test_key",
                temperature=0.5,
                convert_system_message_to_human=True,
            )

    def test_parse_task_simple(self, llm_service, mock_llm_response):
        """Test parsing simple task description."""
        llm_service.model.invoke.return_value = mock_llm_response(
            """
        {
            "content": "Call dentist",
            "description": "Schedule cleaning appointment",
            "priority": 3,
            "due_string": "tomorrow",
            "labels": ["calls", "personal", "health"]
        }
        """
        )

        task = llm_service.parse_task("Call dentist tomorrow about cleaning")

        assert task.content == "Call dentist"
        assert task.description == "Schedule cleaning appointment"
        assert task.priority == 3
        assert task.due_string == "tomorrow"
        assert "calls" in task.labels

    def test_parse_task_urgent(self, llm_service, mock_llm_response):
        """Test parsing urgent task."""
        llm_service.model.invoke.return_value = mock_llm_response(
            """
        {
            "content": "Finish project report",
            "description": "Complete and submit quarterly project report",
            "priority": 4,
            "due_string": "Friday",
            "labels": ["work", "urgent", "reports"]
        }
        """
        )

        task = llm_service.parse_task("URGENT: Finish project report by Friday")

        assert task.content == "Finish project report"
        assert task.priority == 4
        assert "urgent" in task.labels

    def test_parse_task_minimal(self, llm_service, mock_llm_response):
        """Test parsing task with minimal information."""
        llm_service.model.invoke.return_value = mock_llm_response(
            """
        {
            "content": "Buy groceries",
            "description": "",
            "priority": 3,
            "due_string": null,
            "labels": ["personal", "errands"]
        }
        """
        )

        task = llm_service.parse_task("Buy groceries")

        assert task.content == "Buy groceries"
        assert task.priority == 3
        assert task.due_string is None

    def test_parse_task_with_details(self, llm_service, mock_llm_response):
        """Test parsing task with detailed description."""
        llm_service.model.invoke.return_value = mock_llm_response(
            """
        {
            "content": "Buy groceries",
            "description": "Items needed: milk, bread, eggs",
            "priority": 3,
            "due_string": null,
            "labels": ["personal", "errands", "shopping"]
        }
        """
        )

        task = llm_service.parse_task("Buy groceries - milk, bread, eggs")

        assert task.content == "Buy groceries"
        assert "milk" in task.description

    def test_parse_task_invalid_json(self, llm_service, mock_llm_response):
        """Test handling of invalid JSON from LLM."""
        llm_service.model.invoke.return_value = mock_llm_response("This is not valid JSON")

        with pytest.raises(ValueError) as exc_info:
            llm_service.parse_task("Test task")

        assert "Failed to parse task" in str(exc_info.value)

    def test_parse_task_missing_required_field(self, llm_service, mock_llm_response):
        """Test handling of response missing required 'content' field."""
        llm_service.model.invoke.return_value = mock_llm_response(
            """
        {
            "description": "Some description",
            "priority": 3
        }
        """
        )

        with pytest.raises(ValueError):
            llm_service.parse_task("Test task")

    def test_parse_task_invalid_priority(self, llm_service, mock_llm_response):
        """Test handling of invalid priority value."""
        llm_service.model.invoke.return_value = mock_llm_response(
            """
        {
            "content": "Test task",
            "priority": 10
        }
        """
        )

        with pytest.raises(ValueError):
            llm_service.parse_task("Test task")

    def test_parse_multiple_tasks_single_input(self, llm_service, mock_llm_response):
        """Test parse_multiple_tasks with single task input."""
        llm_service.model.invoke.return_value = mock_llm_response(
            """
        {
            "content": "Test task",
            "description": "",
            "priority": 3,
            "due_string": null,
            "labels": []
        }
        """
        )

        tasks = llm_service.parse_multiple_tasks("Test task")

        assert len(tasks) == 1
        assert tasks[0].content == "Test task"

    def test_llm_invocation_includes_format_instructions(self, llm_service):
        """Test that LLM is invoked with proper format instructions."""
        llm_service.model.invoke.return_value = Mock(
            content="""
        {
            "content": "Test",
            "description": "",
            "priority": 3,
            "due_string": null,
            "labels": []
        }
        """
        )

        llm_service.parse_task("Test input")

        # Verify invoke was called
        assert llm_service.model.invoke.called

        # Get the call arguments
        call_args = llm_service.model.invoke.call_args[0][0]

        # Verify format instructions are included
        prompt_text = str(call_args)
        assert "TodoistTask" in prompt_text or "content" in prompt_text
