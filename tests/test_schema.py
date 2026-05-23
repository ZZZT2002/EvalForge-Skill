"""D1 schema 校验单元测试

按 PLAN.md D1：1 条合法用例返回 True，5 条非法用例返回 False。
"""
from typing import List

from models import TestCase, ExpectedToolCall
from skills_ontology import SKILLS
from validator.schema_validator import validate_schema


def _make_case(expected_calls: List[ExpectedToolCall]) -> TestCase:
    return TestCase(
        task_id="T_0001",
        skill_definition=SKILLS["SecureAdminExecution"],
        prompt="dummy",
        expected_tool_calls=expected_calls,
        difficulty="normal",
        version="v0.1",
        created_at="2026-05-23",
    )


def test_valid_case():
    case = _make_case([
        ExpectedToolCall(
            tool="Verify_Permission",
            args={"user_id": "USR_777", "action": "DELETE"},
        ),
    ])
    assert validate_schema(case) is True


def test_unknown_tool_name():
    case = _make_case([
        ExpectedToolCall(tool="Nonexistent_Tool", args={}),
    ])
    assert validate_schema(case) is False


def test_missing_required_field():
    # Verify_Permission 缺 action
    case = _make_case([
        ExpectedToolCall(tool="Verify_Permission", args={"user_id": "USR_777"}),
    ])
    assert validate_schema(case) is False


def test_enum_violation():
    # action 不在 READ/WRITE/DELETE/ADMIN
    case = _make_case([
        ExpectedToolCall(
            tool="Verify_Permission",
            args={"user_id": "USR_777", "action": "HACK"},
        ),
    ])
    assert validate_schema(case) is False


def test_pattern_violation():
    # user_id 不匹配 ^USR_\d{3}$
    case = _make_case([
        ExpectedToolCall(
            tool="Verify_Permission",
            args={"user_id": "ABC123", "action": "READ"},
        ),
    ])
    assert validate_schema(case) is False


def test_type_violation():
    # user_id 应为 string，传 int
    case = _make_case([
        ExpectedToolCall(
            tool="Verify_Permission",
            args={"user_id": 777, "action": "READ"},
        ),
    ])
    assert validate_schema(case) is False
