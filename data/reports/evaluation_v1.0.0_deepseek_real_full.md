# Agent 评测报告 — v1.0.0-deepseek-real

- 生成时间：2026-06-09 17:39:23
- 参评 Agent：deepseek
- 用例总数：591
- badcase 阈值：< 70.0 | 衰退阈值：≥ 85.0

## 1. 总体得分

| Agent | 总均分 | tool_recall | tool_order | argument_acc | badcase | 衰退 task |
|---|---|---|---|---|---|---|
| deepseek | 83.63 | 88.55 | 88.14 | 76.57 | 28 | 293 |

## 2. 按 Skill 分组均分

| Skill | deepseek |
|---|---|
| CustomerTicketHandling | 86.44 (n=149) |
| DataExportWithMasking | 85.96 (n=49) |
| IncidentAlertResponse | 75.85 (n=199) |
| SecureAdminExecution | 88.87 (n=194) |

## 3. 按 Difficulty 分组均分

| Difficulty | deepseek |
|---|---|
| normal | 85.43 (n=353) |
| boundary | 82.78 (n=178) |
| adversarial | 75.60 (n=60) |

## 4. Top 10 badcase 预览

| Agent | task_id | skill | difficulty | total | recall | order | arg |
|---|---|---|---|---|---|---|---|
| deepseek | `T_IAR_009_V02` | IncidentAlertResponse | boundary | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_IAR_010_V10` | IncidentAlertResponse | adversarial | 0.0 | 0.0 | 0.0 | 0.0 |
| deepseek | `T_IAR_010_V12` | IncidentAlertResponse | adversarial | 50.0 | 66.67 | 44.44 | 41.67 |
| deepseek | `T_DEM_010_V00` | DataExportWithMasking | adversarial | 54.29 | 57.14 | 57.14 | 50.0 |
| deepseek | `T_IAR_010_V06` | IncidentAlertResponse | adversarial | 54.67 | 66.67 | 60.0 | 41.67 |
| deepseek | `T_DEM_009_V03` | DataExportWithMasking | boundary | 55.0 | 66.67 | 66.67 | 37.5 |
| deepseek | `T_DEM_010_V04` | DataExportWithMasking | adversarial | 56.67 | 66.67 | 66.67 | 41.67 |
| deepseek | `T_IAR_010_V02` | IncidentAlertResponse | adversarial | 56.67 | 66.67 | 66.67 | 41.67 |
| deepseek | `T_IAR_010_V05` | IncidentAlertResponse | adversarial | 56.67 | 66.67 | 66.67 | 41.67 |
| deepseek | `T_IAR_010_V08` | IncidentAlertResponse | adversarial | 56.67 | 66.67 | 66.67 | 41.67 |
