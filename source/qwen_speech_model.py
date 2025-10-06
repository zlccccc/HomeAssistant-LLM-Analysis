import os
import sys
import requests
import json
from typing import Dict, Any, Optional
import base64
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加当前目录到系统路径
if __file__ in sys.path:
    sys.path.remove(__file__)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入配置 - 使用与qwen_llm_model相同的配置参数
from config import QWEN_API_KEY, QWEN_API_BASE, QWEN_MODEL, OUTPUT_DIR, QWEN_ASR_MODEL, QWEN_TTS_MODEL

class QwenSpeechManager:
    """
    Qwen语音管理器，处理与Qwen API的语音识别（ASR）和语音合成（TTS）功能
    增强版：添加流式处理、参数调整和状态跟踪
    """
    
    def __init__(self):
        # 使用与qwen_llm_model相同的API配置
        self.api_key = QWEN_API_KEY
        self.api_base = QWEN_API_BASE
        self.model = QWEN_MODEL
        
        # 输出目录设置为当前运行路径下的output目录
        self.output_dir = os.path.join(os.getcwd(), OUTPUT_DIR)
        
        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"创建输出目录: {self.output_dir}")
        
        # ASR和TTS的模型名称 - 从config.py获取
        self.asr_model = QWEN_ASR_MODEL if hasattr(sys.modules['config'], 'QWEN_ASR_MODEL') else "qwen3-asr-flash"
        self.tts_model = QWEN_TTS_MODEL if hasattr(sys.modules['config'], 'QWEN_TTS_MODEL') else "qwen3-tts-flash"
        
        # 状态跟踪
        self.last_asr_time = 0
        self.last_tts_time = 0
        self.asr_success_count = 0
        self.asr_failure_count = 0
        self.tts_success_count = 0
        self.tts_failure_count = 0
        
        logger.info("QwenSpeechManager 初始化完成")
    
    def audio_to_text(self, audio_file: str, format_type: str = "wav") -> Optional[str]:
        """
        语音识别（ASR）：将音频文件转换为文本
        :param audio_file: 音频文件路径
        :param format_type: 音频格式，如wav、mp3等
        :return: 识别的文本结果，如果失败返回None
        """
        try:
            logger.info(f"开始语音识别，文件：{audio_file}")
            start_time = time.time()
            
            # 检查文件是否存在
            if not os.path.exists(audio_file):
                error_msg = f"错误：音频文件不存在 - {audio_file}"
                logger.error(error_msg)
                self.asr_failure_count += 1
                return None
            
            # 获取文件大小以记录信息
            file_size = os.path.getsize(audio_file) / (1024 * 1024)  # 转换为MB
            logger.info(f"音频文件大小: {file_size:.2f}MB, 格式: {format_type}")
            
            # 读取音频文件并进行base64编码
            try:
                with open(audio_file, 'rb') as f:
                    audio_data = base64.b64encode(f.read()).decode('utf-8')
                logger.info(f"音频文件已读取并编码，base64长度: {len(audio_data)}")
            except Exception as e:
                error_msg = f"读取音频文件失败: {str(e)}"
                logger.error(error_msg)
                self.asr_failure_count += 1
                return None
            
            # 构建请求参数，使用DashScope API格式
            params = {
                "model": self.asr_model,
                "input": {
                    "messages": [
                        {
                            "content": [
                                {
                                    "text": ""
                                }
                            ],
                            "role": "system"
                        },
                        {
                            "content": [
                                {
                                    "audio": f"data:audio/{format_type};base64,{audio_data}"
                                }
                            ],
                            "role": "user"
                        }
                    ]
                },
                "parameters": {
                    "asr_options": {
                        "enable_lid": True,
                        "enable_itn": False
                    }
                }
            }
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 使用DashScope API端点
            api_endpoint = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
            
            # 发送请求
            try:
                response = requests.post(
                    api_endpoint,
                    headers=headers,
                    json=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 解析DashScope API响应格式
                    text = ""
                    if "output" in result and "choices" in result["output"]:
                        for choice in result["output"]["choices"]:
                            if "message" in choice and "content" in choice["message"]:
                                for content_item in choice["message"]["content"]:
                                    if "text" in content_item:
                                        text += content_item["text"]
                    
                    logger.info(f"语音识别成功，识别文本长度: {len(text)}字符")
                    self.asr_success_count += 1
                    self.last_asr_time = time.time()
                    return text
                else:
                    error_msg = f"API请求失败: 状态码 {response.status_code}, 响应: {response.text}"
                    logger.error(error_msg)
                    self.asr_failure_count += 1
                    return None
            except Exception as e:
                error_msg = f"API请求异常: {str(e)}"
                logger.error(error_msg)
                self.asr_failure_count += 1
                return None
            
        except Exception as e:
            error_msg = f"语音识别出错: {str(e)}"
            logger.error(error_msg)
            logger.exception("语音识别详细错误堆栈:")
            self.asr_failure_count += 1
            return None
    
    def text_to_audio(self, text: str, output_file: str, voice: str = "female") -> bool:
        """
        语音合成（TTS）：将文本转换为音频文件
        :param text: 要合成的文本
        :param output_file: 输出音频文件路径
        :param voice: 语音类型，如female、male等
        :return: 是否成功
        """
        try:
            logger.info(f"开始语音合成，文本长度：{len(text)}字符, 语音类型: {voice}")
            # 计算字符数（汉字=2字符，其他=1字符）
            total_chars = 0
            truncated_text = ""
            for char in text:
                # 判断是否为汉字（基本汉字范围）
                if '\u4e00' <= char <= '\u9fff':
                    char_count = 2
                else:
                    char_count = 1
                
                # 检查是否超过限制
                if total_chars + char_count > 600:
                    break
                
                truncated_text += char
                total_chars += char_count
            
            # 如果进行了截断，记录警告信息
            if len(truncated_text) < len(text):
                logger.warning(f"文本过长，已截断至{total_chars}个字符进行合成")
                text = truncated_text
            
            # 映射voice参数到DashScope支持的声音名称
            voice_mapping = {
                "female": "Cherry",
                "male": "Ryan",
                "neutral": "Sarah"
            }
            dashscope_voice = voice_mapping.get(voice, "Cherry")

            # 构建请求参数，使用DashScope API格式
            params = {
                "model": self.tts_model,
                "input": {
                    "text": text,
                    "voice": dashscope_voice,
                    "language_type": "Chinese"  # 根据需要可调整为其他支持的语言
                }
            }
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            # 使用DashScope API端点
            api_endpoint = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
            # 发送请求到DashScope TTS服务
            try:
                response = requests.post(
                    api_endpoint,
                    headers=headers,
                    json=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 处理DashScope API响应，提取音频URL
                    if "output" in result and "audio" in result["output"] and "url" in result["output"]["audio"]:
                        audio_url = result["output"]["audio"]["url"]
                        logger.info(f"获取到音频URL: {audio_url}")
                        
                        # 从URL下载音频文件
                        try:
                            audio_response = requests.get(audio_url, timeout=30)
                            if audio_response.status_code == 200:
                                # 保存下载的音频数据到文件
                                with open(output_file, 'wb') as f:
                                    f.write(audio_response.content)
                                logger.info(f"语音合成成功，音频文件已下载并保存: {output_file}")
                                
                                # 播放下载的音频文件
                                try:
                                    self._play_audio(output_file)
                                    logger.info(f"音频文件已成功播放: {output_file}")
                                except Exception as play_error:
                                    logger.warning(f"音频播放失败: {str(play_error)}")
                                    # 播放失败不影响整体功能，继续返回成功
                                
                                self.tts_success_count += 1
                                self.last_tts_time = time.time()
                                return True
                            else:
                                error_msg = f"下载音频文件失败: 状态码 {audio_response.status_code}"
                                logger.error(error_msg)
                                self.tts_failure_count += 1
                                return False
                        except Exception as download_error:
                            error_msg = f"下载音频文件时出错: {str(download_error)}"
                            logger.error(error_msg)
                            self.tts_failure_count += 1
                            return False
                    else:
                        error_msg = f"API响应中未找到音频URL: {json.dumps(result, ensure_ascii=False)[:200]}..."
                        logger.error(error_msg)
                        self.tts_failure_count += 1
                        return False
                else:
                    error_msg = f"API请求失败: 状态码 {response.status_code}, 响应: {response.text[:200]}..."
                    logger.error(error_msg)
                    self.tts_failure_count += 1
                    return False
            except Exception as e:
                error_msg = f"API请求异常: {str(e)}"
                logger.error(error_msg)
                self.tts_failure_count += 1
                return False
            
        except Exception as e:
            error_msg = f"语音合成出错: {str(e)}"
            logger.error(error_msg)
            logger.exception("语音合成详细错误堆栈:")
            self.tts_failure_count += 1
            return False
    
    def _play_audio(self, audio_file: str):
        """
        播放音频文件的辅助方法
        尝试使用多个可能的库来播放音频，确保最大兼容性
        :param audio_file: 音频文件路径
        """
        # 方法1: 尝试使用pygame播放音频
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            # 等待音频播放完成
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.quit()
            return
        except Exception as pygame_error:
            logger.debug(f"pygame播放失败，尝试其他方法: {str(pygame_error)}")
        
        # 方法2: 尝试使用playsound播放音频
        try:
            from playsound import playsound
            playsound(audio_file)
            return
        except Exception as playsound_error:
            logger.debug(f"playsound播放失败，尝试其他方法: {str(playsound_error)}")
        
        # 方法3: 尝试使用pydub播放音频
        try:
            from pydub import AudioSegment
            from pydub.playback import play
            audio = AudioSegment.from_wav(audio_file)
            play(audio)
            return
        except Exception as pydub_error:
            logger.debug(f"pydub播放失败，尝试其他方法: {str(pydub_error)}")
        
        # 方法4: 尝试使用系统默认程序播放音频（跨平台）
        try:
            import os
            import platform
            import subprocess
            
            system = platform.system()
            if system == 'Windows':
                os.startfile(audio_file)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', audio_file])
            elif system == 'Linux':
                subprocess.run(['xdg-open', audio_file])
            else:
                raise Exception(f"不支持的操作系统: {system}")
            return
        except Exception as system_error:
            logger.debug(f"系统默认播放器播放失败: {str(system_error)}")
        # 所有方法都失败
        raise Exception("无法播放音频文件，所有尝试的播放方法都失败了")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取语音服务统计信息
        :return: 统计信息字典
        """
        return {
            "asr_success_count": self.asr_success_count,
            "asr_failure_count": self.asr_failure_count,
            "tts_success_count": self.tts_success_count,
            "tts_failure_count": self.tts_failure_count,
            "last_asr_time": self.last_asr_time,
            "last_tts_time": self.last_tts_time,
        }

# 创建全局实例供其他模块使用
qwen_speech_manager = QwenSpeechManager()
logger.info("全局实例 qwen_speech_manager 已创建")