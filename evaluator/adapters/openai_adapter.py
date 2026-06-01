"""OpenAI Adapter（PROJECT.md §8.1）— 预留接口

D8 评测时第二 Agent (qwen) 走 MockAdapter + 高 error_rate 模拟，
未实际调用 OpenAI / Qwen 真 API（参考 PROJECT.md §11.1 MOCK 模式说明）。

切换 REAL 模式时，按 BaseAdapter 接口实现 call(prompt, tools_schema) → str 即可，
evaluator/pipeline.py 通过 adapter.name 路由，无需改动判分链路。
"""

from evaluator.adapters.base import BaseAdapter


class OpenAIAdapter(BaseAdapter):
    name = "openai"

    def call(self, prompt: str, tools_schema):  # pragma: no cover — REAL 模式才会用到
        raise NotImplementedError(
            "OpenAIAdapter 仅作为 REAL 模式预留。MOCK 评测请用 MockAdapter。"
        )
