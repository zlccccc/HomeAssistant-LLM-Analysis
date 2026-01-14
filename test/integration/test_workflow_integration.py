"""
End-to-End Workflow Integration Tests

These tests test the complete workflow from user input to response,
using mocks for external dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.source.services.command_parser import CommandParser
from backend.source.services.langgraph_controller import (
    HomeAssistantLLMControllerLangGraph,
)
from backend.source.ui_service.entity_service import EntityService


@pytest.mark.integration
class TestWorkflowIntegration:
    """End-to-end workflow tests with mocked external dependencies."""

    @pytest.fixture
    def mock_ha_manager(self):
        """Mock Home Assistant manager."""
        manager = MagicMock()
        manager.url = "http://localhost:8123"
        manager.headers = {"Authorization": "Bearer test_token", "content-type": "application/json"}
        manager.entity_data = {
            "sensor_data": {
                "numeric_sensors_by_group": {
                    "temperature": [
                        {
                            "entity_id": "sensor.temperature_1",
                            "friendly_name": "客厅温度",
                            "state": "25.5",
                            "unit_of_measurement": "°C",
                            "last_updated": "2024-01-01T00:00:00",
                        }
                    ]
                },
                "text_sensors_by_group": {},
                "invalid_sensors_by_group": {},
            },
            "non_sensor_data": {
                "light": [
                    {
                        "entity_id": "light.living_room",
                        "friendly_name": "客厅灯",
                        "state": "off",
                    }
                ],
                "switch": [
                    {
                        "entity_id": "switch.fan",
                        "friendly_name": "风扇",
                        "state": "off",
                    }
                ],
            },
        }
        manager.update_entity_data = MagicMock()
        return manager

    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM manager."""
        manager = MagicMock()
        manager.call_openai_api = MagicMock(return_value="好的，我来帮您打开客厅灯。")
        return manager

    @pytest.fixture
    def mock_memory_manager(self):
        """Mock memory manager."""
        manager = MagicMock()
        manager.memory = None
        manager.memorize_messages = AsyncMock(return_value={"status": "success"})
        manager.retrieve_memory_info = AsyncMock(return_value="")
        return manager

    @pytest.mark.asyncio
    async def test_complete_chat_workflow(self, mock_ha_manager, mock_llm_manager, mock_memory_manager):
        """Test complete chat workflow from user message to response."""
        with patch(
            "backend.source.services.langgraph_controller.hass_manager", mock_ha_manager
        ), patch(
            "backend.source.services.langgraph_controller.llm_manager", mock_llm_manager
        ), patch(
            "backend.source.services.langgraph_controller.memory_manager", mock_memory_manager
        ):
            controller = HomeAssistantLLMControllerLangGraph()

            response = await controller.process_home_assistant_message(
                message="打开客厅灯", history=None
            )

            assert response is not None
            assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_workflow_with_dict_history(self, mock_ha_manager, mock_llm_manager, mock_memory_manager):
        """Test workflow with dictionary format history."""
        with patch(
            "backend.source.services.langgraph_controller.hass_manager", mock_ha_manager
        ), patch(
            "backend.source.services.langgraph_controller.llm_manager", mock_llm_manager
        ), patch(
            "backend.source.services.langgraph_controller.memory_manager", mock_memory_manager
        ):
            controller = HomeAssistantLLMControllerLangGraph()

            history = [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！"},
            ]
            response = await controller.process_home_assistant_message(
                message="帮我查看传感器", history=history
            )

            assert response is not None
            assert isinstance(response, str)

    def test_entity_service_workflow(self, mock_ha_manager):
        """Test entity service workflow."""
        with patch(
            "backend.source.ui_service.entity_service.hass_manager", mock_ha_manager
        ):
            service = EntityService()

            # Test getting device groups - returns list of group names
            groups = service.get_device_groups("light")
            assert isinstance(groups, list)

            # Test getting device list (needs device_type and group_name)
            devices = service.get_device_list("light", "客厅")
            assert isinstance(devices, list)

    def test_command_parser_workflow(self, mock_ha_manager):
        """Test command parser workflow."""
        parser = CommandParser(
            entity_data=mock_ha_manager.entity_data,
            url=mock_ha_manager.url,
            headers=mock_ha_manager.headers,
        )

        # Test parsing a valid command
        result = parser.parse_and_execute_command("打开客厅灯")
        assert "未找到" in result or "成功" in result or "失败" in result

        # Test parsing an invalid command
        result = parser.parse_and_execute_command("做一道数学题")
        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_workflow_edge_cases(self, mock_ha_manager, mock_llm_manager, mock_memory_manager):
        """Test workflow edge cases."""
        with patch(
            "backend.source.services.langgraph_controller.hass_manager", mock_ha_manager
        ), patch(
            "backend.source.services.langgraph_controller.llm_manager", mock_llm_manager
        ), patch(
            "backend.source.services.langgraph_controller.memory_manager", mock_memory_manager
        ):
            controller = HomeAssistantLLMControllerLangGraph()

            # Test empty message
            response = await controller.process_home_assistant_message("", history=None)
            assert "无效" in response or "空" in response

            # Test None message
            response = await controller.process_home_assistant_message(None, history=None)
            assert "无效" in response

    def test_entity_service_sensor_workflow(self, mock_ha_manager):
        """Test entity service sensor data workflow."""
        with patch(
            "backend.source.ui_service.entity_service.hass_manager", mock_ha_manager
        ):
            service = EntityService()

            # Test getting sensor groups - returns list of group names
            groups = service.get_sensor_groups("numeric")
            assert isinstance(groups, list)

            # Test getting sensor list
            sensors = service.get_sensor_list("numeric", "temperature")
            assert isinstance(sensors, list)

    def test_entity_service_device_control_workflow(self, mock_ha_manager):
        """Test entity service device control workflow."""
        with patch(
            "backend.source.ui_service.entity_service.hass_manager", mock_ha_manager
        ):
            service = EntityService()

            # Test getting device status (needs device_type, group_name, device_name)
            status = service.get_device_status("light", "客厅", "客厅灯")
            assert isinstance(status, dict)

            # Test controlling device (will fail due to mock, but should not crash)
            result = service.control_device("light", "客厅", "客厅灯")
            assert isinstance(result, dict)
            assert "success" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
