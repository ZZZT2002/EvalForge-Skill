"""hello_deepseek.py —— D0 验证 DeepSeek function calling 可用

运行前：
1. pip install -r requirements.txt
2. 设置环境变量 DEEPSEEK_API_KEY（或写到 .env 后用 dotenv 加载）
3. python hello_deepseek.py

预期：模型识别用户意图，返回一个 tool_calls，其中 tool name = "Verify_Permission"，
      args 包含 user_id 和 action。
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # 从 .env 读取 DEEPSEEK_API_KEY

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

if not API_KEY:
    raise SystemExit("请先设置环境变量 DEEPSEEK_API_KEY")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "Verify_Permission",
            "description": "校验用户是否有权限执行某操作",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "形如 USR_777"},
                    "action": {"type": "string", "enum": ["READ", "WRITE", "DELETE", "ADMIN"]},
                },
                "required": ["user_id", "action"],
            },
        },
    }
]

PROMPT = "请帮我校验用户 USR_777 是否有 DELETE 权限。"


def main():
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": PROMPT}],
        tools=TOOLS,
        tool_choice="auto",
    )
    msg = response.choices[0].message
    print("=== content ===")
    print(msg.content)
    print("=== tool_calls ===")
    if msg.tool_calls:
        for tc in msg.tool_calls:
            print(f"name: {tc.function.name}")
            print(f"args: {json.loads(tc.function.arguments)}")
    else:
        print("(no tool calls — 模型未触发 function calling)")


if __name__ == "__main__":
    main()
