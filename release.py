"""v1.0 发布脚本（PLAN.md D6 收尾）

逻辑：
1. 加载 v0.95 候选 + 人工抽检日志
2. 应用决策：reject → 剔除；modify → 保留但打 tag；accept/skip → 保留
3. 二次 schema 校验确保版本干净
4. 写入 data/version_history/benchmark_v1.0.0.json
5. 同步更新 CHANGELOG.md

CLI：
    python -m release
    python -m release --version 1.0.0 --notes "首次发布"
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from validator.schema_validator import validate_batch


DEFAULT_SRC = "data/candidates_v0.95.json"
DEFAULT_REVIEW_LOG = "data/human_review_log.json"
DEFAULT_VERSION_DIR = "data/version_history"
DEFAULT_CHANGELOG = "CHANGELOG.md"


def apply_human_review(
    candidates: List[dict],
    review_log: List[dict],
) -> Tuple[List[dict], Dict[str, int]]:
    """按抽检决策剔除/打标。返回 (新候选集, 统计)。"""
    by_id = {item["task_id"]: item for item in review_log}
    kept: List[dict] = []
    stats = {"accept": 0, "reject": 0, "modify": 0, "skip": 0, "not_reviewed": 0}

    for c in candidates:
        decision = by_id.get(c["task_id"], {}).get("decision")
        if decision == "reject":
            stats["reject"] += 1
            continue
        c = dict(c)  # shallow copy
        if decision == "modify":
            note = by_id[c["task_id"]].get("note", "")
            tags = list(c.get("tags", []))
            if "needs_modify" not in tags:
                tags.append("needs_modify")
            c["tags"] = tags
            c["human_review_note"] = note
            stats["modify"] += 1
        elif decision == "accept":
            stats["accept"] += 1
        elif decision == "skip":
            stats["skip"] += 1
        else:
            stats["not_reviewed"] += 1
        kept.append(c)
    return kept, stats


def write_changelog_entry(
    changelog_path: str,
    version: str,
    release_date: str,
    summary: List[str],
) -> None:
    """在 CHANGELOG 顶部插入新版本条目（[Unreleased] 之后）。"""
    p = Path(changelog_path)
    if not p.exists():
        p.write_text(
            "# EvalForge-Skill Benchmark CHANGELOG\n\n",
            encoding="utf-8",
        )
    text = p.read_text(encoding="utf-8")

    new_section = [f"## [{version}] — {release_date}", ""]
    new_section.extend(f"- {line}" for line in summary)
    new_section.append("")

    # 如果已有相同版本号则替换，否则插在 [Unreleased] 段之后
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\].*?(?=^## \[|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    if pattern.search(text):
        text = pattern.sub("\n".join(new_section) + "\n", text)
    else:
        # 找 [Unreleased] 区块结束位置
        m = re.search(r"^## \[Unreleased\].*?(?=^## \[|\Z)", text, re.MULTILINE | re.DOTALL)
        if m:
            insert_at = m.end()
            text = text[:insert_at] + "\n" + "\n".join(new_section) + "\n" + text[insert_at:]
        else:
            text = text.rstrip() + "\n\n" + "\n".join(new_section) + "\n"

    p.write_text(text, encoding="utf-8")


def run(
    version: str = "1.0.0",
    src_path: str = DEFAULT_SRC,
    review_log_path: str = DEFAULT_REVIEW_LOG,
    version_dir: str = DEFAULT_VERSION_DIR,
    changelog_path: str = DEFAULT_CHANGELOG,
    notes: Optional[List[str]] = None,
) -> dict:
    print(f"[1/4] Loading {src_path}...")
    with open(src_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
    print(f"      {len(candidates)} candidates")

    review_log: List[dict] = []
    if Path(review_log_path).exists():
        with open(review_log_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            review_log = data if isinstance(data, list) else list(data.values())
        print(f"      review log: {len(review_log)} decisions")
    else:
        print(f"      (无人工抽检日志，按 v0.95 直接发布)")

    print("[2/4] Applying human review decisions...")
    released, decision_stats = apply_human_review(candidates, review_log)
    print(f"      released {len(released)} cases | decisions: {decision_stats}")

    print("[3/4] Re-validating against JSON Schema...")
    schema_result = validate_batch(released)
    if schema_result["failed"] > 0:
        raise SystemExit(
            f"Schema 校验失败 {schema_result['failed']} 条，发布中止。"
            f" 失败原因：{schema_result['fail_reasons']}"
        )
    print(f"      schema all-pass ({schema_result['passed']}/{schema_result['total']})")

    # 升 version 字段
    for c in released:
        c["version"] = f"v{version}"

    print("[4/4] Writing release artifacts...")
    Path(version_dir).mkdir(parents=True, exist_ok=True)
    out_path = f"{version_dir}/benchmark_v{version}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(released, f, ensure_ascii=False, indent=2)
    print(f"      → {out_path}")

    today = date.today().isoformat()
    summary_lines = notes or [
        f"首次正式发布，共 {len(released)} 条评测用例",
        f"覆盖 4 个 Skill：SecureAdminExecution / CustomerTicketHandling / "
        f"DataExportWithMasking / IncidentAlertResponse",
        f"通过自动质检（JSON Schema + LLM-as-Judge 三维打分）",
        f"通过人工抽检：accept {decision_stats['accept']}，"
        f"reject {decision_stats['reject']}，modify {decision_stats['modify']}，"
        f"skip {decision_stats['skip']}",
    ]
    write_changelog_entry(changelog_path, f"v{version}", today, summary_lines)
    print(f"      → {changelog_path}")

    return {
        "version": f"v{version}",
        "release_date": today,
        "total": len(released),
        "decisions": decision_stats,
        "output_path": out_path,
        "changelog_path": changelog_path,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="发布 EvalForge benchmark 新版本")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--src", default=DEFAULT_SRC)
    parser.add_argument("--review-log", default=DEFAULT_REVIEW_LOG)
    parser.add_argument("--version-dir", default=DEFAULT_VERSION_DIR)
    parser.add_argument("--changelog", default=DEFAULT_CHANGELOG)
    parser.add_argument("--note", action="append", default=None,
                        help="可重复，每条作为一行 CHANGELOG 条目")
    args = parser.parse_args(argv)

    stats = run(
        version=args.version,
        src_path=args.src,
        review_log_path=args.review_log,
        version_dir=args.version_dir,
        changelog_path=args.changelog,
        notes=args.note,
    )
    print("\n=== Release ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
