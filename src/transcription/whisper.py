import os
import threading
import time
import base64
from functools import wraps

import dotenv
from openai import OpenAI

from ..llm.symbol import SymbolProcessor
from ..text_processing import TextPostProcessor
from ..utils.logger import logger

dotenv.load_dotenv()

def timeout_decorator(seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            error = [None]
            completed = threading.Event()

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e
                finally:
                    completed.set()

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()

            if completed.wait(seconds):
                if error[0] is not None:
                    raise error[0]
                return result[0]
            raise TimeoutError(f"操作超时 ({seconds}秒)")

        return wrapper
    return decorator

class WhisperProcessor:
    # 类级别的配置参数
    DEFAULT_TIMEOUT = 20  # API 超时时间（秒）- GROQ等其他服务
    OPENAI_TIMEOUT = 180  # OpenAI GPT-4o transcribe 超时时间（秒）
    DEFAULT_MODEL = None
    
    def __init__(self):
        self.text_postprocessor = TextPostProcessor.from_environment()
        self.add_symbol = os.getenv("ADD_SYMBOL", "false").lower() == "true"
        self.optimize_result = os.getenv("OPTIMIZE_RESULT", "false").lower() == "true"
        self.symbol = SymbolProcessor() if self.add_symbol or self.optimize_result else None
        self.service_platform = os.getenv("SERVICE_PLATFORM", "groq").lower()
        self.timeout_seconds = self.OPENAI_TIMEOUT if self.service_platform == "openai" else self.DEFAULT_TIMEOUT

        if self.service_platform == "openai":
            # OpenAI GPT-4o transcribe 配置
            api_key = os.getenv("OFFICIAL_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            assert api_key, "未设置 OFFICIAL_OPENAI_API_KEY 或 OPENAI_API_KEY 环境变量"
            # 使用官方 OpenAI API
            self.client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1")
            self.DEFAULT_MODEL = "gpt-4o-transcribe"
        elif self.service_platform in ("aliyun", "dashscope", "bailian"):
            api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY")
            assert api_key, "未设置 DASHSCOPE_API_KEY 或 BAILIAN_API_KEY 环境变量"
            self.client = OpenAI(
                api_key=api_key,
                base_url=os.getenv(
                    "DASHSCOPE_BASE_URL",
                    "https://dashscope.aliyuncs.com/compatible-mode/v1",
                ),
            )
            self.DEFAULT_MODEL = os.getenv("DASHSCOPE_ASR_MODEL", "qwen3-asr-flash")
            self.timeout_seconds = self.OPENAI_TIMEOUT
        elif self.service_platform == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            base_url = os.getenv("GROQ_BASE_URL")
            assert api_key, "未设置 GROQ_API_KEY 环境变量"
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url if base_url else None
            )
            self.DEFAULT_MODEL = "whisper-large-v3-turbo"
        elif self.service_platform == "siliconflow":
            api_key = os.getenv("GROQ_API_KEY")
            assert api_key, "未设置 SILICONFLOW_API_KEY 环境变量"
            self.DEFAULT_MODEL = "FunAudioLLM/SenseVoiceSmall"
        else:
            raise ValueError(f"未知的平台: {self.service_platform}")
        
    @timeout_decorator(180)  # OpenAI 专用超时时间
    def _call_openai_api(self, mode, audio_data, prompt):
        """调用 OpenAI GPT-4o transcribe API"""
        if mode == "translations":
            response = self.client.audio.translations.create(
                model="gpt-4o-transcribe",
                response_format="text",
                prompt=prompt,
                file=("audio.wav", audio_data)
            )
        else:  # transcriptions
            response = self.client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                response_format="text",
                prompt=prompt,
                file=("audio.wav", audio_data)
            )
        return str(response).strip()

    @timeout_decorator(180)
    def _call_dashscope_asr_api(self, audio_data):
        """调用阿里云百炼 Qwen-ASR 录音文件识别接口。"""
        audio_data.seek(0)
        audio_b64 = base64.b64encode(audio_data.read()).decode("ascii")
        response = self.client.chat.completions.create(
            model=self.DEFAULT_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:audio/wav;base64,{audio_b64}",
                            },
                        },
                    ],
                },
            ],
            extra_body={
                "asr_options": {
                    "enable_itn": os.getenv("DASHSCOPE_ASR_ENABLE_ITN", "true").lower() == "true",
                },
            },
        )
        return (response.choices[0].message.content or "").strip()
    
    def _call_whisper_api(self, mode, audio_data, prompt):
        """调用 Whisper API"""
        if self.service_platform == "openai":
            # 使用专用的 OpenAI API 调用（已有180秒超时）
            return self._call_openai_api(mode, audio_data, prompt)
        elif self.service_platform in ("aliyun", "dashscope", "bailian"):
            if mode == "translations":
                raise ValueError("DashScope/Qwen-ASR 不支持翻译模式")
            return self._call_dashscope_asr_api(audio_data)
        else:
            # GROQ API 使用10秒超时
            return self._call_groq_api(mode, audio_data, prompt)
    
    @timeout_decorator(10)
    def _call_groq_api(self, mode, audio_data, prompt):
        """调用 GROQ API"""
        if mode == "translations":
            response = self.client.audio.translations.create(
                model="whisper-large-v3",
                response_format="text",
                prompt=prompt,
                file=("audio.wav", audio_data)
            )
        else:  # transcriptions
            response = self.client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                response_format="text",
                prompt=prompt,
                file=("audio.wav", audio_data)
            )
        return str(response).strip()

    def process_audio(self, audio_buffer, mode="transcriptions", prompt="", archive_path=None):
        """调用 Whisper API 处理音频（转录或翻译）
        
        Args:
            audio_path: 音频文件路径
            mode: 'transcriptions' 或 'translations'，决定是转录还是翻译
            prompt: 提示词
        
        Returns:
            tuple: (结果文本, 错误信息)
            - 如果成功，错误信息为 None
            - 如果失败，结果文本为 None
        """
        try:
            start_time = time.time()

            logger.info(f"正在调用 Whisper API... (模式: {mode})")
            result = self._call_whisper_api(mode, audio_buffer, prompt)

            logger.info(f"API 调用成功 ({mode}), 耗时: {time.time() - start_time:.1f}秒")
            result = self.text_postprocessor.process(result)
            logger.info(f"识别结果: {result}")
            
            # OpenAI GPT-4o transcribe 自带标点符号，无需额外处理
            if self.service_platform != "openai":
                # 仅在 groq API 时添加标点符号
                if self.service_platform == "groq" and self.add_symbol and self.symbol:
                    result = self.symbol.add_symbol(result)
                    logger.info(f"添加标点符号: {result}")
                if self.optimize_result and self.symbol:
                    result = self.symbol.optimize_result(result)
                    logger.info(f"优化结果: {result}")

            return result, None
            

        except TimeoutError:
            error_msg = f"❌ API 请求超时 ({self.timeout_seconds}秒)"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"❌ {str(e)}"
            logger.error(f"音频处理错误: {str(e)}", exc_info=True)
            return None, error_msg
        finally:
            audio_buffer.close()  # 显式关闭字节流
