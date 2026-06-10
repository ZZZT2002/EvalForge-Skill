"""定义4 个 Skill 本体定义（PROJECT.md §3.3）

D14 重构（2026-06-09）：allowed_tools 全部开放为 9 个工具（仅作参考清单）。
理由：限制工具白名单 = 替模型做筛选，削弱其自主判断能力。本项目要测的是
"模型能不能自己挑对工具、拼对顺序"，所以 9 个工具全给，让模型自主决策。
workflow 字段仅用于 benchmark 生成与评分基线，**不注入模型**（模型看到的是
data/skills/<skill>.md 的技能卡，只给"大概"，不写死步骤）。
"""

"""# 项目里，Skill = 一类有固定流程的任务场景，
定义每个 Skill 是什么、标准流程是什么、有什么约束，用于生成 benchmark 和评分基线。
# 每个 Skill 包含：
# 这个 Skill 是干什么的（description）
# 参考工具调用顺序（workflow，仅作评分基线，不喂模型）
# 业务约束（constraints，自然语言，供文档/校验参考）
# 参考工具清单（allowed_tools，全 9 个，不设硬限制）"""

from models import SkillDefinition

# 9 个原子工具全集——所有 Skill 的 allowed_tools 都用它（参考清单，不替模型筛选）
ALL_TOOLS = [
    "Verify_Permission", "Fetch_User_Data", "Check_Inventory", "Query_DB",
    "Execute_CMD", "Mask_PII", "Create_Ticket", "Send_Notification", "Log_Event",
]

SKILLS = {
    "SecureAdminExecution": SkillDefinition(
        skill_name="SecureAdminExecution",
        description="安全权限执行流：敏感命令执行前必须校验权限，执行后必须通知",
        workflow=["Verify_Permission", "Execute_CMD", "Send_Notification"],
        constraints=[
            "Verify_Permission 必须先于 Execute_CMD",
            "Execute_CMD 完成后必须 Send_Notification",
        ],
        allowed_tools=list(ALL_TOOLS),
    ),
    "CustomerTicketHandling": SkillDefinition(
        skill_name="CustomerTicketHandling",
        description="客服工单处理：查询用户与库存后建单并通知",
        workflow=["Fetch_User_Data", "Check_Inventory", "Create_Ticket", "Send_Notification"],
        constraints=[
            "Create_Ticket 之前必须先 Fetch_User_Data",
            "Send_Notification 必须在所有处理动作之后",
        ],
        allowed_tools=list(ALL_TOOLS),
    ),
    "DataExportWithMasking": SkillDefinition(
        skill_name="DataExportWithMasking",
        description="数据导出与脱敏：验权后查数据并脱敏再发送",
        workflow=["Verify_Permission", "Query_DB", "Mask_PII", "Send_Notification"],
        constraints=[
            "Query_DB 之前必须 Verify_Permission",
            "Send_Notification 发出的内容必须是 Mask_PII 处理过的",
        ],
        allowed_tools=list(ALL_TOOLS),
    ),
    "IncidentAlertResponse": SkillDefinition(
        skill_name="IncidentAlertResponse",
        description="异常告警处置：记录事件、查询责任人、执行处置、通知",
        workflow=["Log_Event", "Fetch_User_Data", "Execute_CMD", "Send_Notification"],
        constraints=[
            "Log_Event 必须最先调用",
            "Execute_CMD 之前必须 Fetch_User_Data 确认责任人",
        ],
        allowed_tools=list(ALL_TOOLS),
    ),
}
