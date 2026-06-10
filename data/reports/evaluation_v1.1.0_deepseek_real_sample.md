# Agent 评测报告 — v1.1.0-real_sample

- 生成时间：2026-06-09 21:08:16
- 参评 Agent：deepseek
- 用例总数：591
- badcase 阈值：< 70.0 | 衰退阈值：≥ 85.0

## 1. 总体得分

| Agent | 总均分 | tool_recall | tool_order | argument_acc | badcase | 衰退 task |
|---|---|---|---|---|---|---|
| deepseek | 74.83 | 82.52 | 82.11 | 63.60 | 101 | 116 |

## 2. 按 Skill 分组均分

| Skill | deepseek |
|---|---|
| CustomerTicketHandling | 81.34 (n=149) |
| DataExportWithMasking | 72.14 (n=49) |
| IncidentAlertResponse | 76.48 (n=199) |
| SecureAdminExecution | 68.81 (n=194) |

## 3. 按 Difficulty 分组均分

| Difficulty | deepseek |
|---|---|
| normal | 79.42 (n=157) |
| boundary | 80.00 (n=100) |
| adversarial | 71.13 (n=334) |

## 4. Top 10 badcase 预览

| Agent | task_id | skill | difficulty | total | recall | order | arg |
|---|---|---|---|---|---|---|---|
| deepseek | `T_CTH_003_V04_EVOLVED` | CustomerTicketHandling | adversarial | 25.24 | 33.33 | 28.57 | 16.67 |
| deepseek | `T_CTH_010_V11_EVOLVED` | CustomerTicketHandling | adversarial | 30.67 | 40.0 | 40.0 | 16.67 |
| deepseek | `T_CTH_005_V05_EVOLVED` | CustomerTicketHandling | adversarial | 30.67 | 40.0 | 40.0 | 16.67 |
| deepseek | `T_SAE_008_V15_EVOLVED` | SecureAdminExecution | adversarial | 37.33 | 40.0 | 40.0 | 33.33 |
| deepseek | `T_SAE_005_V19_EVOLVED` | SecureAdminExecution | adversarial | 37.33 | 40.0 | 40.0 | 33.33 |
| deepseek | `T_CTH_008_V09_EVOLVED` | CustomerTicketHandling | adversarial | 41.67 | 50.0 | 44.44 | 33.33 |
| deepseek | `T_SAE_004_V08_EVOLVED` | SecureAdminExecution | adversarial | 43.33 | 50.0 | 50.0 | 33.33 |
| deepseek | `T_SAE_007_V04_EVOLVED` | SecureAdminExecution | adversarial | 43.33 | 50.0 | 50.0 | 33.33 |
| deepseek | `T_SAE_003_V06_EVOLVED` | SecureAdminExecution | adversarial | 43.33 | 50.0 | 50.0 | 33.33 |
| deepseek | `T_SAE_007_V05_EVOLVED` | SecureAdminExecution | adversarial | 43.33 | 50.0 | 50.0 | 33.33 |
