"""
Task formatting utilities for the DarkWave Task Manager.

Provides helpers to format Todoist task data into user-friendly
markdown strings for display in the Streamlit UI.
"""

from typing import Any

from app.todoist_links import build_task_url


def format_task_list(
    tasks: list[dict[str, Any]], filter_description: str | None = None
) -> str:
    """
    Format a list of Todoist tasks into markdown for UI display.

    Args:
        tasks: List of task dictionaries from Todoist API
        filter_description: Optional description of the filter used
                          (e.g., "due today", "labeled 'work'")

    Returns:
        Markdown-formatted string with task list or empty state message

    Examples:
        >>> tasks = [
        ...     {'id': '1', 'content': 'Buy groceries', 'due': {'date': '2024-01-15'}, 'labels': ['personal']},
        ...     {'id': '2', 'content': 'Review PR', 'labels': ['work']}
        ... ]
        >>> print(format_task_list(tasks))
        ### Your Tasks (2 items)

        - **Buy groceries** 📅 2024-01-15 · _personal_
        - **Review PR** · _work_

    Format Rules (per FW-2.3 specification):
    - Header: "### Your Tasks (N items)" or "### Tasks {filter_description} (N items)"
    - Bullet list with task content in bold
    - Due date with 📅 emoji if present
    - Labels as comma-separated italics
    - Empty state: "You don't have any active tasks right now." with helpful suggestions
    """
    if not tasks:
        # Empty state message
        empty_msg = "You don't have any active tasks right now. ✨\n\n"
        if filter_description:
            empty_msg += f"No tasks found {filter_description}.\n\n"
        empty_msg += "Try creating a task like:\n"
        empty_msg += '- "Buy groceries tomorrow"\n'
        empty_msg += '- "Call dentist at 2pm"\n'
        empty_msg += '- "Review project proposal"'
        return empty_msg

    # Build header
    count = len(tasks)
    item_word = "item" if count == 1 else "items"

    if filter_description:
        header = f"### Tasks {filter_description} ({count} {item_word})\n\n"
    else:
        header = f"### Your Tasks ({count} {item_word})\n\n"

    # Build task list
    task_lines = []
    for task in tasks:
        line_parts = []

        # Task content (required, bold)
        content = task.get("content", "Untitled task")
        line_parts.append(f"**{content}**")

        # Due date (optional, with emoji)
        if "due" in task and task["due"]:
            due_date = task["due"].get("date") or task["due"].get("datetime", "")
            if due_date:
                # Extract just the date part if datetime is provided
                date_str = due_date.split("T")[0] if "T" in due_date else due_date
                line_parts.append(f"📅 {date_str}")

        # Labels (optional, comma-separated italics)
        labels = task.get("labels", [])
        if labels:
            labels_str = ", ".join([f"_{label}_" for label in labels])
            line_parts.append(labels_str)

        # Join parts with separator
        task_line = " · ".join(line_parts)

        # Add "View in Todoist" link if available
        task_url = build_task_url(task)
        if task_url:
            task_line += f" · [View in Todoist]({task_url})"

        task_lines.append(f"- {task_line}")

    return header + "\n".join(task_lines)
