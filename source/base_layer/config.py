import os
import sys

# 导入日志工具
from source.base_layer.utils import logger
logger.info("配置文件已加载")

# 配置文件 - 存储所有API密钥和配置参数

# Home Assistant API配置
HA_URL = "http://localhost:8123"  # Home Assistant 访问地址
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI1NTg0MDljZjhjMDY0MTE0YmYzZDJiYTcwMTYzMzJjMyIsImlhdCI6MTc1OTYzNDU1MSwiZXhwIjoyMDc0OTk0NTUxfQ.3BuidUXBqG6dU0LzrrF6BaYhpfv9zWyYDxLbpWPyesI"  # Home Assistant访问令牌
# 通用请求头（认证+JSON格式）
HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json"
}

# Qwen大模型OpenAI兼容API配置
QWEN_API_KEY = "sk-62796c02b9e84e44a12d9fabc60b8bdb"  # Qwen API密钥
QWEN_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # 阿里云Qwen API地址
QWEN_MODEL = "qwen-flash"  # Qwen模型名称

# 阿里云语音服务配置
QWEN_ASR_MODEL = "qwen3-asr-flash"  # 阿里云Qwen语音识别模型
QWEN_TTS_MODEL = "qwen3-tts-flash"  # 阿里云Qwen语音合成模型

# 输出配置
OUTPUT_DIR = "output"  # 输出目录