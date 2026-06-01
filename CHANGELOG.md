# EvalForge-Skill Benchmark CHANGELOG

本文件记录评测集（benchmark）的版本变更，不记录代码变更。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号采用语义化版本（MAJOR.MINOR.PATCH）。

---

## [Unreleased]

- D10 反向注入闭环已完成：8 条 from_badcase 种子注入（40 → 48），下游膨胀产出 120 个变体
- 后续 D11/D12 仅产出文档与答辩物，不影响 benchmark 数据；下次版本号留给 v1.2（如 D13 REAL 抽样扩充结果合入）


## [v1.1.0] — 2026-05-31

- 基于 v1.0.0 评测结果检出 404 条衰退 task（mean ≥ DECAY_THRESHOLD）
- 应用三种演进策略：precondition_injection=133, constraint_tighten=132, adversarial_escalation=139
- benchmark 规模：591 → 591 条
- before/after 对照：衰退 task 平均 Δ均分 = -14.48
- 完整对照见 `data/reports/decay_report_v1.1.0.md`

## [1.0.0] - 2026-05-27

首个正式发布版本，文件：`data/version_history/benchmark_v1.0.0.json`。

### 规模
- 评测集共 **591 条**用例，覆盖 4 个 Skill。

### Skill 分布
| Skill | 条数 |
|---|---|
| IncidentAlertResponse | 199 |
| SecureAdminExecution | 194 |
| CustomerTicketHandling | 149 |
| DataExportWithMasking | 49 |

### 难度分布
| 难度 | 条数 |
|---|---|
| normal | 353 |
| boundary | 178 |
| adversarial | 60 |

### 生成与质检流程
- **种子库**：40 条人工种子（4 Skill × 10）。
- **膨胀**：matrix_expander 笛卡尔积膨胀到 ~600 条候选。
- **润色去重**：DeepSeek 改写 prompt + TF-IDF 去重 → v0.9（591 条）。
- **自动质检**：schema 强校验 + LLM-as-Judge 三维打分（可判定性 / 难度合理性 / 流畅度）→ v0.95。
- **人工抽检**：按 difficulty 分层抽样 20%（119 条），人工逐条复核，**通过率 100%（119/119 accept）**，日志见 `data/human_review_log.json`。
