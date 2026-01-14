"""UI 服务模块

为前端提供业务逻辑服务，与 Gradio UI 解耦。
"""

from backend.source.ui_service.entity_service import entity_service
from backend.source.ui_service.chat_service import chat_service

__all__ = ["entity_service", "chat_service"]
