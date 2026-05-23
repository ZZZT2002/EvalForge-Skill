"""D2 matrix_expander 单元测试

验证:
- 40 seeds → ≥ 500 variants
- 每条种子膨胀 ≤ 20
- 所有变体通过 schema 校验
- task_id 全局唯一
- skill_name / difficulty 保持不变
"""
import json
from collections import Counter

import pytest

from generator.matrix_expander import expand_seed, expand_all, MAX_VARIANTS_PER_SEED
from models import TestCase
from skills_ontology import SKILLS
from validator.schema_validator import validate_schema


with open("data/seeds.json", "r", encoding="utf-8") as f:
    _SEEDS = json.load(f)


@pytest.fixture(scope="module")
def variants():
    return expand_all(_SEEDS)


def _hydrate(d: dict) -> TestCase:
    d = dict(d)
    skill_name = d.pop("skill_name")
    d["skill_definition"] = SKILLS[skill_name]
    return TestCase(**d)


def test_total_variants_meets_target(variants):
    assert len(variants) >= 500, f"variants {len(variants)} < 500"


def test_per_seed_cap(variants):
    by_origin = Counter(v["task_id"].rsplit("_V", 1)[0] for v in variants)
    for origin, n in by_origin.items():
        assert n <= MAX_VARIANTS_PER_SEED, f"{origin}: {n} > {MAX_VARIANTS_PER_SEED}"


def test_all_variants_pass_schema(variants):
    for v in variants:
        case = _hydrate(v)
        assert validate_schema(case), f"{v['task_id']} 未通过 schema 校验"


def test_task_id_unique(variants):
    ids = [v["task_id"] for v in variants]
    assert len(ids) == len(set(ids)), "变体 task_id 存在重复"


def test_skill_and_difficulty_preserved(variants):
    """膨胀只动 user_id/IP/item_id 这些参数，skill_name 和 difficulty 不应变。"""
    origin_by_id = {s["task_id"]: s for s in _SEEDS}
    for v in variants:
        origin = origin_by_id[v["task_id"].rsplit("_V", 1)[0]]
        assert v["skill_name"] == origin["skill_name"]
        assert v["difficulty"] == origin["difficulty"]


def test_variant_actually_differs_from_origin(variants):
    """每个变体的 user_id/IP/item_id 至少有一项与原种子不同。"""
    origin_by_id = {s["task_id"]: s for s in _SEEDS}
    for v in variants:
        origin = origin_by_id[v["task_id"].rsplit("_V", 1)[0]]
        assert v["prompt"] != origin["prompt"] or v["expected_tool_calls"] != origin["expected_tool_calls"], \
            f"{v['task_id']} 与原种子完全相同，膨胀失败"
