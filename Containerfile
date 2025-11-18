# DarkWave Task Manager - Containerfile
# Podman/Docker container for deploying the Streamlit application

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# curl is needed for health checks
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first (for layer caching)
COPY pyproject.toml .
COPY README.md .

# Install dependencies using uv
# uv sync creates a virtual environment and installs all dependencies
RUN uv sync --no-dev

# Copy application code
COPY app/ ./app/
COPY config/ ./config/
COPY .streamlit/ ./.streamlit/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose Streamlit default port
EXPOSE 8501

# Health check to verify Streamlit is running
# Checks the health endpoint every 30 seconds
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run Streamlit application using uv
CMD ["uv", "run", "streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
