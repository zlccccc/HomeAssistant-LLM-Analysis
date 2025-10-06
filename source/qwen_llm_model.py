import os
import requests
import json
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

# 添加当前目录到系统路径
import os
import sys
if __file__ in sys.path:
    sys.path.remove(__file__)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入配置和Home Assistant模块
from config import QWEN_API_KEY, QWEN_API_BASE, QWEN_MODEL, OUTPUT_DIR
from home_assistant import hass_manager

class QwenLLMModelManager:
    """
    Qwen大模型管理器，处理与Qwen API的所有交互
    """
    
    def __init__(self):
        self.api_key = QWEN_API_KEY
        self.api_base = QWEN_API_BASE
        self.model = QWEN_MODEL
        
        # 输出目录设置为当前运行路径下的output目录
        self.output_dir = os.path.join(os.getcwd(), OUTPUT_DIR)
        
        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def call_openai_api(self, messages: List[Dict[str, str]], model: str = None, 
                       temperature: float = 0.7) -> Optional[str]:
        """
        调用OpenAI兼容的API（如Qwen）
        :param messages: 消息列表
        :param model: 模型名称
        :param temperature: 生成温度
        :return: 生成的文本
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 使用指定的模型或默认模型
            target_model = model or self.model
            
            data = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2000
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                error_msg = f"API调用失败: {response.status_code} {response.text}"
                print(error_msg)
                return error_msg
        except Exception as e:
            error_msg = f"API调用异常: {str(e)}"
            print(error_msg)
            return error_msg

    def analyze_entities(self, sensor_data: Dict[str, Any], non_sensor_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, Optional[str]]:
        """
        分析实体数据并生成可能的控制逻辑
        :param sensor_data: 传感器数据
        :param non_sensor_data: 非传感器实体数据
        :return: (实体摘要, 分析结果)
        """
        print("\n开始分析实体数据...")
        
        # 准备实体摘要信息
        entity_summary = []
        
        # 添加传感器摘要
        if sensor_data:
            entity_summary.append("## 传感器信息")
            entity_summary.append(f"- 数值型传感器数量: {len(sensor_data.get('numeric_sensors', []))}")
            entity_summary.append(f"- 文本型传感器数量: {len(sensor_data.get('text_sensors', []))}")
            entity_summary.append(f"- 无效传感器数量: {len(sensor_data.get('invalid_sensors', []))}")
            
            # 添加一些关键数值型传感器示例
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
                    grouped = hass_manager.group_entities_by_name(entities)
                    for group_name, group_entities in list(grouped.items())[:2]:
                        entity_summary.append(f"- 分组'{group_name}': {len(group_entities)}个实体")
                        for entity in group_entities[:3]:
                            entity_summary.append(f"  - {entity.get('friendly_name', entity.get('entity_id', '未知'))} (状态: {entity.get('state', '未知')})")
        
        entity_summary_text = "\n".join(entity_summary)
        print("实体摘要信息准备完成")

        # 准备提示词
        prompt = f"""你是一个智能家居自动化专家，擅长分析Home Assistant实体并生成智能控制逻辑。

以下是从Home Assistant获取的实体摘要信息：
{entity_summary_text}

请根据这些实体信息，执行以下分析：

1. 实体类型分析：总结有哪些主要类型的实体，它们的数量分布如何，以及可能的用途
2. 潜在的智能场景：基于已有实体，提出3-5个实用的自动化场景建议
3. 场景控制逻辑：为每个场景提供详细的控制逻辑说明，包括触发条件和执行动作
4. 场景代码示例：为每个场景提供Home Assistant自动化YAML代码示例
5. 优化建议：如果发现某些实体缺失或配置不完整，提供改进建议

请确保分析专业、实用，并符合Home Assistant的最佳实践。
"""
        
        # 构建消息
        messages = [
            {"role": "system", "content": "你是一个专业的智能家居自动化顾问，精通Home Assistant系统。"},
            {"role": "user", "content": prompt}
        ]
        
        print("\n调用Qwen大模型进行分析...")
        analysis_result = self.call_openai_api(messages)
        
        return entity_summary_text, analysis_result
    
    def save_analysis_results(self, summary: str, analysis_result: str) -> Tuple[Optional[str], Optional[str]]:
        """
        保存分析结果到文件
        :param summary: 实体摘要
        :param analysis_result: 分析结果
        :return: (摘要文件路径, 分析结果文件路径)
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.join(os.getcwd(), self.output_dir)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存实体摘要
            summary_file = os.path.join(output_dir, f"entity_summary_{timestamp}.txt")
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(summary)
            
            # 保存分析结果
            analysis_file = os.path.join(output_dir, f"automation_analysis_{timestamp}.md")
            with open(analysis_file, "w", encoding="utf-8") as f:
                f.write("# Home Assistant 实体分析与自动化场景建议\n\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("## 大模型分析结果\n\n")
                f.write(analysis_result if analysis_result else "分析失败，请检查API配置")
            
            return summary_file, analysis_file
        except Exception as e:
            print(f"保存结果失败: {str(e)}")
            return None, None
    
    def process_message(self, message: str, history: List[Tuple[str, str]]) -> str:
        """
        处理用户消息并生成响应
        :param message: 用户消息
        :param history: 历史对话
        :return: 响应消息
        """
        # 先检查是否是控制指令
        control_keywords = ['打开', '关闭', '开启', '关灯', '开灯']
        if any(keyword in message.lower() for keyword in control_keywords):
            # 尝试执行控制指令
            control_result = hass_manager.parse_and_execute_command(message)
            
            # 如果执行成功，也可以用大模型生成更友好的回复
            messages = [
                {"role": "system", "content": "你是一个智能家居助手，请用友好的语言回复用户的设备控制结果。"},
                {"role": "user", "content": f"用户说：'{message}'，控制结果是：'{control_result}'。请生成一个友好的回复。"}
            ]
            
            friendly_response = self.call_openai_api(messages, temperature=0.3)
            if "API调用" not in friendly_response:
                return f"{friendly_response}\n\n[系统消息] {control_result}"
            else:
                return control_result
        
        # 准备上下文信息
        context = f"""
你是一个智能家居助手，负责帮助用户了解和控制他们的Home Assistant设备。

以下是当前的Home Assistant实体摘要信息：
{hass_manager.get_current_entity_summary()}

请基于这些信息回答用户的问题或提供建议。
"""
        
        # 构建消息历史
        messages = [
            {"role": "system", "content": context},
        ]
        
        # 添加历史对话
        for user_msg, assistant_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
        
        # 添加最新消息
        messages.append({"role": "user", "content": message})
        
        # 调用大模型
        response = self.call_openai_api(messages)
        return response

# 创建全局实例供其他模块使用
qwen_llm_manager = QwenLLMModelManager()
print("全局实例 qwen_llm_manager 已创建")
