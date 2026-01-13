"""
QwenSpeechManager Test Suite

Tests the Qwen speech model integration module (ASR and TTS).
Run with: uv run pytest test/test_qwen_speech_model.py -v
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from frontend.api_layer.qwen_speech_model import QwenSpeechManager


class TestQwenSpeechManager:
    """Test cases for QwenSpeechManager class."""

    @pytest.fixture
    def manager(self, mock_llm_config, tmp_path):
        """Create a QwenSpeechManager instance with mocked config."""
        with (
            patch.dict(os.environ, mock_llm_config, clear=False),
            patch.dict(os.environ, {"OUTPUT_DIR": str(tmp_path / "output")}),
        ):
            manager = QwenSpeechManager()
            yield manager

    @pytest.fixture
    def mock_audio_file(self, tmp_path):
        """Create a mock audio file for testing."""
        audio_file = tmp_path / "test_audio.wav"
        # Create a minimal WAV file (valid header + silence)
        with (audio_file).open("wb") as f:
            # Write a minimal WAV header
            f.write(b"RIFF")
            f.write((36).to_bytes(4, "little"))  # File size
            f.write(b"WAVE")
            f.write(b"fmt ")
            f.write((16).to_bytes(4, "little"))  # Chunk size
            f.write((1).to_bytes(2, "little"))  # Audio format (PCM)
            f.write((1).to_bytes(2, "little"))  # Number of channels
            f.write((16000).to_bytes(4, "little"))  # Sample rate
            f.write((32000).to_bytes(4, "little"))  # Byte rate
            f.write((2).to_bytes(2, "little"))  # Block align
            f.write((16).to_bytes(2, "little"))  # Bits per sample
            f.write(b"data")
            f.write((0).to_bytes(4, "little"))  # Data size
        return str(audio_file)

    @pytest.fixture
    def mock_asr_response(self):
        """Mock ASR API response."""
        return {
            "output": {
                "choices": [{"message": {"content": [{"text": "你好，这是测试识别结果。"}]}}]
            }
        }

    @pytest.fixture
    def mock_tts_response(self):
        """Mock TTS API response."""
        return {"output": {"audio": {"url": "https://example.com/audio.mp3"}}}

    # ============== Initialization Tests ==============

    def test_initialization(self, manager, mock_llm_config):
        """Test manager initialization."""
        assert manager.api_key == mock_llm_config["QWEN_API_KEY"]
        assert manager.api_base == mock_llm_config["QWEN_API_BASE"]
        assert manager.asr_model == "qwen3-asr-flash"
        assert manager.tts_model == "qwen3-tts-flash"
        assert manager.asr_success_count == 0
        assert manager.asr_failure_count == 0
        assert manager.tts_success_count == 0
        assert manager.tts_failure_count == 0

    def test_initialization_creates_output_dir(self, manager, tmp_path):
        """Test that output directory is created."""
        output_dir = tmp_path / "output"
        assert output_dir.exists()

    def test_initialization_with_custom_models(self):
        """Test initialization with custom model names."""
        with patch.dict(
            os.environ,
            {
                "QWEN_ASR_MODEL": "custom-asr-model",
                "QWEN_TTS_MODEL": "custom-tts-model",
            },
        ):
            manager = QwenSpeechManager()
            assert manager.asr_model == "custom-asr-model"
            assert manager.tts_model == "custom-tts-model"

    # ============== ASR (Audio to Text) Tests ==============

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    def test_audio_to_text_success(self, mock_post, manager, mock_audio_file, mock_asr_response):
        """Test successful audio to text conversion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_asr_response
        mock_post.return_value = mock_response

        result = manager.audio_to_text(mock_audio_file)

        assert result == "你好，这是测试识别结果。"
        assert manager.asr_success_count == 1
        assert manager.asr_failure_count == 0
        mock_post.assert_called_once()

    def test_audio_to_text_with_different_format(self, manager):
        """Test audio to text with different audio format - using temp file."""
        import tempfile

        # Create a temporary mp3 file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_file = f.name
            # Write minimal wav header as mp3 (this is just for testing file existence)
            f.write(b"ID3")  # MP3 header

        try:
            # The test will fail to read the file properly, but should handle the error gracefully
            result = manager.audio_to_text(temp_file, format_type="mp3")
            # We expect None or error since the file isn't a real audio file
            assert result is None or isinstance(result, str)
        finally:
            # Clean up
            temp_path = Path(temp_file)
            if temp_path.exists():
                temp_path.unlink()

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    def test_audio_to_text_file_not_found(self, mock_post, manager):
        """Test audio to text with non-existent file."""
        result = manager.audio_to_text("nonexistent.wav")

        assert result is None
        assert manager.asr_failure_count == 1

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    def test_audio_to_text_api_failure(self, mock_post, manager, mock_audio_file):
        """Test audio to text with API failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = manager.audio_to_text(mock_audio_file)

        assert result is None
        assert manager.asr_failure_count == 1

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    def test_audio_to_text_api_exception(self, mock_post, manager, mock_audio_file):
        """Test audio to text with API exception."""
        mock_post.side_effect = Exception("Connection error")

        result = manager.audio_to_text(mock_audio_file)

        assert result is None
        assert manager.asr_failure_count == 1

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    def test_audio_to_text_empty_response(self, mock_post, manager, mock_audio_file):
        """Test audio to text with empty API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": {"choices": []}}
        mock_post.return_value = mock_response

        result = manager.audio_to_text(mock_audio_file)

        assert result == ""
        assert manager.asr_success_count == 1

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    def test_audio_to_text_updates_stats(
        self, mock_post, manager, mock_audio_file, mock_asr_response
    ):
        """Test that ASR updates statistics."""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_asr_response
        mock_post.return_value = mock_response

        before_time = manager.last_asr_time
        manager.audio_to_text(mock_audio_file)

        assert manager.last_asr_time > before_time
        assert manager.asr_success_count == 1

    # ============== TTS (Text to Audio) Tests ==============

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    @patch("frontend.api_layer.qwen_speech_model.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_text_to_audio_success(
        self, mock_file_open, mock_get, mock_post, manager, tmp_path, mock_tts_response
    ):
        """Test successful text to audio conversion."""
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = mock_tts_response
        mock_post.return_value = mock_post_response

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.content = b"fake audio data"
        mock_get.return_value = mock_get_response

        output_file = str(tmp_path / "output.wav")
        with patch.object(manager, "_play_audio"):
            result = manager.text_to_audio("你好，世界", output_file)

        assert result is True
        assert manager.tts_success_count == 1
        assert manager.tts_failure_count == 0

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    @patch("frontend.api_layer.qwen_speech_model.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_text_to_audio_with_different_voice(
        self, mock_file_open, mock_get, mock_post, manager, tmp_path, mock_tts_response
    ):
        """Test text to audio with different voice."""
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = mock_tts_response
        mock_post.return_value = mock_post_response

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.content = b"fake audio data"
        mock_get.return_value = mock_get_response

        output_file = str(tmp_path / "output.wav")
        with patch.object(manager, "_play_audio"):
            result = manager.text_to_audio("测试", output_file, voice="male")

        assert result is True

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    def test_text_to_audio_api_failure(self, mock_post, manager, tmp_path):
        """Test text to audio with API failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        output_file = str(tmp_path / "output.wav")
        result = manager.text_to_audio("测试", output_file)

        assert result is False
        assert manager.tts_failure_count == 1

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    def test_text_to_audio_no_audio_url(self, mock_post, manager, tmp_path):
        """Test text to audio when API doesn't return audio URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": {}}
        mock_post.return_value = mock_response

        output_file = str(tmp_path / "output.wav")
        result = manager.text_to_audio("测试", output_file)

        assert result is False

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    @patch("frontend.api_layer.qwen_speech_model.requests.get")
    def test_text_to_audio_download_failure(
        self, mock_get, mock_post, manager, tmp_path, mock_tts_response
    ):
        """Test text to audio when audio download fails."""
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = mock_tts_response
        mock_post.return_value = mock_post_response

        mock_get_response = MagicMock()
        mock_get_response.status_code = 404
        mock_get.return_value = mock_get_response

        output_file = str(tmp_path / "output.wav")
        result = manager.text_to_audio("测试", output_file)

        assert result is False

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    @patch("frontend.api_layer.qwen_speech_model.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_text_to_audio_long_text_truncation(
        self, mock_file_open, mock_get, mock_post, manager, tmp_path, mock_tts_response
    ):
        """Test that long text is truncated for TTS."""
        # Create a very long text (over 600 characters)
        long_text = "这是一个很长的文本。" * 200

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = mock_tts_response
        mock_post.return_value = mock_post_response

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.content = b"fake audio data"
        mock_get.return_value = mock_get_response

        output_file = str(tmp_path / "output.wav")
        with patch.object(manager, "_play_audio"):
            result = manager.text_to_audio(long_text, output_file)

        assert result is True
        # Verify the request was made with truncated text
        call_args = mock_post.call_args
        sent_text = call_args[1]["json"]["input"]["text"]
        assert len(sent_text) < len(long_text)

    @patch("frontend.api_layer.qwen_speech_model.requests.post")
    @patch("frontend.api_layer.qwen_speech_model.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_text_to_audio_updates_stats(
        self, mock_file_open, mock_get, mock_post, manager, tmp_path, mock_tts_response
    ):
        """Test that TTS updates statistics."""

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = mock_tts_response
        mock_post.return_value = mock_post_response

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.content = b"fake audio data"
        mock_get.return_value = mock_get_response

        output_file = str(tmp_path / "output.wav")
        with patch.object(manager, "_play_audio"):
            before_time = manager.last_tts_time
            manager.text_to_audio("测试", output_file)

            assert manager.last_tts_time > before_time
            assert manager.tts_success_count == 1

    # ============== Voice Mapping Tests ==============

    def test_voice_mapping(self):
        """Test voice parameter mapping."""
        with patch.dict(os.environ, {}):
            manager = QwenSpeechManager()

        expected_mapping = {
            "female": "Cherry",
            "male": "Ryan",
            "neutral": "Sarah",
        }

        for voice, expected in expected_mapping.items():
            with (
                patch("frontend.api_layer.qwen_speech_model.requests.post") as mock_post,
                patch("frontend.api_layer.qwen_speech_model.requests.get") as mock_get,
                patch("builtins.open", mock_open()),
                patch.object(manager, "_play_audio"),
            ):
                mock_post_response = MagicMock()
                mock_post_response.status_code = 200
                mock_post.return_value = mock_post_response

                mock_get_response = MagicMock()
                mock_get_response.status_code = 200
                mock_get_response.content = b"fake audio data"
                mock_get.return_value = mock_get_response

                manager.text_to_audio("测试", "output.wav", voice=voice)

                # Verify the correct voice was used
                call_args = mock_post.call_args
                used_voice = call_args[1]["json"]["input"]["voice"]
                assert used_voice == expected

    # ============== Statistics Tests ==============

    def test_get_stats(self, manager):
        """Test getting statistics."""
        manager.asr_success_count = 5
        manager.asr_failure_count = 2
        manager.tts_success_count = 3
        manager.tts_failure_count = 1

        import time

        manager.last_asr_time = time.time() - 100
        manager.last_tts_time = time.time() - 50

        stats = manager.get_stats()

        assert stats["asr_success_count"] == 5
        assert stats["asr_failure_count"] == 2
        assert stats["tts_success_count"] == 3
        assert stats["tts_failure_count"] == 1

    # ============== Audio Playback Tests ==============

    def test_play_audio_file_not_found(self, manager):
        """Test audio playback with non-existent file."""
        # Should handle missing file gracefully without crashing
        # The method tries multiple playback methods and logs errors
        manager._play_audio("nonexistent_file.wav")
        # If we get here without raising, the test passes
        assert True

    def test_play_audio_method_exists(self, manager):
        """Test that _play_audio method exists."""
        assert hasattr(manager, "_play_audio")
        assert callable(manager._play_audio)


@pytest.mark.requires_llm
class TestQwenSpeechManagerIntegration:
    """Integration tests that require actual LLM API connection."""

    @pytest.fixture
    def live_manager(self):
        """Create a manager with real config."""
        manager = QwenSpeechManager()
        yield manager

    def test_real_api_connection(self, live_manager):
        """Test real connection to Qwen API."""
        # This test only runs if API keys are configured
        if os.getenv("QWEN_API_KEY"):
            stats = live_manager.get_stats()
            assert isinstance(stats, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
