"""D10 反向注入测试（PLAN.md D10）

验证：
  - inject_auto 按 skill 均匀注入 N 条
  - 新种子带 from_badcase / source_* 元信息
  - task_id 不与现有 seed 冲突
  - matrix_expander 后 from_badcase tag 透到 variant
  - benchmark 找不到原 task 时跳过且不抛异常
"""
import json
import os
import tempfile
from pathlib import Path

from generator.feedback_injector import (
    SKILL_PREFIX,
    _alloc_seed_id,
    build_seed_from_badcase,
    inject_auto,
)
from generator.matrix_expander import expand_seed


def _make_badcase(task_id, skill, score, expected, difficulty="normal", agent="deepseek"):
    return {
        "agent": agent,
        "task_id": task_id,
        "skill_name": skill,
        "difficulty": difficulty,
        "total_score": score,
        "tool_recall": 0.0,
        "tool_order": 0.0,
        "argument_accuracy": 0.0,
        "expected": expected,
        "predicted": [],
    }


def _make_benchmark_case(task_id, skill, prompt, expected):
    return {
        "task_id": task_id,
        "skill_name": skill,
        "difficulty": "normal",
        "prompt": prompt,
        "expected_tool_calls": expected,
        "version": "v1.0.0",
        "created_at": "2026-05-27",
        "tags": ["seed", "expanded"],
    }


EXP_SAE = [
    {"tool": "Verify_Permission", "args": {"user_id": "USR_001", "action": "ADMIN"}},
    {"tool": "Execute_CMD", "args": {"target_ip": "10.0.0.5", "command": "ls"}},
    {"tool": "Send_Notification", "args": {"channel": "Slack", "receiver": "#ops", "content": "done"}},
]


def test_alloc_seed_id_no_collision():
    taken = {"T_SAE_001", "T_SAE_002", "T_SAE_FB_001"}
    new = _alloc_seed_id("SecureAdminExecution", taken)
    assert new == "T_SAE_FB_002"
    assert new not in taken


def test_alloc_seed_id_skill_prefix_fallback():
    new = _alloc_seed_id("UnknownSkill", set())
    assert new.startswith("T_FB_")


def test_build_seed_from_badcase_records_provenance():
    bc = _make_badcase("T_SAE_001_V03", "SecureAdminExecution", 35.0, EXP_SAE)
    bm = {"T_SAE_001_V03": _make_benchmark_case(
        "T_SAE_001_V03", "SecureAdminExecution", "执行 ls", EXP_SAE)}
    seed = build_seed_from_badcase(bc, bm, "T_SAE_FB_001")
    assert seed is not None
    assert seed["task_id"] == "T_SAE_FB_001"
    assert "from_badcase" in seed["tags"]
    assert seed["source_badcase_task_id"] == "T_SAE_001_V03"
    assert seed["source_agent"] == "deepseek"
    assert seed["source_score"] == 35.0
    assert seed["prompt"] == "执行 ls"
    assert seed["expected_tool_calls"] == EXP_SAE


def test_build_seed_returns_none_when_benchmark_missing():
    bc = _make_badcase("UNKNOWN_ID", "SecureAdminExecution", 0.0, EXP_SAE)
    assert build_seed_from_badcase(bc, {}, "T_SAE_FB_001") is None


def test_inject_auto_balances_across_skills(tmp_path):
    seeds = [
        {"task_id": "T_SAE_001", "skill_name": "SecureAdminExecution",
         "difficulty": "normal", "prompt": "p", "expected_tool_calls": EXP_SAE,
         "version": "v0.1", "created_at": "2026-05-23", "tags": ["seed"]},
    ]
    seeds_path = tmp_path / "seeds.json"
    seeds_path.write_text(json.dumps(seeds, ensure_ascii=False), encoding="utf-8")

    badcases = [
        _make_badcase("BM_SAE_1", "SecureAdminExecution", 10.0, EXP_SAE),
        _make_badcase("BM_SAE_2", "SecureAdminExecution", 5.0, EXP_SAE),  # lower → 优先
        _make_badcase("BM_SAE_3", "SecureAdminExecution", 60.0, EXP_SAE),
        _make_badcase("BM_CTH_1", "CustomerTicketHandling", 20.0, EXP_SAE),
    ]
    benchmark = [_make_benchmark_case(bc["task_id"], bc["skill_name"], f"prompt_{bc['task_id']}", EXP_SAE)
                 for bc in badcases]

    stats = inject_auto(badcases, benchmark, per_skill=2, seeds_path=str(seeds_path))

    assert stats["injected"] == 3  # SAE 取 2 条 + CTH 仅有 1 条
    assert stats["by_skill"]["SecureAdminExecution"] == 2
    assert stats["by_skill"]["CustomerTicketHandling"] == 1

    saved = json.loads(seeds_path.read_text(encoding="utf-8"))
    assert len(saved) == 4  # 原 1 + 注入 3
    fb_seeds = [s for s in saved if "from_badcase" in s.get("tags", [])]
    assert len(fb_seeds) == 3
    # SAE 应优先取 lowest score (BM_SAE_2 -> 5.0)
    sae_fb = [s for s in fb_seeds if s["skill_name"] == "SecureAdminExecution"]
    sources = {s["source_badcase_task_id"] for s in sae_fb}
    assert "BM_SAE_2" in sources  # 5.0 最低必入选
    assert "BM_SAE_3" not in sources  # 60.0 最高被挤出


def test_inject_auto_no_taskid_collision(tmp_path):
    seeds = [{"task_id": "T_SAE_FB_001", "skill_name": "SecureAdminExecution",
              "difficulty": "normal", "prompt": "p", "expected_tool_calls": EXP_SAE,
              "version": "v0.1", "created_at": "2026-05-23", "tags": ["seed"]}]
    seeds_path = tmp_path / "seeds.json"
    seeds_path.write_text(json.dumps(seeds, ensure_ascii=False), encoding="utf-8")

    bc = [_make_badcase("BM_X", "SecureAdminExecution", 1.0, EXP_SAE)]
    bm = [_make_benchmark_case("BM_X", "SecureAdminExecution", "p", EXP_SAE)]
    stats = inject_auto(bc, bm, per_skill=1, seeds_path=str(seeds_path))

    saved = json.loads(seeds_path.read_text(encoding="utf-8"))
    assert {s["task_id"] for s in saved} == {"T_SAE_FB_001", "T_SAE_FB_002"}


def test_expander_propagates_from_badcase_tag():
    fb_seed = {
        "task_id": "T_SAE_FB_001",
        "skill_name": "SecureAdminExecution",
        "difficulty": "normal",
        "prompt": "替 USR_777 在 10.0.0.5 上跑 ls",
        "expected_tool_calls": EXP_SAE,
        "version": "v0.2",
        "created_at": "2026-05-31",
        "tags": ["seed", "from_badcase"],
        "source_badcase_task_id": "T_SAE_005_V03",
    }
    variants = expand_seed(fb_seed)
    assert variants, "expander 应产出至少 1 个变体"
    for v in variants:
        assert "from_badcase" in v["tags"]
        assert "expanded" in v["tags"]
