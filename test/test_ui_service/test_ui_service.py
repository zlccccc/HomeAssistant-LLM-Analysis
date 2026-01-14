"""UI 服务模块的单元测试

测试 EntityService 和 ChatService 的业务逻辑。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.source.ui_service.entity_service import EntityService
from backend.source.ui_service.chat_service import ChatService


# ==================== EntityService Tests ====================

class TestEntityService:
    """EntityService 测试"""

    def test_initialization(self):
        """测试服务初始化"""
        service = EntityService()
        assert service is not None

    # ==================== 设备控制服务测试 ====================

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_get_device_groups_with_mock_data(self, mock_hass):
        """测试获取设备分组 - 使用模拟数据"""
        entity = {"entity_id": "light.living_room", "friendly_name": "客厅吸顶灯"}
        mock_hass.entity_data = {
            "non_sensor_data": {
                "light": [entity]
            }
        }
        mock_hass.group_entities_by_name.return_value = {"客厅": [entity]}

        service = EntityService()
        groups = service.get_device_groups("light")

        assert groups == ["客厅"]

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_get_device_groups_invalid_type(self, mock_hass):
        """测试获取设备分组 - 无效类型"""
        mock_hass.entity_data = {"non_sensor_data": {}}

        service = EntityService()
        groups = service.get_device_groups("invalid")

        assert groups == []

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_get_device_list(self, mock_hass):
        """测试获取设备列表"""
        entity = {"entity_id": "light.living_room", "friendly_name": "客厅吸顶灯"}
        mock_hass.entity_data = {
            "non_sensor_data": {
                "light": [entity]
            }
        }
        mock_hass.group_entities_by_name.return_value = {"客厅": [entity]}

        service = EntityService()
        devices = service.get_device_list("light", "客厅")

        assert devices == ["客厅吸顶灯"]

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_get_device_status(self, mock_hass):
        """测试获取设备状态"""
        entity = {
            "entity_id": "light.living_room",
            "friendly_name": "客厅吸顶灯",
            "state": "on",
            "last_updated": "2024-01-01T00:00:00"
        }
        mock_hass.entity_data = {
            "non_sensor_data": {
                "light": [entity]
            }
        }
        mock_hass.group_entities_by_name.return_value = {"客厅": [entity]}

        service = EntityService()
        status = service.get_device_status("light", "客厅", "客厅吸顶灯")

        assert status["entity_id"] == "light.living_room"
        assert status["state"] == "on"
        assert status["last_updated"] == "2024-01-01T00:00:00"

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_control_device_success(self, mock_hass):
        """测试控制设备 - 成功"""
        entity = {
            "entity_id": "light.living_room",
            "friendly_name": "客厅吸顶灯",
            "state": "on"
        }
        mock_hass.entity_data = {
            "non_sensor_data": {
                "light": [entity]
            }
        }
        mock_hass.group_entities_by_name.return_value = {"客厅": [entity]}
        mock_hass.call_home_assistant_service.return_value = "控制成功"

        service = EntityService()
        result = service.control_device("light", "客厅", "客厅吸顶灯")

        assert result["success"] is True
        assert "控制成功" in result["message"]
        assert result["new_state"] == "off"

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_control_device_api_failure(self, mock_hass):
        """测试控制设备 - API 返回失败"""
        entity = {
            "entity_id": "light.living_room",
            "friendly_name": "客厅吸顶灯",
            "state": "on"
        }
        mock_hass.entity_data = {
            "non_sensor_data": {
                "light": [entity]
            }
        }
        mock_hass.group_entities_by_name.return_value = {"客厅": [entity]}
        mock_hass.call_home_assistant_service.return_value = "控制失败：API错误"

        service = EntityService()
        result = service.control_device("light", "客厅", "客厅吸顶灯")

        assert result["success"] is False
        assert "控制失败" in result["message"]

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_control_device_not_found(self, mock_hass):
        """测试控制设备 - 设备未找到"""
        mock_hass.entity_data = {
            "non_sensor_data": {
                "light": []
            }
        }
        mock_hass.group_entities_by_name.return_value = {"客厅": []}

        service = EntityService()
        result = service.control_device("light", "客厅", "不存在的设备")

        assert result["success"] is False
        assert "未找到设备" in result["message"]

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_refresh_devices(self, mock_hass):
        """测试刷新设备列表"""
        mock_hass.entity_data = {
            "non_sensor_data": {
                "light": [],
                "switch": []
            }
        }

        service = EntityService()
        types = service.refresh_devices()

        assert types == ["light", "switch"]
        mock_hass.update_entity_data.assert_called_once()

    # ==================== 传感器数据服务测试 ====================

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_get_sensor_groups_numeric(self, mock_hass):
        """测试获取传感器分组 - 数值型"""
        mock_hass.entity_data = {
            "sensor_data": {
                "numeric_sensors_by_group": {
                    "temperature": [],
                    "humidity": []
                }
            }
        }

        service = EntityService()
        groups = service.get_sensor_groups("numeric")

        assert groups == ["temperature", "humidity"]

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_get_sensor_groups_text(self, mock_hass):
        """测试获取传感器分组 - 文本型"""
        mock_hass.entity_data = {
            "sensor_data": {
                "text_sensors_by_group": {
                    "status": []
                }
            }
        }

        service = EntityService()
        groups = service.get_sensor_groups("text")

        assert groups == ["status"]

    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_get_sensor_groups_invalid_type(self, mock_hass):
        """测试获取传感器分组 - 无效类型"""
        mock_hass.entity_data = {"sensor_data": {}}

        service = EntityService()
        groups = service.get_sensor_groups("invalid")

        assert groups == []

    def test_map_sensor_type(self):
        """测试传感器类型映射"""
        service = EntityService()
        assert service._map_sensor_type("numeric") == "numeric_sensors"
        assert service._map_sensor_type("text") == "text_sensors"
        assert service._map_sensor_type("invalid") == ""

    # ==================== 实体分析测试 ====================

    @patch("backend.source.ui_service.entity_service.hass_llm_controller")
    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_analyze_all_entities_success(self, mock_hass, mock_llm):
        """测试分析所有实体 - 成功"""
        mock_hass.entity_data = {
            "sensor_data": {},
            "non_sensor_data": {}
        }
        mock_llm.analyze_entities.return_value = ("summary", "analysis")
        mock_llm.save_analysis_results.return_value = ("summary.json", "analysis.json")

        service = EntityService()
        result = service.analyze_all_entities()

        assert result["success"] is True
        assert "分析完成" in result["message"]

    @patch("backend.source.ui_service.entity_service.hass_llm_controller")
    @patch("backend.source.ui_service.entity_service.hass_manager")
    def test_analyze_all_entities_failure(self, mock_hass, mock_llm):
        """测试分析所有实体 - 失败"""
        mock_hass.entity_data = {
            "sensor_data": {},
            "non_sensor_data": {}
        }
        mock_llm.analyze_entities.side_effect = Exception("Test error")

        service = EntityService()
        result = service.analyze_all_entities()

        assert result["success"] is False
        assert "分析失败" in result["message"]


# ==================== ChatService Tests ====================

class TestChatService:
    """ChatService 测试"""

    def test_initialization(self):
        """测试服务初始化"""
        service = ChatService()
        assert service is not None

    def test_normalize_history_with_dict(self):
        """测试标准化历史 - 字典格式"""
        service = ChatService()
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"}
        ]

        normalized = service.normalize_history(history)

        assert len(normalized) == 2
        assert normalized == history

    def test_normalize_history_with_tuple(self):
        """测试标准化历史 - 元组格式"""
        service = ChatService()
        history = [("user message", "assistant message")]

        normalized = service.normalize_history(history)

        assert len(normalized) == 2
        assert normalized[0] == {"role": "user", "content": "user message"}
        assert normalized[1] == {"role": "assistant", "content": "assistant message"}

    def test_normalize_history_mixed(self):
        """测试标准化历史 - 混合格式"""
        service = ChatService()
        history = [
            {"role": "user", "content": "first"},
            ("second user", "second assistant")
        ]

        normalized = service.normalize_history(history)

        assert len(normalized) == 3
        assert normalized[0]["role"] == "user"
        assert normalized[1]["role"] == "user"
        assert normalized[2]["role"] == "assistant"

    @pytest.mark.asyncio
    @patch("backend.source.ui_service.chat_service.qwen_speech_manager")
    @patch("backend.source.ui_service.chat_service.hass_llm_controller")
    @patch("backend.source.api_layer.home_assistant.hass_manager")
    async def test_process_message(self, mock_hass, mock_llm, mock_speech):
        """测试处理消息"""
        mock_llm.process_home_assistant_message = AsyncMock(return_value="Test response")
        mock_speech.text_to_audio.return_value = True

        service = ChatService()
        history, voice_success, voice_error = await service.process_message("test", [])

        assert isinstance(history, list)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[0]["content"] == "test"
        assert history[1]["content"] == "Test response"
        assert voice_success is True
        assert voice_error is None

    @pytest.mark.asyncio
    @patch("backend.source.ui_service.chat_service.qwen_speech_manager")
    @patch("backend.source.ui_service.chat_service.hass_llm_controller")
    @patch("backend.source.api_layer.home_assistant.hass_manager")
    async def test_process_message_with_existing_history(self, mock_hass, mock_llm, mock_speech):
        """测试处理消息 - 带有历史记录"""
        mock_llm.process_home_assistant_message = AsyncMock(return_value="New response")
        mock_speech.text_to_audio.return_value = False

        service = ChatService()
        existing_history = [{"role": "user", "content": "previous"}]
        history, voice_success, voice_error = await service.process_message("new", existing_history)

        assert len(history) == 3
        assert history[0] == existing_history[0]
        assert history[1]["role"] == "user"
        assert history[1]["content"] == "new"
        assert history[2]["role"] == "assistant"
        assert history[2]["content"] == "New response"
        assert voice_success is False
