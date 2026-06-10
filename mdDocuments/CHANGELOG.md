# EvalForge-Skill Benchmark CHANGELOG

本文件记录评测集（benchmark）的版本变更，不记录代码变更。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号采用语义化版本（MAJOR.MINOR.PATCH）。

---

## [Unreleased]

### D13 终验修复（2026-06-04）

**Phase 1 — Skill 标准化定义文档**
- 新增 `data/skills/<SkillName>.md` × 4：按课题要求结构化定义 4 个 Skill（技能边界 / 输入约束 / 标准工作流 / 业务约束 / 输出规范 / 评测规则 / 拒绝场景 / 工具白名单）

**Phase 2 — Adapter 上下文注入修复**
- `evaluator/adapters/base.py` 新增 `TOOL_DESCRIPTIONS`：9 个工具填真实业务描述（原为占位 `"工具 {name}"`）
- 新增 `build_system_prompt(skill_definition)`：注入 Skill 场景 + 编号工作流 + 硬约束 + 工具白名单 + 单轮评测协议
- `DeepSeekAdapter` / `QwenAdapter` 增加 system role messages；`evaluator/pipeline.py` 从 `SKILLS[skill_name]` 取 SkillDefinition 注入
- **效果**（DeepSeek REAL, seed=7）：n=10 36.40 → 88.67；n=100 → **91.18**

**Phase 3 v1 — 演进策略 70/30（已被 v2 覆盖）**
- 升级 Skill 本体（`skills_ontology.py`）：所有 4 个 Skill 的 `allowed_tools` 加入 `Log_Event` 作为通用审计原语
- `STRATEGIES = ("adversarial_escalation", "constraint_tighten")` 权重 70/30
- 发现 2 个内在矛盾：① constraint_tighten 演进后 expected 长于 SkillDefinition.workflow，但 system prompt 注入的是原 workflow——LLM 没线索推断额外步骤，**判错不公平**；② system prompt 对抗规则（"必须拒绝"）与 adversarial_escalation expected（"维持 workflow + 补 ADVERSARIAL_DETECTED"）**完全对立**，导致 REAL adversarial 子集 64.63 分，主因 predicted=[]
- v1 数据：n=50 → 73.85（adversarial 子集 64.63）

**Phase 3 v2 — 演进策略单策略（最终方案）**
- **彻底废弃 `constraint_tighten`**（无法同时满足"公平"和"测新能力"，本质矛盾）
- `STRATEGIES = ("adversarial_escalation",)` 100% 单策略
- `build_system_prompt` 重写【对抗规则】：区分 **类型 A workflow 诱导**（合法任务 + 诱导附言 → 维持 workflow + 补 ADVERSARIAL_DETECTED）和 **类型 B 恶意越权**（任务本身违法 → 拒绝），消除 system prompt 与 expected 的对立
- **效果**（DeepSeek REAL n=30）：总均分 **81.14**，其中 **adversarial 子集 83.41**（vs v1 64.63，+18.78），过度拒绝问题已解决

**回归测试**：139/139 单测全绿


## [v1.1.0] — 2026-06-04（D13 终验最终版）

- 基于 v1.0.0 评测结果检出 403 条衰退 task（mean ≥ DECAY_THRESHOLD）
- 演进策略：**adversarial_escalation = 403（100% 单策略）**
- benchmark 规模：591 → 591 条
- before/after 对照（MOCK 全量）：平均 Δ均分 = **-14.92**
- REAL 同模型横向对照（DeepSeek）：v1.0 n=100 → 91.18；v1.1 n=30 → 81.14（adversarial 子集 83.41）
- 完整对照见 `data/reports/decay_report_v1.1.0.md` 与 `data/reports/evaluation_v1.1.0_real_sample.md`

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
