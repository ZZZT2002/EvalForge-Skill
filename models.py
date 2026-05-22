"""Pydantic 数据契约（PROJECT.md §4）"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class SkillDefinition(BaseModel):
    """Skill 本体定义"""
    skill_name: str
    description: str
    workflow: List[str]              # 标准工具调用顺序
    constraints: List[str]           # 业务约束（自然语言）
    allowed_tools: List[str]         # 工具白名单


class ExpectedToolCall(BaseModel):
    tool: str
    args: Dict[str, Any]


class TestCase(BaseModel):
    task_id: str
    skill_definition: SkillDefinition
    prompt: str
    expected_tool_calls: List[ExpectedToolCall]
    difficulty: str                  # normal / boundary / adversarial
    version: str
    created_at: str
    updated_at: Optional[str] = None
    tags: List[str] = []
