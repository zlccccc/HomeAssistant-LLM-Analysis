import requests
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入日志记录器
from source.base_layer.utils import logger

class QwenLLMModelManager:
    """
    Qwen大模型管理器，处理与Qwen API的所有交互
    """
    
    def __init__(self):
        # 从环境变量读取API配置
        self.api_key = os.getenv("QWEN_API_KEY", "")
        self.api_base = os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = os.getenv("QWEN_MODEL", "qwen-flash")
        
        # 输出目录设置为当前运行路径下的output目录
        output_dir_name = os.getenv("OUTPUT_DIR", "output")
        self.output_dir = os.path.join(os.getcwd(), output_dir_name)
        
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
                logger.error(error_msg)
                return error_msg
        except Exception as e:
            error_msg = f"API调用异常: {str(e)}"
            logger.error(error_msg)
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
logger.info("全局实例 qwen_llm_manager 已创建")
