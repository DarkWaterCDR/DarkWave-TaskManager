"""
Todoist API client with robust error handling and retry logic.

This module provides a clean interface to the Todoist API with:
- Bearer token authentication
- Automatic retry for transient failures
- User-friendly error messages for common failure scenarios

LLM Note: Error handling is designed to provide actionable feedback
to users rather than exposing technical API details.
"""

from typing import Any

import requests
import structlog
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = structlog.get_logger()


class TodoistError(Exception):
    """Base exception for Todoist client errors."""

    pass


class AuthenticationError(TodoistError):
    """Raised when API token is invalid or expired."""

    pass


class RateLimitError(TodoistError):
    """Raised when API rate limit is exceeded."""

    pass


class ValidationError(TodoistError):
    """Raised when request data is invalid."""

    pass


class TodoistClient:
    """
    Client for interacting with Todoist REST API v2.

    Handles authentication, retries, and error conversion to user-friendly messages.

    API Documentation: https://developer.todoist.com/rest/v2/
    """

    BASE_URL = "https://api.todoist.com/rest/v2"

    def __init__(self, api_token: str):
        """
        Initialize Todoist client with API token.

        Args:
            api_token: Todoist API bearer token

        LLM Note: Session is configured with retry strategy to handle
        transient network failures and rate limiting automatically.
        """
        self.api_token = api_token
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic and authentication.

        Returns:
            Configured requests session

        LLM Note: Retry strategy targets 429 (rate limit) and 5xx (server errors).
        We use exponential backoff to avoid overwhelming the API during issues.
        """
        session = requests.Session()

        # Configure retry strategy
        # Retry on: 429 (rate limit), 500, 502, 503, 504 (server errors)
        retry_strategy = Retry(
            total=3,  # Maximum 3 retries
            backoff_factor=1,  # Wait 1s, 2s, 4s between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)

        # Set authentication header
        session.headers.update(
            {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }
        )

        return session

    def create_task(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new task in Todoist.

        Args:
            task_data: Task details (content, description, priority, due_string, labels, etc.)

        Returns:
            Created task object with the following fields:
            - id (str): Unique task identifier
            - url (str): Canonical URL to view the task in Todoist
            - content (str): Task content/title
            - project_id (str): ID of the project containing this task
            - Other fields: description, priority, due, labels, etc.

        Raises:
            ValidationError: If task data is invalid
            AuthenticationError: If API token is invalid
            RateLimitError: If rate limit is exceeded (despite retries)
            TodoistError: For other API errors

        Example:
            >>> client.create_task({
            ...     "content": "Buy groceries",
            ...     "description": "Milk, bread, eggs",
            ...     "priority": 2,
            ...     "due_string": "tomorrow"
            ... })

        LLM Note: The 'content' field is required. Priority ranges from 1 (lowest)
        to 4 (highest). The due_string accepts natural language like "tomorrow",
        "next Monday", or specific dates.

        API Contract: The response includes 'id' and 'url' fields.
        The 'url' field provides the canonical link for viewing the task.
        """
        try:
            response = self.session.post(f"{self.BASE_URL}/tasks", json=task_data, timeout=10)
            response.raise_for_status()

            task = response.json()
            logger.info("task_created", task_id=task.get("id"), content=task.get("content"))
            return task  # type: ignore[no-any-return]

        except requests.exceptions.HTTPError as e:
            self._handle_http_error(e, "create task")
            raise  # _handle_http_error always raises
        except requests.exceptions.Timeout as e:
            raise TodoistError("Request to Todoist API timed out. Please try again.") from e
        except requests.exceptions.ConnectionError as e:
            raise TodoistError(
                "Unable to connect to Todoist API. Check your internet connection."
            ) from e

    def get_tasks(
        self,
        project_id: str | None = None,
        label: str | None = None,
        filter_query: str | None = None,
        due_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve tasks from Todoist.

        Args:
            project_id: Filter by specific project ID
            label: Filter by label name
            filter_query: Todoist filter query (e.g., "today | overdue")
            due_date: Filter by due date - "today", "tomorrow", or ISO date (YYYY-MM-DD)

        Returns:
            List of task dictionaries. Each task includes:
            - id (str): Unique task identifier
            - url (str): Canonical URL to view the task in Todoist
            - content (str): Task content/title
            - project_id (str): ID of the project containing this task
            - due (dict, optional): Due date information
            - labels (list, optional): List of label strings
            - Other fields: description, priority, etc.

        Raises:
            AuthenticationError: If API token is invalid
            TodoistError: For other API errors

        LLM Note: Filter query supports Todoist's powerful filter syntax.
        See https://todoist.com/help/articles/introduction-to-filters

        The due_date parameter is a convenience filter that converts to filter_query.
        For "today", it retrieves tasks due today. For specific dates, use ISO format.

        API Contract: Each task in the returned list includes 'id' and 'url' fields.
        The 'url' field provides the canonical link for viewing the task.
        """
        params = {}
        if project_id:
            params["project_id"] = project_id
        if label:
            params["label"] = label

        # Handle due_date convenience parameter
        if due_date and not filter_query:
            if due_date.lower() == "today":
                filter_query = "today"
            elif due_date.lower() == "tomorrow":
                filter_query = "tomorrow"
            else:
                # Assume ISO date format YYYY-MM-DD
                filter_query = due_date

        if filter_query:
            params["filter"] = filter_query

        try:
            response = self.session.get(f"{self.BASE_URL}/tasks", params=params, timeout=10)
            response.raise_for_status()

            tasks = response.json()
            logger.info("tasks_retrieved", count=len(tasks), filters=params)
            return tasks  # type: ignore[no-any-return]

        except requests.exceptions.HTTPError as e:
            self._handle_http_error(e, "retrieve tasks")
            raise  # _handle_http_error always raises
        except requests.exceptions.Timeout as e:
            raise TodoistError("Request to Todoist API timed out. Please try again.") from e
        except requests.exceptions.ConnectionError as e:
            raise TodoistError(
                "Unable to connect to Todoist API. Check your internet connection."
            ) from e

    def get_projects(self) -> list[dict[str, Any]]:
        """
        Retrieve all projects.

        Returns:
            List of project objects

        Raises:
            AuthenticationError: If API token is invalid
            TodoistError: For other API errors
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/projects", timeout=10)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

        except requests.exceptions.HTTPError as e:
            self._handle_http_error(e, "retrieve projects")
            raise  # _handle_http_error always raises
        except requests.exceptions.Timeout as e:
            raise TodoistError("Request to Todoist API timed out. Please try again.") from e
        except requests.exceptions.ConnectionError as e:
            raise TodoistError(
                "Unable to connect to Todoist API. Check your internet connection."
            ) from e

    def _handle_http_error(self, error: requests.exceptions.HTTPError, operation: str) -> None:
        """
        Convert HTTP errors to user-friendly exceptions.

        Args:
            error: HTTP error from requests
            operation: Description of operation that failed

        Raises:
            Specific TodoistError subclass based on status code

        LLM Note: This method translates technical HTTP status codes into
        actionable error messages that users can understand and act upon.
        """
        status_code = error.response.status_code

        if status_code == 400:
            # Bad request - invalid data
            try:
                error_details = error.response.json()
                raise ValidationError(
                    f"Invalid task data: {error_details.get('error', 'Unknown validation error')}"
                )
            except ValueError as e:
                raise ValidationError(f"Invalid data provided to {operation}") from e

        elif status_code == 401:
            # Unauthorized - invalid token
            raise AuthenticationError(
                "Invalid Todoist API token. Please check your TODOIST_API_TOKEN in .env file."
            )

        elif status_code == 403:
            # Forbidden - insufficient permissions
            raise AuthenticationError(
                "Insufficient permissions. Your API token may not have access to this resource."
            )

        elif status_code == 404:
            # Not found
            raise TodoistError("Resource not found. The requested item may have been deleted.")

        elif status_code == 429:
            # Rate limit exceeded (after retries)
            raise RateLimitError(
                "Todoist API rate limit exceeded. Please wait a moment before trying again."
            )

        else:
            # Other errors
            logger.error(
                "todoist_api_error",
                status_code=status_code,
                operation=operation,
                response_text=error.response.text,
            )
            raise TodoistError(
                f"Todoist API error ({status_code}): Unable to {operation}. Please try again later."
            )
