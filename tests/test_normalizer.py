"""响应归一化单元测试（PROJECT.md §8.2 / PLAN D7）

4 种格式必须解析正确 + 失败 case 返回 []。
"""
from evaluator.normalizer import normalize_response

EXPECTED = [
    {"tool": "Verify_Permission", "args": {"user_id": "USR_777", "action": "DELETE"}},
]


def test_1_plain_json():
    """① 纯 JSON 数组。"""
    raw = '[{"tool": "Verify_Permission", "args": {"user_id": "USR_777", "action": "DELETE"}}]'
    assert normalize_response(raw) == EXPECTED


def test_2_markdown_wrapped():
    """② ```json ... ``` 代码块包裹。"""
    raw = '```json\n[{"tool": "Verify_Permission", "args": {"user_id": "USR_777", "action": "DELETE"}}]\n```'
    assert normalize_response(raw) == EXPECTED


def test_3_with_surrounding_text():
    """③ 前后夹带解释文字。"""
    raw = (
        "好的，根据您的需求我会先校验权限：\n"
        '[{"tool": "Verify_Permission", "args": {"user_id": "USR_777", "action": "DELETE"}}]\n'
        "完成后我会通知您。"
    )
    assert normalize_response(raw) == EXPECTED


def test_4_native_tool_calls():
    """④ 原生 tool_calls 字段（OpenAI 风格，arguments 为 JSON 字符串）。"""
    raw = {
        "tool_calls": [
            {
                "function": {
                    "name": "Verify_Permission",
                    "arguments": '{"user_id": "USR_777", "action": "DELETE"}',
                }
            }
        ]
    }
    assert normalize_response(raw) == EXPECTED


def test_5_field_name_compat():
    """字段命名兼容：tool_name / arguments。"""
    raw = '[{"tool_name": "Verify_Permission", "arguments": {"user_id": "USR_777", "action": "DELETE"}}]'
    assert normalize_response(raw) == EXPECTED


def test_6_garbage_returns_empty():
    """完全不是 JSON → 返回 []（→ 判 0 分）。"""
    assert normalize_response("我无法完成这个操作，因为权限不足。") == []


def test_7_empty_and_none():
    """空串 / None → []。"""
    assert normalize_response("") == []
    assert normalize_response(None) == []
