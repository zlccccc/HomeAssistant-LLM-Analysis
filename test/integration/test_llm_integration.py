"""
LLM Integration Tests

These tests test LLM integration with mocked API calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.source.api_layer.llm_manager import LLMManager


@pytest.mark.integration
class TestLLMIntegration:
    """Integration tests for LLM functionality."""

    @pytest.fixture
    def mock_llm_response(self):
        """Create a mock LLM response."""
        return "好的，我来帮您处理这个请求。"

    @pytest.mark.asyncio
    async def test_llm_manager_api_call(self, mock_llm_response):
        """Test LLM manager API call with mock."""
        with patch("backend.source.api_layer.llm_manager.ChatOpenAI") as mock_chat:
            mock_llm_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.content = mock_llm_response
            mock_llm_instance.invoke.return_value = mock_response
            mock_llm_instance.temperature = 0.7
            mock_chat.return_value = mock_llm_instance

            manager = LLMManager()
            manager.llm = mock_llm_instance

            messages = [{"role": "user", "content": "你好"}]
            result = manager.call_openai_api(messages)

            assert result == mock_llm_response
            assert mock_llm_instance.invoke.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
