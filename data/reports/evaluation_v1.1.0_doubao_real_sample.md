# Agent 评测报告 — v1.1.0-real_sample

- 生成时间：2026-06-05 12:52:57
- 参评 Agent：doubao
- 用例总数：591
- badcase 阈值：< 70.0 | 衰退阈值：≥ 92.0

## 1. 总体得分

| Agent | 总均分 | tool_recall | tool_order | argument_acc | badcase | 衰退 task |
|---|---|---|---|---|---|---|
| doubao | 81.91 | 93.82 | 91.39 | 65.86 | 2 | 88 |

## 2. 按 Skill 分组均分

| Skill | doubao |
|---|---|
| CustomerTicketHandling | 83.99 (n=149) |
| DataExportWithMasking | 77.01 (n=49) |
| IncidentAlertResponse | 81.05 (n=199) |
| SecureAdminExecution | 82.43 (n=194) |

## 3. 按 Difficulty 分组均分

| Difficulty | doubao |
|---|---|
| normal | 90.67 (n=114) |
| boundary | 91.10 (n=55) |
| adversarial | 78.34 (n=422) |

## 4. Top 10 badcase 预览

| Agent | task_id | skill | difficulty | total | recall | order | arg |
|---|---|---|---|---|---|---|---|
| doubao | `T_DEM_010_V04_EVOLVED` | DataExportWithMasking | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| doubao | `T_DEM_010_V02_EVOLVED` | DataExportWithMasking | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
