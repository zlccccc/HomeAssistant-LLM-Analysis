import re
from typing import Dict, List, Any
from utils import logger

class CommandParser:
    """
    命令解析器类，负责解析和执行Home Assistant控制命令
    """
    
    def __init__(self, entity_data: Dict[str, Any], url: str, headers: Dict[str, str]):
        """
        初始化命令解析器
        :param entity_data: 实体数据
        :param url: Home Assistant URL
        :param headers: 请求头
        """
        self.entity_data = entity_data
        self.url = url
        self.headers = headers
        
    def update_entity_data(self, entity_data: Dict[str, Any]):
        """
        更新实体数据
        :param entity_data: 新的实体数据
        """
        self.entity_data = entity_data
    
    def call_home_assistant_service(self, entity_id: str, service: str) -> str:
        """
        调用Home Assistant服务
        :param entity_id: 实体ID
        :param service: 服务名称（turn_on/turn_off等）
        :return: 执行结果
        """
        try:
            # 导入requests模块
            import requests
            
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