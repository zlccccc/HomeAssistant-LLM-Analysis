"""Entity analysis using LLM.

Provides entity analysis functionality that can be used independently
by both langgraph_controller and ui_service.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.source.api_layer.llm_manager import llm_manager
from backend.source.infrastructure.utils import logger

# 读取环境变量
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")


class EntityAnalyzer:
    """
    实体分析器类

    使用 LLM 分析 Home Assistant 实体数据。
    """

    def analyze_entities(
        self, sensor_data: dict[str, Any], non_sensor_data: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """
        分析实体数据

        Args:
            sensor_data: 传感器数据
            non_sensor_data: 非传感器数据

        Returns:
            摘要和分析结果的元组

        Example:
            >>> analyzer = EntityAnalyzer()
            >>> sensor_data = {"numeric_sensors": [...], "text_sensors": [...]}
            >>> non_sensor_data = {"light": [...], "switch": [...]}
            >>> summary, analysis = analyzer.analyze_entities(sensor_data, non_sensor_data)
            >>> print(summary)
            "系统包含5个传感器和10个设备..."
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

        Args:
            summary: 分析摘要
            analysis: 分析结果

        Returns:
            摘要文件路径和分析文件路径的元组

        Example:
            >>> analyzer = EntityAnalyzer()
            >>> summary = "系统包含5个传感器..."
            >>> analysis = {"timestamp": "...", "raw_analysis": "..."}
            >>> summary_file, analysis_file = analyzer.save_analysis_results(summary, analysis)
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
            return str(summary_file), str(analysis_file)

        except Exception as e:
            error_msg = f"保存分析结果时出错: {e!s}"
            logger.error(error_msg)
            return None, None

    def _generate_device_overview(self, entity_data: dict[str, Any]) -> str:
        """
        生成设备概览

        用于构建系统提示词中的设备概览部分。

        Args:
            entity_data: 包含 sensor_data 和 non_sensor_data 的字典

        Returns:
            设备概览字符串

        Example:
            >>> analyzer = EntityAnalyzer()
            >>> entity_data = {"sensor_data": {...}, "non_sensor_data": {...}}
            >>> overview = analyzer._generate_device_overview(entity_data)
            >>> print(overview)
            "- light设备: 5个
             - 数值传感器: 3个"
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


# 创建全局单例实例
entity_analyzer = EntityAnalyzer()
