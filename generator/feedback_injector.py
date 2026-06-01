"""Badcase 反向注入：badcase → seeds.json（PROJECT.md §10）

闭环逻辑：
  1. 从 badcases.json 取低分用例
  2. 关联 benchmark 找回原 prompt（badcase 本身不含 prompt 字段）
  3. 改写为种子格式 + 打 `from_badcase` tag + 记录 source_badcase_task_id / source_agent
  4. 追加到 seeds.json，task_id 采用 `<skill_prefix>_FB_NNN` 避开原序号

两种模式：
  - inject_auto        ：按 skill 取最低分前 N 条（教学 / CI 兜底）
  - inject_interactive ：y / n / q 交互审阅
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

SKILL_PREFIX = {
    "SecureAdminExecution": "T_SAE",
    "CustomerTicketHandling": "T_CTH",
    "DataExportWithMasking": "T_DEM",
    "IncidentAlertResponse": "T_IAR",
}


def _alloc_seed_id(skill: str, taken_ids: set) -> str:
    prefix = SKILL_PREFIX.get(skill, "T_FB")
    idx = 1
    while True:
        cand = f"{prefix}_FB_{idx:03d}"
        if cand not in taken_ids:
            return cand
        idx += 1


def build_seed_from_badcase(
    badcase: dict,
    benchmark_by_id: Dict[str, dict],
    new_task_id: str,
    today_iso: Optional[str] = None,
) -> Optional[dict]:
    """从 badcase 构造一条种子；找不到原 prompt 则返回 None。"""
    src = benchmark_by_id.get(badcase["task_id"])
    if src is None:
        return None
    return {
        "task_id": new_task_id,
        "skill_name": badcase["skill_name"],
        "difficulty": badcase["difficulty"],
        "prompt": src["prompt"],
        "expected_tool_calls": badcase["expected"],
        "version": "v0.2",
        "created_at": today_iso or date.today().isoformat(),
        "tags": ["seed", "from_badcase"],
        "source_badcase_task_id": badcase["task_id"],
        "source_agent": badcase.get("agent", "unknown"),
        "source_score": badcase.get("total_score"),
    }


def inject_auto(
    badcases: List[dict],
    benchmark: List[dict],
    *,
    per_skill: int = 2,
    seeds_path: str = "data/seeds.json",
) -> dict:
    """按 skill 取 lowest-score 前 per_skill 条注入；同一原 task_id 不重复注入。"""
    benchmark_by_id = {c["task_id"]: c for c in benchmark}
    by_skill: Dict[str, List[dict]] = defaultdict(list)
    for bc in badcases:
        by_skill[bc["skill_name"]].append(bc)

    with open(seeds_path, "r", encoding="utf-8") as f:
        seeds = json.load(f)
    taken_ids = {s["task_id"] for s in seeds}

    new_seeds: List[dict] = []
    skipped = 0
    for skill, items in by_skill.items():
        items.sort(key=lambda x: x["total_score"])
        seen_src: set = set()
        added = 0
        for bc in items:
            if added >= per_skill:
                break
            if bc["task_id"] in seen_src:
                continue
            new_id = _alloc_seed_id(skill, taken_ids)
            seed = build_seed_from_badcase(bc, benchmark_by_id, new_id)
            if seed is None:
                skipped += 1
                continue
            new_seeds.append(seed)
            taken_ids.add(new_id)
            seen_src.add(bc["task_id"])
            added += 1

    seeds.extend(new_seeds)
    with open(seeds_path, "w", encoding="utf-8") as f:
        json.dump(seeds, f, ensure_ascii=False, indent=2)

    return {
        "injected": len(new_seeds),
        "skipped": skipped,
        "seeds_total_now": len(seeds),
        "by_skill": {
            sk: sum(1 for s in new_seeds if s["skill_name"] == sk) for sk in by_skill
        },
        "new_task_ids": [s["task_id"] for s in new_seeds],
    }


def inject_interactive(
    badcases: List[dict],
    benchmark: List[dict],
    seeds_path: str = "data/seeds.json",
) -> dict:
    """y / n / q 交互审阅。"""
    benchmark_by_id = {c["task_id"]: c for c in benchmark}
    with open(seeds_path, "r", encoding="utf-8") as f:
        seeds = json.load(f)
    taken_ids = {s["task_id"] for s in seeds}

    new_seeds: List[dict] = []
    accepted = rejected = 0
    quit_early = False

    for i, bc in enumerate(badcases, 1):
        src = benchmark_by_id.get(bc["task_id"], {})
        print(
            f"\n[{i}/{len(badcases)}] {bc['task_id']} | {bc['skill_name']} | "
            f"{bc['difficulty']} | score={bc['total_score']}"
        )
        print(f"  Prompt   : {src.get('prompt', '<missing>')[:160]}")
        print(f"  Expected : {json.dumps(bc['expected'], ensure_ascii=False)[:200]}")
        print(f"  Predicted: {json.dumps(bc['predicted'], ensure_ascii=False)[:200]}")
        try:
            ans = input("  Inject? [y/n/q] ").strip().lower()
        except EOFError:
            quit_early = True
            break
        if ans == "q":
            quit_early = True
            break
        if ans != "y":
            rejected += 1
            continue
        new_id = _alloc_seed_id(bc["skill_name"], taken_ids)
        seed = build_seed_from_badcase(bc, benchmark_by_id, new_id)
        if seed is None:
            rejected += 1
            continue
        new_seeds.append(seed)
        taken_ids.add(new_id)
        accepted += 1

    seeds.extend(new_seeds)
    with open(seeds_path, "w", encoding="utf-8") as f:
        json.dump(seeds, f, ensure_ascii=False, indent=2)
    return {
        "accepted": accepted,
        "rejected": rejected,
        "quit_early": quit_early,
        "seeds_total_now": len(seeds),
        "new_task_ids": [s["task_id"] for s in new_seeds],
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="badcase → seeds.json 反向注入")
    p.add_argument("--mode", choices=["auto", "interactive"], default="auto")
    p.add_argument("--per-skill", type=int, default=2)
    p.add_argument("--badcases", default="data/badcases.json")
    p.add_argument(
        "--benchmark", default="data/version_history/benchmark_v1.0.0.json"
    )
    p.add_argument("--seeds", default="data/seeds.json")
    args = p.parse_args(argv)

    with open(args.badcases, "r", encoding="utf-8") as f:
        badcases = json.load(f)
    with open(args.benchmark, "r", encoding="utf-8") as f:
        benchmark = json.load(f)

    if args.mode == "auto":
        stats = inject_auto(
            badcases, benchmark, per_skill=args.per_skill, seeds_path=args.seeds
        )
    else:
        stats = inject_interactive(badcases, benchmark, seeds_path=args.seeds)

    print("\n=== Inject ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
