"""Pydantic 数据契约（PROJECT.md §4）
定义整个评测框架中所有核心数据结构的「标准格式」
用 Pydantic 规定了 Skill、测试用例、期望输出长什么样，确保数据在流转过程中格式正确、不出错。
"""
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
    __test__ = False  # 告诉 pytest 这不是测试类（避免 PytestCollectionWarning）

    task_id: str
    skill_definition: SkillDefinition
    prompt: str
    expected_tool_calls: List[ExpectedToolCall]
    difficulty: str                  # normal / boundary / adversarial
    version: str
    created_at: str
    updated_at: Optional[str] = None
    tags: List[str] = []
