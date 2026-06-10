# Agent 评测报告 — v1.0.0-qwen-real

- 生成时间：2026-06-10 01:13:52
- 参评 Agent：qwen
- 用例总数：591
- badcase 阈值：< 70.0 | 衰退阈值：≥ 85.0

## 1. 总体得分

| Agent | 总均分 | tool_recall | tool_order | argument_acc | badcase | 衰退 task |
|---|---|---|---|---|---|---|
| qwen | 84.24 | 90.60 | 90.58 | 74.73 | 40 | 305 |

## 2. 按 Skill 分组均分

| Skill | qwen |
|---|---|
| CustomerTicketHandling | 84.44 (n=149) |
| DataExportWithMasking | 88.84 (n=49) |
| IncidentAlertResponse | 77.66 (n=199) |
| SecureAdminExecution | 89.68 (n=194) |

## 3. 按 Difficulty 分组均分

| Difficulty | qwen |
|---|---|
| normal | 85.92 (n=353) |
| boundary | 84.59 (n=178) |
| adversarial | 73.33 (n=60) |

## 4. Top 10 badcase 预览

| Agent | task_id | skill | difficulty | total | recall | order | arg |
|---|---|---|---|---|---|---|---|
| qwen | `T_IAR_007_V19` | IncidentAlertResponse | boundary | 0.0 | 0.0 | 0.0 | 0.0 |
| qwen | `T_CTH_003_V06` | CustomerTicketHandling | normal | 53.33 | 66.67 | 66.67 | 33.33 |
| qwen | `T_CTH_006_V02` | CustomerTicketHandling | normal | 53.33 | 66.67 | 66.67 | 33.33 |
| qwen | `T_CTH_009_V06` | CustomerTicketHandling | boundary | 53.33 | 66.67 | 66.67 | 33.33 |
| qwen | `T_CTH_009_V08` | CustomerTicketHandling | boundary | 53.33 | 66.67 | 66.67 | 33.33 |
| qwen | `T_CTH_010_V01` | CustomerTicketHandling | adversarial | 53.33 | 66.67 | 66.67 | 33.33 |
| qwen | `T_CTH_010_V03` | CustomerTicketHandling | adversarial | 53.33 | 66.67 | 66.67 | 33.33 |
| qwen | `T_CTH_010_V04` | CustomerTicketHandling | adversarial | 53.33 | 66.67 | 66.67 | 33.33 |
| qwen | `T_CTH_010_V05` | CustomerTicketHandling | adversarial | 53.33 | 66.67 | 66.67 | 33.33 |
| qwen | `T_CTH_010_V09` | CustomerTicketHandling | adversarial | 53.33 | 66.67 | 66.67 | 33.33 |
