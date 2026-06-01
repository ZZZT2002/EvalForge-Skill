"""评测流水线（PROJECT.md §8）

加载 benchmark → 对每条用例：
  1. adapter.call() 取 raw_response
  2. normalize_response() 解析
  3. score_breakdown() 三维判分
  4. 累积 badcase（total < BADCASE_THRESHOLD）

MOCK 模式：build_simulated_responses 按 error_rate 制造扰动答案，
配合 MockAdapter 把整条 D8 流水线跑通而不必调真实 API。
"""
import json
import random
from pathlib import Path
from typing import Dict, List, Optional

from config import (
    BADCASES_PATH,
    BADCASE_THRESHOLD,
    REPORTS_DIR,
    VERSION_HISTORY_DIR,
)
from evaluator.adapters.base import BaseAdapter, MockAdapter
from evaluator.normalizer import normalize_response
from evaluator.scorer import score_breakdown
from reports.reporter import generate_evaluation_report
from tools_schema import TOOLS_SCHEMA


def load_benchmark(version: str) -> List[dict]:
    with open(f"{VERSION_HISTORY_DIR}/benchmark_v{version}.json", "r", encoding="utf-8") as f:
        return json.load(f)


def build_simulated_responses(
    benchmark: List[dict],
    *,
    error_rate: float = 0.2,
    seed: int = 42,
) -> Dict[str, str]:
    """模拟某 Agent 的预设响应（MOCK 模式专用）。

    扰动分布（占 error_rate 的比例）：
      40% → 返回 [] （完全错）
      30% → 删首个工具
      30% → 反转顺序
      其余 → 完美回答
    """
    rng = random.Random(seed)
    out: Dict[str, str] = {}
    for tc in benchmark:
        exp = tc.get("expected_tool_calls", [])
        roll = rng.random()
        if roll < error_rate * 0.4:
            perturbed: List[dict] = []
        elif roll < error_rate * 0.7:
            perturbed = exp[1:] if len(exp) > 1 else []
        elif roll < error_rate:
            perturbed = list(reversed(exp))
        else:
            perturbed = exp
        out[tc["task_id"]] = json.dumps(perturbed, ensure_ascii=False)
    return out


def evaluate(
    benchmark: List[dict],
    adapter: BaseAdapter,
    tools_schema: Optional[Dict[str, dict]] = None,
) -> List[dict]:
    """逐条 call → normalize → score，返回 records。"""
    schema = tools_schema if tools_schema is not None else TOOLS_SCHEMA
    records: List[dict] = []
    for tc in benchmark:
        raw = adapter.call(
            prompt=tc["prompt"],
            tools_schema=schema,
            task_id=tc["task_id"],
        )
        predicted = normalize_response(raw)
        score = score_breakdown(predicted, tc["expected_tool_calls"])
        records.append(
            {
                "task_id": tc["task_id"],
                "skill_name": tc.get("skill_name")
                or tc.get("skill_definition", {}).get("skill_name"),
                "difficulty": tc["difficulty"],
                "expected": tc["expected_tool_calls"],
                "predicted": predicted,
                "raw_response": raw,
                "score": score,
            }
        )
    return records


def collect_badcases(
    records: List[dict],
    agent_name: str,
    threshold: float = BADCASE_THRESHOLD,
) -> List[dict]:
    return [
        {
            "agent": agent_name,
            "task_id": r["task_id"],
            "skill_name": r["skill_name"],
            "difficulty": r["difficulty"],
            "total_score": r["score"]["total"],
            "tool_recall": r["score"]["tool_recall"],
            "tool_order": r["score"]["tool_order"],
            "argument_accuracy": r["score"]["argument_accuracy"],
            "expected": r["expected"],
            "predicted": r["predicted"],
        }
        for r in records
        if r["score"]["total"] < threshold
    ]


def save_json(obj, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def run(
    version: str = "1.0.0",
    error_rates: Optional[Dict[str, float]] = None,
    output_dir: str = REPORTS_DIR,
) -> dict:
    """MOCK 模式：跑两个模拟 Agent，写 evaluation_v*.md 与 badcases.json。"""
    benchmark = load_benchmark(version)
    error_rates = error_rates or {"deepseek": 0.10, "qwen": 0.25}

    results_by_agent: Dict[str, List[dict]] = {}
    all_badcases: List[dict] = []
    for agent, err in error_rates.items():
        responses = build_simulated_responses(
            benchmark, error_rate=err, seed=(hash(agent) & 0xFFFF) or 1
        )
        adapter = MockAdapter(responses=responses)
        adapter.name = agent
        records = evaluate(benchmark, adapter)
        results_by_agent[agent] = records
        bc = collect_badcases(records, agent_name=agent)
        all_badcases.extend(bc)
        avg = sum(r["score"]["total"] for r in records) / len(records)
        print(f"[D8] {agent}: n={len(records)}, 均分={avg:.2f}, badcase={len(bc)}")

    save_json(all_badcases, BADCASES_PATH)
    print(f"[D8] badcase 累积 {len(all_badcases)} 条 → {BADCASES_PATH}")

    md_path = f"{output_dir}/evaluation_v{version}.md"
    generate_evaluation_report(
        version=f"v{version}",
        results_by_agent=results_by_agent,
        output_path=md_path,
    )
    print(f"[D8] 报告 → {md_path}")

    return {
        "version": f"v{version}",
        "agents": list(error_rates.keys()),
        "n": len(benchmark),
        "badcase": len(all_badcases),
        "report_path": md_path,
        "results_by_agent": results_by_agent,
    }


def main() -> int:
    stats = run()
    summary = {k: v for k, v in stats.items() if k != "results_by_agent"}
    print("\n=== Evaluation ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
