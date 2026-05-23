"""JSON Schema 强校验器（PROJECT.md §6.1 第一层）

D1 MVP：对单条 TestCase 的 expected_tool_calls 做 JSON Schema 强校验。
D5 会扩展为批量校验 + 错误聚合到 quality_report。
"""
from jsonschema import validate, ValidationError

from models import TestCase
from tools_schema import TOOLS_SCHEMA


def validate_schema(test_case: TestCase) -> bool:
    """逐条校验 expected_tool_calls 的工具名 + 参数是否符合 JSON Schema。

    任一 tool_call 工具名不存在或参数不通过 schema，即判定整条用例不合法。
    """
    for call in test_case.expected_tool_calls:
        schema = TOOLS_SCHEMA.get(call.tool)
        if schema is None:
            return False
        try:
            validate(instance=call.args, schema=schema)
        except ValidationError:
            return False
    return True
