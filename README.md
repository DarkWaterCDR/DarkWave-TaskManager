# 🌙 DarkWave Task Manager

An AI-powered natural language interface for Todoist task management, built with Google Gemini LLM and Streamlit.

## Overview

DarkWave Task Manager eliminates the friction of traditional task management by allowing you to interact naturally. The AI understands three conversation modes and routes your requests appropriately.

Bellevue University Capstone Project.  Integrating LLM with Todoist API for natural language task creation.

### Key Features

- 🤖 **AI-Powered Parsing**: Google Gemini LLM understands natural language task descriptions
- 💬 **Conversational Interface**: Chat naturally - greetings, questions, and task creation
- 🔍 **Smart Retrieval**: Query your tasks with natural language ("show tasks due today")
- ✅ **Smart Extraction**: Automatically detects priority, due dates, and relevant labels
- 📋 **Task Preview**: Review extracted details before creation
- 🔐 **Secure**: API keys managed via environment variables
- 🐳 **Containerized**: Easy deployment with Podman/Docker
- 🎨 **Clean UI**: Modern Streamlit interface with branding colors

## Requirements

- Python 3.13+
- Todoist account and API token
- Google AI API key (Gemini access)
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- Podman or Docker (for containerized deployment)

## Quick Start

### 1. Clone and Setup

```powershell
git clone git@github.com:DarkWaterCDR/DarkWave-TaskManager.git
```

```powershell
cd DarkWave-TaskManager
```

### 2. Install uv (recommended)

```powershell
# Install uv if not already installed
# See https://docs.astral.sh/uv/getting-started/installation/
```

### 3. Configure Environment Variables

Copy the example environment file and add your API keys:

```powershell
cp .env.example .env
```

Edit `.env` and add:
```
TODOIST_API_TOKEN=your_todoist_api_token_here
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.3
LOG_LEVEL=INFO
```

**Getting API Keys:**
- **Todoist**: https://todoist.com/app/settings/integrations/developer
- **Google AI**: https://ai.google.dev/

### 4. Run Locally

Install dependencies with uv:
```powershell
uv sync --all-extras
```

Run the application:
```powershell
uv run streamlit run app/main.py
```

Or use traditional pip (not recommended):
```powershell
pip install -e ".[dev]"
streamlit run app/main.py
```

Open your browser to http://localhost:8501

### 5. Run with Container

Build the container image:
```powershell
podman build -t darkwave-taskmgr .
```

Run the container with environment file:
```powershell
podman run -p 8501:8501 --env-file .env darkwave-taskmgr
```

Or pass environment variables directly:
```powershell
podman run -p 8501:8501 `
  -e TODOIST_API_TOKEN=your_token `
  -e GOOGLE_API_KEY=your_key `
  darkwave-taskmgr
```

Access the application at http://localhost:8501

## Usage Examples

DarkWave supports three conversation modes automatically detected from your input:

### 💬 Chat Mode (Conversational)

Ask questions or get help without creating tasks:

- **"Hello"** → Friendly greeting with feature overview
- **"What can you do?"** → Explains capabilities with examples
- **"Good morning"** → Responds with encouragement

### 🔍 Retrieve Mode (Query Tasks)

View your existing tasks with natural language queries:

- **"What tasks do I have?"** → Lists all active tasks
- **"Show tasks due today"** → Filters tasks by due date
- **"List tasks labeled work"** → Filters by label

### ✅ Create Mode (Add Tasks)

Simply describe what you need to do:

- **"Call dentist tomorrow about cleaning"**
  - Creates task with due date "tomorrow" and labels: calls, personal, health

- **"URGENT: Finish project report by Friday"**
  - Creates high-priority task with Friday deadline and labels: work, urgent, reports

- **"Buy groceries - milk, bread, eggs"**
  - Creates task with detailed description and labels: personal, errands
  - Creates task with detailed description of items needed

- **"Send email to team about meeting next week"**
  - Creates task with "next week" due date and work-related labels

## Architecture

```
project three/
├── app/
│   ├── __init__.py
│   ├── main.py              # Streamlit UI
│   ├── llm_service.py       # Gemini LLM integration
│   └── todoist_client.py    # Todoist API client
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration management
├── tests/
│   └── __init__.py
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── .env                     # Environment variables (not in git)
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
└── Containerfile            # Container definition
```

## Development

### Running Tests

#### Unit Tests

Run all unit tests with uv:
```powershell
uv run pytest
```

Run specific test file:
```powershell
uv run pytest tests/test_mode.py -v
```

Run with coverage:
```powershell
uv run pytest --cov=app --cov-report=html
```

**Current Test Coverage:**
- **83 total unit tests** across all modules
- **24 mode detection tests** (`tests/test_mode.py`)
  - 16 core tests (CHAT/CREATE/RETRIEVE classification)
  - 8 edge case tests (todo/list variations, possessive patterns, question forms)

#### Code Quality

Run linting:
```powershell
uv run ruff check .
```

Auto-fix linting issues:
```powershell
uv run ruff check . --fix
```

Format code:
```powershell
uv run ruff format .
```

Type checking:
```powershell
uv run mypy app tests config
```

Pre-commit hooks (run automatically on git commit):
```powershell
uv run pre-commit install  # one-time setup
uv run pre-commit run --all-files  # manual run
```

#### UI Tests (Browser Automation)

UI tests use Playwright to validate mode switching in the actual Streamlit app.

**Setup** (one-time):
```powershell
uv run playwright install chromium
```

**Run UI tests**:
```powershell
# Headless mode (no browser window)
pytest tests/ui/ -v --browser chromium

# Headed mode (see browser)
pytest tests/ui/ -v --browser chromium --headed

# Single scenario
pytest tests/ui/test_mode_switching.py::TestModeSwitchingUI::test_greeting_to_retrieve_to_create -v
```

**UI Test Scenarios** (8 tests):
1. Greeting → Retrieve → Create workflow
2. Query → Greeting → Create workflow
3. Multiple retrieve patterns validation
4. CREATE not triggered by queries
5. Edge case: "my task is to..." handling
6. Todo/to-do/list variation coverage
7. CREATE with task word priority

**Note**: UI tests start Streamlit automatically, take ~1-2 minutes for full suite.

See `docs/MDF-3-UI-TESTING-STATUS.md` for detailed UI testing documentation.

### Mode Detection Testing

Mode detection is critical to routing user intent correctly. Test the current implementation:

```powershell
# Quick validation
python -c "from app.mode import detect_mode; print(detect_mode('Show me what\\'s on my todo list.'))"
# Expected: Mode.RETRIEVE

# Run all mode tests
pytest tests/test_mode.py -v
# Expected: 24/24 passing
```

**Supported Patterns:**
- **CHAT**: Greetings, meta questions about capabilities
- **RETRIEVE**: Task queries with variations (task/todo/to-do/list)
- **CREATE**: Task descriptions, explicit creation commands

See `docs/MODE-DETECTION-FIX-PLAN.md` for pattern details and fix history.

### Code Quality

This project follows best practices:
- Type hints with Pydantic models
- Structured logging with structlog
- Comprehensive error handling
- Separation of concerns (UI, business logic, API clients)

### Adding Features

The modular architecture makes it easy to extend:
- **New LLM capabilities**: Modify `app/llm_service.py` and update prompts
- **Additional Todoist operations**: Extend `app/todoist_client.py`
- **UI enhancements**: Update `app/main.py` Streamlit components

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TODOIST_API_TOKEN` | Yes | - | Todoist API bearer token |
| `GOOGLE_API_KEY` | Yes | - | Google AI API key for Gemini |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model name |
| `GEMINI_TEMPERATURE` | No | `0.3` | LLM temperature (0.0-1.0) |
| `LOG_LEVEL` | No | `INFO` | Logging level |

### Streamlit Configuration

Customize the UI by editing `.streamlit/config.toml`:
- Theme colors
- Server settings
- Browser behavior

## Security

- **API Keys**: Never commit `.env` file (already in `.gitignore`)
- **Container Secrets**: Use `podman secret` for production deployments
- **Non-root User**: Container runs as non-root user `appuser`
- **Minimal Dependencies**: Only essential packages installed

## Troubleshooting

### "Missing required environment variable"
Ensure `.env` file exists with all required variables.

### "Invalid Todoist API token"
Verify your token at https://todoist.com/app/settings/integrations/developer

### "Gemini API error"
Check your Google AI API key and quota at https://ai.google.dev/

### Container won't start
Check logs: `podman logs <container-id>`

## License

This project is for educational purposes as part of DSC 680 - Applied Data Science.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Google Gemini](https://ai.google.dev/gemini-api)
- Integrated with [Todoist](https://todoist.com/)
- LangChain framework for LLM orchestration

---

**DarkWave Task Manager** - Transform thoughts into organized tasks. 🌙
