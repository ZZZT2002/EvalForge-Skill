# Agent 评测报告 — v1.0.0

- 生成时间：2026-06-10 17:51:32
- 参评 Agent：deepseek, qwen
- 用例总数：591
- badcase 阈值：< 70.0 | 衰退阈值：≥ 85.0

## 1. 总体得分

| Agent | 总均分 | tool_recall | tool_order | argument_acc | badcase | 衰退 task |
|---|---|---|---|---|---|---|
| deepseek | 94.31 | 95.38 | 92.18 | 95.11 | 25 | 526 |
| qwen | 86.30 | 88.03 | 83.04 | 87.45 | 66 | 454 |

## 2. 按 Skill 分组均分

| Skill | deepseek | qwen |
|---|---|---|
| CustomerTicketHandling | 96.04 (n=149) | 87.15 (n=149) |
| DataExportWithMasking | 92.12 (n=49) | 90.62 (n=49) |
| IncidentAlertResponse | 96.39 (n=199) | 84.33 (n=199) |
| SecureAdminExecution | 91.41 (n=194) | 86.58 (n=194) |

## 3. 按 Difficulty 分组均分

| Difficulty | deepseek | qwen |
|---|---|---|
| normal | 93.33 (n=353) | 84.44 (n=353) |
| boundary | 95.87 (n=178) | 87.75 (n=178) |
| adversarial | 95.49 (n=60) | 92.97 (n=60) |

## 4. Top 10 badcase 预览

| Agent | task_id | skill | difficulty | total | recall | order | arg |
|---|---|---|---|---|---|---|---|
| deepseek | `T_SAE_001_V15` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_002_V11` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_003_V02` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_003_V14` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_004_V16` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_005_V03` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_006_V02` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_006_V11` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_006_V14` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_007_V06` | SecureAdminExecution | boundary | 0.0 | 0.0 | 0.0 | 0.0 |
