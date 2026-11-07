"""文生图接口（智谱 bigmodel，OpenAI images 兼容）。

默认模型 cogview-3-flash（中文提示词友好），
也可在 .env 换成 black-forest-labs 等。
"""
import time

from openai import OpenAI

import config


def generate_image(prompt: str) -> str:
    """输入提示词，返回图片 URL。未配置 key 时返回空串（mock）。"""
    if config.IMAGE_MOCK:
        time.sleep(1)
        return ""
    client = OpenAI(api_key=config.IMAGE_API_KEY, base_url=config.IMAGE_BASE_URL)
    resp = client.images.generate(
        model=config.IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",
    )
    return resp.data[0].url or ""
