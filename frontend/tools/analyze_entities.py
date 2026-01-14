import os
from typing import Any

import requests
from dotenv import load_dotenv

# 导入日志工具
from backend.source.infrastructure.utils import logger

# 读取环境变量（不自动加载 .env，由调用者决定）
HA_URL = os.getenv("HA_URL", "http://localhost:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}

# 延迟导入的模块（只在主程序运行时需要）
hass_manager = None
hass_llm_controller = None


# 从get_sensor.py合并的功能函数
def get_entity_info(entity_id: str) -> dict[str, Any] | None:
    """
    获取单个实体的详细信息

    :param entity_id: 实体ID
    :return: 实体信息字典, 如果实体不存在返回None
    """
    try:
        url = f"{HA_URL}/api/states/{entity_id}"
        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"获取实体 {entity_id} 信息失败: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"获取实体 {entity_id} 信息异常: {e!s}")
        return None


def get_entity_history(entity_id: str, hours: int = 24) -> list[dict[str, Any]] | None:
    """
    获取实体的历史数据

    :param entity_id: 实体ID
    :param hours: 历史数据的时间范围(小时)
    :return: 历史数据列表, 如果获取失败返回None
    """
    try:
        url = f"{HA_URL}/api/history/period"
        # 计算开始时间(现在减去hours小时)
        import datetime

        start_time = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()

        params = {
            "start_time": start_time,
            "filter_entity_id": entity_id,
            "end_time": datetime.datetime.now().isoformat(),
        }

        response = requests.get(url, headers=HEADERS, params=params, timeout=30)

        if response.status_code == 200:
            history_data = response.json()
            return history_data[0] if history_data else []
        else:
            logger.error(f"获取实体 {entity_id} 历史数据失败: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"获取实体 {entity_id} 历史数据异常: {e!s}")
        return None


def get_all_entities() -> list[dict[str, Any]] | None:
    """
    获取所有实体的列表

    :return: 实体列表, 如果获取失败返回None
    """
    try:
        url = f"{HA_URL}/api/states"
        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"获取所有实体失败: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"获取所有实体异常: {e!s}")
        return None


def main() -> None:
    """
    主函数, 用于直接运行实体分析
    """
    # 加载环境变量（仅在作为主程序运行时）
    load_dotenv()

    # 延迟导入模块（避免测试时触发连接）
    from backend.source.api_layer.home_assistant import hass_manager as _hass_manager
    from backend.source.services.langgraph_controller import (
        hass_llm_controller_langgraph as _hass_llm_controller,
    )

    logger.info("开始实体分析...")

    # 获取实体数据
    sensor_data, non_sensor_data = _hass_manager.get_and_classify_entities()
    # 更新实体数据
    entity_excel_file = _hass_manager.export_to_excel(sensor_data, non_sensor_data)

    # 打印实体统计信息(从get_sensor.py合并)
    logger.info("\n实体统计信息:")

    if sensor_data:
        logger.info("\n传感器:")
        logger.info(f"- 数值型传感器: {len(sensor_data.get('numeric_sensors', []))}")
        logger.info(f"- 文本型传感器: {len(sensor_data.get('text_sensors', []))}")
        logger.info(f"- 无效传感器: {len(sensor_data.get('invalid_sensors', []))}")

    if non_sensor_data:
        logger.info("\n非传感器实体:")
        for entity_type, entities in non_sensor_data.items():
            logger.info(f"- {entity_type}: {len(entities)}个")

    # 运行分析
    summary, analysis = _hass_llm_controller.analyze_entities(sensor_data, non_sensor_data)

    # 打印分析结果
    logger.info("\n实体摘要:")
    logger.info(summary)

    logger.info("\n分析结果:")
    logger.info(analysis)

    # 保存结果
    summary_file, analysis_file = _hass_llm_controller.save_analysis_results(summary, analysis)

    if summary_file and analysis_file and entity_excel_file:
        logger.info("\n分析结果已保存到以下文件:")
        logger.info(f"- 实体摘要: {summary_file}")
        logger.info(f"- 分析报告: {analysis_file}")
        logger.info(f"- 实体Excel文件: {entity_excel_file}")
    else:
        logger.error("\n保存分析结果失败")
        logger.error(f"- 实体摘要: {summary_file}")
        logger.error(f"- 分析报告: {analysis_file}")
        logger.error(f"- 实体Excel文件: {entity_excel_file}")


if __name__ == "__main__":
    main()
