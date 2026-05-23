"""D2 种子全量 schema 校验

加载 data/seeds.json 中所有 40 条种子，通过 schema_validator 强校验。
任何一条 expected_tool_calls 不符合 JSON Schema 都会让对应 test 红。
"""
import json
from collections import Counter

import pytest

from seed_loader import load_seeds
from validator.schema_validator import validate_schema


_SEEDS = load_seeds("data/seeds.json")


@pytest.mark.parametrize("case", _SEEDS, ids=[c.task_id for c in _SEEDS])
def test_seed_passes_schema(case):
    assert validate_schema(case), f"{case.task_id} 未通过 schema 校验"


def test_seed_total_count():
    assert len(_SEEDS) == 40, f"种子总数应为 40，实际 {len(_SEEDS)}"


def test_seed_distribution_per_skill():
    """每个 Skill 必须严格 6 normal + 3 boundary + 1 adversarial = 10 条。"""
    by_skill = {}
    for c in _SEEDS:
        by_skill.setdefault(c.skill_definition.skill_name, []).append(c.difficulty)
    expected = {"normal": 6, "boundary": 3, "adversarial": 1}
    for skill, difficulties in by_skill.items():
        actual = dict(Counter(difficulties))
        assert actual == expected, f"{skill} 分布异常: {actual}"
    assert len(by_skill) == 4, f"Skill 数应为 4，实际 {len(by_skill)}"


def test_seed_task_id_unique():
    task_ids = [c.task_id for c in _SEEDS]
    assert len(task_ids) == len(set(task_ids)), "task_id 存在重复"
