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

# 导入配置
from config import QWEN_API_KEY, QWEN_API_BASE, QWEN_MODEL, OUTPUT_DIR

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

    def process_message(self, message: str, history: List[Tuple[str, str]]) -> str:
        """
        处理用户消息并生成响应
        :param message: 用户消息
        :param history: 历史对话
        :return: 响应消息
        """
        # 基础系统提示
        context = """
你是一个智能助手，请根据用户的问题提供有用的回答。
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
