"""D8 评测器 + D9 衰退检测/演进 集成测试"""
import json

from evaluator.pipeline import (
    build_simulated_responses,
    collect_badcases,
    evaluate,
)
from evaluator.adapters.base import MockAdapter
from updater.constraint_evolver import (
    STRATEGIES,
    assign_strategy,
    evolve_benchmark,
)
from updater.decay_detector import detect_decay


EXP = [
    {"tool": "Verify_Permission", "args": {"user_id": "USR_001", "action": "ADMIN"}},
    {"tool": "Execute_CMD", "args": {"target_ip": "10.0.0.5", "command": "ls"}},
    {"tool": "Send_Notification", "args": {"channel": "Slack", "receiver": "#ops", "content": "done"}},
]


def _mk_case(task_id, skill="SecureAdminExecution", difficulty="normal", expected=None):
    return {
        "task_id": task_id,
        "skill_name": skill,
        "difficulty": difficulty,
        "prompt": f"prompt for {task_id}",
        "expected_tool_calls": expected if expected is not None else EXP,
        "version": "v1.0.0",
        "created_at": "2026-05-27",
        "tags": ["seed"],
    }


# ---------- D8 ----------
def test_simulated_responses_zero_error_gives_perfect_scores():
    benchmark = [_mk_case(f"T_{i:03d}") for i in range(20)]
    responses = build_simulated_responses(benchmark, error_rate=0.0, seed=1)
    adapter = MockAdapter(responses=responses)
    adapter.name = "perfect"
    records = evaluate(benchmark, adapter, tools_schema={})
    assert all(r["score"]["total"] == 100.0 for r in records)


def test_simulated_responses_high_error_produces_badcases():
    benchmark = [_mk_case(f"T_{i:03d}") for i in range(50)]
    responses = build_simulated_responses(benchmark, error_rate=0.6, seed=7)
    adapter = MockAdapter(responses=responses)
    adapter.name = "noisy"
    records = evaluate(benchmark, adapter, tools_schema={})
    bc = collect_badcases(records, agent_name="noisy")
    assert len(bc) > 0
    avg = sum(r["score"]["total"] for r in records) / len(records)
    assert avg < 100.0


def test_evaluate_record_shape():
    benchmark = [_mk_case("T_001")]
    adapter = MockAdapter(responses={"T_001": json.dumps(EXP)})
    adapter.name = "x"
    rec = evaluate(benchmark, adapter, tools_schema={})[0]
    assert set(rec.keys()) >= {
        "task_id", "skill_name", "difficulty",
        "expected", "predicted", "raw_response", "score",
    }
    assert set(rec["score"].keys()) >= {
        "total", "tool_recall", "tool_order", "argument_accuracy",
    }


# ---------- D9 ----------
def test_detect_decay_picks_high_mean_only():
    results = {
        "a1": [
            {"task_id": "T1", "score": {"total": 95.0}},
            {"task_id": "T2", "score": {"total": 50.0}},
        ],
        "a2": [
            {"task_id": "T1", "score": {"total": 98.0}},
            {"task_id": "T2", "score": {"total": 60.0}},
        ],
    }
    decay = detect_decay(results, threshold=92.0)
    ids = [d["task_id"] for d in decay]
    assert "T1" in ids and "T2" not in ids
    assert decay[0]["mean_score"] == 96.5


def test_assign_strategy_stable_and_in_range():
    for tid in ["T_X_001", "T_Y_042", "long_task_id_with_suffix_V05"]:
        s = assign_strategy(tid)
        assert s in STRATEGIES
        assert assign_strategy(tid) == s  # 多次调用稳定


def test_evolve_benchmark_only_touches_decay_set():
    benchmark = [_mk_case(f"T_{i:03d}") for i in range(6)]
    decay_ids = ["T_001", "T_003", "T_005"]
    v11, stats, id_map = evolve_benchmark(benchmark, decay_ids)

    assert len(v11) == len(benchmark)
    assert sum(stats.values()) == len(decay_ids)
    assert set(id_map.keys()) == set(decay_ids)
    # 演进后的 task 必有标记
    evolved = [c for c in v11 if c["task_id"] in set(id_map.values())]
    assert len(evolved) == len(decay_ids)
    for c in evolved:
        assert "evolved" in c["tags"]
        assert c["evolution_strategy"] in STRATEGIES
        assert c["evolved_from"] in decay_ids
    # 非衰退 task 不应有 evolution_strategy 字段
    untouched = [c for c in v11 if c["task_id"] not in set(id_map.values())]
    assert all("evolution_strategy" not in c for c in untouched)


def test_evolve_strategies_modify_expected_or_prompt():
    case = _mk_case("T_001")
    benchmark = [case]
    # 强制各策略各跑一次
    from updater.constraint_evolver import evolve_case
    for strat in STRATEGIES:
        new = evolve_case(case, strat)
        if strat == "adversarial_escalation":
            assert new["prompt"] != case["prompt"]
            assert new["difficulty"] == "adversarial"
            # 即使 prompt 改了，expected 也追加了审计 Log_Event
            assert len(new["expected_tool_calls"]) == len(case["expected_tool_calls"]) + 1
        else:
            # 前置 / 后置两种策略都改变 expected 长度
            assert len(new["expected_tool_calls"]) > len(case["expected_tool_calls"])
        assert new["task_id"] != case["task_id"]
        assert "evolved" in new["tags"]
