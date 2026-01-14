"""聊天服务

提供聊天功能服务，与 Gradio UI 解耦。
"""

import tempfile
from pathlib import Path
from typing import Any

from backend.source.infrastructure.utils import logger
from backend.source.services.langgraph_controller import (
    hass_llm_controller_langgraph as hass_llm_controller,
)
from frontend.api_layer.qwen_speech_model import qwen_speech_manager


class ChatService:
    """
    聊天服务类

    提供消息处理、历史格式化和语音生成功能。
    """

    async def process_message(
        self, message: str, history: list
    ) -> tuple[list[dict[str, Any]], bool, str | None]:
        """
        处理用户消息并生成响应

        Args:
            message: 用户消息
            history: 聊天历史

        Returns:
            (更新后的历史记录, 语音生成是否成功, 错误消息)

        Example:
            >>> service = ChatService()
            >>> history, voice_success, error = await service.process_message("hello", [])
            >>> isinstance(history, list)
            True
        """
        # 更新实体数据
        from backend.source.api_layer.home_assistant import hass_manager

        hass_manager.update_entity_data()

        # 标准化历史格式
        normalized_history = self.normalize_history(history)

        # 调用 LLM 控制器处理消息
        response = await hass_llm_controller.process_home_assistant_message(
            message, normalized_history
        )

        # 构建更新后的历史记录
        updated_history = [
            *normalized_history,
            {"role": "user", "content": message},
            {"role": "assistant", "content": response},
        ]

        # 尝试生成语音回复
        voice_success = False
        voice_error = None
        try:
            temp_dir = Path(tempfile.gettempdir())
            output_file = str(temp_dir / "auto_response_audio.wav")

            voice_success = qwen_speech_manager.text_to_audio(
                response, output_file, voice="female"
            )
            if voice_success:
                logger.info("自动生成语音回复成功")
            else:
                logger.error("语音合成失败")
        except Exception as e:
            voice_error = str(e)
            logger.error(f"自动播放语音时出错: {e}")

        return updated_history, voice_success, voice_error

    def normalize_history(self, history: list) -> list[dict[str, Any]]:
        """
        标准化聊天历史格式

        将各种可能的聊天历史格式统一转换为字典格式。

        Args:
            history: 聊天历史，可能是字典列表或元组列表

        Returns:
            标准化后的字典列表，格式为 [{"role": "...", "content": "..."}]

        Example:
            >>> service = ChatService()
            >>> # 测试元组格式
            >>> normalized = service.normalize_history([("user", "hello"), ("assistant", "hi")])
            >>> len(normalized)
            2
            >>> normalized[0]["role"]
            'user'
        """
        normalized = []
        for h in history:
            if isinstance(h, dict) and "role" in h and "content" in h:
                normalized.append(h)
            elif isinstance(h, (tuple, list)) and len(h) == 2:
                normalized.append({"role": "user", "content": h[0]})
                normalized.append({"role": "assistant", "content": h[1]})
            else:
                # 其他格式保持原样
                normalized.append(h)
        return normalized


# 创建全局单例实例
chat_service = ChatService()
