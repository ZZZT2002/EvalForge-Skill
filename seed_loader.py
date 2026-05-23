"""加载 data/seeds.json 并 hydrate SkillDefinition。

seeds.json 用 `skill_name` 字符串简写引用 4 个 Skill 本体（避免 40 次重复内嵌）；
加载时把 skill_name 替换为 skills_ontology.SKILLS 里的完整 SkillDefinition，
得到符合 models.TestCase 模型的对象列表。
"""
import json
from typing import List

from models import TestCase
from skills_ontology import SKILLS


def load_seeds(path: str = "data/seeds.json") -> List[TestCase]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [_hydrate(item) for item in raw]


def _hydrate(item: dict) -> TestCase:
    item = dict(item)  # 避免修改调用方传入的 dict
    skill_name = item.pop("skill_name")
    if skill_name not in SKILLS:
        raise KeyError(f"Unknown skill_name in seeds.json: {skill_name!r}")
    item["skill_definition"] = SKILLS[skill_name]
    return TestCase(**item)
