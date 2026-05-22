"""响应归一化（PROJECT.md §8.2）

将 LLM 多样化输出（纯 JSON / ```json / 带前后解释 / 原生 tool_calls）
统一解析为 List[{"tool": str, "args": dict}]。
TODO: D7 完成
"""
