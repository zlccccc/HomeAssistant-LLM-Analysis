import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

# 导入dotenv（不在顶层加载，由调用者决定）
# 导入langgraph相关模块
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

# 导入延迟初始化的管理器
from backend.source.api_layer.home_assistant import hass_manager

# 导入其他必要的模块
from backend.source.api_layer.llm_manager import llm_manager
from backend.source.api_layer.memory_manager import memory_manager

# 导入日志工具
from backend.source.base_layer.utils import logger
from backend.source.command_parser import CommandParser

# 读取环境变量（不自动加载 .env）
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")


# 定义状态类型
class State(BaseModel):
    messages: list[dict[str, Any]] = []
    memorized_messages: list[dict[str, Any]] = []
    entity_data: dict[str, Any] | None = None
    response: str = ""
    parsed_command: dict[str, Any] | None = None
    execution_result: str = ""
    analysis_summary: str = ""
    analysis_details: dict[str, Any] | None = None


class HomeAssistantLLMControllerLangGraph:
    """
    基于LangGraph的Home Assistant LLM控制器
    负责协调大模型和Home Assistant之间的交互
    """

    def __init__(self, auto_initialize: bool = True):
        if auto_initialize:
            # 确保hass_manager已初始化，获取必要的参数
            # Handle case where hass_manager.entity_data is None
            entity_data = hass_manager.entity_data or {}
            self.command_parser = CommandParser(
                entity_data=entity_data.get("non_sensor_data", {}),
                url=hass_manager.url,
                headers=hass_manager.headers,
            )

            # 初始化LangGraph
            self.graph = self._build_graph()
            self.compiled_graph = self.graph.compile()

            logger.info("基于LangGraph的HomeAssistantLLMController已初始化")
        else:
            self.command_parser = None
            self.graph = None
            self.compiled_graph = None

    def _memory_messages(self, state: State) -> dict[str, Any]:
        """
        记忆消息
        使用memory_manager存储对话消息
        """
        import asyncio

        logger.info("处理对话记忆")

        to_memorize_messages = [
            msg for msg in state.messages if msg not in state.memorized_messages
        ]

        # 实际调用记忆功能
        # 尝试运行异步记忆操作，但如果已经在一个事件循环中则跳过
        if to_memorize_messages:
            try:
                # 检查是否已经有运行的事件循环
                asyncio.get_running_loop()
                # 如果有运行的循环，不能用run()，所以只更新内部状态
                logger.debug("检测到正在运行的事件循环，跳过异步记忆调用")
            except RuntimeError:
                # 没有运行的事件循环，可以安全地运行
                try:
                    asyncio.run(memory_manager.memorize_messages(to_memorize_messages))
                except Exception as e:
                    logger.error(f"记忆操作失败: {e}")

        # 返回状态更新，将新消息添加到记忆列表
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
        # 确保有最新的实体数据
        if not state.entity_data:
            # Handle case where hass_manager.entity_data is None
            entity_data = hass_manager.entity_data or {}
            state.entity_data = {
                "sensor_data": entity_data.get("sensor_data", {}),
                "non_sensor_data": entity_data.get("non_sensor_data", {}),
            }

        # 更新命令解析器的实体数据
        self.command_parser.update_entity_data(state.entity_data.get("non_sensor_data", {}))

        return {"entity_data": state.entity_data}

    def _check_for_command(self, state: State) -> dict[str, Any]:
        """
        检查消息是否包含可执行的命令
        """
        logger.info("检查是否包含可执行命令")

        # 获取最新的用户消息
        last_message = state.messages[-1] if state.messages else {"content": ""}
        user_message = last_message.get("content", "")

        # 尝试解析命令
        parsed_result = self.command_parser.parse_and_execute_command(user_message)

        # 将字符串结果包装成字典格式
        parsed_command = {
            "message": parsed_result,
            "should_execute": "成功执行" in parsed_result,  # 如果包含"成功执行"，认为是可执行命令
        }

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

        # 获取最新的用户消息
        last_message = state.messages[-1] if state.messages else {"content": ""}
        user_message = last_message.get("content", "")

        # 实际执行命令
        result = self.command_parser.parse_and_execute_command(user_message)

        # 重新获取实体数据以确保是最新的
        hass_manager.update_entity_data()
        # Handle case where hass_manager.entity_data is None
        entity_data = hass_manager.entity_data or {}
        updated_entity_data = {
            "sensor_data": entity_data.get("sensor_data", {}),
            "non_sensor_data": entity_data.get("non_sensor_data", {}),
        }

        return {
            "execution_result": result,  # 直接使用字符串结果
            "entity_data": updated_entity_data,
        }

    def _create_react_agent(self, tools):
        # 使用llm_manager中已配置好的模型，确保整个应用使用统一的模型配置
        llm_model = llm_manager.get_chat_model()
        agent = create_agent(llm_model, tools)
        return agent

    async def _generate_response_async(self, state: State) -> dict[str, Any]:
        """
        异步生成回复消息（内部实现）
        """
        # 获取最新的用户消息
        last_message = state.messages[-1] if state.messages else {"content": ""}
        user_message = last_message.get("content", "")

        # 如果有执行结果，使用它来生成回复
        if state.execution_result:
            response = state.execution_result
        else:
            # 构建系统提示
            system_prompt = await self._build_system_prompt(state.entity_data, state, user_message)

            to_invoke_messages = [{"role": "system", "content": system_prompt}, *state.messages]

            try:
                # 使用hass_manager中的方法获取MCP工具
                # 检查是否有运行的事件循环
                import asyncio

                try:
                    asyncio.get_running_loop()
                    # 在异步上下文中，直接调用
                    tools = await hass_manager.get_mcp_tools()
                except RuntimeError:
                    # 没有运行的事件循环，跳过MCP工具
                    logger.warning("没有异步事件循环，跳过MCP工具获取")
                    tools = None

                # Only use agent with tools if tools are available and LLM is working
                if tools:
                    agent = self._create_react_agent(tools)
                    response_obj = await agent.ainvoke({"messages": to_invoke_messages})
                    print(f"agent.ainvoke: {response_obj}")

                    formatted_msgs = []
                    if response_obj.get("messages"):
                        for msg in response_obj["messages"]:
                            if isinstance(msg, HumanMessage):
                                formatted_msgs.append(
                                    {"role": "user", "content": getattr(msg, "content", "")}
                                )
                            elif isinstance(msg, SystemMessage):
                                formatted_msgs.append(
                                    {"role": "system", "content": getattr(msg, "content", "")}
                                )
                            else:
                                formatted_msgs.append(
                                    {"role": "assistant", "content": getattr(msg, "content", "")}
                                )

                        # Safely get the last message content
                        last_msg = response_obj["messages"][-1]
                        response = (
                            getattr(last_msg, "content", str(last_msg))
                            if last_msg
                            else str(response_obj)
                        )
                    else:
                        # If no messages in response, just get the content
                        if hasattr(response_obj, "content"):
                            response = getattr(response_obj, "content", "")
                        else:
                            response = str(response_obj)
                else:
                    # Fallback to simple LLM call without tools if no tools available
                    response = llm_manager.call_openai_api(to_invoke_messages)

            except Exception as e:
                logger.error(f"使用Agent调用时出错: {e!s}, 尝试简单调用")
                try:
                    # Fallback to simple LLM call without tools
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

        # 如果有执行结果，直接使用它来生成回复
        if state.execution_result:
            response = state.execution_result
            # 保持原有的消息列表，只添加助手回复
            return {
                "response": response,
                "messages": [*state.messages, {"role": "assistant", "content": response}],
            }
        else:
            # 调用异步方法生成回复
            try:
                result = await self._generate_response_async(state)
            except Exception as e:
                logger.error(f"生成回复时出错: {e!s}")
                import traceback

                traceback.print_exc()
                # 发生错误时返回默认消息
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
        # 填充记忆 - 直接在异步上下文中调用
        retrieved_prompt = ""
        try:
            retrieved_prompt = await memory_manager.retrieve_memory_info()
        except Exception as e:
            logger.error(f"获取记忆信息失败: {e}")

        # 生成设备概览
        device_overview = self._generate_device_overview(entity_data)

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

    def _generate_device_overview(self, entity_data: dict[str, Any]) -> str:
        """
        生成设备概览
        """
        overview = []

        # Check if entity_data is None
        if entity_data is None:
            overview.append("设备数据不可用（可能是因为Home Assistant连接问题）")
            return "\n".join(overview)

        # 获取非传感器设备
        non_sensor_data = entity_data.get("non_sensor_data", {})

        # Additional check in case non_sensor_data itself is None
        if non_sensor_data is not None:
            for device_type, entities in non_sensor_data.items():
                if entities:
                    overview.append(f"- {device_type}设备: {len(entities)}个")
                    # 只列出前3个设备作为示例
                    for _i, entity in enumerate(entities[:3]):
                        name = entity.get("friendly_name", entity.get("entity_id", "未知设备"))
                        state = entity.get("state", "未知状态")
                        overview.append(f"  - {name}: 当前状态为{state}")
                    if len(entities) > 3:
                        overview.append(f"  - ... 等{len(entities) - 3}个设备")
        else:
            overview.append("- 非传感器设备: 数据不可用")

        # 获取传感器数据
        sensor_data = entity_data.get("sensor_data", {})
        # Check if sensor_data is None before accessing its attributes
        if sensor_data is not None:
            numeric_sensors = sensor_data.get("numeric_sensors", [])
            text_sensors = sensor_data.get("text_sensors", [])

            if numeric_sensors:
                overview.append(f"- 数值传感器: {len(numeric_sensors)}个")

            if text_sensors:
                overview.append(f"- 文本传感器: {len(text_sensors)}个")
        else:
            overview.append("- 传感器数据: 不可用")

        if not overview:
            overview.append("暂无可用设备信息")

        return "\n".join(overview)

    async def process_home_assistant_message(
        self, message: str, history: list[tuple[str, str]] | None = None
    ) -> str:
        """
        处理Home Assistant相关消息
        :param message: 用户消息
        :param history: 历史对话
        :return: 响应消息
        """
        logger.info(
            f"开始处理Home Assistant消息: {message[:100]}..."
        )  # Log first 100 chars of message
        start_time = datetime.now()
        try:
            # 构建消息历史
            messages = []
            if history:
                for user_msg, assistant_msg in history:
                    messages.append({"role": "user", "content": user_msg})
                    messages.append({"role": "assistant", "content": assistant_msg})

            # 添加最新消息
            messages.append({"role": "user", "content": message})
            logger.debug(f"构建的消息历史包含 {len(messages)} 条消息")

            # 获取最新的实体数据
            logger.info("更新Home Assistant实体数据")
            hass_manager.update_entity_data()
            # Handle case where hass_manager.entity_data is None or contains None values
            entity_data_from_manager = hass_manager.entity_data or {}
            entity_data = {
                "sensor_data": entity_data_from_manager.get("sensor_data") or {},
                "non_sensor_data": entity_data_from_manager.get("non_sensor_data") or {},
            }
            logger.info(
                f"获取到实体数据 - 传感器: {len(entity_data['sensor_data'].get('numeric_sensors', []) + entity_data['sensor_data'].get('text_sensors', []))}, 设备: {sum(len(v) for v in entity_data['non_sensor_data'].values() if isinstance(v, list))}"
            )

            # 运行图
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
            logger.exception("处理消息时发生异常")  # Also log the full traceback
            return error_msg

    def analyze_entities(
        self, sensor_data: dict[str, Any], non_sensor_data: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """
        分析实体数据
        :param sensor_data: 传感器数据
        :param non_sensor_data: 非传感器数据
        :return: 摘要和分析结果
        """
        try:
            # 准备系统提示
            system_prompt = """
你是一个智能家居分析师，请对提供的Home Assistant实体数据进行全面分析。
请提供：
1. 一个简短的摘要（最多200字）
2. 详细的分析报告，包括设备分类统计、状态概览等
            """

            # 准备实体数据描述
            entity_description = self._prepare_entity_description(sensor_data, non_sensor_data)

            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"实体数据：\n{entity_description}"},
            ]

            # 调用大模型分析
            analysis_result = llm_manager.call_openai_api(messages, temperature=0.3)

            # 生成简短摘要
            summary_prompt = f"""
请将以下分析报告浓缩为一个简短摘要（最多200字）：
{analysis_result}
            """

            summary_messages = [
                {"role": "system", "content": "你是一个摘要生成器。"},
                {"role": "user", "content": summary_prompt},
            ]

            summary = llm_manager.call_openai_api(summary_messages, temperature=0.1)

            # 解析分析结果为结构化数据
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "raw_analysis": analysis_result,
                "sensor_count": self._count_entities(sensor_data),
                "device_count": self._count_entities(non_sensor_data),
            }

            return summary, analysis

        except Exception as e:
            error_msg = f"分析实体时出错: {e!s}"
            logger.error(error_msg)
            return error_msg, {"error": str(e)}

    def _prepare_entity_description(
        self, sensor_data: dict[str, Any], non_sensor_data: dict[str, Any]
    ) -> str:
        """
        准备实体数据描述
        """
        description = []

        # Check if non_sensor_data is None
        if non_sensor_data is not None:
            # 添加非传感器设备信息
            description.append("## 非传感器设备")
            for device_type, entities in non_sensor_data.items():
                description.append(f"### {device_type}")
                for entity in entities[:5]:  # 只显示前5个设备
                    name = entity.get("friendly_name", entity.get("entity_id", "未知设备"))
                    state = entity.get("state", "未知状态")
                    description.append(f"- {name}: {state}")
                if len(entities) > 5:
                    description.append(f"... 等{len(entities) - 5}个设备")
        else:
            description.append("## 非传感器设备\n（设备数据不可用）")

        # Check if sensor_data is None
        if sensor_data is not None:
            # 添加传感器信息
            description.append("## 传感器")
            numeric_sensors = sensor_data.get("numeric_sensors", [])
            text_sensors = sensor_data.get("text_sensors", [])

            description.append(f"### 数值传感器 ({len(numeric_sensors)})")
            for sensor in numeric_sensors[:5]:
                name = sensor.get("friendly_name", sensor.get("entity_id", "未知传感器"))
                state = sensor.get("state", "未知")
                unit = sensor.get("unit_of_measurement", "")
                description.append(f"- {name}: {state}{unit}")

            description.append(f"### 文本传感器 ({len(text_sensors)})")
            for sensor in text_sensors[:5]:
                name = sensor.get("friendly_name", sensor.get("entity_id", "未知传感器"))
                state = sensor.get("state", "未知")
                description.append(f"- {name}: {state}")
        else:
            description.append("## 传感器\n（传感器数据不可用）")

        return "\n".join(description)

    def _count_entities(self, data: dict[str, Any]) -> int:
        """
        计算实体数量
        """
        if isinstance(data, list):
            return len(data)
        elif isinstance(data, dict):
            total = 0
            for value in data.values():
                total += self._count_entities(value)
            return total
        return 0

    def save_analysis_results(self, summary: str, analysis: dict[str, Any]) -> tuple[str, str]:
        """
        保存分析结果到文件
        :param summary: 分析摘要
        :param analysis: 分析结果
        :return: 摘要文件路径和分析文件路径
        """
        try:
            # 确保输出目录存在
            output_dir = Path.cwd() / OUTPUT_DIR
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_file = output_dir / f"entity_summary_{timestamp}.txt"
            analysis_file = output_dir / f"entity_analysis_{timestamp}.json"

            # 保存摘要
            with (summary_file).open("w", encoding="utf-8") as f:
                f.write(summary)

            # 保存分析结果
            with (analysis_file).open("w", encoding="utf-8") as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)

            logger.info(f"分析结果已保存到: {summary_file} 和 {analysis_file}")
            return summary_file, analysis_file

        except Exception as e:
            error_msg = f"保存分析结果时出错: {e!s}"
            logger.error(error_msg)
            return None, None


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
