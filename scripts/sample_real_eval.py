"""按 difficulty 分层抽样，对 N 条用例做 REAL 模式评测。

为什么需要这个脚本：
  evaluator/pipeline.py 的 run() 是全量评测（591 条 × 2 agent ≈ 1200 次 API 调用），
  REAL 模式跑一次成本太高。本脚本只抽 N 条（默认 100）跑真 API，
  产出独立的 evaluation_v*_real_sample.md，作为答辩"REAL 抽样"证据，
  对照原 MOCK 全量报告，证明判分链路在真 API 上也能正常工作。

  --dry-run 用 MockAdapter + 高 error_rate 顶替真 API，保证没 API Key 时也能
  跑通 CLI 与产物路径，方便离线开发。

用法：
  python -m scripts.sample_real_eval --n 100 --agent deepseek --dry-run
  python -m scripts.sample_real_eval --n 100 --agent deepseek                # 真跑（需 DEEPSEEK_API_KEY）
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import config
from evaluator.adapters.base import BaseAdapter, MockAdapter
from evaluator.pipeline import (
    build_simulated_responses,
    collect_badcases,
    evaluate,
    load_benchmark,
    save_json,
)
from reports.reporter import generate_evaluation_report


def stratified_sample(
    benchmark: List[dict],
    *,
    n: int,
    seed: int = 7,
) -> List[dict]:
    """按 difficulty 分层抽样：保持 normal / boundary / adversarial 原始比例。

    n 小于 benchmark 大小时，每层至少抽 1 条（防止 adversarial 在 n=10 时被抽空）。
    """
    rng = random.Random(seed)
    by_diff: Dict[str, List[dict]] = defaultdict(list)
    for tc in benchmark:
        by_diff[tc["difficulty"]].append(tc)

    total = len(benchmark)
    sampled: List[dict] = []
    for diff, items in by_diff.items():
        quota = max(1, round(n * len(items) / total))
        rng.shuffle(items)
        sampled.extend(items[:quota])
    return sampled[:n]


def _build_real_adapter(agent: str, dry_run: bool, benchmark: List[dict]) -> BaseAdapter:
    if dry_run:
        responses = build_simulated_responses(benchmark, error_rate=0.20, seed=99)
        a = MockAdapter(responses=responses)
        a.name = f"{agent}-dryrun"
        return a
    if agent == "deepseek":
        from evaluator.adapters.deepseek_adapter import DeepSeekAdapter
        return DeepSeekAdapter()
    if agent == "openai":
        from evaluator.adapters.openai_adapter import OpenAIAdapter
        return OpenAIAdapter()
    raise ValueError(f"未知 agent: {agent}")


def run_sample(
    *,
    version: str,
    n: int,
    agent: str,
    dry_run: bool,
    output_dir: str,
    seed: int = 7,
) -> dict:
    benchmark = load_benchmark(version)
    sample = stratified_sample(benchmark, n=n, seed=seed)

    print(f"[sample_real_eval] 抽样 {len(sample)} / {len(benchmark)} 条 "
          f"(agent={agent}, dry_run={dry_run})")

    adapter = _build_real_adapter(agent, dry_run=dry_run, benchmark=sample)
    records = evaluate(sample, adapter)
    bc = collect_badcases(records, agent_name=agent)
    avg = sum(r["score"]["total"] for r in records) / len(records) if records else 0.0
    print(f"[sample_real_eval] 均分={avg:.2f}, badcase={len(bc)}")

    suffix = "real_sample_dryrun" if dry_run else "real_sample"
    md_path = f"{output_dir}/evaluation_v{version}_{suffix}.md"
    generate_evaluation_report(
        version=f"v{version}-{suffix}",
        results_by_agent={agent: records},
        output_path=md_path,
    )
    print(f"[sample_real_eval] 报告 → {md_path}")

    bc_path = f"{output_dir}/badcases_{suffix}.json"
    save_json(bc, bc_path)
    print(f"[sample_real_eval] badcase → {bc_path}")

    return {
        "version": f"v{version}",
        "agent": agent,
        "dry_run": dry_run,
        "n_sampled": len(sample),
        "mean_score": round(avg, 2),
        "badcase": len(bc),
        "report_path": md_path,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="REAL 模式抽样评测（默认 100 条分层抽样）")
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--version", default="1.0.0")
    p.add_argument("--agent", default="deepseek", choices=["deepseek", "openai"])
    p.add_argument("--dry-run", action="store_true", help="用 MockAdapter 顶替真 API")
    p.add_argument("--output-dir", default=config.REPORTS_DIR)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    stats = run_sample(
        version=args.version,
        n=args.n,
        agent=args.agent,
        dry_run=args.dry_run,
        output_dir=args.output_dir,
        seed=args.seed,
    )
    print("\n=== Sample Eval ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
