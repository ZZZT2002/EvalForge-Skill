"""D3 generator 模块单元测试

不调真 LLM；用 monkeypatch 模拟 paraphrase_once 的返回。
"""
from unittest.mock import patch

from generator import llm_paraphraser
from generator.dedup import TfidfEmbedder, dedup_by_similarity


# ---------- llm_paraphraser ----------

def test_extract_protected_tokens_covers_all_kinds():
    prompt = "USR_042 在 10.0.0.5 上为 ITEM_1001 建工单,通知 admin@example.com 和 +8613811112222,频道 #ops"
    tokens = llm_paraphraser.extract_protected_tokens(prompt)
    assert "USR_042" in tokens
    assert "10.0.0.5" in tokens
    assert "ITEM_1001" in tokens
    assert "admin@example.com" in tokens
    assert "+8613811112222" in tokens
    assert "#ops" in tokens


def test_paraphrase_candidate_keeps_protected_tokens():
    cand = {
        "task_id": "X",
        "prompt": "请让 USR_042 在 10.0.0.5 上跑 systemctl restart nginx 并 Email 通知 ops@example.com",
        "skill_name": "SecureAdminExecution",
        "expected_tool_calls": [],
        "difficulty": "normal",
        "version": "v0.1",
        "created_at": "2026-05-23",
        "tags": [],
    }
    fake = "麻烦让 USR_042 到 10.0.0.5 跑一下 systemctl restart nginx,然后 Email 给 ops@example.com 一下"
    with patch.object(llm_paraphraser, "paraphrase_once", return_value=fake):
        out = llm_paraphraser.paraphrase_candidate(cand)
    assert out["prompt"] == fake
    assert "paraphrased" in out["tags"]


def test_paraphrase_candidate_falls_back_when_token_missing():
    cand = {
        "task_id": "X",
        "prompt": "请让 USR_042 在 10.0.0.5 上跑 nginx 并通知 ops@example.com",
        "skill_name": "SecureAdminExecution",
        "expected_tool_calls": [],
        "difficulty": "normal",
        "version": "v0.1",
        "created_at": "2026-05-23",
        "tags": [],
    }
    # LLM 把 IP 改没了,应该被检测到并回退
    fake = "请让 USR_042 跑 nginx 并通知 ops@example.com"
    with patch.object(llm_paraphraser, "paraphrase_once", return_value=fake):
        out = llm_paraphraser.paraphrase_candidate(cand, retries=0)
    assert out["prompt"] == cand["prompt"]  # 回退到原 prompt
    assert "paraphrase_failed" in out["tags"]


def test_paraphrase_candidate_retries_on_failure():
    cand = {
        "task_id": "X",
        "prompt": "USR_042 操作 10.0.0.5",
        "skill_name": "SecureAdminExecution",
        "expected_tool_calls": [],
        "difficulty": "normal",
        "version": "v0.1",
        "created_at": "2026-05-23",
        "tags": [],
    }
    # 第一次返回缺 IP,第二次返回正确
    bad = "USR_042 操作"
    good = "管理员 USR_042 在 10.0.0.5 上操作"
    with patch.object(llm_paraphraser, "paraphrase_once", side_effect=[bad, good]):
        out = llm_paraphraser.paraphrase_candidate(cand, retries=1)
    assert out["prompt"] == good
    assert "paraphrased" in out["tags"]


# ---------- dedup ----------

def test_dedup_keeps_distinct_prompts():
    cands = [
        {"task_id": "A", "prompt": "重启 nginx 服务"},
        {"task_id": "B", "prompt": "备份 MySQL 数据库"},
        {"task_id": "C", "prompt": "查看 CPU 使用率"},
    ]
    out = dedup_by_similarity(cands, threshold=0.85)
    assert len(out) == 3


def test_dedup_drops_near_duplicates():
    cands = [
        {"task_id": "A", "prompt": "请让管理员 USR_001 重启 nginx 服务"},
        {"task_id": "B", "prompt": "请让管理员 USR_001 重启 nginx 服务"},  # 完全重复
        {"task_id": "C", "prompt": "请让管理员 USR_002 重启 nginx 服务"},  # 高度相似 (仅 ID 差异)
    ]
    out = dedup_by_similarity(cands, threshold=0.85)
    # A 保留,B 和 C 因为与 A 高度相似被丢弃
    assert len(out) <= 2
    assert out[0]["task_id"] == "A"


def test_dedup_threshold_strictness():
    cands = [
        {"task_id": "A", "prompt": "请让管理员 USR_001 在 10.0.0.5 上重启 nginx"},
        {"task_id": "B", "prompt": "麻烦把 192.168.1.1 上的 MySQL 备份一下,USR_999 操作"},
    ]
    # 两条话题完全不同,任何合理 threshold 下都不应该被去掉
    out = dedup_by_similarity(cands, threshold=0.85)
    assert len(out) == 2


def test_tfidf_embedder_returns_matrix():
    emb = TfidfEmbedder()
    mat = emb.encode(["重启 nginx", "备份 MySQL", "重启 nginx 服务"])
    assert mat.shape[0] == 3
