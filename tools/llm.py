"""DeepSeek 文本接口（OpenAI 兼容）。

主题规划、文案生成都走这一个入口；换厂商只需改 .env 里的
BASE_URL / MODEL / KEY，业务代码不动。
"""
import time

from openai import OpenAI

import config

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
    return _client


def chat(system_prompt: str, user_prompt: str) -> str:
    """统一的 LLM 调用入口。未配置 key 时返回 mock 文本。"""
    if config.LLM_MOCK:
        time.sleep(1)  # 模拟耗时，便于观察前端状态流转
        return f"[mock] 针对「{user_prompt[:30]}」生成的文本"
    resp = _get_client().chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content.strip()
