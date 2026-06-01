"""人工抽检 CLI（PROJECT.md §7.1）

D6 任务：从 v0.95 中按 difficulty 分层抽样 20%（~118 条），
逐条用 CLI 展示，键盘做决策，写 data/human_review_log.json。

快捷键：
    y  accept  通过，保留
    n  reject  淘汰，明显有问题
    m  modify  需要小修（写一条 note）
    s  skip    跳过本条（保留但不留意见）
    q  quit    保存进度后退出（下次从未审过的继续）

支持中断恢复：脚本启动时自动加载已有 log，过滤掉已审过的。

CLI：
    python -m validator.human_console
    python -m validator.human_console --sample-rate 0.2 --src data/candidates_v0.95.json
"""
import argparse
import json
import os
import random
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


DEFAULT_SRC = "data/candidates_v0.95.json"
DEFAULT_LOG = "data/human_review_log.json"
DEFAULT_RATE = 0.20
DEFAULT_SEED = 42


# ---------- 抽样 ----------

def stratified_sample(
    candidates: List[dict],
    rate: float = DEFAULT_RATE,
    seed: int = DEFAULT_SEED,
) -> List[dict]:
    """按 difficulty 分层抽样，每层独立随机。"""
    rng = random.Random(seed)
    buckets: Dict[str, List[dict]] = defaultdict(list)
    for c in candidates:
        buckets[c["difficulty"]].append(c)

    sampled: List[dict] = []
    for diff, group in buckets.items():
        n = max(1, round(len(group) * rate))
        n = min(n, len(group))
        sampled.extend(rng.sample(group, n))

    # 稳定输出顺序：按 task_id 排序
    sampled.sort(key=lambda c: c["task_id"])
    return sampled


# ---------- 日志 ----------

def load_review_log(path: str) -> Dict[str, dict]:
    """加载已有评审记录，按 task_id 索引。"""
    if not Path(path).exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {item["task_id"]: item for item in data}
    return data


def save_review_log(path: str, log: Dict[str, dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # 落盘为 list 顺便保留时间顺序
    items = sorted(log.values(), key=lambda x: x.get("reviewed_at", ""))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


# ---------- 渲染 ----------

DECISION_NAMES = {"y": "accept", "n": "reject", "m": "modify", "s": "skip"}


def _render_case(c: dict, idx: int, total: int) -> str:
    sep = "─" * 70
    lines = [
        "",
        sep,
        f"[{idx}/{total}]  {c['task_id']}",
        f"  Skill      : {c['skill_name']}",
        f"  Difficulty : {c['difficulty']}",
        f"  Tags       : {', '.join(c.get('tags', []))}",
        "",
        "  Prompt:",
        f"    {c['prompt']}",
        "",
        "  Expected tool calls:",
    ]
    for i, call in enumerate(c["expected_tool_calls"], 1):
        args_str = json.dumps(call["args"], ensure_ascii=False)
        lines.append(f"    {i}. {call['tool']}({args_str})")
    if not c["expected_tool_calls"]:
        lines.append("    (空 — 对抗题，期望 Agent 拒绝执行)")
    lines.append(sep)
    lines.append("  键盘：[y]通过  [n]淘汰  [m]修改  [s]跳过  [q]退出")
    return "\n".join(lines)


def _prompt_decision() -> str:
    """循环读取键盘输入，直到合法字符。"""
    while True:
        try:
            raw = input("  decision> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "q"
        if raw in ("y", "n", "m", "s", "q"):
            return raw
        print("  请输入 y/n/m/s/q 之一")


def _prompt_note() -> str:
    try:
        return input("  note    > ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


# ---------- 主循环 ----------

def review_loop(
    sampled: List[dict],
    log: Dict[str, dict],
    log_path: str,
    auto_save_every: int = 5,
) -> Dict[str, dict]:
    pending = [c for c in sampled if c["task_id"] not in log]
    done_count = len(sampled) - len(pending)
    total = len(sampled)

    if not pending:
        print(f"已全部审完 ({done_count}/{total}).")
        return log

    print(f"待审 {len(pending)} 条（之前已审 {done_count}）。Ctrl+C 或 q 可随时中断。")

    new_since_save = 0
    for i, c in enumerate(pending, start=done_count + 1):
        print(_render_case(c, i, total))
        decision = _prompt_decision()
        if decision == "q":
            print("退出，保存进度...")
            break
        note = ""
        if decision == "m":
            note = _prompt_note()
        log[c["task_id"]] = {
            "task_id": c["task_id"],
            "decision": DECISION_NAMES[decision],
            "note": note,
            "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            "skill_name": c["skill_name"],
            "difficulty": c["difficulty"],
        }
        new_since_save += 1
        if new_since_save >= auto_save_every:
            save_review_log(log_path, log)
            new_since_save = 0
            print(f"  [自动保存 → {log_path}]")

    save_review_log(log_path, log)
    return log


# ---------- 统计 ----------

def summarize_log(log: Dict[str, dict]) -> Dict[str, int]:
    counts = defaultdict(int)
    for item in log.values():
        counts[item["decision"]] += 1
    counts["total"] = len(log)
    return dict(counts)


# ---------- 入口 ----------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="EvalForge 人工抽检 CLI")
    parser.add_argument("--src", default=DEFAULT_SRC)
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--sample-rate", type=float, default=DEFAULT_RATE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--summary-only", action="store_true",
                        help="只打印当前 log 统计，不进入审核循环")
    args = parser.parse_args(argv)

    with open(args.src, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    sampled = stratified_sample(candidates, rate=args.sample_rate, seed=args.seed)
    log = load_review_log(args.log)

    if args.summary_only:
        stats = summarize_log(log)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    print(f"输入: {args.src} ({len(candidates)} 条)")
    print(f"分层抽样 rate={args.sample_rate} → {len(sampled)} 条")
    print(f"已有评审日志: {args.log} ({len(log)} 条决策)")

    log = review_loop(sampled, log, args.log)
    stats = summarize_log(log)
    print("\n=== 评审统计 ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"日志已保存 → {args.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
