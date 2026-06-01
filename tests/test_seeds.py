"""D2 种子全量 schema 校验 + D10 反向注入种子兼容

加载 data/seeds.json 中所有种子，通过 schema_validator 强校验。
原始 40 条（无 from_badcase tag）必须严格 4 Skill × (6 normal + 3 boundary + 1 adversarial)。
D10 反向注入的种子（含 from_badcase tag）单独校验：仅做 schema + task_id 唯一。
"""
from collections import Counter

import pytest

from seed_loader import load_seeds
from validator.schema_validator import validate_schema


_SEEDS = load_seeds("data/seeds.json")
_ORIGINAL = [c for c in _SEEDS if "from_badcase" not in c.tags]
_INJECTED = [c for c in _SEEDS if "from_badcase" in c.tags]


@pytest.mark.parametrize("case", _SEEDS, ids=[c.task_id for c in _SEEDS])
def test_seed_passes_schema(case):
    assert validate_schema(case), f"{case.task_id} 未通过 schema 校验"


def test_original_seed_total_count():
    assert len(_ORIGINAL) == 40, f"原始种子总数应为 40，实际 {len(_ORIGINAL)}"


def test_original_seed_distribution_per_skill():
    """原始 40 条种子：每个 Skill 必须严格 6 normal + 3 boundary + 1 adversarial。"""
    by_skill = {}
    for c in _ORIGINAL:
        by_skill.setdefault(c.skill_definition.skill_name, []).append(c.difficulty)
    expected = {"normal": 6, "boundary": 3, "adversarial": 1}
    for skill, difficulties in by_skill.items():
        actual = dict(Counter(difficulties))
        assert actual == expected, f"{skill} 分布异常: {actual}"
    assert len(by_skill) == 4, f"Skill 数应为 4，实际 {len(by_skill)}"


def test_seed_task_id_unique():
    task_ids = [c.task_id for c in _SEEDS]
    assert len(task_ids) == len(set(task_ids)), "task_id 存在重复"


def test_injected_seeds_have_provenance():
    """D10 反向注入的种子必须带 from_badcase tag，且 task_id 形如 T_<SKILL>_FB_NNN。"""
    for c in _INJECTED:
        assert "from_badcase" in c.tags, f"{c.task_id} 未标记 from_badcase"
        assert "_FB_" in c.task_id, f"{c.task_id} 不符合 _FB_ 命名空间"
