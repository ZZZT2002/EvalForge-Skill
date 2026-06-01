# PLAN：EvalForge-Skill 13 天实施排期

> 配套文档：`PROJECT.md`（PRD）、`README.md`（课题原文）
> 立项日：2026-05-22（周五） / 终验日：2026-06-04（周四）
> 实施者：1 人 + Claude 辅导

---

## 0. 关键里程碑

| 日期 | 事件 | 必须完成的阶段 |
|---|---|---|
| 5/22（周五） | 课题介绍 + 立项（今天） | PROJECT.md / PLAN.md / 项目骨架 |
| **5/26（周二） 19:00** | 第一次答疑 | README 阶段 1+2（需求分析、种子库与生成） |
| **5/28（周四） 19:00** | 第二次答疑 | README 阶段 3+4（自动质检、人工校验 + v1.0 发布） |
| **6/2（周二） 19:00** | 第三次答疑 | README 阶段 5+6（衰退检测、Agent 实测 + 反向注入） |
| **6/4（周四） 19:00** | 终验 | 整体作品验收 |

---

## 1. 每日任务清单

### D0 — 5/22（周五，今天）
> **目标：把"该做什么"全部固化下来**
- [x] 阅读 README.md，理解课题要求
- [x] 与 Claude 讨论确定方向 = Skill 能力
- [x] 完成 PROJECT.md（v1.0）
- [x] 完成 PLAN.md
- [ ] 初始化项目骨架：
  - 创建目录结构（按 PROJECT.md §12）
  - `requirements.txt`（pydantic、jsonschema、sentence-transformers、openai、requests、tqdm）
  - 空文件占位 + `__init__.py`
  - 初始化 git 仓库，第一次 commit："chore: init project skeleton"
- [ ] 申请 / 测通 DeepSeek API Key，写一个 30 行的 `hello_deepseek.py` 验证 function calling 可用

**今晚验收**：能跑通一个最小的 DeepSeek function call demo。

---

### D1 — 5/23（周六）
> **目标：把数据契约和工具集敲定**
- [ ] `models.py`：实现 `SkillDefinition` / `ExpectedToolCall` / `TestCase`
- [ ] `tools_schema.py`：9 个工具的完整 JSON Schema，写单元测试验证 schema 本身合法
- [ ] `skills_ontology.py`：4 个 Skill 的定义（workflow + constraints + allowed_tools）
- [ ] `config.py`：所有阈值、模式开关
- [ ] 写一个 `validate_schema()` 单元测试，确保对 1 条合法用例返回 True、对 5 条非法用例返回 False

**晚间检查点**：跑 `python -m pytest tests/test_schema.py` 全绿。

---

### D2 — 5/24（周日）
> **目标：种子库 + 生成器骨架**
- [ ] 手写 40 条种子（4 Skill × 10 条），存 `data/seeds.json`
  - 每个 Skill：normal 6 / boundary 3 / adversarial 1
  - 严格满足对应 Skill 的 workflow 和 JSON Schema
- [ ] `generator/matrix_expander.py`：从种子抽取可变参数，做笛卡尔积膨胀（每条限 20 倍）
- [ ] 跑通：40 种子 → 膨胀到 ~600 条候选（不调 LLM）

**晚间检查点**：`python -m generator.matrix_expander` 能产出 ≥500 条 JSON。

---

### D3 — 5/25（周一）
> **目标：LLM 润色 + 去重，凑齐 v0.9 候选集**
- [ ] `generator/llm_paraphraser.py`：调 DeepSeek 改写 prompt，硬参数正则保护
- [ ] embedding 去重（`paraphrase-MiniLM-L3-v2`，阈值 0.85）
- [ ] 跑完整 generator，输出 `data/candidates_v0.9.json`，目标 ≥500 条
- [ ] 临时简报：用脚本统计难度分布、Skill 分布，截图准备明天答疑

**晚间检查点**：v0.9 候选集生成成功，分布偏差 ≤ ±5%。

---

### D4 — 5/26（周二）🔥 **第一次答疑（19:00）**
> **目标：阶段 1+2 review 过关**
- [ ] 上午：补 Skill 场景文档（PROJECT.md §3 已写，再写 1 页可视化概要 PPT）
- [ ] 下午：跑一次完整 generator，确认稳定
- [ ] 19:00 答疑：
  - 展示：场景覆盖矩阵 + 种子库样例 + 生成脚本运行截图 + v0.9 候选数据
  - 准备回答："为什么选 Skill 方向？""生成的多样性怎么保证？"

**当天交付**：种子库（40 条） + 生成脚本 + v0.9 候选集（≥500 条）。

---

### D5 — 5/27（周三）
> **目标：自动质检模块**
- [ ] `validator/schema_validator.py`：对每条候选用例的 `expected_tool_calls` 做 JSON Schema 强校验
- [ ] `validator/llm_judge.py`：调 DeepSeek 做三维打分（可判定性 / 难度合理性 / 流畅度）
- [ ] `reports/reporter.py`：生成 `quality_report_v1.0.0.md`
- [ ] 跑完整质检流水线，淘汰 schema_fail / quality_fail，得到 `data/candidates_v0.95.json`

**晚间检查点**：质检报告自动生成，通过率合理（建议保留 ≥85%）。

---

### D6 — 5/28（周四）🔥 **第二次答疑（19:00）**
> **目标：阶段 3+4 review 过关 + 发布 v1.0**
- [ ] 上午：`validator/human_console.py` 人工抽检 CLI（y/n/m/s 快捷键）
- [ ] 下午：实操抽检 20% 用例（≥100 条），记录 `human_review_log.json`
- [ ] 发布 v1.0：拷贝到 `data/version_history/benchmark_v1.0.0.json`，写 `CHANGELOG.md`
- [ ] 19:00 答疑：
  - 展示：质检报告 + 抽检日志截图 + v1.0 发布文件 + CHANGELOG
  - 准备回答："抽检 20% 够吗？""LLM-as-Judge 自己也会错怎么办？"

**当天交付**：v1.0 评测集（≥500 条）+ 质检报告 + 抽检日志 + CHANGELOG.md。

---

### D7 — 5/29（周五）
> **目标：评测器骨架 + 响应归一化**
- [ ] `evaluator/adapters/base.py` + `deepseek_adapter.py`
- [ ] `evaluator/normalizer.py`：4 种格式容错（纯 JSON / ```json / 带前后解释 / 原生 tool_calls）
- [ ] `evaluator/scorer.py`：三维判分（F1 + LCS + 顺序贪心匹配）
- [ ] **重点：写 `tests/test_scorer.py`**，至少 8 个 case：
  - 完全正确
  - 工具对、顺序错
  - 顺序对、参数错
  - 重复工具刷分（验证 matched_expected_idx 生效）
  - 对抗样例（expected 为空）

**晚间检查点**：`pytest tests/test_scorer.py` 全绿。**这是答辩技术深度的核心证据**。

---

### D8 — 5/30（周六）
> **目标：跑通 Agent 实测，产出 v1.0 评测报告**
- [ ] `evaluator/pipeline.py`：批量调度 Agent，记录 raw_response、normalized、score
- [ ] 加 `OpenAIAdapter`（或第二个 Agent 备选：豆包 / Qwen 等）
- [ ] 切 REAL 模式，跑 DeepSeek + 第二个 Agent 在 v1.0 上的完整评测
- [ ] 生成 `data/reports/evaluation_v1.0.0.md`：总分、各维度均分、Skill 分组得分
- [ ] 累积 `badcases.json`（分数 <70 的样本）

**晚间检查点**：拿到两份 Agent 评测结果，badcase 数 ≥30。

---

### D9 — 5/31（周日）
> **目标：衰退检测 + 约束演进**
- [ ] `updater/decay_detector.py`：找出平均分 >92 的衰退 task
- [ ] `updater/constraint_evolver.py`：三种演进策略（前置工具注入 / 约束加强 / 对抗诱导升级）
- [ ] 生成 v1.1.0，写入 `version_history` + `CHANGELOG.md`
- [ ] **跑 before/after 对照实验**：v1.0 衰退 task vs v1.1 演进版本，相同 Agent 跑两次
- [ ] 生成 `data/reports/decay_report_v1.1.0.md`

**晚间检查点**：decay_report 中 v1.1 平均分相比 v1.0 下降 ≥15。

---

### D10 — 6/1（周一）
> **目标：反向注入闭环 + 全流程贯通**
- [ ] `generator/feedback_injector.py`：badcase 审阅 CLI，通过的回流到 `seeds.json`
- [ ] 实操审阅 badcase，至少注入 5 条新种子
- [ ] 跑一次 `generator.run()`，验证新种子产生了新候选（tags 含 `from_badcase`）
- [ ] 跑 `python main.py` 完整流水线一次，确保零报错
- [ ] 修复发现的 bug

**晚间检查点**：main.py 一键跑通；如发现卡点提前预警。

---

### D11 — 6/2（周二）🔥 **第三次答疑（19:00）**
> **目标：阶段 5+6 review 过关**
- [ ] 上午：补充答辩展示物
  - 三份报告（quality / evaluation / decay）打印备份
  - before/after 对照表准备一张大图
- [ ] 19:00 答疑：
  - 展示：v1.1 评测集 + decay_report + Agent 评测得分 + badcase 反向注入示例
  - 准备回答："演进证据是什么？""怎么证明不是变得不同而是真的更难？"→ 给对照表
  - 准备回答："如果 LLM-as-Judge 也错了？" → 答：人工抽检兜底 + 多模型交叉

**当天交付**：v1.1 评测集 + decay_report + 反向注入证据。

---

### D12 — 6/3（周三）
> **目标：代码整理 + 答辩 PPT**
- [ ] 代码审查：删调试 print、补关键函数 docstring（只写非显然的部分）
- [ ] 完善仓库 README：how to run / how to switch MOCK-REAL / 项目截图
- [ ] 写答辩 PPT（10-15 页）：
  - p1 项目背景与方向选择（讲为什么选 Skill）
  - p2 整体架构图
  - p3-4 工具集 + Skill 场景 + 覆盖矩阵
  - p5 生成策略（三阶段）
  - p6 质检与人工抽检
  - p7 三维判分算法（重点页）
  - p8 评测结果（Agent 对比表）
  - p9 衰退检测 + before/after 对照（重点页）
  - p10 反向注入闭环
  - p11 项目目录与代码结构
  - p12 总结 + 未来工作（DAG 编辑距离、沙箱执行验证等）
- [ ] 答辩模拟一遍，找 1-2 个朋友提问练习

**晚间检查点**：PPT 完整，自演一遍 ≤15 分钟讲完。

---

### D13 — 6/4（周四）🔥 **终验（19:00）**
> **目标：稳定输出，沉着应答**
- [ ] 上午：最后一次 `python main.py` 端到端跑通，确认环境
- [ ] 下午：备份所有产物（代码 + 报告 + PPT）到 U 盘 / 云盘
- [ ] 19:00 终验

---

## 2. 风险预案

| 风险 | 概率 | 预案 |
|---|---|---|
| DeepSeek API 突然不稳定 | 中 | 备一个 Qwen / OpenAI key；MOCK 模式可临时顶住所有 demo |
| Embedding 模型下载慢 | 中 | D2 提前预下载 `paraphrase-MiniLM-L3-v2`，离线缓存 |
| 第二个 Agent 难选 | 中 | 优先级：DeepSeek → 豆包 → Qwen → OpenAI；不强求都是闭源 |
| 衰退检测找不到 task | 低 | 把 `DECAY_THRESHOLD` 调到 85；若仍找不到，主动给 v1.0 加几条简单题 |
| 人工抽检 100 条耗时 | 中 | D6 上午做完 CLI，下午集中 2 小时抽检；可以只展示 50 条的抽检日志先答疑 |
| 评测 API 调用超慢 | 中 | 用 `concurrent.futures` 多线程并发，限制 10 并发 |
| 时间紧来不及做演进 | 高 | 优先级排序：评测器 > 衰退检测 > 反向注入；最差情况反向注入用最简单的 CLI |

---

## 3. 每日固定动作

- 每天结束时：`git commit`，commit message 写清楚今天做了什么
- 每个 review 前一晚：跑一次 `python main.py` 端到端，确认没新 bug
- 遇到卡 30 分钟以上的问题：立刻问 Claude，不死磕

---

## 4. 当前进度

> 截至 2026-05-31（D9 当晚）

- [x] **D0** PROJECT.md / PLAN.md / 项目骨架 / DeepSeek hello demo
- [x] **D1** models / tools_schema / skills_ontology / config
- [x] **D2** 40 种子 + matrix_expander → ~600 候选
- [x] **D3** llm_paraphraser + dedup → `candidates_v0.9.json`（591 条）
- [x] **D4** 第一次答疑 ✅
- [x] **D5** schema_validator + llm_judge + `quality_report_v1.0.0.md` → `candidates_v0.95.json`
- [x] **D6** human_console 抽检（119/119 accept，100% 通过率）+ `benchmark_v1.0.0.json` 发布
- [x] **D7** evaluator/adapters + normalizer + scorer + 10 个判分单测
- [x] **D8** `evaluator/pipeline.py` 两 Agent MOCK 评测 + `evaluation_v1.0.0.md` + 73 条 badcase
- [x] **D9** decay_detector（404 task）+ constraint_evolver（三策略）+ `benchmark_v1.1.0.json` + `decay_report_v1.1.0.md`（before/after Δ均分 = -14.48）
- [x] **D10** feedback_injector（auto + interactive）+ 8 条 from_badcase 种子注入，膨胀后 120 个变体带 tag；`python main.py` 端到端零报错
- [ ] **D11** 6/2 19:00 第三次答疑（准备 before/after 大图 + badcase 反向注入示例） ← **下一步**
- [ ] **D12** 代码整理 + 仓库 README + 答辩 PPT
- [ ] **D13** 6/4 19:00 终验
