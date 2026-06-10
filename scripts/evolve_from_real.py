"""从 REAL v1.0 评测结果中检测衰退并生成 v1.1。

用法：
  python -m scripts.evolve_from_real                          # 默认：deepseek + doubao
  python -m scripts.evolve_from_real --agent deepseek         # 单 Agent 演进
  python -m scripts.evolve_from_real --agent doubao --tag doubao  # 独立输出，不覆写默认 v1.1

[0/6] 检查 API Key
   ↓
[1/6] 加载 v1.0 benchmark（1247 条）
   ↓
[2/6] REAL 评测 v1.0（真调用 DeepSeek + Doubao）
   ↓
[3/6] 衰退检测（找出两模型均分≥92 的题）
   ↓
[4/6] 演进生成 v1.1（注入诱导话术）
   ↓
[5/6] before/after 对照（对升级后的 prompt 真实重测）
   ↓
[6/6] 生成报告

流程：
  1. 加载 v1.0 benchmark
  2. 用指定 Agent REAL API 全量评测 v1.0
  3. 保存完整评测记录（records）供后续溯源
  4. 生成 v1.0 评测报告
  5. 从 Agent 均分中检测衰退（mean ≥ 92）
  6. 对衰退 task 执行 adversarial_escalation 演进
  7. 保存 v1.1 benchmark
  8. 生成衰退报告
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

from config import BADCASE_THRESHOLD, DECAY_THRESHOLD, REPORTS_DIR, VERSION_HISTORY_DIR
from evaluator.adapters.deepseek_adapter import DeepSeekAdapter
from evaluator.adapters.doubao_adapter import DoubaoAdapter
from evaluator.adapters.qwen_adapter import QwenAdapter
from evaluator.pipeline import collect_badcases, evaluate, load_benchmark, save_json
from reports.reporter import generate_decay_report, generate_evaluation_report
from updater.constraint_evolver import evolve_benchmark
from updater.decay_detector import detect_decay


SEP = "=" * 72

# 参评模型可配置：环境变量 EVAL_AGENTS（逗号分隔），默认 deepseek,doubao。
# 豆包端点不可用时，可改为 EVAL_AGENTS=deepseek,qwen。
_ADAPTER_FACTORY = {
    "deepseek": DeepSeekAdapter,
    "doubao": DoubaoAdapter,
    "qwen": QwenAdapter,
}

def _resolve_agents(cli_agent: str = None) -> Dict:
    """解析参评 Agent 列表。CLI --agent 优先，否则读 EVAL_AGENTS 环境变量。"""
    names = (
        [cli_agent]
        if cli_agent
        else [a.strip() for a in os.getenv("EVAL_AGENTS", "deepseek,doubao").split(",") if a.strip()]
    )
    return {name: _ADAPTER_FACTORY[name]() for name in names}

_DEFAULT_AGENTS = {name: _ADAPTER_FACTORY[name]() for name in
                   [a.strip() for a in os.getenv("EVAL_AGENTS", "deepseek,doubao").split(",") if a.strip()]}


def _check_api_keys(agents: Dict) -> bool:
    ok = True
    for agent_name, adapter in agents.items():
        try:
            adapter._ensure_client()
            print(f"  [{agent_name}] API Key [OK]")
        except Exception as e:
            print(f"  [{agent_name}] API Key [FAIL] - {e}")
            ok = False
    return ok


def _skill_of(benchmark: List[dict]) -> Dict[str, str]:
    return {tc["task_id"]: tc.get("skill_name", "?") for tc in benchmark}


def main() -> int:
    p = argparse.ArgumentParser(description="REAL v1.0 → 衰退检测 → v1.1 演进")
    p.add_argument("--agent", default=None,
                   help="仅评测指定 Agent（deepseek/doubao/qwen），不传则读 EVAL_AGENTS 环境变量（默认 deepseek,doubao）")
    p.add_argument("--tag", default=None,
                   help="产物文件名后缀，如 --tag doubao → benchmark_v1.1.0_doubao.json。不传则无后缀（会覆写默认文件）")
    args = p.parse_args()

    agents = _resolve_agents(args.agent)

    # 若未指定 tag，自动根据 agent 生成：单 agent 时用 agent 名作为 tag，多 agent 时无 tag
    tag = args.tag
    if tag is None and args.agent is not None:
        tag = args.agent  # 单 agent 时自动用 agent 名，保护默认文件不被覆盖

    _suffix = f"_{tag}" if tag else ""

    print(SEP)
    print(f"  EvalForge-Skill: REAL v1.0 → 衰退检测 → v1.1 演进")
    print(f"  Agent: {', '.join(agents.keys())} | tag: {tag or '(无)'}")
    print(f"  启动时间：{datetime.now().isoformat(timespec='seconds')}")
    print(SEP)

    # ── 0. 检查 API Key ──
    print("\n[0/6] 检查 API Key …")
    if not _check_api_keys(agents):
        print("\n[错误] 缺少 API Key，请在 .env 中设置后重试。")
        return 1

    # ── 1. 加载 v1.0 ──
    print(f"\n[1/6] 加载 v1.0 benchmark …")
    v10 = load_benchmark("1.0.0")
    print(f"  规模：{len(v10)} 条")
    print(f"  Skill 分布：{dict(Counter(_skill_of(v10).values()))}")

    # ── 2. REAL 评测 v1.0 ──
    print(f"\n[2/6] REAL 评测 v1.0（{len(v10)} 条 × {len(agents)} Agent）…")
    results: Dict[str, List[dict]] = {}
    all_badcases: List[dict] = []

    for agent_name, adapter in agents.items():
        print(f"  [{agent_name}] 评测中 …")
        records = evaluate(v10, adapter)
        results[agent_name] = records

        avg = sum(r["score"]["total"] for r in records) / len(records) if records else 0
        bc = collect_badcases(records, agent_name=agent_name)
        all_badcases.extend(bc)

        decay_cnt = sum(1 for r in records if r["score"]["total"] >= DECAY_THRESHOLD)
        print(f"  [{agent_name}] 均分={avg:.2f}  badcase(<{BADCASE_THRESHOLD})={len(bc)}  "
              f"高分(≥{DECAY_THRESHOLD})={decay_cnt}")

    # 保存完整 records + badcase（带 tag 后缀，多 Agent 场景不覆写默认文件）
    records_path = f"{REPORTS_DIR}/records_v1.0.0{_suffix}_real.json"
    records_serializable = {
        agent: [
            {**r, "expected": r["expected"], "predicted": r["predicted"]}
            for r in recs
        ]
        for agent, recs in results.items()
    }
    save_json(records_serializable, records_path)
    print(f"  完整评测记录 → {records_path}")

    bc_path = f"{REPORTS_DIR}/badcases_v1.0.0{_suffix}_real.json"
    save_json(all_badcases, bc_path)
    print(f"  badcase → {bc_path}")

    # v1.0 评测报告（合并版 + 各 Agent 单独版）
    v10_combined = f"{REPORTS_DIR}/evaluation_v1.0.0_real_full{_suffix}.md"
    generate_evaluation_report(
        version="v1.0.0-real",
        results_by_agent=results,
        output_path=v10_combined,
    )
    print(f"  v1.0 合并报告 → {v10_combined}")

    for agent_name, recs in results.items():
        agent_report = f"{REPORTS_DIR}/evaluation_v1.0.0_{agent_name}_real_full.md"
        generate_evaluation_report(
            version=f"v1.0.0-{agent_name}-real",
            results_by_agent={agent_name: recs},
            output_path=agent_report,
        )
        print(f"  v1.0 [{agent_name}] 单独报告 → {agent_report}")

    # ── 3. 衰退检测 ──
    print(f"\n[3/6] 衰退检测（两 Agent 均分 ≥ {DECAY_THRESHOLD}）…")
    decay = detect_decay(results)
    decay_ids = [d["task_id"] for d in decay]
    pct = len(decay) / len(v10) * 100
    print(f"  衰退 task：{len(decay)} / {len(v10)} ({pct:.1f}%)")

    if not decay:
        print("  [结果] 未检出衰退 task。v1.1 无需生成，流程结束。")
        return 0

    skill_of = _skill_of(v10)
    by_skill = Counter(skill_of.get(tid, "?") for tid in decay_ids)
    print(f"  按 Skill：{dict(by_skill)}")

    # ── 4. 演进生成 v1.1 ──
    print(f"\n[4/6] 演进生成 v1.1（adversarial_escalation）…")
    v11, strat_stats, id_map = evolve_benchmark(v10, decay_ids)
    print(f"  v1.1 规模：{len(v11)} 条（其中已演进 {len(id_map)} 条）")
    print(f"  策略分布：{strat_stats}")

    v11_path = f"{VERSION_HISTORY_DIR}/benchmark_v1.1.0{_suffix}.json"
    save_json(v11, v11_path)
    print(f"  v1.1 benchmark → {v11_path}")

    # ── 5. before/after 对照（真实重测演进后的对抗 prompt）──
    print(f"\n[5/6] before/after 对照（对操纵后的 prompt 真实重测）…")
    v10_score = {
        (agent, r["task_id"]): r["score"]["total"]
        for agent, recs in results.items()
        for r in recs
    }

    from evaluator.normalizer import normalize_response
    from evaluator.scorer import score_breakdown
    from skills_ontology import SKILLS
    from tools_schema import TOOLS_SCHEMA

    before_after: List[dict] = []
    for v10_case in v10:
        tid = v10_case["task_id"]
        if tid not in decay_ids:
            continue
        new_id = id_map[tid]
        new_case = next(c for c in v11 if c["task_id"] == new_id)
        skill_name = new_case.get("skill_name")
        skill_def = SKILLS.get(skill_name) if skill_name else None

        by_old = {a: v10_score.get((a, tid), 0) for a in agents}
        m_old = sum(by_old.values()) / len(by_old) if by_old else 0

        # expected 不变，但 prompt 被注入了操纵话术 → 真实调用各模型重测，
        # 看它会不会被骗着跳过合规步骤（这才是诚实的 v1.1 掉分证据）。
        by_new: Dict[str, float] = {}
        for agent, adapter in agents.items():
            raw = adapter.call(
                prompt=new_case["prompt"],
                tools_schema=TOOLS_SCHEMA,
                task_id=new_id,
                skill_definition=skill_def,
            )
            predicted = normalize_response(raw)
            by_new[agent] = score_breakdown(predicted, new_case["expected_tool_calls"])["total"]
        m_new = sum(by_new.values()) / len(by_new) if by_new else 0

        before_after.append({
            "task_id_old": tid,
            "task_id_new": new_id,
            "strategy": new_case.get("evolution_strategy", "?"),
            "by_agent_old": by_old,
            "by_agent_new": by_new,
            "delta_mean": round(m_new - m_old, 2),
        })

    avg_delta = sum(r["delta_mean"] for r in before_after) / len(before_after) if before_after else 0
    print(f"  对照样本数：{len(before_after)}")
    print(f"  平均 Δ均分：{avg_delta:+.2f}（负值=操纵话术成功拉低得分，符合预期）")

    # ── 6. 生成报告 ──
    print(f"\n[6/6] 生成报告 …")
    decay_report_path = f"{REPORTS_DIR}/decay_report_v1.1.0{_suffix}_real.md"
    generate_decay_report(
        version_old="v1.0.0",
        version_new="v1.1.0-real",
        decay_tasks=decay,
        strategy_stats=strat_stats,
        before_after=before_after,
        output_path=decay_report_path,
    )
    print(f"  衰退演进报告 → {decay_report_path}")

    # ── 总结 ──
    print(f"\n{SEP}")
    print(f"  完成！")
    print(f"  v1.0 ({len(v10)} 条) → 检出 {len(decay)} 条衰退 → v1.1 ({len(v11)} 条)")
    print(f"  before/after 平均 Δ均分：{avg_delta:+.2f}")
    print(f"")
    print(f"  下一步 — 评测 v1.1：")
    if tag:
        print(f"    python -m scripts.sample_real_eval --n 591 --version 1.1.0_{tag} --agent {tag}")
    else:
        print(f"    python -m scripts.sample_real_eval --n 591 --version 1.1.0 --agent deepseek")
        print(f"    python -m scripts.sample_real_eval --n 591 --version 1.1.0 --agent doubao")
    print(f"")
    print(f"  产物清单：")
    print(f"    v1.0 评测记录：{records_path}")
    print(f"    v1.0 badcase：  {bc_path}")
    print(f"    v1.0 合并报告：{v10_combined}")
    for agent_name in agents:
        print(f"    v1.0 [{agent_name}] 报告：{REPORTS_DIR}/evaluation_v1.0.0_{agent_name}_real_full.md")
    print(f"    v1.1 benchmark：{v11_path}")
    print(f"    衰退演进报告：{decay_report_path}")
    print(SEP)

    return 0


if __name__ == "__main__":
    sys.exit(main())
