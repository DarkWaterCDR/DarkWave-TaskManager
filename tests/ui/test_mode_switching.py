"""
Browser-based UI tests for mode switching behavior.

These tests verify that the mode detection works correctly in the actual
Streamlit UI, covering the scenarios:
1. Greeting → Retrieve → Create
2. Query → Greeting → Create
3. Multiple retrieves with different patterns
4. CREATE not triggered by queries

Tests use Playwright to interact with the running Streamlit app.
"""

from playwright.sync_api import Page


class TestModeSwitchingUI:
    """UI tests for mode detection and switching in Streamlit app."""

    def test_greeting_to_retrieve_to_create(
        self, page: Page, streamlit_app, mode_test_context
    ):
        """
        Scenario 1: User greets, queries tasks, then creates task.

        Steps:
        1. Send greeting: "Hello" → Should get CHAT response
        2. Send retrieve query: "Show me what's on my todo list." → Should get task list (RETRIEVE)
        3. Send create command: "Buy groceries tomorrow" → Should get task preview (CREATE)

        This was the original failing case that triggered MDF-1 through MDF-4.
        """
        page.goto(streamlit_app)
        page.wait_for_load_state("networkidle")

        # Step 1: Greeting
        mode_test_context.send_message("Hello")
        assert (
            mode_test_context.has_greeting_response()
        ), "Expected greeting response with 'Darkwave' or 'Task Manager'"
        assert (
            not mode_test_context.has_error_message()
        ), "Should not show error for greeting"

        # Step 2: Retrieve query (the original bug case)
        mode_test_context.send_message("Show me what's on my todo list.")
        assert (
            mode_test_context.has_task_list()
        ), "Expected task list or empty state for retrieve query"
        assert (
            not mode_test_context.has_error_message()
        ), "Should NOT show 'task_parsing_failed' error (bug was mode=create causing LLM error)"

        # Step 3: Create task
        mode_test_context.send_message("Buy groceries tomorrow")
        assert mode_test_context.has_task_preview(), "Expected task creation preview"
        assert (
            not mode_test_context.has_error_message()
        ), "Should not show error for task creation"

    def test_query_to_greeting_to_create(
        self, page: Page, streamlit_app, mode_test_context
    ):
        """
        Scenario 2: User queries first, then greets, then creates.

        Steps:
        1. Query: "What tasks do I have?" → RETRIEVE
        2. Greeting: "Good morning" → CHAT
        3. Create: "Call dentist at 2pm" → CREATE
        """
        page.goto(streamlit_app)
        page.wait_for_load_state("networkidle")

        # Step 1: Query tasks
        mode_test_context.send_message("What tasks do I have?")
        assert (
            mode_test_context.has_task_list()
        ), "Expected task list for 'What tasks do I have?'"
        assert (
            not mode_test_context.has_error_message()
        ), "Should not error on task query"

        # Step 2: Greeting
        mode_test_context.send_message("Good morning")
        assert mode_test_context.has_greeting_response(), "Expected greeting response"

        # Step 3: Create task
        mode_test_context.send_message("Call dentist at 2pm")
        assert mode_test_context.has_task_preview(), "Expected task creation preview"

    def test_multiple_retrieve_patterns(
        self, page: Page, streamlit_app, mode_test_context
    ):
        """
        Scenario 3: Various retrieve patterns in sequence.

        Tests all the new patterns added in MDF-1:
        - "show my tasks"
        - "what's on my todo list"
        - "check my to-do"
        - "view tasks due today"
        - "do i have any tasks"
        """
        page.goto(streamlit_app)
        page.wait_for_load_state("networkidle")

        retrieve_queries = [
            "show my tasks",
            "what's on my todo list",
            "check my to-do",
            "view tasks due today",
            "do i have any tasks",
        ]

        for query in retrieve_queries:
            mode_test_context.send_message(query)
            assert (
                mode_test_context.has_task_list()
            ), f"Query '{query}' should trigger RETRIEVE and show task list"
            assert (
                not mode_test_context.has_error_message()
            ), f"Query '{query}' should not cause parsing error"

    def test_create_not_triggered_by_queries(
        self, page: Page, streamlit_app, mode_test_context
    ):
        """
        Scenario 4: Ensure queries don't trigger task creation.

        These queries should be RETRIEVE, not CREATE:
        - "Do I have any tasks due today?"
        - "Show me my todo list"
        - "What's on my list?"

        If mode detection incorrectly classifies as CREATE, the LLM will refuse
        to parse (guardrails) and show task_parsing_failed error.
        """
        page.goto(streamlit_app)
        page.wait_for_load_state("networkidle")

        retrieve_queries = [
            "Do I have any tasks due today?",
            "Show me my todo list",
            "What's on my list?",
        ]

        for query in retrieve_queries:
            mode_test_context.send_message(query)
            # Should NOT see task creation preview
            assert (
                not mode_test_context.has_task_preview()
            ), f"Query '{query}' should NOT trigger task creation"
            # Should see task list
            assert (
                mode_test_context.has_task_list()
            ), f"Query '{query}' should show task list"
            # Should NOT see error (this was the original bug)
            assert (
                not mode_test_context.has_error_message()
            ), f"Query '{query}' should not cause LLM parsing error"

    def test_edge_case_my_task_is_to(
        self, page: Page, streamlit_app, mode_test_context
    ):
        """
        Edge case: "My task is to..." should be CREATE not RETRIEVE.

        This tests the negative lookahead pattern: r'\bmy task\b(?! is)'
        "My task is to finish the report" should create a task, not query.
        """
        page.goto(streamlit_app)
        page.wait_for_load_state("networkidle")

        mode_test_context.send_message("My task is to finish the report")
        assert (
            mode_test_context.has_task_preview()
        ), "'My task is to...' should trigger CREATE and show task preview"
        assert (
            not mode_test_context.has_error_message()
        ), "Should not error on task creation"


class TestModeSwitchingEdgeCases:
    """Additional edge cases for mode switching."""

    def test_todo_variations_all_retrieve(
        self, page: Page, streamlit_app, mode_test_context
    ):
        """
        Test todo/to-do/list variations all trigger RETRIEVE.

        These are the patterns that were missing and caused the original bug.
        """
        page.goto(streamlit_app)
        page.wait_for_load_state("networkidle")

        variations = [
            "show my todo",
            "show my to-do",
            "show my todo list",
            "show my to-do list",
            "what's on my list",
            "check my tasks",
        ]

        for query in variations:
            mode_test_context.send_message(query)
            assert (
                mode_test_context.has_task_list()
            ), f"'{query}' should trigger RETRIEVE"
            assert (
                not mode_test_context.has_error_message()
            ), f"'{query}' should not error"

    def test_create_with_task_word_not_confused(
        self, page: Page, streamlit_app, mode_test_context
    ):
        """
        Ensure CREATE mode works even when message contains word 'task'.

        Tests that CREATE patterns have priority over RETRIEVE patterns.
        """
        page.goto(streamlit_app)
        page.wait_for_load_state("networkidle")

        create_commands = [
            "Add task to review document",
            "Create a task to review my paper with a peer",
            "Remind me to task john with the project",
        ]

        for command in create_commands:
            mode_test_context.send_message(command)
            assert (
                mode_test_context.has_task_preview()
            ), f"'{command}' should trigger CREATE even though it contains 'task'"
            assert (
                not mode_test_context.has_error_message()
            ), f"'{command}' should not error"
