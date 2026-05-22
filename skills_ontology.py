"""4 个 Skill 本体定义（PROJECT.md §3.3）"""
from models import SkillDefinition

SKILLS = {
    "SecureAdminExecution": SkillDefinition(
        skill_name="SecureAdminExecution",
        description="安全权限执行流：敏感命令执行前必须校验权限，执行后必须通知",
        workflow=["Verify_Permission", "Execute_CMD", "Send_Notification"],
        constraints=[
            "Verify_Permission 必须先于 Execute_CMD",
            "Execute_CMD 完成后必须 Send_Notification",
        ],
        allowed_tools=["Verify_Permission", "Execute_CMD", "Send_Notification"],
    ),
    "CustomerTicketHandling": SkillDefinition(
        skill_name="CustomerTicketHandling",
        description="客服工单处理：查询用户与库存后建单并通知",
        workflow=["Fetch_User_Data", "Check_Inventory", "Create_Ticket", "Send_Notification"],
        constraints=[
            "Create_Ticket 之前必须先 Fetch_User_Data",
            "Send_Notification 必须在所有处理动作之后",
        ],
        allowed_tools=["Fetch_User_Data", "Check_Inventory", "Create_Ticket", "Send_Notification"],
    ),
    "DataExportWithMasking": SkillDefinition(
        skill_name="DataExportWithMasking",
        description="数据导出与脱敏：验权后查数据并脱敏再发送",
        workflow=["Verify_Permission", "Query_DB", "Mask_PII", "Send_Notification"],
        constraints=[
            "Query_DB 之前必须 Verify_Permission",
            "Send_Notification 发出的内容必须是 Mask_PII 处理过的",
        ],
        allowed_tools=["Verify_Permission", "Query_DB", "Mask_PII", "Send_Notification"],
    ),
    "IncidentAlertResponse": SkillDefinition(
        skill_name="IncidentAlertResponse",
        description="异常告警处置：记录事件、查询责任人、执行处置、通知",
        workflow=["Log_Event", "Fetch_User_Data", "Execute_CMD", "Send_Notification"],
        constraints=[
            "Log_Event 必须最先调用",
            "Execute_CMD 之前必须 Fetch_User_Data 确认责任人",
        ],
        allowed_tools=["Log_Event", "Fetch_User_Data", "Execute_CMD", "Send_Notification"],
    ),
}
