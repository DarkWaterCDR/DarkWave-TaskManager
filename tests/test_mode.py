"""
Unit tests for the mode detection module.

Tests cover all three modes (CHAT, CREATE, RETRIEVE) with various
input patterns to ensure accurate classification.
"""

from app.mode import Mode, detect_mode


class TestModeDetection:
    """Test suite for detect_mode() function."""

    # CHAT mode tests
    def test_detect_chat_hello(self):
        """Simple greetings should be classified as CHAT."""
        assert detect_mode("hello") == Mode.CHAT
        assert detect_mode("hi") == Mode.CHAT
        assert detect_mode("hey") == Mode.CHAT
        assert detect_mode("Hi!") == Mode.CHAT
        assert detect_mode("HELLO") == Mode.CHAT

    def test_detect_chat_greetings_with_time(self):
        """Time-based greetings should be CHAT."""
        assert detect_mode("good morning") == Mode.CHAT
        assert detect_mode("Good afternoon!") == Mode.CHAT
        assert detect_mode("good evening") == Mode.CHAT

    def test_detect_chat_meta_questions(self):
        """Questions about capabilities should be CHAT."""
        assert detect_mode("what can you do?") == Mode.CHAT
        assert detect_mode("how do you work") == Mode.CHAT
        assert detect_mode("help me") == Mode.CHAT
        assert detect_mode("show me how to use this") == Mode.CHAT
        assert detect_mode("who are you?") == Mode.CHAT
        assert detect_mode("what are you") == Mode.CHAT

    def test_detect_chat_empty_input(self):
        """Empty or whitespace-only input should be CHAT."""
        assert detect_mode("") == Mode.CHAT
        assert detect_mode("   ") == Mode.CHAT
        assert detect_mode("\n\t") == Mode.CHAT

    # RETRIEVE mode tests
    def test_detect_retrieve_what_tasks(self):
        """'What tasks' patterns should be RETRIEVE."""
        assert detect_mode("what tasks do I have?") == Mode.RETRIEVE
        assert detect_mode("what are my tasks") == Mode.RETRIEVE
        assert detect_mode("What tasks are on my list?") == Mode.RETRIEVE

    def test_detect_retrieve_show_list(self):
        """'Show/list tasks' patterns should be RETRIEVE."""
        assert detect_mode("show my tasks") == Mode.RETRIEVE
        assert detect_mode("list all tasks") == Mode.RETRIEVE
        assert detect_mode("display tasks") == Mode.RETRIEVE
        assert detect_mode("show tasks") == Mode.RETRIEVE
        assert detect_mode("list tasks") == Mode.RETRIEVE
        assert detect_mode("my tasks") == Mode.RETRIEVE

    def test_detect_retrieve_due_date_queries(self):
        """Date-based task queries should be RETRIEVE."""
        assert detect_mode("what tasks are due today?") == Mode.RETRIEVE
        assert detect_mode("show me tasks due tomorrow") == Mode.RETRIEVE
        assert detect_mode("what's overdue") == Mode.RETRIEVE
        assert detect_mode("tasks due today") == Mode.RETRIEVE

    def test_detect_retrieve_label_queries(self):
        """Label-based queries should be RETRIEVE."""
        assert detect_mode("show tasks labeled work") == Mode.RETRIEVE
        assert detect_mode("tasks with label personal") == Mode.RETRIEVE
        assert detect_mode("find tasks tagged urgent") == Mode.RETRIEVE

    def test_detect_retrieve_reverse_order(self):
        """Reversed word order should still detect RETRIEVE."""
        assert detect_mode("tasks what do I have") == Mode.RETRIEVE
        assert detect_mode("tasks show me") == Mode.RETRIEVE

    # CREATE mode tests (default behavior)
    def test_detect_create_task_descriptions(self):
        """Task creation statements should be CREATE."""
        assert detect_mode("buy groceries tomorrow") == Mode.CREATE
        assert detect_mode("Schedule dentist appointment next week") == Mode.CREATE
        assert detect_mode("Call mom at 3pm") == Mode.CREATE
        assert detect_mode("Finish the project report by Friday") == Mode.CREATE

    def test_detect_create_imperative_statements(self):
        """Imperative commands should be CREATE."""
        assert detect_mode("Remind me to pay bills") == Mode.CREATE
        assert detect_mode("Add buy milk to my list") == Mode.CREATE
        assert detect_mode("Create task: review code") == Mode.CREATE

    def test_detect_create_ambiguous_input(self):
        """Ambiguous input defaults to CREATE."""
        assert detect_mode("random text") == Mode.CREATE
        assert detect_mode("meeting") == Mode.CREATE
        assert detect_mode("urgent") == Mode.CREATE

    def test_detect_create_task_with_task_keyword(self):
        """Using 'task' in creation context should still be CREATE."""
        # These don't match retrieve patterns, so they default to CREATE
        assert detect_mode("create task for project review") == Mode.CREATE
        assert detect_mode("add task: buy snacks") == Mode.CREATE
        assert detect_mode("new task needed") == Mode.CREATE

    # Edge cases
    def test_detect_mode_case_insensitive(self):
        """Mode detection should be case-insensitive."""
        assert detect_mode("HELLO") == Mode.CHAT
        assert detect_mode("WHAT TASKS DO I HAVE") == Mode.RETRIEVE
        assert detect_mode("BUY GROCERIES") == Mode.CREATE

    def test_detect_mode_with_extra_whitespace(self):
        """Extra whitespace should be handled correctly."""
        assert detect_mode("  hello  ") == Mode.CHAT
        assert detect_mode("   what tasks   ") == Mode.RETRIEVE
        assert detect_mode("  buy milk  ") == Mode.CREATE

    def test_detect_mode_with_punctuation(self):
        """Punctuation should not affect detection."""
        assert detect_mode("hello!!!") == Mode.CHAT
        assert detect_mode("what tasks???") == Mode.RETRIEVE
        assert detect_mode("buy groceries.") == Mode.CREATE


class TestModeDetectionEdgeCases:
    """Additional edge cases discovered from real usage (MDF-2)."""

    def test_detect_retrieve_todo_list(self):
        """'todo list' should be recognized as RETRIEVE."""
        assert detect_mode("Show me what's on my todo list.") == Mode.RETRIEVE
        assert detect_mode("what's on my todo list") == Mode.RETRIEVE
        assert detect_mode("show my todo list") == Mode.RETRIEVE
        assert detect_mode("whats on my todo") == Mode.RETRIEVE

    def test_detect_retrieve_to_do_hyphenated(self):
        """Hyphenated 'to-do' should be RETRIEVE."""
        assert detect_mode("show my to-do list") == Mode.RETRIEVE
        assert detect_mode("what's on my to-do") == Mode.RETRIEVE
        assert detect_mode("check my to-do") == Mode.RETRIEVE

    def test_detect_retrieve_possessive_my(self):
        """Possessive 'my' patterns should be RETRIEVE."""
        assert detect_mode("check my tasks") == Mode.RETRIEVE
        assert detect_mode("view my todo") == Mode.RETRIEVE
        assert detect_mode("see my list") == Mode.RETRIEVE
        assert detect_mode("my tasks") == Mode.RETRIEVE

    def test_detect_retrieve_whats_on(self):
        """'what's on my' patterns should be RETRIEVE."""
        assert detect_mode("what's on my list?") == Mode.RETRIEVE
        assert detect_mode("whats on my todo") == Mode.RETRIEVE
        assert detect_mode("what's on my tasks") == Mode.RETRIEVE

    def test_detect_retrieve_check_view(self):
        """'check' and 'view' verbs should trigger RETRIEVE."""
        assert detect_mode("check tasks") == Mode.RETRIEVE
        assert detect_mode("view my todo list") == Mode.RETRIEVE
        assert detect_mode("view tasks") == Mode.RETRIEVE

    def test_detect_retrieve_todo_without_list(self):
        """'todo' without 'list' should still be RETRIEVE."""
        assert detect_mode("show my todo") == Mode.RETRIEVE
        assert detect_mode("what's my todo") == Mode.RETRIEVE
        assert detect_mode("check todo") == Mode.RETRIEVE

    def test_detect_retrieve_question_forms(self):
        """Question forms should be RETRIEVE."""
        assert detect_mode("Do I have any tasks?") == Mode.RETRIEVE
        assert detect_mode("Do I have tasks due today?") == Mode.RETRIEVE
        assert detect_mode("What do I have on my list?") == Mode.RETRIEVE

    def test_detect_create_not_confused_by_task_word(self):
        """Task descriptions with 'task' word should still be CREATE."""
        assert detect_mode("Add task to review document") == Mode.CREATE
        assert detect_mode("Task: call the client") == Mode.CREATE
        assert detect_mode("My task is to finish the report") == Mode.CREATE
        assert detect_mode("Create a task for meeting prep") == Mode.CREATE
