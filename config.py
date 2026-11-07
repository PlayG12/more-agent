"""集中读取 .env 配置。

设计约定：哪个能力没配 key，哪个能力就自动进入 mock 模式，
保证骨架零配置也能跑通整个编排流程。
"""
import os

from dotenv import load_dotenv

load_dotenv()

# DeepSeek（主题规划 / 文案）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 文生图（硅基流动 SiliconFlow）
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", "")
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "https://api.siliconflow.cn/v1")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "Kwai-Kolors/Kolors")

# 语音合成（edge-tts）
TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")

LLM_MOCK = not DEEPSEEK_API_KEY
IMAGE_MOCK = not IMAGE_API_KEY
TTS_MOCK = os.getenv("TTS_MOCK", "0") == "1"
