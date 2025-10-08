import requests
import json
import re
import os
import sys
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# 添加当前目录到系统路径
if __file__ in sys.path:
    sys.path.remove(__file__)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入日志记录器
from utils import logger

# 导入配置和模型模块
from config import HA_URL, HA_TOKEN, OUTPUT_DIR, HEADERS

class HomeAssistantManager:
    """
    Home Assistant管理类，处理与Home Assistant的所有交互
    """
    
    def __init__(self):
        self.url = HA_URL
        self.token = HA_TOKEN
        self.headers = HEADERS
        self.entity_data = {}
        self.current_entity_summary = ""
        logger.info("正在初始化Home Assistant数据...")
        self.update_entity_data()
    
    def group_entities_by_name(self, entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        将实体按名称分组
        分组规则：
        1. 优先从friendly_name中提取分组信息（如"客厅温度"分组为"客厅"）
        2. 如果friendly_name不可用，则从entity_id中提取位置/区域信息
        3. 使用常见的分隔符和规则识别位置/区域信息
        """
        grouped_entities = {}
        
        # 常见的位置关键词（可根据需要扩展）
        location_keywords = [
            "客厅", "卧室", "厨房", "卫生间", "浴室", "书房", "儿童房", "主卧", "次卧", 
            "阳台", "门厅", "走廊", "餐厅", "车库", "花园", "院子", "阁楼"
        ]
        
        for entity in entities:
            group_name = "其他"
            
            # 尝试从friendly_name提取分组
            friendly_name = entity.get("friendly_name", "")
            if friendly_name:
                # 检查是否包含常见位置关键词
                for keyword in location_keywords:
                    if keyword in friendly_name:
                        group_name = keyword
                        break
                
                # 如果没有匹配到关键词，尝试按分隔符分割
                if group_name == "其他":
                    # 尝试按常见分隔符分割
                    separators = ["-", "_", "(", "（", " "]
                    for sep in separators:
                        if sep in friendly_name:
                            parts = friendly_name.split(sep, 1)
                            if parts:
                                group_name = parts[0].strip()
                                break
            
            # 如果friendly_name未能提取分组，尝试从entity_id提取
            if group_name == "其他":
                entity_id = entity.get("entity_id", "")
                # 提取entity_type部分
                if "." in entity_id:
                    entity_type, entity_name = entity_id.split(".", 1)
                    # 尝试按下划线分割entity_name
                    if "_" in entity_name:
                        parts = entity_name.split("_")
                        # 通常第一个或前两个部分是位置信息
                        if parts:
                            # 如果是类似 "living_room_temperature" 的格式
                            if len(parts) > 1:
                                group_name = parts[0] + "_" + parts[1]
                            else:
                                group_name = parts[0]
            
            # 将实体添加到对应分组
            if group_name not in grouped_entities:
                grouped_entities[group_name] = []
            grouped_entities[group_name].append(entity)
        
        # 对分组进行排序
        sorted_groups = {}
        for group in sorted(grouped_entities.keys()):
            # 对同一分组内的实体按名称排序
            sorted_entities = sorted(grouped_entities[group], key=lambda s: s.get("friendly_name", s.get("entity_id", "")))
            sorted_groups[group] = sorted_entities
        
        return sorted_groups
    
    def get_and_classify_entities(self) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, List[Dict[str, Any]]]]]:
        """
        获取Home Assistant中所有实体，并进行分类
        :return: (sensor实体分类结果, 非sensor实体分类结果)
        """
        # 调用API获取所有实体
        all_entities_url = f"{self.url}/api/states"
        try:
            response = requests.get(all_entities_url, headers=self.headers, timeout=15)
            if response.status_code == 401:
                logger.error("获取实体失败！状态码：401，原因：未授权访问")
                logger.error("\n可能的解决方案：")
                logger.error("1. 检查访问令牌是否正确 - 令牌格式应为以Bearer开头的长字符串")
                logger.error("2. 生成新的长生命周期访问令牌")
                return None, None
            elif response.status_code != 200:
                logger.error(f"获取实体失败！状态码：{response.status_code}，原因：{response.text}")
                return None, None
            all_entities = response.json()
        except requests.exceptions.ConnectionError:
            logger.error("连接异常！无法连接到Home Assistant服务器")
            return None, None
        except Exception as e:
            logger.error(f"请求异常！原因：{str(e)}")
            return None, None

        # 分离sensor和非sensor实体
        sensor_entities = [entity for entity in all_entities if entity["entity_id"].startswith("sensor.")]
        non_sensor_entities = [entity for entity in all_entities if not entity["entity_id"].startswith("sensor.")]
        
        # 处理sensor实体
        valid_sensors = []  # 存储状态有效的传感器
        invalid_sensors = []  # 存储状态无效的传感器

        for sensor in sensor_entities:
            sensor_state = sensor["state"].strip().lower()
            # 排除状态为"unknown"（未知）、"unavailable"（不可用）的传感器
            if sensor_state in ["unknown", "unavailable", "none"]:
                invalid_sensors.append({
                    "entity_id": sensor["entity_id"],
                    "friendly_name": sensor["attributes"].get("friendly_name", "未命名"),
                    "state": sensor["state"],
                    "last_updated": sensor["last_updated"][:19].replace("T", " ")
                })
            else:
                # 提取传感器关键信息
                valid_sensor_info = {
                    "entity_id": sensor["entity_id"],
                    "friendly_name": sensor["attributes"].get("friendly_name", "未命名"),
                    "state": sensor["state"],
                    "unit": sensor["attributes"].get("unit_of_measurement", "无单位"),
                    "unit_of_measurement": sensor["attributes"].get("unit_of_measurement", ""),
                    "last_updated": sensor["last_updated"][:19].replace("T", " "),
                    "external_attributes": {k: v for k, v in sensor["attributes"].items() if k not in ["friendly_name", "unit_of_measurement"]}
                }
                valid_sensors.append(valid_sensor_info)

        # 对有效传感器按"数值型"和"文本型"分类
        numeric_sensors = []  # 数值型传感器
        text_sensors = []     # 文本型传感器
        
        for sensor in valid_sensors:
            sensor_state = sensor["state"].strip().lower()
            # 检查是否为数值型
            try:
                # 处理特殊数值（如"25.5%""100W"需先提取数字）
                clean_state = ''.join(filter(lambda c: c.isdigit() or c == '.', sensor_state))
                float(clean_state)  # 尝试转换为浮点数
                numeric_sensors.append(sensor)
            except (ValueError, TypeError):
                # 其他为文本型
                text_sensors.append(sensor)

        # 按实体名称分组
        numeric_sensors_by_group = self.group_entities_by_name(numeric_sensors)
        text_sensors_by_group = self.group_entities_by_name(text_sensors)
        invalid_sensors_by_group = self.group_entities_by_name(invalid_sensors)

        # 处理非sensor实体
        non_sensor_entities_by_type = {}
        for entity in non_sensor_entities:
            try:
                # 提取实体类型
                entity_type = entity["entity_id"].split(".")[0]
                
                # 提取实体关键信息
                entity_info = {
                    "entity_id": entity["entity_id"],
                    "friendly_name": entity["attributes"].get("friendly_name", "未命名"),
                    "state": entity["state"],
                    "last_updated": entity["last_updated"][:19].replace("T", " ")
                }
                
                # 为特定实体类型添加额外信息
                if entity_type == "light":
                    attributes = entity.get("attributes", {})
                    entity_info["external_attributes"] = attributes
                elif entity_type == "event":
                    attributes = entity.get("attributes", {})
                    entity_info["external_attributes"] = attributes
                    entity_info["event_type"] = attributes.get("event_type", "未知")
                
                # 按类型分组
                if entity_type not in non_sensor_entities_by_type:
                    non_sensor_entities_by_type[entity_type] = []
                non_sensor_entities_by_type[entity_type].append(entity_info)
            except Exception as e:
                # 忽略单个实体处理错误
                logger.warning(f"处理实体 {entity.get('entity_id', '未知')} 时出错: {str(e)}")
                continue

        # 构建返回结果
        sensor_result = {
            "numeric_sensors": numeric_sensors,
            "text_sensors": text_sensors,
            "invalid_sensors": invalid_sensors,
            "numeric_sensors_by_group": numeric_sensors_by_group,
            "text_sensors_by_group": text_sensors_by_group,
            "invalid_sensors_by_group": invalid_sensors_by_group
        }
        
        return sensor_result, non_sensor_entities_by_type
    
    def get_current_entity_summary(self):
        """
        获取当前实体摘要信息
        :return: 当前实体摘要字符串
        """
        return self.current_entity_summary
        
    def update_entity_data(self) -> str:
        """
        更新实体数据
        :return: 实体摘要信息
        """
        logger.info("正在更新Home Assistant实体数据...")
        sensor_data, non_sensor_data = self.get_and_classify_entities()
        
        # 存储实体数据
        self.entity_data = {
            "sensor_data": sensor_data,
            "non_sensor_data": non_sensor_data
        }
        
        # 准备实体摘要信息
        entity_summary = []
        
        # 添加传感器摘要
        if sensor_data:
            entity_summary.append("## 传感器信息")
            entity_summary.append(f"- 数值型传感器数量: {len(sensor_data.get('numeric_sensors', []))}")
            entity_summary.append(f"- 文本型传感器数量: {len(sensor_data.get('text_sensors', []))}")
            entity_summary.append(f"- 无效传感器数量: {len(sensor_data.get('invalid_sensors', []))}")
            
            # 添加关键数值型传感器示例
            numeric_groups = sensor_data.get('numeric_sensors_by_group', {})
            if numeric_groups:
                entity_summary.append("\n### 数值型传感器分组示例:")
                for group_name, sensors in list(numeric_groups.items())[:3]:
                    entity_summary.append(f"- 分组'{group_name}': {len(sensors)}个传感器")
                    for sensor in sensors[:2]:
                        entity_summary.append(f"  - {sensor['friendly_name']} (当前值: {sensor['state']}{sensor.get('unit', '')})")
        
        # 添加非传感器实体摘要
        if non_sensor_data:
            entity_summary.append("\n## 非传感器实体信息")
            
            # 按类型统计
            entity_types = []
            for entity_type, entities in non_sensor_data.items():
                entity_types.append(f"- {entity_type}: {len(entities)}个")
            entity_summary.extend(entity_types)
            
            # 添加关键实体类型的详细信息
            for key_type in ['light', 'switch', 'binary_sensor']:
                if key_type in non_sensor_data:
                    entities = non_sensor_data[key_type]
                    entity_summary.append(f"\n### {key_type}实体示例:")
                    # 对实体按名称分组
                    grouped = self.group_entities_by_name(entities)
                    for group_name, group_entities in list(grouped.items())[:2]:
                        entity_summary.append(f"- 分组'{group_name}': {len(group_entities)}个实体")
                        for entity in group_entities[:3]:
                            entity_summary.append(f"  - {entity.get('friendly_name', entity.get('entity_id', '未知'))} (状态: {entity.get('state', '未知')})")
        
        self.current_entity_summary = "\n".join(entity_summary)
        logger.info(f"实体数据更新完成, 总共 {len(entity_summary)} 条信息")
        return self.current_entity_summary
    
    def call_home_assistant_service(self, entity_id: str, service: str) -> str:
        """
        调用Home Assistant服务
        :param entity_id: 实体ID
        :param service: 服务名称（turn_on/turn_off等）
        :return: 执行结果
        """
        try:
            # 从entity_id中提取域（domain）
            domain = entity_id.split(".")[0] if "." in entity_id else ""
            
            if not domain:
                return f"无效的实体ID: {entity_id}"
            
            # 构建服务调用URL
            service_url = f"{self.url}/api/services/{domain}/{service}"
            
            # 准备请求体
            payload = {
                "entity_id": entity_id
            }
            
            # 发送请求
            response = requests.post(
                service_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return f"成功执行: {service} {entity_id}"
            else:
                return f"执行失败: {response.status_code} {response.text}"
        except Exception as e:
            return f"执行异常: {str(e)}"
    
    def parse_and_execute_command(self, command_text: str) -> str:
        """
        解析并执行控制指令
        :param command_text: 指令文本
        :return: 执行结果
        """
        # 简单的指令解析规则
        command_patterns = [
            (r'打开\s*(.+?)灯', 'light', 'turn_on'),
            (r'关闭\s*(.+?)灯', 'light', 'turn_off'),
            (r'开灯', 'light', 'turn_on'),
            (r'关灯', 'light', 'turn_off'),
            (r'打开\s*(.+?)开关', 'switch', 'turn_on'),
            (r'关闭\s*(.+?)开关', 'switch', 'turn_off'),
            (r'开启\s*(.+?)', 'switch', 'turn_on'),
            (r'关闭\s*(.+?)', 'switch', 'turn_off'),
            # 支持模糊表达的规则
            (r'打开所有灯', 'light', 'turn_on', True),
            (r'关闭所有灯', 'light', 'turn_off', True),
            (r'打开所有开关', 'switch', 'turn_on', True),
            (r'关闭所有开关', 'switch', 'turn_off', True),
            (r'全部开灯', 'light', 'turn_on', True),
            (r'全部关灯', 'light', 'turn_off', True),
            (r'所有灯打开', 'light', 'turn_on', True),
            (r'所有灯关闭', 'light', 'turn_off', True),
        ]
        
        # 首先检查是否是"所有"类的模糊指令
        for pattern, domain, service, is_all in [p for p in command_patterns if len(p) > 3 and p[3]]:
            if re.search(pattern, command_text):
                # 执行所有该类型设备的操作
                if self.entity_data and self.entity_data.get('non_sensor_data') and domain in self.entity_data['non_sensor_data']:
                    results = []
                    for entity in self.entity_data['non_sensor_data'][domain]:
                        result = self.call_home_assistant_service(entity.get('entity_id'), service)
                        results.append(f"- {entity.get('friendly_name', entity.get('entity_id'))}: {result}")
                    
                    if results:
                        action_name = "打开" if service == "turn_on" else "关闭"
                        return f"已{action_name}所有{domain}设备：\n" + "\n".join(results)
                    else:
                        return f"没有找到{domain}类型的设备"
        
        # 检查是否包含明确的实体ID
        if self.entity_data and self.entity_data.get('non_sensor_data'):
            non_sensor_data = self.entity_data['non_sensor_data']
            
            # 遍历所有实体类型
            for entity_type, entities in non_sensor_data.items():
                for entity in entities:
                    entity_id = entity.get('entity_id', '')
                    friendly_name = entity.get('friendly_name', '').lower()
                    
                    # 检查实体名称是否在指令中
                    if friendly_name and friendly_name in command_text.lower():
                        if '打开' in command_text or '开启' in command_text:
                            return self.call_home_assistant_service(entity_id, 'turn_on')
                        elif '关闭' in command_text or '关' in command_text:
                            return self.call_home_assistant_service(entity_id, 'turn_off')
                    
                    # 检查实体ID是否在指令中
                    if entity_id and entity_id in command_text:
                        if '打开' in command_text or '开启' in command_text:
                            return self.call_home_assistant_service(entity_id, 'turn_on')
                        elif '关闭' in command_text or '关' in command_text:
                            return self.call_home_assistant_service(entity_id, 'turn_off')
        
        # 使用正则表达式匹配普通指令（非全部操作）
        for pattern, domain, service in [p[:3] for p in command_patterns if len(p) <= 3 or not p[3]]:
            match = re.search(pattern, command_text)
            if match:
                device_name = match.group(1) if len(match.groups()) > 0 else ''
                
                # 查找匹配的设备
                if self.entity_data and self.entity_data.get('non_sensor_data') and domain in self.entity_data['non_sensor_data']:
                    for entity in self.entity_data['non_sensor_data'][domain]:
                        friendly_name = entity.get('friendly_name', '').lower()
                        if device_name.lower() in friendly_name:
                            return self.call_home_assistant_service(entity.get('entity_id'), service)
        
        return "未找到匹配的设备控制指令或设备不存在"
    
    def export_to_excel(self, sensor_data: Dict[str, Any], non_sensor_data: Dict[str, List[Dict[str, Any]]]) -> Optional[str]:
        """
        将实体数据导出到Excel文件
        :param sensor_data: 传感器数据
        :param non_sensor_data: 非传感器实体数据
        :return: 导出的文件路径
        """
        try:
            # 创建Excel写入器
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"home_assistant_entities_{timestamp}.xlsx"
            
            # 确保输出目录存在
            output_dir = os.path.join(os.getcwd(), OUTPUT_DIR)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            file_path = os.path.join(output_dir, filename)
            
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 1. 实体分类工作表
                all_entity_data = []
                
                # 处理sensor类型实体
                # 数值型传感器（已分组）
                for group_name, sensors in sensor_data.get("numeric_sensors_by_group", {}).items():
                    for sensor in sensors:
                        all_entity_data.append({
                            "分组": group_name,
                            "实体类型": "sensor",
                            "子类型": "数值型",
                            "实体ID": sensor["entity_id"],
                            "友好名称": sensor["friendly_name"],
                            "状态值": sensor["state"],
                            "单位": sensor.get("unit", "无单位"),
                            "最后更新时间": sensor["last_updated"]
                        })

                # 文本型传感器（已分组）
                for group_name, sensors in sensor_data.get("text_sensors_by_group", {}).items():
                    for sensor in sensors:
                        all_entity_data.append({
                            "分组": group_name,
                            "实体类型": "sensor",
                            "子类型": "文本型",
                            "实体ID": sensor["entity_id"],
                            "友好名称": sensor["friendly_name"],
                            "状态值": sensor["state"],
                            "单位": sensor.get("unit", "无单位"),
                            "最后更新时间": sensor["last_updated"]
                        })
                
                # 无效传感器（已分组）
                for group_name, sensors in sensor_data.get("invalid_sensors_by_group", {}).items():
                    for sensor in sensors:
                        all_entity_data.append({
                            "分组": group_name,
                            "实体类型": "sensor",
                            "子类型": "无效",
                            "实体ID": sensor["entity_id"],
                            "友好名称": sensor["friendly_name"],
                            "状态值": sensor["state"],
                            "单位": "无单位",
                            "最后更新时间": sensor.get("last_updated", "未知")
                        })
                
                # 添加非sensor类型实体
                for entity_type, entities in sorted(non_sensor_data.items()):
                    # 对每个实体类型进行分组处理
                    entities_by_group = self.group_entities_by_name(entities)
                    for group_name, entities_in_group in entities_by_group.items():
                        for entity in entities_in_group:
                            # 为不同类型添加特殊子类型标记
                            subtype = ""
                            if entity_type == "switch":
                                subtype = "开关"
                            elif entity_type == "light":
                                subtype = "灯光"
                            elif entity_type == "event":
                                subtype = "事件"
                            
                            entity_row = {
                                "分组": group_name,
                                "实体类型": entity_type,
                                "子类型": subtype,
                                "实体ID": entity["entity_id"],
                                "友好名称": entity["friendly_name"],
                                "状态值": entity["state"],
                                "单位": "无单位",
                                "最后更新时间": entity["last_updated"]
                            }
                            
                            # 为特定实体类型添加额外列
                            try:
                                if entity_type == "light":
                                    entity_row["亮度"] = str(entity.get("brightness", "未知"))
                                    entity_row["颜色模式"] = entity.get("color_mode", "未知")
                                elif entity_type == "event":
                                    entity_row["事件类型"] = entity.get("event_type", "未知")
                            except Exception:
                                pass
                            
                            all_entity_data.append(entity_row)
                
                # 创建实体分类工作表并按分组排序
                if all_entity_data:
                    df_entities = pd.DataFrame(all_entity_data)
                    df_entities = df_entities.sort_values(by=["分组", "实体类型"])
                    df_entities.to_excel(writer, sheet_name="实体分类", index=False)
                    
                    # 自动调整列宽
                    worksheet = writer.sheets["实体分类"]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            return file_path
        except Exception as e:
            logger.error(f"导出Excel失败: {str(e)}")
            return None

# 创建全局的HomeAssistantManager实例
hass_manager = HomeAssistantManager()
