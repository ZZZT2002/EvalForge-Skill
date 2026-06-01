# EvalForge-Skill 答辩产物索引（自动生成）

- 生成时间：2026-06-01T15:12:01
- 用法：照下表逐一拉开产物给评审看；每条都附文件路径以便快速跳转。

## 1. 冻结评测集（version_history/）

| 版本 | 用例数 | 文件 |
|---|---|---|
| v1.0.0 | 591 | `data/version_history/benchmark_v1.0.0.json` |
| v1.1.0 | 591 | `data/version_history/benchmark_v1.1.0.json` |

## 2. 自动生成报告（data/reports/）

| 报告 | 摘要首行 | 文件 |
|---|---|---|
| 衰退检测与演进报告 — v1.0.0 → v1.1.0 | - 生成时间：2026-05-31 20:34:54 | `data/reports/decay_report_v1.1.0.md` |
| Agent 评测报告 — v1.0.0 | - 生成时间：2026-05-31 20:34:53 | `data/reports/evaluation_v1.0.0.md` |
| 质量评估报告 — v1.0.0 | - 生成时间：2026-05-26 14:11:05 | `data/reports/quality_report_v1.0.0.md` |

## 3. CHANGELOG 最新条目

```markdown
## [Unreleased]

- D10 反向注入闭环已完成：8 条 from_badcase 种子注入（40 → 48），下游膨胀产出 120 个变体
- 后续 D11/D12 仅产出文档与答辩物，不影响 benchmark 数据；下次版本号留给 v1.2（如 D13 REAL 抽样扩充结果合入）
```

## 4. 三次答疑演讲稿

- `SPEECH_REVIEW1.md` — 第一次答疑演讲稿（5/26）
- `SPEECH_REVIEW2.md` — 第二次答疑演讲稿（5/28）
- `SPEECH_REVIEW3.md` — 第三次答疑演讲稿（6/2）

---

由 `python -m scripts.build_report_index` 重新生成。
