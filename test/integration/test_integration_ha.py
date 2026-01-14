"""
Home Assistant Integration Tests

These tests require a real Home Assistant instance.
Run with: uv run pytest test/test_integration_ha.py -v

Make sure to configure .env with valid HA_URL and HA_TOKEN before running.
"""

import os

import pytest
from dotenv import load_dotenv

from backend.source.api_layer.home_assistant import HomeAssistantManager

# Load real environment variables for integration tests
load_dotenv()


@pytest.mark.integration
@pytest.mark.requires_ha
class TestHomeAssistantIntegration:
    """Integration tests with real Home Assistant instance."""

    @pytest.fixture
    def real_manager(self):
        """Create a manager with real configuration from .env."""
        manager = HomeAssistantManager()
        yield manager

    def test_connection_to_ha(self, real_manager):
        """Test that we can connect to Home Assistant."""
        # This test requires HA to be running and configured
        ha_url = os.getenv("HA_URL")
        ha_token = os.getenv("HA_TOKEN")

        if not ha_url or not ha_token:
            pytest.skip("HA_URL and HA_TOKEN must be set in .env")

        assert real_manager.url == ha_url
        assert real_manager.token == ha_token

    def test_get_and_classify_entities(self, real_manager):
        """Test retrieving and classifying entities from real HA."""
        ha_url = os.getenv("HA_URL")
        ha_token = os.getenv("HA_TOKEN")

        if not ha_url or not ha_token:
            pytest.skip("HA_URL and HA_TOKEN must be set in .env")

        sensor_data, non_sensor_data = real_manager.get_and_classify_entities()

        # Should successfully retrieve data
        assert sensor_data is not None, "Failed to connect to Home Assistant"
        assert non_sensor_data is not None

        # Check structure
        assert "numeric_sensors" in sensor_data
        assert "text_sensors" in sensor_data
        assert "invalid_sensors" in sensor_data

    def test_entity_summary(self, real_manager):
        """Test generating entity summary."""
        ha_url = os.getenv("HA_URL")
        ha_token = os.getenv("HA_TOKEN")

        if not ha_url or not ha_token:
            pytest.skip("HA_URL and HA_TOKEN must be set in .env")

        summary = real_manager.get_current_entity_summary()
        assert isinstance(summary, str)

    def test_group_entities(self, real_manager):
        """Test entity grouping functionality."""
        ha_url = os.getenv("HA_URL")
        ha_token = os.getenv("HA_TOKEN")

        if not ha_url or not ha_token:
            pytest.skip("HA_URL and HA_TOKEN must be set in .env")

        # Update entity data first
        real_manager.update_entity_data()

        sensor_data = real_manager.entity_data.get("sensor_data", {})
        numeric_sensors = sensor_data.get("numeric_sensors", [])

        if numeric_sensors:
            grouped = real_manager.group_entities_by_name(numeric_sensors)
            assert isinstance(grouped, dict)

    def test_export_to_excel(self, real_manager, tmp_path):
        """Test exporting entity data to Excel."""
        ha_url = os.getenv("HA_URL")
        ha_token = os.getenv("HA_TOKEN")

        if not ha_url or not ha_token:
            pytest.skip("HA_URL and HA_TOKEN must be set in .env")

        # Update entity data first
        real_manager.update_entity_data()

        sensor_data = real_manager.entity_data.get("sensor_data")
        non_sensor_data = real_manager.entity_data.get("non_sensor_data")

        if sensor_data and non_sensor_data:
            result = real_manager.export_to_excel(sensor_data, non_sensor_data)
            if result:
                assert result.endswith(".xlsx")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
