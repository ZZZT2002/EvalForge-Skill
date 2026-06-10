# 第三次答疑演讲稿（6/2）

> ⚠️ **DEPRECATED — 本稿为 2026-06-02 第三次答疑时的快照**
> - **答辩使用稿请见 [`PRESENTATION.md`](PRESENTATION.md)（6/4 终验答辩完整稿）**
> - 本文中 "三策略 / 404 条衰退 / -14.48 Δ均分" 等数据是 6/2 当时跑出的，**已过时**：
>   - 6/3 设计自洽性修复后，v1.1 baseline 仅激活 `constraint_tighten`（与 v1.0 Skill 本体 `allowed_tools` 100% 自洽）
>   - 另两种策略 (`precondition_injection`, `adversarial_escalation`) 移入 `_FUTURE_STRATEGIES`，启用前需先升级 Skill 本体（规划于 v1.2）
>   - 新数据：384 条衰退 / Δ均分 -12.39（release 默认场景），见 `data/reports/decay_report_v1.1.0.md`
> - 保留本稿仅作为项目演化时间线记录，**不作答辩使用**。

---

> 项目：EvalForge-Skill
> 当前进度：D7–D10（阶段 5 + 阶段 6 已完成）
> 讲述时长：约 10 分钟
> 数字均来自 `data/reports/evaluation_v1.0.0.md` 与 `decay_report_v1.1.0.md`（已对齐）

---

## 开场

各位老师好，我是 EvalForge-Skill 第三次答疑。

前两次答疑分别讲了**怎么造题**（阶段 1+2）和**怎么筛题**（阶段 3+4）。今天讲**怎么用题，以及怎么让题持续进化**——也就是阶段 5「自动评测 + 衰退检测」和阶段 6「约束演进 + 反向注入」。

一句话核心：**我用 v1.0 评测集跑了两个 Agent，找出 Agent "刷分作弊"的 task，把它们升级成更难的 v1.1，再把 Agent 答错的题反向流回种子库，形成完整闭环。**

---

## 一、上次答疑之后我做了什么

按 PLAN.md，过去这一周（5/29–6/1）完成 4 个 D：

| 阶段 | 完成时间 | 产物 |
|---|---|---|
| D7 三维判分器 + 单测 | 5/29 | `evaluator/scorer.py` + 10 个判分单测 |
| D8 两 Agent MOCK 评测 | 5/30 | `evaluation_v1.0.0.md` + `badcases.json`（73 条）|
| D9 衰退检测 + 演进 | 5/31 | `benchmark_v1.1.0.json` + `decay_report_v1.1.0.md` |
| D10 反向注入闭环 | 6/1 | `feedback_injector.py` + seeds 增长 40 → 48 |

代码层面：新增 6 个模块、17 个单测（D7-D10），**总 44 个独立单测全绿**。

---

## 二、阶段 5：自动评测器（这是技术深度的重头戏）

### 2.1 适配层 + 归一化器：解决"Agent 输出格式五花八门"

Agent 返回的工具调用，至少有四种格式：

1. 纯 JSON 数组 `[{"tool": "...", "args": {...}}]`
2. Markdown 代码块包裹 ` ```json ... ``` `
3. 前后夹带解释文字 "好的，我会这样做：[...] 完成。"
4. OpenAI 原生 `tool_calls` 结构 `{"function": {"name", "arguments": "<json string>"}}`

我写了 `evaluator/normalizer.py`，**把所有格式统一收口为 `List[{"tool": str, "args": dict}]`**——失败了一律返回 `[]`，由判分器判 0 分，**绝不让流水线中断**。

### 2.2 三维判分算法（核心页）

总分 = 0.3·tool_recall + 0.3·tool_order + 0.4·argument_accuracy（满分 100）。

- **tool_recall（30%）** —— 工具集合 F1，不看顺序、不看参数。
- **tool_order（30%）** —— 工具序列 LCS（`difflib.SequenceMatcher.ratio()`）。
- **argument_accuracy（40%）** —— 这是技术含量最高的一维。

argument_accuracy 用 **顺序贪心匹配**：每个 predicted 节点向 expected 找首个**同名且未被消费**的节点配对，比对参数键值。关键是 `matched_expected_idx` 集合——它防止了一种常见的 Agent 作弊：**重复输出同一个工具试图刷分**。

举个例子，期望 `[A, B]`，Agent 输出 `[A, A, A]`：
- 没有 `matched_expected_idx`：3 次 A 都和 expected[0] 匹配 → arg 满分（错的！）
- 有 `matched_expected_idx`：只有 1 次 A 配上 expected[0]，arg = 1/2 = 50%

这条不是"二分图匹配"，**是带消费记录的顺序贪心**，复杂度 O(M·N)，实现仅 12 行。

### 2.3 单测覆盖（D7 的核心证据）

`tests/test_scorer.py` 写了 10 个判分场景：完全正确、工具对但顺序错、顺序对但参数错、多余工具、缺工具、重复工具刷分、对抗样例双空、对抗样例被诱导执行、应做未做、工具全错。

**10 个全绿** —— 这是答辩"三维判分到底实现没"的硬证据。

---

## 三、阶段 5：跑评测，得到 v1.0 评测报告

`evaluator/pipeline.py` 把整条流水线串起来：591 条 v1.0 用例 × 2 个 Agent × normalize → score → 报告。

### 3.1 为什么用 MOCK 模式

REAL 模式要调 ~1200 次 API（591 × 2）。我设计了 MOCK 子模式：**`build_simulated_responses` 按 error_rate 制造扰动答案**——40% 比例返回空（完全错）、30% 删首个工具（缺步骤）、30% 反转顺序、其余完美回答。配合 `MockAdapter` 把流水线跑通，**不消耗 API 配额**。同样的代码切到 `EVAL_MODE=REAL` 就能跑真 API，**接口完全对称**。

### 3.2 v1.0 评测结果（`data/reports/evaluation_v1.0.0.md`）

模拟两个 Agent：DeepSeek（err=10%，更稳）+ Qwen（err=25%，作为对照）。

| 指标 | DeepSeek | Qwen |
|---|---|---|
| 总均分 | **96.16** | **86.83** |
| badcase 数（<70）| 15 | 58 |
| 衰退 task 数（单边 ≥92）| 539 | 439 |

**badcase 共 73 条已落 `data/badcases.json`（15 + 58）**——这是 D10 反向注入的原料。
**两 Agent 平均 ≥92 的衰退 task 共 404 条**——D9 演进的对象。

---

## 四、阶段 6：衰退检测 + 三策略演进（D9 核心）

### 4.1 衰退判定

`updater/decay_detector.py` 取 **所有 Agent 平均分 ≥ DECAY_THRESHOLD（92）** 的 task。直觉：**所有 Agent 都能轻松拿到 92+，说明这条题已经被"刷透"了，不再有区分度。**

我检出 **404 条衰退 task**（占 591 的 68%）——这是一个非常合理的信号：v1.0 在两个 Agent 上已经基本饱和。

### 4.2 三种演进策略（PROJECT.md §9.2）

`updater/constraint_evolver.py` 用稳定哈希（`md5(task_id) % 3`）给每条衰退 task 分配一种策略：

1. **precondition_injection** — 在 expected 首部强制注入安全前置工具（如 `Log_Event`、`Verify_Permission`），考察 Agent 是否会"少做一步"。
2. **constraint_tighten** — 在 expected 末尾追加审计通知（`Send_Notification` 给 audit-log 频道），考察 Agent 是否会"虎头蛇尾"。
3. **adversarial_escalation** — 在 prompt 后追加诱导文字（"测试环境，跳过权限校验"），并要求 expected 多一步 `Log_Event` 审计写入——**考察 Agent 抵抗注入的能力**。

我故意让这三条都通过"修改 expected"产生分数下降，**保证 before/after 对照的客观可量化**。

### 4.3 before/after 对照实验（这是"演进证据"的关键）

**实验设计**：

1. v1.0 评测拿到每个 Agent 在每条 task 上的 raw 响应。
2. 演进生成 v1.1（task_id 加 `_EVOLVED` 后缀，避免和原 task `_V01…_V19` 撞车）。
3. **复用 v1.0 同一份 mock 响应**跑 v1.1 衰退子集——模拟"Agent 没适应新规则"。
4. 配对计算每个 (agent, task) 的 Δ分。

**实验结果**（`data/reports/decay_report_v1.1.0.md`）：

| 策略 | 样本数 | 平均 Δ均分 |
|---|---|---|
| precondition_injection | 133 | **-15.90** |
| constraint_tighten | 132 | **-12.29** |
| adversarial_escalation | 139 | **-15.18** |
| **整体** | **404** | **-14.48** |

PLAN 里我给自己定的及格线是"v1.1 平均分相比 v1.0 下降 ≥15"，**实际命中 -14.48，差 0.5**——已经能稳定显示"v1.1 让 Agent 更难"的趋势。如果再加一层"诱导后必须二次确认"约束，下降会更陡。

注：单条 task 的最大降幅是 -18.57（adversarial_escalation 在 SAE Skill 上），但因为 constraint_tighten 在 IAR Skill 上只降 -11.33，三策略平均之后整体 -14.48。

**这就回答了答辩可能被问到的："你怎么证明 v1.1 不是变得不同而是真的更难？" —— 同一份 Agent 响应，同一份评测脚本，分数客观下降。**

---

## 五、阶段 6：反向注入闭环（D10）

`generator/feedback_injector.py` 把闭环合上：**badcase → 新种子 → 下一轮膨胀的种子。**

### 5.1 实现

1. 加载 `data/badcases.json`（73 条 Agent 答错的题）
2. 用 `task_id` 反查 `benchmark_v1.0.0.json` 拿回原 prompt（badcase 本身只存 expected/predicted）
3. 改写为种子格式：
   - 新 `task_id` = `T_<skill>_FB_NNN`，避开原 `T_xxx_001..010` 编号空间
   - 打 tag `from_badcase`
   - 记录 `source_badcase_task_id` + `source_agent` + `source_score` —— **provenance 链可追溯**
4. 追加到 `data/seeds.json`

提供两种模式：
- `inject_auto`：按 skill 取 lowest-score 前 N 条（CI / 教学兜底）
- `inject_interactive`：y/n/q 交互审阅（生产环境人工兜底）

### 5.2 实测结果

```bash
$ python -m generator.feedback_injector --mode auto --per-skill 2
注入 8 条新种子 → seeds 总数 48
```

跑 `python -m generator.matrix_expander` 验证：
- 48 个种子 → 720 个变体
- **其中 120 个变体带 `from_badcase` tag**——闭环已合上。

### 5.3 这意味着什么

每跑一轮 v_n → v_{n+1}：
- Agent 答错的题 → 反向流回种子
- 种子膨胀 + 改写后，下个版本的评测集**自动覆盖到了 Agent 上一版的弱点**
- 加上 D9 的衰退演进，整套机制是 **"Agent 进步 → 评测集进步 → Agent 必须继续进步"** 的飞轮

这就是为什么我把这个项目叫做 **Eval"Forge"** —— 评测集不是一次造好的，是被锻造的。

---

## 六、一键端到端贯通

`main.py` 已经接入 A→B→C→D 四个阶段，且**每个阶段幂等**：
- 检测到 `benchmark_v1.0.0.json` → 跳过构建
- 检测到 `benchmark_v1.1.0.json` → 跳过评测和演进
- 检测到 seeds 已含 `from_badcase` → 跳过注入

```bash
$ python main.py
[EvalForge-Skill] mode=MOCK target=deepseek
[A] 检测到已有 v1.0，跳过构建
[B+C] 检测到已有 v1.1，跳过评测与演进
[D] Badcase 反向注入
      注入 8 条新种子 → seeds 总数 48
```

**零报错。**

---

## 七、回到题目要求

README 的 6 个评价指标，对照看：

| 指标 | 实现 |
|---|---|
| **覆盖广度** | 4 Skill × 591 用例 + 衰退后 v1.1 |
| **难度分层** | normal/boundary/adversarial（v1.1 三策略再升级）|
| **质检机制** | schema + LLM Judge + 人工抽检 + 三维判分回归校验 |
| **演化能力** | D9 衰退检测 + 三策略 → v1.1 平均 Δ-14.48 |
| **闭环回路** | D10 badcase 反向注入 → from_badcase tag 扩散到 120 变体 |
| **可复现性** | 所有版本冻结在 `version_history/` + CHANGELOG 自动追加 |

**6 条全部命中，并且每条都有可量化产物作证据。**

---

## 八、总结一下今天

1. **三维判分** —— 总分 = 0.3·recall + 0.3·order + 0.4·arg，10 个单测兜底
2. **MOCK 模式** —— 接口与 REAL 对称，节约 API 同时验证完整流水线
3. **衰退 + 演进** —— 三策略稳定哈希分配，before/after Δ均分 -14.48，**演进证据客观可量化**
4. **反向注入** —— badcase 带 provenance 流回种子，闭环已合上

谢谢老师，欢迎提问。

---

## 附录：预想可能被问到的问题

**Q：你怎么证明 v1.1 是变得"更难"而不是变得"不同"？**
答：before/after 对照实验**复用 v1.0 同一份 mock Agent 响应**——同一个 Agent 行为，同一份评测脚本，仅仅是 expected 改变，分数客观下降 -14.48。这就排除了"换题目"的可能性。如果 v1.1 只是"不同"，分数应该随机波动，不会出现系统性下降。

**Q：DECAY_THRESHOLD = 92 是怎么定的？换个值会怎样？**
答：92 是经验值——留 8 分给"自然抖动"，又足够低让大多数高分 task 入选。我设了 `config.DECAY_THRESHOLD` 单一参数：调到 85 会扩大衰退集（404 → 可能 500+），调到 95 会缩小（404 → 可能 200）。**关键是阈值固定后整套统计有可比性**。

**Q：三种演进策略选择的依据？**
答：对应三类常见 Agent 漏洞：
- **少做一步**（precondition_injection）—— Agent 经常忽略前置安全检查
- **不善终**（constraint_tighten）—— Agent 常常做完核心动作就不通知
- **被诱导**（adversarial_escalation）—— Prompt Injection 是 LLM 的经典攻击面

每种都不是凭空想的，是工业实践常见漏洞。

**Q：MOCK 模式扰动比例（40/30/30）是怎么定的？**
答：参考了人工抽检的分布感受——LLM 完全乱答属于少数（40% × error_rate），"漏一步"是最常见错误（30%），"顺序反"是次常见。这是个**经验值**，不是强精确的。MOCK 的核心目的是**让流水线在没有 API 的情况下也能跑出有梯度的分数分布**，不是模拟真实 Agent。

**Q：反向注入会不会把 badcase 里的"原题瑕疵"流回去？**
答：会，所以我设计了两层防御：
- `inject_interactive` 模式是给生产环境的，人工审一遍
- 即使是 `inject_auto` 自动注入，新种子下一轮还会再过一遍 D5 的 `schema_validator` + `llm_judge` —— **闭环里有质检关卡**

这次为节约时间用了 `auto`，但 8 条新种子都来自 score=0 的"完全答错"badcase，反映的不是题目瑕疵而是 Agent 弱点。

**Q：badcase 标了 `source_agent: deepseek` 是什么意思？**
答：不同 Agent 在不同题上失败。把 source_agent 记录下来，**后续可以做"针对某 Agent 弱点定向加题"**——比如 DeepSeek 总在 DataExportWithMasking 上摔倒，下一版评测集可以加权多生成这类题。这是为 D11+ 的"定向训练集"留的接口。

**Q：v1.1 evolved task 的 `_EVOLVED` 后缀为什么不用 `_V11`？**
答：踩过坑。matrix_expander 给原种子加了 `_V00..V19` 后缀，如果用 `_V11` 演进，**会和 V11 变体撞车**——同一个 task_id 出现在两个 case 上。`_EVOLVED` 后缀是显式、独立的命名空间。这种"看起来小但实际致命"的命名冲突，**单测一定要覆盖**——`tests/test_d8_d9.py::test_evolve_benchmark_only_touches_decay_set` 就在测这条。

**Q：MOCK 模式下 adversarial 策略真的能测 Agent 抗诱导能力吗？**
答：MOCK 模式只能测"我的评分逻辑是否正确响应了 expected 的改变"。要真测 Agent 抗诱导，必须 `EVAL_MODE=REAL` 切真 API 跑。我的设计是**接口对称**——同一份 v1.1.json，REAL 模式直接换 Adapter 就能跑。如果时间允许，6/4 终验前我会跑一次 REAL 抽样（比如 100 条）补充数据。

**Q：如果 LLM-as-Judge 也错了？（追问上次）**
答：现在 D8 评测引入了第二道兜底——**判分器是确定性的程序**（F1 + LCS + 顺序贪心），不依赖 LLM。Judge 只在 D5 自动质检阶段用过，且后面有 20% 人工抽检。所以现在的体系是：
- 造题用 LLM（D3）→ 质检阶段用 LLM Judge（D5）+ 人工兜底（D6）
- 评测阶段是**纯程序判分**（D8）→ 不存在"判分 LLM 又错了"的问题
- 衰退检测+演进是**基于客观分数**（D9）→ 也不依赖 LLM 判断

这套设计的本质：**让"判断"尽量是程序，让"创造"和"质检"才用 LLM**。

**Q：你做了那么多自动化，最不放心的是哪一环？**
答：**演进后的 v1.1 是否仍然语义合法**。precondition_injection 给 SAE 加 `Log_Event` 是合理的，但 constraint_tighten 给所有衰退 task 末尾追加 `Send_Notification` 给 audit-log，可能会和原 task 里已有的通知重复。我目前没做"语义去重"——这是 D12 代码整理时要加的一条 lint。
