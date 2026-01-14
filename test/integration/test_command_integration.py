"""
End-to-End Workflow Integration Tests

These tests test the complete workflow from user input to response,
using mocks for external dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.source.services.command_parser import CommandParser


@pytest.mark.integration
class TestCommandParserIntegration:
    """Integration tests for command parser with mocked HTTP."""

    @pytest.fixture
    def realistic_entity_data(self):
        """Create realistic entity data structure."""
        return {
            "non_sensor_data": {
                "light": [
                    {"entity_id": "light.living_room_main", "friendly_name": "客厅主灯", "state": "off"},
                    {"entity_id": "light.bedroom_main", "friendly_name": "卧室主灯", "state": "off"},
                    {"entity_id": "light.kitchen_main", "friendly_name": "厨房灯", "state": "on"},
                ],
                "switch": [
                    {"entity_id": "switch.fan", "friendly_name": "客厅风扇", "state": "off"},
                ],
            }
        }

    @pytest.fixture
    def parser(self, realistic_entity_data):
        """Create a parser with realistic entity data."""
        return CommandParser(
            entity_data=realistic_entity_data,
            url="http://localhost:8123",
            headers={"Authorization": "Bearer test_token", "content-type": "application/json"},
        )

    @patch("requests.post")
    def test_light_control_integration(self, mock_post, parser):
        """Test light control commands with mocked HTTP."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_post.return_value = mock_response

        commands = ["打开客厅主灯", "关闭卧室主灯", "开灯", "关灯"]
        for command in commands:
            result = parser.parse_and_execute_command(command)
            assert result is not None
            assert isinstance(result, str)

    @patch("requests.post")
    def test_switch_control_integration(self, mock_post, parser):
        """Test switch control commands with mocked HTTP."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_post.return_value = mock_response

        commands = ["打开客厅风扇", "关闭风扇"]
        for command in commands:
            result = parser.parse_and_execute_command(command)
            assert result is not None
            assert isinstance(result, str)

    @patch("requests.post")
    def test_error_handling_integration(self, mock_post, parser):
        """Test error handling with HTTP failures."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Entity not found"
        mock_post.return_value = mock_response

        result = parser.parse_and_execute_command("打开客厅主灯")
        assert result is not None
        assert isinstance(result, str)

    @patch("requests.post")
    def test_timeout_handling(self, mock_post, parser):
        """Test timeout handling."""
        import requests

        mock_post.side_effect = requests.exceptions.Timeout()

        result = parser.parse_and_execute_command("打开客厅主灯")
        assert result is not None
        assert isinstance(result, str)

    def test_command_parser_boundary_conditions(self, parser):
        """Test command parser boundary conditions."""
        # Empty command
        result = parser.parse_and_execute_command("")
        assert "未找到" in result

        # None command
        result = parser.parse_and_execute_command(None)
        assert "未找到" in result

        # Whitespace only
        result = parser.parse_and_execute_command("   ")
        assert "未找到" in result

    @patch("requests.post")
    def test_http_request_verification(self, mock_post, parser):
        """Verify that HTTP requests are made correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_post.return_value = mock_response

        parser.parse_and_execute_command("打开客厅主灯")

        # Verify the mock was called
        assert mock_post.called

    @patch("requests.post")
    def test_concurrent_commands(self, mock_post, parser):
        """Test multiple commands in sequence."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_post.return_value = mock_response

        commands = ["打开客厅主灯", "打开卧室主灯", "关闭厨房灯"]

        results = [parser.parse_and_execute_command(cmd) for cmd in commands]

        # All should return valid responses
        for result in results:
            assert result is not None
            assert isinstance(result, str)

    def test_command_parser_update_entity_data(self, realistic_entity_data):
        """Test updating entity data dynamically."""
        parser = CommandParser(
            entity_data={},
            url="http://localhost:8123",
            headers={"Authorization": "Bearer test_token"},
        )

        # Initially no entities
        result = parser.parse_and_execute_command("打开灯")
        assert "未找到" in result

        # Update with new entity data
        parser.update_entity_data(realistic_entity_data)

        # Now should find entities
        result = parser.parse_and_execute_command("打开灯")
        assert result is not None
        assert isinstance(result, str)

    @patch("requests.post")
    def test_special_characters_in_commands(self, mock_post, parser):
        """Test commands with special characters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_post.return_value = mock_response

        commands = ["打开客厅灯！", "开灯~", "打开灯。"]

        for command in commands:
            result = parser.parse_and_execute_command(command)
            assert result is not None
            assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
