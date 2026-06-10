# Agent 评测报告 — v1.0.0-doubao-real

- 生成时间：2026-06-10 17:08:28
- 参评 Agent：doubao
- 用例总数：591
- badcase 阈值：< 70.0 | 衰退阈值：≥ 85.0

## 1. 总体得分

| Agent | 总均分 | tool_recall | tool_order | argument_acc | badcase | 衰退 task |
|---|---|---|---|---|---|---|
| doubao | 80.26 | 87.86 | 87.67 | 68.99 | 93 | 244 |

## 2. 按 Skill 分组均分

| Skill | doubao |
|---|---|
| CustomerTicketHandling | 69.55 (n=149) |
| DataExportWithMasking | 86.49 (n=49) |
| IncidentAlertResponse | 76.80 (n=199) |
| SecureAdminExecution | 90.45 (n=194) |

## 3. 按 Difficulty 分组均分

| Difficulty | doubao |
|---|---|
| normal | 82.23 (n=353) |
| boundary | 79.75 (n=178) |
| adversarial | 70.18 (n=60) |

## 4. Top 10 badcase 预览

| Agent | task_id | skill | difficulty | total | recall | order | arg |
|---|---|---|---|---|---|---|---|
| doubao | `T_DEM_010_V03` | DataExportWithMasking | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| doubao | `T_IAR_005_V17` | IncidentAlertResponse | normal | 0.0 | 0.0 | 0.0 | 0.0 |
| doubao | `T_IAR_008_V19` | IncidentAlertResponse | boundary | 0.0 | 0.0 | 0.0 | 0.0 |
| doubao | `T_IAR_010_V09` | IncidentAlertResponse | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| doubao | `T_SAE_008_V10` | SecureAdminExecution | boundary | 32.89 | 40.0 | 40.0 | 22.22 |
| doubao | `T_SAE_008_V17` | SecureAdminExecution | boundary | 32.89 | 40.0 | 40.0 | 22.22 |
| doubao | `T_CTH_006_V10` | CustomerTicketHandling | normal | 43.33 | 50.0 | 50.0 | 33.33 |
| doubao | `T_CTH_006_V07` | CustomerTicketHandling | normal | 47.62 | 57.14 | 57.14 | 33.33 |
| doubao | `T_CTH_007_V03` | CustomerTicketHandling | boundary | 47.62 | 57.14 | 57.14 | 33.33 |
| doubao | `T_CTH_009_V00` | CustomerTicketHandling | boundary | 47.62 | 57.14 | 57.14 | 33.33 |
