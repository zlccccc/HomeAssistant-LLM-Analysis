"""LangGraph controller for Home Assistant LLM integration.

Provides LangGraph workflow orchestration for processing Home Assistant messages.
"""

from datetime import datetime
from typing import Any

# Import LangGraph related modules
from langchain.agents import create_agent
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

# Import lazy-initialized managers
from backend.source.api_layer.home_assistant import hass_manager
from backend.source.api_layer.llm_manager import llm_manager
from backend.source.api_layer.memory_manager import memory_manager

# Import services
from backend.source.services.command_parser import CommandParser
from backend.source.services.entity_analyzer import entity_analyzer

# Import logger
from backend.source.infrastructure.utils import logger


# Define state type
class State(BaseModel):
    messages: list[dict[str, Any]] = []
    memorized_messages: list[dict[str, Any]] = []
    entity_data: dict[str, Any] | None = None
    response: str = ""
    parsed_command: dict[str, Any] | None = None
    execution_result: str = ""


class HomeAssistantLLMControllerLangGraph:
    """
    基于LangGraph的Home Assistant LLM控制器
    负责协调大模型和Home Assistant之间的交互
    """

    def __init__(self, auto_initialize: bool = True):
        if auto_initialize:
            self.command_parser = CommandParser(
                entity_data=(hass_manager.entity_data or {}).get("non_sensor_data", {}),
                url=hass_manager.url,
                headers=hass_manager.headers,
            )

            self.graph = self._build_graph()
            self.compiled_graph = self.graph.compile()

            logger.info("基于LangGraph的HomeAssistantLLMController已初始化")
        else:
            self.command_parser = None
            self.graph = None
            self.compiled_graph = None

    async def _memory_messages(self, state: State) -> dict[str, Any]:
        """
        记忆消息
        使用memory_manager存储对话消息
        """
        logger.info("处理对话记忆")

        to_memorize_messages = [
            msg for msg in state.messages if msg not in state.memorized_messages
        ]

        # 边界条件检查：只有在有消息需要记忆且记忆管理器可用时才执行
        if to_memorize_messages and memory_manager.memory:
            try:
                await memory_manager.memorize_messages(to_memorize_messages)
            except Exception as e:
                logger.error(f"记忆操作失败: {e}")

        return {"memorized_messages": state.memorized_messages + to_memorize_messages}

    def _build_graph(self) -> StateGraph:
        """
        构建LangGraph状态图
        """
        graph = StateGraph(State)

        # 添加节点
        graph.add_node("analyze_message", self._analyze_message)
        graph.add_node("check_for_command", self._check_for_command)
        graph.add_node("execute_command", self._execute_command)
        graph.add_node("generate_response", self._generate_response)
        graph.add_node("memory_messages", self._memory_messages)

        # 添加边缘
        graph.set_entry_point("analyze_message")
        graph.add_edge("analyze_message", "memory_messages")
        graph.add_edge("memory_messages", "check_for_command")
        graph.add_conditional_edges(
            "check_for_command",
            self._should_execute_command,
            {"execute": "execute_command", "respond": "generate_response"},
        )
        graph.add_edge("execute_command", "generate_response")
        graph.add_edge("generate_response", END)

        return graph

    def _analyze_message(self, state: State) -> dict[str, Any]:
        """
        分析用户消息
        """
        logger.info("分析用户消息")
        if not state.entity_data:
            entity_data = hass_manager.entity_data or {}
            state.entity_data = {
                "sensor_data": entity_data.get("sensor_data", {}),
                "non_sensor_data": entity_data.get("non_sensor_data", {}),
            }

        # CommandParser 期望直接传入 non_sensor_data，而不是包含它的 entity_data
        self.command_parser.update_entity_data(
            {"non_sensor_data": state.entity_data.get("non_sensor_data", {})}
        )

        return {"entity_data": state.entity_data}

    def _check_for_command(self, state: State) -> dict[str, Any]:
        """
        检查消息是否包含可执行的命令
        """
        logger.info("检查是否包含可执行命令")

        last_message = state.messages[-1] if state.messages else {"content": ""}
        user_message = last_message.get("content", "")
        parsed_result = self.command_parser.parse_and_execute_command(user_message)

        # 记录解析结果
        logger.info(f"命令解析结果: {parsed_result}")

        parsed_command = {
            "message": parsed_result,
            "should_execute": "成功执行" in parsed_result,
        }

        logger.info(f"是否应该执行命令: {parsed_command['should_execute']}")

        return {"parsed_command": parsed_command}

    def _should_execute_command(self, state: State) -> str:
        """
        决定是否执行命令
        """
        if state.parsed_command and state.parsed_command.get("should_execute", False):
            return "execute"
        return "respond"

    def _execute_command(self, state: State) -> dict[str, Any]:
        """
        执行解析出的命令
        """
        logger.info(f"执行命令: {state.parsed_command}")

        last_message = state.messages[-1] if state.messages else {"content": ""}
        user_message = last_message.get("content", "")
        result = self.command_parser.parse_and_execute_command(user_message)

        hass_manager.update_entity_data()
        entity_data = hass_manager.entity_data or {}
        updated_entity_data = {
            "sensor_data": entity_data.get("sensor_data", {}),
            "non_sensor_data": entity_data.get("non_sensor_data", {}),
        }

        return {
            "execution_result": result,
            "entity_data": updated_entity_data,
        }

    def _create_react_agent(self, tools):
        """创建ReAct代理，使用统一配置的模型"""
        llm_model = llm_manager.get_chat_model()
        return create_agent(llm_model, tools)

    def _extract_response_content(self, response_obj: Any) -> str:
        """从代理响应中提取内容"""
        if response_obj.get("messages"):
            # 安全地获取最后一条消息的内容
            last_msg = response_obj["messages"][-1]
            if last_msg:
                return getattr(last_msg, "content", str(last_msg))
        if hasattr(response_obj, "content"):
            return getattr(response_obj, "content", "")
        return str(response_obj)

    async def _generate_response_async(self, state: State) -> dict[str, Any]:
        """
        异步生成回复消息（内部实现）
        """
        last_message = state.messages[-1] if state.messages else {"content": ""}
        user_message = last_message.get("content", "")

        if state.execution_result:
            response = state.execution_result
        else:
            system_prompt = await self._build_system_prompt(state.entity_data, state, user_message)
            to_invoke_messages = [{"role": "system", "content": system_prompt}, *state.messages]

            try:
                import asyncio

                try:
                    asyncio.get_running_loop()
                    tools = await hass_manager.get_mcp_tools()
                except RuntimeError:
                    logger.warning("没有异步事件循环，跳过MCP工具获取")
                    tools = None

                if tools:
                    agent = self._create_react_agent(tools)
                    response_obj = await agent.ainvoke({"messages": to_invoke_messages})
                    print(f"agent.ainvoke: {response_obj}")
                    response = self._extract_response_content(response_obj)
                else:
                    response = llm_manager.call_openai_api(to_invoke_messages)

            except Exception as e:
                logger.error(f"使用Agent调用时出错: {e!s}, 尝试简单调用")
                try:
                    response = llm_manager.call_openai_api(to_invoke_messages)
                except Exception as fallback_e:
                    logger.error(f"简单调用也失败: {fallback_e!s}")
                    response = f"抱歉，我遇到了一些技术问题: {fallback_e!s}"

        return {
            "response": response,
            "messages": [*state.messages, {"role": "assistant", "content": response}],
        }

    async def _generate_response(self, state: State) -> dict[str, Any]:
        """
        生成回复消息（异步版本）
        """
        logger.info("生成回复消息")

        if state.execution_result:
            response = state.execution_result
            return {
                "response": response,
                "messages": [*state.messages, {"role": "assistant", "content": response}],
            }
        else:
            try:
                result = await self._generate_response_async(state)
            except Exception as e:
                logger.error(f"生成回复时出错: {e!s}")
                import traceback

                traceback.print_exc()
                error_msg = f"抱歉，生成回复时出错: {e!s}"
                return {
                    "response": error_msg,
                    "messages": [*state.messages, {"role": "assistant", "content": error_msg}],
                }

            return result

    async def _build_system_prompt(
        self, entity_data: dict[str, Any], state: State, user_message: str
    ) -> str:
        """
        构建系统提示，包含实体信息
        """
        # 填充记忆 - 边界条件检查：记忆管理器可用时才调用
        retrieved_prompt = ""
        if memory_manager.memory:
            try:
                retrieved_prompt = await memory_manager.retrieve_memory_info()
            except Exception as e:
                logger.error(f"获取记忆信息失败: {e}")

        # 生成设备概览 - 使用 entity_analyzer
        device_overview = entity_analyzer._generate_device_overview(entity_data)

        system_prompt = f"""
你是一个智能家居助手，专门帮助用户控制和了解他们的Home Assistant智能家居设备。

当前可用设备概览：
{device_overview}

{"这里是和用户有关的记忆信息:" if retrieved_prompt else ""}
{retrieved_prompt}

请根据用户的问题或请求，提供有用的回答。如果你无法回答，请坦诚告知。
对于设备控制命令，请使用提供的工具。
        """

        return system_prompt

    async def process_home_assistant_message(
        self, message: str, history: list[tuple[str, str]] | list[dict[str, str]] | None = None
    ) -> str:
        """
        处理Home Assistant相关消息

        Args:
            message: 用户消息
            history: 历史对话，支持两种格式：
                - 元组格式: [(user_msg, assistant_msg), ...]
                - 字典格式: [{"role": "user", "content": "..."}, ...]

        Returns:
            响应消息

        Example:
            >>> controller = HomeAssistantLLMControllerLangGraph()
            >>> response = await controller.process_home_assistant_message(
            ...     message="打开客厅灯",
            ...     history=[("你好", "你好！")]
            ... )
            >>> print(response)
            "好的，我来帮您打开客厅灯。"
        """
        # 边界条件检查
        if not message or not isinstance(message, str):
            return "无效的消息"

        message = message.strip()
        if not message:
            return "消息为空"

        if not self.compiled_graph:
            return "控制器未正确初始化"

        logger.info(f"接收到用户输入: {message[:100]}...")
        logger.info(f"开始处理Home Assistant消息: {message[:100]}...")
        start_time = datetime.now()

        # 构建消息历史
        messages = []
        if history:
            for h in history:
                if isinstance(h, dict) and "role" in h and "content" in h:
                    # 字典格式: {"role": "user/assistant", "content": "..."}
                    messages.append(h)
                elif isinstance(h, (tuple, list)) and len(h) >= 2:
                    # 元组格式: (user_msg, assistant_msg)
                    messages.append({"role": "user", "content": h[0]})
                    messages.append({"role": "assistant", "content": h[1]})

        messages.append({"role": "user", "content": message})
        logger.debug(f"构建的消息历史包含 {len(messages)} 条消息")

        # 更新实体数据
        logger.info("更新Home Assistant实体数据")
        hass_manager.update_entity_data()
        entity_data_from_manager = hass_manager.entity_data or {}
        entity_data = {
            "sensor_data": entity_data_from_manager.get("sensor_data") or {},
            "non_sensor_data": entity_data_from_manager.get("non_sensor_data") or {},
        }
        logger.info(
            f"获取到实体数据 - 传感器: {len(entity_data['sensor_data'].get('numeric_sensors', []) + entity_data['sensor_data'].get('text_sensors', []))}, 设备: {sum(len(v) for v in entity_data['non_sensor_data'].values() if isinstance(v, list))}"
        )

        try:
            # 运行LangGraph处理流程
            logger.info("开始运行LangGraph处理流程")
            config = {"configurable": {"thread_id": "home_assistant_thread"}}
            result = await self.compiled_graph.ainvoke(
                {"messages": messages, "entity_data": entity_data}, config=config
            )
            logger.info("LangGraph处理完成")

            response = result.get("response", "抱歉，我无法处理您的请求")
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"处理完成，响应长度: {len(response)} 字符，耗时: {processing_time:.2f}秒")
            return response

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"处理消息时出错: {e!s}"
            logger.error(error_msg)
            logger.error(f"处理失败，耗时: {processing_time:.2f}秒")
            logger.exception("处理消息时发生异常")
            return error_msg

    # Delegate methods to entity_analyzer for backward compatibility
    def analyze_entities(
        self, sensor_data: dict[str, Any], non_sensor_data: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """
        分析实体数据（委托给 entity_analyzer）

        保留此方法以保持向后兼容性。
        """
        return entity_analyzer.analyze_entities(sensor_data, non_sensor_data)

    def save_analysis_results(self, summary: str, analysis: dict[str, Any]) -> tuple[str, str]:
        """
        保存分析结果到文件（委托给 entity_analyzer）

        保留此方法以保持向后兼容性。
        """
        return entity_analyzer.save_analysis_results(summary, analysis)

    def _generate_device_overview(self, entity_data: dict[str, Any]) -> str:
        """
        生成设备概览（委托给 entity_analyzer）

        保留此方法以保持向后兼容性。
        """
        return entity_analyzer._generate_device_overview(entity_data)

    def _prepare_entity_description(
        self, sensor_data: dict[str, Any], non_sensor_data: dict[str, Any]
    ) -> str:
        """
        准备实体描述（委托给 entity_analyzer）

        保留此方法以保持向后兼容性。
        """
        return entity_analyzer._prepare_entity_description(sensor_data, non_sensor_data)

    def _count_entities(self, data: Any) -> int:
        """
        统计实体数量（委托给 entity_analyzer）

        保留此方法以保持向后兼容性。
        """
        return entity_analyzer._count_entities(data)


# 创建全局实例（使用延迟初始化）
_hass_llm_controller_langgraph: HomeAssistantLLMControllerLangGraph | None = None


def get_hass_llm_controller_langgraph() -> HomeAssistantLLMControllerLangGraph:
    """获取全局HomeAssistantLLMControllerLangGraph实例（延迟初始化）"""
    global _hass_llm_controller_langgraph
    if _hass_llm_controller_langgraph is None:
        _hass_llm_controller_langgraph = HomeAssistantLLMControllerLangGraph()
    return _hass_llm_controller_langgraph


# 为了向后兼容，创建一个属性访问器
class _HassLLMControllerLangGraphProxy:
    """代理类，用于延迟初始化hass_llm_controller_langgraph"""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_hass_llm_controller_langgraph(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(get_hass_llm_controller_langgraph(), name, value)


hass_llm_controller_langgraph = _HassLLMControllerLangGraphProxy()  # type: ignore[misc]
logger.info("全局实例 hass_llm_controller_langgraph 已创建")
