"""
DarkWave Task Manager - Streamlit UI

A natural language interface for Todoist task management using Google Gemini LLM.

This module provides the user interface layer, delegating business logic
to the LLM service and Todoist client modules.

LLM Note: UI code is kept separate from business logic for testability.
Session state manages chat history and API client instances.
"""

import sys
from pathlib import Path

# Add project root to Python path for imports to work
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import re

import streamlit as st
import structlog

from app.llm_service import LLMService
from app.mode import Mode, detect_mode
from app.task_formatter import format_task_list
from app.todoist_client import AuthenticationError, TodoistClient, TodoistError
from app.todoist_links import build_task_url
from config.settings import ConfigurationError, settings

# Configure logging
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(settings().log_level),
)

logger = structlog.get_logger()

# FW-1.2: LOGGING COVERAGE VERIFICATION
# Current logging hooks cover the complete task lifecycle:
# - services_initialized: When LLM and Todoist clients are ready
# - mode_detected: When mode classifier determines conversation intent (FW-3.3)
# - chat_response_sent: When CHAT mode sends conversational response (FW-5.1)
# - retrieval_started: When RETRIEVE mode begins task query (FW-4.3)
# - retrieval_completed: When RETRIEVE mode completes successfully (FW-4.3)
# - task_parsed: When LLM successfully extracts task structure (llm_service.py)
# - task_created: When Todoist API confirms task creation (todoist_client.py)
# - task_created_successfully: Final confirmation in UI flow (main.py)
# - task_parsing_failed: When LLM cannot extract valid task structure
# - authentication_failed: When Todoist API rejects credentials
# - todoist_error: When Todoist API returns other errors
# - unexpected_error: Catch-all for unforeseen exceptions
# - tasks_retrieved: When retrieving task lists (todoist_client.py)


def initialize_services():
    """
    Initialize LLM and Todoist services.

    Returns:
        Tuple of (LLMService, TodoistClient) or raises error

    LLM Note: Services are initialized once and stored in session state
    to avoid recreating API clients on every rerun.
    """
    try:
        # Validate configuration first
        settings().validate()

        # Initialize services
        llm_service = LLMService(
            api_key=settings().google_api_key,
            model=settings().gemini_model,
            temperature=settings().gemini_temperature,
        )

        todoist_client = TodoistClient(api_token=settings().todoist_api_token)

        logger.info("services_initialized")
        return llm_service, todoist_client

    except ConfigurationError as e:
        st.error(f"⚙️ **Configuration Error**\n\n{str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"❌ **Initialization Error**\n\n{str(e)}")
        logger.exception("service_initialization_failed")
        st.stop()


def display_task_preview(task):
    """
    Display a preview of the parsed task before creation.

    Args:
        task: TodoistTask object

    LLM Note: Preview allows users to verify the LLM extraction
    before committing to task creation in Todoist.
    """
    st.markdown("### 📋 Task Preview")

    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**Title:** {task.content}")
            if task.description:
                st.markdown(f"**Description:** {task.description}")

        with col2:
            # Priority badge
            priority_labels = {
                4: ("🔴 Urgent", "red"),
                2: ("🟡 High", "orange"),
                3: ("🟢 Medium", "green"),
                1: ("⚪ Low", "gray"),
            }
            label, color = priority_labels.get(task.priority, ("Unknown", "gray"))
            st.markdown(f"**Priority:** {label}")

            if task.due_string:
                st.markdown(f"**Due:** {task.due_string}")

        if task.labels:
            st.markdown(f"**Labels:** {', '.join(task.labels)}")


def generate_chat_response(user_message: str) -> str:
    """
    Generate conversational response for CHAT mode.

    Handles greetings and capability questions without creating tasks.

    Args:
        user_message: User's conversational input

    Returns:
        Friendly response string

    LLM Note: This is template-based (no LLM needed) for fast, deterministic
    responses to common conversational patterns.
    """
    message_lower = user_message.lower().strip()

    # Greeting responses
    if re.search(r"^(hi|hello|hey|greetings)[\s!?.]*$", message_lower):
        return (
            "👋 Hello! I'm your DarkWave Task Manager assistant.\n\n"
            "I can help you:\n"
            "- **Create tasks**: Just describe what you need to do\n"
            '- **View tasks**: Ask "what tasks do I have?" or "show tasks due today"\n'
            "- **Organize**: I'll auto-label tasks and set priorities\n\n"
            "What would you like to do?"
        )

    if re.search(r"^(good morning|good afternoon|good evening)[\s!?.]*$", message_lower):
        return (
            "Good day! 🌟 Ready to tackle your tasks?\n\n"
            "Tell me what you need to get done, or ask to see your current tasks."
        )

    # Capability questions
    if re.search(r"\b(what can you do|how do you work|help)\b", message_lower):
        return (
            "**I'm here to make task management effortless!** ✨\n\n"
            "**Create Tasks**\n"
            "Just tell me what you need to do:\n"
            '- "Buy groceries tomorrow"\n'
            '- "Call dentist at 2pm"\n'
            '- "Review project proposal"\n\n'
            "**View Tasks**\n"
            "Ask me to show your tasks:\n"
            '- "What tasks do I have?"\n'
            '- "Show tasks due today"\n'
            '- "List tasks labeled work"\n\n'
            "I'll automatically infer priorities, due dates, and labels to keep you organized!"
        )

    # Who/what are you
    if re.search(r"\b(who are you|what are you)\b", message_lower):
        return (
            "I'm **DarkWave Task Manager** 🌙, your AI-powered task assistant!\n\n"
            "I use Google's Gemini AI to understand your natural language and "
            "create perfectly organized tasks in Todoist.\n\n"
            "Just tell me what you need to do, and I'll handle the rest."
        )

    # Default friendly response
    return (
        "I'm not sure I understand. 🤔\n\n"
        "I can help you **create tasks** or **view your existing tasks**.\n\n"
        "Try:\n"
        '- Describing a task: "Finish report by Friday"\n'
        '- Asking about tasks: "What tasks do I have?"'
    )


def handle_retrieve_mode(user_message: str, todoist_client: TodoistClient):
    """
    Handle RETRIEVE mode - fetch and display existing tasks.

    Implements UC-R1, UC-R2, UC-R3 from DETAILED-PLAN-FUNCTIONAL.md:
    - UC-R1: List all active tasks
    - UC-R2: List tasks due today
    - UC-R3: List tasks by single label

    Args:
        user_message: User's natural language query
        todoist_client: Todoist client instance

    LLM Note: This function extracts intent from the query using simple
    pattern matching (no LLM needed for retrieval).
    """
    logger.info("retrieval_started", query=user_message[:50])

    try:
        # Parse user intent from message
        message_lower = user_message.lower()

        # Determine filter parameters
        due_date = None
        label = None
        filter_desc = None

        # UC-R2: Check for "due today" pattern
        if re.search(r"\b(due\s+)?today\b", message_lower):
            due_date = "today"
            filter_desc = "due today"

        # UC-R3: Check for label pattern (simple extraction)
        label_match = re.search(
            r'\b(?:labeled?|tagged?|with\s+label)\s+["\']?(\w+)["\']?', message_lower
        )
        if label_match:
            label = label_match.group(1)
            filter_desc = f"labeled '{label}'"

        # Fetch tasks with filters
        tasks = todoist_client.get_tasks(due_date=due_date, label=label)

        # Format and display
        formatted_tasks = format_task_list(tasks, filter_description=filter_desc)
        st.markdown(formatted_tasks)

        # Add to chat history
        st.session_state.messages.append({"role": "assistant", "content": formatted_tasks})

        logger.info("retrieval_completed", task_count=len(tasks), due_date=due_date, label=label)

    except AuthenticationError as e:
        error_msg = f"🔑 **Authentication Error**\n\n{str(e)}"
        st.error(error_msg)
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        logger.error("authentication_failed", error=str(e))

    except TodoistError as e:
        error_msg = f"⚠️ **Todoist Error**\n\n{str(e)}"
        st.error(error_msg)
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        logger.error("todoist_error", error=str(e))

    except Exception as e:
        error_msg = f"❌ **Unexpected Error**\n\n{str(e)}"
        st.error(error_msg)
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        logger.exception("unexpected_error", error=str(e))


def handle_user_input(user_message: str, llm_service: LLMService, todoist_client: TodoistClient):
    """
    Process user input and create task in Todoist.

    Args:
        user_message: User's natural language task description
        llm_service: LLM service instance
        todoist_client: Todoist client instance

    LLM Note: This function orchestrates the full workflow:
    1. Parse natural language with LLM
    2. Display preview for user confirmation
    3. Create task in Todoist
    4. Show success/error feedback

    Error handling provides actionable feedback at each step.
    """
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_message})

    # Display user message
    with st.chat_message("user"):
        st.markdown(user_message)

    # FW-3.3: Detect conversation mode
    detected_mode = detect_mode(user_message)
    logger.info("mode_detected", mode=detected_mode.value, message_preview=user_message[:50])

    # FW-4.3: Route RETRIEVE mode to retrieval handler
    if detected_mode == Mode.RETRIEVE:
        with st.chat_message("assistant"), st.spinner("🔍 Fetching your tasks..."):
            handle_retrieve_mode(user_message, todoist_client)
        return  # Exit early, retrieval complete

    # FW-5.1: Handle CHAT mode with conversational responses
    if detected_mode == Mode.CHAT:
        with st.chat_message("assistant"):
            # Generate appropriate response based on message
            response = generate_chat_response(user_message)
            st.markdown(response)

            # Add to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})

            logger.info("chat_response_sent", mode="chat")
        return  # Exit early, chat complete

    # CREATE mode: Process with LLM and create task
    with st.chat_message("assistant"), st.spinner("🤔 Understanding your request..."):
        try:
            # Parse task with LLM
            task = llm_service.parse_task(user_message)

            # Display preview
            display_task_preview(task)

            # Create task in Todoist
            with st.spinner("📝 Creating task in Todoist..."):
                # Convert Pydantic model to dict for API
                task_data = task.model_dump(exclude_none=True)
                created_task = todoist_client.create_task(task_data)

                # Success message
                success_msg = "✅ **Task created successfully!**\n\n"
                success_msg += f"Task ID: `{created_task['id']}`\n\n"

                # Add "View in Todoist" link if we can build it
                task_url = build_task_url(created_task)
                if task_url:
                    success_msg += f"[View in Todoist]({task_url})"
                else:
                    success_msg += "_Note: Unable to generate Todoist link (see logs)_"

                st.success(success_msg)

                # Log to chat history
                st.session_state.messages.append({"role": "assistant", "content": success_msg})

                logger.info(
                    "task_created_successfully",
                    task_id=created_task["id"],
                    content=created_task["content"],
                )

        except ValueError as e:
            # LLM parsing error
            error_msg = f"❌ **Unable to understand your request**\n\n{str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            logger.warning("task_parsing_failed", error=str(e))

        except AuthenticationError as e:
            # API authentication error
            error_msg = f"🔑 **Authentication Error**\n\n{str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            logger.error("authentication_failed", error=str(e))

        except TodoistError as e:
            # Todoist API error
            error_msg = f"⚠️ **Todoist Error**\n\n{str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            logger.error("todoist_error", error=str(e))

        except Exception as e:
            # Unexpected error
            error_msg = (
                f"💥 **Unexpected Error**\n\n{str(e)}\n\nPlease try again or check the logs."
            )
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            logger.exception("unexpected_error")


def main():
    """
    Main Streamlit application entry point.

    LLM Note: Streamlit apps are scripts that rerun on every interaction.
    Session state persists data across reruns. We store:
    - messages: Chat history
    - services_initialized: Flag to avoid re-initializing services
    - llm_service, todoist_client: API client instances
    """

    # Page configuration
    st.set_page_config(
        page_title="DarkWave Task Manager",
        page_icon="🌙",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Header
    st.title("🌙 DarkWave Task Manager")
    st.markdown(
        "Transform your thoughts into organized tasks using natural language. "
        "Powered by AI and Todoist."
    )

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        st.markdown(f"**LLM Model:** {settings().gemini_model}")
        st.markdown(f"**Temperature:** {settings().gemini_temperature}")

        st.markdown("---")

        st.header("📖 How to Use")
        st.markdown(
            """
        1. **Describe your task** in natural language
        2. **Review the preview** to verify details
        3. **Task is created** automatically in Todoist

        **Examples:**
        - "Call dentist tomorrow about cleaning"
        - "URGENT: Finish project report by Friday"
        - "Buy groceries - milk, bread, eggs"
        - "Send email to team about meeting next week"
        """
        )

        st.markdown("---")

        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "services_initialized" not in st.session_state:
        llm_service, todoist_client = initialize_services()
        st.session_state.llm_service = llm_service
        st.session_state.todoist_client = todoist_client
        st.session_state.services_initialized = True

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Describe your task in natural language..."):
        handle_user_input(prompt, st.session_state.llm_service, st.session_state.todoist_client)


if __name__ == "__main__":
    main()
