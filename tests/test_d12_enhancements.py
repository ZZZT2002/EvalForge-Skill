"""D12 完善代码相关测试：

- BaseAdapter.call 签名应接受 task_id 占位参数
- evaluator.pipeline._build_adapter 在 MOCK/REAL 之间正确路由
- scripts.sample_real_eval.stratified_sample 保持 difficulty 比例
- scripts.build_report_index.build_index 输出含三个必备小节
"""
import inspect
import json
import re
from pathlib import Path

import pytest

import config
from evaluator.adapters.base import BaseAdapter, MockAdapter
from evaluator import pipeline as eval_pipeline
from scripts.sample_real_eval import stratified_sample
from scripts.build_report_index import build_index


# ---------- BaseAdapter 签名 ----------

def test_base_adapter_call_accepts_task_id():
    sig = inspect.signature(BaseAdapter.call)
    assert "task_id" in sig.parameters, "BaseAdapter.call 必须接受 task_id 占位参数"
    # 默认值是空字符串，否则 REAL Adapter 调用方就需要硬编码传 task_id
    assert sig.parameters["task_id"].default == ""


def test_mock_adapter_subclass_compatible():
    """子类 MockAdapter 应能被当作 BaseAdapter 使用，且 task_id 透传。"""
    adapter: BaseAdapter = MockAdapter(responses={"T_X": '[{"tool":"A","args":{}}]'})
    out = adapter.call(prompt="ignored", tools_schema=[], task_id="T_X")
    assert "tool" in out


# ---------- pipeline MOCK / REAL 路由 ----------

def test_pipeline_mock_routing(monkeypatch):
    monkeypatch.setattr(config, "EVAL_MODE", "MOCK")
    benchmark = [{"task_id": "T1", "expected_tool_calls": []}]
    adapter = eval_pipeline._build_adapter("deepseek", benchmark, error_rate=0.1)
    assert isinstance(adapter, MockAdapter)
    assert adapter.name == "deepseek"


def test_pipeline_real_routing_unknown_agent(monkeypatch):
    monkeypatch.setattr(config, "EVAL_MODE", "REAL")
    with pytest.raises(ValueError, match="未实现的 agent"):
        eval_pipeline._build_adapter("qwen", [], error_rate=0.0)


# ---------- 分层抽样 ----------

def _make_benchmark(n_normal: int, n_boundary: int, n_adv: int):
    items = []
    for i in range(n_normal):
        items.append({"task_id": f"N_{i}", "difficulty": "normal", "expected_tool_calls": []})
    for i in range(n_boundary):
        items.append({"task_id": f"B_{i}", "difficulty": "boundary", "expected_tool_calls": []})
    for i in range(n_adv):
        items.append({"task_id": f"A_{i}", "difficulty": "adversarial", "expected_tool_calls": []})
    return items


def test_stratified_sample_keeps_all_difficulties():
    bm = _make_benchmark(100, 50, 10)  # 比例 ~60/30/10
    sample = stratified_sample(bm, n=20, seed=1)
    diffs = {tc["difficulty"] for tc in sample}
    assert diffs == {"normal", "boundary", "adversarial"}, (
        f"分层抽样应覆盖三档难度，实际只见到 {diffs}"
    )


def test_stratified_sample_respects_n():
    bm = _make_benchmark(60, 30, 10)
    sample = stratified_sample(bm, n=10, seed=1)
    assert len(sample) <= 10  # 配额向上 round 后用 [:n] 截断


def test_stratified_sample_at_least_one_per_difficulty_even_when_small():
    """对抗题量少，n=10 时不能因为 round(10*10/600)=0 而被抽空。"""
    bm = _make_benchmark(353, 178, 60)  # v1.0 真实分布
    sample = stratified_sample(bm, n=10, seed=1)
    diffs = {tc["difficulty"] for tc in sample}
    assert "adversarial" in diffs, "对抗题不能因配额向下取整被抽空"


# ---------- 报告索引生成 ----------

def test_build_index_has_required_sections(tmp_path: Path):
    # 准备一个最小报告目录
    reports = tmp_path / "reports"
    versions = tmp_path / "vh"
    reports.mkdir()
    versions.mkdir()
    (reports / "demo.md").write_text("# Demo Report\n\n- 摘要这一行\n", encoding="utf-8")
    (versions / "benchmark_v0.1.0.json").write_text(json.dumps([{"x": 1}, {"x": 2}]), encoding="utf-8")
    changelog = tmp_path / "CL.md"
    changelog.write_text(
        "# CL\n\n## [Unreleased]\n\n- nothing\n\n## [v0.1.0] - 2026-01-01\n\n- 初版\n",
        encoding="utf-8",
    )

    out = build_index(
        reports_dir=str(reports),
        versions_dir=str(versions),
        changelog_path=str(changelog),
    )
    assert "## 1. 冻结评测集" in out
    assert "## 2. 自动生成报告" in out
    assert "## 3. CHANGELOG 最新条目" in out
    assert "v0.1.0" in out, "应抓到 benchmark 版本"
    assert "Demo Report" in out, "应抓到报告标题"


def test_build_index_handles_missing_dirs(tmp_path: Path):
    """目录不存在也不应炸——只是该段为空。"""
    out = build_index(
        reports_dir=str(tmp_path / "no_reports"),
        versions_dir=str(tmp_path / "no_versions"),
        changelog_path=str(tmp_path / "no_changelog.md"),
    )
    assert "## 1. 冻结评测集" in out
    assert "无版本条目" in out or "未找到" in out
