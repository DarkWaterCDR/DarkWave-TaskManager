"""
Unit tests for configuration module.

Tests environment variable loading, validation, and error handling.
"""

import os
from unittest.mock import patch

import pytest

from config.settings import ConfigurationError, Settings


class TestSettings:
    """Test suite for Settings class."""

    @patch.dict(
        os.environ,
        {
            "TODOIST_API_TOKEN": "test_todoist_token_12345",
            "GOOGLE_API_KEY": "test_google_key_12345",
        },
    )
    def test_settings_initialization_success(self):
        """Test successful settings initialization with valid env vars."""
        settings = Settings()

        assert settings.todoist_api_token == "test_todoist_token_12345"
        assert settings.google_api_key == "test_google_key_12345"
        assert settings.gemini_model == "gemini-2.5-flash"
        assert settings.gemini_temperature == 0.3
        assert settings.log_level == "INFO"

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_todoist_token(self):
        """Test that missing TODOIST_API_TOKEN raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            Settings()

        assert "TODOIST_API_TOKEN" in str(exc_info.value)

    @patch.dict(os.environ, {"TODOIST_API_TOKEN": "test_token"}, clear=True)
    def test_missing_google_key(self):
        """Test that missing GOOGLE_API_KEY raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            Settings()

        assert "GOOGLE_API_KEY" in str(exc_info.value)

    @patch.dict(
        os.environ,
        {
            "TODOIST_API_TOKEN": "test_todoist_token_12345",
            "GOOGLE_API_KEY": "test_google_key_12345",
            "GEMINI_MODEL": "gemini-pro",
            "GEMINI_TEMPERATURE": "0.7",
            "LOG_LEVEL": "DEBUG",
        },
    )
    def test_custom_settings(self):
        """Test that custom environment variables are properly loaded."""
        settings = Settings()

        assert settings.gemini_model == "gemini-pro"
        assert settings.gemini_temperature == 0.7
        assert settings.log_level == "DEBUG"

    @patch.dict(
        os.environ,
        {"TODOIST_API_TOKEN": "short", "GOOGLE_API_KEY": "test_google_key_12345"},
    )
    def test_validate_short_todoist_token(self):
        """Test validation fails for suspiciously short Todoist token."""
        settings = Settings()

        with pytest.raises(ConfigurationError) as exc_info:
            settings.validate()

        assert "TODOIST_API_TOKEN" in str(exc_info.value)
        assert "too short" in str(exc_info.value)

    @patch.dict(
        os.environ,
        {"TODOIST_API_TOKEN": "test_todoist_token_12345", "GOOGLE_API_KEY": "short"},
    )
    def test_validate_short_google_key(self):
        """Test validation fails for suspiciously short Google API key."""
        settings = Settings()

        with pytest.raises(ConfigurationError) as exc_info:
            settings.validate()

        assert "GOOGLE_API_KEY" in str(exc_info.value)
        assert "too short" in str(exc_info.value)

    @patch.dict(
        os.environ,
        {
            "TODOIST_API_TOKEN": "test_todoist_token_12345",
            "GOOGLE_API_KEY": "test_google_key_12345",
            "GEMINI_TEMPERATURE": "1.5",
        },
    )
    def test_validate_temperature_out_of_range(self):
        """Test validation fails for temperature outside 0.0-1.0 range."""
        settings = Settings()

        with pytest.raises(ConfigurationError) as exc_info:
            settings.validate()

        assert "GEMINI_TEMPERATURE" in str(exc_info.value)
        assert "0.0 and 1.0" in str(exc_info.value)

    @patch.dict(
        os.environ,
        {
            "TODOIST_API_TOKEN": "test_todoist_token_12345",
            "GOOGLE_API_KEY": "test_google_key_12345",
        },
    )
    def test_validate_success(self):
        """Test successful validation with valid settings."""
        settings = Settings()

        assert settings.validate() is True
