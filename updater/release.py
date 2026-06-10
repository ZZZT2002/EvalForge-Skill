"""D9 演进发布主驱动（PROJECT.md §9）
自动发现 v1.0 中的"简单题"（所有模型都会做的），给它们注入诱导话术升级成 v1.1 对抗题，并验证升级效果。
流程：
  1. 加载 v1.0 benchmark
  2. MOCK 评测 v1.0 → results_by_agent
  3. detect_decay 找 mean ≥ DECAY_THRESHOLD 的 task
  4. evolve_benchmark 对衰退 task 应用三策略，生成 v1.1.0
  5. 写 data/version_history/benchmark_v1.1.0.json
  6. before/after 对照实验：复用 v1.0 同份 mock 响应跑 v1.1 衰退子集
  7. 写 data/reports/decay_report_v1.1.0.md
  8. 更新 CHANGELOG

[1/5] 加载 v1.0 + 评测
   ↓ 找出所有模型都高分的题
[2/5] 衰退检测
   ↓ 得到需要升级的题目列表
[3/5] 演进生成 v1.1
   ↓ 注入诱导话术，生成新 benchmark
[4/5] before/after 对照实验
   ↓ 用同一份模型回答对比分数变化
[5/5] 生成报告 + 更新 CHANGELOG

CLI： python -m updater.release
"""
import json
from datetime import date
from pathlib import Path
from typing import Dict, List

from config import REPORTS_DIR, VERSION_HISTORY_DIR
from evaluator.adapters.base import MockAdapter
from evaluator.pipeline import (
    build_simulated_responses,
    evaluate,
    load_benchmark,
    run as run_d8_evaluation,
    save_json,
)
from release import write_changelog_entry
from reports.reporter import generate_decay_report
from updater.constraint_evolver import evolve_benchmark
from updater.decay_detector import detect_decay


def run(
    version_old: str = "1.0.0",
    version_new: str = "1.1.0",
    error_rates: Dict[str, float] = None,
) -> dict:
    error_rates = error_rates or {"deepseek": 0.10, "qwen": 0.25}

    # ---------- 1+2. v1.0 评测（复用 D8 pipeline，顺便落 evaluation_v1.0.0.md） ----------
    print(f"[1/5] 加载 v{version_old} benchmark + D8 评测")
    v10 = load_benchmark(version_old)
    print(f"      {len(v10)} 条用例")
    d8_stats = run_d8_evaluation(version=version_old, error_rates=error_rates)
    results_v10: Dict[str, List[dict]] = d8_stats["results_by_agent"]
    # 重建 responses_per_agent（同种子，用于 v1.1 复用同份模拟回答）
    responses_per_agent = {
        a: build_simulated_responses(
            v10, error_rate=err, seed=(hash(a) & 0xFFFF) or 1
        )
        for a, err in error_rates.items()
    }

    # ---------- 3. 衰退检测 ----------
    print("[2/5] 衰退检测")
    decay = detect_decay(results_v10)
    decay_ids = [d["task_id"] for d in decay]
    print(f"      衰退 task: {len(decay)}")

    if not decay:
        raise SystemExit("未检测到衰退 task，请降低 DECAY_THRESHOLD 或调整 mock error_rate")

    # ---------- 3. 演进生成 v1.1 ----------
    print("[3/5] 演进生成 v1.1")
    v11, strat_stats, id_map = evolve_benchmark(v10, decay_ids)
    print(f"      策略分布: {strat_stats}")

    out_path = f"{VERSION_HISTORY_DIR}/benchmark_v{version_new}.json"
    save_json(v11, out_path)
    print(f"      → {out_path}")

    # ---------- 4. v1.1 衰退子集 before/after 对照 ----------
    print("[4/5] before/after 对照实验")
    v11_decay_subset = [c for c in v11 if c["task_id"] in set(id_map.values())]
    inverse_id_map = {new: old for old, new in id_map.items()}

    results_v11: Dict[str, List[dict]] = {}
    for agent, old_responses in responses_per_agent.items():
        # 复用 v1.0 同一份 mock 响应：演进后的 task_id 沿用原 task_id 的 raw
        new_responses = {
            new_id: old_responses[inverse_id_map[new_id]]
            for new_id in inverse_id_map
        }
        adapter = MockAdapter(responses=new_responses)
        adapter.name = agent
        results_v11[agent] = evaluate(v11_decay_subset, adapter)

    # 配对 before/after
    v10_score = {
        (a, r["task_id"]): r["score"]["total"]
        for a, recs in results_v10.items()
        for r in recs
    }
    v11_score = {
        (a, r["task_id"]): r["score"]["total"]
        for a, recs in results_v11.items()
        for r in recs
    }
    strategy_by_new_id = {c["task_id"]: c["evolution_strategy"] for c in v11_decay_subset}

    before_after: List[dict] = []
    for old_id, new_id in id_map.items():
        by_agent_old = {a: v10_score[(a, old_id)] for a in results_v10}
        by_agent_new = {a: v11_score[(a, new_id)] for a in results_v11}
        mean_old = sum(by_agent_old.values()) / len(by_agent_old)
        mean_new = sum(by_agent_new.values()) / len(by_agent_new)
        before_after.append(
            {
                "task_id_old": old_id,
                "task_id_new": new_id,
                "strategy": strategy_by_new_id[new_id],
                "by_agent_old": by_agent_old,
                "by_agent_new": by_agent_new,
                "delta_mean": round(mean_new - mean_old, 2),
            }
        )

    avg_delta = sum(r["delta_mean"] for r in before_after) / len(before_after)
    print(f"      平均 Δ均分: {avg_delta:+.2f}")

    # ---------- 5. 报告 + CHANGELOG ----------
    print("[5/5] 报告 + CHANGELOG")
    report_path = f"{REPORTS_DIR}/decay_report_v{version_new}.md"
    generate_decay_report(
        version_old=f"v{version_old}",
        version_new=f"v{version_new}",
        decay_tasks=decay,
        strategy_stats=strat_stats,
        before_after=before_after,
        output_path=report_path,
    )
    print(f"      报告 → {report_path}")

    # 衰退 task 全集落盘（D11 答辩展示用）
    save_json(decay, f"data/decay_tasks_v{version_old}.json")

    summary_lines = [
        f"基于 v{version_old} 评测结果检出 {len(decay)} 条衰退 task（mean ≥ DECAY_THRESHOLD）",
        f"应用演进策略：" + ", ".join(f"{k}={v}" for k, v in strat_stats.items()),
        f"benchmark 规模：{len(v10)} → {len(v11)} 条",
        f"before/after 对照：衰退 task 平均 Δ均分 = {avg_delta:+.2f}",
        f"完整对照见 `{report_path}`",
    ]
    write_changelog_entry(
        "CHANGELOG.md", f"v{version_new}", date.today().isoformat(), summary_lines
    )
    print("      → CHANGELOG.md 已更新")

    return {
        "version_new": f"v{version_new}",
        "decay_count": len(decay),
        "strategy_stats": strat_stats,
        "avg_delta_mean": round(avg_delta, 2),
        "report_path": report_path,
    }


def main() -> int:
    stats = run()
    print("\n=== D9 Release ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
