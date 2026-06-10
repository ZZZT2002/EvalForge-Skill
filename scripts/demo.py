"""答辩当场演示脚本（MOCK 模式，30 秒内贯通完整闭环）

5 步骤分段打印，每步都给出关键数字：
  1. 加载 v1.0 评测集     → 规模 / Skill 分布 / 难度分布
  2. 双 Agent MOCK 评测   → 各自均分 / badcase 数 / 高分 task 数
  3. 衰退检测             → 衰退 task 数 / 按 Skill 分布 / Top 3
  4. 三策略演进生成 v1.1  → 策略分布 / 演进举例
  5. before/after 对照    → 平均 Δ 均分 / 分策略下降 / 写报告

用法：
  python -m scripts.demo            # 一气呵成（约 20-30 秒）
  python -m scripts.demo --pause    # 每步等回车，方便演讲节奏控制
"""
import argparse
import json
from collections import Counter
from typing import Dict, List

from config import BADCASE_THRESHOLD, DECAY_THRESHOLD, REPORTS_DIR
from evaluator.adapters.base import MockAdapter
from evaluator.pipeline import (
    build_simulated_responses,
    collect_badcases,
    evaluate,
    load_benchmark,
)
from reports.reporter import generate_decay_report, generate_evaluation_report
from updater.constraint_evolver import evolve_benchmark
from updater.decay_detector import detect_decay


SEP = "=" * 72


def _banner(step: int, title: str) -> None:
    print()
    print(SEP)
    print(f"  STEP {step}/5 — {title}")
    print(SEP)


def _pause(enabled: bool) -> None:
    if enabled:
        input("  [回车继续] ")


def _count_field(items: List[dict], key: str) -> Counter:
    c: Counter = Counter()
    for x in items:
        v = x.get(key) or x.get("skill_definition", {}).get(key)
        c[v] += 1
    return c


def run_demo(*, version: str = "1.0.0", pause: bool = False) -> dict:
    # MOCK 错误率压低，确保两 Agent 平均分都能进入 DECAY_THRESHOLD（92）区间
    error_rates = {"deepseek": 0.05, "qwen": 0.15}
    output_dir = REPORTS_DIR

    # ----------------- STEP 1 -----------------
    _banner(1, "加载 v1.0 评测集")
    benchmark = load_benchmark(version)
    by_skill = _count_field(benchmark, "skill_name")
    by_diff = _count_field(benchmark, "difficulty")
    print(f"  路径：data/version_history/benchmark_v{version}.json")
    print(f"  规模：{len(benchmark)} 条用例")
    print(f"  Skill 分布：")
    for sk, n in sorted(by_skill.items()):
        print(f"    - {sk}: {n}")
    print(f"  难度分布：")
    for df in ("normal", "boundary", "adversarial"):
        n = by_diff.get(df, 0)
        pct = n / len(benchmark) * 100 if benchmark else 0
        print(f"    - {df}: {n}  ({pct:.1f}%)")
    _pause(pause)

    # ----------------- STEP 2 -----------------
    _banner(2, "双 Agent MOCK 评测（v1.0）")
    results_by_agent: Dict[str, List[dict]] = {}
    responses_per_agent: Dict[str, Dict[str, str]] = {}
    for agent, err in error_rates.items():
        print(f"  [{agent}] error_rate={err:.0%}, 正在评测 {len(benchmark)} 条用例 ...")
        responses = build_simulated_responses(
            benchmark, error_rate=err, seed=(hash(agent) & 0xFFFF) or 1
        )
        responses_per_agent[agent] = responses
        adapter = MockAdapter(responses=responses)
        adapter.name = agent
        records = evaluate(benchmark, adapter)
        results_by_agent[agent] = records
        avg = sum(r["score"]["total"] for r in records) / len(records)
        bc = collect_badcases(records, agent_name=agent)
        decay_cnt = sum(1 for r in records if r["score"]["total"] >= DECAY_THRESHOLD)
        print(f"  [{agent}] 均分={avg:.2f}, "
              f"badcase(<{BADCASE_THRESHOLD:.0f})={len(bc)}, "
              f"高分(≥{DECAY_THRESHOLD:.0f})={decay_cnt}")
    _pause(pause)

    # ----------------- STEP 3 -----------------
    _banner(3, "衰退检测 (mean ≥ DECAY_THRESHOLD)")
    decay = detect_decay(results_by_agent)
    decay_ids = [d["task_id"] for d in decay]
    print(f"  衰退阈值：≥ {DECAY_THRESHOLD:.0f}  （两 Agent 均分都到这就算被刷爆）")
    pct = len(decay) / len(benchmark) * 100 if benchmark else 0
    print(f"  衰退 task：{len(decay)} / {len(benchmark)}  ({pct:.1f}%)")
    skill_of = {tc["task_id"]: tc.get("skill_name") for tc in benchmark}
    by_skill_decay: Counter = Counter()
    for tid in decay_ids:
        by_skill_decay[skill_of.get(tid, "?")] += 1
    print(f"  按 Skill 分布：")
    for sk, n in by_skill_decay.most_common():
        print(f"    - {sk}: {n}")
    print(f"  Top 3 衰退 task（mean 倒序）：")
    for d in decay[:3]:
        print(f"    - {d['task_id']}  mean={d['mean_score']}  by_agent={d['by_agent']}")
    if not decay:
        print("  [warn] 未检出衰退 task，请降低 error_rate 或调低 DECAY_THRESHOLD")
        return {"benchmark_size": len(benchmark), "decay_count": 0}
    _pause(pause)

    # ----------------- STEP 4 -----------------
    _banner(4, "约束加强演进生成 v1.1（按 Skill 定制审计参数）")
    v11, strat_stats, id_map = evolve_benchmark(benchmark, decay_ids)
    print(f"  策略分布（按 task_id 哈希稳定分配）：")
    for s, n in strat_stats.items():
        print(f"    - {s}: {n}")
    print(f"  v1.1 规模：{len(v11)} 条  (其中已演进 {len(id_map)} 条)")
    sample = next(iter(id_map.items()), None)
    if sample:
        old_id, new_id = sample
        new_case = next(c for c in v11 if c["task_id"] == new_id)
        old_case = next(c for c in benchmark if c["task_id"] == old_id)
        print(f"  演进举例：")
        print(f"    {old_id}  →  {new_id}")
        print(f"    策略 = {new_case['evolution_strategy']}")
        print(f"    expected 工具序列：")
        old_tools = [(t['tool'], t.get('args', {})) for t in old_case['expected_tool_calls']]
        new_tools = [(t['tool'], t.get('args', {})) for t in new_case['expected_tool_calls']]
        print(f"      v1.0 ({len(old_case['expected_tool_calls'])} 步):")
        for i, (tool, args) in enumerate(old_tools, 1):
            print(f"        {i}. {tool}{args}")
        print(f"      v1.1 ({len(new_case['expected_tool_calls'])} 步):")
        for i, (tool, args) in enumerate(new_tools, 1):
            marker = " ← 新增审计" if i == len(new_tools) else ""
            print(f"        {i}. {tool}{args}{marker}")
    _pause(pause)

    # ----------------- STEP 5 -----------------
    _banner(5, "before/after 对照 + 生成报告")
    v11_decay_subset = [c for c in v11 if c["task_id"] in set(id_map.values())]
    inverse_id_map = {new: old for old, new in id_map.items()}
    results_v11: Dict[str, List[dict]] = {}
    print(f"  复用 v1.0 同份 mock 响应跑 v1.1 衰退子集 ({len(v11_decay_subset)} 条)...")
    for agent, old_responses in responses_per_agent.items():
        new_responses = {
            new_id: old_responses[inverse_id_map[new_id]]
            for new_id in inverse_id_map
        }
        adapter = MockAdapter(responses=new_responses)
        adapter.name = agent
        results_v11[agent] = evaluate(v11_decay_subset, adapter)

    v10_score = {(a, r["task_id"]): r["score"]["total"]
                 for a, recs in results_by_agent.items() for r in recs}
    v11_score = {(a, r["task_id"]): r["score"]["total"]
                 for a, recs in results_v11.items() for r in recs}
    strategy_by_new_id = {c["task_id"]: c["evolution_strategy"] for c in v11_decay_subset}

    before_after: List[dict] = []
    for old_id, new_id in id_map.items():
        by_old = {a: v10_score[(a, old_id)] for a in results_by_agent}
        by_new = {a: v11_score[(a, new_id)] for a in results_v11}
        m_old = sum(by_old.values()) / len(by_old)
        m_new = sum(by_new.values()) / len(by_new)
        before_after.append({
            "task_id_old": old_id,
            "task_id_new": new_id,
            "strategy": strategy_by_new_id[new_id],
            "by_agent_old": by_old,
            "by_agent_new": by_new,
            "delta_mean": round(m_new - m_old, 2),
        })

    avg_delta = sum(r["delta_mean"] for r in before_after) / len(before_after)
    print(f"  对照样本数：{len(before_after)}")
    print(f"  平均 Δ均分：{avg_delta:+.2f}  ← 负值=v1.1 真的更难，不是变得不同")

    by_strat: Dict[str, List[float]] = {}
    for r in before_after:
        by_strat.setdefault(r["strategy"], []).append(r["delta_mean"])
    print(f"  分策略下降：")
    for s, xs in by_strat.items():
        print(f"    - {s}: 平均 {sum(xs)/len(xs):+.2f}  (n={len(xs)})")

    eval_path = f"{output_dir}/evaluation_demo.md"
    report_path = f"{output_dir}/decay_report_demo.md"
    generate_evaluation_report(
        version=f"v{version}-demo",
        results_by_agent=results_by_agent,
        output_path=eval_path,
    )
    generate_decay_report(
        version_old=f"v{version}",
        version_new="v1.1.0-demo",
        decay_tasks=decay,
        strategy_stats=strat_stats,
        before_after=before_after,
        output_path=report_path,
    )
    print(f"  评测报告 → {eval_path}")
    print(f"  演进报告 → {report_path}")

    # ----------------- 总结 -----------------
    print()
    print(SEP)
    print("  DEMO 完成 — 评测集自更新闭环已贯通")
    print(SEP)
    print(f"  v1.0 ({len(benchmark)} 条) → 检出 {len(decay)} 条衰退 "
          f"→ 演进生成 v1.1（{len(v11_decay_subset)} 条升级）")
    print(f"  before/after 平均下降 {avg_delta:+.2f} 分，三策略均生效")
    print()

    return {
        "benchmark_size": len(benchmark),
        "decay_count": len(decay),
        "strategy_stats": strat_stats,
        "avg_delta": round(avg_delta, 2),
        "evaluation_report": eval_path,
        "decay_report": report_path,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="答辩当场演示：MOCK 模式完整闭环（v1.0 → 衰退 → v1.1 → before/after）"
    )
    p.add_argument("--version", default="1.0.0")
    p.add_argument("--pause", action="store_true", help="每步等回车，演讲节奏可控")
    args = p.parse_args()
    stats = run_demo(version=args.version, pause=args.pause)
    print("=== Summary ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
