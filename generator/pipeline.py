"""D3 主流水线：seeds → matrix_expander → llm_paraphraser → dedup → v0.9

可独立运行：
    python -m generator.pipeline

注意：会调用 DeepSeek API（约 600 次并发），需要 .env 里的 DEEPSEEK_API_KEY。
"""
import json
import time
from collections import Counter
from pathlib import Path

from generator.matrix_expander import expand_all
from generator.llm_paraphraser import paraphrase_all
from generator.dedup import dedup_by_similarity


def run(
    seeds_path: str = "data/seeds.json",
    output_path: str = "data/candidates_v0.9.json",
    dedup_threshold: float = 0.85,
    paraphrase_workers: int = 10,
) -> dict:
    t_start = time.time()

    print("[1/4] Loading seeds...")
    with open(seeds_path, "r", encoding="utf-8") as f:
        seeds = json.load(f)
    print(f"      {len(seeds)} seeds loaded")

    print("[2/4] Matrix expansion...")
    t = time.time()
    expanded = expand_all(seeds)
    print(f"      {len(expanded)} variants in {time.time()-t:.1f}s")

    print(f"[3/4] LLM paraphrase ({paraphrase_workers} workers)...")
    t = time.time()
    paraphrased = paraphrase_all(expanded, max_workers=paraphrase_workers)
    succ = sum("paraphrased" in c.get("tags", []) for c in paraphrased)
    fail = sum("paraphrase_failed" in c.get("tags", []) for c in paraphrased)
    print(f"      done in {time.time()-t:.1f}s | success {succ}  fail {fail}")

    print(f"[4/4] Dedup at cosine >= {dedup_threshold}...")
    t = time.time()
    deduped = dedup_by_similarity(paraphrased, threshold=dedup_threshold)
    print(f"      kept {len(deduped)} / {len(paraphrased)} in {time.time()-t:.1f}s")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    stats = _compute_stats(deduped)
    stats["total_runtime_sec"] = round(time.time() - t_start, 1)
    stats["paraphrase_success"] = succ
    stats["paraphrase_failed"] = fail
    stats["output_path"] = output_path
    return stats


def _compute_stats(candidates: list) -> dict:
    by_skill = Counter(c["skill_name"] for c in candidates)
    by_difficulty = Counter(c["difficulty"] for c in candidates)
    total = len(candidates)
    skill_dist = {k: round(v / total, 3) for k, v in by_skill.items()}
    diff_dist = {k: round(v / total, 3) for k, v in by_difficulty.items()}
    return {
        "total": total,
        "by_skill": dict(by_skill),
        "by_difficulty": dict(by_difficulty),
        "skill_distribution_pct": skill_dist,
        "difficulty_distribution_pct": diff_dist,
    }


if __name__ == "__main__":
    stats = run()
    print("\n=== Stats ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
