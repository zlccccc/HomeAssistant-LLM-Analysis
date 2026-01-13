import asyncio
import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from memu.app import MemoryService

from backend.source.base_layer.utils import logger


class MemoryManager:
    """
    记忆管理类，负责处理对话记忆的存储和检索
    使用 MemU MemoryService 进行记忆管理

    支持两种模式：
    1. 本地模式：使用 OPENAI_API_KEY 或 QWEN_API_KEY 本地运行
    2. 云端模式：使用 MEMU_API_KEY 连接到云端服务（需要额外配置）
    """

    def __init__(self, auto_initialize: bool = True):
        if auto_initialize:
            self.memory = self._build_memory()
        else:
            self.memory = None

    def _build_memory(self) -> MemoryService | None:
        """
        构建 MemU 记忆客户端
        """
        if os.environ.get("USE_MEMORY_MESSAGES", "false") != "true":
            return None

        try:
            # 构建 LLM 配置
            llm_profiles = None
            qwen_api_key = os.environ.get("QWEN_API_KEY")
            openai_api_key = os.environ.get("OPENAI_API_KEY")

            if qwen_api_key:
                # 使用 Qwen API
                llm_profiles = {
                    "default": {
                        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                        "api_key": qwen_api_key,
                        "chat_model": "qwen-max",
                        "embed_model": "text-embedding-v3",
                    }
                }
                logger.info("使用 Qwen API 配置 MemU")
            elif openai_api_key:
                # 使用 OpenAI API
                llm_profiles = {
                    "default": {
                        "api_key": openai_api_key,
                    }
                }
                logger.info("使用 OpenAI API 配置 MemU")
            else:
                logger.warning("未找到 QWEN_API_KEY 或 OPENAI_API_KEY，使用默认配置")
                return None

            # 用户配置
            user_config = {
                "user_id": os.environ.get("MEMU_USER_ID", "user001"),
                "user_name": os.environ.get("MEMU_USER_NAME", "master"),
            }

            # 初始化 MemoryService（使用内存存储，无需数据库）
            memory_service = MemoryService(
                llm_profiles=llm_profiles,
                user_config=user_config,
                database_config={"type": "memory"},  # 使用内存存储
            )
            logger.info("MemU 记忆客户端初始化完成")
            return memory_service

        except Exception as e:
            logger.error(f"初始化 MemU 记忆客户端失败: {e!s}")
            import traceback

            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    async def memorize_messages(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """
        记忆对话消息（存储过程）

        Args:
            messages: 要记忆的消息列表，格式如：
                [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]

        Returns:
            记忆结果字典，包含状态和记忆的消息数量

        Example:
            >>> manager = MemoryManager()
            >>> messages = [
            ...     {"role": "user", "content": "我喜欢咖啡"},
            ...     {"role": "assistant", "content": "好的，记住了"}
            ... ]
            >>> result = await manager.memorize_messages(messages)
            >>> print(result["status"])
            "success"
        """
        if self.memory is None:
            logger.info("记忆功能未启用")
            return {"memorized_count": 0, "status": "disabled"}

        if not messages:
            return {"memorized_count": 0, "status": "no_messages"}

        try:
            # 将消息转换为临时 JSON 文件（MemU memorize 需要 resource_url）
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
                temp_file_path = f.name

            try:
                # 添加超时保护（15秒）
                result = await asyncio.wait_for(
                    self.memory.memorize(
                        resource_url=temp_file_path,
                        modality="conversation",
                        user={"user_id": os.environ.get("MEMU_USER_ID", "user001")},
                    ),
                    timeout=15.0,
                )
                logger.info(f"成功记忆对话，结果: {result}")
                return {
                    "memorized_count": len(messages),
                    "status": "success",
                    "result": result,
                }
            except TimeoutError:
                logger.warning("记忆操作超时，跳过本次记忆")
                return {"memorized_count": 0, "status": "timeout", "error": "操作超时"}
            finally:
                # 清理临时文件
                with contextlib.suppress(Exception):
                    Path(temp_file_path).unlink(missing_ok=True)

        except Exception as e:
            # Check if this is an async context issue (expected in some scenarios)
            error_str = str(e)
            if "Not currently running on any asynchronous event loop" in error_str:
                logger.debug("记忆消息: 需要异步上下文")
            elif "No JSON object found" in error_str or "Failed to extract segments" in error_str:
                # memu库内部解析错误，记录为警告而不是错误
                logger.warning(f"memu库解析警告（可忽略）: {e}")
            else:
                logger.error(f"记忆消息失败: {e!s}")
                import traceback

                logger.error(f"详细错误: {traceback.format_exc()}")
            return {"memorized_count": 0, "status": "error", "error": error_str}

    async def retrieve_memory_info(self, query: str = "chat history preferences") -> str:
        """
        检索记忆信息（检索过程）

        Args:
            query: 查询文本，如 "chat history", "preferences" 等

        Returns:
            格式化的记忆信息字符串

        Example:
            >>> manager = MemoryManager()
            >>> memory_info = await manager.retrieve_memory_info("用户偏好")
            >>> print(memory_info)
            "## 记忆分类\\n\\n### 用户偏好\\n用户喜欢喝咖啡..."
        """
        if self.memory is None:
            return ""

        try:
            # 添加超时保护（10秒）
            result = await asyncio.wait_for(
                self.memory.retrieve(
                    queries=[{"role": "user", "content": {"text": query}}],
                    where={"user_id": os.environ.get("MEMU_USER_ID", "user001")}
                    if os.environ.get("MEMU_USER_ID")
                    else None,
                ),
                timeout=10.0,
            )

            # 处理检索结果
            retrieved_prompt = ""

            # MemU 返回格式：{"categories": [...], "items": [...], "resources": [...]}
            if isinstance(result, dict):
                # 处理 categories
                categories = result.get("categories", [])
                if categories:
                    retrieved_prompt += "## 记忆分类\n\n"
                    for cat in categories:
                        name = cat.get("name", "")
                        summary = cat.get("summary", "")
                        retrieved_prompt += f"### {name}\n{summary}\n\n"

                # 处理 items
                items = result.get("items", [])
                if items:
                    retrieved_prompt += "## 相关记忆项\n\n"
                    for idx, item in enumerate(items):
                        content = item.get("content", "")
                        if content:
                            retrieved_prompt += f"{idx + 1}. {content}\n\n"

                # 处理 resources
                resources = result.get("resources", [])
                if resources:
                    retrieved_prompt += "## 相关资源\n\n"
                    for res in resources:
                        resource_id = res.get("id", "")
                        resource_type = res.get("type", "")
                        retrieved_prompt += f"- {resource_type}: {resource_id}\n"

            logger.info("成功检索记忆信息")
            return retrieved_prompt

        except TimeoutError:
            logger.warning("检索记忆信息超时，跳过本次检索")
            return ""
        except Exception as e:
            # Check if this is an async context issue (expected in some scenarios)
            error_str = str(e)
            if "Not currently running on any asynchronous event loop" in error_str:
                logger.debug("检索记忆信息: 需要异步上下文")
            else:
                logger.error(f"检索记忆信息失败: {e!s}")
                import traceback

                logger.error(f"详细错误: {traceback.format_exc()}")
            return ""


# 创建全局实例（使用延迟初始化）
_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """获取全局MemoryManager实例（延迟初始化）"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


# 为了向后兼容，创建一个属性访问器
class _MemoryManagerProxy:
    """代理类，用于延迟初始化memory_manager"""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_memory_manager(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(get_memory_manager(), name, value)


memory_manager = _MemoryManagerProxy()  # type: ignore[misc]
logger.info("全局实例 memory_manager 已创建")
