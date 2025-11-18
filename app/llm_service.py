"""
LLM service for parsing natural language into structured Todoist tasks.

This module uses Google Gemini via LangChain to extract task information
from user input and convert it to Todoist-compatible task objects.

LLM Note: Prompt engineering is critical here. The system prompt guides
the model to extract specific fields (content, description, priority, etc.)
in a consistent format. Temperature is kept low (0.3) for predictable output.
"""

import structlog
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class TodoistTask(BaseModel):
    """
    Pydantic model for a Todoist task.

    This structure matches the Todoist API v2 schema for task creation.
    The model is used both for LLM output parsing and API request validation.

    LLM Note: Field descriptions are used in the prompt to guide the model
    on what information to extract and in what format.
    """

    content: str = Field(
        description="Task title - concise, actionable description (required)"
    )

    description: str | None = Field(
        default="",
        description="Detailed description with context, steps, or additional information",
    )

    priority: int = Field(
        default=3,
        ge=1,
        le=4,
        description="Priority level: 1 (lowest), 2 (low), 3 (medium/default), 4 (urgent/highest)",
    )

    due_string: str | None = Field(
        default=None,
        description="Natural language due date (e.g., 'tomorrow', 'next Monday', 'Dec 25')",
    )

    labels: list[str] = Field(
        default_factory=list,
        description="List of labels to categorize the task (e.g., ['work', 'urgent', 'calls'])",
    )

    project_id: str | None = Field(
        default=None, description="Project ID to add the task to (if specified)"
    )


class LLMService:
    """
    Service for interacting with Google Gemini LLM to parse task requests.

    Uses structured output parsing to ensure consistent, validated responses.
    """

    def __init__(
        self, api_key: str, model: str = "gemini-2.5-flash", temperature: float = 0.3
    ):
        """
        Initialize LLM service with Google Gemini model.

        Args:
            api_key: Google API key for Gemini access
            model: Gemini model name
            temperature: Sampling temperature (0.0-1.0, lower = more deterministic)

        LLM Note: Low temperature ensures consistent field extraction.
        The model is initialized with system messages converted to human
        messages as required by Gemini's chat format.
        """
        self.model = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
            convert_system_message_to_human=True,
        )

        self.parser = PydanticOutputParser(pydantic_object=TodoistTask)
        self.prompt = self._create_prompt()

        logger.info("llm_service_initialized", model=model, temperature=temperature)

    def _create_prompt(self) -> ChatPromptTemplate:
        """
        Create the system prompt for task parsing.

        Returns:
            Chat prompt template with system instructions and format guidance

        LLM Note: This prompt is the core of the parsing logic. It:
        1. Defines the assistant's role and capabilities
        2. Provides rules for extracting task information
        3. Includes few-shot examples to guide behavior
        4. Embeds the Pydantic schema via format_instructions

        Prompt design choices:
        - Explicit priority mappings (urgent=4, high=2, medium=3, low=1)
        - Natural language due date preservation (let Todoist parse it)
        - Automatic label inference from context
        - Clear handling of missing information (use sensible defaults)
        - Guardrails against creating tasks from greetings/casual conversation (FW-6.1)
        """

        system_message = """You are a task extraction assistant that converts natural language into structured Todoist tasks.

            ROLE: Parse user input and extract task details into a JSON object matching the provided schema.

            IMPORTANT CONTEXT:
            This assistant operates in CREATE mode specifically. The input you receive has already been
            classified as a task creation request (not a greeting or query). Your job is to extract the
            task details from the description provided.

            Do NOT attempt to handle:
            - Greetings (hello, hi, good morning) - these are handled separately
            - Questions about existing tasks - these are handled by retrieval mode
            - Meta questions about capabilities - these are handled by chat mode

            If you receive input that seems like a greeting or question (which should not happen),
            return an error instead of creating a meaningless task.

            RULES:
            1. Extract task title (content): Keep it concise and actionable (5-10 words max)
            2. Generate description: Add helpful context, but only if user provides details
            3. Determine priority based on urgency signals:
            - Priority 4 (urgent/highest): Words like "urgent", "ASAP", "critical", "immediately"
            - Priority 2 (high): Words like "important", "soon", "this week"
            - Priority 3 (medium): Default for most tasks
            - Priority 1 (low): Words like "someday", "whenever", "low priority"
            4. Parse due dates: Preserve natural language ("tomorrow", "next Monday", "Dec 25")
            - Do NOT convert to ISO format; Todoist handles natural language
            5. Infer labels from context:
            - Work-related → ["work"]
            - Personal errands → ["personal", "errands"]
            - Urgent tasks → add "urgent" label
            - Phone calls → ["calls"]
            - Emails → ["email"]
            6. If input contains multiple distinct tasks, extract only the FIRST task
            7. If information is unclear, use sensible defaults (priority 3, no due date, empty description)

            EXAMPLES:

            Input: "Call dentist tomorrow about cleaning appointment"
            Output:
            {{
            "content": "Call dentist about cleaning",
            "description": "Schedule appointment for dental cleaning",
            "priority": 3,
            "due_string": "tomorrow",
            "labels": ["calls", "personal", "health"]
            }}

            Input: "URGENT: Finish project report by Friday"
            Output:
            {{
            "content": "Finish project report",
            "description": "Complete and submit quarterly project report",
            "priority": 4,
            "due_string": "Friday",
            "labels": ["work", "urgent", "reports"]
            }}

            Input: "Buy groceries - milk, bread, eggs"
            Output:
            {{
            "content": "Buy groceries",
            "description": "Items needed: milk, bread, eggs",
            "priority": 3,
            "due_string": null,
            "labels": ["personal", "errands", "shopping"]
            }}

            Input: "Send email to team about meeting next week"
            Output:
            {{
            "content": "Send email to team about meeting",
            "description": "Notify team members about upcoming meeting",
            "priority": 3,
            "due_string": "next week",
            "labels": ["work", "email"]
            }}

            {format_instructions}

            Now parse the following user input:"""

        return ChatPromptTemplate.from_messages(
            [("system", system_message), ("human", "{input}")]
        )

    def parse_task(self, user_input: str) -> TodoistTask:
        """
        Parse natural language input into a structured TodoistTask.

        Args:
            user_input: User's natural language task description

        Returns:
            Validated TodoistTask object ready for API submission

        Raises:
            ValueError: If LLM output cannot be parsed or validated

        Example:
            >>> service = LLMService(api_key="...")
            >>> task = service.parse_task("Call dentist tomorrow")
            >>> task.content
            'Call dentist'
            >>> task.due_string
            'tomorrow'

        LLM Note: The chain executes: prompt -> LLM -> parser -> validated Pydantic model.
        If parsing fails, we raise ValueError with details for user feedback.
        """
        try:
            # Format the prompt with user input and schema instructions
            formatted_prompt = self.prompt.format_messages(
                input=user_input,
                format_instructions=self.parser.get_format_instructions(),
            )

            # Invoke LLM
            logger.debug("invoking_llm", input=user_input)
            response = self.model.invoke(formatted_prompt)

            # Parse and validate response
            # Parse response with output parser
            task = self.parser.parse(response.content)  # type: ignore[arg-type]

            logger.info(
                "task_parsed",
                content=task.content,
                priority=task.priority,
                due_string=task.due_string,
                labels=task.labels,
            )

            # Type check for mypy (runtime validation instead of assert)
            if not isinstance(task, TodoistTask):
                raise ValueError(f"Parser returned unexpected type: {type(task)}")
            return task

        except Exception as e:
            logger.error("task_parsing_failed", error=str(e), input=user_input)
            raise ValueError(
                f"Failed to parse task from input: {str(e)}\n"
                f"Please try rephrasing your request or provide more specific details."
            ) from e

    def parse_multiple_tasks(self, user_input: str) -> list[TodoistTask]:
        """
        Parse input that may contain multiple tasks.

        Args:
            user_input: Natural language input potentially describing multiple tasks

        Returns:
            List of TodoistTask objects

        Note: Currently extracts only the first task as per prompt design.
        This method is a placeholder for future multi-task support.

        LLM Note: Multi-task parsing requires more sophisticated prompting
        and potentially recursive LLM calls. For MVP, we focus on single-task
        extraction with clear user feedback if multiple tasks are detected.
        """
        # For now, just parse as single task
        # Future: Enhance prompt to return List[TodoistTask] when multiple tasks detected
        task = self.parse_task(user_input)
        return [task]
