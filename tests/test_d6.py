"""D6 测试：人工抽检 CLI + v1.0 发布脚本

不依赖键盘输入：通过 monkeypatch 模拟 input。
"""
import json
from collections import Counter
from pathlib import Path

import pytest

from release import apply_human_review, run as release_run, write_changelog_entry
from validator.human_console import (
    DECISION_NAMES,
    load_review_log,
    review_loop,
    save_review_log,
    stratified_sample,
    summarize_log,
)


# ---------- fixtures ----------

def _mkcase(tid, skill, diff, prompt="管理员 USR_001 在 10.0.0.1 上 systemctl restart nginx"):
    return {
        "task_id": tid,
        "skill_name": skill,
        "difficulty": diff,
        "prompt": prompt,
        "expected_tool_calls": [
            {"tool": "Verify_Permission", "args": {"user_id": "USR_001", "action": "ADMIN"}},
            {"tool": "Execute_CMD", "args": {"target_ip": "10.0.0.1", "command": "systemctl restart nginx"}},
            {"tool": "Send_Notification", "args": {"channel": "Slack", "receiver": "#ops", "content": "done"}},
        ],
        "version": "v0.95",
        "created_at": "2026-05-26",
    }


@pytest.fixture
def candidates_100():
    """60 normal + 30 boundary + 10 adversarial."""
    cases = []
    for i in range(60):
        cases.append(_mkcase(f"T_N_{i:03d}", "SecureAdminExecution", "normal"))
    for i in range(30):
        cases.append(_mkcase(f"T_B_{i:03d}", "SecureAdminExecution", "boundary"))
    for i in range(10):
        c = _mkcase(f"T_A_{i:03d}", "SecureAdminExecution", "adversarial")
        c["expected_tool_calls"] = []
        cases.append(c)
    return cases


# ---------- 抽样 ----------

def test_stratified_sample_per_layer_size(candidates_100):
    sampled = stratified_sample(candidates_100, rate=0.2, seed=1)
    cnt = Counter(c["difficulty"] for c in sampled)
    # 60 * 0.2 = 12, 30 * 0.2 = 6, 10 * 0.2 = 2
    assert cnt["normal"] == 12
    assert cnt["boundary"] == 6
    assert cnt["adversarial"] == 2


def test_stratified_sample_deterministic(candidates_100):
    a = stratified_sample(candidates_100, rate=0.2, seed=42)
    b = stratified_sample(candidates_100, rate=0.2, seed=42)
    assert [c["task_id"] for c in a] == [c["task_id"] for c in b]


def test_stratified_sample_min_one_per_layer():
    # 单层只有 2 条，rate=0.1 → round(0.2)=0 → 至少 1
    cases = [_mkcase("T_X_001", "SecureAdminExecution", "adversarial")]
    sampled = stratified_sample(cases, rate=0.1)
    assert len(sampled) == 1


# ---------- log I/O ----------

def test_save_and_load_log_roundtrip(tmp_path):
    log = {
        "T_001": {"task_id": "T_001", "decision": "accept", "note": "",
                  "reviewed_at": "2026-05-28T10:00:00",
                  "skill_name": "SecureAdminExecution", "difficulty": "normal"},
    }
    path = tmp_path / "log.json"
    save_review_log(str(path), log)
    loaded = load_review_log(str(path))
    assert loaded == log


def test_load_log_missing_file_returns_empty(tmp_path):
    assert load_review_log(str(tmp_path / "nope.json")) == {}


# ---------- review_loop ----------

def test_review_loop_records_decisions(tmp_path, monkeypatch, candidates_100):
    sampled = candidates_100[:3]
    log_path = tmp_path / "log.json"

    inputs = iter(["y", "n", "m", "needs param fix"])
    monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

    log = review_loop(sampled, {}, str(log_path), auto_save_every=100)
    assert log[sampled[0]["task_id"]]["decision"] == "accept"
    assert log[sampled[1]["task_id"]]["decision"] == "reject"
    assert log[sampled[2]["task_id"]]["decision"] == "modify"
    assert log[sampled[2]["task_id"]]["note"] == "needs param fix"


def test_review_loop_skip_and_quit(tmp_path, monkeypatch, candidates_100):
    sampled = candidates_100[:3]
    log_path = tmp_path / "log.json"

    inputs = iter(["s", "q"])
    monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

    log = review_loop(sampled, {}, str(log_path))
    assert log[sampled[0]["task_id"]]["decision"] == "skip"
    # 第二条按 q，所以只记录了 1 条
    assert len(log) == 1


def test_review_loop_resume_skips_done(tmp_path, monkeypatch, candidates_100):
    sampled = candidates_100[:3]
    log_path = tmp_path / "log.json"

    # 预置一条已审过
    existing = {sampled[0]["task_id"]: {
        "task_id": sampled[0]["task_id"], "decision": "accept", "note": "",
        "reviewed_at": "2026-05-28T09:00:00",
        "skill_name": sampled[0]["skill_name"], "difficulty": sampled[0]["difficulty"],
    }}

    inputs = iter(["y", "y"])
    monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

    log = review_loop(sampled, dict(existing), str(log_path))
    assert len(log) == 3
    assert log[sampled[0]["task_id"]]["reviewed_at"] == "2026-05-28T09:00:00"


def test_summarize_log_counts():
    log = {
        "A": {"task_id": "A", "decision": "accept"},
        "B": {"task_id": "B", "decision": "reject"},
        "C": {"task_id": "C", "decision": "accept"},
    }
    s = summarize_log(log)
    assert s == {"accept": 2, "reject": 1, "total": 3}


# ---------- release.apply_human_review ----------

def test_apply_human_review_basic(candidates_100):
    cases = candidates_100[:5]
    review = [
        {"task_id": cases[0]["task_id"], "decision": "accept"},
        {"task_id": cases[1]["task_id"], "decision": "reject"},
        {"task_id": cases[2]["task_id"], "decision": "modify", "note": "改一下"},
        {"task_id": cases[3]["task_id"], "decision": "skip"},
        # cases[4] 没有评审
    ]
    kept, stats = apply_human_review(cases, review)
    ids = [c["task_id"] for c in kept]
    assert cases[0]["task_id"] in ids
    assert cases[1]["task_id"] not in ids  # rejected
    assert cases[2]["task_id"] in ids
    assert cases[3]["task_id"] in ids
    assert cases[4]["task_id"] in ids
    # modify 应该带上 needs_modify tag + note
    modified = next(c for c in kept if c["task_id"] == cases[2]["task_id"])
    assert "needs_modify" in modified["tags"]
    assert modified["human_review_note"] == "改一下"
    assert stats == {
        "accept": 1, "reject": 1, "modify": 1, "skip": 1, "not_reviewed": 1,
    }


# ---------- release.run 端到端 ----------

def test_release_run_end_to_end(tmp_path, candidates_100):
    src = tmp_path / "v095.json"
    review = tmp_path / "review.json"
    vdir = tmp_path / "version_history"
    changelog = tmp_path / "CHANGELOG.md"

    src.write_text(json.dumps(candidates_100, ensure_ascii=False), encoding="utf-8")
    review.write_text(json.dumps([
        {"task_id": candidates_100[0]["task_id"], "decision": "reject"},
    ], ensure_ascii=False), encoding="utf-8")

    stats = release_run(
        version="1.0.0",
        src_path=str(src),
        review_log_path=str(review),
        version_dir=str(vdir),
        changelog_path=str(changelog),
    )
    assert stats["total"] == len(candidates_100) - 1
    out = json.loads((vdir / "benchmark_v1.0.0.json").read_text(encoding="utf-8"))
    assert all(c["version"] == "v1.0.0" for c in out)
    cl_text = changelog.read_text(encoding="utf-8")
    assert "## [v1.0.0]" in cl_text


def test_release_run_no_review_log(tmp_path, candidates_100):
    """没有 review_log 时也能直接发布（按 v0.95 原样）"""
    src = tmp_path / "v095.json"
    src.write_text(json.dumps(candidates_100, ensure_ascii=False), encoding="utf-8")

    stats = release_run(
        version="1.0.0",
        src_path=str(src),
        review_log_path=str(tmp_path / "nope.json"),
        version_dir=str(tmp_path / "vh"),
        changelog_path=str(tmp_path / "CL.md"),
    )
    assert stats["total"] == len(candidates_100)


# ---------- changelog ----------

def test_changelog_replaces_same_version(tmp_path):
    p = tmp_path / "CHANGELOG.md"
    p.write_text(
        "# CHANGELOG\n\n## [Unreleased]\n\n## [v1.0.0] — 2026-05-28\n- old summary\n",
        encoding="utf-8",
    )
    write_changelog_entry(str(p), "v1.0.0", "2026-05-28", ["new summary"])
    text = p.read_text(encoding="utf-8")
    assert "new summary" in text
    assert "old summary" not in text
    assert text.count("## [v1.0.0]") == 1
