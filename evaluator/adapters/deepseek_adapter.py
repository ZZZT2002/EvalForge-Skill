"""DeepSeek Adapter（PROJECT.md §8.1）

调用 DeepSeek function calling API，返回归一化器可解析的 raw_response 字符串。
- 有 tool_calls → 序列化成 [{"tool", "args"}] JSON 字符串
- 无 tool_calls → 回退返回 message.content（可能是 json / markdown / 解释文字）
失败重试 MAX_RETRIES 次，仍失败返回 "[]"（→ 判 0 分，不中断流水线）。
"""
import os
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI
from dotenv import load_dotenv

from config import MAX_RETRIES, RETRY_DELAY
from evaluator.adapters.base import BaseAdapter, serialize_tool_calls, to_openai_tools

load_dotenv()


class DeepSeekAdapter(BaseAdapter):
    name = "deepseek"

    def __init__(self, model: str = "deepseek-chat"):
        self.model = model
        self._client: Optional[OpenAI] = None

    def _ensure_client(self) -> OpenAI:
        if self._client is None:
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            if not api_key:
                raise RuntimeError("DEEPSEEK_API_KEY not set")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        return self._client

    def call(self, prompt: str, tools_schema: Dict[str, Dict[str, Any]], **_) -> str:
        tools = to_openai_tools(tools_schema)
        last_err: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self._ensure_client().chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    tools=tools,
                    tool_choice="auto",
                    timeout=30.0,
                )
                msg = resp.choices[0].message
                if msg.tool_calls:
                    return serialize_tool_calls(msg.tool_calls)
                return msg.content or "[]"
            except Exception as e:  # 网络 / 限流 / 超时
                last_err = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
        print(f"[DeepSeekAdapter] 调用失败，已重试 {MAX_RETRIES} 次: {last_err}")
        return "[]"
