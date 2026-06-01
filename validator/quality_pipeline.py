"""D5 主流水线：v0.9 候选 → 自动质检 → v0.95 候选

流程：
1. 加载 data/candidates_v0.9.json
2. JSON Schema 强校验（淘汰 schema_fail）
3. LLM-as-Judge 三维打分（默认 REAL，可通过 EVAL_MODE=MOCK 切换）
4. 淘汰策略：schema_fail 必淘 + 三维任一 < 3 淘汰
5. 输出 data/candidates_v0.95.json
6. 生成 data/reports/quality_report_v1.0.0.md

CLI：
    python -m validator.quality_pipeline                  # REAL 默认
    EVAL_MODE=MOCK python -m validator.quality_pipeline   # MOCK 跑通逻辑
"""
import json
import os
import time
from pathlib import Path
from typing import List

from reports.reporter import generate_quality_report
from validator.llm_judge import judge_all
from validator.schema_validator import validate_batch


DEFAULT_CUTOFF = 3  # 三维任一 < 3 即淘汰


def run(
    src_path: str = "data/candidates_v0.9.json",
    dst_path: str = "data/candidates_v0.95.json",
    report_path: str = "data/reports/quality_report_v1.0.0.md",
    judge_scores_path: str = "data/judge_scores_v0.9.json",
    version_tag: str = "v1.0.0",
    mode: str = None,
    cutoff: int = DEFAULT_CUTOFF,
    max_workers: int = 10,
) -> dict:
    mode = (mode or os.getenv("EVAL_MODE") or "REAL").upper()
    t_start = time.time()

    print(f"[1/4] Loading {src_path}...")
    with open(src_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
    print(f"      {len(candidates)} candidates")

    print("[2/4] JSON Schema batch validation...")
    schema_result = validate_batch(candidates)
    print(
        f"      passed {schema_result['passed']}/{schema_result['total']} "
        f"({schema_result['pass_rate']*100:.1f}%)"
    )

    # 只让 schema 通过的进 judge，节省 API
    schema_ok_ids = {r["task_id"] for r in schema_result["results"] if r["ok"]}
    judge_input = [c for c in candidates if c["task_id"] in schema_ok_ids]

    print(f"[3/4] LLM Judge ({mode} mode, {max_workers} workers, {len(judge_input)} cases)...")
    t = time.time()
    judge_scores = judge_all(judge_input, mode=mode, max_workers=max_workers)
    print(f"      done in {time.time()-t:.1f}s")

    # 落盘原始打分，便于复查
    Path(judge_scores_path).parent.mkdir(parents=True, exist_ok=True)
    with open(judge_scores_path, "w", encoding="utf-8") as f:
        json.dump(judge_scores, f, ensure_ascii=False, indent=2)

    # 应用淘汰规则
    by_id = {s["task_id"]: s for s in judge_scores}
    keep_ids: List[str] = []
    for c in candidates:
        tid = c["task_id"]
        if tid not in schema_ok_ids:
            continue
        s = by_id.get(tid)
        if s is None:
            continue
        if any(s[d] < cutoff for d in ("decidability", "difficulty_fit", "fluency")):
            continue
        keep_ids.append(tid)

    keep_set = set(keep_ids)
    kept = [c for c in candidates if c["task_id"] in keep_set]

    # 升版 + 写出 v0.95
    for c in kept:
        c["version"] = "v0.95"
    Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)
    print(f"[4/4] Wrote v0.95 → {dst_path} ({len(kept)} kept)")

    # 生成报告
    generate_quality_report(
        version=version_tag,
        candidates_v09=candidates,
        schema_result=schema_result,
        judge_scores=judge_scores,
        keep_ids=keep_ids,
        output_path=report_path,
        cutoff_threshold=cutoff,
    )
    print(f"      report → {report_path}")

    elapsed = round(time.time() - t_start, 1)
    stats = {
        "mode": mode,
        "input_total": len(candidates),
        "schema_passed": schema_result["passed"],
        "schema_failed": schema_result["failed"],
        "judged": len(judge_scores),
        "kept_after_judge": len(kept),
        "keep_rate": round(len(kept) / len(candidates), 4) if candidates else 0.0,
        "elapsed_sec": elapsed,
        "output_path": dst_path,
        "report_path": report_path,
    }
    return stats


if __name__ == "__main__":
    stats = run()
    print("\n=== Stats ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
