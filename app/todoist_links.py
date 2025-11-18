"""
Todoist URL construction utilities.

Provides helper functions for building valid Todoist task links
using the modern project/{project_id}/task/{task_id} format.
"""

from typing import Any

import structlog

logger = structlog.get_logger()


def build_task_url(task: dict[str, Any] | None) -> str | None:
    """
    Build a Todoist task URL from a task dictionary.

    Prefers the 'url' field from the API response if available,
    otherwise constructs the URL using the task ID.

    Args:
        task: Task dictionary from Todoist API containing 'id' and optionally 'url' fields

    Returns:
        Full Todoist task URL, or None if required fields are missing

    Examples:
        >>> task = {'id': '12345', 'url': 'https://app.todoist.com/app/task/12345'}
        >>> build_task_url(task)
        'https://app.todoist.com/app/task/12345'

        >>> task = {'id': '12345', 'content': 'Example task'}
        >>> build_task_url(task)
        'https://app.todoist.com/app/task/12345'

    Note:
        The Todoist API returns a 'url' field which is the canonical URL for the task.
        If not present, we construct it using the task ID.
    """
    if task is None:
        logger.warning("build_task_url_called_with_none")
        return None

    # Prefer the URL provided by Todoist API
    if "url" in task and task["url"]:
        return str(task["url"])

    # Fallback: construct URL from task ID
    task_id = task.get("id")

    if not task_id:
        logger.warning("build_task_url_missing_task_id", task=task)
        return None

    return f"https://app.todoist.com/app/task/{task_id}"
