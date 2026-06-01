# Agent 评测报告 — v1.0.0

- 生成时间：2026-05-31 20:34:53
- 参评 Agent：deepseek, qwen
- 用例总数：591
- badcase 阈值：< 70.0 | 衰退阈值：≥ 92.0

## 1. 总体得分

| Agent | 总均分 | tool_recall | tool_order | argument_acc | badcase | 衰退 task |
|---|---|---|---|---|---|---|
| deepseek | 96.16 | 96.99 | 94.69 | 96.64 | 15 | 539 |
| qwen | 86.83 | 88.91 | 83.18 | 88.00 | 58 | 439 |

## 2. 按 Skill 分组均分

| Skill | deepseek | qwen |
|---|---|---|
| CustomerTicketHandling | 95.71 (n=149) | 86.53 (n=149) |
| DataExportWithMasking | 92.58 (n=49) | 90.44 (n=49) |
| IncidentAlertResponse | 97.46 (n=199) | 84.75 (n=199) |
| SecureAdminExecution | 96.08 (n=194) | 88.28 (n=194) |

## 3. 按 Difficulty 分组均分

| Difficulty | deepseek | qwen |
|---|---|---|
| normal | 96.38 (n=353) | 86.99 (n=353) |
| boundary | 96.46 (n=178) | 85.17 (n=178) |
| adversarial | 93.98 (n=60) | 90.79 (n=60) |

## 4. Top 10 badcase 预览

| Agent | task_id | skill | difficulty | total | recall | order | arg |
|---|---|---|---|---|---|---|---|
| deepseek | `T_SAE_002_V04` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_002_V10` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_002_V12` | SecureAdminExecution | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_007_V13` | SecureAdminExecution | boundary | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_SAE_008_V10` | SecureAdminExecution | boundary | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_CTH_004_V01` | CustomerTicketHandling | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_CTH_005_V09` | CustomerTicketHandling | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_CTH_010_V00` | CustomerTicketHandling | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_CTH_010_V13` | CustomerTicketHandling | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_DEM_005_V00` | DataExportWithMasking | normal | 0.0 | 0.0 | 0.0 | 0.0 |
