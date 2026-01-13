"""
HomeAssistantManager Test Suite

Tests the Home Assistant API integration module.
Run with: uv run pytest test/test_home_assistant.py -v
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from backend.source.api_layer.home_assistant import HomeAssistantManager


class TestHomeAssistantManager:
    """Test cases for HomeAssistantManager class."""

    @pytest.fixture
    def manager(self, mock_ha_config):
        """Create a HomeAssistantManager instance with mocked config."""
        with patch.dict(os.environ, mock_ha_config, clear=False):
            with patch("backend.source.api_layer.home_assistant.requests"):
                manager = HomeAssistantManager()
                yield manager

    @pytest.fixture
    def mock_response(self):
        """Create a mock response object."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.text = "OK"
        return mock_resp

    # ============== Initialization Tests ==============

    def test_initialization(self, mock_ha_config):
        """Test manager initialization with config."""
        with patch.dict(os.environ, mock_ha_config, clear=False):
            with patch("backend.source.api_layer.home_assistant.requests"):
                manager = HomeAssistantManager()
                assert manager.url == "http://localhost:8123"
                assert manager.token == "test_token_12345"
                assert "Authorization" in manager.headers
                assert "Bearer test_token_12345" in manager.headers["Authorization"]
                assert isinstance(manager.entity_data, dict)

    def test_initialization_with_defaults(self):
        """Test manager initialization with default values."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("backend.source.api_layer.home_assistant.requests"):
                manager = HomeAssistantManager()
                assert manager.url == "http://localhost:8123"
                assert manager.token == ""
                # entity_data is initialized with None values due to failed API call
                assert "sensor_data" in manager.entity_data
                assert "non_sensor_data" in manager.entity_data

    # ============== Entity Grouping Tests ==============

    def test_group_entities_by_name_with_location_keywords(self, manager):
        """Test grouping entities by location keywords."""
        entities = [
            {"entity_id": "sensor.living_room_temp", "friendly_name": "客厅温度"},
            {"entity_id": "sensor.bedroom_humidity", "friendly_name": "卧室湿度"},
            {"entity_id": "sensor.kitchen_temp", "friendly_name": "厨房温度"},
        ]

        result = manager.group_entities_by_name(entities)

        assert "客厅" in result
        assert "卧室" in result
        assert "厨房" in result
        assert len(result["客厅"]) == 1
        assert result["客厅"][0]["friendly_name"] == "客厅温度"

    def test_group_entities_by_name_with_separators(self, manager):
        """Test grouping entities with common separators."""
        entities = [
            {"entity_id": "sensor.living_room_temp", "friendly_name": "living-room-temp"},
            {"entity_id": "sensor.bedroom_humid", "friendly_name": "bedroom_humidity"},
            {"entity_id": "sensor.office_temp", "friendly_name": "office temperature"},
        ]

        result = manager.group_entities_by_name(entities)

        assert "living" in result or "living-room-temp" in result
        assert "bedroom_humidity" in result or "bedroom" in result

    def test_group_entities_by_name_from_entity_id(self, manager):
        """Test grouping entities by extracting from entity_id."""
        entities = [
            {"entity_id": "sensor.living_room_temperature", "friendly_name": ""},
            {"entity_id": "sensor.bedroom_humidity", "friendly_name": ""},
        ]

        result = manager.group_entities_by_name(entities)

        # Should group by entity_id parts
        assert len(result) > 0

    def test_group_entities_sorting(self, manager):
        """Test that groups and entities within groups are sorted."""
        entities = [
            {"entity_id": "sensor.bedroom_temp", "friendly_name": "卧室温度"},
            {"entity_id": "sensor.kitchen_temp", "friendly_name": "厨房温度"},
            {"entity_id": "sensor.living_room_temp", "friendly_name": "客厅温度"},
            {"entity_id": "sensor.bedroom_humid", "friendly_name": "卧室湿度"},
        ]

        result = manager.group_entities_by_name(entities)

        # Groups should be sorted
        group_names = list(result.keys())
        assert group_names == sorted(group_names)

        # Entities within groups should be sorted
        for group_name, group_entities in result.items():
            friendly_names = [e.get("friendly_name", "") for e in group_entities]
            assert friendly_names == sorted(friendly_names)

    # ============== MCP Client Tests ==============

    def test_get_mcp_client(self, manager):
        """Test MCP client creation."""
        client = manager.get_mcp_client()
        assert client is not None
        assert hasattr(client, "get_tools")

    def test_get_mcp_client_with_custom_endpoint(self, manager):
        """Test MCP client with custom endpoint."""
        with patch.dict(os.environ, {"HA_MCP_ENDPOINT": "/custom/mcp"}):
            client = manager.get_mcp_client()
            assert client is not None

    # ============== Entity Data Tests ==============

    @patch("backend.source.api_layer.home_assistant.requests.get")
    def test_get_and_classify_entities_success(self, mock_get, manager, mock_ha_response_states):
        """Test successful entity retrieval and classification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ha_response_states
        mock_get.return_value = mock_response

        sensor_data, non_sensor_data = manager.get_and_classify_entities()

        assert sensor_data is not None
        assert non_sensor_data is not None
        assert "numeric_sensors" in sensor_data
        assert "text_sensors" in sensor_data
        assert "invalid_sensors" in sensor_data

    @patch("backend.source.api_layer.home_assistant.requests.get")
    def test_get_and_classify_entities_unauthorized(self, mock_get, manager):
        """Test entity retrieval with unauthorized status."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        sensor_data, non_sensor_data = manager.get_and_classify_entities()

        assert sensor_data is None
        assert non_sensor_data is None

    def test_get_and_classify_entities_connection_error(self, manager):
        """Test entity retrieval with connection error."""
        # Import the actual exception class before mocking
        from requests.exceptions import ConnectionError

        # Patch the requests module to preserve the exceptions module
        with patch("backend.source.api_layer.home_assistant.requests") as mock_requests:
            # Make sure exceptions are preserved
            mock_requests.exceptions.ConnectionError = ConnectionError
            mock_requests.get.side_effect = ConnectionError()

            sensor_data, non_sensor_data = manager.get_and_classify_entities()

            assert sensor_data is None
            assert non_sensor_data is None

    @patch("backend.source.api_layer.home_assistant.requests.get")
    def test_sensor_classification_numeric(self, mock_get, manager):
        """Test numeric sensor classification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "entity_id": "sensor.temperature",
                "state": "24.5",
                "attributes": {"friendly_name": "温度", "unit_of_measurement": "°C"},
                "last_updated": "2024-01-13T10:00:00+00:00",
            }
        ]
        mock_get.return_value = mock_response

        sensor_data, _ = manager.get_and_classify_entities()

        assert len(sensor_data["numeric_sensors"]) == 1
        assert sensor_data["numeric_sensors"][0]["entity_id"] == "sensor.temperature"

    @patch("backend.source.api_layer.home_assistant.requests.get")
    def test_sensor_classification_text(self, mock_get, manager):
        """Test text sensor classification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "entity_id": "sensor.condition",
                "state": "晴",
                "attributes": {"friendly_name": "天气状况"},
                "last_updated": "2024-01-13T10:00:00+00:00",
            }
        ]
        mock_get.return_value = mock_response

        sensor_data, _ = manager.get_and_classify_entities()

        assert len(sensor_data["text_sensors"]) == 1
        assert sensor_data["text_sensors"][0]["entity_id"] == "sensor.condition"

    @patch("backend.source.api_layer.home_assistant.requests.get")
    def test_sensor_classification_invalid(self, mock_get, manager):
        """Test invalid sensor classification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "entity_id": "sensor.unknown",
                "state": "unknown",
                "attributes": {"friendly_name": "未知传感器"},
                "last_updated": "2024-01-13T10:00:00+00:00",
            },
            {
                "entity_id": "sensor.unavailable",
                "state": "unavailable",
                "attributes": {"friendly_name": "不可用传感器"},
                "last_updated": "2024-01-13T10:00:00+00:00",
            },
        ]
        mock_get.return_value = mock_response

        sensor_data, _ = manager.get_and_classify_entities()

        assert len(sensor_data["invalid_sensors"]) == 2
        assert sensor_data["invalid_sensors"][0]["state"] in ["unknown", "unavailable"]

    @patch("backend.source.api_layer.home_assistant.requests.get")
    def test_non_sensor_entity_classification(self, mock_get, manager):
        """Test non-sensor entity classification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {
                    "friendly_name": "客厅灯",
                    "brightness": 255,
                    "color_mode": "xy",
                },
                "last_updated": "2024-01-13T10:00:00+00:00",
            },
            {
                "entity_id": "switch.fan",
                "state": "off",
                "attributes": {"friendly_name": "风扇"},
                "last_updated": "2024-01-13T10:00:00+00:00",
            },
        ]
        mock_get.return_value = mock_response

        _, non_sensor_data = manager.get_and_classify_entities()

        assert "light" in non_sensor_data
        assert "switch" in non_sensor_data
        assert len(non_sensor_data["light"]) == 1
        assert non_sensor_data["light"][0]["entity_id"] == "light.living_room"

    # ============== Entity Summary Tests ==============

    def test_get_current_entity_summary_initial(self, manager):
        """Test getting current entity summary when empty."""
        summary = manager.get_current_entity_summary()
        assert isinstance(summary, str)

    @patch("backend.source.api_layer.home_assistant.requests.get")
    def test_update_entity_data(self, mock_get, manager):
        """Test updating entity data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "entity_id": "sensor.temperature",
                "state": "24.5",
                "attributes": {
                    "friendly_name": "温度",
                    "unit_of_measurement": "°C",
                },
                "last_updated": "2024-01-13T10:00:00+00:00",
            }
        ]
        mock_get.return_value = mock_response

        summary = manager.update_entity_data()

        assert isinstance(summary, str)
        assert len(summary) > 0
        assert manager.entity_data is not None
        assert "sensor_data" in manager.entity_data

    # ============== Export Tests ==============

    @patch("backend.source.api_layer.home_assistant.pd.ExcelWriter")
    @patch("backend.source.api_layer.home_assistant.os.path.exists")
    @patch("backend.source.api_layer.home_assistant.os.makedirs")
    def test_export_to_excel_success(self, mock_makedirs, mock_exists, mock_writer, manager, mock_entity_data):
        """Test successful Excel export."""
        mock_exists.return_value = False
        mock_writer.return_value.__enter__ = MagicMock()
        mock_writer.return_value.__exit__ = MagicMock()

        result = manager.export_to_excel(
            mock_entity_data["sensor_data"],
            mock_entity_data["non_sensor_data"]
        )

        assert result is not None
        assert result.endswith(".xlsx")

    @patch("backend.source.api_layer.home_assistant.pd.ExcelWriter")
    def test_export_to_excel_with_output_dir(self, mock_writer, manager, mock_entity_data, temp_output_dir):
        """Test Excel export with custom output directory."""
        with patch.dict(os.environ, {"OUTPUT_DIR": str(temp_output_dir)}):
            mock_writer.return_value.__enter__ = MagicMock()
            mock_writer.return_value.__exit__ = MagicMock()

            result = manager.export_to_excel(
                mock_entity_data["sensor_data"],
                mock_entity_data["non_sensor_data"]
            )

            assert result is not None

    @patch("backend.source.api_layer.home_assistant.pd.ExcelWriter")
    def test_export_to_excel_failure(self, mock_writer, manager, mock_entity_data):
        """Test Excel export failure handling."""
        mock_writer.side_effect = Exception("Export failed")

        result = manager.export_to_excel(
            mock_entity_data["sensor_data"],
            mock_entity_data["non_sensor_data"]
        )

        assert result is None


@pytest.mark.requires_ha
class TestHomeAssistantManagerIntegration:
    """Integration tests that require actual Home Assistant connection."""

    @pytest.fixture
    def live_manager(self):
        """Create a manager with real config."""
        manager = HomeAssistantManager()
        yield manager

    def test_real_connection(self, live_manager):
        """Test real connection to Home Assistant."""
        sensor_data, non_sensor_data = live_manager.get_and_classify_entities()
        # This test only runs if HA is configured
        if sensor_data is not None and non_sensor_data is not None:
            assert "numeric_sensors" in sensor_data
            assert isinstance(non_sensor_data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
