"""Pytest fixtures for UI testing with Playwright."""

import contextlib
import socket
import subprocess
import time
from pathlib import Path

import pytest


def find_free_port():
    """Find an available port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="session")
def streamlit_app():
    """
    Start Streamlit app in background for UI testing.

    Yields:
        str: URL of the running Streamlit app
    """
    port = find_free_port()
    app_url = f"http://localhost:{port}"

    # Get project root (two levels up from tests/ui)
    project_root = Path(__file__).parent.parent.parent
    app_path = project_root / "app" / "main.py"

    # Start Streamlit in background using uv run
    # Note: Use headless mode and disable browser auto-open
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--server.address",
            "localhost",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(project_root),
    )

    # Wait for Streamlit to start (check if port is listening)
    max_wait = 60  # seconds - increased for slower startups
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("localhost", port))
                # Connection successful, Streamlit is ready
                print(f"Streamlit connected on port {port}")
                break
        except (TimeoutError, ConnectionRefusedError, OSError):
            time.sleep(1)
    else:
        # Timeout reached - print process output for debugging
        stdout, stderr = process.communicate(timeout=5)
        print(f"STDOUT: {stdout.decode() if stdout else 'None'}")
        print(f"STDERR: {stderr.decode() if stderr else 'None'}")
        process.terminate()
        raise RuntimeError(f"Streamlit app failed to start on port {port} within {max_wait}s")

    # Additional wait for app to fully initialize
    time.sleep(5)
    print(f"Streamlit app ready at {app_url}")

    yield app_url

    # Teardown: kill Streamlit process
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


@pytest.fixture
def mode_test_context(page):
    """
    Context for mode detection tests.

    Provides helper methods for common UI interactions.
    """

    class ModeTestContext:
        def __init__(self, page):
            self.page = page

        def send_message(self, message: str):
            """Send a message through the chat input."""
            # Wait for page to be ready and chat input to reappear
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            time.sleep(1)

            # Scroll to bottom to ensure chat input is in view
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            # Use the working selector from debug test
            chat_input = self.page.locator("[data-testid='stChatInputTextArea']")

            # Wait for it to be visible and enabled - may need to wait for it to reappear after previous message
            try:
                chat_input.wait_for(state="visible", timeout=15000)
            except Exception:
                # If still not visible, try scrolling again and wait
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                chat_input.wait_for(state="visible", timeout=10000)

            time.sleep(1)

            # Clear any existing text, fill, and submit
            chat_input.click()
            chat_input.fill("")
            time.sleep(0.5)
            chat_input.fill(message)
            chat_input.press("Enter")

            # Wait for response - Streamlit needs time to process
            time.sleep(10)
            # Network idle may not trigger, but message should still appear
            with contextlib.suppress(Exception):
                self.page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(2)

        def get_latest_message(self):
            """Get the text of the most recent message."""
            # Wait a moment for message to appear
            time.sleep(1)
            # Get all message containers - try multiple selectors
            messages = self.page.locator("[data-testid='stChatMessage']").all()
            if not messages:
                # Fallback: look for markdown content in chat messages
                messages = self.page.locator(".stChatMessage").all()
            if messages:
                return messages[-1].inner_text()
            # Last resort: get all markdown elements
            markdown_elements = self.page.locator("[data-testid='stMarkdown']").all()
            if markdown_elements:
                return markdown_elements[-1].inner_text()
            return self.page.locator("body").inner_text()

        def has_error_message(self):
            """Check if there's an error message visible."""
            error_indicators = [
                "Unable to understand",
                "error",
                "failed",
                "task_parsing_failed",
            ]
            latest = self.get_latest_message().lower()
            return any(indicator in latest for indicator in error_indicators)

        def has_task_list(self):
            """Check if a task list is displayed."""
            latest = self.get_latest_message().lower()
            # Look for task list indicators or empty state messages
            indicators = [
                "your tasks",
                "don't have any",
                "no tasks",
                "task id:",
                "due:",
                "priority:",
                "you don't have any active tasks",
                "here are your tasks",
            ]
            return any(indicator in latest for indicator in indicators)

        def has_task_preview(self):
            """Check if a task creation preview is displayed."""
            latest = self.get_latest_message().lower()
            # Look for task preview or creation confirmation
            indicators = [
                "task preview",
                "creating task",
                "task created",
                "title:",
                "description:",
                "✅",
                "successfully",
                "view in todoist",
            ]
            return any(indicator in latest for indicator in indicators)

        def has_greeting_response(self):
            """Check if response contains greeting."""
            latest = self.get_latest_message().lower()
            # Look for greeting-like responses from the chat mode
            indicators = [
                "darkwave",
                "task manager",
                "hello",
                "hi",
                "help you",
                "assist",
                "how can i",
                "good morning",
                "good afternoon",
            ]
            return any(indicator in latest for indicator in indicators)

    return ModeTestContext(page)
