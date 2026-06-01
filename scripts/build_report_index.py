"""扫 data/reports/ + version_history/ + CHANGELOG，生成答辩用产物索引。

输出：data/reports/INDEX.md
内容：
  · 每份评测/质检/衰退报告的标题、首行摘要、文件路径
  · 冻结版本（benchmark_v*.json）列表 + 行数
  · CHANGELOG 最新条目摘要

用法：
  python -m scripts.build_report_index
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import config


def _first_line_after_title(md_path: Path) -> str:
    """读 Markdown，返回首个非标题非空行作为摘要。"""
    if not md_path.exists():
        return ""
    for line in md_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        return line[:120]
    return ""


def _md_title(md_path: Path) -> str:
    if not md_path.exists():
        return md_path.stem
    for line in md_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return md_path.stem


def _count_json_array(json_path: Path) -> Optional[int]:
    """对 list 顶层的 JSON 文件返回元素数；非 list 返回 None。"""
    if not json_path.exists():
        return None
    try:
        obj = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return len(obj) if isinstance(obj, list) else None


def _changelog_latest(changelog_path: Path) -> str:
    """提取 CHANGELOG 中最新一段（首个 `## [` 到下一个 `## [` 之间）。"""
    if not changelog_path.exists():
        return ""
    text = changelog_path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^## \[", text, flags=re.MULTILINE))
    if len(matches) < 2:
        return text[matches[0].start():].strip() if matches else ""
    return text[matches[0].start(): matches[1].start()].strip()


def build_index(
    reports_dir: str = config.REPORTS_DIR,
    versions_dir: str = config.VERSION_HISTORY_DIR,
    changelog_path: str = "CHANGELOG.md",
) -> str:
    rd = Path(reports_dir)
    vd = Path(versions_dir)
    cp = Path(changelog_path)

    lines: List[str] = []
    lines.append("# EvalForge-Skill 答辩产物索引（自动生成）")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}")
    lines.append("- 用法：照下表逐一拉开产物给评审看；每条都附文件路径以便快速跳转。")
    lines.append("")

    # ---------- 评测集冻结版本 ----------
    lines.append("## 1. 冻结评测集（version_history/）")
    lines.append("")
    lines.append("| 版本 | 用例数 | 文件 |")
    lines.append("|---|---|---|")
    for v in sorted(vd.glob("benchmark_v*.json")) if vd.exists() else []:
        n = _count_json_array(v)
        lines.append(f"| {v.stem.replace('benchmark_', '')} | {n if n is not None else '—'} | `{v.as_posix()}` |")
    lines.append("")

    # ---------- 自动报告 ----------
    lines.append("## 2. 自动生成报告（data/reports/）")
    lines.append("")
    lines.append("| 报告 | 摘要首行 | 文件 |")
    lines.append("|---|---|---|")
    if rd.exists():
        for md in sorted(rd.glob("*.md")):
            if md.name == "INDEX.md":
                continue
            title = _md_title(md)
            summary = _first_line_after_title(md).replace("|", "\\|")
            lines.append(f"| {title} | {summary} | `{md.as_posix()}` |")
    lines.append("")

    # ---------- CHANGELOG 最新 ----------
    lines.append("## 3. CHANGELOG 最新条目")
    lines.append("")
    latest = _changelog_latest(cp)
    if latest:
        lines.append("```markdown")
        lines.append(latest)
        lines.append("```")
    else:
        lines.append("_（未找到 CHANGELOG.md 或无版本条目）_")
    lines.append("")

    # ---------- 演讲稿 ----------
    lines.append("## 4. 三次答疑演讲稿")
    lines.append("")
    for s in ("SPEECH_REVIEW1.md", "SPEECH_REVIEW2.md", "SPEECH_REVIEW3.md"):
        p = Path(s)
        title = _md_title(p) if p.exists() else "（缺失）"
        lines.append(f"- `{s}` — {title}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("由 `python -m scripts.build_report_index` 重新生成。")
    return "\n".join(lines) + "\n"


def main() -> int:
    out = build_index()
    target = Path(config.REPORTS_DIR) / "INDEX.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(out, encoding="utf-8")
    print(f"[build_report_index] → {target.as_posix()} ({len(out)} chars)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
