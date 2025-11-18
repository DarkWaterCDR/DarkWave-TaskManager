"""
Configuration management for DarkWave Task Manager.

This module handles environment variable loading and validation,
providing clear error messages when required configuration is missing.
LLM Note: Configuration is centralized here to avoid scattered env var access.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""

    pass


class Settings:
    """
    Application settings loaded from environment variables.

    Required environment variables:
    - TODOIST_API_TOKEN: Bearer token for Todoist API authentication
    - GOOGLE_API_KEY: API key for Google Gemini LLM

    Optional environment variables:
    - GEMINI_MODEL: Model name (default: gemini-2.5-flash)
    - GEMINI_TEMPERATURE: Temperature for LLM responses (default: 0.3)
    - LOG_LEVEL: Logging level (default: INFO)
    """

    def __init__(self):
        """
        Initialize settings and validate required configuration.

        Raises:
            ConfigurationError: If required environment variables are missing
        """
        self.todoist_api_token = self._get_required_env("TODOIST_API_TOKEN")
        self.google_api_key = self._get_required_env("GOOGLE_API_KEY")

        # Optional settings with defaults
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.gemini_temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.3"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

    def _get_required_env(self, key: str) -> str:
        """
        Retrieve a required environment variable.

        Args:
            key: Environment variable name

        Returns:
            Environment variable value

        Raises:
            ConfigurationError: If environment variable is not set
        """
        value = os.getenv(key)
        if not value:
            raise ConfigurationError(
                f"Missing required environment variable: {key}\n"
                f"Please set {key} in your .env file or environment.\n"
                f"See .env.example for reference."
            )
        return value

    def validate(self) -> bool:
        """
        Validate that all configuration is properly set.

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate API token format (basic check)
        if len(self.todoist_api_token) < 20:
            raise ConfigurationError("TODOIST_API_TOKEN appears to be invalid (too short)")

        if len(self.google_api_key) < 20:
            raise ConfigurationError("GOOGLE_API_KEY appears to be invalid (too short)")

        # Validate temperature range
        if not 0.0 <= self.gemini_temperature <= 1.0:
            raise ConfigurationError(
                f"GEMINI_TEMPERATURE must be between 0.0 and 1.0, got {self.gemini_temperature}"
            )

        return True


def get_settings() -> Settings:
    """
    Get or create the global settings instance.

    Returns:
        Settings instance

    LLM Note: This function allows lazy initialization of settings,
    which is useful for testing where we may not have env vars set.
    """
    return Settings()


# Global settings instance - will be initialized on first access
# LLM Note: Import get_settings() function to access configuration throughout the app
_settings: Settings | None = None


def settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
