"""定义9个工具中每个工具的参数格式、类型、必填字段、约束条件，用于验证和生成模型调用。"""

TOOLS_SCHEMA = {
    "Verify_Permission": {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "pattern": "^USR_\\d{3}$"},
            "action": {"type": "string", "enum": ["READ", "WRITE", "DELETE", "ADMIN"]},
        },
        "required": ["user_id", "action"],
    },
    "Fetch_User_Data": {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "pattern": "^USR_\\d{3}$"},
        },
        "required": ["user_id"],
    },
    "Check_Inventory": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
        },
        "required": ["item_id"],
    },
    "Query_DB": {
        "type": "object",
        "properties": {
            "table": {"type": "string"},
            "conditions": {"type": "object"},
        },
        "required": ["table", "conditions"],
    },
    "Execute_CMD": {
        "type": "object",
        "properties": {
            "target_ip": {"type": "string", "format": "ipv4"},
            "command": {"type": "string"},
        },
        "required": ["target_ip", "command"],
    },
    "Mask_PII": {
        "type": "object",
        "properties": {
            "data": {"type": "string"},
            "fields": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["data", "fields"],
    },
    "Create_Ticket": {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "pattern": "^USR_\\d{3}$"},
            "issue": {"type": "string"},
            "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"]},
        },
        "required": ["user_id", "issue", "priority"],
    },
    "Send_Notification": {
        "type": "object",
        "properties": {
            "channel": {"type": "string", "enum": ["Email", "Slack", "SMS", "Audit"]},
            "receiver": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["channel", "receiver", "content"],
    },
    "Log_Event": {
        "type": "object",
        "properties": {
            "event_type": {"type": "string"},
            "details": {"type": "object"},
        },
        "required": ["event_type", "details"],
    },
}
