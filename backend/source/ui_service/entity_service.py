"""实体服务

提供设备和传感器数据查询和控制服务。
"""

from pathlib import Path
from typing import Any

from backend.source.api_layer.home_assistant import hass_manager
from backend.source.infrastructure.utils import logger
from backend.source.services.entity_analyzer import entity_analyzer


class EntityService:
    """
    实体服务类

    提供设备和传感器数据的查询、控制和分析功能。
    所有方法返回纯 Python 数据类型，不依赖 Gradio。
    """

    # ==================== 设备控制服务 ====================

    def get_device_groups(self, device_type: str) -> list[str]:
        """
        获取指定设备类型的分组列表

        Args:
            device_type: 设备类型（如 "light", "switch" 等）

        Returns:
            分组名称列表，如果设备类型不存在则返回空列表

        Example:
            >>> service = EntityService()
            >>> groups = service.get_device_groups("light")
            >>> isinstance(groups, list)
            True
        """
        entity_data = self._get_entity_data()
        non_sensor_data = entity_data.get("non_sensor_data", {})

        if not device_type or device_type not in non_sensor_data:
            return []

        entities = non_sensor_data.get(device_type, [])
        grouped = hass_manager.group_entities_by_name(entities)
        return list(grouped.keys())

    def get_device_list(self, device_type: str, group_name: str) -> list[str]:
        """
        获取指定分组下的设备列表

        Args:
            device_type: 设备类型
            group_name: 分组名称

        Returns:
            设备友好名称列表

        Example:
            >>> service = EntityService()
            >>> devices = service.get_device_list("light", "客厅")
            >>> isinstance(devices, list)
            True
        """
        entity_data = self._get_entity_data()
        non_sensor_data = entity_data.get("non_sensor_data", {})

        if not device_type or not group_name or device_type not in non_sensor_data:
            return []

        entities = non_sensor_data.get(device_type, [])
        grouped = hass_manager.group_entities_by_name(entities)

        if group_name not in grouped:
            return []

        return [
            e.get("friendly_name", e.get("entity_id", "未知"))
            for e in grouped[group_name]
        ]

    def get_device_status(
        self, device_type: str, group_name: str, device_name: str
    ) -> dict[str, Any]:
        """
        获取设备状态信息

        Args:
            device_type: 设备类型
            group_name: 分组名称
            device_name: 设备名称

        Returns:
            包含 entity_id, state, last_updated 的字典

        Example:
            >>> service = EntityService()
            >>> status = service.get_device_status("light", "客厅", "吸顶灯")
            >>> "entity_id" in status
            True
        """
        entity_data = self._get_entity_data()
        non_sensor_data = entity_data.get("non_sensor_data", {})

        if not device_type or not group_name or device_type not in non_sensor_data:
            return {}

        entities = non_sensor_data.get(device_type, [])
        grouped = hass_manager.group_entities_by_name(entities)

        if group_name not in grouped:
            return {}

        for entity in grouped[group_name]:
            if entity.get("friendly_name", entity.get("entity_id", "未知")) == device_name:
                return {
                    "entity_id": entity.get("entity_id", "未知"),
                    "state": entity.get("state", "未知"),
                    "last_updated": entity.get("last_updated", "未知"),
                }

        return {}

    def control_device(
        self, device_type: str, group_name: str, device_name: str
    ) -> dict[str, Any]:
        """
        控制设备开关状态

        Args:
            device_type: 设备类型
            group_name: 分组名称
            device_name: 设备名称

        Returns:
            包含 success 和 message 的字典

        Example:
            >>> service = EntityService()
            >>> result = service.control_device("light", "客厅", "吸顶灯")
            >>> "success" in result
            True
        """
        entity_data = self._get_entity_data()
        non_sensor_data = entity_data.get("non_sensor_data", {})

        if not device_type or not group_name or device_type not in non_sensor_data:
            return {
                "success": False,
                "message": "参数无效",
                "new_state": None,
                "status": None,
            }

        entities = non_sensor_data.get(device_type, [])
        grouped = hass_manager.group_entities_by_name(entities)

        if group_name not in grouped:
            return {
                "success": False,
                "message": f"未找到分组 {group_name}",
                "new_state": None,
                "status": None,
            }

        for entity in grouped[group_name]:
            if entity.get("friendly_name", entity.get("entity_id", "未知")) == device_name:
                entity_id = entity.get("entity_id", "未知")
                current_state = entity.get("state", "未知")
                new_state = "off" if current_state == "on" else "on"

                success_message = hass_manager.call_home_assistant_service(
                    entity_id, f"turn_{new_state}"
                )

                if "成功" in success_message:
                    hass_manager.update_entity_data()
                    return {
                        "success": True,
                        "message": f"控制成功：已将 {device_name} {new_state}",
                        "new_state": new_state,
                        "status": self.get_device_status(device_type, group_name, device_name),
                    }
                else:
                    return {
                        "success": False,
                        "message": f"控制失败：{success_message}",
                        "new_state": None,
                        "status": None,
                    }

        return {
            "success": False,
            "message": f"控制失败：未找到设备 {device_name}",
            "new_state": None,
            "status": None,
        }

    def refresh_devices(self) -> list[str]:
        """
        刷新设备列表

        Returns:
            可用设备类型列表

        Example:
            >>> service = EntityService()
            >>> types = service.refresh_devices()
            >>> isinstance(types, list)
            True
        """
        hass_manager.update_entity_data()
        entity_data = self._get_entity_data()
        non_sensor_data = entity_data.get("non_sensor_data", {})
        device_types = list(non_sensor_data.keys())
        return device_types if device_types else ["无可用设备"]

    # ==================== 传感器数据服务 ====================

    def get_sensor_groups(self, sensor_type: str) -> list[str]:
        """
        获取传感器分组列表

        Args:
            sensor_type: 传感器类型 ("numeric" 或 "text")

        Returns:
            分组名称列表

        Example:
            >>> service = EntityService()
            >>> groups = service.get_sensor_groups("numeric")
            >>> isinstance(groups, list)
            True
        """
        backend_sensor_type = self._map_sensor_type(sensor_type)
        if not backend_sensor_type:
            return []

        sensor_key = f"{backend_sensor_type}_by_group"
        entity_data = self._get_entity_data()
        sensor_data = entity_data.get("sensor_data", {})

        if sensor_key not in sensor_data:
            return []

        return list(sensor_data.get(sensor_key, {}).keys())

    def get_sensor_list(self, sensor_type: str, group_name: str) -> list[str]:
        """
        获取传感器列表

        Args:
            sensor_type: 传感器类型
            group_name: 分组名称

        Returns:
            传感器友好名称列表

        Example:
            >>> service = EntityService()
            >>> sensors = service.get_sensor_list("numeric", "temperature")
            >>> isinstance(sensors, list)
            True
        """
        backend_sensor_type = self._map_sensor_type(sensor_type)
        if not backend_sensor_type or not group_name:
            return []

        sensor_key = f"{backend_sensor_type}_by_group"
        entity_data = self._get_entity_data()
        sensor_data = entity_data.get("sensor_data", {})

        if sensor_key not in sensor_data or group_name not in sensor_data.get(sensor_key, {}):
            return []

        sensors = sensor_data.get(sensor_key, {}).get(group_name, [])
        return [s.get("friendly_name", s.get("entity_id", "未知")) for s in sensors]

    def get_sensor_info(
        self, sensor_type: str, group_name: str, sensor_name: str
    ) -> dict[str, Any]:
        """
        获取传感器信息

        Args:
            sensor_type: 传感器类型
            group_name: 分组名称
            sensor_name: 传感器名称

        Returns:
            包含传感器详细信息的字典

        Example:
            >>> service = EntityService()
            >>> info = service.get_sensor_info("numeric", "temperature", "温度")
            >>> "entity_id" in info
            True
        """
        backend_sensor_type = self._map_sensor_type(sensor_type)
        if not backend_sensor_type or not group_name or not sensor_name:
            return {}

        sensor_key = f"{backend_sensor_type}_by_group"
        entity_data = self._get_entity_data()
        sensor_data = entity_data.get("sensor_data", {})

        if sensor_key not in sensor_data or group_name not in sensor_data.get(sensor_key, {}):
            return {}

        for sensor in sensor_data.get(sensor_key, {}).get(group_name, []):
            if sensor.get("friendly_name", sensor.get("entity_id", "未知")) == sensor_name:
                entity_id = sensor.get("entity_id", "未知")
                state = sensor.get("state", "未知")
                unit = sensor.get("unit_of_measurement", sensor.get("unit", ""))
                last_updated = sensor.get("last_updated", "未知")

                result = {
                    "entity_id": entity_id,
                    "friendly_name": sensor.get("friendly_name", "未知"),
                    "state": f"{state}{unit}",
                    "last_updated": last_updated,
                }

                # 处理额外属性
                if "external_attributes" in sensor:
                    ext_attrs = sensor["external_attributes"]
                    if ext_attrs:
                        result["external_attributes"] = {}
                        for attr_name, attr_value in ext_attrs.items():
                            if isinstance(attr_value, str) and len(attr_value) > 50:
                                attr_value = attr_value[:50] + "..."
                            result["external_attributes"][attr_name] = attr_value

                return result

        return {}

    def refresh_sensors(self) -> list[str]:
        """
        刷新传感器列表

        Returns:
            可用传感器类型列表

        Example:
            >>> service = EntityService()
            >>> types = service.refresh_sensors()
            >>> "numeric" in types
            True
        """
        hass_manager.update_entity_data()
        return ["numeric", "text"]

    def analyze_all_entities(self) -> dict[str, Any]:
        """
        分析所有实体

        Returns:
            包含 success 和 message/file_paths 的字典

        Example:
            >>> service = EntityService()
            >>> result = service.analyze_all_entities()
            >>> "success" in result
            True
        """
        try:
            hass_manager.update_entity_data()

            entity_data = self._get_entity_data()
            sensor_data = entity_data.get("sensor_data", {})
            non_sensor_data = entity_data.get("non_sensor_data", {})

            summary, analysis = entity_analyzer.analyze_entities(
                sensor_data,
                non_sensor_data,
            )

            summary_file, analysis_file = entity_analyzer.save_analysis_results(
                summary, analysis
            )

            if summary_file and analysis_file:
                return {
                    "success": True,
                    "message": f"分析完成！\n实体摘要已保存到: {summary_file}\n分析报告已保存到: {analysis_file}",
                    "summary_file": summary_file,
                    "analysis_file": analysis_file,
                }
            else:
                return {
                    "success": False,
                    "message": "分析失败：无法保存结果",
                }
        except Exception as e:
            logger.error(f"分析实体时出错: {e!s}")
            return {
                "success": False,
                "message": f"分析失败：{e!s}",
            }

    # ==================== 辅助方法 ====================

    def _get_entity_data(self) -> dict[str, Any]:
        """获取实体数据，确保返回非空的字典"""
        if hass_manager.entity_data is None:
            return {"sensor_data": {}, "non_sensor_data": {}}
        return hass_manager.entity_data

    def _map_sensor_type(self, sensor_type: str) -> str:
        """
        转换UI中的传感器类型名称为后端使用的类型名称

        Args:
            sensor_type: UI中的类型名称 ("numeric" 或 "text")

        Returns:
            后端使用的类型名称 ("numeric_sensors" 或 "text_sensors")
        """
        sensor_type_map = {"numeric": "numeric_sensors", "text": "text_sensors"}
        return sensor_type_map.get(sensor_type, "")


# 创建全局单例实例
entity_service = EntityService()
