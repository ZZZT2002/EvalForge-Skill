# Agent 评测报告 — v1.1.0-full

- 生成时间：2026-06-04 21:02:35
- 参评 Agent：deepseek
- 用例总数：591
- badcase 阈值：< 70.0 | 衰退阈值：≥ 92.0

## 1. 总体得分

| Agent | 总均分 | tool_recall | tool_order | argument_acc | badcase | 衰退 task |
|---|---|---|---|---|---|---|
| deepseek | 70.19 | 79.87 | 78.04 | 57.04 | 104 | 100 |

## 2. 按 Skill 分组均分

| Skill | deepseek |
|---|---|
| CustomerTicketHandling | 74.80 (n=149) |
| DataExportWithMasking | 57.45 (n=49) |
| IncidentAlertResponse | 67.35 (n=199) |
| SecureAdminExecution | 72.78 (n=194) |

## 3. 按 Difficulty 分组均分

| Difficulty | deepseek |
|---|---|
| normal | 90.92 (n=114) |
| boundary | 90.35 (n=55) |
| adversarial | 61.96 (n=422) |

## 4. Top 10 badcase 预览

| Agent | task_id | skill | difficulty | total | recall | order | arg |
|---|---|---|---|---|---|---|---|
| deepseek | `T_SAE_001_V17_EVOLVED` | SecureAdminExecution | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_002_V02_EVOLVED` | SecureAdminExecution | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_002_V16_EVOLVED` | SecureAdminExecution | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_003_V01_EVOLVED` | SecureAdminExecution | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_003_V03_EVOLVED` | SecureAdminExecution | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_003_V14_EVOLVED` | SecureAdminExecution | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_003_V16_EVOLVED` | SecureAdminExecution | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_003_V17_EVOLVED` | SecureAdminExecution | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_004_V07_EVOLVED` | SecureAdminExecution | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_004_V11_EVOLVED` | SecureAdminExecution | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
