"""Agent 适配层基类（PROJECT.md §8.1）"""
import json
from typing import Any, Dict, List


class BaseAdapter:
    name: str = "base"

    def call(self, prompt: str, tools_schema: List[Dict[str, Any]]) -> str:
        """返回 Agent 的原始 raw_response 字符串"""
        raise NotImplementedError


class MockAdapter(BaseAdapter):
    """MOCK 模式：按 task_id 从 data/mock_responses.json 读预设 raw_response。

    用于 D8 切 REAL 之前跑通整条流水线。pipeline 调用时通过 task_id 取响应；
    若无预设则返回 "[]"（归一化为空 → 判 0 分），保证流程不中断。
    """
    name = "mock"

    def __init__(self, responses: Dict[str, str]):
        self._responses = responses

    def call(self, prompt: str, tools_schema: List[Dict[str, Any]], task_id: str = "") -> str:
        return self._responses.get(task_id, "[]")


def to_openai_tools(tools_schema: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 tools_schema.TOOLS_SCHEMA（name -> JSON Schema）转成 OpenAI function 列表。"""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": f"工具 {name}",
                "parameters": schema,
            },
        }
        for name, schema in tools_schema.items()
    ]


def serialize_tool_calls(tool_calls) -> str:
    """把 OpenAI 风格 tool_calls 序列化成归一化器可解析的 JSON 字符串。"""
    calls = []
    for tc in tool_calls or []:
        try:
            args = json.loads(tc.function.arguments)
        except (json.JSONDecodeError, ValueError, TypeError):
            args = {}
        calls.append({"tool": tc.function.name, "args": args})
    return json.dumps(calls, ensure_ascii=False)
