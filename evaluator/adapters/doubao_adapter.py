"""Doubao Adapter（豆包 / 字节豆包，Volcengine ARK OpenAI 兼容模式）

走火山方舟 ARK 的 OpenAI 兼容接口，复用 openai SDK，
与 DeepSeekAdapter / QwenAdapter 同一个套路。

需要在 .env 里设：
  DOUBAO_API_KEY=ark-xxxxx         # 火山方舟控制台拿
  DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3   # 可选，默认值
"""
import os
import time
from typing import Any, Dict, Optional

from openai import OpenAI
from dotenv import load_dotenv

from config import MAX_RETRIES, RETRY_DELAY
from evaluator.adapters.base import BaseAdapter, build_system_prompt
from models import SkillDefinition

load_dotenv()


class DoubaoAdapter(BaseAdapter):
    name = "doubao"

    def __init__(self, model: str = "doubao-seed-2-0-mini-260428"):
        self.model = model
        self._client: Optional[OpenAI] = None

    def _ensure_client(self) -> OpenAI:
        if self._client is None:
            api_key = os.getenv("DOUBAO_API_KEY", "")
            if not api_key:
                raise RuntimeError("DOUBAO_API_KEY not set")
            base_url = os.getenv(
                "DOUBAO_BASE_URL",
                "https://ark.cn-beijing.volces.com/api/v3",
            )
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        return self._client

    def call(
        self,
        prompt: str,
        tools_schema: Dict[str, Dict[str, Any]],
        task_id: str = "",
        skill_definition: Optional[SkillDefinition] = None,
    ) -> str:
        system_prompt = build_system_prompt(skill_definition)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        last_err: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                # JSON-plan 模式：不传 tools，模型在 content 里输出完整调用序列 JSON
                resp = self._ensure_client().chat.completions.create(
                    model=self.model,
                    messages=messages,
                    timeout=30.0,
                )
                return resp.choices[0].message.content or "[]"
            except Exception as e:
                last_err = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
        print(f"[DoubaoAdapter] 调用失败，已重试 {MAX_RETRIES} 次: {last_err}")
        return "[]"
