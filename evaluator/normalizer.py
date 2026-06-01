"""响应归一化（PROJECT.md §8.2）

将 LLM 多样化输出统一解析为 List[{"tool": str, "args": dict}]：
  ① 纯 JSON          [{"tool": ..., "args": ...}]
  ② Markdown 包裹     ```json ... ```
  ③ 携带前后解释文字   "好的，我会这样做：```json ...``` 完成。"
  ④ 原生 tool_calls   {"tool_calls": [{"function": {"name", "arguments"}}]}

字段命名兼容：tool / tool_name / name；args / arguments / parameters。
解析失败一律返回 []，由 scorer 直接判 0 分。
"""
import json
import re
from typing import Any, Dict, List, Optional

# 优先匹配 ```json ... ```，其次匹配裸 ``` ... ```
_CODE_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

# obj 形态下，工具序列可能挂在这些键之一上
_LIST_KEYS = ("tool_pipeline", "tool_calls", "calls", "steps", "pipeline")


def normalize_response(raw: Any) -> List[Dict[str, Any]]:
    """主入口：任意 raw_response → 规整工具调用列表，失败返回 []。"""
    if raw is None:
        return []
    if isinstance(raw, list):
        return _coerce_calls(raw)
    if isinstance(raw, dict):
        return _extract_from_obj(raw)
    if not isinstance(raw, str):
        return []

    text = raw.strip()
    if not text:
        return []

    parsed: Optional[Any] = None
    m = _CODE_BLOCK.search(text)
    if m:
        parsed = _try_json(m.group(1).strip())
    if parsed is None:
        parsed = _try_json(text)
    if parsed is None:
        parsed = _try_json(_slice_outer(text))
    if parsed is None:
        return []

    if isinstance(parsed, list):
        return _coerce_calls(parsed)
    if isinstance(parsed, dict):
        return _extract_from_obj(parsed)
    return []


def _try_json(s: Optional[str]) -> Optional[Any]:
    if not s:
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return None


def _slice_outer(text: str) -> Optional[str]:
    """从夹带解释文字的文本里，截出最外层的 [...] 或 {...}。"""
    for open_c, close_c in (("[", "]"), ("{", "}")):
        i, j = text.find(open_c), text.rfind(close_c)
        if i != -1 and j != -1 and j > i:
            return text[i : j + 1]
    return None


def _extract_from_obj(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in _LIST_KEYS:
        val = obj.get(key)
        if isinstance(val, list):
            return _coerce_calls(val)
    # 对象本身可能就是单条调用
    single = _coerce_call(obj)
    return [single] if single else []


def _coerce_calls(items: List[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items:
        call = _coerce_call(item)
        if call:
            out.append(call)
    return out


def _coerce_call(item: Any) -> Optional[Dict[str, Any]]:
    """把单个调用对象规整成 {"tool": str, "args": dict}，无法识别返回 None。"""
    if not isinstance(item, dict):
        return None

    # OpenAI 原生：{"function": {"name", "arguments": "<json string>"}}
    fn = item.get("function")
    if isinstance(fn, dict):
        tool = fn.get("name")
        args = _as_dict(fn.get("arguments"))
        return {"tool": tool, "args": args} if tool else None

    tool = item.get("tool") or item.get("tool_name") or item.get("name")
    if not tool:
        return None
    raw_args = (
        item.get("args")
        if item.get("args") is not None
        else item.get("arguments")
        if item.get("arguments") is not None
        else item.get("parameters")
    )
    return {"tool": tool, "args": _as_dict(raw_args)}


def _as_dict(value: Any) -> Dict[str, Any]:
    """args 可能是 dict、JSON 字符串或 None，一律规整为 dict。"""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = _try_json(value)
        return parsed if isinstance(parsed, dict) else {}
    return {}
