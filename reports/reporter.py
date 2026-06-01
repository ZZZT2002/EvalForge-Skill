"""通用 Markdown 报告生成器

D5：generate_quality_report —— v0.9 → v0.95 的质检结果总结
D8、D9 会在后续添加 evaluation / decay 报告生成函数
"""
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def _fmt_pct(x: float) -> str:
    return f"{x*100:.1f}%"


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _bar(value: float, total: float, width: int = 20) -> str:
    if total <= 0:
        return ""
    filled = int(round(value / total * width))
    return "█" * filled + "░" * (width - filled)


def generate_quality_report(
    *,
    version: str,
    candidates_v09: List[dict],
    schema_result: Dict,
    judge_scores: List[Dict],
    keep_ids: List[str],
    output_path: str,
    cutoff_threshold: int = 3,
) -> str:
    """汇总 schema 校验 + LLM Judge 打分，写出 markdown 报告。

    返回 markdown 字符串（同时写入文件）。
    """
    total = len(candidates_v09)
    kept = len(keep_ids)
    keep_set = set(keep_ids)

    # ----- schema -----
    schema_pass = schema_result["passed"]
    schema_fail = schema_result["failed"]
    schema_pass_rate = schema_result["pass_rate"]
    schema_fail_reasons = schema_result["fail_reasons"]

    # ----- judge 分布 -----
    by_id_score = {s["task_id"]: s for s in judge_scores}
    dims = ("decidability", "difficulty_fit", "fluency")
    dim_values = {d: [s[d] for s in judge_scores] for d in dims}
    dim_mean = {d: _mean(dim_values[d]) for d in dims}

    # 单维度 <cutoff 的数量
    below_per_dim = {
        d: sum(1 for v in dim_values[d] if v < cutoff_threshold) for d in dims
    }

    # 分数直方
    histograms = {
        d: Counter(dim_values[d]) for d in dims
    }

    # ----- 按 Skill / Difficulty 的保留率 -----
    by_skill_total: Counter = Counter()
    by_skill_kept: Counter = Counter()
    by_diff_total: Counter = Counter()
    by_diff_kept: Counter = Counter()
    for c in candidates_v09:
        sk = c["skill_name"]
        df = c["difficulty"]
        by_skill_total[sk] += 1
        by_diff_total[df] += 1
        if c["task_id"] in keep_set:
            by_skill_kept[sk] += 1
            by_diff_kept[df] += 1

    # ----- 淘汰原因聚合 -----
    drop_reasons: Counter = Counter()
    for c in candidates_v09:
        tid = c["task_id"]
        if tid in keep_set:
            continue
        # 先看 schema
        schema_entry = next(
            (r for r in schema_result["results"] if r["task_id"] == tid), None
        )
        if schema_entry and not schema_entry["ok"]:
            drop_reasons[f"schema:{schema_entry['reason'].split(':')[0]}"] += 1
            continue
        # 再看 judge 哪一维 < cutoff
        s = by_id_score.get(tid)
        if s is None:
            drop_reasons["no_judge_score"] += 1
            continue
        low_dims = [d for d in dims if s[d] < cutoff_threshold]
        if low_dims:
            drop_reasons[f"judge_low:{'+'.join(low_dims)}"] += 1
        else:
            drop_reasons["unknown"] += 1

    # ----- 渲染 -----
    lines: List[str] = []
    lines.append(f"# 质量评估报告 — {version}")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 输入：v0.9 候选 {total} 条")
    lines.append(f"- 输出：v0.95 保留 {kept} 条（保留率 {_fmt_pct(kept/total) if total else 'N/A'}）")
    lines.append(f"- 单维度淘汰阈值：< {cutoff_threshold} 分")
    lines.append("")

    lines.append("## 1. JSON Schema 强校验")
    lines.append("")
    lines.append(f"- 通过：{schema_pass} / {total}（{_fmt_pct(schema_pass_rate)}）")
    lines.append(f"- 失败：{schema_fail}")
    if schema_fail_reasons:
        lines.append("")
        lines.append("失败原因分布：")
        lines.append("")
        lines.append("| 原因 | 数量 |")
        lines.append("|---|---|")
        for reason, cnt in sorted(schema_fail_reasons.items(), key=lambda x: -x[1]):
            lines.append(f"| `{reason}` | {cnt} |")
    lines.append("")

    lines.append("## 2. LLM-as-Judge 三维打分")
    lines.append("")
    lines.append("| 维度 | 均分 | <3 分数量 |")
    lines.append("|---|---|---|")
    name_cn = {"decidability": "可判定性", "difficulty_fit": "难度合理性", "fluency": "流畅度"}
    for d in dims:
        lines.append(f"| {name_cn[d]} ({d}) | {dim_mean[d]:.2f} | {below_per_dim[d]} |")
    lines.append("")

    for d in dims:
        lines.append(f"### {name_cn[d]} 分布")
        lines.append("")
        lines.append("| 分数 | 数量 | 占比 | 直方 |")
        lines.append("|---|---|---|---|")
        n_total = len(dim_values[d])
        for score in (1, 2, 3, 4, 5):
            cnt = histograms[d].get(score, 0)
            pct = cnt / n_total if n_total else 0
            lines.append(f"| {score} | {cnt} | {_fmt_pct(pct)} | `{_bar(cnt, n_total)}` |")
        lines.append("")

    lines.append("## 3. 按 Skill 的保留率")
    lines.append("")
    lines.append("| Skill | v0.9 | v0.95 | 保留率 |")
    lines.append("|---|---|---|---|")
    for sk in sorted(by_skill_total):
        t = by_skill_total[sk]
        k = by_skill_kept[sk]
        lines.append(f"| {sk} | {t} | {k} | {_fmt_pct(k/t) if t else 'N/A'} |")
    lines.append("")

    lines.append("## 4. 按 Difficulty 的保留率")
    lines.append("")
    lines.append("| Difficulty | v0.9 | v0.95 | 保留率 |")
    lines.append("|---|---|---|---|")
    for df in ("normal", "boundary", "adversarial"):
        t = by_diff_total.get(df, 0)
        k = by_diff_kept.get(df, 0)
        lines.append(f"| {df} | {t} | {k} | {_fmt_pct(k/t) if t else 'N/A'} |")
    lines.append("")

    lines.append("## 5. 淘汰原因 Top")
    lines.append("")
    lines.append("| 原因 | 数量 |")
    lines.append("|---|---|")
    for reason, cnt in drop_reasons.most_common():
        lines.append(f"| `{reason}` | {cnt} |")
    lines.append("")

    md = "\n".join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md


# ----------------------------------------------------------------------
# D8: Agent 评测报告
# ----------------------------------------------------------------------
def generate_evaluation_report(
    *,
    version: str,
    results_by_agent: Dict[str, List[Dict]],
    output_path: str,
) -> str:
    """汇总多 Agent 在某 benchmark 上的评测结果。"""
    from config import BADCASE_THRESHOLD, DECAY_THRESHOLD

    lines: List[str] = []
    lines.append(f"# Agent 评测报告 — {version}")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 参评 Agent：{', '.join(results_by_agent.keys())}")
    any_records = next(iter(results_by_agent.values()), [])
    lines.append(f"- 用例总数：{len(any_records)}")
    lines.append(
        f"- badcase 阈值：< {BADCASE_THRESHOLD} | 衰退阈值：≥ {DECAY_THRESHOLD}"
    )
    lines.append("")

    lines.append("## 1. 总体得分")
    lines.append("")
    lines.append("| Agent | 总均分 | tool_recall | tool_order | argument_acc | badcase | 衰退 task |")
    lines.append("|---|---|---|---|---|---|---|")
    for agent, records in results_by_agent.items():
        total = _mean([r["score"]["total"] for r in records])
        recall = _mean([r["score"]["tool_recall"] for r in records])
        order = _mean([r["score"]["tool_order"] for r in records])
        arg = _mean([r["score"]["argument_accuracy"] for r in records])
        bc = sum(1 for r in records if r["score"]["total"] < BADCASE_THRESHOLD)
        decay = sum(1 for r in records if r["score"]["total"] >= DECAY_THRESHOLD)
        lines.append(
            f"| {agent} | {total:.2f} | {recall:.2f} | {order:.2f} | {arg:.2f} | {bc} | {decay} |"
        )
    lines.append("")

    lines.append("## 2. 按 Skill 分组均分")
    lines.append("")
    skills = sorted({r["skill_name"] for recs in results_by_agent.values() for r in recs})
    lines.append("| Skill | " + " | ".join(results_by_agent.keys()) + " |")
    lines.append("|---|" + "---|" * len(results_by_agent))
    for sk in skills:
        row = [sk]
        for agent, records in results_by_agent.items():
            xs = [r["score"]["total"] for r in records if r["skill_name"] == sk]
            row.append(f"{_mean(xs):.2f} (n={len(xs)})")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## 3. 按 Difficulty 分组均分")
    lines.append("")
    lines.append("| Difficulty | " + " | ".join(results_by_agent.keys()) + " |")
    lines.append("|---|" + "---|" * len(results_by_agent))
    for df in ("normal", "boundary", "adversarial"):
        row = [df]
        for agent, records in results_by_agent.items():
            xs = [r["score"]["total"] for r in records if r["difficulty"] == df]
            row.append(f"{_mean(xs):.2f} (n={len(xs)})")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## 4. Top 10 badcase 预览")
    lines.append("")
    lines.append("| Agent | task_id | skill | difficulty | total | recall | order | arg |")
    lines.append("|---|---|---|---|---|---|---|---|")
    flat: List[tuple] = []
    for agent, records in results_by_agent.items():
        for r in records:
            if r["score"]["total"] < BADCASE_THRESHOLD:
                flat.append((agent, r))
    flat.sort(key=lambda x: x[1]["score"]["total"])
    for agent, r in flat[:10]:
        s = r["score"]
        lines.append(
            f"| {agent} | `{r['task_id']}` | {r['skill_name']} | {r['difficulty']} | "
            f"{s['total']} | {s['tool_recall']} | {s['tool_order']} | {s['argument_accuracy']} |"
        )
    lines.append("")

    md = "\n".join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md


# ----------------------------------------------------------------------
# D9: 衰退检测 + 演进 before/after 报告
# ----------------------------------------------------------------------
def generate_decay_report(
    *,
    version_old: str,
    version_new: str,
    decay_tasks: List[Dict],
    strategy_stats: Dict[str, int],
    before_after: List[Dict],
    output_path: str,
) -> str:
    """生成 v_old → v_new 演进对照报告。

    before_after 每条形如：
      {task_id_old, task_id_new, strategy, by_agent_old, by_agent_new, delta_mean}
    """
    lines: List[str] = []
    lines.append(f"# 衰退检测与演进报告 — {version_old} → {version_new}")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 衰退 task 数：{len(decay_tasks)}")
    lines.append("")

    lines.append("## 1. 演进策略分布")
    lines.append("")
    lines.append("| 策略 | 数量 |")
    lines.append("|---|---|")
    for s, n in strategy_stats.items():
        lines.append(f"| `{s}` | {n} |")
    lines.append("")

    if before_after:
        lines.append("## 2. before / after 均分对照")
        lines.append("")
        agents = sorted({a for r in before_after for a in r["by_agent_old"].keys()})
        header = ["task_id", "strategy"] + [f"{a}↓" for a in agents] + ["Δ均分"]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * len(header))
        for r in before_after:
            row = [f"`{r['task_id_old']}`", r["strategy"]]
            for a in agents:
                old = r["by_agent_old"].get(a, 0)
                new = r["by_agent_new"].get(a, 0)
                row.append(f"{old:.0f}→{new:.0f}")
            row.append(f"{r['delta_mean']:+.2f}")
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

        # 总览
        deltas = [r["delta_mean"] for r in before_after]
        lines.append("## 3. 总览")
        lines.append("")
        lines.append(f"- 衰退 task 在 {version_old} 上的平均分：{_mean([sum(r['by_agent_old'].values())/len(r['by_agent_old']) for r in before_after]):.2f}")
        lines.append(f"- 衰退 task 在 {version_new} 上的平均分：{_mean([sum(r['by_agent_new'].values())/len(r['by_agent_new']) for r in before_after]):.2f}")
        lines.append(f"- 平均下降幅度：{_mean(deltas):+.2f}")
        lines.append("")

        # 按策略汇总下降幅度
        lines.append("## 4. 按策略平均下降")
        lines.append("")
        lines.append("| 策略 | 样本数 | 平均 Δ均分 |")
        lines.append("|---|---|---|")
        by_strat: Dict[str, List[float]] = {}
        for r in before_after:
            by_strat.setdefault(r["strategy"], []).append(r["delta_mean"])
        for s, xs in by_strat.items():
            lines.append(f"| `{s}` | {len(xs)} | {_mean(xs):+.2f} |")
        lines.append("")

    md = "\n".join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md
