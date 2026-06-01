"""JSON Schema 强校验器（PROJECT.md §6.1 第一层）

- validate_schema(test_case)：单条校验，True/False
- validate_one(candidate_dict)：单条候选 → (ok, reason)
- validate_batch(candidates)：批量 → dict 统计 + 每条结果
"""
from typing import Dict, List, Tuple

from jsonschema import validate, ValidationError

from models import TestCase
from skills_ontology import SKILLS
from tools_schema import TOOLS_SCHEMA


def validate_schema(test_case: TestCase) -> bool:
    """逐条校验 expected_tool_calls 的工具名 + 参数是否符合 JSON Schema。"""
    for call in test_case.expected_tool_calls:
        schema = TOOLS_SCHEMA.get(call.tool)
        if schema is None:
            return False
        try:
            validate(instance=call.args, schema=schema)
        except ValidationError:
            return False
    return True


def validate_one(candidate: dict) -> Tuple[bool, str]:
    """对一条候选（dict 形式）做完整校验，返回 (是否合法, 失败原因)。

    检查：
    1. 必需字段齐全
    2. skill_name 在 SKILLS 中
    3. difficulty 取值合法
    4. expected_tool_calls 每个工具名在 TOOLS_SCHEMA、参数符合 JSON Schema
    5. 工具必须在该 Skill 的 allowed_tools 内（对抗题除外，对抗题允许空 expected_tool_calls）
    """
    required = ["task_id", "skill_name", "difficulty", "prompt", "expected_tool_calls"]
    for f in required:
        if f not in candidate:
            return False, f"missing_field:{f}"

    skill_name = candidate["skill_name"]
    skill = SKILLS.get(skill_name)
    if skill is None:
        return False, f"unknown_skill:{skill_name}"

    if candidate["difficulty"] not in ("normal", "boundary", "adversarial"):
        return False, f"bad_difficulty:{candidate['difficulty']}"

    calls = candidate["expected_tool_calls"]
    if not isinstance(calls, list):
        return False, "expected_tool_calls_not_list"

    # 对抗题允许空 expected（"拒绝执行"），其他难度必须非空
    if len(calls) == 0 and candidate["difficulty"] != "adversarial":
        return False, "empty_expected_for_non_adversarial"

    allowed = set(skill.allowed_tools)
    for i, call in enumerate(calls):
        if not isinstance(call, dict) or "tool" not in call or "args" not in call:
            return False, f"malformed_call_at_{i}"
        tool = call["tool"]
        if tool not in TOOLS_SCHEMA:
            return False, f"unknown_tool:{tool}"
        if tool not in allowed:
            return False, f"tool_not_in_skill_allowed:{tool}"
        try:
            validate(instance=call["args"], schema=TOOLS_SCHEMA[tool])
        except ValidationError as e:
            return False, f"args_schema_fail_at_{i}:{e.message[:80]}"

    return True, "ok"


def validate_batch(candidates: List[dict]) -> Dict:
    """批量校验，返回统计字典。

    返回结构：
        {
          "total": N,
          "passed": int,
          "failed": int,
          "pass_rate": float,
          "fail_reasons": {reason_prefix: count},
          "results": [{"task_id":..., "ok":bool, "reason":str}, ...],
        }
    """
    results = []
    fail_reasons: Dict[str, int] = {}
    passed = 0

    for c in candidates:
        ok, reason = validate_one(c)
        results.append({"task_id": c.get("task_id", "?"), "ok": ok, "reason": reason})
        if ok:
            passed += 1
        else:
            # 取冒号前的 reason 前缀做聚合
            key = reason.split(":")[0]
            fail_reasons[key] = fail_reasons.get(key, 0) + 1

    total = len(candidates)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "fail_reasons": fail_reasons,
        "results": results,
    }
