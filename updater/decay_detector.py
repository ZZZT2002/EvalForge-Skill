"""衰退检测（PROJECT.md §9.1）

找出所有 Agent 平均分 ≥ DECAY_THRESHOLD 的 task。
"""
from collections import defaultdict
from typing import Dict, List

from config import DECAY_THRESHOLD


def detect_decay(
    results_by_agent: Dict[str, List[dict]],
    threshold: float = DECAY_THRESHOLD,
) -> List[Dict]:
    """返回 [{task_id, mean_score, by_agent}]，按 mean_score 倒序。"""
    task_scores: Dict[str, Dict[str, float]] = defaultdict(dict)
    for agent, records in results_by_agent.items():
        for r in records:
            task_scores[r["task_id"]][agent] = r["score"]["total"]

    decay: List[dict] = []
    for task_id, by_agent in task_scores.items():
        if not by_agent:
            continue
        mean = sum(by_agent.values()) / len(by_agent)
        if mean >= threshold:
            decay.append(
                {
                    "task_id": task_id,
                    "mean_score": round(mean, 2),
                    "by_agent": {a: round(s, 2) for a, s in by_agent.items()},
                }
            )
    return sorted(decay, key=lambda x: -x["mean_score"])
