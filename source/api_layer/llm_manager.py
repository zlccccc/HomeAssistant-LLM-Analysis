import os
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from source.base_layer.utils import logger

class LLMManager:
    """
    LLM管理器，封装大语言模型的调用接口
    使用ChatOpenAI直接调用，支持OpenAI兼容的各种模型
    """
    
    def __init__(self):
        """
        初始化LLM管理器
        从环境变量中读取配置
        """
        self.model_name = os.getenv("QWEN_MODEL", "gpt-3.5-turbo")
        self.api_key = os.getenv("QWEN_API_KEY", os.getenv("OPENAI_API_KEY"))
        self.api_base = os.getenv("QWEN_API_BASE", os.getenv("OPENAI_API_BASE"))
        
        # 初始化ChatOpenAI模型
        self.llm = self._initialize_chat_model()
        
    def _initialize_chat_model(self):
        """
        初始化ChatOpenAI模型实例
        """
        try:
            chat_model = ChatOpenAI(
                model=self.model_name,
                api_key=self.api_key,
                base_url=self.api_base,
                temperature=0.7,
                max_tokens=2048
            )
            logger.info(f"LLMManager初始化成功，使用模型: {self.model_name}")
            return chat_model
        except Exception as e:
            logger.error(f"LLMManager初始化失败: {str(e)}")
            return None
            
    def get_chat_model(self):
        """
        获取已配置好的ChatOpenAI模型实例
        供控制器和其他组件使用
        """
        return self.llm
    
    def call_openai_api(self, messages: List[Dict[str, Any]], temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """
        调用OpenAI兼容的API进行对话生成
        
        Args:
            messages: 消息列表，格式为[{"role": "user/system/assistant", "content": "消息内容"}]
            temperature: 生成温度，控制输出的随机性
            max_tokens: 最大生成令牌数
            
        Returns:
            生成的回复内容
        """
        try:
            # 将消息转换为langchain消息对象
            langchain_messages = []
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content", "")
                
                if role == "user":
                    langchain_messages.append(HumanMessage(content=content))
                elif role == "system":
                    langchain_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    langchain_messages.append(AIMessage(content=content))
            
            # 如果没有初始化llm或需要重新配置temperature和max_tokens
            if not self.llm or self.llm.temperature != temperature or self.llm.max_tokens != max_tokens:
                try:
                    self.llm = ChatOpenAI(
                        model=self.model_name,
                        api_key=self.api_key,
                        base_url=self.api_base,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    logger.info(f"重新初始化ChatOpenAI模型，temperature={temperature}, max_tokens={max_tokens}")
                except Exception as e:
                    logger.error(f"重新初始化ChatOpenAI模型失败: {str(e)}")
                    return f"重新初始化模型失败: {str(e)}"
            
            # 调用模型
            response = self.llm.invoke(langchain_messages)
            
            # 返回生成的内容
            return response.content
            
        except Exception as e:
            error_msg = f"调用OpenAI API失败: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        生成文本摘要
        
        Args:
            text: 要摘要的文本
            max_length: 摘要最大长度
            
        Returns:
            生成的摘要
        """
        system_prompt = f"请将以下文本浓缩为一个简短摘要（最多{max_length}字）。"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        return self.call_openai_api(messages, temperature=0.1)
    
    def analyze_content(self, content: str, task_description: str) -> str:
        """
        分析内容
        
        Args:
            content: 要分析的内容
            task_description: 分析任务描述
            
        Returns:
            分析结果
        """
        system_prompt = f"你是一个分析助手，请根据以下任务描述分析提供的内容：{task_description}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        
        return self.call_openai_api(messages, temperature=0.3)

# 创建全局实例供其他模块使用
llm_manager = LLMManager()
logger.info("全局实例 llm_manager 已创建")