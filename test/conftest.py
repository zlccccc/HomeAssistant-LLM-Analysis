"""
Pytest configuration and shared fixtures

This file contains common fixtures and configuration for all tests.
Run with: uv run pytest
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 注意: 测试中不应自动加载 .env 文件
# 单元测试使用 mock 配置，集成测试手动加载 load_dotenv()


# ============== Fixtures for testing ==============


@pytest.fixture
def mock_ha_config() -> dict[str, str]:
    """Mock Home Assistant configuration."""
    return {
        "HA_URL": "http://localhost:8123",
        "HA_TOKEN": "test_token_12345",
    }


@pytest.fixture
def mock_llm_config() -> dict[str, str]:
    """Mock LLM configuration."""
    return {
        "QWEN_API_KEY": "sk-test-key-12345",
        "QWEN_API_BASE": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "QWEN_MODEL": "qwen-flash",
    }


@pytest.fixture
def mock_entity_data() -> dict[str, Any]:
    """Mock entity data for testing."""
    return {
        "sensor_data": {
            "numeric_sensors": [
                {
                    "entity_id": "sensor.living_room_temperature",
                    "friendly_name": "客厅温度",
                    "state": "24.5",
                    "unit": "°C",
                    "unit_of_measurement": "°C",
                    "last_updated": "2024-01-13 10:30:00",
                    "external_attributes": {"device_class": "temperature"},
                },
                {
                    "entity_id": "sensor.bedroom_humidity",
                    "friendly_name": "卧室湿度",
                    "state": "55",
                    "unit": "%",
                    "unit_of_measurement": "%",
                    "last_updated": "2024-01-13 10:30:00",
                    "external_attributes": {"device_class": "humidity"},
                },
            ],
            "text_sensors": [
                {
                    "entity_id": "sensor.weather_condition",
                    "friendly_name": "天气状况",
                    "state": "晴",
                    "unit": "无单位",
                    "unit_of_measurement": "",
                    "last_updated": "2024-01-13 10:30:00",
                    "external_attributes": {},
                }
            ],
            "invalid_sensors": [],
            "numeric_sensors_by_group": {
                "客厅": [
                    {
                        "entity_id": "sensor.living_room_temperature",
                        "friendly_name": "客厅温度",
                        "state": "24.5",
                        "unit": "°C",
                        "unit_of_measurement": "°C",
                        "last_updated": "2024-01-13 10:30:00",
                        "external_attributes": {"device_class": "temperature"},
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
                    "state": "on",
                    "last_updated": "2024-01-13 10:30:00",
                    "external_attributes": {
                        "brightness": 255,
                        "color_mode": "xy",
                    },
                },
                {
                    "entity_id": "light.bedroom",
                    "friendly_name": "卧室灯",
                    "state": "off",
                    "last_updated": "2024-01-13 10:30:00",
                    "external_attributes": {
                        "brightness": 100,
                        "color_mode": "color_temp",
                    },
                },
            ],
            "switch": [
                {
                    "entity_id": "switch.fan",
                    "friendly_name": "风扇开关",
                    "state": "off",
                    "last_updated": "2024-01-13 10:30:00",
                }
            ],
        },
    }


@pytest.fixture
def mock_ha_response_states() -> list[dict[str, Any]]:
    """Mock Home Assistant API response for /api/states."""
    return [
        {
            "entity_id": "sensor.living_room_temperature",
            "state": "24.5",
            "attributes": {
                "friendly_name": "客厅温度",
                "unit_of_measurement": "°C",
                "device_class": "temperature",
            },
            "last_updated": "2024-01-13T10:30:00+00:00",
        },
        {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {
                "friendly_name": "客厅灯",
                "brightness": 255,
                "color_mode": "xy",
            },
            "last_updated": "2024-01-13T10:30:00+00:00",
        },
        {
            "entity_id": "switch.fan",
            "state": "off",
            "attributes": {
                "friendly_name": "风扇开关",
            },
            "last_updated": "2024-01-13T10:30:00+00:00",
        },
    ]


@pytest.fixture
def mock_llm_response() -> dict[str, Any]:
    """Mock LLM API response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "qwen-flash",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "您好！我是您的智能助手。当前客厅温度是24.5°C，需要我帮您调整吗？",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 30,
            "total_tokens": 80,
        },
    }


@pytest.fixture
def mock_memory_result() -> dict[str, Any]:
    """Mock memory API result."""
    return {
        "status": "success",
        "memorized_count": 3,
        "message": "Messages successfully memorized",
    }


@pytest.fixture
def sample_chat_history() -> list[tuple[str, str]]:
    """Sample chat history for testing."""
    return [
        ("你好", "你好！有什么我可以帮助您的吗？"),
        ("今天天气怎么样", "抱歉，我无法获取天气信息，但您可以查看天气传感器。"),
    ]


@pytest.fixture
def sample_command_texts() -> dict[str, str]:
    """Sample command texts for testing command parser."""
    return {
        "open_light": "打开客厅灯",
        "close_light": "关闭卧室灯",
        "open_all_lights": "打开所有灯",
        "close_all_lights": "关闭所有灯",
        "open_switch": "打开风扇开关",
        "close_switch": "关闭风扇开关",
        "simple_open": "开灯",
        "simple_close": "关灯",
        "unknown": "做一道数学题",
    }


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for testing."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_requests_response():
    """Create a mock requests.Response object."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_response.text = "OK"
    return mock_response


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_asyncio_sleep():
    """Mock asyncio.sleep to speed up tests."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        yield


@pytest.fixture
def mock_hass_manager():
    """Mock Home Assistant manager for testing."""
    mock = MagicMock()
    mock.url = "http://localhost:8123"
    mock.headers = {"Authorization": "Bearer test_token", "Content-Type": "application/json"}
    mock.entity_data = {
        "sensor_data": {"numeric_sensors": [], "text_sensors": []},
        "non_sensor_data": {
            "light": [
                {
                    "entity_id": "light.living_room",
                    "friendly_name": "客厅灯",
                    "state": "off",
                    "last_updated": "2024-01-13 10:30:00",
                    "external_attributes": {},
                }
            ],
            "switch": [],
        },
    }
    mock.update_entity_data = MagicMock()
    mock.get_mcp_tools = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager for testing."""
    mock = MagicMock()
    mock.model_name = "qwen-flash"
    mock.api_key = "test-key"
    mock.api_base = "https://api.example.com/v1"
    mock.get_chat_model = MagicMock(return_value=MagicMock())
    mock.call_openai_api = MagicMock(return_value="Test response from LLM")
    return mock


# ============== Markers ==============


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "requires_ha: marks tests that require Home Assistant")
    config.addinivalue_line("markers", "requires_llm: marks tests that require LLM API")


# ============== Skip patterns ==============


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on test file names
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "test_" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Skip tests that require external services if not available
        if item.get_closest_marker("requires_ha") and (
            not os.getenv("HA_URL") or not os.getenv("HA_TOKEN")
        ):
            item.add_marker(pytest.mark.skip(reason="Home Assistant not configured"))

        if item.get_closest_marker("requires_llm") and not os.getenv("QWEN_API_KEY"):
            item.add_marker(pytest.mark.skip(reason="LLM API key not configured"))
