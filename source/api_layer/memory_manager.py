import os
from typing import Optional, Dict, List, Any
from memu import MemuClient
from source.base_layer.utils import logger

class MemoryManager:
    """
    记忆管理类，负责处理对话记忆的存储和检索
    使用MemU API进行记忆管理
    """
    
    def __init__(self):
        self.memory = self._build_memory()
    
    def _build_memory(self) -> Optional[MemuClient]:
        """
        构建MemU记忆客户端
        """
        if os.environ.get("USE_MEMORY_MESSAGES", "false") != "true":
            return None
        
        try:
            memory_client = MemuClient(
                base_url="https://api.memu.so",
                api_key=os.environ.get("MEMU_API_KEY", "")
            )
            logger.info("MemU记忆客户端初始化完成")
            return memory_client
        except Exception as e:
            logger.error(f"初始化MemU记忆客户端失败: {str(e)}")
            return None
    
    def memorize_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        记忆对话消息（存储过程）
        :param messages: 要记忆的消息列表
        :return: 记忆结果
        """
        if self.memory is None:
            logger.info("记忆功能未启用")
            return {}
        
        try:
            # 过滤出需要记忆的消息
            to_memorize_messages = messages
            
            if to_memorize_messages:
                self.memory.memorize_conversation(
                    conversation=to_memorize_messages,
                    user_id=os.environ.get("MEMU_USER_ID", "user001"), 
                    user_name=os.environ.get("MEMU_USER_NAME", "master"), 
                    agent_id=os.environ.get("MEMU_AGENT_ID", "homeassistant"), 
                    agent_name=os.environ.get("MEMU_AGENT_NAME", "Home Assistant")
                )
                logger.info(f"成功记忆 {len(to_memorize_messages)} 条消息")
            
            return {"memorized_count": len(to_memorize_messages)}
        except Exception as e:
            logger.error(f"记忆消息失败: {str(e)}")
            return {"error": str(e)}
    
    def retrieve_memory_info(self) -> str:
        """
        检索记忆信息（检索过程）
        :return: 格式化的记忆信息字符串
        """
        if self.memory is None:
            return ""
        
        try:
            retrieved_prompt = ""
            
            retrieved_info = self.memory.retrieve_default_categories(
                user_id=os.environ.get("MEMU_USER_ID", "user001"),
                agent_id=os.environ.get("MEMU_AGENT_ID", "homeassistant")
            )
        
            for category in retrieved_info.categories:
                if category.summary:
                    retrieved_prompt += f"**{category.name}:** {category.summary}\n\n"
            
            logger.info("成功检索记忆信息")
            return retrieved_prompt
        except Exception as e:
            logger.error(f"检索记忆信息失败: {str(e)}")
            return ""

# 创建全局实例供其他模块使用
memory_manager = MemoryManager()
logger.info("全局实例 memory_manager 已创建")