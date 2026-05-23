"""参数矩阵插值器：从种子用例膨胀到候选池

PLAN.md D2 目标：40 种子 → 约 600 候选（不调 LLM）

策略：对每条种子识别可变参数（user_id / IP / item_id）的"当前值"，
从预定义池中挑选替代值，做笛卡尔积，每条种子最多生成 20 个变体。
变体的 task_id 形如 `<原 id>_V00..V19`，并打 `expanded` tag。
"""
import itertools
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional


USER_ID_POOL = ["USR_001", "USR_042", "USR_103", "USR_215", "USR_777", "USR_888"]
IP_POOL = ["10.0.0.5", "10.0.0.20", "192.168.1.1", "172.16.0.10", "10.0.0.99"]
ITEM_ID_POOL = ["ITEM_1001", "ITEM_2002", "ITEM_5005", "ITEM_9999"]

MAX_VARIANTS_PER_SEED = 20


def expand_seed(seed: dict) -> List[dict]:
    """对单条种子做参数化膨胀，返回 ≤ MAX_VARIANTS_PER_SEED 条变体。"""
    text = seed["prompt"]
    old_uid = _first_match(text, r"USR_\d{3}")
    old_ip = _first_match(text, r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
    old_item = _first_match(text, r"ITEM_\d{4}")

    uid_alts = _exclude(USER_ID_POOL, old_uid)[:5] if old_uid else [None]
    ip_alts = _exclude(IP_POOL, old_ip)[:4] if old_ip else [None]
    item_alts = _exclude(ITEM_ID_POOL, old_item)[:3] if old_item else [None]

    combos = list(itertools.product(uid_alts, ip_alts, item_alts))
    random.seed(seed["task_id"])  # 让每条种子的变体顺序可复现
    random.shuffle(combos)
    combos = combos[:MAX_VARIANTS_PER_SEED]

    variants = []
    for idx, (new_uid, new_ip, new_item) in enumerate(combos):
        v = _apply_substitutions(seed, old_uid, new_uid, old_ip, new_ip, old_item, new_item)
        v["task_id"] = f"{seed['task_id']}_V{idx:02d}"
        v["tags"] = list(v.get("tags", [])) + ["expanded"]
        variants.append(v)
    return variants


def expand_all(seeds: List[dict]) -> List[dict]:
    out = []
    for seed in seeds:
        out.extend(expand_seed(seed))
    return out


def run(input_path: str = "data/seeds.json",
        output_path: str = "data/candidates_v0.0.json") -> List[dict]:
    """加载种子，全量膨胀，写到 output_path。返回膨胀后的列表。"""
    with open(input_path, "r", encoding="utf-8") as f:
        seeds = json.load(f)
    variants = expand_all(seeds)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(variants, f, ensure_ascii=False, indent=2)
    return variants


def _first_match(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text)
    return m.group() if m else None


def _exclude(pool: List[str], value: Optional[str]) -> List[str]:
    return [x for x in pool if x != value]


def _apply_substitutions(seed: dict, old_uid, new_uid, old_ip, new_ip, old_item, new_item) -> dict:
    """对整条种子做全局字符串替换。

    把 JSON 序列化成字符串，对 old → new 做 str.replace，再反序列化。
    这样 prompt + tool_calls.args 中的同一标识符会被一致地替换。
    """
    s = json.dumps(seed, ensure_ascii=False)
    if old_uid and new_uid:
        s = s.replace(old_uid, new_uid)
    if old_ip and new_ip:
        s = s.replace(old_ip, new_ip)
    if old_item and new_item:
        s = s.replace(old_item, new_item)
    return json.loads(s)


if __name__ == "__main__":
    variants = run()
    with open("data/seeds.json", "r", encoding="utf-8") as f:
        seed_count = len(json.load(f))
    print(f"Expanded {seed_count} seeds -> {len(variants)} variants")
    print(f"Avg per seed: {len(variants) / seed_count:.1f}")
    print("Output: data/candidates_v0.0.json")
