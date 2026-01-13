"""
LLMManager Test Suite

Tests the LLM API integration module.
Run with: uv run pytest test/test_llm_manager.py -v
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from backend.source.api_layer.llm_manager import LLMManager


class TestLLMManager:
    """Test cases for LLMManager class."""

    @pytest.fixture
    def manager(self, mock_llm_config):
        """Create an LLMManager instance with mocked config."""
        with patch.dict(os.environ, mock_llm_config, clear=False):
            manager = LLMManager()
            yield manager

    # ============== Initialization Tests ==============

    def test_initialization(self, manager, mock_llm_config):
        """Test manager initialization."""
        assert manager.api_key == mock_llm_config["QWEN_API_KEY"]
        assert manager.api_base == mock_llm_config["QWEN_API_BASE"]
        assert manager.model_name == mock_llm_config["QWEN_MODEL"]

    def test_initialization_with_defaults(self):
        """Test manager initialization with default values."""
        with patch.dict(os.environ, {}, clear=True):
            manager = LLMManager()
            # Default model from llm_manager.py is gpt-3.5-turbo
            assert manager.model_name == "gpt-3.5-turbo"

    def test_initialization_missing_api_key(self):
        """Test manager initialization with missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            manager = LLMManager()
            assert manager.api_key is None

    # ============== get_chat_model Tests ==============

    def test_get_chat_model(self, manager):
        """Test getting chat model instance."""
        model = manager.get_chat_model()
        assert model is not None

    # ============== call_openai_api Tests ==============
    # Note: These tests use mocking at the ChatOpenAI class level
    # because invoke is a bound method that's difficult to patch on Pydantic models

    @patch("backend.source.api_layer.llm_manager.ChatOpenAI")
    def test_call_openai_api_success(self, mock_chat, mock_llm_config):
        """Test successful OpenAI API call."""
        # Set up the mock to return a response with content attribute
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "您好！这是测试回复。"
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm_instance.temperature = 0.7
        mock_llm_instance.max_tokens = 2048
        mock_chat.return_value = mock_llm_instance

        with patch.dict(os.environ, mock_llm_config, clear=False):
            manager = LLMManager()
            # Replace the llm with our mock
            manager.llm = mock_llm_instance

            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
            ]
            result = manager.call_openai_api(messages)

            assert "测试" in result or "Hello" in result

    @patch("backend.source.api_layer.llm_manager.ChatOpenAI")
    def test_call_openai_api_with_different_temperature(self, mock_chat, mock_llm_config):
        """Test API call with custom temperature."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Response"
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm_instance.temperature = 0.7  # Different from requested
        mock_llm_instance.max_tokens = 2048
        mock_chat.return_value = mock_llm_instance

        with patch.dict(os.environ, mock_llm_config, clear=False):
            manager = LLMManager()
            manager.llm = mock_llm_instance

            messages = [{"role": "user", "content": "Hello"}]
            result = manager.call_openai_api(messages, temperature=0.3)

            assert result is not None

    @patch("backend.source.api_layer.llm_manager.ChatOpenAI")
    def test_call_openai_api_empty_messages(self, mock_chat, mock_llm_config):
        """Test API call with empty message list."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = ""
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm_instance.temperature = 0.7
        mock_llm_instance.max_tokens = 2048
        mock_chat.return_value = mock_llm_instance

        with patch.dict(os.environ, mock_llm_config, clear=False):
            manager = LLMManager()
            manager.llm = mock_llm_instance

            result = manager.call_openai_api([])

            # Should handle empty messages gracefully
            assert result == ""

    @patch("backend.source.api_layer.llm_manager.ChatOpenAI")
    def test_call_openai_api_exception(self, mock_chat, mock_llm_config):
        """Test API call with exception."""
        mock_llm_instance = MagicMock()
        mock_llm_instance.temperature = 0.7
        mock_llm_instance.max_tokens = 2048
        mock_llm_instance.invoke.side_effect = Exception("API connection failed")
        mock_chat.return_value = mock_llm_instance

        with patch.dict(os.environ, mock_llm_config, clear=False):
            manager = LLMManager()
            manager.llm = mock_llm_instance

            messages = [{"role": "user", "content": "Hello"}]
            result = manager.call_openai_api(messages)

            # Should return error message, not raise
            assert "失败" in result or "API" in result or "Exception" in result

    @patch("backend.source.api_layer.llm_manager.ChatOpenAI")
    def test_call_openai_api_with_system_prompt(self, mock_chat, mock_llm_config):
        """Test API call with system prompt."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Weather is sunny"
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm_instance.temperature = 0.7
        mock_llm_instance.max_tokens = 2048
        mock_chat.return_value = mock_llm_instance

        with patch.dict(os.environ, mock_llm_config, clear=False):
            manager = LLMManager()
            manager.llm = mock_llm_instance

            messages = [
                {"role": "system", "content": "You are a weather assistant."},
                {"role": "user", "content": "What's the weather?"},
            ]
            result = manager.call_openai_api(messages)

            assert result is not None

    # ============== generate_summary Tests ==============

    @patch("backend.source.api_layer.llm_manager.ChatOpenAI")
    def test_generate_summary(self, mock_chat, mock_llm_config):
        """Test text summarization."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Summary: This is a summary"
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm_instance.temperature = 0.7
        mock_llm_instance.max_tokens = 2048
        mock_chat.return_value = mock_llm_instance

        with patch.dict(os.environ, mock_llm_config, clear=False):
            manager = LLMManager()
            manager.llm = mock_llm_instance

            text = "This is a long text that needs to be summarized."
            result = manager.generate_summary(text, max_length=100)

            assert result is not None

    # ============== analyze_content Tests ==============

    @patch("backend.source.api_layer.llm_manager.ChatOpenAI")
    def test_analyze_content(self, mock_chat, mock_llm_config):
        """Test content analysis."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Temperature is 25 degrees"
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm_instance.temperature = 0.7
        mock_llm_instance.max_tokens = 2048
        mock_chat.return_value = mock_llm_instance

        with patch.dict(os.environ, mock_llm_config, clear=False):
            manager = LLMManager()
            manager.llm = mock_llm_instance

            content = "The temperature is 25 degrees"
            task = "Extract the temperature value"
            result = manager.analyze_content(content, task)

            assert result is not None


class TestLLMManagerUnit:
    """Unit tests for LLMManager specific functionality."""

    def test_global_instance_exists(self):
        """Test that global llm_manager instance exists."""
        from backend.source.api_layer.llm_manager import get_llm_manager

        manager = get_llm_manager()
        assert manager is not None
        assert isinstance(manager, LLMManager)


@pytest.mark.requires_llm
class TestLLMManagerIntegration:
    """Integration tests that require actual LLM API connection."""

    @pytest.fixture
    def live_manager(self):
        """Create a manager with real config."""
        manager = LLMManager()
        yield manager

    @pytest.mark.slow
    def test_real_api_call(self, live_manager):
        """Test real API call to LLM service."""
        # This test only runs if API keys are configured
        if os.getenv("QWEN_API_KEY"):
            messages = [{"role": "user", "content": "Say 'Hello, world!' in Chinese."}]
            result = live_manager.call_openai_api(messages)

            assert result is not None
            assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
