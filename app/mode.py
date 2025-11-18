"""
Conversational mode detection for the DarkWave Task Manager.

This module defines the conceptual modes the assistant can operate in
and provides utilities for classifying user input into the appropriate mode.

Modes:
- CHAT: Conversational interactions (greetings, questions about capabilities)
- CREATE: Task creation from natural language descriptions
- RETRIEVE: Querying existing tasks from Todoist

LLM Note: Mode detection happens before LLM invocation to route requests
efficiently and prevent unwanted task creation on casual conversation.
"""

import re
from enum import Enum


class Mode(str, Enum):
    """
    Conversation modes for the task assistant.

    Each mode represents a distinct intent category that determines
    how the assistant should respond to user input.
    """

    CHAT = "chat"  # Conversational/meta questions, no task operations
    CREATE = "create"  # Create new Todoist task from description
    RETRIEVE = "retrieve"  # Query and display existing tasks


def detect_mode(user_message: str) -> Mode:
    """
    Classify user input into a conversation mode.

    This is a pure function using heuristics to route user intent before
    LLM invocation. The classification is fast and deterministic.

    Classification Rules:
    - CHAT: Greetings, meta questions about capabilities
    - RETRIEVE: Questions about existing tasks (what/show/list patterns)
    - CREATE: Default mode for task descriptions

    Args:
        user_message: The user's natural language input

    Returns:
        The detected Mode (CHAT, CREATE, or RETRIEVE)

    Examples:
        >>> detect_mode("hello")
        Mode.CHAT
        >>> detect_mode("what tasks do I have?")
        Mode.RETRIEVE
        >>> detect_mode("buy groceries tomorrow")
        Mode.CREATE
    """
    if not user_message or not user_message.strip():
        return Mode.CHAT

    message_lower = user_message.strip().lower()

    # CHAT patterns: greetings and meta questions
    chat_patterns = [
        r"^(hi|hello|hey|greetings)[\s!?.]*$",
        r"^(good morning|good afternoon|good evening)[\s!?.]*$",
        r"\b(what can you do|how do you work|help me|show me how)\b",
        r"\b(who are you|what are you)\b",
    ]

    for pattern in chat_patterns:
        if re.search(pattern, message_lower):
            return Mode.CHAT

    # CREATE patterns: explicit task creation verbs
    # Check these BEFORE retrieve patterns to avoid false positives
    # e.g., "Add buy milk to my list" should be CREATE not RETRIEVE
    create_patterns = [
        r"^(add|create|new|make|remind me to|i need to|todo:)",
        r"\b(add|create|remind me)\b.*\b(task|todo|to-do|list)\b",
    ]

    for pattern in create_patterns:
        if re.search(pattern, message_lower):
            return Mode.CREATE

    # RETRIEVE patterns: questions about existing tasks
    # Pattern order: most specific first to avoid false matches
    retrieve_patterns = [
        # Direct "what's on my" patterns
        r"^what'?s? on my",
        # Question forms starting with "do i have"
        r"^do i have (any )?task",
        # Possessive patterns (my tasks, my todo, my list)
        # But NOT "my task is to" (that's task description in CREATE mode)
        r"\bmy (tasks|todo|to-do|to do|list)\b",
        r"\bmy task\b(?! is)",  # "my task" but not followed by "is"
        # Action verbs with task/todo/list variations
        r"\b(what|show|list|display|get|find|see|view|check)\b.*\b(task|todo|to-do|to do)",
        r"\b(task|todo|to-do|to do).*\b(what|show|list|display|do i have)",
        # List-specific patterns
        r"\b(what|show|list|display|get|view|check)\b.*\b(list|todo list|to-do list)",
        r"\bon my (list|todo|to-do|tasks?)",
        # Simple imperatives
        r"^(my tasks|show tasks|list tasks|check tasks|view tasks)",
        r"^(show|check|view) (my )?(task|todo|to-do|list)",
        # Date-based queries
        r"\b(due today|due tomorrow|overdue)\b",
        # Label-based queries
        r"\b(tasks? (with|labeled|tagged))\b",
    ]

    for pattern in retrieve_patterns:
        if re.search(pattern, message_lower):
            return Mode.RETRIEVE

    # Default: CREATE mode
    return Mode.CREATE


# TODO(FW-3.3): Wire mode detection into app/main.py with logging
