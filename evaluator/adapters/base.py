"""Agent 适配层基类（PROJECT.md §8.1）"""
from typing import List, Dict, Any


class BaseAdapter:
    name: str = "base"

    def call(self, prompt: str, tools_schema: List[Dict[str, Any]]) -> str:
        """返回 Agent 的原始 raw_response 字符串"""
        raise NotImplementedError
